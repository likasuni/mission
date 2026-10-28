"""고등 영어 부교재 신간 후보 모으기 (알라딘 도서 API). 매주 Actions `book-new` 가 실행해서 book_candidates.json 에 쌓음.

  ALADIN_TTB_KEY=... python book_new.py

- 검색어 여러 개로 출간일 최신순 검색 → 분류가 '고등'·'영어'(수능 영어 포함)인 책만 → 최근 DAYS 일 안에 나온 책만.
- 이미 있는 책(isbn13)은 그대로 두고 새 책만 status 'new' 로 추가. 글로 쓴 책은 'posted', 안 쓸 책은 'skip' 으로 바꿔 둠.
- 표지 이미지는 저장하지 않음 (교재 소식에 표지 싣지 않음).
"""
import datetime, json, os, sys, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'book_candidates.json')
DAYS = 60
QUERIES = ['수능 영어', '고등 영어 독해', '고등 영어 어휘', '고등 영어 문법', '수능 영어 듣기', '영어 모의고사', '고1 영어', '고2 영어', '영어 구문']
KST = datetime.timezone(datetime.timedelta(hours=9))


def search(key, q):
    u = 'https://www.aladin.co.kr/ttb/api/ItemSearch.aspx?' + urllib.parse.urlencode({
        'ttbkey': key, 'Query': q, 'QueryType': 'Keyword', 'SearchTarget': 'Book', 'Sort': 'PublishTime',
        'MaxResults': 50, 'start': 1, 'output': 'js', 'Version': '20131101'})
    raw = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30).read().decode('utf-8', 'replace')
    d = json.loads(raw.rstrip().rstrip(';'))
    if d.get('errorCode'):
        sys.exit(f"aladin: 오류 {d.get('errorCode')} — {d.get('errorMessage')}")
    return d.get('item', [])


def is_target(it):
    c = it.get('categoryName', '')
    return '고등' in c and '영어' in c


def main():
    key = os.environ.get('ALADIN_TTB_KEY', '').strip()
    if not key:
        sys.exit('aladin: ALADIN_TTB_KEY (GitHub Secrets) 없음')
    today = datetime.datetime.now(KST).date()
    since = (today - datetime.timedelta(days=DAYS)).isoformat()
    data = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {'books': []}
    have = {b['isbn13'] for b in data['books']}
    added = 0
    for q in QUERIES:
        for it in search(key, q):
            isbn = it.get('isbn13') or it.get('isbn')
            if not isbn or isbn in have or not is_target(it) or it.get('pubDate', '') < since:
                continue
            data['books'].append({'isbn13': isbn, 'title': it.get('title', ''), 'author': it.get('author', ''),
                                  'publisher': it.get('publisher', ''), 'pubDate': it.get('pubDate', ''),
                                  'category': it.get('categoryName', ''), 'price': it.get('priceStandard'),
                                  'description': it.get('description', ''), 'link': it.get('link', ''),
                                  'found': today.isoformat(), 'status': 'new'})
            have.add(isbn); added += 1
    data['books'].sort(key=lambda b: (b['pubDate'], b['publisher'], b['title']), reverse=True)
    data['updated'] = today.isoformat()
    json.dump(data, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'aladin: 새 후보 {added}권 · 전체 {len(data["books"])}권 (status new: {sum(b["status"] == "new" for b in data["books"])}권)')
    for b in data['books'][:40]:
        if b['status'] == 'new':
            print(f"  {b['pubDate']} · {b['publisher']} · {b['title']}")


if __name__ == '__main__':
    main()
