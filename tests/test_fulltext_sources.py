import json
import unittest
from test_notice_index import M,S,NOW,BODY

class FulltextSources(unittest.TestCase):
    def test_every_source_has_a_bounded_body_budget(self):
        self.assertGreaterEqual(len(S.SOURCES),14)
        self.assertTrue(all(0<s.get('detail_budget',0)<=50 for s in S.SOURCES))

    def test_source_specific_bodies_include_requirements_and_exclude_navigation(self):
        containers={
            'academictransfer':('section',''), 'hku':('div','itemprop="description"'),
            'csiro':('span','itemprop="description"'), 'yale':('main',''),
            'stanford':('article','class="node-postdocs-job"'),
            'leibniz':('div','class="tx_jobfair"'),'mpg':('main','class="content"'),
            'eth':('section','class="description"'),'copenhagen':('div','class="vacancy_details_area"'),
            'kth':('div','class="job-details-content"'),'ubc':('article','class="node--type-job-posting"'),
            'jrec':('div','class="card_body"'),'jobsuk':('div','id="job-description"'),'jobrxiv':('div','class="job_description"')}
        for sid,(tag,attrs) in containers.items():
            with self.subTest(source=sid):
                title='Postdoctoral Researcher in Biology'
                row={'source_id':sid,'title':title}
                heading=f'<h1>{title}</h1>'
                if sid=='stanford':row['title']='Postdoc · Biology · Jane Scientist';heading='<h1>Open Postdoctoral position, faculty mentor Jane Scientist</h1>'
                if sid=='jrec':heading=f'<h5 class="card_title_min">{title}</h5>'
                h=f'<nav>unrelatednavigation</nav><{tag} {attrs}>{heading}<p>{BODY}</p><h2>Requirements</h2><p>Uniquequalification Python remote sensing.</p></{tag}><footer>unrelatedfooter</footer>'
                body,_,_=M.notice_body(S.Document(h).root,row,S.Document)
                words,phrases=M.terms(body)
                self.assertIn('uniquequalification',words)
                self.assertIn('remote sensing',phrases)
                self.assertNotIn('unrelatednavigation',words)
                self.assertNotIn('unrelatedfooter',words)
                row['title']='Completely different notice'
                with self.assertRaises(ValueError):M.notice_body(S.Document(h).root,row,S.Document)

    def test_jsonld_html_title_and_extra_requirements_are_retained(self):
        row={'source_id':'jobsuk','title':'Postdoc in vivo'}
        posting={'@type':'JobPosting','title':'Postdoc <em>in vivo</em>','description':BODY,'qualifications':'Python imaging'}
        body,_,_=M.notice_body(S.Document('<script type="application/ld+json">'+json.dumps(posting)+'</script>').root,row,S.Document)
        self.assertIn('Python imaging',body)

    def test_access_challenge_is_never_indexed(self):
        with self.assertRaisesRegex(ValueError,'Access restricted'):
            M.notice_body(S.Document('<h1>JavaScript is disabled</h1><p>'+BODY+'</p>').root,{'source_id':'hku','title':'Postdoc'},S.Document)

    def test_new_listing_snapshot_does_not_erase_validated_body_cache(self):
        old={'id':'1','title':'Postdoc','detail_status':'indexed','detail_index_version':2,'detail_checked_at':NOW,'search_terms':['soil']}
        merged=M.merge_cache_snapshots({'generated_at':'1','jobs':[old]},{'generated_at':'2','jobs':[{'id':'1','title':'Postdoc'}]})
        self.assertEqual(merged['jobs'][0]['search_terms'],['soil'])

    def test_new_snapshot_keeps_extra_body_cache_until_listing_replacement(self):
        old={'id':'extra','title':'Postdoc','source_id':'yale','detail_status':'indexed','detail_index_version':2,'search_terms':['soil']}
        merged=M.merge_cache_snapshots({'generated_at':'1','jobs':[old]},{'generated_at':'2','jobs':[]})
        self.assertEqual(merged['jobs'],[old])
        self.assertEqual(S.combine(merged,[([],{'id':'yale','status':'ok'})],NOW)['jobs'],[])

    def test_failed_retry_backoff_preserves_prior_evidence_and_does_not_fetch(self):
        row={'id':'x','title':'Postdoc','source_id':'hku','url':'https://example.org/x'}
        old={**row,'detail_status':'unavailable','detail_error':'access_restricted','detail_attempted_at':NOW}
        class Client:
            def __init__(self,source):raise AssertionError('Backoff must prevent fetching')
        result=M.enrich_source([row],{'detail_budget':5},{'jobs':[old]},Client,S.Document,S.parse_date,NOW)[0]
        self.assertEqual(result['detail_error'],'access_restricted')
        self.assertEqual(M.body_coverage([result])['body_unavailable'],1)

    def test_mpg_real_show_more_controls_advance_offset(self):
        doc=S.Document('<a href="/jobboard/123/more_items" data-loadmore-context="jobs" data-loadmore-next-limit="5" data-loadmore-first-limit="5">More</a>').root
        first=S.next_page(doc,'https://www.mpg.de/jobboard','www.mpg.de')
        self.assertIn('offset=5',first)
        second=S.next_page(S.Document('<li><h4>Next notice</h4></li>').root,first,'www.mpg.de')
        self.assertIn('offset=10',second)
        self.assertIsNone(S.next_page(S.Document('').root,second,'www.mpg.de'))

    def test_jrec_language_form_must_belong_to_same_notice(self):
        class Client:
            def __init__(self,identifier):self.identifier=identifier;self.calls=[]
            def get(self,url):
                self.calls.append(url)
                return '<p>English notice</p>' if 'Changelang' in url else '<button name="changeLangBtn" value="1" data-id="'+self.identifier+'">English</button>'
        row={'source_id':'jrec','url':'https://jrecin.jst.go.jp/seek/SeekJorDetail?id=D123'}
        right=Client('D123');M.detail_document(row,right,S.Document)
        self.assertEqual(len(right.calls),2)
        self.assertTrue(right.calls[-1].endswith('id=D123&lang=1'))
        wrong=Client('OTHER');M.detail_document(row,wrong,S.Document)
        self.assertEqual(len(wrong.calls),1)

    def test_mpg_pagination_uses_actual_control_and_retains_offset(self):
        doc=S.Document('<a href="/jobboard/123/more_items" data-loadmore-context="jobs" data-loadmore-next-limit="5" data-loadmore-first-limit="5"></a>').root
        target=S.next_page(doc,'https://www.mpg.de/jobboard','www.mpg.de')
        self.assertIn('offset=5',target)
        following=S.next_page(S.Document('<li>Another vacancy</li>').root,target,'www.mpg.de')
        self.assertIn('offset=10',following)

    def test_missing_body_and_failed_body_are_distinct_in_coverage(self):
        stats=M.body_coverage([{}, {'detail_status':'unavailable'}, {'detail_status':'indexed','detail_index_version':M.INDEX_VERSION}])
        self.assertEqual((stats['body_indexed'],stats['body_pending'],stats['body_unavailable']),(1,1,1))
