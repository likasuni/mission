"""고등 영어 부교재 신간 후보 모으기 (네이버 책 검색 API). 매주 Actions `book-new` 가 실행해서 book_candidates.json 에 쌓음.

  NAVER_CLIENT_ID=... NAVER_CLIENT_SECRET=... python book_new.py

- 검색어 여러 개로 출간일 최신순(sort=date) 검색 → 제목·소개에 '영어'와 고등 관련 말(수능·고등·고1~3·모의고사·내신)이 있는 책만
  → 최근 DAYS 일 안에 나온 책만. (알라딘 OpenAPI 는 2026-11-01 서비스 종료라 네이버로 바꿈)
- 이미 있는 책(isbn)은 그대로 두고 새 책만 status 'new' 로 추가. 글로 쓴 책은 'posted', 안 쓸 책은 'skip' 으로 바꿔 둠.
- 표지 이미지는 저장하지 않음 (교재 소식에 표지 싣지 않음).
"""
import datetime, html, json, os, re, sys, urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'book_candidates.json')
DAYS = 60
QUERIES = ['수능 영어', '고등 영어 독해', '고등 영어 어휘', '고등 영어 문법', '수능 영어 듣기', '영어 모의고사', '고1 영어', '고2 영어', '고3 영어', '영어 구문 독해', '영어 내신']
LEVEL = re.compile(r'수능|고등|고[123]|모의고사|내신|EBS')
KST = datetime.timezone(datetime.timedelta(hours=9))


def env(k): return os.environ.get(k, '').strip()


def clean(s): return html.unescape(re.sub(r'<[^>]+>', '', s or '')).strip()


def search(q):
    u = 'https://openapi.naver.com/v1/search/book.json?' + urllib.parse.urlencode({'query': q, 'display': 100, 'start': 1, 'sort': 'date'})
    req = urllib.request.Request(u, headers={'X-Naver-Client-Id': env('NAVER_CLIENT_ID'), 'X-Naver-Client-Secret': env('NAVER_CLIENT_SECRET')})
    try:
        return json.load(urllib.request.urlopen(req, timeout=30)).get('items', [])
    except urllib.error.HTTPError as x:
        sys.exit(f'naver: 오류 {x.code} — {x.read().decode(errors="replace")[:300]}')


def main():
    if not (env('NAVER_CLIENT_ID') and env('NAVER_CLIENT_SECRET')):
        sys.exit('naver: NAVER_CLIENT_ID / NAVER_CLIENT_SECRET (GitHub Secrets) 없음')
    today = datetime.datetime.now(KST).date()
    since = (today - datetime.timedelta(days=DAYS)).strftime('%Y%m%d')
    upto = (today + datetime.timedelta(days=31)).strftime('%Y%m%d')  # 출간 예정 한 달까지
    data = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {'books': []}
    have = {b['isbn13'] for b in data['books']}
    added = 0
    for q in QUERIES:
        for it in search(q):
            isbn = (it.get('isbn') or '').split()[-1] if it.get('isbn') else ''
            title, desc, pd = clean(it.get('title')), clean(it.get('description')), it.get('pubdate', '')
            text = title + ' ' + desc
            if not isbn or isbn in have or not (since <= pd <= upto) or '영어' not in text or not LEVEL.search(text):
                continue
            data['books'].append({'isbn13': isbn, 'title': title, 'author': clean(it.get('author')).replace('^', ', '),
                                  'publisher': clean(it.get('publisher')), 'pubDate': f'{pd[:4]}-{pd[4:6]}-{pd[6:8]}',
                                  'price': it.get('discount') or None, 'description': desc, 'link': it.get('link', ''),
                                  'found': today.isoformat(), 'status': 'new'})
            have.add(isbn); added += 1
    data['books'].sort(key=lambda b: (b['pubDate'], b['publisher'], b['title']), reverse=True)
    data['updated'] = today.isoformat()
    json.dump(data, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'naver: 새 후보 {added}권 · 전체 {len(data["books"])}권 (status new: {sum(b["status"] == "new" for b in data["books"])}권)')
    for b in data['books'][:60]:
        if b['status'] == 'new':
            print(f"  {b['pubDate']} · {b['publisher']} · {b['title']}")


if __name__ == '__main__':
    main()
