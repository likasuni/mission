"""쿠팡 파트너스 Open API 로 _tools/coupang.json 의 책 링크를 자동으로 채운다.

- 책마다 query(쿠팡 검색어)로 상품을 찾고, must 단어가 모두 들어 있고 SKIP 단어가 없는 첫 상품의 파트너스 링크를 url 에 넣음.
- lock: true 인 책은 원장님이 직접 넣은 링크라 건드리지 않음.
- 못 찾거나 API 가 실패하면 원래 url 을 그대로 둠 (상자가 갑자기 비지 않게).
- DRY_RUN=1 이면 고른 결과만 보여 주고 파일은 안 바꿈.
- 키: 환경변수 COUPANG_ACCESS_KEY, COUPANG_SECRET_KEY (GitHub Secrets).
"""
import datetime, hashlib, hmac, json, os, sys, time, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, '_tools', 'coupang.json')
HOST = 'https://api-gateway.coupang.com'
SEARCH = '/v2/providers/affiliate_open_api/apis/openapi/v1/products/search'
# 다른 출판사 변형문제·분석서는 고르지 않음 (원래 교재만)
SKIP = ['변형', '분석', '올바른', 'E기적', '싸인', '불꽃', '워크북', '해설집', '자습서', '평가문제집', '중고']

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


def pick(b, items):  # must 의 'A|B' 는 둘 중 하나만 있어도 됨 (예: '기본 1|기본1'), not 은 그 책에서만 빼는 단어
    must, skip = b.get('must') or [], SKIP + (b.get('not') or [])
    for it in items:
        name = it.get('productName', '').lower()
        if all(any(a.lower() in name for a in w.split('|')) for w in must) and not any(w.lower() in name for w in skip):
            return it


def main():
    if not (AK and SK):
        sys.exit('COUPANG_ACCESS_KEY / COUPANG_SECRET_KEY 가 없어요.')
    data = json.load(open(PATH, encoding='utf-8'))
    today = datetime.date.today().isoformat()
    lines, changed = [], 0
    for g in ('go1', 'go2', 'go3'):
        for b in data.get(g, []):
            if b.get('lock') or not b.get('query'):
                lines.append(f'- [{g}] {b["name"]}: 그대로 (직접 넣은 링크)')
                continue
            try:
                it = pick(b, search(b['query']))
            except (urllib.error.URLError, RuntimeError, ValueError) as ex:
                lines.append(f'- [{g}] {b["name"]}: ⚠️ API 실패, 그대로 둠 ({ex})')
                time.sleep(3)
                continue
            if not it:
                lines.append(f'- [{g}] {b["name"]}: ⚠️ 맞는 상품 없음, 그대로 둠 (검색어: {b["query"]})')
            else:
                lines.append(f'- [{g}] {b["name"]}: {it["productName"]} · {it.get("productPrice", "")}원')
                if b.get('url') != it['productUrl'] or b.get('product') != it['productName']:
                    changed += 1
                b.update(url=it['productUrl'], product=it['productName'], checked=today)
            time.sleep(3)
    report = '\n'.join(lines) + f'\n\n바뀐 책 {changed}권' + (' (미리보기라 저장 안 함)' if DRY else '')
    print(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8').write('### 쿠팡 링크\n' + report + '\n')
    if not DRY:
        json.dump(data, open(PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        open(PATH, 'a', encoding='utf-8').write('\n')


if __name__ == '__main__':
    main()
