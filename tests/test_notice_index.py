import importlib.util
from pathlib import Path
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
def load(name):
    spec=importlib.util.spec_from_file_location(name,SCRIPTS/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
M=load('notice_index')
S=load('sync_jobs')
NOW='2026-11-18T12:00:00+00:00'
RECORD={'id':'example','title':'Postdoctoral Researcher in Microbial Ecology','source_id':'leibniz','url':'https://example.org/job'}
BODY='Our project studies microbial ecology and the collection of soil, plant and rhizosphere samples. '+('Research experience in laboratory and field experiments is required. '*3)

class NoticeIndexTests(unittest.TestCase):
    def html(self,title=None):
        return '<nav>soil physics</nav><div class="tx_jobfair"><h1>'+str(title or RECORD['title'])+'</h1><p>'+BODY+'</p><p>Please send your complete application by November 24, 2026.</p></div><footer>unrelated field</footer>'

    def test_real_notice_body_terms_and_explicit_deadline_are_indexed(self):
        class Client:
            def get(inner,url):return self.html()
        result=M.enrich_record(RECORD,Client(),S.Document,S.parse_date,NOW)
        self.assertIn('soil',result['search_terms'])
        self.assertNotIn('physics',result['search_terms'])
        self.assertNotIn('unrelated',result['search_terms'])
        self.assertEqual(result['deadline_at'],'2026-11-24')
        self.assertEqual(result['detail_locator'],'tx_jobfair')

    def test_mismatched_notice_title_is_not_used_for_search(self):
        doc=S.Document(self.html('Different vacancy')).root
        with self.assertRaises(ValueError):M.notice_body(doc,RECORD,S.Document)

    def test_publication_start_and_degree_dates_do_not_become_deadlines(self):
        body='Posted November 1, 2026. The position starts from February 1, 2027. A PhD is required by January 1, 2027.'
        self.assertEqual(M.deadline_from_text(body,S.parse_date),'')

    def test_multiple_conflicting_deadlines_stay_unknown(self):
        body='Application deadline: November 24, 2026. Closing date: November 30, 2026.'
        self.assertEqual(M.deadline_from_text(body,S.parse_date),'')

    def test_cache_does_not_refetch_or_advance_successful_evidence_dates(self):
        old={**RECORD,'search_terms':['soil'],'detail_status':'indexed','detail_index_version':M.INDEX_VERSION,'detail_checked_at':'2026-11-18T10:00:00+00:00'}
        class Client:
            def __init__(self,source):raise AssertionError('Fresh evidence must be reused')
        result=M.enrich_source([RECORD],{'detail_budget':25},{'jobs':[old]},Client,S.Document,S.parse_date,NOW)[0]
        self.assertEqual(result['detail_checked_at'],old['detail_checked_at'])
        self.assertEqual(result['search_terms'],['soil'])

    def test_failed_refresh_keeps_prior_terms_and_prior_date(self):
        old={**RECORD,'search_terms':['soil'],'detail_status':'indexed','detail_index_version':M.INDEX_VERSION,'detail_checked_at':'2026-11-01T10:00:00+00:00'}
        class Client:
            def __init__(self,source):pass
            def get(self,url):raise OSError('Unavailable')
        result=M.enrich_source([RECORD],{'detail_budget':25},{'jobs':[old]},Client,S.Document,S.parse_date,NOW)[0]
        self.assertEqual(result['detail_checked_at'],old['detail_checked_at'])
        self.assertEqual(result['search_terms'],['soil'])

    def test_changed_title_never_inherits_old_soil_terms(self):
        old={**RECORD,'search_terms':['soil'],'detail_status':'indexed','detail_index_version':M.INDEX_VERSION,'detail_checked_at':NOW}
        result=M.enrich_source([{**RECORD,'title':'Unrelated new vacancy'}],{'detail_budget':0},{'jobs':[old]},None,S.Document,S.parse_date,NOW)[0]
        self.assertNotIn('search_terms',result)

    def test_contact_strings_are_not_stored_as_terms(self):
        words,_=M.terms('soil contact '+'example'+'@'+'example.org https://example.org/private/query')
        self.assertIn('soil',words)
        self.assertNotIn('example',words)

