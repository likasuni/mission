"""네이버 블로그 글 만들기 도우미 (2026-11-16~, CLAUDE.md '네이버 블로그 글')

    python3 _tools/naver_post.py _tools/naver_posts/<날짜>-<자료>.txt "<썸네일 위 두 줄(<br>로 줄바꿈)>" "<파란 배지 문구>" ["<골드 줄>" "<바닥 줄>"]

- txt([제목]·[태그]·[대표 사진: …]·[본문]) → 같은 이름 .html (브라우저에서 열어 드래그 복사 → 네이버 본문 붙여 넣기)
- 2026-11-26~ 원장님 예시 틀: 제목(h2)·검색 미리보기 → 남색 '한눈에 보는 정답' → ①② 번호 제목, 정답 근거 주황 상자, 구문·오답 회색 상자, 어휘 표, 서술형 남색 상자, 받는 법 파란 상자 → 자주 묻는 질문 → 학원 안내 → 태그(맨 아래). 상자는 table+bgcolor (네이버 붙여 넣기에 남음).
- [대표 사진: thumb-….png] 이름으로 1080 정사각형 남색 썸네일을 헤드리스 크롬으로 만들어요.
"""
import html, os, re, subprocess, sys, tempfile

CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

THUMB = '''<!doctype html><meta charset="utf-8"><style>
html,body{{margin:0;width:1080px;height:1080px;overflow:hidden}}
body{{background:radial-gradient(circle at 85% 12%,rgba(91,155,255,.35),transparent 40%),radial-gradient(circle at 10% 90%,rgba(26,115,232,.3),transparent 45%),linear-gradient(#08142f,#162954);
font-family:'Apple SD Gothic Neo',sans-serif;color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}}
.bar{{width:90px;height:10px;border-radius:5px;background:#FFC857;margin-bottom:40px}}
.a{{font-size:44px;font-weight:700;color:#9fbcf5;margin-bottom:28px}}
.t{{font-size:84px;font-weight:900;line-height:1.25}}
.b{{margin-top:44px;background:#1a73e8;border-radius:60px;padding:18px 54px;font-size:52px;font-weight:800}}
.s{{margin-top:34px;font-size:40px;font-weight:700;color:#FFC857}}
.f{{position:absolute;bottom:60px;font-size:34px;color:#7d97cf;font-weight:600}}
</style><div class="bar"></div><div class="a">이매동 코코스학원 · 리카수니</div><div class="t">{t}</div><div class="b">{b}</div>
<div class="s">{s}</div><div class="f">{f}</div>'''


# 2026-11-26 원장님 예시(…/2026_10_고1_영어_20번_네이버.html) 틀: 상자는 table+bgcolor+<font color> → 네이버 스마트에디터에 붙여도 색·상자가 남아요
NAVY, ORANGE, BLUE, GOLD = '#14213d', '#e8621f', '#2f6fdb', '#FFC857'
P = 'font-size:16px;line-height:1.9;margin:0 0 6px'
NUM = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫'


def _e(t):
    return re.sub(r'(https?://[^\s<]+)', r'<a href="\1" target="_blank"><b>\1</b></a>', html.escape(t))


def _box(inner, bg, border='', pad=14, white=False):
    b = f'border:{border};' if border else ''
    if white:
        inner = f'<font color="#ffffff">{inner}</font>'
    return (f'<table width="100%" cellpadding="{pad}" cellspacing="0" border="0" style="width:100%;border-collapse:collapse;margin:0 0 18px;">'
            f'<tr><td bgcolor="{bg}" style="background:{bg};{b}font-size:15px;line-height:1.85;">{inner}</td></tr></table>')


def _vocab_split(t):
    ws = t.split(' ')
    for i, w in enumerate(ws):
        if i and re.search('[가-힣]', w):
            return ' '.join(ws[:i]), ' '.join(ws[i:])
    return t, ''


def _vocab_table(items):
    td = 'padding:7px 10px;border:1px solid #dfe3ea;'
    th = 'background:#f1f4fa;text-align:left;padding:8px 10px;'
    rows = ''.join(f'<tr><td style="{td}"><b>{html.escape(a)}</b></td><td style="{td}">{html.escape(b)}</td></tr>'
                   for a, b in map(_vocab_split, items))
    return (f'<table width="100%" cellpadding="0" cellspacing="0" border="1" style="width:100%;border-collapse:collapse;border:1px solid #dfe3ea;'
            f'font-size:15px;line-height:1.6;margin:0 0 18px;"><tr><th width="40%" bgcolor="#f1f4fa" style="{th}">영어</th>'
            f'<th bgcolor="#f1f4fa" style="{th}">뜻</th></tr>{rows}</table>')


