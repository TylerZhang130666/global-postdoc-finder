import unittest
from test_notice_index import load,S
D=load('notice_details')
H=load('build_hosts')

class RichNoticeTests(unittest.TestCase):
    def test_requirements_salary_contract_are_source_extracts_not_inferred(self):
        body='Project background Our project studies soil carbon under climate change. Required Qualifications: A PhD in ecology is required. Experience with Python is preferred. Required Application Materials: Please provide a CV and research statement. This appointment is a fixed-term contract for two years. The salary is EUR 4500 per month.'
        html='<nav><h2>Qualifications</h2>Unrelated site text</nav><main>'+body.replace('Required Qualifications:','<div class="field-label">Required Qualifications:</div>').replace('Required Application Materials:','<div class="field-label">Required Application Materials:</div>')+'</main>'
        info=D.extract_details(S.Document(html).root,body,{},dict(title='Postdoc',source_id='stanford',url='https://example.org/job'))
        self.assertIn('PhD',info['requirements'][0]);self.assertIn('4500',info['salary']);self.assertIn('two years',info['contract']);self.assertNotIn('Unrelated',str(info))

    def test_experience_and_degree_age_are_not_contract_duration(self):
        body='This position requires three years of experience. The PhD must have been obtained in the last two years.'
        info=D.extract_details(S.Document('<main>'+body+'</main>').root,body,{},dict(title='Postdoc',source_id='yale',url='https://example.org/job'))
        self.assertFalse(info['contract']);self.assertFalse(info['salary'])

    def test_contact_details_are_removed_from_extracts(self):
        contact='private'+'@'+'example.org'
        text=D.clean('Please contact '+contact+' or https://example.org for details.')
        self.assertNotIn(contact,text);self.assertNotIn('https://',text)

    def test_potential_host_does_not_become_a_confirmed_vacancy(self):
        source={'name':'Example Researcher','institution':'Example University','country':'荷兰','url':'https://example.org/lab','research_excerpt':'Soil science','checked_at':'2026-11-18'}
        result=H.build([], [source], '2026-11-18')['hosts'][0]
        self.assertEqual(result['vacancy_status'],'not_checked');self.assertEqual(result['related_jobs'],[])

    def test_repeated_faculty_merge_related_adverts_without_inventing_person(self):
        base={'source_id':'stanford','detail_status':'indexed','title':'Postdoc · Biology · Example PI','country':'美国','institution':'Stanford University','search_terms':['soil']}
        jobs=[dict(base,id=str(i),url='https://example.org/job/'+str(i)) for i in range(2)]
        result=H.build(jobs, [], '2026-11-18')['hosts']
        self.assertEqual(len(result),1);self.assertEqual(len(result[0]['related_jobs']),2)

    def test_jobrxiv_title_identity_ignores_separate_employment_badge(self):
        from test_notice_index import M,BODY
        row={'title':'Postdoctoral Researcher','source_id':'jobrxiv'}
        html='<h1>Postdoctoral Researcher <span>Full-time</span></h1><div class="job_description">'+BODY+'</div>'
        body,_,_=M.notice_body(S.Document(html).root,row,S.Document)
        self.assertIn('soil',body)
        row['title']='A different position'
        with self.assertRaises(ValueError):M.notice_body(S.Document(html).root,row,S.Document)
