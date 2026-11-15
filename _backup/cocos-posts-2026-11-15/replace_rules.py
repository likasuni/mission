import re, json, glob, os
B='/private/tmp/claude-502/-Users-likasuni2--claude-spares-spare-rXkIVR/0054c465-b10f-492a-87c5-33234c77f5e4/scratchpad/cocos_backup'
SKIP={'5752533207974695292','3328938026287258622'}  # 미래엔 교재 단계 이름(예비중학)만 있는 글
SPEC=[('#이매동예비중1 #예비중1영어 #예비중영어 ','#이매동초6영어 '),('초6 예비중반','초6 중등 준비반'),('초6 예비중 ~','초6 ~'),('초6 예비중부터','초6부터'),
 ('예비고1(중3)','중3'),('중3, 예비고1 영어','중3 영어'),('예비중·예비고','초6·중3'),('예비 중등 필수','중등 필수'),
 ('예비 중학생(5~6학년)도','초등 5~6학년도'),('예비 중학생도','초등 5~6학년도'),('#예비중영어','#초6영어')]
RX=[(r'예비\s?중1','초6'),(r'예비고1','중3'),(r'예비\s?중2','중2 준비'),(r'예비\s?중3','중3 준비'),(r'예비고','중3'),(r'예비중(?!학)','초6')]
def fix_text(s):
    for a,b in SPEC: s=s.replace(a,b)
    for a,b in RX: s=re.sub(a,b,s)
    return s
def fix_html(c):  # 주소(src·href) 안은 건드리지 않음
    parts=re.split(r'((?:src|href)="[^"]*")',c)
    return ''.join(p if i%2 else fix_text(p) for i,p in enumerate(parts))
def plan():
    out=[]
    for f in sorted(glob.glob(B+'/*.json')):
        r=json.load(open(f))
        if r['id'] in SKIP: continue
        t=fix_text(r['title']); c=fix_html(r['content']); l=[('중3영어' if x=='예비고1' else x) for x in (r.get('labels') or [])]
        out.append((r,t,c,l))
    return out
if __name__=='__main__':
    for r,t,c,l in plan():
        left=len(re.findall('예비',re.sub(r'(?:src|href)="[^"]*"','',c)))+t.count('예비')
        print('\n##',r['url'].split('.kr')[1],'| 남은 예비:',left,'| 길이',len(r['content']),'→',len(c))
        if t!=r['title']: print('   제목:',t)
        seen=set()
        for m in re.finditer(r'초6|중3|중2 준비|중등 준비반|초등 5~6학년도|중등 필수',c):
            x=re.sub(r'\s+',' ',re.sub('<[^>]+>',' ',c[max(0,m.start()-60):m.end()+60]))[:95]
            o=re.sub(r'\s+',' ',re.sub('<[^>]+>',' ',r['content']))
            if x[20:60] not in o and x not in seen: seen.add(x); print('   ·',x[15:85])
