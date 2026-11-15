import re, json, glob, os
B=os.path.dirname(os.path.abspath(__file__))
SKIP={'4247926672926093180','302018609379639360','2127302986237315165','2275472463622639545'}  # 선행사(문법 용어)·'선행되어야'(다른 뜻)
SPEC=[('예비고1인 중3은','중3은'),('중3 예비고1 통합과학','중3 통합과학'),('중3·예비고1','중3'),('#예비고1 ',''),
 ('예비 중1 과정 완성 몰입 클래스','중등 준비 몰입 클래스'),('예비과정','준비 과정'),
 ('선행 몰입','심화 몰입'),('엘리트 선행반','엘리트 심화반'),('중등 학습 선행','중등 학습 대비'),('중등 선행','중등 대비'),
 ('선행 학습하는','먼저 학습하는'),('선행 학습','사전 학습'),('#중등수학선행','#중등수학심화')]
RX=[(r'예비\s?중1','초6'),(r'예비고1','중3'),(r'\s?\(현 초6\)',''),(r'선행','연계')]
def fix_text(s):
    for a,b in SPEC: s=s.replace(a,b)
    for a,b in RX: s=re.sub(a,b,s)
    return s
def fix_html(c):
    parts=re.split(r'((?:src|href)="[^"]*")',c)
    return ''.join(p if i%2 else fix_text(p) for i,p in enumerate(parts))
def plan():
    for f in sorted(glob.glob(B+'/*.json')):
        r=json.load(open(f)); kind=os.path.basename(f).split('-')[0]
        if r['id'] in SKIP: continue
        yield kind,r,fix_text(r['title']),fix_html(r['content'])
if __name__=='__main__':
    for kind,r,t,c in plan():
        vis=re.sub(r'(?:src|href)="[^"]*"','',c)
        print('\n##',r['url'].split('.kr')[1],'| 남은 예비/선행:',len(re.findall('예비|선행',t+vis)),'| 제목:',t if t!=r['title'] else '(그대로)')
        seen=set()
        for m in re.finditer(r'연계|심화 몰입|심화반|대비|사전 학습|먼저 학습|준비 과정|중등 준비 몰입',vis):
            x=re.sub(r'\s+',' ',re.sub('<[^>]*>',' ',vis[max(0,m.start()-40):m.end()+25])).strip()
            o=re.sub(r'\s+',' ',re.sub('<[^>]*>',' ',r['content']))
            if x not in o and x[10:] not in seen: seen.add(x[10:]); print('   ·',x)
