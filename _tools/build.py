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
AD_SLOT = '1035299275'          # 반응형 디스플레이 광고
TODAY = datetime.date.today().isoformat()

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
    m = _re.search(r'(\d{4})\s*(년|학년도)[\s_]*(\d{1,2})\s*월[\s_]*고\s*(\d)', t)
    nm = _re.search(r'[_\s](\d{1,2}(?:\s*[~-]\s*\d{1,2})?)\s*번', t)
    if not m or not nm: continue
    y, mo, g = int(m.group(1)), int(m.group(3)), int(m.group(4))
    if g == 3 and mo in (6, 9) and m.group(2) == '년': y += 1  # 고3 모의평가는 학년도 기준 회차로
    VAR[('moe', g, y, mo)].append((nm.group(1).replace(' ', '').replace('-', '~'), v['id']))
def vkey(n): return int(_re.match(r'\d+', n).group())

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
    for s in sorted({r['subject'] for r in rs}, key=lambda x: SUBJ_ORDER.index(x) if x in SUBJ_ORDER else 99):
        d[s] = sorted([r for r in rs if r['subject'] == s], key=lambda r: KIND_ORDER.index(r['kind']))
    return d

# ---------- 공통 레이아웃 ----------
NAV = [('/', '홈'), ('/english/', '🇬🇧 영어 모의고사'), ('/books/', '📚 부교재'), ('/exams/', '📄 전과목 기출'), ('/notes/', '📘 분석노트 요청')]

def ad():
    return (f'<div class="ad-slot"><ins class="adsbygoogle" style="display:block" data-ad-client="{ADS_CLIENT}" '
            f'data-ad-slot="{AD_SLOT}" data-ad-format="rectangle, horizontal" data-full-width-responsive="true"></ins>'
            f'<script>(adsbygoogle=window.adsbygoogle||[]).push({{}});</script></div>')

def page(path, title, desc, body, crumbs=(), active='/', comments=None):
    url = SITE + path
    ld = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u} for i, (u, n) in enumerate(crumbs)]}] if crumbs else []
    crumb_html = ('<nav class="crumb">' + ' › '.join(f'<a href="{u}">{e(n)}</a>' for u, n in crumbs) + '</nav>') if crumbs else ''
    act = '/exams/' if (active.startswith('/moe/') or active == '/suneung/') else ('/english/' if active == '/variants/' else active)  # 학년별·수능 페이지는 '기출문제' 메뉴에 불이 들어옴
    nav = ''.join(f'<a href="{u}" class="{"on " if u == act else ""}">{n}</a>' for u, n in NAV)
    cm = ''
    if comments:
        cm = f'<section class="card" id="comments" data-page-key="{e(comments[0])}" data-page-title="{e(comments[1])}"><h2>💬 댓글</h2><p class="muted">댓글 불러오는 중...</p></section>'
    out = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="리카수니 자료실">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/og.png">
