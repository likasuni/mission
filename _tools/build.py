#!/usr/bin/env python3
"""리카수니 자료실 정적 페이지 생성기

_tools/catalog.json (구글드라이브 기출 PDF 목록)을 읽어
홈 / 학년 / 회차 / 과목 페이지와 sitemap.xml 을 저장소 루트에 만든다.
자료가 추가되면 catalog.json 만 갱신하고 다시 실행하면 된다.
"""
import json, os, html, datetime, collections, shutil, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://data.likasuni.com'
ADS_CLIENT = 'ca-pub-3951386769813957'
AD_SLOT = '8157681795'          # data자료실_섹션사이_반응형 (자료실 전용, 2026-10-16)
GA_ID = 'G-J12SZ4Z4K7'  # 구글 애널리틱스(GA4) 속성 '리카수니 자료실' (2026-10-19)
GA = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>'
      f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA_ID}');</script>")
TODAY = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat()  # 한국 시간

SLUG = {'국어': 'kor', '수학': 'math', '수학 가형': 'math-ga', '수학 나형': 'math-na', '영어': 'eng',
        '한국사': 'history', '통합사회': 'social', '통합과학': 'science',
        '생활과윤리': 'ethics', '윤리와사상': 'ethics-thought', '한국지리': 'korean-geo', '세계지리': 'world-geo',
        '동아시아사': 'east-asia', '세계사': 'world-history', '경제': 'economics', '정치와법': 'politics-law',
        '사회문화': 'society-culture', '물리학1': 'physics1', '물리학2': 'physics2', '화학1': 'chem1', '화학2': 'chem2',
        '생명과학1': 'bio1', '생명과학2': 'bio2', '지구과학1': 'earth1', '지구과학2': 'earth2'}
DISP = {'물리학1': '물리학Ⅰ', '물리학2': '물리학Ⅱ', '화학1': '화학Ⅰ', '화학2': '화학Ⅱ', '생명과학1': '생명과학Ⅰ',
        '생명과학2': '생명과학Ⅱ', '지구과학1': '지구과학Ⅰ', '지구과학2': '지구과학Ⅱ', '생활과윤리': '생활과 윤리',
        '윤리와사상': '윤리와 사상', '정치와법': '정치와 법', '사회문화': '사회·문화'}
GROUP_ORDER = ['국어', '수학', '영어', '한국사', '사회', '과학', '사회탐구', '과학탐구']
GROUP_NAME = {'사회': '통합사회', '과학': '통합과학', '기타': '전과목 정답·해설'}
SUBJ_ORDER = list(SLUG)
KIND_ORDER = ['문제', '해설', '정답', '듣기대본']
KIND_LABEL = {'문제': '문제지', '해설': '해설', '정답': '정답표', '듣기대본': '듣기대본'}

e = html.escape
def dname(s): return DISP.get(s, s)
def view(i): return f'https://drive.google.com/file/d/{i}/view'
def down(i): return f'https://drive.google.com/uc?export=download&id={i}'
def mb(n): return f'{n/1048576:.1f}MB' if n else ''

R = json.load(open(os.path.join(ROOT, '_tools', 'catalog.json')))
import re as _re
# 스타일을 페이지 안에 직접 넣어 첫 화면 표시를 앞당김 (별도 파일 요청 1회 절약)
CSS = _re.sub(r'\s+', ' ', _re.sub(r'/\*.*?\*/', '', open(os.path.join(ROOT, 'style.css')).read(), flags=_re.S))
CSS = _re.sub(r'\s*([{};:,>])\s*', r'\1', CSS).strip()
INFO = json.load(open(os.path.join(ROOT, '_tools', 'exam_info.json')))

# 리카수니 변형문제 (드라이브 '모의고사 변형문제' 폴더, sync_drive.py 가 variants.json 으로 저장)
VAR = collections.defaultdict(list)
_vp = os.path.join(ROOT, '_tools', 'variants.json')
for v in (json.load(open(_vp)) if os.path.exists(_vp) else []):
    t = v['title']
    _ex = r'(\d{4})\s*(년|학년도)[\s_]*(\d{1,2})\s*월[\s_]*고\s*(\d)'
    m = _re.search(_ex, t) or _re.search(_ex, v['path'][-1])  # 파일명에 회차가 없으면(예: 18번_변형문제.pdf) 폴더 이름에서
    nm = _re.search(r'[_\s](\d{1,2}(?:\s*[~-]\s*\d{1,2})?)\s*번', '_' + t)
    if not m or not nm: continue
    y, mo, g = int(m.group(1)), int(m.group(3)), int(m.group(4))
    if g == 3 and mo in (6, 9) and m.group(2) == '년': y += 1  # 고3 모의평가는 학년도 기준 회차로
    VAR[('moe', g, y, mo)].append((nm.group(1).replace(' ', '').replace('-', '~'), v['id']))
def vkey(n): return int(_re.match(r'\d+', n).group())

# 문항별 해설 글 (_tools/posts/*.json) — 원장님이 자료를 주면 Claude 가 JSON 으로 써서 올림
POSTS = []
_pd = os.path.join(ROOT, '_tools', 'posts')
for _f in sorted(os.listdir(_pd)) if os.path.isdir(_pd) else []:
    if not _f.endswith('.json'): continue
    _p = json.load(open(os.path.join(_pd, _f)))
    if _p['date'] > TODAY: continue  # 예약 글: date 날짜 새벽 빌드(drive-sync) 때 공개
    _x = _p['exam'].split('-')  # sn-2022 / moe-1-2026-9
    _p['k'] = ('sn', 0, int(_x[1]), 0) if _x[0] == 'sn' else ('moe', int(_x[1]), int(_x[2]), int(_x[3]))
    _p['subj'] = _p.get('subj', '영어')
    _p['qs'] = _p.get('qs') or [_p]  # 장문 세트(41~42 등)는 qs 에 문항별 정답·근거·선택지
    POSTS.append(_p)
POSTS.sort(key=lambda p: (p['date'], p['n']), reverse=True)
POSTS_BY = collections.defaultdict(list)
for _p in POSTS: POSTS_BY[_p['k']].append(_p)
CIRC = '①②③④⑤'
def post_no(p): return f"{p['n']}~{p['n2']}" if p.get('n2') else str(p['n'])
def post_url(p): return subj_url(p['k'], p['subj']) + (f"{p['n']}-{p['n2']}/" if p.get('n2') else f"{p['n']}/")
def post_name(p): return f"{s_name(p['k'])} {dname(p['subj'])} {post_no(p)}번"
def post_ans(p):
    if p.get('n2'): return ' · '.join(f"{q['n']}번 {CIRC[q['answer'] - 1]}" for q in p['qs'])
    return f"정답 {CIRC[p['answer'] - 1]}"
def post_card(ps, title):
    return (f'<div class="card" id="posts"><h2>{e(title)}</h2><div class="plist">' + ''.join(
        f'<a href="{post_url(p)}"><b>{e(post_name(p))}</b><span>{post_ans(p)} · {e(p["type"])} · {e(p["topic"])}</span></a>' for p in ps)
        + '</div></div>')


def skey(t):  # 제목·폴더 이름에서 회차 (moe, 학년, 연도, 월)
    m = _re.search(r'(\d{4})\s*(년|학년도)[\s_]*(\d{1,2})\s*월[\s_]*고\s*(\d)', t)
    if not m: return None
    y, mo, g = int(m.group(1)), int(m.group(3)), int(m.group(4))
    if g == 3 and mo in (6, 9) and m.group(2) == '년': y += 1
    return ('moe', g, y, mo)

# 분석노트(18~29·41~45 공개, 30~40 카톡 요청) · 모의고사 단어 · 부교재 단어 (sync_drive.py → extras.json)
NOTES = collections.defaultdict(dict); WORDS = {}; BWORDS = collections.defaultdict(list)
_xp = os.path.join(ROOT, '_tools', 'extras.json')
import unicodedata as _ud
for x in (json.load(open(_xp)) if os.path.exists(_xp) else []):
    x['title'] = _ud.normalize('NFC', x['title']); x['path'] = [_ud.normalize('NFC', q) for q in x['path']]  # 맥에서 올린 이름(NFD) 보정
    t, p0 = x['title'], x['path'][0]
    if not t.lower().endswith('.pdf'): continue
    if p0 == '모의고사 분석노트':
        if _re.search('문제|정답|해설|듣기', t): continue  # 같은 폴더의 시험지 원본은 제외
        k = skey(' '.join(x['path'][1:])) or skey(t)
        nm = (_re.search(r'(?<!\d)(\d{1,2})\s*(?:[-~]\s*(\d{1,2}))?\s*번', t)  # '..._30번.pdf', '41-42번'
              or _re.match(r'^(\d{1,2})(?:\s*[-~]\s*(\d{1,2}))?\s*\.pdf$', t))  # '30.pdf', '41-42.pdf'
        if k and nm: NOTES[k][nm.group(1) + ('~' + nm.group(2) if nm.group(2) else '')] = x['id']
    elif p0 == '모의고사 단어':
        k = skey(t)
        if k: WORDS[k] = x['id']
    elif p0 == '부교재 단어':
        BWORDS[x['path'][1] if len(x['path']) > 1 else '기타'].append((t, x['id']))
NOTE_NUMS = [str(i) for i in range(18, 41)] + ['41~42', '43~45']
def is_req(n): return 30 <= vkey(n) <= 40   # 30~40번은 카톡 요청(최근 업데이트 자료)

def ikey(k):
    ex, g, y, m = k
    return f'moe-{g}-{y}-{m}' if ex == 'moe' else f'sn-{y}'

def cut_table(rows):
    if not rows: return ''
    n = max([len(r.get('c', r.get('abs', []))) for r in rows] + [1])
    n = max(n, 1)
    head = ''.join(f'<th>{i + 1}등급</th>' for i in range(n))
    has_max = any('max' in r for r in rows)
    has_r1 = any('r1' in r or 'rates' in r for r in rows)
    body = ''
    for r in rows:
        cells = ''
        if 'abs' in r:
            rt = r.get('rates', [])
            for i in range(n):
                if i < len(r['abs']):
                    sub = (f'<small>{rt[i]}%{" 누적" if i else ""}</small>' if i < len(rt) else '')
                    cells += f'<td>{r["abs"][i]}{sub}</td>'
                else:
                    cells += '<td>–</td>'
            basis = '원점수(절대평가)'
            r1 = f'{rt[0]}%' if rt else '–'
        elif 'c' in r:
            cells = ''.join(f'<td>{r["c"][i]:g}</td>' if i < len(r['c']) else '<td>–</td>' for i in range(n))
            basis = r.get('basis', '')
            r1 = r.get('r1', '–')
        else:
            cells = '<td>–</td>' * n
            basis = ''
            r1 = r.get('r1', '–')
        body += (f'<tr><th>{e(dname(r["s"]))}<small>{e(basis)}</small></th>{cells}'
                 + (f'<td>{r.get("max", "–")}</td>' if has_max else '') + (f'<td>{r1}</td>' if has_r1 else '') + '</tr>')
    return (f'<div class="cut-wrap"><table class="cut"><thead><tr><th>과목</th>{head}'
            + ('<th>표준점수<br>최고점</th>' if has_max else '') + ('<th>1등급<br>비율</th>' if has_r1 else '')
            + f'</tr></thead><tbody>{body}</tbody></table></div>')

CUT_NOTE = '<p class="note">교육청·평가원 채점 결과 기준이에요. 절대평가 과목은 등급별 비율(누적)을 함께 적었어요. 학습 참고용이며, 정확한 성적은 개인 성적표를 확인하세요.</p>'

# ---------- 회차(session) 묶기 ----------
sessions = collections.OrderedDict()
for r in R:
    if r['exam'] == 'moe':
        k = ('moe', r['grade'], r['year'], r['month'])
    else:
        k = ('sn', 0, r['year'], 0)
    sessions.setdefault(k, []).append(r)

def s_url(k):
    ex, g, y, m = k
    return f'/moe/go{g}/{y}-{m:02d}/' if ex == 'moe' else f'/suneung/{y}/'

def s_name(k, short=False):
    ex, g, y, m = k
    if ex == 'moe':
        if g == 3 and m in (6, 9):  # 평가원 모의평가는 학년도 기준 (폴더 연도 = 학년도, 시행은 전년도)
            return f'{y}학년도 {m}월 모의평가(고3)' if not short else f'{y}학년도 {m}월 모평'
        return f'{y}년 {m}월 고{g} 모의고사' if not short else f'{m}월'
    return f'{y}학년도 수능'

def s_org(k):
    ex, g, y, m = k
    if ex == 'sn': return '한국교육과정평가원 (대학수학능력시험)'
    if g == 3 and m in (6, 9): return '한국교육과정평가원 (모의평가)'
    return '시·도교육청 (전국연합학력평가)'

def s_when(k):
    ex, g, y, m = k
    if ex == 'sn': return '2020년 12월 시행' if y == 2021 else f'{y - 1}년 11월 시행'
    if g == 3 and m in (6, 9): return f'{y - 1}년 {m}월 시행'
    return f'{y}년 {m}월 시행'

