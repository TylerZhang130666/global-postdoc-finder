"""Synthetic fixtures: source boundaries and evidence retention, no live requests."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import sync_hosts as H
from scripts.build_hosts import build,merge_hosts,write
from scripts.host_zalf import people as zalf_people,profile as zalf_profile,collect_zalf

NOW='2026-11-18T15:00:00+00:00'
def source(mode):return next(s for s in H.SOURCES if s['parser']==mode)

class HostDirectories(unittest.TestCase):
    def test_zalf_explicit_group_contacts_exclude_staff_and_admin(self):
        html='''<div id="PageContent__ControlWrapper_RichHtmlField"><h3>Soil Erosion</h3>
        <p>Water and wind erosion.</p><p><strong>Contact: <a href="/en/ueber_uns/mitarbeiter/Pages/maerker_m.aspx">Prof. Dr. Michael Märker</a></strong></p>
        <p><a href="/en/ueber_uns/mitarbeiter/Pages/student.aspx">Student Author</a> - research assistant</p>
        <h3>Remote Sensing</h3><p><strong>Kontakt: <a href="/en/ueber_uns/mitarbeiter/Pages/example.aspx">Dr Scientist Example</a></strong></p>
        <h3>IAT Coordination Office</h3><p>Contact: <a href="/en/ueber_uns/mitarbeiter/Pages/admin.aspx">Administrator</a></p></div>'''
        s=source('zalf');rows=zalf_people(H.Document(html).root,s,NOW,H.row,H.clean)
        self.assertEqual([r['name'] for r in rows],['Michael Märker','Scientist Example'])
        self.assertIn('Michael Maerker',rows[0]['aliases'])
        self.assertEqual(rows[0]['research_scope'],'group_description')
        self.assertEqual(rows[0]['vacancy_status'],'not_checked')

    def test_zalf_nested_research_fields_exclude_cv_contacts_and_ids(self):
        html='''<div id="PageContent__ControlWrapper_RichHtmlField"><div><h3>Michael Maerker</h3><p>Contact block</p></div>
        <div><h4>Research Topics</h4><div><ul><li>Soil erosion by water</li><li>Digital Soil Mapping</li></ul></div>
        <h4>Tasks</h4><div><ul><li>Lead of working group</li><li>2024–2028 Committee service</li></ul></div><p>Curriculum Vitae</p><a>private identifier</a></div></div>'''
        self.assertEqual(zalf_profile(H.Document(html).root,H.clean),['Soil erosion by water','Digital Soil Mapping','Lead of working group'])

    def test_zalf_partial_directory_failure_retains_successful_groups(self):
        directory='<div id="PageContent__ControlWrapper_RichHtmlField"><h3>Soil Erosion</h3><p><strong>Contact: <a href="/en/ueber_uns/mitarbeiter/Pages/example.aspx">Dr. Example Scientist</a></strong></p></div>'
        links=''.join('<a href="/en/struktur/'+key+'/Pages/Arbeitsgruppen.aspx#x">WG</a>' for key in ['pb1','pb2','pb3','pb4','iat'])
        class Client:
            def get(self,url):
                if url==source('zalf')['url']:return links
                if '/pb1/' in url:return directory
                raise ValueError('unavailable')
        rows,state=collect_zalf(Client(),source('zalf'),NOW,H.row,H.clean,H.Document)
        self.assertEqual(len(rows),1)
        self.assertEqual(state['status'],'partial')
        self.assertEqual(rows[0]['research_scope'],'group_description')
        self.assertEqual(rows[0]['checked_at'],NOW)
        self.assertNotIn('group_evidence_url',rows[0])

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
