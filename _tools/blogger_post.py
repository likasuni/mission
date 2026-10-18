"""리카수니 블로그(likasuni.com, Blogger)에 그날 공개된 자료실 해설의 '요약 글'을 자동 발행.

자료실은 문항 1개 = 페이지 1개(상세 해설), 블로그는 하루치 문항을 묶은 요약 글 1개로 구성이 달라
같은 글로 보이지 않게 한다. 끝에 자료실 링크와 내일 공개 예고를 붙인다.

  python blogger_post.py                          # 오늘(한국 시간) 공개분 발행 — BLOGGER_* 환경변수가 없으면 건너뜀
  python blogger_post.py --preview 2026-10-19 out.html   # 발행하지 않고 그날 글 미리보기 HTML 저장

환경변수(GitHub Secrets): BLOGGER_CLIENT_ID, BLOGGER_CLIENT_SECRET, BLOGGER_REFRESH_TOKEN, BLOGGER_BLOG_ID
"""
import json, os, sys, html, datetime, collections, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = 'https://data.likasuni.com'
LOG = os.path.join(HERE, 'blogger_posted.json')  # 이미 발행한 글 기록 (같은 날 두 번 올리지 않게)
CIRC = '①②③④⑤'
KST = datetime.timezone(datetime.timedelta(hours=9))
e = html.escape

# 박스는 애드센스가 뚫고 나가지 않게 box-sizing / overflow / width / max-width 를 모두 넣음
BOX = 'box-sizing:border-box;overflow:hidden;width:100%;max-width:100%;'


def load_posts():
    ps = []
    for f in sorted(os.listdir(os.path.join(HERE, 'posts'))):
        if f.endswith('.json'):
            p = json.load(open(os.path.join(HERE, 'posts', f)))
            p['qs'] = p.get('qs') or [p]
            ps.append(p)
    return ps


def exam_url(exam):  # build.py 의 subj_url 과 같은 규칙 (영어)
    x = exam.split('-')
    if x[0] == 'sn': return f'/suneung/{x[1]}/eng/'
    g, y, m = int(x[1]), int(x[2]), int(x[3])
    return f'/moe/go{g}/{y}-{m:02d}/eng/'


def exam_name(exam):
    x = exam.split('-')
    if x[0] == 'sn': return f'{x[1]} 수능 영어'
    g, y, m = int(x[1]), int(x[2]), int(x[3])
    if g == 3 and m in (6, 9): return f'{y}학년도 {m}월 모평 영어'
    return f'{y}년 {m}월 고{g} 모의고사 영어'


def no(p): return f"{p['n']}~{p['n2']}" if p.get('n2') else str(p['n'])
def url(p): return SITE + exam_url(p['exam']) + (f"{p['n']}-{p['n2']}/" if p.get('n2') else f"{p['n']}/")
def short_type(p): return '장문' if p.get('n2') else p['type']


def title_of(exam, ps):
    nums = '·'.join(no(p) for p in ps)
    types = '·'.join(dict.fromkeys(short_type(p) for p in ps))
    return f'{exam_name(exam)} {nums}번 정답과 핵심 근거 한눈에 ({types})'


def key_evidence(q):  # 정답과 이어지는 근거 문장: 메모에 '정답' → 정답 번호(②)가 든 문장 → 첫 문장
    ev = q.get('evidence') or []
    c = CIRC[q['answer'] - 1]
    ch = (q.get('choices') or [{}] * 5)[q['answer'] - 1].get('en', '')
    mk = ch[:ch.index(')') + 1] if ch.startswith('(') and ')' in ch[:5] else c  # (c) 같은 밑줄 기호
    return (next((x for x in ev if '정답' in x['note']), None) or next((x for x in ev if mk in x['en'] or c in x['en'] or c in x['note']), None)
            or (ev[0] if ev else None))


def item_html(p):
    ans = ' · '.join(f"{q['n']}번 {CIRC[q['answer'] - 1]}" for q in p['qs']) if p.get('n2') else f"정답 {CIRC[p['answer'] - 1]}"
    sm = (p.get('summary') or {}).get('ko') or p['topic']
    ev = ''
    for q in p['qs']:
        x = key_evidence(q)
        if not x: continue
        lab = f"<b style=\"color:#1e3a8a;\">{q['n']}번 근거</b><br>" if p.get('n2') else ''
        ev += (f'<div style="{BOX}margin:10px 0 0;padding:10px 14px;border-left:4px solid #FFC857;background:#fffdf5;border-radius:6px;">'
               f'{lab}<span style="font-style:italic;">{e(x["en"])}</span><br><span style="color:#555;">{e(x["ko"])}</span></div>')
    point = p.get('note') or p.get('tip')
    pt = (f'<p style="margin:12px 0 0;"><b style="color:#1e3a8a;">{"원장님 포인트" if p.get("note") else "풀이 포인트"}</b> {e(point)}</p>') if point else ''
    return (f'<div style="{BOX}margin:0 0 18px;padding:16px 18px;border:1px solid #d6def0;border-radius:12px;background:#ffffff;">'
            f'<h3 style="margin:0 0 6px;color:#1e3a8a;font-size:1.15em;">{no(p)}번 · {e(p["type"])} <span style="color:#16a34a;">{ans}</span></h3>'
            f'<p style="margin:0;"><b>한 줄 요약</b> {e(sm)}</p>{ev}{pt}'
            f'<p style="margin:14px 0 0;text-align:right;"><a href="{url(p)}" style="display:inline-block;padding:8px 14px;border-radius:8px;background:#1e3a8a;color:#ffffff;text-decoration:none;font-weight:bold;">{no(p)}번 전체 해설 보기 →</a></p>'
            '</div>')