import hashlib
def sslug(s): return SLUG.get(s) or ('all' if s == '전과목' else 'x-' + hashlib.md5(s.encode()).hexdigest()[:6])  # 제2외국어·직업탐구 등
def subj_url(k, s): return s_url(k) + sslug(s) + '/'

def bysubj(rs):
    d = collections.OrderedDict()
    for s in sorted({r['subject'] for r in rs}, key=lambda x: (SUBJ_ORDER.index(x) if x in SUBJ_ORDER else 99, x)):  # 이름으로 동점 정렬 → 빌드마다 순서 고정
        d[s] = sorted([r for r in rs if r['subject'] == s], key=lambda r: KIND_ORDER.index(r['kind']))
    return d

# ---------- 공통 레이아웃 ----------
NAV = [('/', '홈'), ('/english/', '영어 모의고사'), ('/posts/', '수업자료'), ('/books/', '부교재'), ('/naesin/', '코코스학원'), ('/exams/', '전과목 기출'), ('/notes/', '분석노트 요청')]  # 코코스학원 = 학교별 내신 분석 + 학원 소식

def ad():
    return (f'<div class="ad-slot"><ins class="adsbygoogle" style="display:block" data-ad-client="{ADS_CLIENT}" '
            f'data-ad-slot="{AD_SLOT}" data-ad-format="auto" data-full-width-responsive="true"></ins>'
            f'<script>(adsbygoogle=window.adsbygoogle||[]).push({{}});</script></div>')

# 학년별 부교재 쿠팡 상자 (_tools/coupang.json, url 있는 책만 표시)
COUPANG = json.load(open(os.path.join(ROOT, '_tools', 'coupang.json'), encoding='utf-8'))
def cp_box(k):
    g = f'go{k[1]}' if k[0] == 'moe' else 'go3'
    bs = [b for b in COUPANG.get(g, []) if b.get('url')]
    if not bs: return ''
    who = '수능' if k[0] == 'sn' else f'고{k[1]}'
    return (f'<div class="card cp-box"><h2>📘 {who} 부교재 구매하기</h2>'
            '<p class="cp-dis">이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p><div class="cp-list">'
            + ''.join(f'<a href="{e(b["url"])}" target="_blank" rel="sponsored nofollow noopener"><b>🛒 {e(b["name"])}</b>'
                      + (f'<small>{e(b["note"])}</small>' if b.get('note') else '') + '</a>' for b in bs)
            + '</div><p class="cp-dis">구매 버튼은 쿠팡 상품 페이지로 연결돼요.</p></div>')

def page(path, title, desc, body, crumbs=(), active='/', comments=None, extra_ld=(), og_type='website', og_image=None):
    url = SITE + path
    ld = list(extra_ld) + ([{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u} for i, (u, n) in enumerate(crumbs)]}] if crumbs else [])
    crumb_html = ('<nav class="crumb">' + ' › '.join(f'<a href="{u}">{e(n)}</a>' for u, n in crumbs) + '</nav>') if crumbs else ''
    act = '/exams/' if (active.startswith('/moe/') or active == '/suneung/') else ('/english/' if active == '/variants/' else ('/naesin/' if active == '/news/' else active))  # 학년별·수능 페이지는 '기출문제' 메뉴에 불이 들어옴
    nav = ''.join(f'<a href="{u}" class="{"on " if u == act else ""}">{n}</a>' for u, n in NAV)
    cm = ''
    if comments:
        cm = f'<section class="card" id="comments" data-page-key="{e(comments[0])}" data-page-title="{e(comments[1])}"><h2>댓글</h2><p class="muted">댓글 불러오는 중...</p></section>'
    out = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="리카수니 자료실">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{og_image or SITE + '/og.png'}">
<meta name="google-site-verification" content="BckdSBCPVseYvq2HonB5Q7G9pfCOG10GZvoCOIoK4sk">
<meta name="naver-site-verification" content="7e1745db79feaa04ab25201be2de4645c4641c34">
<link rel="icon" href="/favicon.png">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/img/icon-180.png">
<meta name="theme-color" content="#172556">
<style>{CSS}</style>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADS_CLIENT}" crossorigin="anonymous"></script>
{GA}
{''.join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)}
</head>
<body>
<header class="top"><div class="top-in"><a class="brand" href="/">리카수니 <b>자료실</b></a><div class="top-r"><button class="push-btn push-ic" type="button" title="새 자료 알림 받기" aria-label="새 자료 알림 받기">🔔</button><a class="hdr-cta" href="/notes/">분석노트 요청</a><div class="auth" id="auth"><button class="btn btn-gold btn-sm" onclick="lazyLogin()">로그인</button></div></div></div></header>
<nav class="nav"><div class="nav-in">{nav}</div></nav>
<main class="wrap">
{crumb_html}
{body}
{cm}
</main>
<footer>
© 리카수니 자료실 · <a href="https://www.likasuni.com" target="_blank" rel="noopener">리카수니 블로그</a>
<a href="/privacy.html">개인정보처리방침</a> <a href="/admin.html" rel="nofollow">관리자</a>
<div class="biz">기출문제 저작권은 한국교육과정평가원·각 시도교육청에 있으며, 학습 목적으로 공개 자료를 정리해 제공합니다.<br>상호: 리카수니</div>
</footer>
<script src="/push.js?v=4" defer></script>
<script>
/* 로그인·댓글 기능은 필요할 때만 불러옴: 로그인했던 회원 / 댓글 영역 근처까지 스크롤 / 로그인 버튼 클릭 */
(function () {{
  var done = false, after = null, srcs = ['https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.58.0/dist/umd/supabase.js', '/common.js?v=4', '/lib.js?v=39'];
  function next(i) {{ if (i >= srcs.length) {{ if (after) after(); return; }} var s = document.createElement('script'); s.src = srcs[i]; s.onload = function () {{ next(i + 1); }}; document.body.appendChild(s); }}
  function go() {{ if (!done) {{ done = true; next(0); }} }}
  window.lazyLogin = function () {{ after = function () {{ showLogin(); }}; if (done) {{ if (window.showLogin) showLogin(); }} else go(); }};
  /* 광고 차단으로 광고 스크립트 자체가 안 불러와졌을 때만 확보해 둔 자리를 접음 */
  addEventListener('load', function () {{ setTimeout(function () {{ if (window.adsbygoogle && window.adsbygoogle.loaded) return; document.querySelectorAll('.ad-slot').forEach(function (d) {{ d.style.display = 'none'; }}); }}, 8000); }});
  var had = false; try {{ had = !!localStorage.getItem('sb-iiyhmskvdjgstoikonwu-auth-token'); }} catch (e) {{}}
  if (had || location.hash.indexOf('access_token') > -1) {{ go(); return; }}
  var els = ['note-req', 'comments', 'recent-cmt', 'talk', 'ns-member'].map(function (id) {{ return document.getElementById(id); }}).filter(Boolean);
  if (els.length && 'IntersectionObserver' in window) {{
    var io = new IntersectionObserver(function (es) {{ if (es.some(function (x) {{ return x.isIntersecting; }})) {{ io.disconnect(); go(); }} }}, {{ rootMargin: '600px' }});
    els.forEach(function (el) {{ io.observe(el); }});
  }}
}})();
</script>
</body>
</html>
'''
    fp = os.path.join(ROOT, path.lstrip('/'), 'index.html') if path.endswith('/') else os.path.join(ROOT, path.lstrip('/'))
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, 'w').write(out)
    PAGES.append(path)

PAGES = []
LASTMOD = {}  # 사이트맵 lastmod: 실제 날짜를 아는 페이지(해설)만 넣음

def dl_buttons(rs):
    return '<div class="dl">' + ''.join(
        f'<a href="{view(r["id"])}" target="_blank" rel="noopener">{KIND_LABEL[r["kind"]]}</a>' for r in rs) + '</div>'

def session_list(keys):
    by_year = collections.OrderedDict()
    for k in sorted(keys, key=lambda k: (-k[2], k[3])):
        by_year.setdefault(k[2], []).append(k)
    h = ''
    for y, ks in by_year.items():
        h += f'<h3 class="year">{y}년</h3><div class="chips">' + ''.join(
            f'<a class="chip" href="{s_url(k)}">{s_name(k, True)}<small>{len(bysubj(sessions[k]))}과목</small></a>' for k in ks) + '</div>'
    return h

# ---------- 폴더 정리 (이전 생성물 삭제) ----------
for d in ('moe', 'suneung'):
    shutil.rmtree(os.path.join(ROOT, d), ignore_errors=True)

# ---------- 회차 · 과목 페이지 ----------
keys_sorted = sorted(sessions, key=lambda k: (k[0], k[1], k[2], k[3]))
for idx, k in enumerate(keys_sorted):
    rs = sessions[k]; subs = bysubj(rs); name = s_name(k)
    same = [x for x in keys_sorted if x[0] == k[0] and x[1] == k[1]]
    i = same.index(k); prev_k = same[i - 1] if i > 0 else None; next_k = same[i + 1] if i + 1 < len(same) else None
    if k[0] == 'moe':
        crumbs = [('/', '홈'), (f'/moe/go{k[1]}/', f'고{k[1]} 모의고사'), (s_url(k), name)]; active = f'/moe/go{k[1]}/'
    else:
        crumbs = [('/', '홈'), ('/suneung/', '수능 기출'), (s_url(k), name)]; active = '/suneung/'

    # 회차 페이지
    groups = collections.OrderedDict()
    for s, xs in subs.items():
        groups.setdefault(xs[0]['group'], []).append((s, xs))
    rows = ''
    core = [g for g in GROUP_ORDER[:6] if g in groups]
    blocks = ([('주요 과목', core)] if core else []) + [(GROUP_NAME.get(g, g), [g]) for g in ('사회탐구', '과학탐구', '직업탐구', '제2외국어·한문', '기타') if g in groups]
    for label, gs in blocks:
        rows += f'<div class="card"><p class="grp">{e(label)}</p>'
        for g in gs:
            for s, xs in groups[g]:
                rows += f'<div class="subj"><a class="nm" href="{subj_url(k, s)}">{e(dname(s))}</a>{dl_buttons(xs)}</div>'
        rows += '</div>'
    sub_names = ', '.join(dname(s) for s in subs)
    inf = INFO.get(ikey(k), {})
    note_banner = ''
    if k[0] == 'moe' and '영어' in subs:
        note_banner = (f'<a class="banner note" href="/notes/?y={k[2]}&m={k[3]}&g={k[1]}"><b>이 회차 영어 문항별 분석노트, 카톡으로 받기</b>'
                       '<p>번호만 고르면 카카오톡으로 바로 보내드려요. 하루 모의고사 2개 · 부교재 1개 · 링크 24시간</p></a>')
    info_html = ''
    if inf.get('summary'):
        info_html += '<div class="card"><h2>시험 요약</h2>' + (f'<p class="muted">{e(inf["date"])}</p>' if inf.get('date') else '') + \
                     '<ul class="sum">' + ''.join(f'<li>{e(x)}</li>' for x in inf['summary']) + '</ul></div>'
    if inf.get('rows'):
        info_html += f'<div class="card"><h2>{e(name)} 등급컷</h2>{cut_table(inf["rows"])}{CUT_NOTE}</div>'
    else:
        info_html += '<div class="card"><h2>등급컷</h2><p class="muted">확정 등급컷을 정리하고 있어요. 확인되는 대로 업데이트할게요.</p></div>'
    if inf.get('wrong'):
        info_html += '<div class="card"><h2>오답이 많았던 문항</h2><table class="info">' + ''.join(
            f'<tr><th>{e(dname(x))}</th><td>{e(v)}</td></tr>' for x, v in inf['wrong'].items()) + '</table></div>'
    pn = '<div class="pn">' + (f'<a href="{s_url(prev_k)}">← {s_name(prev_k)}</a>' if prev_k else '<span></span>') + \
         (f'<a href="{s_url(next_k)}">{s_name(next_k)} →</a>' if next_k else '<span></span>') + '</div>'
    body = f'''<h1 class="page-h1">{e(name)} 기출문제·정답·해설 PDF</h1>
<p class="lead">{e(name)} 전과목({len(subs)}과목) 문제지와 정답·해설을 무료로 내려받을 수 있어요.</p>
{note_banner}
<div class="card"><table class="info">
<tr><th>시행</th><td>{s_when(k)}</td></tr>
<tr><th>주관</th><td>{s_org(k)}</td></tr>
<tr><th>과목</th><td>{e(sub_names)}</td></tr>
</table></div>
{info_html}
{rows}
{ad()}
{pn}'''
    page(s_url(k), f'{name} ' + ('등급컷 · ' if inf.get('rows') else '') + '전과목 기출문제·정답·해설 PDF | 리카수니 자료실',
         f'{name} 전과목 기출문제 PDF 무료 다운로드와 ' + ('등급컷·시험 요약. ' if inf else '') + f'{sub_names} 문제지·정답·해설. 리카수니 자료실', body, crumbs, active,
         comments=(s_url(k).strip('/'), name))

    # 과목 페이지
    for s, xs in subs.items():
        sn = dname(s); full = f'{name} {sn}'
        files = ''.join(f'''<div class="file"><div><div class="t">{e(full)} {KIND_LABEL[r["kind"]]}</div><div class="s">PDF {mb(r.get("size", 0))}</div></div>
