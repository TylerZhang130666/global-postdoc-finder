"""Index terms from verified notice bodies without republishing whole adverts."""
from datetime import datetime, timezone, timedelta
from html import unescape
import json
import re
import unicodedata

INDEX_VERSION = 2
PHRASES = ('machine learning','remote sensing','soil carbon','soil organic carbon','artificial intelligence','deep learning','data science','climate change','soil science','soil ecology','freeze thaw')
SKIP_TAGS = {'script','style','template','nav','header','footer','aside','form','dialog','button'}

def node_text(node):
    if node.tag in SKIP_TAGS:
        return ''
    return ' '.join(node_text(c) if hasattr(c,'tag') else c for c in node.children)

def canonical_title(value):
    value=re.sub(r'<[^>]*>',' ',unescape(str(value)))
    return ''.join(c for c in unicodedata.normalize('NFKC',value).lower() if c.isalnum())

def title_matches(expected,actual):
    expected,actual=canonical_title(expected),canonical_title(actual)
    return bool(expected and actual and (expected==actual or len(expected)>=80 and actual.startswith(expected)))

def find_attr(doc,key,value,tag=None):
    return next((n for n in doc.all(tag) if n.attrs.get(key)==value),None)

def meaningful(node):
    return re.sub(r'\s+',' ',node_text(node)).strip() if node else ''

def plain_text(value, Document):
    return re.sub(r'\s+',' ',node_text(Document(unescape(value)).root)).strip()

def terms(text):
    # Discard addresses and contact strings before tokenization. Store a bag of
    # distinct alphabetic words, not the complete advertisement or contact data.
    text=re.sub(r'https?://\S+|\S+@\S+|\S+\s*\(at\)\s*\S+',' ',text,flags=re.I)
    text=unicodedata.normalize('NFKC',text).lower().replace('–',' ').replace('-',' ')
    words=sorted({word for word in re.findall(r'[^\W\d_]{2,35}',text,re.UNICODE)})
    words=sorted(set(words)|set(re.findall(r'(?<!\w)(?:r|c\+\+|c#)(?!\w)',text)))
    return words, [phrase for phrase in PHRASES if phrase in text]

def json_postings(doc):
    def walk(value):
        if isinstance(value,list):
            for item in value: yield from walk(item)
        elif isinstance(value,dict):
            kind=value.get('@type',[])
            if kind=='JobPosting' or isinstance(kind,list) and 'JobPosting' in kind:yield value
            for key in ('@graph','mainEntity','itemListElement','item'):
                if key in value:yield from walk(value[key])
    for script in doc.all('script'):
        if script.attrs.get('type')!='application/ld+json':continue
        try:
            raw=''.join(c for c in script.children if isinstance(c,str))
            yield from walk(json.loads(raw))
        except (ValueError,TypeError):continue

