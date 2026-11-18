"""Index terms from verified notice bodies without republishing whole adverts."""
from datetime import datetime, timezone, timedelta
from html import unescape
import json
import re
import unicodedata

INDEX_VERSION = 1
PHRASES = ('machine learning','remote sensing','soil carbon','soil organic carbon','artificial intelligence','deep learning','data science','climate change','soil science','soil ecology','freeze thaw')
SKIP_TAGS = {'script','style','template','nav','header','footer','aside','form'}

def node_text(node):
    if node.tag in SKIP_TAGS:
        return ''
    return ' '.join(node_text(c) if hasattr(c,'tag') else c for c in node.children)

def canonical_title(value):
    return ''.join(c for c in unicodedata.normalize('NFKC',unescape(value)).lower() if c.isalnum())

def plain_text(value, Document):
    return re.sub(r'\s+',' ',node_text(Document(unescape(value)).root)).strip()

def terms(text):
    # Discard addresses and contact strings before tokenization. Store a bag of
    # distinct alphabetic words, not the complete advertisement or contact data.
    text=re.sub(r'https?://\S+|\S+@\S+|\S+\s*\(at\)\s*\S+',' ',text,flags=re.I)
    text=unicodedata.normalize('NFKC',text).lower().replace('–',' ').replace('-',' ')
    words=sorted({word for word in re.findall(r'[^\W\d_]{2,35}',text,re.UNICODE)})
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
    for posting in json_postings(doc):
        if canonical_title(posting.get('title','')) != canonical_title(record['title']):continue
        description=posting.get('description')
        if isinstance(description,str):
            body=plain_text(description,Document)
            if len(body)>=150:return body,'JobPosting.description',posting
    if record['source_id']=='leibniz':
        box=doc.first('div','tx_jobfair')
        heading=box.first('h1')
        if canonical_title(heading.text())!=canonical_title(record['title']):
            raise ValueError('Notice title does not match listed vacancy')
        body=re.sub(r'\s+',' ',node_text(box)).strip()
        if len(body)>=150:return body,'tx_jobfair',{}
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

def enrich_record(record,client,Document,parse_date,now):
    doc=Document(client.get(record['url'])).root
    body,locator,posting=notice_body(doc,record,Document)
    words,phrases=terms(body)
    result=dict(record,search_terms=words,search_phrases=phrases,detail_status='indexed',
                detail_checked_at=now,detail_locator=locator,detail_index_version=INDEX_VERSION)
    deadline=posting.get('validThrough')
    if isinstance(deadline,str) and re.match(r'^\d{4}-\d{2}-\d{2}(?:T|$)',deadline):
        try:datetime.fromisoformat(deadline.replace('Z','+00:00'));result['deadline_at']=deadline
        except ValueError:pass
    elif not record.get('deadline_at'):
        deadline=deadline_from_text(body,parse_date)
        if deadline:result['deadline_at']=deadline
    return result

CACHE_FIELDS=('search_terms','search_phrases','detail_status','detail_checked_at','detail_locator','detail_index_version')
def enrich_source(rows,source,previous,Client,Document,parse_date,now):
    budget=source.get('detail_budget',0)
    if not budget:return rows
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
        backoff=not previous_ok and cached.get('detail_attempted_at','')>=retry
        if not fresh and not backoff and checked<budget:
            checked+=1
            try:
                if client is None:client=Client(source)
                row=enrich_record(row,client,Document,parse_date,now)
            except Exception:
                # A failed refresh must not advance successful evidence dates.
                if not previous_ok:row['detail_status']='unavailable'
            row['detail_attempted_at']=now
        elif backoff:
            row['detail_status']=cached.get('detail_status','unavailable')
            row['detail_attempted_at']=cached.get('detail_attempted_at')
        result.append(row)
    return result