<div class="dl"><a href="{view(r["id"])}" target="_blank" rel="noopener">미리보기</a><a href="{down(r["id"])}" rel="noopener">다운로드</a></div></div>''' for r in xs)
        extra = ''
        en_top = ''
        if s == '영어' and k[0] == 'moe':
            nt = NOTES.get(k, {})
            def nbtn(n):
                if is_req(n):
                    return f'<a class="nb req" href="#note-req" data-n="{vkey(n)}" title="카톡으로 요청">{e(n)}번</a>'
                if n in nt:
                    return f'<a class="nb open" href="{view(nt[n])}" target="_blank" rel="noopener">{e(n)}번</a>'
                return f'<span class="nb off" title="준비 중">{e(n)}번</span>'
            vs0 = sorted(dict(VAR.get(k, [])).items(), key=lambda x: vkey(x[0]))
            wd = WORDS.get(k)
            en_top = (f'''<section class="card en-sec" id="notes"><h2>문항별 분석노트</h2>
<div class="legend"><span><i class="nb open"></i>바로 보기</span><span><i class="nb req"></i>카톡 요청</span><span><i class="nb off"></i>준비 중</span></div>
<p class="hot"><b>30~40번은 최근 업데이트 자료</b>예요. 번호를 누르고 아래 요청 칸에서 카카오톡으로 받아 가세요. <b>하루 2개</b>까지, 번호를 <b>하나씩</b> 골라 받아요. (하나 받은 뒤 "다른 번호 받기"로 두 번째 번호)</p>
<div class="nbs">''' + ''.join(nbtn(n) for n in NOTE_NUMS) + '</div></section>' + ad()
                + ('<section class="card en-sec" id="var"><h2>변형문제 <small>무료 · 번호별 전체 공개</small></h2><div class="nbs">'
                   + ''.join(f'<a class="nb var" href="{view(i)}" target="_blank" rel="noopener">{e(n)}번</a>' for n, i in vs0) + '</div></section>'
                   if vs0 else '<section class="card en-sec" id="var"><h2>변형문제</h2><p class="muted">이 회차 변형문제는 준비 중이에요.</p></section>') + ad()
                + (f'<section class="card en-sec" id="words"><h2>영어 단어 총정리</h2><p class="muted">이 회차 18~45번 지문의 핵심 어휘를 한 장에 정리했어요.</p><div class="dl"><a href="{view(wd)}" target="_blank" rel="noopener">미리보기</a><a href="{down(wd)}" rel="noopener">다운로드</a></div></section>'
                   if wd else '<section class="card en-sec" id="words"><h2>영어 단어 총정리</h2><p class="muted">이 회차 단어 자료는 준비 중이에요.</p></section>'))
        if s == '영어':
            pre = f' data-y="{k[2]}" data-m="{k[3]}" data-g="{k[1]}"' if k[0] == 'moe' else ''
            vs = sorted(dict(VAR.get(k, [])).items(), key=lambda x: vkey(x[0]))
            var_html = ('<div class="soon"><b>변형문제</b> · 준비 중이에요</div>' if not vs else
                        '<div class="var" id="var"><b>리카수니 변형문제 (무료)</b><p class="muted">번호를 누르면 PDF가 열려요. 미리보기 화면에서 바로 내려받을 수 있어요.</p><div class="chips">'
                        + ''.join(f'<a class="chip" href="{view(i)}" target="_blank" rel="noopener">{e(n)}번</a>' for n, i in vs) + '</div></div>')
            extra = f'''<section class="card mission" id="note-req"{pre}><h2>분석노트 카톡 요청 <small>30~40번 · 최신 자료</small></h2><p class="muted">이 회차 30~40번 분석노트를 카카오톡으로 받을 수 있어요. 불러오는 중...</p></section>'''
            if k[0] != 'moe': extra += f'<div class="card">{var_html}</div>'
        # 같은 과목 다른 회차
        others = [x for x in same if x != k and s in {r['subject'] for r in sessions[x]}]
        others = sorted(others, key=lambda x: (-x[2], -x[3]))[:12]
        rel = ''
        if others:
            rel = '<div class="card"><h2>다른 회차 ' + e(sn) + '</h2><div class="chips">' + ''.join(
                f'<a class="chip" href="{subj_url(x, s)}">{e(s_name(x))}</a>' for x in others) + '</div></div>'
        sibs = '<div class="chips">' + ''.join(
            f'<a class="chip" href="{subj_url(k, x)}">{e(dname(x))}</a>' for x in subs if x != s) + '</div>'
        srows = [r for r in inf.get('rows', []) if r['s'] == s or (s == '수학' and r['s'].startswith('수학'))]
        sinfo = ''
        if srows or (inf.get('wrong') or {}).get(s):
            sinfo = f'<div class="card"><h2>{e(full)} 등급컷</h2>' + (cut_table(srows) + CUT_NOTE if srows else '') + \
                    (f'<p><b>오답이 많았던 문항</b> · {e(inf["wrong"][s])}</p>' if (inf.get('wrong') or {}).get(s) else '') + \
                    f'<p><a href="{s_url(k)}">{e(name)} 전체 요약·등급컷 보기 →</a></p></div>'
        if en_top:
            body = f'''<h1 class="page-h1">{e(full)} 분석노트·변형문제·단어</h1>
<p class="lead">{e(s_when(k))} · 리카수니 원장이 직접 만든 영어 자료와 기출 원본을 한곳에 모았어요.</p>
{en_top}
{extra}
{ad()}
<div class="card" id="orig"><h2>{e(full)} 기출 원본</h2>{files}</div>
{cp_box(k)}
{sinfo}'''
        else:
            body = f'''<h1 class="page-h1">{e(full)} 문제·정답·해설 PDF</h1>
<p class="lead">{e(s_when(k))} · {e(s_org(k))}</p>
{files}
{sinfo}
{ad()}
{extra}
<div class="card"><h2>{e(name)} 다른 과목</h2>{sibs}</div>
{rel}
{ad()}'''
        if POSTS_BY.get(k) and any(p['subj'] == s for p in POSTS_BY[k]):
            body += post_card([p for p in POSTS_BY[k] if p['subj'] == s], f'{full} 문항별 해설')
        if en_top:
            page(subj_url(k, s), f'{full} 분석노트·변형문제·단어 PDF | 리카수니 자료실',
                 f'{full} 문항별 분석노트, 변형문제, 영어 단어 총정리와 기출 원본 PDF 무료. 리카수니 자료실',
                 body, crumbs + [(subj_url(k, s), sn)], '/english/', comments=(subj_url(k, s).strip('/'), full))
        else:
            page(subj_url(k, s), f'{full} 기출문제·해설 PDF 다운로드 | 리카수니 자료실',
                 f'{full} 문제지·정답·해설 PDF 무료 다운로드. {s_when(k)}. 리카수니 자료실',
                 body, crumbs + [(subj_url(k, s), sn)], active, comments=(subj_url(k, s).strip('/'), full))

# ---------- 문항별 해설 ----------
for p in POSTS:
    k, n = p['k'], p['n']
    nm, url = post_name(p), post_url(p)
    sn = dname(p['subj'])
    qs, multi = p['qs'], len(p['qs']) > 1
    pts = f' [{p["points"]}점]' if p.get('points') == 3 else ''
    ans_s = post_ans(p)
    LASTMOD[url] = p.get('updated', p['date'])
    desc = f'{nm} {ans_s}. ' + _re.sub('^' + _re.escape(nm) + '[은는]\\s*', '', p['lead'])
    h1 = f'{nm} 해설·분석 · {p["type"]} {ans_s}'
    flow = ''.join(f'<li><b>{e(a)}</b> {e(b)}</li>' for a, b in p.get('flow', []))
    def _ev(q): return ''.join(f'<blockquote class="ev"><p class="en">{e(x["en"])}</p><p class="ko">{e(x["ko"])}</p><p class="nt">{e(x["note"])}</p></blockquote>' for x in q.get('evidence', []))
    def _ch(q): return ''.join(f'<li class="{"ok" if i + 1 == q["answer"] else ""}"><span class="no">{CIRC[i]}</span><div><p class="en">{e(c["en"])}</p><p class="ko">{e(c["ko"])}</p><p class="why">{e(c["why"])}</p></div></li>' for i, c in enumerate(q.get('choices', [])))
    def _qh(q, t): return f'{q["n"]}번 {q["type"]} · {t}' if multi else t
    if multi:
        qtd = ' · '.join(f'{q["n"]}번 {e(q["type"])}' + (' [3점]' if q.get('points') == 3 else '') for q in qs)
        atd = '<br>'.join(f'{q["n"]}번 <b class="ans">{CIRC[q["answer"] - 1]}</b> {e(q["choices"][q["answer"] - 1]["en"])}' for q in qs)
    else:
        qtd = f'{n}번 · {e(p["type"])}{pts}'
        atd = f'<b class="ans">{CIRC[p["answer"] - 1]}</b> {e(p["choices"][p["answer"] - 1]["en"]) if p.get("choices") else ""}'
    qcards = ''.join(f'''<div class="card"><h2>{e(_qh(q, "정답 근거 문장"))}</h2>{_ev(q)}</div>
{ad() if i == 0 else ''}
<div class="card"><h2>{e(_qh(q, "선택지 해석과 오답 이유"))}</h2><ol class="chs">{_ch(q)}</ol></div>
''' for i, q in enumerate(qs))
    gr = ''.join(f'<div class="gr"><b>{e(g["t"])}</b><p class="en">{e(g["ex"])}</p><p>{e(g["d"])}</p></div>' for g in p.get('grammar', []))
    vo = ''.join(f'<tr><th>{e(a)}</th><td>{e(b)}</td></tr>' for a, b in p.get('vocab', []))
    faq = ''.join(f'<details><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in p.get('faq', []))
    sm, wr = p.get('summary'), p.get('writing')
    others = [x for x in POSTS_BY[k] if x is not p]
    # 같은 번호 변형문제가 있으면 제목·본문에 연결 (41~42 같은 묶음 번호도 포함)
    def _cov(r):
        a = [int(x) for x in _re.findall(r'\d+', r)]
        return a[0] <= p.get('n2', n) and n <= a[-1]
    vid = next((i for r, i in VAR.get(k, []) if _cov(r)), None) if p['subj'] == '영어' else None
    vtag = ' · 변형문제' if vid else ''
    vcard = (f'<div class="card"><h2>{e(nm)} 변형문제</h2><p class="muted">같은 지문으로 만든 리카수니 변형문제예요. 해설로 정리한 뒤 바로 풀어 보세요.</p>'
             f'<div class="dl"><a href="{view(vid)}" target="_blank" rel="noopener">변형문제 PDF 보기</a></div></div>') if vid else ''
    body = f'''<h1 class="page-h1">{e(h1)}</h1>