def post_html(exam, ps, upcoming):
    nums = '·'.join(no(p) for p in ps)
    h = (f'<div style="{BOX}line-height:1.7;">'
         f'<p>{e(exam_name(exam))} {nums}번의 정답과 정답 근거를 한눈에 정리했어요. '
         '문항마다 지문 한 줄 요약, 정답을 고르는 결정적 문장, 풀이 포인트만 짧게 모았어요. '
         '선택지별 오답 이유, 구문, 어휘까지 담은 전체 해설은 각 문항의 버튼을 눌러 리카수니 자료실에서 볼 수 있어요.</p>')
    h += ''.join(item_html(p) for p in ps)
    if upcoming:
        h += (f'<div style="{BOX}margin:0 0 18px;padding:14px 18px;border-radius:12px;background:#eef4ff;border:1px solid #c9dbfb;">'
              '<b style="color:#1e3a8a;">내일 공개 예고</b><br>' +
              '<br>'.join(e(f"{exam_name(x)} {'·'.join(no(p) for p in q)}번 ({'·'.join(dict.fromkeys(short_type(p) for p in q))})") for x, q in upcoming.items()) +
              '</div>')
    h += (f'<p style="margin:0;">회차 전체 기출 PDF와 지금까지 공개된 해설은 '
          f'<a href="{SITE}{exam_url(exam)}">리카수니 자료실 {e(exam_name(exam))}</a>에서 무료로 볼 수 있어요.</p></div>')
    return h


def by_exam(ps, day):
    g = collections.OrderedDict()
    for p in sorted((p for p in ps if p['date'] == day), key=lambda p: (p['exam'], p['n'])):
        g.setdefault(p['exam'], []).append(p)
    return g


def access_token():
    d = urllib.parse.urlencode({'client_id': os.environ['BLOGGER_CLIENT_ID'], 'client_secret': os.environ['BLOGGER_CLIENT_SECRET'],
                                'refresh_token': os.environ['BLOGGER_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}).encode()
    return json.load(urllib.request.urlopen('https://oauth2.googleapis.com/token', d))['access_token']


def publish(tok, title, content, labels):
    body = json.dumps({'kind': 'blogger#post', 'title': title, 'content': content, 'labels': labels}).encode()
    req = urllib.request.Request(f"https://www.googleapis.com/blogger/v3/blogs/{os.environ['BLOGGER_BLOG_ID']}/posts/",
                                 body, {'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req))


def main():
    ps = load_posts()
    if sys.argv[1:2] == ['--preview']:
        day, out = sys.argv[2], sys.argv[3]
    else:
        day, out = datetime.datetime.now(KST).date().isoformat(), None
    nxt = (datetime.date.fromisoformat(day) + datetime.timedelta(days=1)).isoformat()
    today, upcoming = by_exam(ps, day), by_exam(ps, nxt)
    if not today:
        print('blogger: 오늘 공개된 해설 없음'); return
    if out:
        page = ''.join(f'<h1 style="font-size:1.4em;">{e(title_of(x, q))}</h1>{post_html(x, q, upcoming)}<hr>' for x, q in today.items())
        open(out, 'w').write(f'<!DOCTYPE html><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                             f'<body style="max-width:760px;margin:24px auto;padding:0 16px;font-family:sans-serif;">{page}</body>')
        print('preview', out); return
    if not all(os.environ.get(k) for k in ('BLOGGER_CLIENT_ID', 'BLOGGER_CLIENT_SECRET', 'BLOGGER_REFRESH_TOKEN', 'BLOGGER_BLOG_ID')):
        print('blogger: 연결 정보(Secrets) 없음 — 건너뜀'); return
    log = json.load(open(LOG)) if os.path.exists(LOG) else {}
    tok = None
    for x, q in today.items():
        key = f'{x}|{day}'
        if key in log: continue
        tok = tok or access_token()
        r = publish(tok, title_of(x, q), post_html(x, q, upcoming), [exam_name(x), '문항별 해설', '리카수니 자료실'])
        log[key] = {'url': r.get('url'), 'id': r.get('id'), 'nums': [no(p) for p in q]}
        print('blogger: 발행', r.get('url'))
    json.dump(log, open(LOG, 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
