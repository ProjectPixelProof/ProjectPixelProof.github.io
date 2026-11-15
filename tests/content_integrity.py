"""Check manuscript bindings and local navigation without executing research code."""
import argparse, hashlib, json, sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_method_extras import abstract_content
from build_paper_content import rows
class Page(HTMLParser):
    def __init__(self):
        super().__init__();self.ids=[];self.links=[];self.assets=[];self.h1=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if tag=='a' and 'href' in a:self.links.append(a['href'])
        if tag in ('script','link'):
            value=a.get('src') or a.get('href','')
            if value.startswith('static/'):self.assets.append(value)
        if tag=='h1':self.h1+=1
parser=argparse.ArgumentParser();parser.add_argument('--paper',type=Path,required=True);args=parser.parse_args()
for item in json.loads((ROOT/'data/paper-content-provenance.json').read_text())['excerptsAndImages']:
    p=ROOT/item['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
    if 'text' in item:assert '\n'.join(p.read_text().splitlines()[item['startLine']-1:item['endLine']])==item['text']
for key,table in json.loads((ROOT/'data/paper-tables.json').read_text()).items():
    assert table['rows']==rows((args.paper/table['source']).read_text(),table['label']),key
abstract=json.loads((ROOT/'data/paper-abstract.json').read_text())
assert abstract['text']==abstract_content((args.paper/abstract['source']).read_text())
assert 'Project page:' not in abstract['text']
assert '\\todo{' not in abstract['text']
pages={}
for p in ROOT.glob('*.html'):
    parsed=Page();text=p.read_text();parsed.feed(text);pages[p.name]=parsed
    assert parsed.h1==1,p.name
    assert len(parsed.ids)==len(set(parsed.ids)),p.name
    assert not any(marker in text for marker in ("googletagmanager.com", "google-analytics.com", "gtag(", "G-8KT0DEBR8Z")),p.name
    assert '{{' not in text,p.name
    for asset in parsed.assets:
        u=urlsplit(asset);file=ROOT/u.path
        assert file.is_file(),asset
        if file.suffix in ('.css','.js'):
            assert u.query=='v='+hashlib.sha256(file.read_bytes()).hexdigest()[:12],asset
for name,page in pages.items():
    for link in page.links:
        u=urlsplit(link)
        if u.scheme or u.netloc:continue
        target=u.path or name
        assert (ROOT/target).exists(),(name,link)
        if target not in pages or not u.fragment or '=' in u.fragment:continue
        fragment=unquote(u.fragment)
        if target=='steering-gallery.html' and 'support-'+fragment in pages[target].ids:continue
        assert fragment in pages[target].ids,(name,link)
print('PASS: manuscript tables and abstract; exact code/image provenance; local files and fragments; unique headings/IDs; analytics; versioned assets.')