<p class="lead">{e(p["lead"])}</p>
<div class="card"><table class="info">
<tr><th>시험</th><td><a href="{subj_url(k, p['subj'])}">{e(s_name(k))} {e(sn)}</a> ({s_when(k)})</td></tr>
<tr><th>문항</th><td>{qtd}</td></tr>
<tr><th>정답</th><td>{atd}</td></tr>
<tr><th>핵심</th><td>{e(p["topic"])}</td></tr>
</table></div>
<div class="card"><h2>글의 흐름 한눈에</h2><ol class="flow">{flow}</ol></div>
{qcards}{f'<div class="tip"><b>풀이 요령</b> {e(p["tip"])}</div>' if p.get("tip") else ''}
{f'<div class="note"><b>원장님 한마디</b><p>{e(p["note"])}</p><small>— 리카수니 원장</small></div>' if p.get("note") else ''}
<div class="card"><h2>꼭 알아야 할 구문</h2>{gr}</div>
<div class="card"><h2>핵심 어휘</h2><table class="info vocab">{vo}</table></div>
{ad()}
{f'<div class="card"><h2>한 줄 요약</h2><p class="en">{e(sm["en"])}</p><p class="ko">{e(sm["ko"])}</p></div>' if sm else ''}
{f'<div class="card"><h2>서술형 대비 문장</h2><p class="en">{e(wr["en"])}</p><p class="ko">{e(wr["ko"])}</p></div>' if wr else ''}
{vcard}
{cp_box(k) if p['subj'] == '영어' else ''}
{f'<div class="card faq"><h2>자주 묻는 질문</h2>{faq}</div>' if faq else ''}
<div class="card"><h2>함께 보면 좋은 자료</h2><div class="chips">
<a class="chip" href="{subj_url(k, p['subj'])}">{e(s_name(k))} {e(sn)} 기출 원본 PDF</a>
<a class="chip" href="/notes/">분석노트 카톡 요청</a><a class="chip" href="/posts/">수업자료 전체</a></div></div>
{post_card(others, f"{s_name(k)} {sn} 다른 문항 해설") if others else ''}'''
    ld = [{"@context": "https://schema.org", "@type": "Article", "headline": h1, "description": p['lead'], "datePublished": p['date'],
           "dateModified": LASTMOD[url], "inLanguage": "ko", "keywords": ', '.join(p.get('keywords', [])), "mainEntityOfPage": SITE + url,
           "author": {"@type": "Person", "name": "리카수니 원장"}, "publisher": {"@type": "Organization", "name": "리카수니 자료실"}}]
    if p.get('faq'):
        ld.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in p['faq']]})
    crumbs = [('/', '홈'), ('/suneung/' if k[0] == 'sn' else f'/moe/go{k[1]}/', '수능 기출' if k[0] == 'sn' else f'고{k[1]} 모의고사'),
              (s_url(k), s_name(k)), (subj_url(k, p['subj']), sn), (url, f'{post_no(p)}번 해설')]
    page(url, f'{nm} 해설·분석 {ans_s}{vtag} | {p["type"]} · {p["topic"]} - 리카수니 자료실',
         desc[:150], body, crumbs, '/posts/',
         comments=(url.strip('/'), f'{nm} 해설'), extra_ld=ld, og_type='article')
    for q in qs if multi else []:  # 세트로 합치기 전 번호별 주소(…/41/)는 세트 페이지로 넘겨 줌
        _d = os.path.join(ROOT, subj_url(k, p['subj']).strip('/'), str(q['n']))
        os.makedirs(_d, exist_ok=True)
        open(os.path.join(_d, 'index.html'), 'w').write(
            f'<!DOCTYPE html><meta charset="UTF-8"><title>{e(nm)} 해설</title><link rel="canonical" href="{SITE}{url}">'
            f'<meta http-equiv="refresh" content="0; url={url}"><a href="{url}">{e(nm)} 해설로 이동</a>')

# 수업자료 (회차별 목록)
def _exam_order(k): return (0 if k[0] == 'sn' else 1, -k[2], -k[3], k[1])
pb = '''<h1 class="page-h1">수업자료 · 영어 문항별 해설</h1>
<p class="lead">리카수니 원장이 모의고사반 수업을 준비하며 정리한 문항별 해설이에요. 정답 근거, 오답 이유, 핵심 구문·어휘 위주로 짧게 정리했어요.</p>'''
# 연도 탭 → 그 연도의 회차 버튼 → 고른 회차 목록 하나만 보임 (JS 없으면 전부 보임). 수능은 '수능' 탭 하나로 묶음.
def _p_year(k):  # 시행 연도 (평가원 6·9월 모평은 학년도 - 1)
    ex, g, y, m = k
    return '수능' if ex == 'sn' else str(y - 1 if g == 3 and m in (6, 9) else y)
def _p_label(k):
    ex, g, y, m = k
    if ex == 'sn': return f'{y}학년도'
    return f'{m}월 모평(고3)' if g == 3 and m in (6, 9) else f'{m}월 고{g}'
def _p_id(k): return "-".join(map(str, k))
if POSTS:
    pk = sorted(POSTS_BY, key=lambda k: (0 if k[0] == 'moe' else 1, -(int(_p_year(k)) if k[0] == 'moe' else 0), -k[3], k[1], -k[2]))
    years = list(collections.OrderedDict.fromkeys(_p_year(k) for k in pk))
    pb += '<div class="y-tabs" role="tablist">' + ''.join(
        f'<button type="button" class="y-tab" role="tab" data-y="{y}">{y if y == "수능" else y + "년"}'
        f'<small>{sum(len(POSTS_BY[k]) for k in pk if _p_year(k) == y)}문항</small></button>' for y in years) + '</div>'
    pb += '<div class="s-tabs">' + ''.join(
        f'<a class="s-tab" href="#{_p_id(k)}" data-y="{_p_year(k)}" data-k="{_p_id(k)}">{e(_p_label(k))}<small>{len(POSTS_BY[k])}문항</small></a>' for k in pk) + '</div>'
    for k in pk:
        ps = sorted(POSTS_BY[k], key=lambda p: p['n'])
        pb += (f'<div class="card p-panel" id="{_p_id(k)}" data-y="{_p_year(k)}"><h2>{e(s_name(k))} 영어 <small class="muted">{len(ps)}문항</small></h2><div class="plist">' + ''.join(
            f'<a href="{post_url(p)}"><b>{post_no(p)}번 · {e(p["type"])}</b><span>{post_ans(p)} · {e(p["topic"])}</span></a>' for p in ps)
            + f'</div><p class="more-l" style="margin:10px 0 0"><a href="{subj_url(k, "영어")}">{e(s_name(k))} 영어 기출·자료 보기 →</a></p></div>')
    pb += ad() + '''<script>(function(){var Y=document.querySelectorAll('.y-tab'),S=document.querySelectorAll('.s-tab'),P=document.querySelectorAll('.p-panel');
function pick(k,push){var p=document.getElementById(k);if(!p||!p.classList.contains('p-panel'))return false;var y=p.dataset.y;
Y.forEach(function(b){var on=b.dataset.y==y;b.classList.toggle('on',on);b.setAttribute('aria-selected',on)});
S.forEach(function(a){a.hidden=a.dataset.y!=y;a.classList.toggle('on',a.dataset.k==k)});
P.forEach(function(x){x.hidden=x.id!=k});if(push)history.replaceState(null,'','#'+k);try{localStorage.setItem('postSess',k)}catch(e){}return true}
function first(y){for(var i=0;i<S.length;i++)if(S[i].dataset.y==y)return S[i].dataset.k}
Y.forEach(function(b){b.onclick=function(){pick(first(b.dataset.y),true)}});
S.forEach(function(a){a.onclick=function(ev){ev.preventDefault();pick(a.dataset.k,true)}});
var s=null;try{s=localStorage.getItem('postSess')}catch(e){}
if(pick(decodeURIComponent(location.hash.slice(1))))setTimeout(function(){scrollTo(0,0)},0);else(s&&pick(s))||pick(S[0].dataset.k)})();</script>'''
else:
    pb += '<div class="card"><p class="muted">곧 첫 수업자료가 올라와요.</p></div>'
page('/posts/', '수업자료 · 수능·모의고사 영어 문항별 해설 모음 | 리카수니 자료실',
     '수능·고3·고2·고1 모의고사 영어 문항별 해설. 정답 근거, 오답 이유, 핵심 구문과 어휘를 짧게 정리. 리카수니 자료실', pb,
     [('/', '홈'), ('/posts/', '수업자료')], '/posts/', comments=('posts', '수업자료'))

# ---------- 학교별 내신 분석 (코코스 학원생 전용) ----------
# 공개 페이지에는 학교 목록과 시험 제목만. 분석 내용은 공개 저장소에 두지 않고 학원생 인증 후 Supabase 에서 불러올 예정.
NAESIN = json.load(open(os.path.join(ROOT, '_tools', 'naesin.json')))['schools']
import glob as _glob
NS_PUB = collections.defaultdict(list)  # (학교, 시험key) → 공개 문항 분석 (검색 노출·학원 홍보용, 문항 원문은 옮기지 않음)
for _f in sorted(_glob.glob(os.path.join(ROOT, '_tools', 'naesin_public', '*.json'))):
    _it = json.load(open(_f))
    if _it.get('date', '') <= TODAY: NS_PUB[(_it['school'], _it['exam'])].append(_it)
ACADEMY = ('<div class="card ns-cocos"><h2>이매동 코코스학원</h2><p>리카수니 원장이 직접 가르치는 성남 분당 이매동 영어학원이에요. '
           '학교별 기출을 분석해 내신 대비 수업에 그대로 반영해요. 상담·등록 문의는 학원으로 연락 주세요.</p>'
           '<p><a class="btn-cocos" href="https://www.cocosedu.co.kr/" target="_blank" rel="noopener">코코스학원 홈페이지 →</a></p></div>')  # www 없는 주소는 인증서 경고가 떠서 www 로
# 학원생 칸: JS 가 로그인 → 인증 신청 → 승인 대기 → (승인되면) 분석 글을 Supabase 에서 불러와 채움. JS 전 내용은 이용 방법 안내.
def ns_member(slug=''):
    sj = e(json.dumps([[x['slug'], x['short']] for x in NAESIN], ensure_ascii=False))
    return (f'<div class="card ns-member" id="ns-member" data-school="{slug}" data-schools="{sj}"><h2>🔒 학원생 전용 분석</h2><ol class="sum">'
            '<li>카카오로 로그인해요.</li><li>학원생 인증을 신청하면 원장님이 한 명씩 확인 후 승인해요.</li>'
            '<li>승인되면 학교별 시험 분석을 볼 수 있어요.</li></ol>'
            '<p><button type="button" class="btn btn-kakao" onclick="lazyLogin()">💬 카카오로 로그인</button></p>'
            '<p class="muted">학교 시험지의 저작권은 각 학교에 있어요. 분석 내용은 코코스 학원생 수업용으로만 공개하고, 외부 공유는 하지 말아 주세요.</p></div>')
def ns_card(sc):
    n = len(sc.get('exams', []))
    return (f'<a class="ns-school" href="/naesin/{sc["slug"]}/"><b>{e(sc["short"])}</b><span>{e(sc["name"])}</span>'
            f'<em class="{"ok" if n else ""}">{f"시험 {n}개 분석" if n else "준비 중"}</em></a>')
# 학원 소식 목록 (내신 목록 위 '학원 소식' 칸과 /news/ 에서 씀)
NEWS = []
_nd = os.path.join(ROOT, '_tools', 'news')
for d in sorted(os.listdir(_nd)) if os.path.isdir(_nd) else []:
    mp = os.path.join(_nd, d, 'meta.json')
    if os.path.exists(mp):
        m = json.load(open(mp, encoding='utf-8'))
        if m['date'] <= TODAY: m['_dir'] = os.path.join(_nd, d); NEWS.append(m)
NEWS.sort(key=lambda m: (m['date'], m['slug']), reverse=True)
def nurl(m): return f'/books/news/{m["slug"]}/' if m.get('cat') == 'book' else f'/news/{m["slug"]}/'  # cat=book → 부교재 메뉴 '교재 소식'
BOOKNEWS = [m for m in NEWS if m.get('cat') == 'book']
NEWS = [m for m in NEWS if m.get('cat') != 'book']  # 학원 소식만
NEWS_CSS = '.nw-list{list-style:none;margin:0;padding:0}.nw-list li+li{border-top:1px dashed var(--line)}.nw-list a{display:flex;gap:14px;align-items:center;padding:12px 0;color:inherit;text-decoration:none}.nw-list img{flex:none;width:84px;height:84px;object-fit:cover;border-radius:10px;border:1px solid var(--line)}.nw-list small{color:var(--muted);font-size:.8rem}.nw-list b{display:block;color:var(--navy-d);margin:2px 0;line-height:1.4}.nw-list span{color:var(--muted);font-size:.9rem}.nw-list a:hover b{text-decoration:underline}.nw-list em{display:block;font-style:normal;color:#475569;font-size:.88rem;line-height:1.45}.nw-chip{display:inline-block;font-style:normal;font-size:.72rem;font-weight:700;padding:1px 8px;border-radius:999px;background:#eef2ff;color:#1f3a8a;margin-right:6px}.nw-chip.new{background:#fff1e6;color:#c2410c}.nw-chip.buy{background:#fee2e2;color:#b42318}.nw-cols{display:grid;grid-template-columns:1fr 1fr;gap:6px 28px}.nw-cols h3{font-size:1rem;margin:4px 0 0;color:var(--navy-d)}.nw-cols h3 small{color:var(--muted);font-weight:500}.nw-cols img{width:64px;height:64px}@media(max-width:760px){.nw-cols{grid-template-columns:1fr}}'
def news_kind(m):  # 교재 소식 분류: 신간 소개 / 자료·정보
    return 'new' if m.get('tag', '').startswith('교재 신간') else 'info'
def news_line(m):
    th = os.path.exists(os.path.join(m['_dir'], 'thumb.png'))
    main, _, sub = m['title'].partition(' — ')  # 목록에선 긴 제목을 두 줄로: 굵은 이름 + 작은 설명
    sub = _re.sub(r'\s*\((이매동 )?코코스학원[^)]*\)\s*$', '', sub)
    tag = m.get('tag', '학원 소식')
    chip = f'<i class="nw-chip{" new" if tag.startswith("교재 신간") else ""}">{e(tag)}</i>'
    buy = '<i class="nw-chip buy">🛒 구매 링크</i>' if 'link.coupang.com' in open(os.path.join(m['_dir'], 'body.html'), encoding='utf-8').read() else ''
    return (f'<li><a href="{nurl(m)}">' + (f'<img src="{nurl(m)}thumb.png" alt="" loading="lazy" width="84" height="84">' if th else '') +
            f'<div><small>{chip}{buy}{m["date"].replace("-", ".")}</small><b>{e(main)}</b>' + (f'<em>{e(sub)}</em>' if sub else '') + '</div></a></li>')
def book_groups(ms, n=None):  # 교재 소식을 신간 소개 / 자료·정보 두 칸으로
    cols = [(k, h, [m for m in ms if news_kind(m) == k]) for k, h in (('new', '📘 신간 소개'), ('info', '🔗 자료·정보'))]
    return '<div class="nw-cols">' + ''.join(f'<section><h3>{h} <small>{len(g)}</small></h3><ul class="nw-list">{"".join(news_line(m) for m in (g[:n] if n else g))}</ul></section>' for k, h, g in cols if g) + '</div>'
nb = ('<h1 class="page-h1">학교별 영어 내신 분석 <small class="ns-lock">🔒 코코스 학원생 전용</small></h1>'
      '<p class="lead">이매동 코코스학원 리카수니 원장이 학교 기출 시험지를 직접 분석해요. 출제 범위, 문항별 포인트, 서술형 대비까지 정리하고, '
      '<b>분석 내용은 코코스 학원생만</b> 볼 수 있어요. 학교별 분석은 시험이 끝날 때마다 계속 채워 가요.</p>')
if NEWS:  # 코코스학원 메뉴: 위에 학원 소식, 아래 학교별 내신 분석
    nb += (f'<div class="card"><style>{NEWS_CSS}</style><h2>📢 학원 소식</h2><ul class="nw-list">{"".join(news_line(m) for m in NEWS[:3])}</ul>'
           + (f'<p style="margin:6px 0 0"><a href="/news/">학원 소식 전체 보기 ({len(NEWS)}개) →</a></p>' if len(NEWS) > 3 else '') + '</div>')
for lv, lname in (('고', '고등학교'), ('중', '중학교')):
    nb += f'<div class="card"><h2>{lname}</h2><div class="ns-grid">' + ''.join(ns_card(sc) for sc in NAESIN if sc['level'] == lv) + '</div></div>'
nb += ns_member() + ACADEMY
page('/naesin/', '학교별 영어 내신 분석 · 태원고 송림고 이매고 돌마고 판교고 · 이매중 야탑중 하탑중 송림중 매송중 | 리카수니 자료실',
     '분당 태원고·송림고·이매고·돌마고·판교고, 이매중·야탑중·하탑중·송림중·매송중 영어 내신 기출 분석. 이매동 코코스학원 학원생 전용. 리카수니 원장 직접 분석.',
     nb, [('/', '홈'), ('/naesin/', '코코스학원')], '/naesin/')
for sc in NAESIN:
    ex = sc.get('exams', [])
    sb_ = (f'<h1 class="page-h1">{e(sc["name"])} 영어 내신 분석 <small class="ns-lock">🔒 코코스 학원생 전용</small></h1>'
           f'<p class="lead">{e(sc["short"])} 영어 내신 기출을 이매동 코코스학원 리카수니 원장이 직접 분석했어요. 출제 범위와 문항별 포인트, 서술형 대비 방법을 정리해요. '
           '분석 내용은 코코스 학원생 인증 후 볼 수 있어요.</p>'
           '<div class="card"><h2>시험별 분석</h2>'
           + (''.join(f'<div class="ns-exam"><div class="ns-exam-h"><b>{e(x["full"])}</b><span class="meta">{e(x["date"])} 시행 · {e(x["info"])}</span></div>'
                      + (('<p class="ns-free">무료 공개 문항</p><ul class="ns-exams">' + ''.join(
                          f'<li><a href="/naesin/{sc["slug"]}/{x["key"]}/{it["n"]}/"><b>{e(it.get("label") or it["n"] + "번")} · {e(it["type"])}</b> {e(it["title"])}</a><span class="ns-open">공개</span></li>'
                          for it in sorted(NS_PUB[(sc['slug'], x['key'])], key=lambda it: int(''.join(c for c in it['n'] if c.isdigit()) or 0) + (100 if it['n'].startswith('seo') else 0))) + '</ul>')
                         if NS_PUB[(sc['slug'], x['key'])] else '')
                      + '<p class="ns-rest">🔒 전체 문항 분석·시험 총평은 코코스 학원생 전용이에요 (아래 학원생 칸)</p></div>' for x in ex) if ex
              else '<p class="muted">첫 분석을 준비하고 있어요. 시험이 끝나면 차례대로 올라와요.</p>') + '</div>'
           + ns_member(sc['slug'])
           + '<div class="card"><h2>다른 학교</h2><div class="chips">' + ''.join(
               f'<a class="chip" href="/naesin/{o["slug"]}/">{e(o["short"])}</a>' for o in NAESIN if o is not sc) + '</div></div>'
           + ACADEMY)
    page(f'/naesin/{sc["slug"]}/', f'{sc["name"]} 영어 내신 기출 분석 ({sc["short"]}) | 리카수니 자료실',
         f'{sc["name"]}({sc["short"]}) 영어 내신 기출문제 분석. 출제 범위, 문항별 포인트, 서술형 대비. 이매동 코코스학원 학원생 전용, 리카수니 원장 직접 분석.',
         sb_, [('/', '홈'), ('/naesin/', '내신 분석'), (f'/naesin/{sc["slug"]}/', sc['short'])], '/naesin/')

def ns_text(t):
    """공개 문항 본문: ' / ', '<br>', ①②… 로 이어 쓴 항목을 줄 목록으로 나눠 읽기 쉽게 (○·✗ 표시는 색 배지)"""
    mk = lambda x: x.replace('○', '<span class="mk ok">○</span>').replace('✗', '<span class="mk ng">✗</span>')
    if isinstance(t, list): parts, intro = t, ''
    elif ' / ' in t: parts, intro = t.split(' / '), ''
    elif '<br>' in t: parts, intro = t.split('<br>'), ''
    else:
        parts = _re.split(r'\s(?=[①②③④⑤⑥⑦⑧⑨]\s)', t)
        intro = '' if parts[0][:1] in '①②③④⑤⑥⑦⑧⑨' else parts.pop(0)
        if len(parts) < 2:
            sents = [x + ('' if x.endswith('.') else '.') for x in _re.split(r'(?<=요\.)\s+', t) if x.strip()]
            if len(t) > 140 and len(sents) >= 3:  # 긴 문단은 문장마다 한 줄씩
                return '<ul class="ns-list">' + ''.join(f'<li>{mk(x)}</li>' for x in sents) + '</ul>'
            return f'<p>{mk(t)}</p>'
    return (f'<p>{mk(intro)}</p>' if intro else '') + '<ul class="ns-list">' + ''.join(f'<li>{mk(x.strip())}</li>' for x in parts if x.strip()) + '</ul>'

for sc in NAESIN:
    for x in sc.get('exams', []):
        for it in NS_PUB[(sc['slug'], x['key'])]:
            url = f'/naesin/{sc["slug"]}/{x["key"]}/{it["n"]}/'
            lbl = it.get('label') or f'{it["n"]}번'
            nm = f'{sc["short"]} {x["title"]} {lbl}'
            body = (f'<h1 class="page-h1">{e(nm)} 분석 · {e(it["type"])}</h1><p class="lead">{e(it["lead"])}</p>'
                    f'<div class="card"><table class="info"><tr><th>시험</th><td>{e(sc["name"])} {e(x["full"])} ({e(x["date"])} 시행)</td></tr>'
                    f'<tr><th>문항</th><td>{e(lbl)} · {e(it["type"])} [{e(it["points"])}]</td></tr>'
                    f'<tr><th>{"모범 답안" if len(it["answer"]) > 3 else "정답"}</th><td><b>{e(it["answer"])}</b></td></tr><tr><th>구성</th><td>{e(x["info"])}</td></tr></table>'
                    '<p class="muted">시험 문제의 저작권은 학교와 관할 교육청에 있어요. 이 글은 문제 원문을 옮기지 않고 리카수니 원장의 분석만 담았어요.</p></div>')
            if it.get('pairs'):
                body += ('<div class="card"><h2>선택지 단어 짝 한눈에</h2><table class="ns-pairs"><tr><th>밑줄 단어</th><th>바꾼 단어</th><th>같은 뜻?</th><th>설명</th></tr>'
                         + ''.join(f'<tr class="{"bad" if ok == "✗" else ""}"><td><b>{e(w)}</b></td><td>{e(a2)}</td><td>{e(ok)}</td><td>{e(d)}</td></tr>' for w, a2, ok, d in it['pairs'])
                         + '</table></div>')
            body += ''.join(f'<div class="card"><h2>{e(h)}</h2>{ns_text(t)}</div>' for h, t in it.get('sections', []))
            if it.get('tip'): body += f'<div class="tip"><b>풀이 팁</b>{e(it["tip"])}</div>'
            body += (f'<div class="card ns-cta"><h2>🔒 {e(sc["short"])} {e(x["title"])} 전체 분석</h2><p>{e(x["info"])} 전체 문항 분석, 시험 총평, 다음 시험 대비 포인트는 <b>코코스 학원생 전용</b>이에요.</p>'
                     f'<p><a class="btn-cocos" href="/naesin/{sc["slug"]}/#ns-member">학원생으로 전체 분석 보기 →</a></p></div>' + ACADEMY)
            LASTMOD[url] = it.get('updated', it['date'])
            ld = [{"@context": "https://schema.org", "@type": "Article", "headline": f'{nm} 분석 · {it["type"]}', "description": it['lead'][:200],
                   "datePublished": it['date'], "dateModified": LASTMOD[url], "inLanguage": "ko", "keywords": ', '.join(it.get('keywords', [])),
                   "author": {"@type": "Person", "name": "리카수니 원장"}, "publisher": {"@type": "Organization", "name": "리카수니 자료실"},
                   "about": f'{sc["name"]} 영어 내신 기출', "mainEntityOfPage": SITE + url}]
            page(url, f'{nm} 영어 내신 기출 해설·분석 ({it["type"]}) | 리카수니 자료실',
                 it['lead'][:150], body,
                 [('/', '홈'), ('/naesin/', '내신 분석'), (f'/naesin/{sc["slug"]}/', sc['short']), (url, lbl)], '/naesin/', extra_ld=ld, og_type='article')

# ---------- 학년 / 수능 목록 ----------
for g in (1, 2, 3):
    ks = [k for k in sessions if k[0] == 'moe' and k[1] == g]
    body = f'''<h1 class="page-h1">고{g} 모의고사 기출문제 전과목 PDF</h1>