def _line(t):
    """상자 안 한 줄"""
    s = t.strip()
    if s.startswith('→') and t.startswith(' '):  # 구문 예문
        return f'<font color="#666666"><i>{_e(s)}</i></font>'
    if s.startswith('→'):
        return f'<b><font color="{ORANGE}">{_e(s)}</font></b>'
    if re.match(r'\d+\) ', s):
        return f'<b>{_e(s)}</b>'
    if s.startswith('▶'):
        return f'<b><font color="{BLUE}">{_e(s)}</font></b>'
    if s.startswith('· '):
        return '· ' + re.sub(r'^([^:<]{1,14}): ', r'<b>\1:</b> ', _e(s[2:]))
    return _e(s)


def to_html(s):
    title = s.split('[제목]\n')[1].split('\n')[0]
    tags = s.split('[태그]\n')[1].split('\n')[0]
    thumb = re.search(r'\[대표 사진: (.+?)\]', s).group(1)
    kw, sub = (title.split(' – ', 1) + [''])[:2]
    lines = [t.rstrip() for t in s.split('[본문]\n')[1].strip('\n').split('\n')]
    # 머리(첫 ■ 전)와 꼬리(마지막 ──── 뒤 학원 안내), 그 사이 칸들로 나눔
    first = next(i for i, t in enumerate(lines) if t.startswith('■ '))
    hrs = [i for i, t in enumerate(lines) if t.startswith('────')]
    tail_at = hrs[-1] if hrs and hrs[-1] > first else len(lines)
    head, body, tail = lines[:first], lines[first:tail_at], lines[tail_at + 1:]
    secs = []
    for t in body:
        if t.startswith('■ '):
            secs.append([t[2:], []])
        elif not t.startswith('────'):
            secs[-1][1].append(t)
    info = next((ls for n, ls in secs if '문제 정보' in n), [])
    ans = next((l.split(': ', 1)[1] for l in info if l.startswith('· 정답')), '')
    out = [f'<p style="font-size:15px;color:#888;margin:0 0 6px;">리카수니 분석노트 해설 · 이매동 코코스학원</p>',
           f'<h2 style="font-size:26px;line-height:1.45;margin:0 0 14px;color:{NAVY};">{html.escape(kw)}'
           + (f'<br><span style="font-size:18px;color:#555;font-weight:normal;">{html.escape(sub)}</span>' if sub else '') + '</h2>']
    hp = [t for t in head if t.strip()]
    if hp:  # 첫 두 줄 = 검색 미리보기
        out.append(f'<p style="{P}"><b>{_e(hp[0])}</b>' + ''.join(f'<br>{_e(x)}' for x in hp[1:2]) + '</p>')
        out += [f'<p style="{P}">{_e(x)}</p>' for x in hp[2:]]
    n = 0
    for name, ls in secs:
        items = [l for l in ls if l.strip()]
        if '문제 정보' in name:  # 남색 '한눈에 보는 정답' 상자
            inner = f'<b><font color="{GOLD}">한눈에 보는 정답</font></b><br>' + '<br>'.join(_e(l) for l in items)
            out.append(_box(inner, NAVY, white=True)); continue
        n += 1
        out.append(f'<h3 style="font-size:21px;color:{NAVY};border-bottom:2px solid #e3e8f2;padding-bottom:8px;margin:30px 0 12px;">'
                   f'{NUM[n - 1] if n <= len(NUM) else "■"} {html.escape(name)}</h3>')
        pics = [re.match(r'\[사진: (\S+)', l).group(1) for l in items if l.startswith('[사진:')]
        items = [l for l in items if not l.startswith('[사진:')]
        if '어휘' in name and all(l.startswith('· ') for l in items):
            out.append(_vocab_table([l[2:] for l in items]))
        elif '근거' in name:
            out.append(_box('<br>'.join(_line(l) for l in items), '#fdf7f2', f'1.5px solid {ORANGE}', 12))
        elif '받는 법' in name or '보는 법' in name:
            out.append(_box(f'<b><font color="{BLUE}">📂 {html.escape(name)}</font></b><br>' + '<br>'.join(_line(l) for l in items),
                            '#eaf2ff', f'2px solid {BLUE}'))
        elif '서술형' in name:
            out.append(_box(f'<b><font color="{GOLD}">서술형 대비</font></b><br>' + '<br>'.join(_e(l) for l in items), NAVY, white=True))
        elif '원문' in name:  # 시험에 나올 문장 (원문 2~3개 + 분석, 2026-11-28~)
            out.append(_box('<br>'.join(f'<b><font color="{NAVY}">{_e(l.strip())}</font></b>' if re.match(r'[①-⑨] ', l.strip())
                                        else _line(l) for l in items), '#ffffff', f'1.5px solid {NAVY}', 14))
        elif '구문' in name or '오답' in name or '푸는' in name:
            out.append(_box('<br>'.join(_line(l) for l in items), '#f7f8fb', '1px solid #dfe3ea'))
        else:
            out.append(f'<p style="{P}">' + '<br>'.join(_line(l) for l in items) + '</p>')
        for p in pics:
            out.append(f'<p style="text-align:center;margin:14px 0 4px;"><img src="{p}" alt="{html.escape(kw)} 분석노트 미리보기" style="max-width:100%;border:1px solid #ddd;"></p>'
                       f'<p style="text-align:center;font-size:13px;color:#888;margin:0 0 16px;">▲ {html.escape(kw)} 분석노트 미리보기</p>')
    # 자주 묻는 질문 (글 안 내용으로만)
    if ans:
        faq = f'<b>Q. {html.escape(kw.replace(" pdf", ""))} 정답은?</b><br>A. {_e(ans)}'
        faq += f'<br><br><b>Q. 분석노트 pdf 는 어디서 받나요?</b><br>A. 리카수니 자료실(data.likasuni.com)에서 카카오 로그인 후 카톡으로 받을 수 있어요. 위 안내의 링크로 이동하세요.'
        out.append(f'<h3 style="font-size:21px;color:{NAVY};border-bottom:2px solid #e3e8f2;padding-bottom:8px;margin:30px 0 12px;">'
                   f'{NUM[n] if n < len(NUM) else "■"} 자주 묻는 질문</h3><p style="{P}">{faq}</p>')
    out.append(f'<p style="{P};margin-top:18px;">이상 <b>{html.escape(kw)}</b> 정리였어요. 궁금한 점은 댓글로 남겨 주세요.</p>')
    tl = [t for t in tail if t.strip() and not t.startswith('■')]
    if tl:
        out.append(_box('<b>🏫 이매동 코코스학원 안내</b><br>' + '<br>'.join(_line(t) for t in tl), '#f7f8fb', '1px solid #dfe3ea', 12))
    out.append(f'<p style="font-size:15px;line-height:1.9;color:{BLUE};">{html.escape(tags)}</p>')  # 태그는 맨 아래 (2026-11-26)
    return thumb, f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title></head><body style="margin:0;padding:16px;background:#ffffff;font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;color:#222;">
