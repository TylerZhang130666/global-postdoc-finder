"""Short, source-backed advert extracts. No inferred eligibility or salary."""
import re
from urllib.parse import urljoin,urlsplit

HEADINGS=re.compile(r'^(?:job description|position description|project background|research description|responsibilities|your tasks|your profile|profile|qualifications?|requirements?|selection criteria|essential criteria|minimum requirements|application instructions|how to apply|application procedure|required documents|we offer|salary|compensation|benefits|contact|about us|about the (?:lab|department)|working conditions|terms of employment|employment conditions|workplace|important info)',re.I)
REQUIREMENTS=re.compile(r'qualifications?|requirements?|selection criteria|essential criteria|your profile|^profile$',re.I)
APPLY=re.compile(r'application instructions|how to apply|application procedure|required documents',re.I)
NOISE=re.compile(r'cookie|equal opportunity|equal employment|reasonable accommodation|privacy policy|all qualified applicants|diversity and inclusion',re.I)

def clean(value,limit=220):
    value=re.sub(r'\s+',' ',str(value)).strip()
    value=re.sub(r'https?://\S+|\S+@\S+|\S+\s*\(at\)\s*\S+','[see notice]',value,flags=re.I)
    value=re.sub(r'(?<!\w)\+\d[\d ()-]{7,}\d','[see notice]',value)
    if len(value)>limit:value=value[:limit].rsplit(' ',1)[0]+'…'
    return value