<meta name="google-site-verification" content="BckdSBCPVseYvq2HonB5Q7G9pfCOG10GZvoCOIoK4sk">
<meta name="naver-site-verification" content="7e1745db79feaa04ab25201be2de4645c4641c34">
<link rel="icon" href="/favicon.png">
<style>{CSS}</style>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADS_CLIENT}" crossorigin="anonymous"></script>
{''.join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)}
</head>
<body>
<header class="top"><div class="top-in"><a class="brand" href="/">리카수니 <b>자료실</b></a><div class="top-r"><a class="hdr-cta" href="/notes/">📘 분석노트 요청</a><div class="auth" id="auth"><button class="btn btn-gold btn-sm" onclick="lazyLogin()">로그인</button></div></div></div></header>
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
<script>
/* 로그인·댓글 기능은 필요할 때만 불러옴: 로그인했던 회원 / 댓글 영역 근처까지 스크롤 / 로그인 버튼 클릭 */
(function () {{
  var done = false, after = null, srcs = ['https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.58.0/dist/umd/supabase.js', '/common.js?v=2', '/lib.js?v=11'];
  function next(i) {{ if (i >= srcs.length) {{ if (after) after(); return; }} var s = document.createElement('script'); s.src = srcs[i]; s.onload = function () {{ next(i + 1); }}; document.body.appendChild(s); }}
  function go() {{ if (!done) {{ done = true; next(0); }} }}
  window.lazyLogin = function () {{ after = function () {{ showLogin(); }}; if (done) {{ if (window.showLogin) showLogin(); }} else go(); }};
  /* 광고 차단으로 광고 스크립트 자체가 안 불러와졌을 때만 확보해 둔 자리를 접음 */
  addEventListener('load', function () {{ setTimeout(function () {{ if (window.adsbygoogle && window.adsbygoogle.loaded) return; document.querySelectorAll('.ad-slot').forEach(function (d) {{ d.style.display = 'none'; }}); }}, 8000); }});
  var had = false; try {{ had = !!localStorage.getItem('sb-iiyhmskvdjgstoikonwu-auth-token'); }} catch (e) {{}}
  if (had || location.hash.indexOf('access_token') > -1) {{ go(); return; }}
  var els = ['note-req', 'comments'].map(function (id) {{ return document.getElementById(id); }}).filter(Boolean);
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
        note_banner = (f'<a class="banner note" href="/notes/?y={k[2]}&m={k[3]}&g={k[1]}"><b>📘 이 회차 영어 문항별 분석노트, 카톡으로 받기</b>'
                       '<p>번호만 고르면 카카오톡으로 바로 보내드려요. 1인 하루 1개 · 링크 24시간</p></a>')
    info_html = ''
    if inf.get('summary'):
        info_html += '<div class="card"><h2>📝 시험 요약</h2>' + (f'<p class="muted">{e(inf["date"])}</p>' if inf.get('date') else '') + \
                     '<ul class="sum">' + ''.join(f'<li>{e(x)}</li>' for x in inf['summary']) + '</ul></div>'
    if inf.get('rows'):
        info_html += f'<div class="card"><h2>📊 {e(name)} 등급컷</h2>{cut_table(inf["rows"])}{CUT_NOTE}</div>'
    else:
        info_html += '<div class="card"><h2>📊 등급컷</h2><p class="muted">확정 등급컷을 정리하고 있어요. 확인되는 대로 업데이트할게요.</p></div>'
    if inf.get('wrong'):
        info_html += '<div class="card"><h2>🔥 오답이 많았던 문항</h2><table class="info">' + ''.join(
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
            en_top = (f'''<section class="card en-sec" id="notes"><h2>📘 문항별 분석노트</h2>
<div class="legend"><span><i class="nb open"></i>바로 보기</span><span><i class="nb req"></i>카톡 요청</span><span><i class="nb off"></i>준비 중</span></div>
<p class="hot">🔥 <b>30~40번은 최근 업데이트 자료</b>예요. 번호를 누르고 아래 요청 칸에서 카카오톡으로 받아 가세요. (1인 하루 1개)</p>
<div class="nbs">''' + ''.join(nbtn(n) for n in NOTE_NUMS) + '</div></section>' + ad()
                + ('<section class="card en-sec" id="var"><h2>✏️ 변형문제 <small>무료 · 번호별 전체 공개</small></h2><div class="nbs">'
                   + ''.join(f'<a class="nb var" href="{view(i)}" target="_blank" rel="noopener">{e(n)}번</a>' for n, i in vs0) + '</div></section>'
                   if vs0 else '<section class="card en-sec" id="var"><h2>✏️ 변형문제</h2><p class="muted">이 회차 변형문제는 준비 중이에요.</p></section>') + ad()
                + (f'<section class="card en-sec" id="words"><h2>📝 영어 단어 총정리</h2><p class="muted">이 회차 18~45번 지문의 핵심 어휘를 한 장에 정리했어요.</p><div class="dl"><a href="{view(wd)}" target="_blank" rel="noopener">미리보기</a><a href="{down(wd)}" rel="noopener">다운로드</a></div></section>'
                   if wd else '<section class="card en-sec" id="words"><h2>📝 영어 단어 총정리</h2><p class="muted">이 회차 단어 자료는 준비 중이에요.</p></section>'))
        if s == '영어':
            pre = f' data-y="{k[2]}" data-m="{k[3]}" data-g="{k[1]}"' if k[0] == 'moe' else ''
            vs = sorted(dict(VAR.get(k, [])).items(), key=lambda x: vkey(x[0]))
            var_html = ('<div class="soon"><b>변형문제</b> · 준비 중이에요</div>' if not vs else
                        '<div class="var" id="var"><b>✏️ 리카수니 변형문제 (무료)</b><p class="muted">번호를 누르면 PDF가 열려요. 미리보기 화면에서 바로 내려받을 수 있어요.</p><div class="chips">'
                        + ''.join(f'<a class="chip" href="{view(i)}" target="_blank" rel="noopener">{e(n)}번</a>' for n, i in vs) + '</div></div>')
            extra = f'''<section class="card mission" id="note-req"{pre}><h2>📘 분석노트 카톡 요청 <small>30~40번 · 최신 자료</small></h2><p class="muted">이 회차 30~40번 분석노트를 카카오톡으로 받을 수 있어요. 불러오는 중...</p></section>'''
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
            sinfo = f'<div class="card"><h2>📊 {e(full)} 등급컷</h2>' + (cut_table(srows) + CUT_NOTE if srows else '') + \
                    (f'<p><b>오답이 많았던 문항</b> · {e(inf["wrong"][s])}</p>' if (inf.get('wrong') or {}).get(s) else '') + \
                    f'<p><a href="{s_url(k)}">{e(name)} 전체 요약·등급컷 보기 →</a></p></div>'
        if en_top:
            body = f'''<h1 class="page-h1">{e(full)} 분석노트·변형문제·단어</h1>
<p class="lead">{e(s_when(k))} · 리카수니 원장이 직접 만든 영어 자료와 기출 원본을 한곳에 모았어요.</p>
{en_top}
{extra}
{ad()}
<div class="card"><h2>📄 {e(full)} 기출 원본</h2>{files}</div>
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
        if en_top:
            page(subj_url(k, s), f'{full} 분석노트·변형문제·단어 PDF | 리카수니 자료실',
                 f'{full} 문항별 분석노트, 변형문제, 영어 단어 총정리와 기출 원본 PDF 무료. 리카수니 자료실',
                 body, crumbs + [(subj_url(k, s), sn)], '/english/', comments=(subj_url(k, s).strip('/'), full))
        else:
            page(subj_url(k, s), f'{full} 기출문제·해설 PDF 다운로드 | 리카수니 자료실',
                 f'{full} 문제지·정답·해설 PDF 무료 다운로드. {s_when(k)}. 리카수니 자료실',
                 body, crumbs + [(subj_url(k, s), sn)], active, comments=(subj_url(k, s).strip('/'), full))

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
var_files = sum(len(dict(VAR[k])) for k in var_sess)
tiles = f'''<div class="grid4">
<a class="tile" href="/moe/go1/"><b>고1</b><span>{cnt[1]}개 회차</span></a>
<a class="tile" href="/moe/go2/"><b>고2</b><span>{cnt[2]}개 회차</span></a>
<a class="tile" href="/moe/go3/"><b>고3</b><span>{cnt[3]}개 회차</span></a>
<a class="tile gold" href="/suneung/"><b>수능</b><span>{cnt["sn"]}개 학년도</span></a>
</div>'''
recent = '<div class="card"><h2>🆕 최근 회차</h2><div class="chips">' + ''.join(
    f'<a class="chip" href="{s_url(k)}">{e(s_name(k))}</a>' for k in latest) + '</div></div>'
en_sess = sorted([k for k in sessions if k[0] == 'moe' and '영어' in {r['subject'] for r in sessions[k]}], key=lambda k: (k[1], -k[2], -k[3]))
note_files = sum(len(NOTES[k]) for k in en_sess)
word_sess = [k for k in en_sess if k in WORDS]
body = f'''<section class="hero"><h1>리카수니 영어 자료실</h1>
<p>고1·고2·고3 영어 모의고사를 회차별로 정리했어요. 리카수니 원장이 직접 만든 <b>분석노트·변형문제·단어</b>를 무료로 받아 가세요.</p></section>
<h2 class="sec-h">🇬🇧 영어 모의고사 핵심 자료</h2>
<div class="svc">
<a class="svc-c c3" href="/english/"><i>📘</i><b>문항별 분석노트</b><span>18~29번·41~45번 바로 보기, 30~40번 최신 자료는 카톡 요청</span><em>{note_files}개 문항</em></a>
<a class="svc-c c2" href="/variants/"><i>✏️</i><b>변형문제</b><span>문항별 변형문제 PDF 전체 공개</span><em>{len(var_sess)}개 회차 · {var_files}개 문항</em></a>
<a class="svc-c c5" href="/english/#words"><i>📝</i><b>영어 단어 총정리</b><span>회차별 18~45번 핵심 어휘 정리</span><em>{len(word_sess)}개 회차</em></a>
<a class="svc-c c4" href="/books/"><i>📚</i><b>부교재 자료</b><span>수능특강 라이트·올림포스 등 분석노트·단어</span><em>{{NBOOKS}}권</em></a>
</div>
<h2 class="sec-h">🆕 최근 영어 모의고사</h2>
<div class="card"><div class="chips">''' + ''.join(
    f'<a class="chip" href="{subj_url(k, "영어")}">{e(s_name(k))}</a>' for k in sorted(en_sess, key=lambda k: (-k[2], -k[3], k[1]))[:9]) + '''</div>
<p><a href="/english/">영어 모의고사 전체 회차 보기 →</a></p></div>''' + ad() + f'''
<h2 class="sec-h">📄 전과목 기출문제</h2>
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
    return (f'<div class="card"><h2>고{g} 영어 모의고사</h2><table class="en-t"><thead><tr><th>회차</th><th>📘 분석노트</th><th>✏️ 변형문제</th><th>📝 단어</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')
enbody = ('''<h1 class="page-h1">영어 모의고사 분석노트·변형문제·단어</h1>
<p class="lead">회차를 누르면 문항별 분석노트, 변형문제, 단어 총정리, 영어 기출 원본을 한 페이지에서 볼 수 있어요.
<b>30~40번 분석노트는 최근 업데이트 자료</b>라 카카오톡 요청으로 받을 수 있어요.</p>'''
          + en_table(1) + ad() + en_table(2) + en_table(3) + ad())
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
<section class="card mission" id="note-req"><h2>📘 분석노트 요청</h2><p class="muted">불러오는 중...</p></section>
<div class="card"><h2>이용 방법</h2><ul class="sum">
<li>카카오로 로그인한 회원만 요청할 수 있어요.</li>
<li>모의고사는 연도·월·학년·번호를, 부교재는 교재·강·번호를 골라 요청해요. (예: 2026년 9월 고1 30번, 수능특강 라이트 20강 1번)</li>
<li>요청하면 카카오톡 '나와의 채팅'으로 분석노트 링크가 바로 와요.</li>
<li>1인 하루 1개까지 받을 수 있고, 링크는 24시간 동안 열려요.</li>
<li>아직 준비되지 않은 자료는 원장님께 요청이 전달돼요. 준비에 1~2일 걸리니 그 뒤에 다시 요청해 주세요. (그날 요청 횟수는 차감되지 않아요)</li>
</ul></div>''' + ad()
page('/notes/', '영어 모의고사·수능특강 분석노트 요청 | 리카수니 자료실',
     '고1·고2·고3 영어 모의고사와 수능특강 라이트 문항별 분석노트를 카카오톡으로 받아보세요. 1인 하루 1개.', nbody,
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
    dict(cover='olympos-gichul-go1', name='올림포스 전국연합학력평가 기출문제집 고1', full='EBS 올림포스 전국연합학력평가 기출문제집 고1 영어', meta='회차별 18~45번', who='고1 · 모의고사 기출',
         intro='고1 전국연합학력평가 기출을 회차별로 모은 EBS 문제집이에요. 회차·문항별 분석노트를 준비하고 있어요.'),
    dict(cover='olympos-gichul-go2', name='올림포스 전국연합학력평가 기출문제집 고2', full='EBS 올림포스 전국연합학력평가 기출문제집 고2 영어', meta='회차별 18~45번', who='고2 · 모의고사 기출',
         intro='고2 전국연합학력평가 기출을 회차별로 모은 EBS 문제집이에요. 회차·문항별 분석노트를 준비하고 있어요.'),
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
    words = ('<div class="bw"><b>📝 단어 학습노트 (무료)</b><div class="chips">' + ''.join(
        f'<a class="chip" href="{view(i)}" target="_blank" rel="noopener">{e(l)}</a>' for l, i in wl) + '</div></div>') if wl else ''
    q = urllib.parse.quote(b['name'])
    blog = f'<a class="btn btn-line" href="{e(b["blog"])}">📝 교재 소개글</a>' if b.get('blog') else ''
    return (f'<section class="card book"><div class="book-top">{book_cover(b)}<div class="book-info">'
            f'<div class="book-hd"><h2>{e(b["full"])}</h2><span class="tag">{e(b["who"])}</span></div>'
            f'<p>{e(b["intro"])}</p>'
            f'<ul class="book-meta"><li>📚 {e(b["meta"])}</li><li>✍️ 리카수니 원장이 직접 만든 분석노트</li></ul></div></div>' + words
            + ('<div class="book-use"><div><b>무료</b><span>카톡으로 문항 1개, 하루 1번</span></div><div><b>유료</b><span>강 단위로 필요한 만큼 구매</span></div></div>'
               if b.get('ready') else
               '<p class="book-soon">📝 분석노트 준비 중이에요. 필요한 강·번호를 요청해 주시면 요청이 많은 것부터 먼저 만들어요.</p>')
            + f'<div class="book-btns"><a class="btn btn-kakao" href="/notes/?book={q}">💬 {"카톡으로 무료 요청" if b.get("ready") else "이 교재 분석노트 요청하기"}</a>'
            + (f'<a class="btn btn-navy" href="{e(b["buy"])}" target="_blank" rel="noopener">🛒 강 단위 구매</a>' if b.get('buy') else '')
            + f'<a class="btn btn-line" href="{SAMPLE}" target="_blank" rel="noopener">📄 분석노트 샘플 보기</a>{blog}</div></section>')
bbody = ('<h1 class="page-h1">부교재 영어 분석노트 요청방</h1>'
         '<p class="lead">리카수니 원장이 직접 만든 부교재 분석노트예요. <b>문항 1개는 카톡으로 무료</b>, 강 전체가 필요하면 <b>강 단위로 구매</b>할 수 있어요.</p>'
         + ''.join(book_card(b) for b in BOOKS) +
         '<div class="card"><h2>이용 방법</h2><ul class="sum">'
         "<li><b>무료 요청:</b> 카카오 로그인 후 교재·강·번호를 고르면 카카오톡 '나와의 채팅'으로 24시간 링크가 와요. 1인 하루 1개 (모의고사 요청과 합산).</li>"
         '<li><b>유료 구매:</b> 네이버 프리미엄 콘텐츠에서 필요한 강만 골라 구매해요.</li>'
         '<li><b>샘플:</b> 먼저 샘플을 보고 분석노트 구성을 확인해 보세요.</li>'
         '<li>아직 준비되지 않은 강·번호는 원장님께 요청이 전달돼요. 1~2일 뒤 다시 요청해 주세요.</li>'
         '<li>다른 부교재 분석노트가 필요하면 아래 댓글로 교재 이름을 남겨 주세요. 요청이 많은 교재부터 추가해요.</li>'
         '</ul></div>' + ad())
page('/books/', 'EBS 부교재 영어 분석노트 요청 · 수능특강 라이트 | 리카수니 자료실',
     '수능특강 라이트 등 EBS 부교재 영어 분석노트. 문항 1개는 카카오톡으로 무료, 강 단위 구매도 가능. 리카수니 원장 직접 제작.', bbody,
     [('/', '홈'), ('/books/', '부교재')], '/books/', comments=('books', '부교재 요청방'))

page('/', '리카수니 자료실 | 모의고사·수능 기출문제 PDF, 영어 변형문제, 분석노트',
     '고1·고2·고3 모의고사와 수능 기출문제 전과목 PDF, 리카수니 영어 변형문제와 문항별 분석노트를 무료로. 리카수니 자료실', body.replace('{NBOOKS}', str(len(BOOKS))), (), '/')

# ---------- sitemap / robots ----------
urls = ''.join(f'<url><loc>{SITE}{p}</loc><lastmod>{TODAY}</lastmod></url>' for p in ['/mission/', '/privacy.html'] + PAGES)
open(os.path.join(ROOT, 'sitemap.xml'), 'w').write(
    f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
open(os.path.join(ROOT, 'robots.txt'), 'w').write(f'User-agent: *\nAllow: /\nDisallow: /admin.html\nDisallow: /get/\nSitemap: {SITE}/sitemap.xml\n')
print('pages', len(PAGES), 'sessions', len(sessions), 'files', len(R))