<div style="max-width:760px;margin:0 auto;">
<div style="background:#fff8e1;border:1px solid #f0c36d;padding:12px 14px;font-size:14px;margin-bottom:20px;line-height:1.7;">📋 <b>네이버 붙여 넣기:</b> 이 노란 상자 아래부터 끝까지 드래그 복사(⌘C) → 네이버 본문에 붙여 넣기(⌘V). 대표 사진({thumb})을 맨 위에 올려 '대표'로 지정.<br>
제목: <b>{html.escape(title)}</b><br>태그 칸: {html.escape(tags)}</div>
<p style="text-align:center;"><img src="{thumb}" alt="{html.escape(kw)}" style="max-width:100%;"></p>
{chr(10).join(out)}
</div></body></html>'''


def main():
    src, top, badge = sys.argv[1:4]
    sub = sys.argv[4] if len(sys.argv) > 4 else '정답 근거 · 구문 · 어휘'
    foot = sys.argv[5] if len(sys.argv) > 5 else '분석노트 PDF · data.likasuni.com'
    thumb, doc = to_html(open(src, encoding='utf-8').read())
    open(src[:-4] + '.html', 'w', encoding='utf-8').write(doc)
    d = os.path.dirname(os.path.abspath(src))
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(THUMB.format(t=top, b=badge, s=sub, f=foot))
    subprocess.run([CHROME, '--headless', '--disable-gpu', '--hide-scrollbars', '--window-size=1080,1080',
                    f'--screenshot={os.path.join(d, thumb)}', 'file://' + f.name], capture_output=True)
    os.unlink(f.name)
    print(src[:-4] + '.html', os.path.join(d, thumb))


if __name__ == '__main__':
    main()