def extract_details(doc,body,posting,record):
    # Only strings contained in the already identity-verified notice body can
    # supply fields. Navigation, related notices and page footers are excluded.
    markers=[]
    for node in doc.all():
        if node.tag not in {'h2','h3','h4','h5','strong','b'} and 'field-label' not in node.attrs.get('class','').split():continue
        label=node.text().strip().rstrip(':')
        if not label or len(label)>65 or not (HEADINGS.search(label) or re.search(r'^required qualifications|^required application|^how to submit|応募資格|仕事内容|応募書類|応募方法|契約期間|待遇',label,re.I)):continue
        pos=body.find(label)
        if pos>=0:markers.append((pos,label))
    markers=sorted(set(markers))
    sections=[]
    for i,(pos,label) in enumerate(markers):
        end=markers[i+1][0] if i+1<len(markers) else len(body)
        value=body[pos+len(label):end].strip(' :')
        if value:sections.append((label,value))
    paragraphs=[]
    for n in doc.all():
        if n.tag!='p':continue
        value=n.text()
        if 60<=len(value)<=2500 and value in body and not NOISE.search(value):paragraphs.append(value)
    science=next((value for label,value in sections if re.search(r'job description|position description|project background|research description|responsibilities|your tasks',label,re.I)),None)
    if not science:science=next((p for p in paragraphs if re.search(r'research|project|stud(?:y|ies)|investigat|laborator',p,re.I)),None)
    info={'excerpt':clean(science,300) if science else '', 'requirements':[], 'application':[], 'salary':'','contract':'','people':[], 'source_url':record['url']}
    def parts(value):
        return [clean(v,150) for v in re.split(r'(?<=[.;])\s+|\s*[•●]\s*',value) if len(v)>25 and not NOISE.search(v)][:2]
    requirements=next((value for label,value in sections if REQUIREMENTS.search(label) or '応募資格' in label),None)
    if requirements:info['requirements']=parts(requirements)
    application=next((value for label,value in sections if APPLY.search(label) or re.search(r'required application|how to submit|応募書類|応募方法',label,re.I)),None)
    if application:info['application']=parts(application)[:1]
    sentences=re.split(r'(?<=[.!?;])\s+',body)
    pay=next((s for s in sentences if re.search(r'(?:£|€|\$|USD|EUR|GBP|CHF|AUD|CAD|HKD|CNY|JPY|SEK|DKK)\s*[\d,]+',s) and re.search(r'salary|pay|remuneration|stipend|compensation',s,re.I)),None)
    if pay:
        match=re.search(r'(?:£|€|\$|USD|EUR|GBP|CHF|AUD|CAD|HKD|CNY|JPY|SEK|DKK)\s*[\d,]+',pay)
        labels=list(re.finditer(r'salary|pay range|remuneration|stipend|compensation',pay[:match.start()],re.I))
        start=labels[-1].start() if labels else match.start()
        value=re.split(r'\s+(?:Location|Job description|Employer|Contact)\b',pay[start:match.end()+80])[0]
        info['salary']=clean(value,140)
    salary=posting.get('baseSalary')
    if isinstance(salary,dict) and re.fullmatch(r'[A-Z]{3}',str(salary.get('currency',''))):
        value=salary.get('value',{})
        if isinstance(value,dict):
            numbers=[value.get('minValue'),value.get('maxValue')] if value.get('minValue') is not None else [value.get('value')]
            if numbers and all(isinstance(n,(int,float)) and 0<=n<1e9 for n in numbers):
                amount='–'.join(dict.fromkeys(f'{n:,.0f}' if float(n).is_integer() else f'{n:,.2f}' for n in numbers))
                unit=value.get('unitText','')
                if unit in {'HOUR','DAY','WEEK','MONTH','YEAR'}:info['salary']=salary['currency']+' '+amount+' / '+unit
    contract=next((s for s in sentences if re.search(r'contract|appointment|position|fixed.term|duration|employment',s,re.I) and re.search(r'\b(?:\d+|one|two|three|four|five)\s*(?:year|month)s?\b',s,re.I) and not re.search(r'experience|Ph\.?D\.? (?:within|in the last|obtained)',s,re.I)),None)
    if contract:
        match=re.search(r'\b(?:\d+|one|two|three|four|five)\s*(?:year|month)s?\b',contract,re.I)
        info['contract']=clean(contract[max(0,match.start()-55):match.end()+35],135)
    if record.get('source_id')=='stanford' and '·' in record['title']:
        info['faculty']=record['title'].rsplit('·',1)[-1].strip()
    # Keep a sentence around an explicit currency/pay-scale or contract period;
    # never convert currencies, infer yearly pay or confuse project duration.
    for sentence in re.split(r'(?<=[.!?])\s+',body):
        if not info['salary'] and re.search(r'\bsalary\b|\bremuneration\b|\bpay scale\b',sentence,re.I):
            amount=re.search(r'[$€£]|\b(?:USD|EUR|GBP|CHF|AUD|CAD|HKD|DKK|SEK|JPY|TV-L|E\s?13)\b',sentence,re.I)
            if amount:
                labels=list(re.finditer(r'salary|remuneration|pay scale',sentence[:amount.start()],re.I))
                start=labels[-1].start() if labels and amount.start()-labels[-1].start()<80 else max(0,amount.start()-30)
                info['salary']=clean(sentence[start:amount.end()+100],150)
    if record['source_id']=='stanford' and '·' in record['title']:
        name=record['title'].rsplit('·',1)[-1].strip()
        # The listing explicitly names faculty. Do not infer a PI elsewhere
        # merely because a personal name occurs in a contact paragraph.
        if name and name in body:
            link=next((a for a in doc.all('a') if a.text().strip()==name and a.attrs.get('href')),None)
            url=urljoin(record['url'],link.attrs['href']) if link else record['url']
            if urlsplit(url).scheme!='https' or urlsplit(url).username:url=record['url']
            info['people']=[{'name':name,'url':url,'evidence_url':record['url']}]
    # A bounded extract, not a republication of the full advert. Avoid cutting
    # salary/contract conditions: display those only as whole bounded snippets.
    chars=1100;words=150
    for key in ('excerpt','requirements','salary','contract','application'):
        values=info[key] if isinstance(info[key],list) else [info[key]]
        kept=[]
        for value in values:
            if not value:continue
            size=len(value.split())
            if len(value)<=chars and size<=words:kept.append(value);chars-=len(value);words-=size
        info[key]=kept if isinstance(info[key],list) else (kept[0] if kept else '')
    return info
