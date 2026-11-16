"""네이버 블로그 글 만들기 도우미 (2026-11-16~, CLAUDE.md '네이버 블로그 글')

    python3 _tools/naver_post.py _tools/naver_posts/<날짜>-<자료>.txt "<썸네일 위 두 줄(<br>로 줄바꿈)>" "<파란 배지 문구>"

- txt([제목]·[태그]·[대표 사진: …]·[본문]) → 같은 이름 .html (브라우저에서 열어 드래그 복사 → 네이버 본문 붙여 넣기)
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
<div class="s">정답 근거 · 구문 · 어휘</div><div class="f">분석노트 PDF · data.likasuni.com</div>'''


def to_html(s):
    title = s.split('[제목]\n')[1].split('\n')[0]
    tags = s.split('[태그]\n')[1].split('\n')[0]
    thumb = re.search(r'\[대표 사진: (.+?)\]', s).group(1)
    out = []
    for t in s.split('[본문]\n')[1].strip('\n').split('\n'):
        t = t.rstrip()
        m = re.match(r'\[사진: (\S+)', t)
        if m:
            out.append(f'<p style="text-align:center"><img src="{m.group(1)}" style="max-width:100%;border:1px solid #ddd;border-radius:8px"></p>')
        elif not t:
            out.append('<p>&nbsp;</p>')
        elif t.startswith('────'):
            out.append('<hr style="border:0;border-top:1px solid #ccd">')
        else:
            e = re.sub(r'(https?://[^\s<]+)', r'<a href="\1">\1</a>', html.escape(t))
            if t.startswith('■ '):
                out.append(f'<h3 style="color:#1e3a8a;font-size:19px;margin:22px 0 8px;border-left:5px solid #FFC857;padding-left:10px">{e[2:]}</h3>')
            elif t.startswith('▶'):
                out.append(f'<p style="font-weight:bold;color:#1a73e8">{e}</p>')
            else:
                if '정답:' in t:
                    e = f'<b style="color:#d93025">{e}</b>'
                out.append(f'<p style="margin:4px 0;line-height:1.8">{e}</p>')
    return thumb, f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>body{{font-family:'Apple SD Gothic Neo',sans-serif;max-width:720px;margin:30px auto;padding:0 16px;font-size:16px;color:#222}}
.guide{{background:#fff8e1;border:1px solid #f0c36d;padding:12px 14px;border-radius:8px;font-size:14px;margin-bottom:20px}}</style></head><body>
<div class="guide">📋 <b>네이버 붙여 넣기:</b> 아래 노란 상자 밑부터 끝까지 마우스로 드래그해 복사(⌘C) → 네이버 글쓰기 본문에 붙여 넣기(⌘V).<br>
제목: <b>{html.escape(title)}</b><br>태그: {html.escape(tags)}</div>
<p style="text-align:center"><img src="{thumb}" style="max-width:100%;border-radius:12px"></p>
{chr(10).join(out)}
</body></html>'''


def main():
    src, top, badge = sys.argv[1:4]
    thumb, doc = to_html(open(src, encoding='utf-8').read())
    open(src[:-4] + '.html', 'w', encoding='utf-8').write(doc)
    d = os.path.dirname(os.path.abspath(src))
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(THUMB.format(t=top, b=badge))
    subprocess.run([CHROME, '--headless', '--disable-gpu', '--hide-scrollbars', '--window-size=1080,1080',
                    f'--screenshot={os.path.join(d, thumb)}', 'file://' + f.name], capture_output=True)
    os.unlink(f.name)
    print(src[:-4] + '.html', os.path.join(d, thumb))


if __name__ == '__main__':
    main()
