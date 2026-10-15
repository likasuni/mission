#!/usr/bin/env python3
"""리카수니 자료실 정적 페이지 생성기

_tools/catalog.json (구글드라이브 기출 PDF 목록)을 읽어
홈 / 학년 / 회차 / 과목 페이지와 sitemap.xml 을 저장소 루트에 만든다.
자료가 추가되면 catalog.json 만 갱신하고 다시 실행하면 된다.
"""
import json, os, html, datetime, collections, shutil

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
GROUP_NAME = {'사회': '통합사회', '과학': '통합과학'}
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
    return f'{y}년 {m}월 시행'

def subj_url(k, s): return s_url(k) + SLUG.get(s, 'etc') + '/'

def bysubj(rs):
    d = collections.OrderedDict()
    for s in sorted({r['subject'] for r in rs}, key=lambda x: SUBJ_ORDER.index(x) if x in SUBJ_ORDER else 99):
        d[s] = sorted([r for r in rs if r['subject'] == s], key=lambda r: KIND_ORDER.index(r['kind']))
    return d

# ---------- 공통 레이아웃 ----------
NAV = [('/', '홈'), ('/moe/go1/', '고1'), ('/moe/go2/', '고2'), ('/moe/go3/', '고3'), ('/suneung/', '수능'), ('/mission/', '자료 미션')]

def ad():
    return (f'<div class="ad-slot"><ins class="adsbygoogle" style="display:block" data-ad-client="{ADS_CLIENT}" '
            f'data-ad-slot="{AD_SLOT}" data-ad-format="rectangle, horizontal" data-full-width-responsive="true"></ins>'
            f'<script>(adsbygoogle=window.adsbygoogle||[]).push({{}});</script></div>')

