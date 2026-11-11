#!/usr/bin/env python3
# 블로그(Blogger) 연결 열쇠를 새로 받아 맥 키체인에 넣어요. 값은 채팅·파일에 남지 않아요.
# 쓰는 법: python3 _tools/auto/blogger_login.py
#   1) 클라이언트 ID·보안 비밀번호를 물어보면 터미널에 붙여 넣기 (보안 비밀번호는 글자가 안 보여요)
#   2) 크롬이 열리면 구글 로그인 → 허용
#   3) 끝나면 키체인에 likasuni-BLOGGER_* 4개가 들어가요
import base64, getpass, hashlib, http.server, json, os, secrets, subprocess, sys, threading, urllib.parse, urllib.request, webbrowser

SCOPE = 'https://www.googleapis.com/auth/blogger'
BLOG_URL = 'https://www.likasuni.com/'

cid = input('클라이언트 ID: ').strip()
if '--show' in sys.argv:   # 붙여 넣기가 안 될 때: 글자가 화면에 보이게 받아요 (끝나면 터미널을 닫거나 clear)
    csec = input('클라이언트 보안 비밀번호 (붙여 넣기, 글자가 보여요): ').strip()
else:
    csec = getpass.getpass('클라이언트 보안 비밀번호 (붙여 넣기, 글자는 안 보여요): ').strip()
if not cid or not csec: sys.exit('값이 비었어요.')

verifier = base64.urlsafe_b64encode(os.urandom(48)).rstrip(b'=').decode()
challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
state = secrets.token_urlsafe(16)
got = {}

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if 'code' in q or 'error' in q:
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers()
            self.wfile.write('<meta charset=utf-8><h2>연결됐어요. 이 창을 닫고 터미널로 돌아가세요.</h2>'.encode())
        else:
            self.send_response(404); self.end_headers()
    def log_message(self, *a): pass

srv = http.server.HTTPServer(('127.0.0.1', 0), H)
redirect = f'http://127.0.0.1:{srv.server_address[1]}'
url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode({
    'client_id': cid, 'redirect_uri': redirect, 'response_type': 'code', 'scope': SCOPE, 'state': state,
    'access_type': 'offline', 'prompt': 'consent', 'code_challenge': challenge, 'code_challenge_method': 'S256'})
print('\n크롬이 열려요. 열리지 않으면 아래 주소를 크롬에 붙여 넣으세요:\n' + url + '\n')
webbrowser.open(url)
while not got: srv.handle_request()
if 'error' in got or got.get('state') != state: sys.exit('허용되지 않았어요: ' + got.get('error', 'state 불일치'))

def post(u, data):
    req = urllib.request.Request(u, data=urllib.parse.urlencode(data).encode())
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        sys.exit('구글 오류: ' + e.read().decode()[:300])

tok = post('https://oauth2.googleapis.com/token', {
    'code': got['code'], 'client_id': cid, 'client_secret': csec, 'redirect_uri': redirect,
    'grant_type': 'authorization_code', 'code_verifier': verifier})
if 'refresh_token' not in tok: sys.exit('refresh token 이 안 왔어요. 구글 계정 > 보안 > 서드파티 연결에서 이 앱을 지운 뒤 다시 해 주세요.')

req = urllib.request.Request('https://www.googleapis.com/blogger/v3/blogs/byurl?url=' + urllib.parse.quote(BLOG_URL),
                             headers={'Authorization': 'Bearer ' + tok['access_token']})
try:
    blog = json.load(urllib.request.urlopen(req, timeout=30))
except urllib.error.HTTPError as e:
    sys.exit('블로그를 못 찾았어요: ' + e.read().decode()[:300])
print('블로그 확인:', blog.get('name'), blog.get('url'))

user = os.environ.get('USER', 'user')
for name, val in [('BLOGGER_CLIENT_ID', cid), ('BLOGGER_CLIENT_SECRET', csec),
                  ('BLOGGER_REFRESH_TOKEN', tok['refresh_token']), ('BLOGGER_BLOG_ID', blog['id'])]:
    r = subprocess.run(['security', 'add-generic-password', '-U', '-s', 'likasuni-' + name, '-a', user, '-w', val], capture_output=True, text=True)
    print(('저장됨   ' if r.returncode == 0 else '실패     ') + name)
print('\n끝났어요. 이제 새벽 자동 작업이 블로그 요약 글도 올려요.')
