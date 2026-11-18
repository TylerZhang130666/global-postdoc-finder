import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('sync_jobs', Path(__file__).resolve().parents[1]/'scripts/sync_jobs.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)

class SourceTests(unittest.TestCase):
    def source(self, name):
        return next(s for s in M.SOURCES if s['id']==name)

    def test_hku_excludes_assistants_and_retains_precise_deadline(self):
        html = '<table><tr><td>Ref</td><td><a class="job-link" href="/en/job/123/postdoc">Post-doctoral Fellow</a></td><td>Biology</td><td><time datetime="2027-01-01T15:55:00Z">Jan</time></td></tr><tr><td><a class="job-link" href="/en/job/124/assistant">Research Assistant</a></td></tr></table>'
        rows, recognized = M.hku(M.Document(html).root, self.source('hku'))
        self.assertEqual(recognized, 2)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['department'], 'Biology')
        self.assertEqual(rows[0]['deadline_at'], '2027-01-01T15:55:00Z')

    def test_stanford_department_and_faculty_not_details_as_title(self):
        html = '<table><caption>Department: Biology</caption><tr><td><p><strong>Position with Example PI</strong></p><strong>Posted on:</strong> November 01, 2026<p>Research on soil carbon and ecological processes in forest systems.</p><a href="/prospective/opportunities/example">Details</a></td></tr></table>'
        rows, _ = M.stanford(M.Document(html).root, self.source('stanford'))
        self.assertEqual(rows[0]['title'], 'Postdoc · Biology · Example PI')
        self.assertEqual(rows[0]['posted_at'], '2026-11-01')
        self.assertEqual(rows[0]['department'], 'Biology')
        self.assertIn('soil carbon', rows[0]['summary'])

    def test_academictransfer_uses_visible_metadata(self):
        html = '<article><a href="/en/jobs/123/postdoc/"></a><h3>Postdoc in remote sensing</h3><p>Satellite research.</p><span class="md:text-right">Example University</span><time datetime="2027-01-01T20:00:00Z"></time><time datetime="2026-11-01T10:00:00Z"></time></article>'
        rows,_ = M.academictransfer(M.Document(html).root,self.source('academictransfer'))
        self.assertEqual(rows[0]['institution'],'Example University')
        self.assertEqual(rows[0]['deadline_at'],'2027-01-01T20:00:00Z')

    def test_yale_keeps_postdoc_and_deduplicates_repeated_links(self):
        first = '-'.join(('2026', '11', '01'))
        second = '-'.join(('2026', '11', '02'))
        html = f'<a href="/posts/{first}-postdoc">Postdoctoral Associate</a><a href="/posts/{first}-postdoc">Postdoctoral Associate</a><a href="/posts/{second}-postgraduate">Postgraduate Associate</a>'
        rows,_ = M.yale(M.Document(html).root,self.source('yale'))
        self.assertEqual(len(rows),1)

    def test_pagination_cannot_switch_hosts(self):
        doc=M.Document('<a rel="next" title="Next page" href="https://unrelated.example/page">Next</a>').root
        self.assertIsNone(M.next_page(doc,'https://jobs.hku.hk/en/search/','jobs.hku.hk'))

    def test_failed_source_preserves_cache_without_advancing_evidence_date(self):
        old={'id':'old','title':'Old','source_id':'hku','last_seen':'2026-11-01T00:00:00Z'}
        data=M.combine({'jobs':[old]},[([] , {'id':'hku','status':'unavailable'})],'2026-11-18T00:00:00Z')
        self.assertEqual(data['jobs'][0]['last_seen'],old['last_seen'])
        self.assertTrue(data['jobs'][0]['stale'])

    def test_successful_source_replaces_prior_coverage_and_deduplicates(self):
        new={'id':'new','title':'New','source_id':'hku'}
        data=M.combine({'jobs':[{'id':'old','title':'Old','source_id':'hku'}]},[([dict(new),dict(new)],{'id':'hku','status':'ok'})],'2026-11-18T00:00:00Z')
        self.assertEqual(len(data['jobs']),1)
        self.assertFalse(data['jobs'][0]['stale'])

    def test_scripts_and_styles_are_never_indexed_as_text(self):
        self.assertEqual(M.Document('<p>Real</p><script>hidden()</script><style>body{}</style>').root.text(),'Real')

if __name__=='__main__':
    unittest.main()
