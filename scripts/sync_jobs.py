#!/usr/bin/env python3
"""Build a small searchable index from public recruitment lists; no model or key.

Listing metadata and distinct search terms from verified notice bodies are retained. Requests respect robots.txt, crawl delays,
same-host pagination and fixed page budgets. Failed sources retain dated cache
entries, explicitly marked stale; a failed fetch never advances last_seen.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit, parse_qsl, urlencode, urlunsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = 'PostdocFinder/1.0 (+https://github.com/TylerZhang130666/global-postdoc-finder)'
POSTDOC = re.compile(r'post[\s\-–]?doc(?:toral|torate)?|博士后|博后', re.I)
VOID = set('area base br col embed hr img input link meta param source track wbr'.split())

class Node:
    def __init__(self, tag='', attrs=(), parent=None):
        self.tag, self.attrs, self.parent, self.children = tag, dict(attrs), parent, []

    def all(self, tag=None, cls=None):
        for child in self.children:
            if not isinstance(child, Node):
                continue
            if (tag is None or child.tag == tag) and (cls is None or cls in child.attrs.get('class', '').split()):
                yield child
            yield from child.all(tag, cls)

    def text(self):
        if self.tag in {'script', 'style', 'template'}:
            return ''
        return re.sub(r'\s+', ' ', ' '.join(c.text() if isinstance(c, Node) else c for c in self.children)).strip()

    def first(self, tag=None, cls=None):
        return next(self.all(tag, cls), Node())

class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)

def excerpt(value, limit=220):
    value = re.sub(r'\s+', ' ', value).strip()
    # No contact details are needed in an index; the original notice has them.
    value = re.sub(r'\S+@\S+', '', value)
    return value if len(value) <= limit else value[:limit].rsplit(' ', 1)[0] + '…'

def job(title, url, source, **fields):
    url = urljoin(source['url'], url)
    if urlsplit(url).hostname != urlsplit(source['url']).hostname:
        raise ValueError('Unexpected external job URL')
    return dict(id=sha256(url.encode()).hexdigest()[:20], title=title.strip(), url=url,
                institution=fields.pop('institution', source['name']), country=fields.pop('country', source['country']),
                source_id=source['id'], source_name=source['name'], **fields)

def academictransfer(doc, source):
    rows, recognized = [], 0
    for card in doc.all('article'):
        link = next((a for a in card.all('a') if re.search(r'/en/jobs/\d+/', a.attrs.get('href', ''))), None)
        if link is None:
            continue
        recognized += 1
        title = card.first('h3').text()
        if not POSTDOC.search(title):
            continue
        dates = list(card.all('time'))
        employer = next((span.text() for span in card.all('span') if 'md:text-right' in span.attrs.get('class', '').split()), '')
        rows.append(job(title, link.attrs['href'], source, institution=employer or source['name'],
                        deadline_at=dates[0].attrs.get('datetime', '') if dates else '',
                        posted_at=dates[1].attrs.get('datetime', '') if len(dates)>1 else '',
                        summary=excerpt(card.first('p').text())))
    return rows, recognized

def hku(doc, source):
    rows, recognized = [], 0
    for row in doc.all('tr'):
        link = row.first('a', 'job-link')
        if not link.attrs.get('href'):
            continue
        recognized += 1
        title = link.text()
        if not POSTDOC.search(title):
            continue
        cells = list(row.all('td'))
        department = cells[2].text() if len(cells)>2 else ''
        rows.append(job(title, link.attrs['href'], source, department=department,
                        deadline_at=row.first('time').attrs.get('datetime', ''), summary=department))
    return rows, recognized

def csiro(doc, source):
    rows, recognized = [], 0
    for row in doc.all('tr', 'data-row'):
        link = row.first('a', 'jobTitle-link')
        if not link.attrs.get('href'):
            continue
        recognized += 1
        if POSTDOC.search(link.text()):
            rows.append(job(link.text(), link.attrs['href'], source,
                            location=row.first('span', 'jobLocation').text(),
                            posted_at=row.first('span', 'jobDate').text(), summary=''))
    return rows, recognized

def yale(doc, source):
    rows, seen = [], set()
    for link in doc.all('a'):
        href = link.attrs.get('href', '')
        if not re.search(r'/posts/\d{4}-\d{2}-\d{2}-', href) or not link.text() or href in seen:
            continue
        seen.add(href)
        title = link.text()
        if POSTDOC.search(title):
            posted = re.search(r'/posts/(\d{4}-\d{2}-\d{2})-', href).group(1)
            rows.append(job(title, href, source, posted_at=posted, summary=''))
    return rows, len(seen)

def stanford(doc, source):
    rows, recognized = [], 0
    for row in doc.all('tr'):
        link = next((a for a in row.all('a') if '/prospective/opportunities/' in a.attrs.get('href','')), None)
        if not link:
            continue
        recognized += 1
        table = row.parent
        while table and table.tag != 'table':
            table = table.parent
        department = table.first('caption').text().removeprefix('Department:').strip() if table else ''
        faculty = row.first('strong').text().removeprefix('Position with ').strip()
        paragraphs = [p.text() for p in row.all('p') if p.text() and not p.text().startswith('Position with')]
        description = next((p for p in paragraphs if len(p)>30), '')
        posted = re.search(r'Posted on:\s*([A-Za-z]+ \d{1,2}, \d{4})', row.text())
        posted_at = datetime.strptime(posted.group(1), '%B %d, %Y').date().isoformat() if posted else ''
        rows.append(job('Postdoc · ' + department + ' · ' + faculty, link.attrs['href'], source,
                        department=department, posted_at=posted_at, summary=excerpt(description)))
    return rows, recognized

def parse_date(value):
    for pattern, fmt in [(r'\d{4}-\d{2}-\d{2}', '%Y-%m-%d'), (r'\d{2}-\d{2}-\d{4}', '%d-%m-%Y'),
                         (r'\d{4}/\d{2}/\d{2}', '%Y/%m/%d'), (r'\d{2}/\d{2}/\d{4}', '%d/%m/%Y'),
                         (r'\d{2}\.\d{2}\.\d{4}', '%d.%m.%Y'), (r'[A-Z][a-z]+ \d{1,2}, \d{4}', '%B %d, %Y')]:
        match = re.search(pattern, value)
        if match:
            try:
                return datetime.strptime(match.group(), fmt).date().isoformat()
            except ValueError:
                pass
    return ''

def ancestor(node, tag=None, cls=None):
    while node:
        if (tag is None or node.tag == tag) and (cls is None or cls in node.attrs.get('class','').split()):
            return node
        node = node.parent
    return Node()

def table_jobs(doc, source):
    rows, recognized = [], 0
    for row in doc.all('tr'):
        link = next((a for a in row.all('a') if re.search(source['link_pattern'], a.attrs.get('href',''))), None)
        if not link:
            continue
        recognized += 1
        if not POSTDOC.search(link.text()):
            continue
        cells = list(row.all('td'))
        title, location, employer = link.text(), '', source['name']
        country = source['country']
        if source['id'] == 'copenhagen':
            location = cells[2].text() if len(cells)>2 else ''
        elif source['id'] == 'kth':
            location = cells[1].text() if len(cells)>1 else ''
            employer = cells[2].text() if len(cells)>2 else employer
        elif source['id'] == 'ubc':
            # This Canadian board also carries US positions; don't label all as Canada.
            if 'UC Santa Barbara' in title:
                country, employer = '美国', 'University of California, Santa Barbara'
            elif 'UBC' in title or 'Vancouver' in title:
                country = '加拿大'
            else:
                country = '未注明'
        value = row.first('time').attrs.get('datetime', '')
        rows.append(job(title, link.attrs['href'], source, institution=employer, country=country,
                        department=location, deadline_at=value or parse_date(cells[-1].text() if cells else ''), summary=''))
    return rows, recognized

def eth(doc, source):
    rows, recognized = [], 0
    for card in doc.all('li', 'job-ad__item__wrapper'):
        link = card.first('a', 'job-ad__item__link')
        if not link.attrs.get('href'):
            continue
        recognized += 1
        title = card.first('h3').text()
        if not POSTDOC.search(title):
            continue
        detail = card.first('div', 'job-ad__item__details').text()
        company = card.first('div', 'job-ad__item__company').text()
        country = '新加坡' if 'Singapore' in detail else '瑞士' if re.search(r'Zürich|Zurich|Basel|Villigen|Lugano|Lausanne|Dübendorf|Davos', detail, re.I) else '未注明'
        rows.append(job(title, link.attrs['href'], source, country=country, location=detail,
                        department=company.split('|')[-1].strip(), posted_at=parse_date(company), summary=''))
    return rows, recognized

def leibniz(doc, source):
    rows, recognized = [], 0
    for link in doc.all('a'):
        if '/careers/jobs/detail/job/show/Job/' not in link.attrs.get('href',''):
            continue
        recognized += 1
        if POSTDOC.search(link.text()):
            parent = link.parent.parent
            country='捷克' if re.search(r'\bPrague\b|\bPrag\b',link.text(),re.I) else source['country']
            rows.append(job(link.text(), link.attrs['href'], source,country=country,
                            institution=parent.first('p').text() or source['name'], summary=''))
    return rows, recognized

def mpg(doc, source):
    rows, recognized = [], 0
    for heading in doc.all('h3'):
        link = heading.first('a')
        if not re.match(r'/\d+/', link.attrs.get('href','')):
            continue
        recognized += 1
        if POSTDOC.search(link.text()):
            box=ancestor(heading, cls='text-box')
            rows.append(job(link.text(), link.attrs['href'], source,
                            institution=box.first('div','institute').text() or source['name'],
                            posted_at=parse_date(box.text()), summary=''))
    return rows, recognized

def jrec(doc, source):
    rows, recognized, seen = [], 0, set()
    for heading in doc.all('h5', 'card_title_min'):
        link = heading.first('a')
        url = link.attrs.get('href','')
        if 'SeekJorDetail' not in url or url in seen:
            continue
        seen.add(url)
        recognized += 1
        title=link.text()
        if not POSTDOC.search(title):
            continue
        card=ancestor(heading, cls='card_header')
        body=card.text()
        tail=body.split(title,1)[-1].strip()
        deadline=re.search(r'End date of accepting applications\s*:\s*(\d{4}/\d{2}/\d{2})',body)
        updated=re.search(r'Date of update\s*:\s*(\d{4}/\d{2}/\d{2})',body)
        employer=heading.parent.first('div','my-1').text() or source['name']
        rows.append(job(title,url,source,institution=employer,summary=excerpt(tail,160),
                        deadline_at=parse_date(deadline.group(1)) if deadline else '',
                        posted_at=parse_date(updated.group(1)) if updated else ''))
    return rows,recognized

def jobsuk(doc, source):
    rows, recognized = [], 0
    for card in doc.all('div','j-doorway__result'):
        link=next((a for a in card.all('a') if '/job/' in a.attrs.get('href','')), None)
        if not link:
            continue
        recognized+=1
        if not POSTDOC.search(link.text()):
            continue
        # The board includes overseas jobs. Preserve its location text without
        # inferring every result is in the UK just because of the portal domain.
        info=card.first('div','j-doorway__result-info')
        employer=info.first('div','j-doorway__employer').text()
        location=info.first('div','j-doorway__location').text()
        body=info.text()
        if not employer:
            blocks=[n.text() for n in info.children if isinstance(n,Node)]
            employer=blocks[1] if len(blocks)>1 else source['name']
        country='英国' if re.search(r'University of (?:Oxford|Cambridge|Exeter|Birmingham|Bristol|Nottingham|Leeds|Liverpool|Manchester|Edinburgh|Warwick|Southampton|Sheffield|York|Bath|Glasgow)|Imperial College London|King.s College London|University College London',employer) else '未注明'
        rows.append(job(link.text(),link.attrs['href'],source,institution=employer,country=country,
                        location=location,posted_at=parse_date(body),summary=excerpt(body.replace(link.text(),'').replace(employer,''),140)))
    return rows,recognized

def jobrxiv(doc,source):
    rows=[];recognized=0
    countries={'United States (US)':'美国','United Kingdom (UK)':'英国','Germany':'德国','China':'中国','Canada':'加拿大','Australia':'澳大利亚','Netherlands':'荷兰','Switzerland':'瑞士','France':'法国','Japan':'日本','Sweden':'瑞典','Denmark':'丹麦','New Zealand':'新西兰','Singapore':'新加坡','Austria':'奥地利','Belgium':'比利时','Spain':'西班牙','Poland':'波兰','Italy':'意大利','Finland':'芬兰','Norway':'挪威','Hong Kong':'中国香港','Taiwan':'中国台湾','South Korea':'韩国','Ireland':'爱尔兰','Israel':'以色列','Brazil':'巴西','South Africa':'南非','Italy':'意大利','Norway':'挪威','Finland':'芬兰','Ireland':'爱尔兰','South Korea':'韩国','Hong Kong':'中国香港','Taiwan':'中国台湾'}
    for card in doc.all('li','job_listing'):
        link=card.first('a');heading=card.first('h4')
        if not link.attrs.get('href') or not heading.text():continue
        recognized+=1
        title=' '.join(c for c in heading.children if isinstance(c,str)).strip()
        if not POSTDOC.search(title):continue
        location=card.first('span','ws-meta-job-location').text()
        rows.append(job(title,link.attrs['href'],source,institution=card.first('span','ws-meta-company-name').text() or source['name'],country=countries.get(location,'未注明'),location=location,posted_at=card.first('time').attrs.get('datetime',''),summary=excerpt(card.first('div','listing-desc').text())))
    return rows,recognized

SOURCES = [
    dict(id='jobrxiv',name='jobRxiv',country='未注明',url='https://jobrxiv.org/job-category/postdoc/',pages=40,parser=jobrxiv,detail_budget=50,scope='公开博后分类，近180天发布记录；未核实当前招聘状态'),
    dict(id='academictransfer', name='AcademicTransfer', country='荷兰', url='https://www.academictransfer.com/en/jobs/?q=postdoc', pages=1, parser=academictransfer, detail_budget=10, scope='首屏10条；其余动态分页API禁止采集，未覆盖全部结果'),
    dict(id='hku', name='The University of Hong Kong', country='中国香港', url='https://jobs.hku.hk/en/search/?category=Senior+Research+Staff+%26+Post-doctoral+Fellow', pages=5, parser=hku, detail_budget=15, scope='博后类目，最多五页；仅保留博后标题'),
    dict(id='csiro', name='CSIRO', country='澳大利亚', url='https://jobs.csiro.au/search/?q=postdoctoral', pages=2, parser=csiro, detail_budget=10, scope='关键词 postdoctoral，最多两页'),
    dict(id='yale', name='Yale University', country='美国', url='https://postdocs.yale.edu/applicants/open-positions', pages=40, parser=yale, detail_budget=30, scope='公开机会，最多四十页；仅保留博后标题'),
    dict(id='stanford', name='Stanford University', country='美国', url='https://postdocs.stanford.edu/prospective/opportunities', pages=2, parser=stanford, detail_budget=12, scope='公开博后列表，最多两页'),
    dict(id='leibniz',name='Leibniz Association',country='德国',url='https://www.leibniz-gemeinschaft.de/en/careers/jobs',pages=1,parser=leibniz,detail_budget=25,scope='公开招聘列表中的博后标题；逐项索引公告正文'),
    dict(id='mpg',name='Max Planck Society',country='德国',url='https://www.mpg.de/jobboard',pages=100,parser=mpg,detail_budget=25,scope='公开招聘列表及 Show more 分页；仅保留博后标题'),
    dict(id='eth',name='ETH Zürich',country='未注明',url='https://jobs.ethz.ch/site/index',pages=1,parser=eth,detail_budget=35, scope='全部可见列表，按岗位地点区分瑞士和新加坡'),
    dict(id='copenhagen',name='University of Copenhagen',country='丹麦',url='https://employment.ku.dk/all-vacancies/',pages=1,parser=table_jobs,link_pattern=r'\?show=\d+',detail_budget=20, scope='全部公开岗位中的博后标题'),
    dict(id='kth',name='KTH',country='瑞典',url='https://www.kth.se/lediga-jobb/?l=en',pages=1,parser=table_jobs,link_pattern=r'/lediga-jobb/\d+',detail_budget=20, scope='全部公开岗位中的博后标题'),
    dict(id='ubc',name='University of British Columbia',country='未注明',url='https://www.postdocs.ubc.ca/careers?order=field_deadline&sort=asc',pages=1,parser=table_jobs,link_pattern=r'/positions/\d+',detail_budget=15, scope='博后招聘表；境外岗位另标地点'),
    dict(id='jrec',name='JREC-IN',country='日本',url='https://jrecin.jst.go.jp/seek/SeekJorSearch?fn=2&jobkind=00015&ln=1&dispcount=50',pages=6,parser=jrec,detail_budget=35, scope='研究员/博后类目，最多六页，仅保留明确博后标题'),
    dict(id='jobsuk',name='jobs.ac.uk',country='未注明',url='https://www.jobs.ac.uk/categories/postdoc-jobs',pages=8,parser=jobsuk,detail_budget=30, scope='Postdoc分类，最多八页，海外地点不默认为英国'),
]

class Client:
    def __init__(self, source):
        self.host = urlsplit(source['url']).hostname
        self.delay = 1.0
        self.last = 0
        self.robot = RobotFileParser()
        try:
            robots = self.raw('https://' + self.host + '/robots.txt')
        except HTTPError as error:
            if error.code not in {404, 410}:
                raise
            robots = ''
        self.robot.parse(robots.lstrip('\ufeff').splitlines())
        self.delay = max(1.0, self.robot.crawl_delay('PostdocFinder') or self.robot.crawl_delay('*') or 1)

    def raw(self, url, data=None):
        if urlsplit(url).scheme != 'https' or urlsplit(url).hostname != self.host:
            raise ValueError('Only same-host HTTPS requests are allowed')
        time.sleep(max(0, self.last + self.delay - time.monotonic()))
        self.last = time.monotonic()
        headers={'User-Agent': USER_AGENT, 'Accept': 'text/html,text/plain'}
        if self.host=='www.mpg.de' and re.fullmatch(r'/jobboard/\d+/more_items',urlsplit(url).path):
            headers['X-Requested-With']='XMLHttpRequest'
        with urlopen(Request(url, data=data, headers=headers), timeout=25) as r:
            if urlsplit(r.url).hostname != self.host:
                raise ValueError('Unexpected cross-host redirect')
            return r.read(5_000_000).decode('utf-8', errors='replace')

    def get(self, url):
        if not self.robot.can_fetch('PostdocFinder', url):
            raise ValueError('Source robots.txt excludes this URL')
        return self.raw(url)

    def search_post(self,url,fields):
        if not self.robot.can_fetch('PostdocFinder',url):raise ValueError('Source robots.txt excludes this URL')
        return self.raw(url,urlencode(fields).encode())

def next_page(doc, url, host):
    if host=='www.mpg.de':
        control=next((a for a in doc.all('a') if a.attrs.get('data-loadmore-context')=='jobs'),None)
        if control:
            target=urljoin(url,control.attrs.get('href',''))
            if urlsplit(target).hostname==host:
                limit=int(control.attrs.get('data-loadmore-next-limit','5'))
                offset=int(control.attrs.get('data-loadmore-first-limit',str(limit)))
                return target+'?'+urlencode({'context':'jobs','limit':limit,'offset':offset})
        parts=urlsplit(url);query=dict(parse_qsl(parts.query))
        if re.fullmatch(r'/jobboard/\d+/more_items',parts.path) and doc.text():
            query['offset']=str(int(query['offset'])+int(query['limit']))
            return urlunsplit((parts.scheme,parts.netloc,parts.path,urlencode(query),''))
    if host=='jrecin.jst.go.jp':
        parts=urlsplit(url)
        query=dict(parse_qsl(parts.query))
        current=int(query.get('page','1'))
        if any(a.attrs.get('data-pageno')==str(current+1) for a in doc.all('a')):
            query['page']=str(current+1)
            return urlunsplit((parts.scheme,parts.netloc,parts.path,urlencode(query),''))
    for link in doc.all('a'):
        a = link.attrs
        if ('next' in a.get('rel', '').split() or a.get('title','').lower() in {'go to next page', 'next page', 'more jobs'}
                or link.text().lower().startswith('more jobs') or link.text().strip().lower() in {'next','下一页'}):
            target = urljoin(url, a.get('href', ''))
            if urlsplit(target).hostname == host:
                return target
    return None

def collect(source, now):
    state = dict(id=source['id'], name=source['name'], url=source['url'], scope=source['scope'], attempted_at=now, pages_read=0)
    rows, recognized = [], 0
    try:
        client = Client(source)
        if source['id']=='jobrxiv':
            # Public load-more request observed in the site's own frontend.
            # Date ordering permits a bounded recent window without crawling
            # years of old adverts or treating all archived records as open.
            cutoff=(datetime.fromisoformat(now)-timedelta(days=180)).date().isoformat()
            for page in range(1,source['pages']+1):
                payload=json.loads(client.search_post('https://jobrxiv.org/jm-ajax/get_listings/',{'search_categories[]':'postdoc','per_page':25,'page':page,'orderby':'date','order':'DESC','show_pagination':'false','search_keywords':'','search_location':''}))
                if not isinstance(payload.get('html'),str) or not isinstance(payload.get('max_num_pages'),(int,float)):raise ValueError('Unrecognized public jobRxiv search response')
                doc=Document(payload['html']).root;found,count=source['parser'](doc,source)
                if not count and payload.get('found_jobs'):raise ValueError('Unrecognized jobRxiv cards')
                state['pages_read']+=1;recognized+=count
                rows.extend(r for r in found if r.get('posted_at','')>=cutoff)
                dates=[n.attrs.get('datetime','') for n in doc.all('time') if n.attrs.get('datetime')]
                reached_window=bool(dates) and max(dates)<cutoff
                if reached_window or page>=payload['max_num_pages']:
                    state.update(status='ok',count=len({r['id'] for r in rows}),observed_at=now,coverage='recent_window' if reached_window else 'end_of_list',listing_entries=recognized)
                    return rows,state
            state.update(status='ok',count=len({r['id'] for r in rows}),observed_at=now,coverage='page_limit',listing_entries=recognized)
            return rows,state
        url, visited = source['url'], set()
        for _ in range(source['pages']):
            if not url or url in visited:
                break
            visited.add(url)
            doc = Document(client.get(url)).root
            found, count = source['parser'](doc, source)
            if not count:
                if source['id']=='mpg' and not doc.text() and state['pages_read']:
                    url=None
                    break
                raise ValueError('Listing structure not recognized; previous cache retained')
            recognized += count
            rows.extend(found)
            state['pages_read'] += 1
            url = next_page(doc, url, client.host)
        state.update(status='ok', count=len({r['id'] for r in rows}), observed_at=now,
                     coverage='page_limit' if url and url not in visited else 'end_of_list')
        state['listing_entries']=recognized
        state['excluded_by_title']=recognized-state['count']
        if source['id']=='academictransfer':state['coverage']='dynamic_paging_unavailable'
    except Exception as e:
        state.update(status='partial' if rows else 'unavailable', count=len({r['id'] for r in rows}), error=str(e)[:180])
        if rows:
            state['observed_at'] = now
    return rows, state

def combine(previous, batches, now):
    records, statuses = {}, []
    for rows, state in batches:
        statuses.append(state)
        for row in rows:
            row.update(last_seen=now, stale=False)
            records[row['id']] = row
        if state['status'] != 'ok':
            for old in previous.get('jobs', []):
                if old.get('source_id') == state['id'] and old['id'] not in records:
                    records[old['id']] = dict(old, stale=True)
    return dict(schema_version='postdoc-jobs/1', generated_at=now, sources=statuses,
                jobs=sorted(records.values(), key=lambda r: (r.get('posted_at',''), r['title']), reverse=True))

def main():
    from notice_index import enrich_source,merge_cache_snapshots,body_coverage
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, default=ROOT/'web/data/jobs.json')
    p.add_argument('--use-published-cache', action='store_true')
    args = p.parse_args()
    previous = json.loads(args.out.read_text(encoding='utf-8')) if args.out.exists() else {}
    if args.use_published_cache:
        try:
            cache_url = 'https://tylerzhang130666.github.io/global-postdoc-finder/data/jobs.json'
            with urlopen(Request(cache_url, headers={'User-Agent': USER_AGENT}), timeout=20) as response:
                cached = json.loads(response.read(20_000_000))
            if (cached.get('schema_version') == 'postdoc-jobs/1' and isinstance(cached.get('jobs'), list)
                    and cached.get('generated_at', '') > previous.get('generated_at', '')):
                previous = merge_cache_snapshots(previous,cached)
        except Exception:
            print('Published cache unavailable; using repository snapshot')
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    def sync_source(source):
        rows,state=collect(source,now)
        unique=list({r['id']:r for r in rows}.values())
        unique=enrich_source(unique,source,previous,Client,Document,parse_date,now)
        state['body_indexed']=sum(r.get('detail_status')=='indexed' for r in unique)
        return unique,state
    with ThreadPoolExecutor(max_workers=3) as pool:
        batches = list(pool.map(sync_source, SOURCES))
    data = combine(previous, batches, now)
    for s in data['sources']:
        s.update(body_coverage([r for r in data['jobs'] if r['source_id']==s['id']]))
        print(f'{s["id"]}: {s["status"]}, {s["count"]} jobs, {s["pages_read"]} pages' + (': '+s['error'] if 'error' in s else ''))
    if not any(s['status']=='ok' for s in data['sources']) and not previous:
        raise SystemExit('No usable source and no previous index; refusing an empty deployment')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temp = args.out.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    temp.replace(args.out)
    from build_hosts import write as write_hosts
    write_hosts(data['jobs'],now,args.out.parent/'hosts.json')
    print(f'{len(data["jobs"])} indexed jobs')

if __name__ == '__main__':
    main()
