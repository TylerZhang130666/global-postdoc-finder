"""Synthetic fixtures: source boundaries and evidence retention, no live requests."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import sync_hosts as H
from scripts.build_hosts import build,merge_hosts,write

NOW='2026-11-18T15:00:00+00:00'
def source(mode):return next(s for s in H.SOURCES if s['parser']==mode)

class HostDirectories(unittest.TestCase):
    def test_tokyo_card_preserves_person_and_lab(self):
        html='<div class="card"><a href="/english/researchers_e/profile_e/?id=prof-demo"><p class="card-text1">DEMO Scientist</p><p>Soil Laboratory</p></a></div>'
        row=H.parse(H.Document(html).root,source('tokyo'),NOW)[0]
        self.assertEqual(row['name'],'DEMO Scientist')
        self.assertIn('soil',row['topics'])
        self.assertEqual(row['vacancy_status'],'not_checked')
        self.assertEqual(row['research_scope'],'directory_fields')

    def test_ubc_only_research_table_and_its_own_pager(self):
        html='''<div><a rel="next" href="?publications=2">Next paper</a>
        <table><tr><td><a href="/researcher/student">Student Author</a></td></tr></table></div>
        <div class="view-id-gps_researcher_lists"><table><tr><th>Name</th><th>Research Interests</th></tr>
        <tr><td>Example, Sally</td><td>soil carbon</td></tr>
        <tr><td>Example, John</td><td>forest ecology</td></tr></table><a rel="next" href="?page=0%2C1%2C0">Next</a></div>'''
        s=source('ubc');doc=H.Document(html).root;rows=H.parse(doc,s,NOW)
        self.assertEqual([h['name'] for h in rows],['Sally Example','John Example'])
        self.assertIn('page=0%2C1%2C0',H.page_next(doc,s,s['url']))
        self.assertEqual(len(merge_hosts([],rows)),2)

    def test_emeritus_is_excluded_and_teams_stay_teams(self):
        html='<div title="Emeritus"><div class="textimage"><h3>Prof. Retired Scientist, Soil</h3><a href="https://example.org/retired">Personal Webpage</a></div></div><div class="textimage"><h3>Prof. Active Scientist, Soil</h3><a href="https://example.org/active">Personal Webpage</a></div>'
        self.assertEqual([r['name'] for r in H.parse(H.Document(html).root,source('eth'),NOW)],['Active Scientist'])
        team=H.parse(H.Document('<section><h3>Remote sensing</h3><a href="/group">RG Example</a></section>').root,source('bonn'),NOW)[0]
        self.assertEqual(team['host_kind'],'research_group')

    def test_njau_uses_role_and_active_supervisor_flags_only(self):
        s=source('njau');html='"siteOwner":123 "viewId":456 selectByCollege(this,12)<a>土壤学系</a>'
        base=dict(showName='Synthetic Scientist',url='https://example.org/person',prorank='教授',doctorTutor='1',profile='个人简介，私人字段不应保留。')
        items=[base,{**base,'showName':'Retired','isRetired':'1'},{**base,'showName':'Student','prorank':'研究生'},{**base,'showName':'Other','doctorTutor':'0'}]
        class Client:
            def get(self,url):return json.dumps(dict(teacherData=items,totalpage=1))
        rows,_=H.njau(Client(),s,html,NOW)
        self.assertEqual(len(rows),1)
        self.assertNotIn('私人字段',rows[0]['research_excerpt'])
        self.assertNotIn('profile',rows[0])

    def test_failure_does_not_invent_observation_date(self):
        class Client:
            def __init__(self,s):pass
            def get(self,url):raise ValueError('source unavailable')
        with patch.object(H,'Client',Client):rows,state=H.collect(source('tokyo'),NOW)
        self.assertFalse(rows)
        self.assertEqual(state['status'],'unavailable')
        self.assertNotIn('observed_at',state)

    def test_hourly_job_rebuild_retains_raw_directory_evidence(self):
        s=source('tokyo');entry=H.row(s,'Demo Scientist','https://example.org/people/demo','Soil',NOW)
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'hosts.json';p.write_text(json.dumps(dict(directory_hosts=[entry],directory_sources=[dict(id=s['id'])])),encoding='utf8')
            first=write([],NOW,p);second=write([],NOW,p)
            self.assertEqual(first['directory_hosts'],second['directory_hosts'])
            self.assertIn(entry['id'],[h['id'] for h in second['hosts']])
        self.assertEqual(merge_hosts([entry],[entry])[0]['checked_at'],NOW)

if __name__=='__main__':unittest.main()
