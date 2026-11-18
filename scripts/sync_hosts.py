"""Dated faculty-directory evidence, separate from advertised vacancies."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
from hashlib import sha256
from html import unescape
import json
from pathlib import Path
import re
from urllib.parse import urljoin,urlsplit,urlencode
from urllib.request import urlopen,Request

try:
    from sync_jobs import Client,Document,next_page,USER_AGENT
    from notice_index import terms
    from build_hosts import build,merge_hosts
except ModuleNotFoundError:
    from scripts.sync_jobs import Client,Document,next_page,USER_AGENT
    from scripts.notice_index import terms
    from scripts.build_hosts import build,merge_hosts

ROOT=Path(__file__).resolve().parents[1]
SOURCES=[
 dict(id='tokyo-agriculture',institution='The University of Tokyo',country='日本',department='Graduate School of Agricultural and Life Sciences',url='https://www.a.u-tokyo.ac.jp/english/researchers_e/profile_e/',parser='tokyo',pages=1,scope='学院公开教师名录；院系与实验室信息，不推断个人职称或招聘状态'),
 dict(id='eth-food',institution='ETH Zürich',country='瑞士',department='World Food System Center',url='https://worldfoodsystem.ethz.ch/people/members.html',parser='eth',pages=1,scope='公开成员与研究组；排除 Emeritus 栏目'),
 dict(id='cambridge-plants',institution='University of Cambridge',country='英国',department='Department of Plant Sciences',url='https://www.plantsci.cam.ac.uk/people/academic-staff',parser='cambridge',pages=5,scope='Academic staff 分页；排除荣休人员'),
 dict(id='usp-soil',institution='University of São Paulo',country='巴西',department='Departamento de Ciência do Solo',url='https://lso.esalq.usp.br/pt-br/equipe/docentes',parser='usp',pages=1,scope='教师名录中明确的职称与研究兴趣'),
 dict(id='ubc-forestry',institution='University of British Columbia',country='加拿大',department='Faculty of Forestry & Environmental Stewardship',url='https://www.grad.ubc.ca/prospective-students/faculties/faculty-forestry-environmental-stewardship',parser='ubc',pages=6,scope='Research Supervisors 表及其分页；不把论文作者作为导师'),
 dict(id='ubc-land',institution='University of British Columbia',country='加拿大',department='Faculty of Land and Food Systems',url='https://www.grad.ubc.ca/prospective-students/faculties/faculty-land-food-systems',parser='ubc',pages=6,scope='Research Supervisors 表及其分页'),
 dict(id='ubc-science',institution='University of British Columbia',country='加拿大',department='Faculty of Science',url='https://www.grad.ubc.ca/prospective-students/faculties/faculty-science',parser='ubc',pages=4,scope='Research Supervisors 表，最多100条；物理、数学、生物、地学等方向'),
 dict(id='njau-environment',institution='南京农业大学',country='中国',department='资源与环境科学学院',url='https://re.njau.edu.cn/jsfc2.jsp?urltype=tree.TreeTempUrl&wbtreeid=1325',parser='njau',pages=8,scope='官网六个院系公开查询；仅保留导师标识与教授/研究员职称，排除退休标识'),
 dict(id='bonn-geography',institution='University of Bonn',country='德国',department='Department of Geography',url='https://www.geographie.uni-bonn.de/en/research/research-groups',parser='bonn',pages=1,scope='公开研究组与研究方向；团队条目，不臆造负责人姓名'),
 dict(id='zalf-groups',institution='Leibniz Centre for Agricultural Landscape Research (ZALF)',country='德国',department='Research groups',url='https://www.zalf.de/en/struktur/Pages/default.aspx',parser='zalf',pages=6,scope='四个研究领域及创新中心公开研究组负责人/联系人；优先读取个人 Expertise / Tasks，不把全体员工当导师'),
]

def clean(text,limit=300):
    text=re.sub(r'<[^>]+>',' ',unescape(str(text or '')))
    text=re.sub(r'[\u200b-\u200d\ufeff]','',text)
    text=re.sub(r'\s+',' ',text).strip()
    text=re.sub(r'https?://\S+|\S+@\S+','',text)
    text=re.sub(r'(?:E-?mail|Telefone|Phone|电话|联系方式)\s*[:：].*','',text,flags=re.I)
    return text[:limit].rstrip()

def safe_url(url):
    p=urlsplit(url)
    return bool(p.scheme in {'http','https'} and p.hostname and not p.username and not p.password)

def row(source,name,url,description,now,role='',department='',kind='person',locator=''):
    name=clean(name,120);url=urljoin(source['url'],url)
    if not name or not safe_url(url):raise ValueError('Missing faculty identity or public URL')
    description=clean(description)
    tags=[]
    # Small explicit translations for research fields appearing in these lists.
    for word,tag in [('soil','soil'),('solo','soil'),('土壤','soil'),('ecolog','ecology'),('生态','ecology'),('hydrolog','hydrology'),('水文','hydrology'),('plant','plant'),('植物','plant'),('forestr','forestry'),('forest','forestry'),('genetic','genetics'),('genomic','genomics'),('climate','climate'),('气候','climate'),('remote sensing','remote sensing'),('sensoriamento remoto','remote sensing'),('遥感','remote sensing'),('microbio','microbiology'),('微生物','microbiology')]:
        if word in description.lower():tags.append(tag)
    words,phrases=terms(description)
    key=sha256((source['id']+':'+name.casefold()).encode()).hexdigest()[:20]
    return dict(id=key,name=name,url=url,institution=source['institution'],country=source['country'],
        department=clean(department or source['department'],180),role=clean(role,100),host_kind=kind,
        research_excerpt=description or '个人研究介绍尚未提取，请查看机构原网页。',
        research_basis='机构教师/研究组名录中的研究字段；不代表完整个人研究成果，招聘未核实',
        research_scope='directory_fields',topics=sorted(set(tags)),search_terms=words,search_phrases=phrases,
        evidence_kind='official_faculty_directory',evidence_url=source['url'],evidence_locator=locator or name,
        directory_source_id=source['id'],checked_at=now,vacancy_status='not_checked',related_jobs=[])

def ancestor(node,predicate):
    while node:
        if predicate(node):return node
        node=node.parent
    return None

def parse(doc,source,now):
    rows=[];mode=source['parser']
    if mode=='tokyo':
        for box in doc.all('div','card'):
            link=next((a for a in box.all('a') if re.search(r'/profile_e/\?id=',a.attrs.get('href',''))),None)
            if not link:continue
            headings=[n for n in link.all() if n.tag in {'h3','h4','h5'}]
            name=headings[0].text() if headings else ''
            if not name:name=link.first('p','card-text1').text()
            if not name:
                name=next((n.text() for n in link.all() if 'name' in n.attrs.get('class','').lower()),'')
            if not name:continue
            text=link.text();description=text.removeprefix(name).strip()
            if re.search(r'emerit|retired',text,re.I):continue
            rows.append(row(source,name,link.attrs['href'],description,now,role='Faculty member（学院教师名录）'))
    elif mode=='eth':
        for h in doc.all('h3'):
            match=re.match(r'(Prof\.|Dr\.)\s+([^,]+),\s*(.+)',h.text())
            if not match:continue
            if ancestor(h,lambda n:'emerit' in n.attrs.get('title','').lower()):continue
            box=ancestor(h,lambda n:'textimage' in n.attrs.get('class','').split())
            if not box:continue
            link=next((a for a in box.all('a') if a.text().strip()=='Personal Webpage'),None)
            if not link:continue
            rows.append(row(source,match[2],link.attrs['href'],match[3],now,role=match[1]))
    elif mode=='cambridge':
        for a in doc.all('a'):
            if a.attrs.get('data-testid')!='card-person':continue
            text=a.text()
            if re.search(r'emerit|retired',text,re.I):continue
            name=text.split('•')[0].strip()
            name=re.sub(r'^(?:Professor|Dr|Sir|Dame)\.?\s+','',name)
            rows.append(row(source,name,a.attrs['href'],'; '.join(text.split('•')[1:]),now,role=text.split(name,1)[0].strip()))
    elif mode=='usp':
        for h in doc.all('h4','pessoa-nome'):
            box=ancestor(h,lambda n:'views-view-responsive-grid__item-inner' in n.attrs.get('class','').split())
            link=h.first('a')
            if not box or not link.attrs.get('href'):continue
            text=box.text()
            if not re.search(r'Professor|Professora',text):continue
            role=re.search(r'Professor(?:a)?\s+(?:Associad[oa]|Titular|Doutor[ao])',text)
            research=re.split(r'Áreas? de interesse',text,maxsplit=1,flags=re.I)
            rows.append(row(source,h.text(),link.attrs['href'],research[-1] if len(research)>1 else '',now,role=role[0] if role else 'Docente'))
    elif mode=='ubc':
        for table in doc.all('table'):
            if 'Research Interests' not in table.text()[:150]:continue
            for tr in table.all('tr'):
                cells=list(tr.all('td'))
                if len(cells) not in {2,3}:continue
                name=cells[0].text()
                if ',' in name:
                    last,first=name.split(',',1);name=first.strip()+' '+last.strip()
                if not name:continue
                rows.append(row(source,name,source['url'],cells[-1].text(),now,role='Research Supervisor（官网导师名录）',department=cells[1].text() if len(cells)==3 else source['department']))
    elif mode=='bonn':
        for a in doc.all('a'):
            if not a.text().startswith('RG ') or not a.attrs.get('href'):continue
            box=ancestor(a,lambda n:bool(list(n.all('h3'))) and len(n.text())<1800)
            heading=box.first('h3').text() if box else ''
            rows.append(row(source,a.text(),a.attrs['href'],heading,now,kind='research_group',role='Research group'))
    return rows

def page_next(doc,source,current):
    if source['parser']=='ubc':
        for table in doc.all('table'):
            if 'Research Interests' not in table.text()[:150]:continue
            view=ancestor(table,lambda n:'view-id-gps_researcher_lists' in n.attrs.get('class','').split())
            if view:
                link=next((a for a in view.all('a') if a.attrs.get('rel')=='next'),None)
                return urljoin(current,link.attrs['href']) if link else None
        return None
    return next_page(doc,current,urlsplit(source['url']).hostname) if source['parser']=='cambridge' else None

def njau(client,source,html,now):
    # Configuration and six college IDs are read from the public page itself.
    owner=re.search(r'"siteOwner":(\d+)',html);view=re.search(r'"viewId":(\d+)',html)
    colleges=re.findall(r'selectByCollege\(this,(\d+)\).*?<a>(.*?)</a>',html)
    if not owner or not view or not colleges:raise ValueError('Teacher query configuration not recognized')
    rows=[];requests=0
    for college,department in colleges:
        for page in range(1,source['pages']+1):
            params=dict(collegeid=college,isshowpage='true',pageindex=page,pagesize=21,showlang='zh_CN',siteOwner=owner[1],viewid=view[1],viewmode=10,viewUniqueId='u7',actiontype='advancesearch',profilelen=100)
            url=urljoin(source['url'],'/system/resource/tsites/portal/queryteacher.jsp')+'?'+urlencode(params)
            data=json.loads(client.get(url));requests+=1
            if not isinstance(data.get('teacherData'),list) or not isinstance(data.get('totalpage'),(int,float)):raise ValueError('Unrecognized public faculty response')
            # Discard all unused fields immediately: no birth dates, sex,
            # addresses, telephone numbers or email fields enter our index.
            for item in data['teacherData']:
                if str(item.get('isRetired','0')).lower() in {'1','true'}:continue
                rank=str(item.get('prorank',''))
                if not re.search(r'教授|研究员',rank) or str(item.get('doctorTutor'))!='1':continue
                url=item.get('url','');name=item.get('showName','')
                if not safe_url(url) or not name:continue
                description=clean(item.get('profile',''))
                research=next((part for part in re.split(r'(?<=[。；])',description) if re.match(r'^(?:研究方向|主要从事|主要研究|研究领域)',part.strip())),department+'；个人研究方向尚未提取。')
                rows.append(row(source,name,url,research,now,role=rank+' / 博士生导师',department=department))
            if page>=data['totalpage']:break
        else:raise ValueError('Faculty query page budget reached')
    return rows,requests

def collect(source,now,cache_dir=None):
    state=dict(id=source['id'],institution=source['institution'],country=source['country'],url=source['url'],scope=source['scope'],attempted_at=now,pages_read=0)
    rows=[]
    try:
        client=Client(source);url=source['url'];visited=set()
        if source['parser']=='zalf':
            try:from host_zalf import collect_zalf
            except ModuleNotFoundError:from scripts.host_zalf import collect_zalf
            return collect_zalf(client,source,now,row,clean,Document,cache_dir)
        for page in range(source['pages']):
            if not url or url in visited:break
            if urlsplit(url).hostname!=urlsplit(source['url']).hostname:raise ValueError('Unexpected directory pagination host')
            visited.add(url);html=client.get(url);doc=Document(html).root;state['pages_read']+=1
            if cache_dir:
                cache_dir.mkdir(parents=True,exist_ok=True)
                (cache_dir/(source['id']+'-'+str(page)+'.html')).write_text(html,encoding='utf8')
            if source['parser']=='njau':
                found,count=njau(client,source,html,now);rows.extend(found);state['pages_read']+=count;url=None;break
            found=parse(doc,source,now)
            if not found:raise ValueError('No recognized faculty records; prior evidence retained')
            for item in found:item['evidence_url']=url
            rows.extend(found);url=page_next(doc,source,url)
        limited=bool(url and url not in visited)
        state.update(status='partial' if limited else 'ok',coverage='page_limit' if limited else 'end_of_directory',observed_at=now,count=len(rows))
    except Exception as error:
        state.update(status='partial' if rows else 'unavailable',error=str(error)[:180],count=len(rows))
        if rows:state['observed_at']=now
    return rows,state

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--use-published-cache',action='store_true');parser.add_argument('--force',action='store_true');parser.add_argument('--cache-dir',type=Path);parser.add_argument('--source',choices=[s['id'] for s in SOURCES]);args=parser.parse_args()
    path=ROOT/'web/data/hosts.json';previous=json.loads(path.read_text(encoding='utf8')) if path.exists() else {}
    if args.use_published_cache:
        try:
            with urlopen(Request('https://tylerzhang130666.github.io/global-postdoc-finder/data/hosts.json',headers={'User-Agent':USER_AGENT}),timeout=20) as response:published=json.loads(response.read(20_000_000))
            if published.get('schema_version')=='postdoc-hosts/1':
                states={s['id']:s for s in previous.get('directory_sources',[])}
                for state in published.get('directory_sources',[]):
                    sid=state['id']
                    if state.get('attempted_at','')>states.get(sid,{}).get('attempted_at',''):
                        previous['directory_hosts']=[h for h in previous.get('directory_hosts',previous.get('hosts',[])) if h.get('directory_source_id') and h.get('directory_source_id')!=sid]+[h for h in published.get('directory_hosts',published.get('hosts',[])) if h.get('directory_source_id')==sid]
                        states[sid]=state
                previous['directory_sources']=list(states.values())
        except Exception:print('Published host cache unavailable; using repository evidence')
    now=datetime.now(timezone.utc).isoformat(timespec='seconds');old_states={s['id']:s for s in previous.get('directory_sources',[])}
    old_rows=previous.get('directory_hosts',[h for h in previous.get('hosts',[]) if h.get('directory_source_id')])
    cutoff=(datetime.now(timezone.utc)-timedelta(days=7)).isoformat();retry=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
    def run(source):
        old=old_states.get(source['id'],{});cached=[h for h in old_rows if h.get('directory_source_id')==source['id']]
        if args.source and args.source!=source['id']:return cached,old
        if not args.force and (old.get('observed_at','')>=cutoff and (old.get('status')=='ok' or old.get('coverage')=='page_limit') or old.get('attempted_at','')>=retry and old.get('status')!='ok'):return cached,old
        rows,state=collect(source,now,args.cache_dir)
        if state['status']!='ok':
            keys={h['id'] for h in rows}
            rows.extend(dict(h,stale=True) for h in cached if h['id'] not in keys)
        return rows,state
    with ThreadPoolExecutor(max_workers=4) as pool:batches=list(pool.map(run,SOURCES))
    jobs=json.loads((ROOT/'web/data/jobs.json').read_text(encoding='utf8'))
    seeds=json.loads((ROOT/'references/host-seeds.json').read_text(encoding='utf8'))
    base=build(jobs['jobs'],seeds,now)
    base['directory_hosts']=[h for rows,_ in batches for h in rows]
    base['hosts']=merge_hosts(base['hosts'],base['directory_hosts']);base['directory_sources']=[state for _,state in batches if state]
    base['scope']='招聘公告、机构教师/导师名录与研究组；招聘状态分别标注，未覆盖全球所有机构。'
    path.write_text(json.dumps(base,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for state in base['directory_sources']:print(state['id'],state['status'],state.get('count',0),'records',state.get('pages_read',0),'pages',state.get('error',''),flush=True)
    print(len(base['hosts']),'hosts',flush=True)

if __name__=='__main__':main()
