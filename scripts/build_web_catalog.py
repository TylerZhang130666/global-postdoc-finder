"""Publish only the public source directory, never candidate/trial data."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGIONS = {
    'euraxess_jobs': ['europe', 'germany', 'netherlands', 'uk'],
    'euraxess_hosting': ['europe', 'germany', 'netherlands', 'uk'],
    'academictransfer': ['europe', 'netherlands'],
    'jobs_ac_uk': ['europe', 'uk'], 'jrec_in': ['japan'],
    'msca_pf': ['europe', 'germany', 'netherlands', 'uk'],
    'rgc_jrfs': ['china-hk'], 'hku_careers': ['china-hk'],
    'csiro_careers': ['australia'], 'cordis': ['europe', 'germany', 'netherlands', 'uk'],
    'dfg_gepris': ['europe', 'germany'], 'nih_reporter': ['us'],
    'ukri_funding_finder': ['europe', 'uk'], 'jsps_international_postdoc': ['japan'],
    'fapesp_opportunities': ['brazil'], 'humboldt_research_fellowship': ['europe', 'germany'],
    'cgiar_careers': ['global'], 'nih_oite_jobs': ['us'],
}
NOTES = {
    'job_portal': '查找招聘线索，再回到雇主公告核实岗位与条件。',
    'employer_careers': '机构自己的招聘入口；以具体公告的地点与条件为准。',
    'fellowship_programme': '先核对当轮资助条件、接收机构与申请时点。',
    'hosting_portal': '寻找愿意接收或联合申请的团队，不保证已有职位或经费。',
    'project_database': '从在研项目寻找研究团队，不代表团队正在招聘。',
    'funding_portal': '区分公开岗位、个人基金与项目资助，核对申请主体。',
}

def build():
    catalog = json.loads((ROOT / 'references/source-catalog.json').read_text(encoding='utf-8'))
    sources = catalog['sources']
    for source in sources:
        source['web_regions'] = REGIONS[source['source_id']]
        source['web_note'] = NOTES[source['source_role']]
    return {'checked_on': catalog['checked_on'], 'sources': sources}

if __name__ == '__main__':
    out = ROOT / 'web/data/sources.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Published {len(build()["sources"])} public source entries')
