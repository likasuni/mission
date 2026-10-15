import json,collections,re,unicodedata
import re as _re
out=json.load(open('files.json'))
for o in out: o['path'][0]=o['path'][0].replace(' 기출','')
SUBJ=[('생활과윤리',['생활과윤리','생활과 윤리','생할과윤리','생활과']),('윤리와사상',['윤리와사상','윤리와 사상','윤리와']),
('한국지리',['한국지리']),('세계지리',['세계지리']),('동아시아사',['동아시아사']),('세계사',['세계사']),('경제',['경제']),
('정치와법',['정치와법','정치와 법','법과정치','법과 정치','정치와']),('사회문화',['사회문화','사회·문화','사회 문화']),
('물리학2',['물리학2','물리학Ⅱ','물리2','물리 II','물리Ⅱ','물리학II']),('물리학1',['물리학1','물리학Ⅰ','물리1','물리Ⅰ','물리학I']),
('화학2',['화학2','화학Ⅱ','화학II']),('화학1',['화학1','화학Ⅰ','화학I']),('생명과학2',['생명과학2','생명과학Ⅱ','생명과학II']),('생명과학1',['생명과학1','생명과학Ⅰ','생명과학I']),
('지구과학2',['지구과학2','지구과학Ⅱ','지구과학II']),('지구과학1',['지구과학1','지구과학Ⅰ','지구과학I']),
('통합사회',['통합사회']),('통합과학',['통합과학']),('한국사',['한국사']),('영어',['영어']),('국어',['국어']),
('수학 가형',['수학 가형','수학가형','수학(가형)']),('수학 나형',['수학 나형','수학나형','수학(나형)']),('수학',['수학'])]
GROUP={'국어':'국어','수학':'수학','수학 가형':'수학','수학 나형':'수학','영어':'영어','한국사':'한국사','통합사회':'사회','통합과학':'과학'}
for s in ['생활과윤리','윤리와사상','한국지리','세계지리','동아시아사','세계사','경제','정치와법','사회문화']: GROUP[s]='사회탐구'
for s in ['물리학1','물리학2','화학1','화학2','생명과학1','생명과학2','지구과학1','지구과학2']: GROUP[s]='과학탐구'
def subj(t):
    t=unicodedata.normalize('NFC',t).replace('-',' ').replace('_',' ')
    for name,keys in SUBJ:
        for k in keys:
            if k in t: return name
    return None
def kind(t):
    t=t.replace('-',' ')
    if '듣기' in t or '음성' in t: return '듣기대본'
    if '해설' in t or '답지' in t: return '해설'
    if '정답' in t: return '정답'
    if '문제' in t or '문재' in t: return '문제'
    return '문제'
recs=[];bad=[]
for o in out:
    t=o['title']; p=o['path']
    s=subj(t)
    if not s:
        fs=(p[4] if len(p)>4 else '') if p[0]=='모의고사' else (p[2] if len(p)>2 else '')
        s={'과학':'통합과학','사회':'통합사회','과학탐구':None,'사회탐구':None}.get(fs,fs)
    k=kind(t)
    fold=' '.join(p)
    tn=unicodedata.normalize('NFC',t)
    if s in ('기타','직업탐구','제2외국어·한문') or '직업탐구' in fold or '제2외국어' in fold:
        if '전과목' in tn: s='전과목'
        elif _re.search(r'(^|[\s_-])과학([\s_,]|$)',tn): s='통합과학'
        elif _re.search(r'(^|[\s_-])사회([\s_,]|$)',tn): s='통합사회'
        else:
            mm=_re.findall(r'[-_]\s*([^-_]+?)\s*(?:문제|정답|해설)',tn)
            nm=(mm[-1] if mm else '').replace('직업탐구','').strip(' _-·')
            grp='직업탐구' if ('직업탐구' in fold or '직업탐구' in tn) else '제2외국어·한문'
            if nm: s=nm; GROUP.setdefault(nm,grp)
    if s=='전과목': GROUP['전과목']='기타'
    if not s or not k: bad.append((p,t)); continue
    try:
      if p[0]=='모의고사':
        r=dict(exam='moe',year=int(p[1]),grade=int(p[2][1]),month=int(p[3][:-1]),subject=s,group=GROUP.get(s,'기타'),kind=k,id=o['id'],size=o['size'],title=t)
      else:
        r=dict(exam='sn',year=int(p[1][:4]),subject=s,group=GROUP.get(s,'기타'),kind=k,id=o['id'],size=o['size'],title=t)
    except (ValueError, IndexError): bad.append((p,t)); continue
    recs.append(r)
# dedupe: same key keep largest
key=lambda r:(r['exam'],r['year'],r.get('grade'),r.get('month'),r['subject'],r['kind'])
best={}
for r in recs:
    k=key(r)
    if k not in best or r['size']>best[k]['size']: best[k]=r
recs=sorted(best.values(),key=key)
json.dump(recs,open('catalog.json','w'),ensure_ascii=False,indent=0)
print('records',len(recs),'bad',len(bad)); [print(b) for b in bad[:20]]
print(collections.Counter(r['group'] for r in recs))
print(collections.Counter(r['kind'] for r in recs))
sess=collections.Counter((r['exam'],r['year'],r.get('grade'),r.get('month')) for r in recs)
print('sessions',len(sess))