def page(path, title, desc, body, crumbs=(), active='/', comments=None):
    url = SITE + path
    ld = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u} for i, (u, n) in enumerate(crumbs)]}] if crumbs else []
    crumb_html = ('<nav class="crumb">' + ' › '.join(f'<a href="{u}">{e(n)}</a>' for u, n in crumbs) + '</nav>') if crumbs else ''
    nav = ''.join(f'<a href="{u}"{" class=on" if u == active else ""}>{n}</a>' for u, n in NAV)
    cm = ''
    if comments:
        cm = f'<section class="card" id="comments" data-page-key="{e(comments[0])}" data-page-title="{e(comments[1])}"><p class="muted">댓글 불러오는 중...</p></section>'
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
<link rel="icon" href="/favicon.png">
<style>{CSS}</style>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADS_CLIENT}" crossorigin="anonymous"></script>
{''.join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)}
</head>
<body>
<header class="top"><div class="top-in"><a class="brand" href="/">리카수니 <b>자료실</b></a><div class="auth" id="auth"><button class="btn btn-gold btn-sm" onclick="lazyLogin()">로그인</button></div></div></header>
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
  var done = false, after = null, srcs = ['https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.58.0/dist/umd/supabase.js', '/common.js?v=2', '/lib.js?v=3'];
  function next(i) {{ if (i >= srcs.length) {{ if (after) after(); return; }} var s = document.createElement('script'); s.src = srcs[i]; s.onload = function () {{ next(i + 1); }}; document.body.appendChild(s); }}
  function go() {{ if (!done) {{ done = true; next(0); }} }}
  window.lazyLogin = function () {{ after = function () {{ showLogin(); }}; if (done) {{ if (window.showLogin) showLogin(); }} else go(); }};
  /* 광고 차단으로 광고 스크립트 자체가 안 불러와졌을 때만 확보해 둔 자리를 접음 */
  addEventListener('load', function () {{ setTimeout(function () {{ if (window.adsbygoogle && window.adsbygoogle.loaded) return; document.querySelectorAll('.ad-slot').forEach(function (d) {{ d.style.display = 'none'; }}); }}, 8000); }});
  var had = false; try {{ had = !!localStorage.getItem('sb-iiyhmskvdjgstoikonwu-auth-token'); }} catch (e) {{}}
  if (had || location.hash.indexOf('access_token') > -1) {{ go(); return; }}
  var c = document.getElementById('comments');
  if (c && 'IntersectionObserver' in window) {{
    var io = new IntersectionObserver(function (es) {{ if (es[0].isIntersecting) {{ io.disconnect(); go(); }} }}, {{ rootMargin: '600px' }});
    io.observe(c);
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
    blocks = ([('주요 과목', core)] if core else []) + [(GROUP_NAME.get(g, g), [g]) for g in ('사회탐구', '과학탐구') if g in groups]
    for label, gs in blocks:
        rows += f'<div class="card"><p class="grp">{e(label)}</p>'
        for g in gs:
            for s, xs in groups[g]:
                rows += f'<div class="subj"><a class="nm" href="{subj_url(k, s)}">{e(dname(s))}</a>{dl_buttons(xs)}</div>'
        rows += '</div>'
    sub_names = ', '.join(dname(s) for s in subs)
    inf = INFO.get(ikey(k), {})
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
        if s == '영어':
            extra = '''<div class="card"><h2>📚 리카수니 영어 자료</h2>
<div class="soon"><b>변형문제</b> · 준비 중이에요</div>
<div class="soon"><b>어휘 학습노트</b> · 준비 중이에요</div>
<div class="soon"><b>문항별 분석노트</b> · 준비 중이에요</div>
<p class="muted">자료가 올라오면 이 페이지에 바로 추가돼요. 질문을 남겨두시면 먼저 알려드릴게요!</p></div>'''
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
        body = f'''<h1 class="page-h1">{e(full)} 문제·정답·해설 PDF</h1>
<p class="lead">{e(s_when(k))} · {e(s_org(k))}</p>
{files}
{sinfo}
{ad()}
{extra}
<div class="card"><h2>{e(name)} 다른 과목</h2>{sibs}</div>
{rel}
{ad()}'''
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
body = f'''<section class="hero"><h1>모의고사·수능 기출문제 전과목 PDF</h1>
<p>고1·고2·고3 모의고사와 수능 기출 문제지·정답·해설을 한곳에서 무료로 받아보세요. 총 {len(R):,}개 파일.</p></section>
<div class="grid4">
<a class="tile" href="/moe/go1/"><b>고1</b><span>{cnt[1]}개 회차</span></a>
<a class="tile" href="/moe/go2/"><b>고2</b><span>{cnt[2]}개 회차</span></a>
<a class="tile" href="/moe/go3/"><b>고3</b><span>{cnt[3]}개 회차</span></a>
<a class="tile gold" href="/suneung/"><b>수능</b><span>{cnt["sn"]}개 학년도</span></a>
</div>
<div class="card"><h2>🆕 최근 회차</h2><div class="chips">''' + ''.join(
    f'<a class="chip" href="{s_url(k)}">{e(s_name(k))}</a>' for k in latest) + '''</div></div>
<a class="banner" href="/mission/"><b>🎯 댓글 미션으로 리카수니 자료 받기</b><p>질문·학습 후기 댓글 10개를 모으면 분석노트·어휘노트를 이메일로 보내드려요.</p></a>
''' + ad()
page('/', '리카수니 자료실 | 모의고사·수능 기출문제 전과목 PDF 무료 다운로드',
     '고1·고2·고3 모의고사와 수능 기출문제 전과목 문제지·정답·해설 PDF를 연도·월별로 무료 다운로드. 리카수니 자료실', body, (), '/')

# ---------- sitemap / robots ----------
urls = ''.join(f'<url><loc>{SITE}{p}</loc><lastmod>{TODAY}</lastmod></url>' for p in ['/mission/', '/privacy.html'] + PAGES)
open(os.path.join(ROOT, 'sitemap.xml'), 'w').write(
    f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
open(os.path.join(ROOT, 'robots.txt'), 'w').write(f'User-agent: *\nAllow: /\nDisallow: /admin.html\nDisallow: /get/\nSitemap: {SITE}/sitemap.xml\n')
print('pages', len(PAGES), 'sessions', len(sessions), 'files', len(R))
