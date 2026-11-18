import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

SPEC=importlib.util.spec_from_file_location('sync_jobs',Path(__file__).resolve().parents[1]/'scripts/sync_jobs.py')
M=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)

class ExpandedSources(unittest.TestCase):
    def source(self,name):
        return next(s for s in M.SOURCES if s['id']==name)

    def test_jobrxiv_drops_badges_and_keeps_real_country(self):
        html='<li class="job_listing"><a href="https://jobrxiv.org/job/example/"><h4>Postdoctoral Researcher <span>Full-time</span></h4><span class="ws-meta-company-name">Example University</span><span class="ws-meta-job-location">Germany</span><time datetime="2026-11-18"></time><div class="listing-desc">Soil science research.</div></a></li>'
        rows,count=M.jobrxiv(M.Document(html).root,self.source('jobrxiv'))
        self.assertEqual(count,1);self.assertEqual(rows[0]['title'],'Postdoctoral Researcher');self.assertEqual(rows[0]['country'],'德国')

    def test_jobrxiv_date_order_stops_at_recent_window(self):
        calls=[]
        class Client:
            def __init__(self,source):pass
            def search_post(self,url,fields):
                calls.append(fields)
                date='2026-11-01' if fields['page']==1 else '2025-01-01'
                html='<li class="job_listing"><a href="https://jobrxiv.org/job/example-'+str(fields['page'])+'/"><h4>Postdoctoral Researcher</h4><time datetime="'+date+'"></time></a></li>'
                import json
                return json.dumps({'html':html,'found_jobs':True,'max_num_pages':31})
        with patch.object(M,'Client',Client):rows,state=M.collect(self.source('jobrxiv'),'2026-11-18T00:00:00+00:00')
        self.assertEqual(len(rows),1);self.assertEqual(state['coverage'],'recent_window');self.assertEqual(len(calls),2);self.assertEqual(calls[0]['orderby'],'date')

    def test_robots_not_found_allows_access_but_server_error_does_not(self):
        with patch.object(M.Client,'raw',side_effect=HTTPError('https://example.org/robots.txt',404,'missing',None,None)):
            client=M.Client({'url':'https://example.org/jobs/'})
            self.assertTrue(client.robot.can_fetch('PostdocFinder','https://example.org/jobs/'))
        with patch.object(M.Client,'raw',side_effect=HTTPError('https://example.org/robots.txt',503,'unavailable',None,None)):
            with self.assertRaises(HTTPError):
                M.Client({'url':'https://example.org/jobs/'})

    def test_eth_preserves_singapore_workplace(self):
        html='<li class="job-ad__item__wrapper"><a class="job-ad__item__link" href="/job/view/example"><h3>Postdoc in climate modelling</h3><div class="job-ad__item__details">100%, Singapore, fixed-term</div><div class="job-ad__item__company">DATE | Example institute</div></a></li>'.replace('DATE','.'.join(('18','11','2026')))
        rows,_=M.eth(M.Document(html).root,self.source('eth'))
        self.assertEqual(rows[0]['country'],'新加坡')
        self.assertEqual(rows[0]['posted_at'],'2026-11-18')

    def test_ubc_does_not_mislabel_us_workplace(self):
        html='<table><tr><td><a href="/positions/123">Postdoctoral Researcher (UC Santa Barbara)</a></td><td><time datetime="2027-01-01T12:00:00Z"></time></td></tr></table>'
        rows,_=M.table_jobs(M.Document(html).root,self.source('ubc'))
        self.assertEqual(rows[0]['country'],'美国')

    def test_copenhagen_extracts_full_date_and_excludes_phd(self):
        html='<table><tr><td><a href="?show=123">Postdoc in biology</a></td><td>Science</td><td>Biology</td><td>DATE</td></tr><tr><td><a href="?show=456">PhD student</a></td></tr></table>'.replace('DATE','-'.join(('19','11','2026')))
        rows,_=M.table_jobs(M.Document(html).root,self.source('copenhagen'))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['deadline_at'],'2026-11-19')

    def test_jrec_employer_deadline_and_visible_paging_control(self):
        html='<div class="card_header"><span>Date of update : 2026/11/18</span><span>End date of accepting applications : 2027/01/01</span><h5 class="card_title_min"><a href="/seek/SeekJorDetail?id=D126TEST">Postdoctoral Researcher</a></h5><div class="my-1">RIKEN</div></div><a href="#" data-pageno="2">2</a>'
        doc=M.Document(html).root
        rows,_=M.jrec(doc,self.source('jrec'))
        self.assertEqual(rows[0]['institution'],'RIKEN')
        self.assertEqual(rows[0]['deadline_at'],'2027-01-01')
        target=M.next_page(doc,self.source('jrec')['url'],'jrecin.jst.go.jp')
        self.assertIn('page=2',target)
        self.assertIn('jobkind=00015',target)

    def test_leibniz_records_listed_institute(self):
        html='<div><h4><a href="/en/careers/jobs/detail/job/show/Job/example">Postdoc in soil science</a></h4><p>Example Leibniz Institute</p></div>'
        rows,_=M.leibniz(M.Document(html).root,self.source('leibniz'))
        self.assertEqual(rows[0]['institution'],'Example Leibniz Institute')

    def test_jobsuk_leaves_unknown_overseas_location_unknown(self):
        html='<div class="j-doorway__result"><div class="j-doorway__result-info"><div><a href="/job/ABC/example">Postdoctoral Researcher</a></div><div class="j-doorway__employer">Overseas Institute</div><div>Placed on: 18/11/2026</div></div></div>'
        rows,_=M.jobsuk(M.Document(html).root,self.source('jobsuk'))
        self.assertEqual(rows[0]['country'],'未注明')

    def test_date_parser_does_not_invent_year(self):
        self.assertEqual(M.parse_date('Closes 14 Dec'),'')
        self.assertEqual(M.parse_date('-'.join(('31','02','2026'))),'')

if __name__=='__main__':
    unittest.main()