def notice_body(doc,record,Document):
    if any(h.text().lower()=='javascript is disabled' for h in doc.all('h1')):
        raise ValueError('Access restricted: JavaScript verification page')
    postings=[p for p in json_postings(doc) if title_matches(record['title'],p.get('title',''))]
    posting=postings[0] if postings else {}
    headings=[n for n in doc.all() if n.tag in {'h1','h2','h3','h4','h5'}]
    matched=next((h for h in headings if title_matches(record['title'],h.text())),None)
    sid=record['source_id']
    if sid=='stanford':
        mentor=record['title'].rsplit('·',1)[-1].strip()
        matched=next((h for h in doc.all('h1') if 'postdoc' in h.text().lower() and len(canonical_title(mentor))>=5 and canonical_title(mentor) in canonical_title(h.text())),None)
    body_node=None;locator=''
    if matched or posting:
        if sid=='academictransfer' and matched:
            body_node=matched.parent
            locator='section:vacancy'
        elif sid in {'hku','csiro'}:
            body_node=find_attr(doc,'itemprop','description');locator='itemprop:description'
        elif sid=='yale':
            body_node=next(doc.all('main'),None);locator='main:post'
        elif sid=='stanford':
            body_node=next(doc.all('article','node-postdocs-job'),None);locator='article:node-postdocs-job'
        elif sid=='leibniz':
            body_node=next(doc.all('div','tx_jobfair'),None);locator='div:tx_jobfair'
        elif sid=='mpg':
            body_node=next(doc.all('main','content'),None);locator='main:content'
        elif sid=='eth':
            body_node=next(doc.all('section','description'),None);locator='section:description'
        elif sid=='copenhagen':
            body_node=next(doc.all('div','vacancy_details_area'),None);locator='div:vacancy_details_area'
        elif sid=='kth':
            body_node=next(doc.all('div','job-details-content'),None);locator='div:job-details-content'
        elif sid=='ubc':
            body_node=next(doc.all('article','node--type-job-posting'),None);locator='article:node--type-job-posting'
        elif sid=='jobsuk':
            body_node=find_attr(doc,'id','job-description') or next(doc.all('div','j-advert__text'),None);locator='job-description'
    if sid=='jrec':
        # JREC uses a bilingual title field, not a page H1. Match that field,
        # then confine indexing to the individual notice card body.
        title_nodes=[n for n in doc.all() if 'title' in n.attrs.get('class','').lower()]
        matched=next((n for n in title_nodes if title_matches(record['title'],n.text())),None)
        if matched:
            body_node=next(doc.all('div','card_body'),None);locator='div:card_body'
    body=meaningful(body_node)
    if len(body)>=150 and (matched or posting):return body,locator,posting
    if posting:
        parts=[]
        for key in ('description','qualifications','skills','responsibilities','experienceRequirements','educationRequirements'):
            value=posting.get(key)
            if isinstance(value,str):parts.append(plain_text(value,Document))
        body=' '.join(parts)
        if len(body)>=150:return body,'JobPosting.description+requirements',posting
    raise ValueError('No matching job-specific notice body')

def deadline_from_text(body,parse_date):
    # A date of publication, project start, or degree award must never silently
    # turn into an application deadline. Ambiguous/multiple dates remain blank.
    explicit=re.findall(r'(?:application deadline|closing date|Bewerbungsfrist)\s*(?:is|:|on)?\s*([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4}|\d{1,2} [A-Za-z]+ \d{4})',body,re.I)
    if not explicit:
        for sentence in re.split(r'(?<=[.!?])\s+',body):
            if not re.search(r'please (?:send|submit|upload)|(?:apply|applications? must be (?:received|submitted))',sentence,re.I):continue
            explicit.extend(re.findall(r'(?:\bby|\buntil|\bbefore|no later than)\s+([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2} [A-Za-z]+ \d{4}|\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4})',sentence,re.I))
    dates=set()
    for value in explicit:
        date=parse_date(value)
        if not date:
            for fmt in ('%d %B %Y','%B %d %Y'):
                try:date=datetime.strptime(value,fmt).date().isoformat();break
                except ValueError:pass
        if date:dates.add(date)
    return dates.pop() if len(dates)==1 else ''

def detail_document(record,client,Document):
    doc=Document(client.get(record['url'])).root
    if record['source_id']=='jrec':
        button=next((b for b in doc.all('button') if b.attrs.get('name')=='changeLangBtn' and b.attrs.get('value')=='1'),None)
        if button:
            from urllib.parse import urlsplit,parse_qsl,urlencode
            identifier=dict(parse_qsl(urlsplit(record['url']).query)).get('id')
            if identifier and button.attrs.get('data-id')==identifier:
                # Parameters come from the notice's own public language form.
                doc=Document(client.get('https://jrecin.jst.go.jp/seek/SeekJorDetail/Changelang?'+urlencode({'id':identifier,'lang':'1'}))).root
    return doc

