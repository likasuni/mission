"""분석노트 웹 보기 그림 만들기: 모의고사 분석노트 PDF 모든 쪽 → notes/view/moe-g<학년>-<연도>-<월>-<번호>-<쪽>.webp (워터마크 없음, 고화질)

    python3 _tools/note_view.py 1 2026 10 30        # 고1 2026년 10월 30번만
    python3 _tools/note_view.py 1 2026 10           # 그 회차 드라이브 폴더에 있는 번호 전부 (바뀐 PDF 만 다시 만듦)

- PDF 는 이 Mac 의 구글 드라이브 '깃허브 홈페이지 자료실/모의고사 분석노트' 에서 읽어요 (note_preview.py 와 같은 곳).
- 그림은 macOS Quick Look(qlmanage)으로 글자를 선명하게 그려요 (sips 는 72dpi 를 키워서 흐림). 폭 1600px WebP(장당 150~250KB, JPEG 의 1/3).
- 검색용 영어 원문은 PDF 글자에서 뽑아요 (한글은 PDF 글꼴 때문에 깨져서 영어 줄만 씀).
- 기록 notes/view/index.json: {키: {pages, v(PDF 수정 시각), en(영어 원문 줄)}} → build.py 가 문항 해설 페이지에 '원장님 분석노트' 칸을 그려요.
- PDF 를 고쳐 다시 올리면 수정 시각이 바뀌어서 다음 실행 때 그림도 새로 만들어요.
"""
import glob, json, os, re, subprocess, sys, tempfile

import pypdf
from PIL import Image  # pip3 install --user pillow (WebP 저장)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVE = os.path.expanduser('~/Library/CloudStorage/GoogleDrive-*/내 드라이브/깃허브 홈페이지 자료실/모의고사 분석노트')
OUT = os.path.join(ROOT, 'notes', 'view')
IDX = os.path.join(OUT, 'index.json')
W = 1600


MARK = str.maketrans({'˝': '①', '˞': '②', '˟': '③', 'ˠ': '④', 'ˡ': '⑤', 'ﬁ': 'fi', 'ﬂ': 'fl'})  # 노트 글꼴의 동그라미 번호·합자


def english(pdf):
    """PDF 글자 중 영어 줄만 (깨진 한글 줄은 뺌) → 문단 목록 (제목 줄에서 나눔)"""
    out = []
    for pg in pypdf.PdfReader(pdf).pages:
        for ln in (pg.extract_text() or '').splitlines():
            ln = ln.strip().translate(MARK)
            chars = [c for c in ln if not c.isspace()]
            if len(re.findall('[A-Za-z]', ln)) < 3 or sum(ord(c) < 128 or c in '①②③④⑤→’‘“”…—–' for c in chars) < len(chars) * 0.95:
                continue
            if not re.search('[a-z]', ln) or re.fullmatch(r'\(.*\)', ln):  # 머리글의 깨진 주소 줄(대문자만), 괄호 동의어만 남은 줄
                continue
            out.append(ln)
    paras, cur = [], []
    for ln in out:
        if re.fullmatch(r'(Core Summary|Vocabulary).*', ln):
            if cur: paras.append(' '.join(cur)); cur = []
            continue
        cur.append(ln)
    if cur: paras.append(' '.join(cur))
    return paras


def make(g, y, m, n, src, idx):
    key = f'moe-g{g}-{y}-{m}-{n}'
    v = int(os.path.getmtime(src))
    if idx.get(key, {}).get('v') == v and all(os.path.exists(os.path.join(OUT, f'{key}-{i + 1}.webp')) for i in range(idx[key]['pages'])):
        return False
    with tempfile.TemporaryDirectory() as t:
        pdf = os.path.join(t, 'in.pdf')
        subprocess.run(['cp', src, pdf], check=True)  # 드라이브 파일을 바로 열지 않고 복사본으로
        r = pypdf.PdfReader(pdf)
        for old in glob.glob(os.path.join(OUT, f'{key}-*.webp')):
            os.remove(old)
        for i, pg in enumerate(r.pages):
            one = os.path.join(t, f'p{i + 1}.pdf')
            w = pypdf.PdfWriter(); w.add_page(pg); w.write(one)
            box = pg.mediabox
            subprocess.run(['qlmanage', '-t', '-s', str(round(W * float(box.height) / float(box.width))), '-o', t, one], check=True, capture_output=True)
            Image.open(one + '.png').convert('RGB').save(os.path.join(OUT, f'{key}-{i + 1}.webp'), 'WEBP', quality=75, method=6)
        idx[key] = {'pages': len(r.pages), 'v': v, 'en': english(pdf)}
    kb = sum(os.path.getsize(os.path.join(OUT, f'{key}-{i + 1}.webp')) for i in range(idx[key]['pages'])) // 1024
    print(f'{key}: {idx[key]["pages"]}쪽 {kb}KB')
    return True


def main():
    g, y, m = sys.argv[1], sys.argv[2], int(sys.argv[3])
    folder = glob.glob(os.path.join(DRIVE, f'고{g} 모의고사', f'{y}년 {m}월 고{g}'))
    if not folder:
        sys.exit(f'드라이브 폴더를 찾지 못했어요: 고{g} {y}년 {m}월')
    nums = sys.argv[4:] or sorted((f[:-4] for f in os.listdir(folder[0]) if re.fullmatch(r'\d+(-\d+)?\.pdf', f)), key=lambda s: int(s.split('-')[0]))
    os.makedirs(OUT, exist_ok=True)
    idx = json.load(open(IDX)) if os.path.exists(IDX) else {}
    done = 0
    for n in nums:
        src = os.path.join(folder[0], f'{n}.pdf')
        if not os.path.exists(src):
            print(f'{n}번 PDF 없음'); continue
        done += make(g, y, m, n, src, idx)
    json.dump(dict(sorted(idx.items())), open(IDX, 'w'), ensure_ascii=False, indent=0)
    print(f'새로 만든 문항 {done}개')


if __name__ == '__main__':
    main()
