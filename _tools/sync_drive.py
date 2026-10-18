# 구글드라이브 공개 기출 폴더(모의고사 기출, 대수능 기출)를 훑어 files.json 을 만듭니다.
# 파일 크기는 기존 catalog.json 값을 재사용하고, 새 파일만 다운로드 주소에 Range 요청으로 확인합니다.
import json, re, html, os, unicodedata, urllib.request, concurrent.futures as cf

ROOTS = {'모의고사': '1D5CHVcncu1G1hUzoSR2iJFNMB8H0rsQ8', '대수능': '1p5BG3oPRZxfi8xfyvMhAHsVAlTAGH4dB'}
VROOTS = {'변형문제': '1e0D-eA_TOZ-4_wPEKlWDnoG-SGu2bXkS'}  # 모의고사 변형문제 (크기 확인 없이 목록만)
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

def walk(roots=ROOTS):
    out, level = [], [(fid, [name]) for name, fid in roots.items()]
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
var = walk(VROOTS)
json.dump(var, open('variants.json', 'w'), ensure_ascii=False)
print('variants', len(var))
# 분석노트·단어 폴더 (목록만): 자료실 영어 페이지의 번호 버튼·단어장 연결에 사용
# 분석노트 폴더는 비공개(원장님 Apps Script 가 관리) → Apps Script 의 '공개 목록'(바로 보기 파일만)을 받음
# 30~40번·부교재 분석노트 주소는 여기(공개 저장소)에 절대 남기지 않음
GAS_URL = ''  # Apps Script 웹 앱 주소 (…/exec)
WORD_ROOTS = {'모의고사 단어': '1Apb5ZT_Fb1jQoV1-Otj9oWUqeNVsfmNj', '부교재 단어': '1Lq_Ps0Hp6VPsfFLVQwlGzh52DFBzgL9_'}
NOTE_ROOTS = {'모의고사 분석노트': '1jSEPdOdM4RD7GplBWwF3jiRKFWToBOBq', '부교재 분석노트': '1vg17CVTqjIRk-hdoA3PhrJ1RTUn84lSO'}
KEEP_PUBLIC = {'105f20gSuhZvR44gCK6oW5mxn2-ZFG12J'}  # 부교재 샘플
def is_public(x):  # Apps Script 의 isPublic 과 같은 규칙: 모의고사 30~40번·부교재 분석노트는 비공개
    t = unicodedata.normalize('NFC', x['title'])
    if x['id'] in KEEP_PUBLIC: return True
    if unicodedata.normalize('NFC', x['path'][0]) == '부교재 분석노트': return False
    if re.search('문제|정답|해설|듣기', t): return True
    ns = [(int(a), int(b or a)) for a, b in re.findall(r'(\d{1,2})\s*(?:[-~]\s*(\d{1,2}))?\s*번', t)]
    m = re.match(r'^(\d{1,2})(?:\s*[-~]\s*(\d{1,2}))?\s*\.pdf$', t, re.I)
    if m: ns.append((int(m.group(1)), int(m.group(2) or m.group(1))))
    return bool(ns) and all(b < 30 or a > 40 for a, b in ns)
ext = walk(WORD_ROOTS)
if not GAS_URL:  # Apps Script 연결 전: 공개 폴더 목록에서 공개 파일만 남김
    ext += [x for x in walk(NOTE_ROOTS) if is_public(x)]
else:
    try:
        with urllib.request.urlopen(urllib.request.Request(GAS_URL + '?action=catalog', headers=UA), timeout=120) as r:
            ext += json.loads(r.read().decode('utf-8'))['files']
    except Exception as e:
        print('분석노트 공개 목록 실패 — 기존 목록 유지', e)
        old = json.load(open('extras.json')) if os.path.exists('extras.json') else []
        ext += [x for x in old if x['path'][0] in NOTE_ROOTS and is_public(x)]
json.dump(ext, open('extras.json', 'w'), ensure_ascii=False)
print('extras', len(ext))
print('files', len(files), 'new size lookups', len(need))
