"""저장소에 써 둔 블로그 글(HTML)을 리카수니 블로그(Blogger)에 발행. (자유 형식 글: 업데이트 소식, 공지 등)

  python blogger_publish_file.py blog_queue/파일.html "제목" "라벨1,라벨2" [--draft | --update]

--update: 이미 발행한 글(발행 기록 있음)의 내용을 새 파일 내용으로 고침. 주소는 그대로.

연결 정보는 blogger_post.py 와 같은 BLOGGER_* 환경변수(GitHub Secrets). 발행 기록은 blogger_posted.json 에 'file:파일명' 으로 남겨
같은 파일을 두 번 올리지 않음 (--draft 는 기록 안 남김).
"""
import json, os, sys
import blogger_post as bp

def main():
    args = [a for a in sys.argv[1:] if a not in ('--draft', '--update')]
    draft = '--draft' in sys.argv
    upd = '--update' in sys.argv
    path, title = args[0], args[1]
    labels = [x.strip() for x in (args[2] if len(args) > 2 else '').split(',') if x.strip()]
    if not all(bp.env(k) for k in ('BLOGGER_CLIENT_ID', 'BLOGGER_CLIENT_SECRET', 'BLOGGER_REFRESH_TOKEN', 'BLOGGER_BLOG_ID')):
        sys.exit('blogger: 연결 정보(Secrets) 없음')
    key = 'file:' + os.path.basename(path)
    log = json.load(open(bp.LOG)) if os.path.exists(bp.LOG) else {}
    if upd:
        if key not in log: sys.exit('blogger: 발행 기록이 없어서 고칠 글을 못 찾았어요')
        r = bp.update(bp.access_token(), log[key]['id'], title, open(os.path.join(bp.HERE, path)).read(), labels)
        print('blogger: 수정', r.get('url')); return
    if key in log and not draft:
        print('blogger: 이미 발행한 글이에요 —', log[key].get('url')); return
    r = bp.publish(bp.access_token(), title, open(os.path.join(bp.HERE, path)).read(), labels, draft)
    if draft:
        print('blogger: 임시저장 완료 —', title); return
    log[key] = {'url': r.get('url'), 'id': r.get('id'), 'title': title}
    json.dump(log, open(bp.LOG, 'w'), ensure_ascii=False, indent=1)
    print('blogger: 발행', r.get('url'))

if __name__ == '__main__':
    main()
