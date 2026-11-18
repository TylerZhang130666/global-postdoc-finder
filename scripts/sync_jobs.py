#!/usr/bin/env python3
"""Build a small searchable index from public recruitment lists; no model or key.

Only listing metadata is retained. Requests respect robots.txt, crawl delays,
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
from urllib.parse import urljoin, urlsplit
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
                institution=fields.pop('institution', source['name']), country=source['country'],
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

SOURCES = [
    dict(id='academictransfer', name='AcademicTransfer', country='荷兰', url='https://www.academictransfer.com/en/jobs/?q=postdoc', pages=1, parser=academictransfer, scope='关键词 postdoc，最新一页'),
    dict(id='hku', name='The University of Hong Kong', country='中国香港', url='https://jobs.hku.hk/en/search/?category=Senior+Research+Staff+%26+Post-doctoral+Fellow', pages=5, parser=hku, scope='博后类目，最多五页；仅保留博后标题'),
    dict(id='csiro', name='CSIRO', country='澳大利亚', url='https://jobs.csiro.au/search/?q=postdoctoral', pages=2, parser=csiro, scope='关键词 postdoctoral，最多两页'),
    dict(id='yale', name='Yale University', country='美国', url='https://postdocs.yale.edu/applicants/open-positions', pages=4, parser=yale, scope='公开机会，最多四页；仅保留博后标题'),
    dict(id='stanford', name='Stanford University', country='美国', url='https://postdocs.stanford.edu/prospective/opportunities', pages=2, parser=stanford, scope='公开博后列表，最多两页'),
]

class Client:
    def __init__(self, source):
        self.host = urlsplit(source['url']).hostname
        self.delay = 1.0
        self.last = 0
        self.robot = RobotFileParser()
        robots = self.raw('https://' + self.host + '/robots.txt')
        self.robot.parse(robots.lstrip('\ufeff').splitlines())
        self.delay = max(1.0, self.robot.crawl_delay('PostdocFinder') or self.robot.crawl_delay('*') or 1)

    def raw(self, url):
        if urlsplit(url).scheme != 'https' or urlsplit(url).hostname != self.host:
            raise ValueError('Only same-host HTTPS requests are allowed')
        time.sleep(max(0, self.last + self.delay - time.monotonic()))
        self.last = time.monotonic()
        with urlopen(Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'text/html,text/plain'}), timeout=25) as r:
            if urlsplit(r.url).hostname != self.host:
                raise ValueError('Unexpected cross-host redirect')
            return r.read(5_000_000).decode('utf-8', errors='replace')

    def get(self, url):
        if not self.robot.can_fetch('PostdocFinder', url):
            raise ValueError('Source robots.txt excludes this URL')
        return self.raw(url)

def next_page(doc, url, host):
    for link in doc.all('a'):
        a = link.attrs
        if ('next' in a.get('rel', '').split() or a.get('title','').lower() in {'go to next page', 'next page', 'more jobs'}
                or link.text().lower().startswith('more jobs')):
            target = urljoin(url, a.get('href', ''))
            if urlsplit(target).hostname == host:
                return target
    return None

def collect(source, now):
    state = dict(id=source['id'], name=source['name'], url=source['url'], scope=source['scope'], attempted_at=now, pages_read=0)
    rows, recognized = [], 0
    try:
        client = Client(source)
        url, visited = source['url'], set()
        for _ in range(source['pages']):
            if not url or url in visited:
                break
            visited.add(url)
            doc = Document(client.get(url)).root
            found, count = source['parser'](doc, source)
            if not count:
                raise ValueError('Listing structure not recognized; previous cache retained')
            recognized += count
            rows.extend(found)
            state['pages_read'] += 1
            url = next_page(doc, url, client.host)
        state.update(status='ok', count=len({r['id'] for r in rows}), observed_at=now)
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
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, default=ROOT/'web/data/jobs.json')
    p.add_argument('--use-published-cache', action='store_true')
    args = p.parse_args()
    previous = json.loads(args.out.read_text(encoding='utf-8')) if args.out.exists() else {}
    if args.use_published_cache:
        try:
            cache_url = 'https://tylerzhang130666.github.io/global-postdoc-finder/data/jobs.json'
            with urlopen(Request(cache_url, headers={'User-Agent': USER_AGENT}), timeout=20) as response:
                cached = json.loads(response.read(5_000_000))
            if (cached.get('schema_version') == 'postdoc-jobs/1' and isinstance(cached.get('jobs'), list)
                    and cached.get('generated_at', '') > previous.get('generated_at', '')):
                previous = cached
        except Exception:
            print('Published cache unavailable; using repository snapshot')
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    with ThreadPoolExecutor(max_workers=3) as pool:
        batches = list(pool.map(lambda s: collect(s, now), SOURCES))
    data = combine(previous, batches, now)
    for s in data['sources']:
        print(f'{s["id"]}: {s["status"]}, {s["count"]} jobs, {s["pages_read"]} pages' + (': '+s['error'] if 'error' in s else ''))
    if not any(s['status']=='ok' for s in data['sources']) and not previous:
        raise SystemExit('No usable source and no previous index; refusing an empty deployment')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temp = args.out.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    temp.replace(args.out)
    print(f'{len(data["jobs"])} indexed jobs')

if __name__ == '__main__':
    main()
