"""ZALF public working-group contacts, not the general staff directory."""
import re
from urllib.parse import urljoin,urlsplit

def content(doc):
    return next((n for n in doc.all('div') if n.attrs.get('id','').endswith('PageContent__ControlWrapper_RichHtmlField')),None)

def people(doc,source,now,row,clean):
    body=content(doc)
    if body is None:raise ValueError('ZALF working-group content not recognized')
    found=[];heading='';description=[]
    for child in body.children:
        if isinstance(child,str):continue
        text=clean(child.text(),2000)
        if child.tag=='h3':heading=text;description=[];continue
        if not heading or re.search(r'thematic area|service working|coordination office',heading,re.I):continue
        links=list(child.all('a'))
        for a in links:
            href=urljoin(source['url'],a.attrs.get('href',''))
            if urlsplit(href).hostname!='www.zalf.de' or not re.fullmatch(r'/en/ueber_uns/mitarbeiter/Pages/(?!default)[^/]+\.aspx',urlsplit(href).path):continue
            # A paper author or a topic-specific staff link is not a group lead.
            # Require the page's explicit Contact/Head/Leadership wording.
            label=clean(a.parent.text(),350)
            if not re.search(r'(?:contact|kontakt)\s*:|head of (?:the )?working group|leadership\s*:',label,re.I):continue
            original=clean(a.text(),150)
            name=re.sub(r'^(?:(?:interim leadership|contact)\s*:\s*)?(?:(?:adjunct|apl\.|Prof\.|Dr\.?|habil\.|PD|PD\.)\s+)*','',original,flags=re.I).strip()
            if not name:continue
            item=row(source,name,href,'; '.join([heading,*description]),now,role='研究组负责人（官网）' if re.search('head|leadership',label,re.I) else '研究组联系人（官网）',department=heading)
            item['research_basis']='官网研究组介绍；方向属于团队，未据此推断个人论文、博后经费或招生资格'
            item['research_scope']='group_description'
            item['aliases']=[original,name.replace('ä','ae').replace('ö','oe').replace('ü','ue').replace('ß','ss')]
            found.append(item)
        if child.tag in {'p','ul'} and text and not links and len(description)<3:description.append(text)
    if not found:raise ValueError('No explicit working-group contacts; prior records retained')
    return found

def profile(doc,clean):
    body=content(doc)
    if body is None:raise ValueError('Personal research content not recognized')
    fields=[]
    # Only explicitly named scientific fields, never CV, contact block or works.
    for heading in body.all():
        if heading.tag not in {'h3','h4'} or clean(heading.text()).lower() not in {'expertise','research topics','tasks'}:continue
        siblings=heading.parent.children
        for sibling in siblings[siblings.index(heading)+1:]:
            if isinstance(sibling,str):continue
            if sibling.tag in {'h2','h3','h4'}:break
            if sibling.tag not in {'ul','ol','div'}:break
            fields.extend(clean(n.text(),250) for n in sibling.all('li'))
    if not fields:raise ValueError('No explicit Expertise or Tasks fields')
    # Service appointments with year ranges add no scientific matching value.
    return list(dict.fromkeys(f for f in fields if not re.search(r'\b(?:19|20)\d{2}\b',f)))

def collect_zalf(client,source,now,row,clean,Document,cache_dir=None):
    state=dict(id=source['id'],institution=source['institution'],country=source['country'],url=source['url'],scope=source['scope'],attempted_at=now,pages_read=0)
    rows=[];errors=[]
    def read(url,key):
        html=client.get(url);state['pages_read']+=1
        if cache_dir:
            cache_dir.mkdir(parents=True,exist_ok=True);(cache_dir/('zalf-'+key+'.html')).write_text(html,encoding='utf8')
        return Document(html).root
    try:
        root=read(source['url'],'structure')
        urls=[]
        for a in root.all('a'):
            url=urljoin(source['url'],a.attrs.get('href',''));p=urlsplit(url)
            if p.hostname=='www.zalf.de' and re.fullmatch(r'/en/struktur/(?:pb[1-4]|iat)/Pages/Arbeitsgruppen\.aspx',p.path):
                canonical=p._replace(query='',fragment='').geturl()
                if canonical not in urls:urls.append(canonical)
        if len(urls)!=5:raise ValueError('Expected four research areas and IAT directory links')
        for i,url in enumerate(urls):
            try:
                batch=people(read(url,'groups-'+str(i)),source,now,row,clean)
                for item in batch:item['evidence_url']=url
                rows.extend(batch)
            except Exception as error:errors.append(str(error)[:100])
        # Group and personal pages may spell one name differently. Personal URL
        # is authoritative within this institution, while group pages are kept.
        unique={}
        for item in rows:
            if item['url'] in unique:
                old=unique[item['url']];old.setdefault('other_groups',[]).append(item['department']);continue
            unique[item['url']]=item
        rows=list(unique.values());verified=0
        for i,item in enumerate(rows):
            try:
                doc=read(item['url'],'person-'+str(i));fields=profile(doc,clean)
                enriched=row(source,item['name'],item['url'],'; '.join(fields),now,role=item['role'],department=item['department'])
                item.update({k:enriched[k] for k in ['research_excerpt','topics','search_terms','search_phrases']})
                item['research_fields']=fields[:20]
                item.update(research_scope='personal_research_fields',research_basis='个人官网 Research Topics / Expertise / Tasks 字段；未据此判断当前空缺或资助',evidence_kind='official_research_page',evidence_url=item['url'],group_evidence_url=item['evidence_url'])
                personal_name=clean(doc.first('h3').text(),120)
                if re.fullmatch(r'[\wÀ-ž .-]{4,120}',personal_name) and ' ' in personal_name:item['aliases'].append(personal_name)
                item['aliases']=list(dict.fromkeys(item['aliases']))
                if any(re.search(r'(?:head|lead) of .*working group',f,re.I) for f in fields):item['role']='研究组负责人（个人官网）'
                verified+=1
            except Exception:item['profile_status']='not_read';item['profile_attempted_at']=now
        state.update(count=len(rows),profiles_read=verified,status='partial' if errors else 'ok',coverage='partial_directories' if errors else 'listed_group_contacts',observed_at=now)
        if errors:state['error']='; '.join(errors)[:180]
    except Exception as error:state.update(count=len(rows),status='partial' if rows else 'unavailable',error=str(error)[:180])
    return rows,state
