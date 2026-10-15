# 구글드라이브 공개 기출 폴더(모의고사 기출, 대수능 기출)를 훑어 files.json 을 만듭니다.
# 파일 크기는 기존 catalog.json 값을 재사용하고, 새 파일만 다운로드 주소에 Range 요청으로 확인합니다.
import json, re, html, os, urllib.request, concurrent.futures as cf

ROOTS = {'모의고사': '1D5CHVcncu1G1hUzoSR2iJFNMB8H0rsQ8', '대수능': '1p5BG3oPRZxfi8xfyvMhAHsVAlTAGH4dB'}
UA = {'User-Agent': 'Mozilla/5.0'}
RE = re.compile(r'<div class="flip-entry" id="entry-([\w-]+)"[\s\S]*?<a href="([^"]+)"[\s\S]*?<div class="flip-entry-title">([^<]*)</div>')

def get(url, headers=None, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={**UA, **(headers or {})})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r
        except Exception as e:
            err = e
    raise err

def listing(fid):
    for i in range(3):
        try:
            req = urllib.request.Request(f'https://drive.google.com/embeddedfolderview?id={fid}', headers=UA)
            t = urllib.request.urlopen(req, timeout=40).read().decode('utf-8', 'replace')
            return [(m[0], html.unescape(m[2]).strip(), '/folders/' in m[1]) for m in RE.findall(t)]
        except Exception:
            pass
    print('목록 실패', fid); return []

def walk():
    out, level = [], [(fid, [name]) for name, fid in ROOTS.items()]
    with cf.ThreadPoolExecutor(12) as ex:
        while level:
            res = list(ex.map(lambda x: listing(x[0]), level))
            nxt = []
            for (fid, path), items in zip(level, res):
                for iid, name, folder in items:
                    if folder: nxt.append((iid, path + [name]))
                    elif name.lower().endswith('.pdf'): out.append(dict(id=iid, title=name, path=path))
            level = nxt
    return out

def size_of(fid):
    for i in range(3):
        try:
            req = urllib.request.Request(f'https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t', headers={**UA, 'Range': 'bytes=0-0'})
            with urllib.request.urlopen(req, timeout=40) as r:
                cr = r.headers.get('Content-Range') or ''
                m = re.search(r'/(\d+)$', cr)
                if m: return int(m.group(1))
                return int(r.headers.get('Content-Length') or 0)
        except Exception:
            pass
    return 0

files = walk()
known = {}
if os.path.exists('catalog.json'):
    known = {r['id']: r.get('size', 0) for r in json.load(open('catalog.json'))}
need = [f for f in files if not known.get(f['id'])]
with cf.ThreadPoolExecutor(16) as ex:
    sizes = dict(zip([f['id'] for f in need], ex.map(lambda f: size_of(f['id']), need)))
for f in files:
    f['size'] = known.get(f['id']) or sizes.get(f['id'], 0)
json.dump(files, open('files.json', 'w'), ensure_ascii=False)
print('files', len(files), 'new size lookups', len(need))
