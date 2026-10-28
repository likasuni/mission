"""리카수니 블로그(또는 코코스 홈페이지) 글 하나를 Blogger API 로 읽어서 로그에 출력. (이 작업 환경에선 블로그 주소 접속이 막혀 있어 Actions 로 읽음)

  python blogger_read.py https://www.likasuni.com/2025/09/blog-post_30.html
"""
import json, os, sys, urllib.parse, urllib.request
import blogger_post as bp

def main():
    u = urllib.parse.urlparse(sys.argv[1])
    tok = bp.access_token()
    h = {'Authorization': f'Bearer {tok}'}
    b = bp.call(urllib.request.Request('https://www.googleapis.com/blogger/v3/blogs/byurl?url=' + urllib.parse.quote(f'{u.scheme}://{u.netloc}/', safe=''), headers=h))
    p = bp.call(urllib.request.Request(f"https://www.googleapis.com/blogger/v3/blogs/{b['id']}/posts/bypath?path=" + urllib.parse.quote(u.path) + '&view=AUTHOR', headers=h))
    print('=====POST=====')
    print(json.dumps({k: p.get(k) for k in ('title', 'url', 'published', 'updated', 'labels', 'content')}, ensure_ascii=False))
    print('=====END=====')

if __name__ == '__main__':
    main()