<p class="lead">연도·월별 고{g} 모의고사 문제지와 정답·해설을 모았어요. 총 {len(ks)}개 회차.</p>
<div class="card">{session_list(ks)}</div>{ad()}'''
    page(f'/moe/go{g}/', f'고{g} 모의고사 기출문제 전과목 PDF 모음 | 리카수니 자료실',
         f'고{g} 모의고사 기출문제 연도별·월별 전과목 문제지·정답·해설 PDF 무료 다운로드.', body,
         [('/', '홈'), (f'/moe/go{g}/', f'고{g} 모의고사')], f'/moe/go{g}/')

ks = sorted([k for k in sessions if k[0] == 'sn'], key=lambda k: -k[2])
body = '''<h1 class="page-h1">대학수학능력시험(수능) 기출문제 전과목 PDF</h1>
<p class="lead">학년도별 수능 문제지와 정답·해설을 모았어요.</p>''' + '<div class="card"><div class="chips">' + ''.join(
    f'<a class="chip" href="{s_url(k)}">{k[2]}학년도<small>{len(bysubj(sessions[k]))}과목</small></a>' for k in ks) + '</div></div>' + ad()
page('/suneung/', '수능 기출문제 전과목 PDF 모음 | 리카수니 자료실', '대학수학능력시험 학년도별 전과목 기출문제·정답·해설 PDF 무료 다운로드.',
     body, [('/', '홈'), ('/suneung/', '수능 기출')], '/suneung/')

# ---------- 홈 ----------
cnt = collections.Counter(k[1] if k[0] == 'moe' else 'sn' for k in sessions)
latest = sorted([k for k in sessions if k[0] == 'moe'], key=lambda k: (-k[2], -k[3], k[1]))[:9]
var_sess = sorted([k for k in VAR if k in sessions], key=lambda k: (k[1], -k[2], -k[3]))
# ---------- 학원 소식 (_tools/news/<slug>/meta.json + body.html [+ thumb.png] → /news/<slug>/) ----------
# 본문은 받은 HTML 그대로. <!--THUMB--> 자리에 썸네일(있을 때만), <!--AD--> 자리에 자료실 수동 광고. date 가 미래면 그날 공개
for m in NEWS + BOOKNEWS:
    url = nurl(m); isbook = m.get('cat') == 'book'
    LASTMOD[url] = m.get('updated', m['date'])
    body = open(os.path.join(m['_dir'], 'body.html'), encoding='utf-8').read()
    has_th = os.path.exists(os.path.join(m['_dir'], 'thumb.png'))
    th_html = (f'<div style="box-sizing:border-box;margin:0 0 16px;max-width:100%;overflow:hidden;text-align:center;width:100%;"><img src="thumb.png" alt="{e(m["title"])}" width="1080" height="1080" loading="eager" style="border-radius:10px;height:auto;max-width:560px;width:100%;"></div>') if has_th else ''
    body = body.replace('<!--THUMB-->', th_html).replace('<!--AD-->', ad())
    others = [x for x in (BOOKNEWS if isbook else NEWS) if x is not m][:5]
    body = f'<div class="card">{body}</div>' + (f'<div class="card"><style>{NEWS_CSS}</style><h2 style="font-size:1rem;margin:0 0 4px">{"다른 교재 소식" if isbook else "다른 학원 소식"}</h2><ul class="nw-list">{"".join(news_line(x) for x in others)}</ul></div>' if others else '')
    ld = [{"@context": "https://schema.org", "@type": "Article", "headline": m['title'], "description": m['desc'], "datePublished": m['date'],
           "dateModified": LASTMOD[url], "inLanguage": "ko", "author": {"@type": "Person", "name": "리카수니"},
           "publisher": {"@type": "Organization", "name": "리카수니 자료실"}, "keywords": ', '.join(m.get('keywords', [])), "mainEntityOfPage": SITE + url}
          | ({"image": SITE + url + 'thumb.png'} if has_th else {})]
    if m.get('faq'):
        ld.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q['q'], "acceptedAnswer": {"@type": "Answer", "text": q['a']}} for q in m['faq']]})
    page(url, f'{m["title"]} | 리카수니 자료실', m['desc'], body,
         ([('/', '홈'), ('/books/', '부교재'), ('/books/news/', '교재 소식'), (url, m.get('tag', '교재 소식'))] if isbook else
          [('/', '홈'), ('/naesin/', '코코스학원'), ('/news/', '학원 소식'), (url, m.get('tag', '학원 소식'))]), '/books/' if isbook else '/news/', extra_ld=ld, og_type='article',
         og_image=(SITE + url + 'thumb.png') if has_th else None)
    if has_th: shutil.copyfile(os.path.join(m['_dir'], 'thumb.png'), os.path.join(ROOT, url.strip('/'), 'thumb.png'))
page('/books/news/', '교재 소식 – 고등 영어 부교재 신간 · 개정 정보 | 리카수니 자료실',
     '고등 영어 부교재 신간·개정 소식을 리카수니 원장이 요약해 알려 드려요. 교재 구성과 대상, 출판사 이벤트 정보.',
     f'<style>{NEWS_CSS}</style><section class="hero"><h1>교재 소식</h1><p>고등 영어 부교재 신간·개정 소식을 요약해 알려 드려요.</p></section>'
     + (f'<div class="card">{book_groups(BOOKNEWS)}</div>' if BOOKNEWS else '<div class="card"><p class="muted">곧 첫 소식이 올라와요.</p></div>'),
     [('/', '홈'), ('/books/', '부교재'), ('/books/news/', '교재 소식')], '/books/')
page('/news/', '학원 소식 – 이매동 코코스학원 시험 대비 · 수업 안내 | 리카수니 자료실',
     '이매동 코코스학원 소식. 중등·고등 시험 대비 핵심 정리와 대비반·수업 안내를 모았어요.',
     f'<style>{NEWS_CSS}</style><section class="hero"><h1>학원 소식</h1><p>이매동 코코스학원의 시험 대비 정리와 수업 안내를 모아 두는 곳이에요.</p></section>'
     + (f'<div class="card"><ul class="nw-list">{"".join(news_line(m) for m in NEWS)}</ul></div>' if NEWS else '<div class="card"><p class="muted">곧 첫 소식이 올라와요.</p></div>'),
     [('/', '홈'), ('/naesin/', '코코스학원'), ('/news/', '학원 소식')], '/news/')

# ---------- 원장님 노트 (_tools/memos/<slug>.json → /memo/<slug>/) ----------
# 원장님이 채팅으로 준 분석노트 메모를 Claude 가 JSON 으로 정리. date 가 미래면 그날 공개 (해설과 같게)
# 원장님이 쓴 설명은 그대로, Claude 가 덧붙인 예문·확인 문제는 'Claude 추가' 표시
MEMO_CSS = _re.sub(r'\s+', ' ', """
.mm{max-width:780px;margin:0 auto}
.mm-tags{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px}
.mm-tag{font-size:.78rem;font-weight:800;padding:3px 10px;border-radius:999px;background:#eef1fa;color:var(--navy)}
.mm-tag.bk{background:var(--navy);color:#fff}
.mm h1{font-size:1.5rem;line-height:1.35;margin:4px 0}
.mm .sub{color:var(--muted);margin:0 0 16px}
.mm h2{font-size:1.1rem;margin:22px 0 10px;padding-left:10px;border-left:4px solid var(--navy)}
.mm-one{border-left:5px solid var(--gold);background:#fff8e6;border-radius:0 12px 12px 0;padding:14px 18px;margin:0 0 6px}
.mm-one small{display:block;color:#92400e;font-weight:800;margin-bottom:2px}
.mm-one b{color:var(--navy)} .mm-one span{color:var(--muted)}
.mm-sent{background:#f8fafc;border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.mm-sent .en{font-family:Georgia,'Times New Roman',serif;font-size:1.08rem;line-height:1.7;margin:0 0 8px}
.mm-sent .en i{color:#94a3b8;font-style:normal;padding:0 2px}
.mm-sent .ko{margin:0;color:#334155}
.mm-flow{display:inline-block;margin-top:10px;font-size:.88rem;font-weight:700;color:#166534;background:#ecfdf3;border-radius:8px;padding:4px 10px}
.mm-pt{border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin:0 0 10px;background:#fff}
.mm-pt h3{margin:0 0 6px;font-size:.98rem} .mm-pt p{margin:4px 0} .mm-pt .en{font-family:Georgia,serif}
.mm u{text-decoration-color:var(--gold);text-decoration-thickness:3px} .mm .rs{color:#2563eb}
.mm-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
@media(max-width:640px){.mm-grid{grid-template-columns:1fr}.mm h1{font-size:1.28rem}}
.mm-k{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.mm-k h3{margin:0 0 4px;font-size:.82rem;color:var(--muted)} .mm-k p{margin:0}
.mm-k.warn{border-color:#fecaca;background:#fff5f5} .mm-k.warn h3{color:#dc2626}
.mm-add{font-size:.72rem;font-weight:700;color:#6366f1;background:#eef2ff;border-radius:6px;padding:2px 7px;margin-left:6px;vertical-align:middle}
.mm-ex{background:#f3f6ff;border-radius:12px;padding:12px 16px;margin:0 0 8px} .mm-ex p{margin:4px 0} .mm-ex .en{font-family:Georgia,serif;font-size:1.04rem}
.mm-q{border:1px dashed #c7d2fe;border-radius:12px;padding:10px 16px;margin:0 0 8px} .mm-q p{margin:4px 0} .mm-q summary{cursor:pointer;color:var(--navy);font-weight:700}
.mm-cta{display:flex;flex-wrap:wrap;gap:8px;margin-top:20px}
.mm-foot{margin-top:14px;color:var(--muted);font-size:.86rem}
.mm-list{list-style:none;margin:0;padding:0} .mm-list li+li{border-top:1px dashed var(--line)}
.mm-list a{display:block;padding:10px 0;color:inherit;text-decoration:none} .mm-list a:hover b{text-decoration:underline}
.mm-list small{color:var(--muted);font-size:.8rem} .mm-list b{display:block;color:var(--navy-d);margin:2px 0} .mm-list span{color:var(--muted);font-size:.9rem}
""").strip()
MEMOS = []
_md = os.path.join(ROOT, '_tools', 'memos')
for f in sorted(os.listdir(_md)) if os.path.isdir(_md) else []:
    if f.endswith('.json'):
        m = json.load(open(os.path.join(_md, f), encoding='utf-8'))
        if m['date'] <= TODAY: MEMOS.append(m)
MEMOS.sort(key=lambda m: (m['date'], m['slug']), reverse=True)
def memo_line(m):  # 목록·첫 화면 한 줄
    o = m['one']
    return (f'<li><a href="/memo/{m["slug"]}/"><small>{m["date"][5:].replace("-", ".")} · {e(m["book"])} {e(m["where"])}</small>'
            f'<b>{e(m["h1"])}</b><span>{e(o["key"])}: {e(o["text"])}</span></a></li>')
for m in MEMOS:
    url = f'/memo/{m["slug"]}/'
    LASTMOD[url] = m.get('updated', m['date'])
    o, st = m['one'], m.get('sentence')
    add = '<span class="mm-add">Claude 추가</span>'
    h = [f'<style>{MEMO_CSS}</style><article class="mm card">',
         '<div class="mm-tags">' + f'<span class="mm-tag bk">{e(m["book"])}</span><span class="mm-tag">{e(m["where"])}</span>' + ''.join(f'<span class="mm-tag">{e(t)}</span>' for t in m.get('tags', [])) + '</div>',
         f'<h1>{e(m["h1"])}</h1><p class="sub">{e(m.get("sub", ""))}</p>',
         f'<div class="mm-one"><small>✏️ 분석노트 한 줄</small><b>{e(o["key"])}</b>: {e(o["text"])}' + (f' <span>— {e(o["note"])}</span>' if o.get('note') else '') + '</div>']
    if st:
        h.append('<h2>문장 끊어 읽기</h2><div class="mm-sent"><p class="en">' + e(st['en']).replace(' / ', ' <i>/</i> ') + f'</p><p class="ko">{e(st["ko"])}</p>'
                 + (f'<span class="mm-flow">✔ {e(st["flow"])}</span>' if st.get('flow') else '') + '</div>')
    if m.get('points'):
        h.append('<h2>구문 포인트</h2>' + ''.join(f'<div class="mm-pt"><h3>{"①②③④⑤⑥"[i]} {e(pt["title"])}</h3>' + (f'<p class="en">{pt["en"]}</p>' if pt.get('en') else '') + f'<p>{e(pt["body"])}</p></div>' for i, pt in enumerate(m['points'])))
    if m.get('vocab'):
        h.append(f'<h2>어휘 포인트: {e(m["vocab"]["title"])}</h2><div class="mm-grid">' + ''.join(
            f'<div class="mm-k{" warn" if len(c) > 2 and c[2] == "warn" else ""}"><h3>{e(c[0])}</h3><p>{e(c[1])}</p></div>' for c in m['vocab']['cards']) + '</div>')
    if m.get('examples'):
        h.append(f'<h2>예문으로 한 번 더{add}</h2>' + ''.join(f'<div class="mm-ex"><p class="en">{x["en"]}</p><p>{e(x["ko"])}</p></div>' for x in m['examples']))
    if m.get('quiz'):
        h.append(f'<h2>확인 문제{add}</h2>' + ''.join(f'<div class="mm-q"><p>{i + 1}. {q["q"]}</p><details><summary>정답 보기</summary><p>{q["a"]}</p></details></div>' for i, q in enumerate(m['quiz'])))
    if m.get('faq'):
        h.append('<h2>자주 묻는 질문</h2><div class="faq">' + ''.join(f'<details><summary>{e(q["q"])}</summary><p>{e(q["a"])}</p></details>' for q in m['faq']) + '</div>')
    cta = [x for x in (m.get('cta'), m.get('more')) if x]
    if cta:
        h.append('<div class="mm-cta">' + ''.join(f'<a class="btn {"btn-navy" if i == 0 else "btn-line"}" href="{e(x["href"])}">{e(x["label"])}</a>' for i, x in enumerate(cta)) + '</div>')
    h.append(f'<p class="mm-foot">리카수니 원장 · {m["date"].replace("-", ".")} · <a href="/memo/">원장님 노트 전체 보기</a></p></article>')
    others = [x for x in MEMOS if x is not m][:5]
    if others:
        h.append(f'<div class="card mm" style="margin-top:16px"><h2 style="font-size:1rem;margin:0 0 4px">다른 원장님 노트</h2><ul class="mm-list">{"".join(memo_line(x) for x in others)}</ul></div>')
    ld = [{"@context": "https://schema.org", "@type": "Article", "headline": m['h1'], "description": m['desc'], "datePublished": m['date'],
           "dateModified": LASTMOD[url], "inLanguage": "ko", "author": {"@type": "Person", "name": "리카수니"},
           "publisher": {"@type": "Organization", "name": "리카수니 자료실"}, "keywords": ', '.join(m.get('keywords', [])), "mainEntityOfPage": SITE + url}]
    if m.get('faq'):
        ld.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q['q'], "acceptedAnswer": {"@type": "Answer", "text": q['a']}} for q in m['faq']]})
    page(url, f'{m["title"]} | 리카수니 자료실', m['desc'], ''.join(h),
         [('/', '홈'), ('/memo/', '원장님 노트'), (url, f'{m["book"]} {m["where"]}')], '/', extra_ld=ld, og_type='article')
page('/memo/', '원장님 노트 – 수능특강·모의고사 영어 구문·어휘 분석 메모 | 리카수니 자료실',
     '리카수니 원장이 분석노트를 만들며 정리한 영어 구문·어휘 포인트. 수능특강 라이트·모의고사 문장별 핵심 설명을 짧게 모았어요.',
     f'<style>{MEMO_CSS}</style><section class="hero"><h1>원장님 노트</h1><p>분석노트를 만들면서 짚은 구문·어휘 포인트를 짧게 모아 두는 곳이에요.</p></section>'
     + (f'<div class="card mm"><ul class="mm-list">{"".join(memo_line(m) for m in MEMOS)}</ul></div>' if MEMOS else '<div class="card"><p class="muted">곧 첫 노트가 올라와요.</p></div>'),
     [('/', '홈'), ('/memo/', '원장님 노트')], '/')
memo_home = (f'<section class="card mm-home"><style>{MEMO_CSS}</style><h2 style="margin:0 0 4px">✏️ 원장님 노트 <small class="muted" style="font-size:.8rem;font-weight:600">분석노트 만들며 정리한 포인트</small></h2>'
             f'<ul class="mm-list">{"".join(memo_line(m) for m in MEMOS[:5])}</ul><p style="margin:6px 0 0"><a href="/memo/">원장님 노트 전체 보기 →</a></p></section>') if MEMOS else ''

var_files = sum(len(dict(VAR[k])) for k in var_sess)
tiles = f'''<div class="grid4">
<a class="tile" href="/moe/go1/"><b>고1</b><span>{cnt[1]}개 회차</span></a>
<a class="tile" href="/moe/go2/"><b>고2</b><span>{cnt[2]}개 회차</span></a>
<a class="tile" href="/moe/go3/"><b>고3</b><span>{cnt[3]}개 회차</span></a>
<a class="tile gold" href="/suneung/"><b>수능</b><span>{cnt["sn"]}개 학년도</span></a>
</div>'''
recent = '<div class="card"><h2>최근 회차</h2><div class="chips">' + ''.join(
    f'<a class="chip" href="{s_url(k)}">{e(s_name(k))}</a>' for k in latest) + '</div></div>'
en_sess = sorted([k for k in sessions if k[0] == 'moe' and '영어' in {r['subject'] for r in sessions[k]}], key=lambda k: (k[1], -k[2], -k[3]))
note_files = sum(len(NOTES[k]) for k in en_sess)
word_sess = [k for k in en_sess if k in WORDS]
body = f'''<section class="hero"><h1>리카수니 영어 자료실</h1>
<p>고1·고2·고3 영어 모의고사를 회차별로 정리했어요. 리카수니 원장이 직접 만든 <b>분석노트·변형문제·단어</b>를 무료로 받아 가세요.</p></section>
<button class="push-btn push-bar" type="button"><span class="pi">🔔</span><span class="pt">새 자료 알림 받기</span><small>새 분석노트·해설이 올라오면 휴대폰으로 바로 알려 드려요</small></button>
<section class="card" id="push-news" hidden><h2>최근 알림</h2><ul></ul></section>
<h2 class="sec-h">영어 모의고사 핵심 자료</h2>
<div class="svc">
<a class="svc-c c3" href="/english/"><b>문항별 분석노트</b><span>18~29번·41~45번 바로 보기, 30~40번 최신 자료는 카톡 요청</span><em>{note_files}개 문항</em></a>
<a class="svc-c c2" href="/variants/"><b>변형문제</b><span>문항별 변형문제 PDF 전체 공개</span><em>{len(var_sess)}개 회차 · {var_files}개 문항</em></a>
<a class="svc-c c5" href="/english/#words"><b>영어 단어 총정리</b><span>회차별 18~45번 핵심 어휘 정리</span><em>{len(word_sess)}개 회차</em></a>
<a class="svc-c c4" href="/books/"><b>부교재 자료</b><span>수능특강 라이트·올림포스 등 분석노트·단어</span><em>{{NBOOKS}}권</em></a>
</div>
{memo_home}
<a class="ns-banner" href="/naesin/"><b>🔒 학교별 영어 내신 분석 <small>코코스 학원생 전용</small></b><span>{" · ".join(x["short"] for x in NAESIN)}</span><em>학교 목록 보기 →</em></a>
<section id="recent-cmt"><div class="rc-head"><span class="rc-live"><i></i>실시간</span><b class="rc-title">자료 요청 · 소통하기</b></div>
<div class="rc-body"><p class="rc-tip">없는 분석노트도 <b>카카오로 로그인</b>한 뒤 <b>요청</b>하면 원장님이 만들어 <b>카톡으로</b> 보내 드려요. 로그인할 때 <b>카톡 메시지 받기</b>에 동의해 주셔야 받을 수 있어요. 궁금한 점은 아래 <b>소통하기</b>에 남겨 주세요.<button type="button" class="rc-login" onclick="showLogin()">💬 카카오로 로그인</button></p>
<div class="rc-list"><p class="muted">불러오는 중...</p></div>
<div id="talk" class="tk-in"><div class="tk-h"><b>소통하기</b><span>공부·자료·수업 무엇이든 원장님께 물어보세요</span></div>
<div class="tk-form"></div><div class="tk-list"><p class="muted">불러오는 중...</p></div></div></div></section>
<h2 class="sec-h">최근 영어 모의고사</h2>
<div class="card"><div class="chips">''' + ''.join(
    f'<a class="chip" href="{subj_url(k, "영어")}">{e(s_name(k))}</a>' for k in sorted(en_sess, key=lambda k: (-k[2], -k[3], k[1]))[:9]) + '''</div>