def enrich_record(record,client,Document,parse_date,now):
    doc=detail_document(record,client,Document)
    body,locator,posting=notice_body(doc,record,Document)
    words,phrases=terms(body)
    result=dict(record,search_terms=words,search_phrases=phrases,detail_status='indexed',
                detail_checked_at=now,detail_locator=locator,detail_index_version=INDEX_VERSION)
    result.pop('detail_error',None)
    result.pop('detail_refresh_failed',None)
    deadline=posting.get('validThrough')
    if isinstance(deadline,str) and re.match(r'^\d{4}-\d{2}-\d{2}(?:T|$)',deadline):
        try:datetime.fromisoformat(deadline.replace('Z','+00:00'));result['deadline_at']=deadline
        except ValueError:pass
    elif not record.get('deadline_at'):
        deadline=deadline_from_text(body,parse_date)
        if deadline:result['deadline_at']=deadline
    return result

def merge_cache_snapshots(repository,published):
    """Use newer listing coverage without discarding newer validated body evidence."""
    if published.get('generated_at','')<=repository.get('generated_at',''):return repository
    older={r['id']:r for r in repository.get('jobs',[])}
    merged=[]
    for row in published.get('jobs',[]):
        old=older.get(row['id'],{})
        if (canonical_title(old.get('title',''))==canonical_title(row.get('title',''))
            and old.get('detail_status')=='indexed'
            and (old.get('detail_index_version',0),old.get('detail_checked_at',''))>
                (row.get('detail_index_version',0),row.get('detail_checked_at',''))):
            row={**row,**{k:old[k] for k in CACHE_FIELDS if k in old}}
        merged.append(row)
    present={r['id'] for r in merged}
    # These are cache candidates only. combine() still replaces successful
    # source lists, so a removed vacancy cannot be resurrected by this union.
    merged.extend(r for r in repository.get('jobs',[]) if r['id'] not in present and r.get('detail_status')=='indexed')
    return {**published,'jobs':merged}

def body_coverage(rows):
    indexed=sum(r.get('detail_status')=='indexed' and r.get('detail_index_version')==INDEX_VERSION for r in rows)
    unavailable=sum(r.get('detail_status')=='unavailable' for r in rows)
    return dict(body_total=len(rows),body_indexed=indexed,body_unavailable=unavailable,
                body_pending=len(rows)-indexed-unavailable,
                body_refresh_failed=sum(bool(r.get('detail_refresh_failed')) for r in rows))

CACHE_FIELDS=('search_terms','search_phrases','detail_status','detail_checked_at','detail_locator','detail_index_version','detail_attempted_at','detail_error','detail_refresh_failed')
def enrich_source(rows,source,previous,Client,Document,parse_date,now):
    budget=source.get('detail_budget',0)
    old={r['id']:r for r in previous.get('jobs',[])}
    client=None
    checked=0
    result=[]
    cutoff=(datetime.fromisoformat(now)-timedelta(days=1)).isoformat()
    retry=(datetime.fromisoformat(now)-timedelta(hours=6)).isoformat()
    for row in rows:
        cached=old.get(row['id'],{})
        previous_ok=(cached.get('detail_status')=='indexed' and cached.get('detail_index_version')==INDEX_VERSION and canonical_title(cached.get('title',''))==canonical_title(row['title']))
        if previous_ok:
            row={**row,**{key:cached[key] for key in CACHE_FIELDS if key in cached}}
            if cached.get('deadline_at') and not row.get('deadline_at'):row['deadline_at']=cached['deadline_at']
        fresh=previous_ok and cached.get('detail_checked_at','')>=cutoff
        backoff=bool(cached.get('detail_error')) and cached.get('detail_attempted_at','')>=retry
        if not previous_ok:row=dict(row,detail_status='pending')
        if not fresh and not backoff and checked<budget:
            checked+=1
            try:
                if client is None:client=Client(source)
                row=enrich_record(row,client,Document,parse_date,now)
            except Exception as error:
                # A failed refresh must not advance successful evidence dates.
                if not previous_ok:row['detail_status']='unavailable'
                row['detail_error']='access_restricted' if any(t in str(error).lower() for t in ('403','robots','javascript','access')) else 'fetch_or_parse_failed'
                row['detail_refresh_failed']=True
            row['detail_attempted_at']=now
        elif backoff:
            for key in ('detail_status','detail_attempted_at','detail_error','detail_refresh_failed'):
                if key in cached:row[key]=cached[key]
        result.append(row)
    return result
