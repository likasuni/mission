"""리카수니 블로그(likasuni.com, Blogger)에 그날 공개된 자료실 해설의 '요약 글'을 자동 발행.

자료실은 문항 1개 = 페이지 1개(상세 해설), 블로그는 하루치 문항의 정답·포인트만 묶은 심플한 요약 글 1개로 구성이 달라
같은 글로 보이지 않게 한다. 끝에 자료실 링크와 내일 공개 예고를 붙인다.

  python blogger_post.py                          # 오늘(한국 시간) 공개분 발행 — BLOGGER_* 환경변수가 없으면 건너뜀
  python blogger_post.py --preview 2026-10-19 out.html   # 발행하지 않고 그날 글 미리보기 HTML 저장
  BLOGGER_DAY=2026-10-19 BLOGGER_DRAFT=1 python blogger_post.py  # 연결 테스트: 그날 글을 블로그 임시저장(비공개)으로, 기록 안 남김

환경변수(GitHub Secrets): BLOGGER_CLIENT_ID, BLOGGER_CLIENT_SECRET, BLOGGER_REFRESH_TOKEN, BLOGGER_BLOG_ID
"""
import json, os, sys, html, datetime, collections, urllib.request, urllib.parse, urllib.error

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
    if len(ps) > 6:  # 한 회차를 한꺼번에 공개한 날은 제목을 짧게
        nums = f"{ps[0]['n']}~{ps[-1].get('n2') or ps[-1]['n']}"
        types = '전 문항' if nums == '18~45' else '유형별'
    return f'{exam_name(exam)} {nums}번 정답과 풀이 포인트 ({types})'


def item_html(p):
    ans = ' · '.join(f"{q['n']}번 {CIRC[q['answer'] - 1]}" for q in p['qs']) if p.get('n2') else f"정답 {CIRC[p['answer'] - 1]}"
    point = p.get('note') or p.get('tip')
    pt = (f'<p style="margin:10px 0 0;"><b style="color:#1e3a8a;">{"원장님 포인트" if p.get("note") else "풀이 포인트"}</b> {e(point)}</p>') if point else ''
    return (f'<div style="{BOX}margin:0 0 16px;padding:16px 18px;border:1px solid #d6def0;border-radius:12px;background:#ffffff;">'
            f'<h3 style="margin:0 0 4px;color:#1e3a8a;font-size:1.15em;">{no(p)}번 · {e(p["type"])} <span style="color:#16a34a;">{ans}</span></h3>'
            f'<p style="margin:0;color:#555;">{e(p["topic"])}</p>{pt}'
            f'<p style="margin:12px 0 0;text-align:right;"><a href="{url(p)}" style="display:inline-block;padding:8px 14px;border-radius:8px;background:#1e3a8a;color:#ffffff;text-decoration:none;font-weight:bold;">{no(p)}번 전체 해설 보기 →</a></p>'
            '</div>')


def post_html(exam, ps, upcoming):
    nums = '·'.join(no(p) for p in ps)
    h = (f'<div style="{BOX}line-height:1.7;">'
         f'<p>{e(exam_name(exam))} {nums}번의 정답과 풀이 포인트만 짧게 정리했어요. '
         '정답 근거 문장, 선택지별 오답 이유, 구문, 어휘까지 담은 전체 해설은 각 문항의 버튼을 눌러 리카수니 자료실에서 볼 수 있어요.</p>')
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


def env(k): return os.environ.get(k, '').strip()  # Secrets 붙여 넣을 때 딸려 온 빈칸·줄바꿈 제거


def call(req, data=None):  # 실패하면 구글이 돌려준 오류 이유(비밀값 없음)를 함께 보여 줌
    try:
        return json.load(urllib.request.urlopen(req, data))
    except urllib.error.HTTPError as x:
        sys.exit(f'blogger: 오류 {x.code} — {x.read().decode(errors="replace")[:500]}')


def access_token():
    d = urllib.parse.urlencode({'client_id': env('BLOGGER_CLIENT_ID'), 'client_secret': env('BLOGGER_CLIENT_SECRET'),
                                'refresh_token': env('BLOGGER_REFRESH_TOKEN'), 'grant_type': 'refresh_token'}).encode()
    return call('https://oauth2.googleapis.com/token', d)['access_token']


def publish(tok, title, content, labels, draft=False):
    body = json.dumps({'kind': 'blogger#post', 'title': title, 'content': content, 'labels': labels}).encode()
    req = urllib.request.Request(f"https://www.googleapis.com/blogger/v3/blogs/{env('BLOGGER_BLOG_ID')}/posts/" + ('?isDraft=true' if draft else ''),
                                 body, {'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'})
    return call(req)


def main():
    ps = load_posts()
    if sys.argv[1:2] == ['--preview']:
        day, out = sys.argv[2], sys.argv[3]
    else:
        day, out = os.environ.get('BLOGGER_DAY') or datetime.datetime.now(KST).date().isoformat(), None
    draft = bool(os.environ.get('BLOGGER_DRAFT'))
    nxt = (datetime.date.fromisoformat(day) + datetime.timedelta(days=1)).isoformat()
    today, upcoming = by_exam(ps, day), by_exam(ps, nxt)
    if not today:
        print('blogger: 오늘 공개된 해설 없음'); return
    if out:
        page = ''.join(f'<h1 style="font-size:1.4em;">{e(title_of(x, q))}</h1>{post_html(x, q, upcoming)}<hr>' for x, q in today.items())
        open(out, 'w').write(f'<!DOCTYPE html><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                             f'<body style="max-width:760px;margin:24px auto;padding:0 16px;font-family:sans-serif;">{page}</body>')
        print('preview', out); return
    if not all(env(k) for k in ('BLOGGER_CLIENT_ID', 'BLOGGER_CLIENT_SECRET', 'BLOGGER_REFRESH_TOKEN', 'BLOGGER_BLOG_ID')):
        print('blogger: 연결 정보(Secrets) 없음 — 건너뜀'); return
    log = json.load(open(LOG)) if os.path.exists(LOG) else {}
    tok = None
    for x, q in today.items():
        key = f'{x}|{day}'
        if key in log and not draft: continue
        tok = tok or access_token()
        r = publish(tok, title_of(x, q), post_html(x, q, upcoming), [exam_name(x), '문항별 해설', '리카수니 자료실'], draft)
        if draft:
            print('blogger: 임시저장 완료 — 블로거 관리 화면의 글 목록에서 확인하세요:', title_of(x, q)); continue
        log[key] = {'url': r.get('url'), 'id': r.get('id'), 'nums': [no(p) for p in q]}
        print('blogger: 발행', r.get('url'))
    json.dump(log, open(LOG, 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