<p><a href="/english/">영어 모의고사 전체 회차 보기 →</a></p></div>''' + ad() + f'''
<h2 class="sec-h">전과목 기출문제</h2>
<p class="muted">국어·수학·사회·과학·한국사까지 전과목 문제지·정답·해설 PDF도 함께 제공해요. 총 {len(sessions)}개 회차, {len(R):,}개 파일.</p>''' + tiles

# ---------- 영어 모의고사 허브 ----------
def en_table(g):
    ks = [k for k in en_sess if k[1] == g]
    if not ks: return ''
    rows = ''
    for k in sorted(ks, key=lambda k: (-k[2], -k[3])):
        nn = len(NOTES.get(k, {})); vv = len(dict(VAR.get(k, [])))
        mark = lambda ok, t: f'<span class="ok">{t}</span>' if ok else '<span class="no">–</span>'
        rows += (f'<tr><td><a href="{subj_url(k, "영어")}">{e(s_name(k))}</a></td>'
                 f'<td>{mark(nn, f"{nn}문항")}</td><td>{mark(vv, f"{vv}문항")}</td><td>{mark(k in WORDS, "✓")}</td></tr>')
    return (f'<div class="card g-panel" id="go{g}" data-g="{g}"><h2>고{g} 영어 모의고사</h2><table class="en-t"><thead><tr><th>회차</th><th>분석노트</th><th>변형문제</th><th>단어</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')
enbody = ('''<h1 class="page-h1">영어 모의고사 분석노트·변형문제·단어</h1>
<p class="lead">회차를 누르면 문항별 분석노트, 변형문제, 단어 총정리, 영어 기출 원본을 한 페이지에서 볼 수 있어요.
<b>30~40번 분석노트는 최근 업데이트 자료</b>라 카카오톡 요청으로 받을 수 있어요.</p>'''
          # 고1·고2·고3 탭: 누른 학년 표만 보임 (JS 없으면 세 표 모두 보임), 고른 학년은 주소(#go2)와 브라우저에 기억
          + '<div class="g-tabs" role="tablist">' + ''.join(
              f'<button type="button" class="g-tab" role="tab" data-g="{g}">고{g}<small>{sum(1 for k in en_sess if k[1] == g)}회차</small></button>'
              for g in (1, 2, 3) if any(k[1] == g for k in en_sess)) + '</div>'
          + en_table(1) + en_table(2) + en_table(3) + ad()
          + '''<script>(function(){var t=document.querySelectorAll('.g-tab'),p=document.querySelectorAll('.g-panel');
function show(g){t.forEach(function(b){var on=b.dataset.g==g;b.classList.toggle('on',on);b.setAttribute('aria-selected',on)});
p.forEach(function(x){x.hidden=x.dataset.g!=g});try{localStorage.setItem('enGrade',g)}catch(e){}}
t.forEach(function(b){b.onclick=function(){show(b.dataset.g);history.replaceState(null,'','#go'+b.dataset.g)}});
var h=(location.hash.match(/go([123])/)||[])[1],s=null;try{s=localStorage.getItem('enGrade')}catch(e){}
show(h||s||'1')})();</script>''')
page('/english/', '영어 모의고사 분석노트·변형문제·단어 PDF | 리카수니 자료실',
     '고1·고2·고3 영어 모의고사 회차별 문항 분석노트, 변형문제, 영어 단어 총정리 PDF 무료. 리카수니 원장 직접 제작.', enbody,
     [('/', '홈'), ('/english/', '영어 모의고사')], '/english/')

# ---------- 기출문제 허브 ----------
ebody = f'''<h1 class="page-h1">모의고사·수능 기출문제 전과목 PDF</h1>
<p class="lead">학년을 고르면 연도·월별 회차가 나와요. 회차마다 전과목 문제지·정답·해설과 등급컷을 볼 수 있어요. 총 {len(sessions)}개 회차, {len(R):,}개 파일.</p>''' + tiles + recent + ad()
page('/exams/', '모의고사·수능 기출문제 전과목 PDF | 리카수니 자료실', '고1·고2·고3 모의고사와 수능 기출문제 전과목 문제지·정답·해설 PDF를 학년·연도·월별로 무료 다운로드.',
     ebody, [('/', '홈'), ('/exams/', '기출문제')], '/exams/')

# ---------- 변형문제 모음 ----------
def var_block(g):
    ks = [k for k in var_sess if k[1] == g]
    if not ks: return ''
    out = f'<div class="card"><h2>고{g} 영어 변형문제</h2>'
    for y in sorted({k[2] for k in ks}, reverse=True):
        out += f'<p class="grp">{y}년</p><div class="chips">' + ''.join(
            f'<a class="chip" href="{subj_url(k, "영어")}#var">{k[3]}월<small>{len(dict(VAR[k]))}문항</small></a>'
            for k in sorted([x for x in ks if x[2] == y], key=lambda x: x[3])) + '</div>'
    return out + '</div>'
vbody = ('''<h1 class="page-h1">모의고사 영어 변형문제 (무료)</h1>
<p class="lead">리카수니 원장이 전국연합학력평가 영어 지문으로 직접 만든 문항별 변형문제예요. 회차를 고르면 18번부터 45번까지 번호별 PDF를 바로 받을 수 있어요.</p>'''
         + var_block(1) + var_block(2) + '''<div class="card"><h2>이용 방법</h2><ul class="sum">
