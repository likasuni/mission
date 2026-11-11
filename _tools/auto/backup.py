#!/usr/bin/env python3
# Supabase 댓글·요청 데이터를 받아 암호화해서 _backup/supabase.json.enc 로 저장 (GitHub Actions db-backup 과 같은 일)
import json, os, re, subprocess, sys, tempfile, urllib.request
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
key = os.environ.get('BACKUP_KEY', '').strip()
if not key: sys.exit('BACKUP_KEY 없음')
js = open(os.path.join(ROOT, 'common.js'), encoding='utf-8').read()
url = re.search(r'https://[a-z0-9]+\.supabase\.co', js).group(0)
anon = re.search(r'sb_publishable_[A-Za-z0-9_-]+', js).group(0)
req = urllib.request.Request(url + '/rest/v1/rpc/backup_export', data=json.dumps({'p_key': key}).encode(),
                             headers={'apikey': anon, 'Content-Type': 'application/json'})
raw = urllib.request.urlopen(req, timeout=60).read()
d = json.loads(raw)
if not (d.get('exported_at') and isinstance(d.get('comments'), list)): sys.exit('받은 데이터 모양이 이상해요')
for k, v in d.items():
    if isinstance(v, list): print(f'{k}: {len(v)}')
out = os.path.join(ROOT, '_backup', 'supabase.json.enc')
env = {**os.environ, 'BACKUP_KEY': key}
tmp = tempfile.NamedTemporaryFile(delete=False); tmp.write(raw); tmp.close(); os.chmod(tmp.name, 0o600)
try:
    enc = ['openssl', 'enc', '-aes-256-cbc', '-pbkdf2', '-iter', '200000']
    subprocess.run(enc + ['-salt', '-pass', 'env:BACKUP_KEY', '-in', tmp.name, '-out', out], check=True, env=env)
    back = subprocess.run(enc + ['-d', '-pass', 'env:BACKUP_KEY', '-in', out], check=True, env=env, capture_output=True).stdout
    if back != raw: sys.exit('암호화 확인 실패: 풀었을 때 원본과 달라요')
finally:
    os.unlink(tmp.name)
print('백업 저장:', out)
