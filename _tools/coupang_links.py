"""쿠팡 파트너스 Open API 로 _tools/coupang.json 의 책 링크를 자동으로 채운다.

- 책마다 query(쿠팡 검색어)로 상품을 찾고, must 단어가 모두 들어 있고 SKIP 단어가 없는 첫 상품의 파트너스 링크를 url 에 넣음.
- lock: true 인 책은 원장님이 직접 넣은 링크라 건드리지 않음.
- 못 찾거나 API 가 실패하면 원래 url 을 그대로 둠 (상자가 갑자기 비지 않게).
- 교재 소식 글 폴더(_tools/news/<slug>/coupang.json)의 책도 같은 방식으로 채움 (글에선 <!--BUY:key--> 등 자리에 들어감).
- DRY_RUN=1 이면 고른 결과만 보여 주고 파일은 안 바꿈.
- 키: 환경변수 COUPANG_ACCESS_KEY, COUPANG_SECRET_KEY (GitHub Secrets).
"""
import datetime, glob, hashlib, hmac, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, '_tools', 'coupang.json')
HOST = 'https://api-gateway.coupang.com'
SEARCH = '/v2/providers/affiliate_open_api/apis/openapi/v1/products/search'
# 다른 출판사 변형문제·분석서는 고르지 않음 (원래 교재만)
SKIP = ['변형', '분석', '올바른', 'E기적', '싸인', '불꽃', '워크북', '해설집', '자습서', '평가문제집', '중고', '세트', '중학', '전4권', '전3권']
OLD = datetime.date.today().year - 2  # 상품 이름에 이보다 오래된 연도(예: 2017년)만 있으면 옛 판이라 건너뜀

AK, SK = os.environ.get('COUPANG_ACCESS_KEY', ''), os.environ.get('COUPANG_SECRET_KEY', '')
DRY = os.environ.get('DRY_RUN') == '1'


def auth(method, path, query):
    t = datetime.datetime.now(datetime.timezone.utc).strftime('%y%m%dT%H%M%SZ')
    sig = hmac.new(SK.encode(), (t + method + path + query).encode(), hashlib.sha256).hexdigest()
    return f'CEA algorithm=HmacSHA256, access-key={AK}, signed-date={t}, signature={sig}'


def search(keyword, limit=10):
    q = urllib.parse.urlencode({'keyword': keyword, 'limit': limit})
    req = urllib.request.Request(f'{HOST}{SEARCH}?{q}', headers={'Authorization': auth('GET', SEARCH, q), 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.load(r)
    if str(d.get('rCode')) != '0':
        raise RuntimeError(f'{d.get("rCode")} {d.get("rMessage")}')
    return (d.get('data') or {}).get('productData') or []


def pick(b, items, book=True):  # must 의 'A|B' 는 둘 중 하나만 있어도 됨 (예: '기본 1|기본1'), not 은 그 책에서만 빼는 단어
    must, skip = b.get('must') or [], (SKIP if book else []) + (b.get('not') or [])  # 책이 아닌 것(인쇄 용품)엔 책용 거르기·연도 규칙을 쓰지 않음
    for it in items:
        name = it.get('productName', '').lower()
        years = [int(y) for y in re.findall(r'20\d\d', name)]
        if book and years and max(years) < OLD:
            continue
        if all(any(a.lower() in name for a in w.split('|')) for w in must) and not any(w.lower() in name for w in skip):
            return it


def main():
    if not (AK and SK):
        sys.exit('COUPANG_ACCESS_KEY / COUPANG_SECRET_KEY 가 없어요.')
    # 학년별 상자 (coupang.json) + 교재 소식 글마다 폴더의 coupang.json
    files = {PATH: json.load(open(PATH, encoding='utf-8'))}
    jobs = [(g, b, PATH) for g in ('go1', 'go2', 'go3', 'print') for b in files[PATH].get(g, [])]
    for f in sorted(glob.glob(os.path.join(ROOT, '_tools', 'news', '*', 'coupang.json'))):
        files[f] = json.load(open(f, encoding='utf-8'))
        jobs += [(os.path.basename(os.path.dirname(f)), b, f) for b in files[f]]
    today = datetime.date.today().isoformat()
    lines, changed = [], 0
    for g, b, _ in jobs:
        if b.get('lock') or not b.get('query'):
            lines.append(f'- [{g}] {b["name"]}: 그대로 (직접 넣은 링크)')
            continue
        try:
            it = pick(b, search(b['query']), book=g != 'print' and not b.get('goods'))  # goods: true = 책이 아닌 물건
        except (urllib.error.URLError, RuntimeError, ValueError) as ex:
            lines.append(f'- [{g}] {b["name"]}: ⚠️ API 실패, 그대로 둠 ({ex})')
            time.sleep(3)
            continue
        if not it:
            lines.append(f'- [{g}] {b["name"]}: ⚠️ 맞는 상품 없음, 그대로 둠 (검색어: {b["query"]})')
        else:
            lines.append(f'- [{g}] {b["name"]}: {it["productName"]} · {int(float(it.get("productPrice") or 0)):,}원')
            if b.get('url') != it['productUrl'] or b.get('product') != it['productName'] or b.get('image') != it.get('productImage', ''):
                changed += 1
            b.update(url=it['productUrl'], product=it['productName'], image=it.get('productImage', ''), checked=today)  # image = 쿠팡 상품 사진 (구매 카드에만 씀)
        time.sleep(3)
    report = '\n'.join(lines) + f'\n\n바뀐 책 {changed}권' + (' (미리보기라 저장 안 함)' if DRY else '')
    print(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8').write('### 쿠팡 링크\n' + report + '\n')
    if not DRY:
        for f, d in files.items():
            json.dump(d, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
            open(f, 'a', encoding='utf-8').write('\n')


if __name__ == '__main__':
    main()