<li>회차를 누르면 해당 회차 영어 페이지의 변형문제로 이동해요.</li>
<li>번호를 누르면 PDF 미리보기가 열리고, 그 화면에서 바로 내려받을 수 있어요.</li>
<li>같은 페이지에서 원본 기출문제와 문항별 분석노트(카톡 요청)도 함께 이용할 수 있어요.</li>
</ul></div>''' + ad())
page('/variants/', '고1·고2 모의고사 영어 변형문제 PDF 무료 | 리카수니 자료실',
     '전국연합학력평가 고1·고2 영어 문항별 변형문제 PDF 무료 다운로드. 리카수니 원장 직접 제작.', vbody,
     [('/', '홈'), ('/variants/', '변형문제')], '/variants/')

nbody = '''<h1 class="page-h1">모의고사·부교재 영어 분석노트 요청</h1>
<p class="lead">고1·고2·고3 영어 모의고사와 부교재(수능특강 라이트 등)의 문항별 분석노트를 카카오톡으로 받아보세요.</p>
<section class="card mission" id="note-req"><h2>분석노트 요청</h2><p class="muted">불러오는 중...</p></section>
<div class="card"><h2>이용 방법</h2><ul class="sum">
<li>카카오로 로그인한 회원만 요청할 수 있어요.</li>
<li>모의고사는 연도·월·학년·번호를, 부교재는 교재·강·번호를 골라 요청해요. (예: 2026년 9월 고1 30번, 수능특강 라이트 20강 1번)</li>
<li>요청하면 카카오톡 '나와의 채팅'으로 분석노트 링크가 바로 와요.</li>
<li>하루에 모의고사 2개, 부교재 1개까지 받을 수 있고, 링크는 24시간 동안 열려요.</li><li>번호를 <b>하나씩</b> 골라 받아요. 모의고사는 하나를 받은 뒤 "다른 번호 받기"를 눌러 두 번째 번호를 받을 수 있어요.</li>
<li>아직 준비되지 않은 자료는 원장님께 요청이 전달돼요. 준비에 1~2일 걸리니 그 뒤에 다시 요청해 주세요. (그날 요청 횟수는 차감되지 않아요)</li>
</ul></div>''' + ad()
page('/notes/', '영어 모의고사·수능특강 분석노트 요청 | 리카수니 자료실',
     '고1·고2·고3 영어 모의고사와 수능특강 라이트 문항별 분석노트를 카카오톡으로 받아보세요. 하루 모의고사 2개·부교재 1개.', nbody,
     [('/', '홈'), ('/notes/', '분석노트 요청')], '/notes/', comments=('notes', '분석노트 요청'))

# ---------- 부교재 요청방 ----------
# 새 부교재는 BOOKS 에 한 줄 추가 (name 은 lib.js NOTE_BOOKS, note-request 함수 BOOKS 와 같게)
SAMPLE = 'https://drive.google.com/file/d/105f20gSuhZvR44gCK6oW5mxn2-ZFG12J/view'  # 샘플은 수능특강 라이트로 통일
BOOKS = [  # name 은 드라이브 '부교재 분석노트' 안 폴더 이름과 같게 (lib.js NOTE_BOOK_CFG, note-request 함수 BOOKS 와 같게)
    dict(cover='suteuk-light', name='수능특강 라이트', full='2026 EBS 수능특강 Light 영어', meta='22강 · 강별 Gateway + 문항별', who='고1~고2 · 수능특강 입문',
         intro='수능특강 본책 전에 유형별 감을 잡는 EBS 입문 교재예요. 강마다 Gateway와 문항별로 끊어읽기·구문·어휘·정답 근거를 정리한 분석노트를 제공해요.',
         buy='https://contents.premium.naver.com/likasuni/cocos/contents?categoryId=1a0c882e9770000nk', ready=True),
    dict(cover='haru6-go1', name='하루 6개 1등급 모의고사 고1', full='EBS 하루 6개 1등급 영어독해 모의고사 고1', meta='회차별 6문항', who='고1 · 모의고사 대비',
         intro='하루 6문항씩 모의고사 유형을 꾸준히 푸는 EBS 고1 독해 교재예요. 회차·문항별 분석노트를 준비하고 있어요.'),
    dict(cover='haru6-go2', name='하루 6개 1등급 모의고사 고2', full='EBS 하루 6개 1등급 영어독해 모의고사 고2', meta='회차별 6문항', who='고2 · 모의고사 대비',
         intro='하루 6문항씩 모의고사 유형을 꾸준히 푸는 EBS 고2 독해 교재예요. 회차·문항별 분석노트를 준비하고 있어요.'),
    dict(cover='olympos-gichul-go1', name='올림포스 전국연합학력평가 기출문제집 고1', full='EBS 올림포스 전국연합학력평가 기출문제집 고1 영어', meta='20강 · 강별 예시문제 + 1~12번', who='고1 · 모의고사 기출',
         intro='고1 전국연합학력평가 기출을 유형별 20강으로 묶은 EBS 문제집이에요. 강별 예시문제와 1~12번 분석노트를 준비하고 있어요.'),
    dict(cover='olympos-gichul-go2', name='올림포스 전국연합학력평가 기출문제집 고2', full='EBS 올림포스 전국연합학력평가 기출문제집 고2 영어', meta='20강 · 강별 예시문제 + 1~12번', who='고2 · 모의고사 기출',
         intro='고2 전국연합학력평가 기출을 유형별 20강으로 묶은 EBS 문제집이에요. 강별 예시문제와 1~12번 분석노트를 준비하고 있어요.'),
    dict(cover='olympos-basic1', name='올림포스 영어독해 기본1', full='EBS 올림포스 영어독해의 기본 1', meta='강별 문항', who='고1 · 내신 부교재',
         intro='학교 내신 부교재로 많이 쓰는 EBS 고등 기본 독해 교재예요. 강·문항별 분석노트를 준비하고 있어요.'),
    dict(cover='readingpower-basic', name='리딩파워 기본', full='리딩파워 기본', meta='강별 문항', who='고1~고2 · 독해 기본',
         intro='유형별 독해 기본기를 다지는 교재예요. 강·문항별 분석노트를 준비하고 있어요.'),
    dict(cover='readingpower-complete', name='리딩파워 완성', full='리딩파워 완성', meta='강별 문항', who='고2~고3 · 독해 완성',
         intro='유형별 독해를 실전 수준으로 완성하는 교재예요. 강·문항별 분석노트를 준비하고 있어요.'),
]
def book_words(b):  # '부교재 단어' 폴더 중 교재 이름의 단어가 모두 들어간 폴더 (가장 짧은 이름)
    ws = b['name'].split()
    cands = [f for f in BWORDS if all(w in f.replace('_', ' ') for w in ws)]
    if not cands: return []
    f = min(cands, key=len)
    def lab(t):
        m = _re.search(r'(\d+)\s*강', t) or _re.search(r'(\d+)\s*회', t)
        if '실전' in t and m: return f'실전 {m.group(1)}회'
        return f'{m.group(1)}강' if m else t.rsplit('.', 1)[0][-12:]
    def order(t):
        m = _re.search(r'(\d+)', t.split('_')[-2] if '_' in t else t)
        return (('실전' in t), int(m.group(1)) if m else 999)
    return [(lab(t), i) for t, i in sorted(BWORDS[f], key=lambda x: order(x[0]))]
# 표지 이미지: img/books/<cover>.jpg (또는 .png/.webp) 를 올리면 자동으로 표시, 없으면 기본 표지
def book_cover(b):
    for ext in ('jpg', 'jpeg', 'png', 'webp'):
        f = f'img/books/{b["cover"]}.{ext}'
        if os.path.exists(os.path.join(ROOT, f)):
            return f'<div class="book-cover"><img src="/{f}" alt="{e(b["full"])} 표지" loading="lazy" width="320" height="400"></div>'
    pub = 'EBS' if b['full'].startswith('EBS') or 'EBS' in b['full'] else '부교재'
    return (f'<div class="book-cover ph"><span class="ph-pub">{e(pub)}</span>'
            f'<b>{e(b["name"])}</b><span class="ph-who">{e(b["who"].split(" · ")[0])}</span></div>')
def book_card(b):
    wl = book_words(b)
    words = ('<div class="bw"><b>단어 학습노트 (무료)</b><div class="chips">' + ''.join(
        f'<a class="chip" href="{view(i)}" target="_blank" rel="noopener">{e(l)}</a>' for l, i in wl) + '</div></div>') if wl else ''
    q = urllib.parse.quote(b['name'])
    blog = f'<a class="btn btn-line" href="{e(b["blog"])}">교재 소개글</a>' if b.get('blog') else ''
    return (f'<section class="card book b-panel" id="book-{b["cover"]}" data-b="{b["cover"]}"><div class="book-top">{book_cover(b)}<div class="book-info">'
            f'<div class="book-hd"><h2>{e(b["full"])}</h2><span class="tag">{e(b["who"])}</span></div>'
            f'<p>{e(b["intro"])}</p>'
            f'<ul class="book-meta"><li>{e(b["meta"])}</li><li>리카수니 원장이 직접 만든 분석노트</li></ul></div></div>' + words
            + ('<div class="book-use"><div><b>무료</b><span>카톡으로 하루 1문항</span></div><div><b>유료</b><span>강 단위로 필요한 만큼 구매</span></div></div>'
               if b.get('ready') else
               '<p class="book-soon">분석노트 준비 중이에요. 필요한 강·번호를 요청해 주시면 요청이 많은 것부터 먼저 만들어요.</p>')
            + f'<div class="book-btns"><a class="btn btn-kakao" href="/notes/?book={q}">{"카톡으로 무료 요청" if b.get("ready") else "이 교재 분석노트 요청하기"}</a>'
            + (f'<a class="btn btn-navy" href="{e(b["buy"])}" target="_blank" rel="noopener">강 단위 구매</a>' if b.get('buy') else '')
            + f'<a class="btn btn-line" href="{SAMPLE}" target="_blank" rel="noopener">분석노트 샘플 보기</a>{blog}</div></section>')
bbody = ('<h1 class="page-h1">부교재 영어 분석노트 요청방</h1>'
         '<p class="lead">리카수니 원장이 직접 만든 부교재 분석노트예요. <b>문항 1개는 카톡으로 무료</b>, 강 전체가 필요하면 <b>강 단위로 구매</b>할 수 있어요.</p>'
         # 교재 책장: 표지를 누르면 그 교재 상세만 보임 (JS 없으면 모두 보임), 고른 교재는 주소(#book-…)와 브라우저에 기억
         + '<div class="shelf">' + ''.join(
             f'<button type="button" class="shelf-b" data-b="{b["cover"]}">{book_cover(b)}<span>{e(b["name"])}</span>'
             f'<em class="{"ready" if b.get("ready") else ""}">{"분석노트 제공" if b.get("ready") else "준비 중"}</em></button>' for b in BOOKS) + '</div>'
         + ''.join(book_card(b) for b in BOOKS)
         + '''<script>(function(){var t=document.querySelectorAll('.shelf-b'),p=document.querySelectorAll('.b-panel');
function show(c,go){var ok=false;t.forEach(function(b){var on=b.dataset.b==c;ok=ok||on;b.classList.toggle('on',on);b.setAttribute('aria-pressed',on)});
if(!ok)return false;p.forEach(function(x){x.hidden=x.dataset.b!=c});try{localStorage.setItem('bookSel',c)}catch(e){}
if(go){var el=document.getElementById('book-'+c);el&&el.scrollIntoView({behavior:'smooth',block:'start'})}return true}
t.forEach(function(b){b.onclick=function(){show(b.dataset.b,true);history.replaceState(null,'','#book-'+b.dataset.b)}});
var h=(location.hash.match(/^#book-(.+)/)||[])[1],s=null;try{s=localStorage.getItem('bookSel')}catch(e){}
show(h,true)||show(s)||show(t[0]&&t[0].dataset.b)})();</script>''' +
         '<div class="card"><h2>이용 방법</h2><ul class="sum">'
         "<li><b>무료 요청:</b> 카카오 로그인 후 교재·강·번호를 고르면 카카오톡 '나와의 채팅'으로 24시간 링크가 와요. 부교재는 하루 1개 (모의고사는 따로 하루 2개).</li>"
         '<li><b>유료 구매:</b> 네이버 프리미엄 콘텐츠에서 필요한 강만 골라 구매해요.</li>'
         '<li><b>샘플:</b> 먼저 샘플을 보고 분석노트 구성을 확인해 보세요.</li>'
         '<li>아직 준비되지 않은 강·번호는 원장님께 요청이 전달돼요. 1~2일 뒤 다시 요청해 주세요.</li>'
         '<li>다른 부교재 분석노트가 필요하면 아래 댓글로 교재 이름을 남겨 주세요. 요청이 많은 교재부터 추가해요.</li>'
         '</ul></div>' + ad())
if BOOKNEWS:
    bbody = bbody.replace('</p>', '</p>' + f'<div class="card"><style>{NEWS_CSS}</style><h2>📚 교재 소식</h2>{book_groups(BOOKNEWS, 3)}'
                          + f'<p style="margin:10px 0 0"><a href="/books/news/">교재 소식 전체 보기 ({len(BOOKNEWS)}개) →</a></p></div>', 1)
page('/books/', 'EBS 부교재 영어 분석노트 요청 · 수능특강 라이트 | 리카수니 자료실',
     '수능특강 라이트 등 EBS 부교재 영어 분석노트. 문항 1개는 카카오톡으로 무료, 강 단위 구매도 가능. 리카수니 원장 직접 제작.', bbody,
     [('/', '홈'), ('/books/', '부교재')], '/books/', comments=('books', '부교재 요청방'))

page('/', '리카수니 자료실 | 모의고사·수능 기출문제 PDF, 영어 변형문제, 분석노트',
     '고1·고2·고3 모의고사와 수능 기출문제 전과목 PDF, 리카수니 영어 변형문제와 문항별 분석노트를 무료로. 리카수니 자료실', body.replace('{NBOOKS}', str(len(BOOKS))), (), '/',
     extra_ld=[{"@context": "https://schema.org", "@type": "WebSite", "name": "리카수니 자료실",  # 검색 결과 사이트 이름
                "alternateName": ["리카수니", "Likasuni"], "url": SITE + '/'}])

# ---------- sitemap / robots ----------
# 사이트맵: 구글이 새 사이트를 조금씩 읽으니 내용 많은 페이지만, 중요한 순서로 (얇은 영어 외 과목 페이지는 사이트엔 그대로 두고 사이트맵에서만 뺌)
def _sm_rank(p):
    q = p.strip('/').split('/')
    if p == '/': return 0
    if q[0] == 'naesin': return 1
    if p in ('/english/', '/posts/', '/books/', '/variants/', '/exams/', '/notes/', '/memo/', '/news/'): return 2
    if q[0] == 'news': return 3  # 학원 소식
    if p == '/books/news/': return 2
    if q[0] == 'books' and len(q) == 3 and q[1] == 'news': return 3  # 교재 소식
    if q[0] == 'memo': return 3  # 원장님 노트
    if q[0] in ('moe', 'suneung') and q[-1].isdigit() or '-' in q[-1] and q[-2:-1] == ['eng']: return 3  # 문항별 해설
    if q[0] in ('moe', 'suneung') and q[-1] == 'eng': return 4  # 회차별 영어
    if q[0] in ('moe', 'suneung') and (len(q) <= 3 and (q[0] == 'moe' or len(q) <= 2)): return 5  # 학년 목록·회차·수능 학년도
    return None
_sm = sorted([p for p in PAGES if _sm_rank(p) is not None], key=lambda p: (_sm_rank(p), -PAGES.index(p) if _sm_rank(p) in (3, 4) else PAGES.index(p)))
urls = ''.join(f'<url><loc>{SITE}{p}</loc>' + (f'<lastmod>{LASTMOD[p]}</lastmod>' if p in LASTMOD else '') + '</url>' for p in _sm)
open(os.path.join(ROOT, 'sitemap.xml'), 'w').write(
    f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
open(os.path.join(ROOT, 'robots.txt'), 'w').write(f'User-agent: *\nAllow: /\nDisallow: /admin.html\nDisallow: /get/\nSitemap: {SITE}/sitemap.xml\n')
print('pages', len(PAGES), 'sessions', len(sessions), 'files', len(R))
