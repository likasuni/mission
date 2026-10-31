"""분석노트 미리보기 그림 만들기: 첫 쪽 윗부분 + '리카수니 자료실 · 미리보기' 워터마크 → notes/pv/moe-g<학년>-<연도>-<월>-<번호>.jpg

    python3 _tools/note_preview.py 2 2026 10 37                    # 고2 2026년 10월 37번
    python3 _tools/note_preview.py book "수능특강 라이트" 20 1        # 부교재: 책 이름(요청 글과 같게)·강·번호 → notes/pv/bk-수능특강라이트-20-1.jpg

- PDF 는 이 Mac 의 구글 드라이브(Drive for desktop) '깃허브 홈페이지 자료실/모의고사 분석노트' 에서 읽어요 (업로드가 끝난 뒤에).
- macOS sips 로 첫 쪽을 그림으로 바꾸고, 크롬 headless 로 위쪽만 잘라 워터마크를 얹어 찍어요. 결과는 JPEG (50~100KB).
- 자료실 첫 화면 '받을 수 있어요' 칸에서 그림이 있는 번호에만 [미리보기] 버튼이 생겨요 (build.py 가 notes/pv/index.json 을 만듦).
"""
import glob, os, subprocess, sys, tempfile, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.expanduser('~/Library/CloudStorage/GoogleDrive-*/내 드라이브/깃허브 홈페이지 자료실')
DRIVE = os.path.join(BASE, '모의고사 분석노트')
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
W, H = 1100, 760  # 첫 쪽(1100×1556)의 위쪽 절반 정도

HTML = '''<!doctype html><meta charset="utf-8"><style>
html,body{{margin:0;width:{w}px;height:{h}px;overflow:hidden;background:#fff}}
img{{display:block;width:{w}px}}
.fade{{position:absolute;left:0;right:0;bottom:0;height:220px;background:linear-gradient(rgba(255,255,255,0),#fff 85%)}}
.wm{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;transform:rotate(-18deg);
  font:900 64px 'Apple SD Gothic Neo',sans-serif;color:rgba(30,58,138,.13);white-space:nowrap}}
.tag{{position:absolute;left:0;right:0;bottom:28px;text-align:center;font:800 30px 'Apple SD Gothic Neo',sans-serif;color:#1e3a8a}}
</style><img src="file://{png}"><div class="fade"></div><div class="wm">리카수니 자료실 · 미리보기</div>
<div class="tag">전체 분석노트는 자료실에서 카톡으로 받아요</div>'''


def main():
    if sys.argv[1] == 'book':  # 부교재: 드라이브 '부교재 분석노트/<책 이름으로 시작하는 폴더>/<강>-<번호>.pdf'
        book, u, n = sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
        # 드라이브 폴더 이름이 한글 자모 분리(NFD)로 저장돼 있을 수 있어서 이름을 맞춰(NFC) 비교
        src = [os.path.join(d, f'{u}-{n}.pdf') for d in glob.glob(os.path.join(BASE, '부교재 분석노트', '*'))
               if unicodedata.normalize('NFC', os.path.basename(d)).startswith(book) and os.path.exists(os.path.join(d, f'{u}-{n}.pdf'))]
        name, key = f'{book} {u}강 {n}번', f'bk-{book.replace(" ", "")}-{u}-{n}'
    else:
        g, y, m, n = sys.argv[1:5]
        src = glob.glob(os.path.join(DRIVE, f'고{g} 모의고사', f'{y}년 {int(m)}월 고{g}', f'{int(n)}.pdf'))
        name, key = f'고{g} {y}년 {m}월 {n}번', f'moe-g{g}-{y}-{int(m)}-{int(n)}'
    if not src:
        sys.exit(f'PDF 를 찾지 못했어요: {name} (드라이브 업로드가 끝났는지 확인)')
    out = os.path.join(ROOT, 'notes', 'pv', key + '.jpg')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        pdf, png, html, shot = (os.path.join(t, x) for x in ('p.pdf', 'p.png', 'p.html', 's.png'))
        subprocess.run(['cp', src[0], pdf], check=True)  # 드라이브 파일을 바로 열지 않고 복사본으로
        subprocess.run(['sips', '-s', 'format', 'png', '--resampleWidth', str(W), pdf, '--out', png], check=True, capture_output=True)
        open(html, 'w', encoding='utf-8').write(HTML.format(w=W, h=H, png=png))
        subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--allow-file-access-from-files',
                        f'--window-size={W},{H}', '--virtual-time-budget=3000', f'--screenshot={shot}', 'file://' + html],
                       check=True, capture_output=True)
        subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '70', shot, '--out', out], check=True, capture_output=True)
    print(out, f'{os.path.getsize(out) // 1024}KB')


if __name__ == '__main__':
    main()
