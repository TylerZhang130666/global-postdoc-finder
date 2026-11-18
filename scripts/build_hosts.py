"""Keep potential hosts separate from vacancies; retain dated official evidence."""
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata

ROOT=Path(__file__).resolve().parents[1]

def identity(value):
    return ''.join(c for c in unicodedata.normalize('NFKC',value).casefold() if c.isalnum())

def merge_hosts(primary,additional):
    """Merge same person at same institution; directory URLs may name many people."""
    result=list(primary)
    def keys(h):
        person=identity(h['name'])+'@'+identity(h['institution'])
        # Never merge two people merely because they share a directory URL.
        return person
    by_key={keys(h):h for h in result}
    by_url={h['url']:h for h in result if h.get('evidence_kind') not in {'official_faculty_directory'}}
    for incoming in additional:
        target=by_key.get(keys(incoming))
        if not target and incoming['url'] in by_url:
            candidate=by_url[incoming['url']]
            # A verified personal profile may use reversed surname/given-name
            # order in another official directory. Shared listing URLs cannot.
            personal=bool(re.search(r'/profile|/people/|/staff/|/researcher/',incoming['url'])) and '?' not in incoming['url'].split('/profile_e/')[0]
            if personal:target=candidate
        if not target:
            target=dict(incoming);result.append(target);by_key[keys(target)]=target
            continue
        if not target.get('department') and incoming.get('department'):target['department']=incoming['department']
        if incoming.get('role'):target['role']=incoming['role']
        target.setdefault('directory_evidence',[])
        evidence={k:incoming[k] for k in ('directory_source_id','evidence_url','evidence_locator','checked_at') if k in incoming}
        if evidence and evidence not in target['directory_evidence']:target['directory_evidence'].append(evidence)
        if target.get('evidence_kind')=='faculty_in_advert':
            target['profile_url']=incoming['url']
        # Preserve the job excerpt and its evidence date; do not silently turn
        # a directory lookup into a fresh vacancy check.
    return sorted(result,key=lambda h:(h['country'],h['institution'],h['name']))

def build(jobs,curated,now):
    hosts={}
    for record in jobs:
        if record.get('source_id')!='stanford' or record.get('detail_status')!='indexed':continue
        parts=record['title'].split('·')
        if len(parts)<3:continue
        name=parts[-1].strip()
        if not name or name.lower() in {'tba','tbd','various','multiple faculty'}:continue
        key=sha256(('stanford:'+name.casefold()).encode()).hexdigest()[:20]
        info=record.get('notice_details',{})
        host=hosts.setdefault(key,dict(id=key,name=name,institution=record['institution'],country=record['country'],
            department=record.get('department',''),url=record['url'],evidence_url=record['url'],
            evidence_kind='faculty_in_advert',research_excerpt=info.get('excerpt') or record.get('summary',''),
            research_basis='关联岗位公告中的研究内容，不代表导师全部研究方向',
            search_terms=[],related_jobs=[],checked_at=record.get('detail_checked_at',''),vacancy_status='advertised_lead'))
        host['search_terms']=sorted(set(host['search_terms'])|set(record.get('search_terms',[])))
        host['related_jobs'].append(dict(id=record['id'],title=record['title'],url=record['url'],deadline_at=record.get('deadline_at',''),last_seen=record.get('last_seen',''),stale=record.get('stale',False)))
        host['checked_at']=max(host['checked_at'],record.get('detail_checked_at',''))
    for entry in curated:
        if not all(entry.get(k) for k in ('name','institution','country','url','research_excerpt','checked_at')):raise ValueError('Incomplete curated host evidence')
        key=sha256(entry['url'].encode()).hexdigest()[:20]
        hosts[key]=dict(entry,id=key,evidence_url=entry['url'],evidence_kind='official_research_page',
                        vacancy_status='not_checked',related_jobs=[],research_basis='机构官网研究介绍；招聘状态未核实')
    return dict(schema_version='postdoc-hosts/1',generated_at=now,
                scope='来自已收录招聘公告中的明确导师，以及人工核对的机构研究页面；不是完整导师名录。',
                hosts=sorted(hosts.values(),key=lambda h:(h['country'],h['name'])))

def write(jobs,now,out=None):
    curated=json.loads((ROOT/'references/host-seeds.json').read_text(encoding='utf8'))
    result=build(jobs,curated,now)
    path=out or ROOT/'web/data/hosts.json'
    if path.exists():
        old=json.loads(path.read_text(encoding='utf8'))
        result['directory_hosts']=old.get('directory_hosts',[h for h in old.get('hosts',[]) if h.get('directory_source_id')])
        result['hosts']=merge_hosts(result['hosts'],result['directory_hosts'])
        result['directory_sources']=old.get('directory_sources',[])
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return result

if __name__=='__main__':
    data=json.loads((ROOT/'web/data/jobs.json').read_text(encoding='utf8'))
    result=write(data['jobs'],data['generated_at']);print(len(result['hosts']),'hosts')
