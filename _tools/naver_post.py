"""네이버 블로그 글 만들기 도우미 (2026-11-16~, CLAUDE.md '네이버 블로그 글')

    python3 _tools/naver_post.py _tools/naver_posts/<날짜>-<자료>.txt "<썸네일 위 두 줄(<br>로 줄바꿈)>" "<파란 배지 문구>" ["<골드 줄>" "<바닥 줄>"]

- txt([제목]·[태그]·[대표 사진: …]·[본문]) → 같은 이름 .html (브라우저에서 열어 드래그 복사 → 네이버 본문 붙여 넣기)
- 2026-11-26~: 문제 정보·어휘는 표, 결론 줄 노란 강조, 구문 예문 기울임, 사진 아래 설명, 맨 아래 핵심어 한 줄 + 태그.
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


NAVY, BLUE, RED, GOLD_BG = '#1e3a8a', '#1a73e8', '#d93025', '#fff4d6'
P = 'margin:0;line-height:1.9;font-size:16px'


def _inline(t):
    """링크·굵게 처리 (HTML 이스케이프 뒤)"""
    e = re.sub(r'(https?://[^\s<]+)', r'<a href="\1" style="color:%s;font-weight:bold">\1</a>' % BLUE, html.escape(t))
    return e


def _kv_table(rows, head=None):
    """2칸 표 — 네이버 스마트에디터에 붙여 넣어도 표로 남아서 가독성이 좋아요"""
    td = 'border:1px solid #d6dbe8;padding:9px 12px;font-size:15px;line-height:1.6;vertical-align:top'
    h = ''
    if head:
        h = '<tr>' + ''.join(f'<th style="{td};background:{NAVY};color:#fff;text-align:left">{x}</th>' for x in head) + '</tr>'
    body = ''.join(f'<tr><td style="{td};background:#eef2fb;font-weight:bold;color:{NAVY};width:34%">{_inline(k)}</td>'
                   f'<td style="{td}">{v}</td></tr>' for k, v in rows)
    return f'<table style="border-collapse:collapse;width:100%;margin:6px 0 4px">{h}{body}</table>'


def _vocab_split(t):
    """'· drill A into B A를 B에게 …' → ('drill A into B', 'A를 B에게 …') — 한글이 처음 나오는 단어에서 나눔"""
    ws = t.split(' ')
    for i, w in enumerate(ws):
        if i and re.search('[가-힣]', w):
            return ' '.join(ws[:i]), ' '.join(ws[i:])
    return t, ''


def to_html(s):
    title = s.split('[제목]\n')[1].split('\n')[0]
    tags = s.split('[태그]\n')[1].split('\n')[0]
    thumb = re.search(r'\[대표 사진: (.+?)\]', s).group(1)
    kw = title.split(' – ')[0].strip()  # 검색 핵심어 (제목 앞부분)
    lines = [t.rstrip() for t in s.split('[본문]\n')[1].strip('\n').split('\n')]
    out, sec, i = [], '', 0
    while i < len(lines):
        t = lines[i]
        m = re.match(r'\[사진: (\S+)', t)
        if t.startswith('■ '):
            sec = t[2:]
            # 표로 바꿀 칸: 문제 정보(· 이름: 값), 꼭 외울 어휘(· 단어 뜻)
            body = []
            j = i + 1
            while j < len(lines) and lines[j].startswith('· '):
                body.append(lines[j][2:]); j += 1
            out.append(f'<p style="margin:30px 0 10px;font-size:19px;font-weight:bold;color:{NAVY}">'
                       f'<span style="color:#f2a900">■</span> {_inline(sec)}</p>')
            if body and '문제 정보' in sec and all(': ' in b for b in body):
                rows = [(b.split(': ', 1)[0], _inline(b.split(': ', 1)[1])) for b in body]
                rows = [(k, f'<b style="color:{RED}">{v}</b>' if k.startswith('정답') else v) for k, v in rows]
                out.append(_kv_table(rows)); i = j; continue
            if body and '어휘' in sec:
                rows = [(a, html.escape(b)) for a, b in map(_vocab_split, body)]
                out.append(_kv_table(rows, ('단어·표현', '뜻'))); i = j; continue
            i += 1; continue
        if m:
            alt = html.escape(kw)
            out.append(f'<p style="text-align:center;margin:14px 0 4px"><img src="{m.group(1)}" alt="{alt} 분석노트 미리보기" '
                       f'style="max-width:100%;border:1px solid #ddd;border-radius:8px"></p>'
                       f'<p style="text-align:center;margin:0 0 10px;font-size:13px;color:#888">▲ {alt} 분석노트 미리보기</p>')
        elif not t:
            out.append('<p style="margin:0;line-height:1.2">&nbsp;</p>')
        elif t.startswith('────'):
            out.append('<hr style="border:0;border-top:1px solid #ccd;margin:24px 0">')
        elif t.startswith('▶'):
            out.append(f'<p style="{P};font-weight:bold;color:{BLUE}">{_inline(t)}</p>')
        elif t.startswith('→'):  # 결론 줄: 노란 바탕 강조
            out.append(f'<p style="{P};font-weight:bold"><span style="background:{GOLD_BG}">{_inline(t)}</span></p>')
        elif t.lstrip().startswith('→'):  # 구문 예문 줄
            out.append(f'<p style="{P};color:#555;padding-left:14px"><i>{_inline(t.strip())}</i></p>')
        elif re.match(r'\d+\) ', t):  # 구문 번호 줄
            out.append(f'<p style="{P};font-weight:bold;color:{NAVY};margin-top:8px">{_inline(t)}</p>')
        elif t.startswith('· '):
            e = _inline(t[2:])
            e = re.sub(r'^([^:<]{1,14}): ', r'<b>\1:</b> ', e)  # '근거 1:' 같은 머리말 굵게
            out.append(f'<p style="{P}">· {e}</p>')
        else:
            e = _inline(t)
            if i < 2:  # 첫 두 줄(검색 미리보기)은 굵게
                e = f'<b>{e}</b>'
            out.append(f'<p style="{P}">{e}</p>')
        i += 1
    # 맨 아래: 핵심어 한 번 더 + 태그 (2026-11-26 원장님: 태그는 글 맨 아래)
    end = f'<p style="{P};margin-top:18px">이상 <b>{html.escape(kw)}</b> 정리였어요. 궁금한 점은 댓글로 남겨 주세요.</p>'
    hrs = [k for k, x in enumerate(out) if x.startswith('<hr')]
    out.insert(hrs[-1] if hrs else len(out), end)  # 학원 안내(마지막 구분선) 바로 위
    out.append(f'<p style="margin:16px 0 0;line-height:1.9;font-size:14px;color:{BLUE}">{html.escape(tags)}</p>')
    return thumb, f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>body{{font-family:'Apple SD Gothic Neo',sans-serif;max-width:720px;margin:30px auto;padding:0 16px;font-size:16px;color:#222}}
.guide{{background:#fff8e1;border:1px solid #f0c36d;padding:12px 14px;border-radius:8px;font-size:14px;margin-bottom:20px;line-height:1.7}}</style></head><body>
<div class="guide">📋 <b>네이버 붙여 넣기:</b> 아래 노란 상자 밑부터 끝까지 마우스로 드래그해 복사(⌘C) → 네이버 글쓰기 본문에 붙여 넣기(⌘V).<br>
제목: <b>{html.escape(title)}</b><br>태그 칸: {html.escape(tags)}<br>
<span style="color:#a15c00">대표 사진({thumb})은 맨 위 사진을 '대표'로 지정해 주세요. 태그는 글 맨 아래에도 들어가 있어요.</span></div>
<p style="text-align:center"><img src="{thumb}" alt="{html.escape(kw)}" style="max-width:100%;border-radius:12px"></p>
{chr(10).join(out)}
</body></html>'''


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
