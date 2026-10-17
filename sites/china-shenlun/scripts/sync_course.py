"""将经审阅的八课原稿同步到静态网站；原稿是正文唯一来源。"""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1];M=ROOT/'manuscripts';P=ROOT/'dist/content.js'
d=json.loads(P.read_text().removeprefix('window.COURSE = ').rstrip(';\n'))
manifest=json.loads((M/'manifest.json').read_text());old=d['lessons'][0];sources=d['sources'];byurl={s['url']:s for s in sources}
publishers={'www.12371.cn':'共产党员网','www.cac.gov.cn':'中央网信办','www.shanghai.gov.cn':'上海市人民政府门户网站','www.beijing.gov.cn':'北京市人民政府门户网站','jhs.moa.gov.cn':'农业农村部','www.zjsjw.gov.cn':'浙江省纪委省监委网站','www.gov.cn':'中国政府网','www.moe.gov.cn':'教育部','www.bjrd.gov.cn':'北京市人大常委会网站','www.ln.gov.cn':'辽宁省人民政府门户网站','www.mofcom.gov.cn':'商务部网站'}
from urllib.parse import urlparse
lessons=[]
for x in manifest:
 text=(M/x['file']).read_text();n=x['unit'];u=d['units'][n-1];u['lessonId']='leadership-in-action' if n==2 else 'unit-'+str(n);u['status']='讲义初稿 · 待用户迁移'
 paragraphs=[p.strip() for p in text.split('\n\n') if p.strip()]
 example=next(p for p in paragraphs if re.match(r'原创(?:论证段|表达|分析段|建议段)：',p))
 prompt=next(p.removeprefix('独立输出：') for p in paragraphs if p.startswith('独立输出：'))
 core=text.split('## 这节课先弄懂什么\n\n')[1].split('\n\n')[0]
 ids=[]
 for line in text.splitlines():
  for label,url in re.findall(r'\[([^\]]+)\]\((https?://[^)]+)\)',line):
   if url not in byurl:
    pub=publishers.get(urlparse(url).hostname,'官方机构网站，发布主体见原文')
    dt=re.search(r'/(20\d{2})/(\d{2})/(\d{2})/',url) or re.search(r'/(20\d{2})(\d{2})/(?:t\d{8}|20\d{2}(\d{2})(\d{2}))',url)
    simple=re.search(r'/(20\d{2})(\d{2})/',url)
    date='-'.join(dt.groups()[:3]) if dt and len(dt.groups())==3 else (simple[1]+'-'+simple[2]+'，日期见原文' if simple else '见原文，事件日期另列于课内')
    title=re.sub(r'\[[^\]]+\]\([^)]+\)','',line).strip('- ：。') or label
    if len(title)<5:title=x['title']+' · '+label
    s={'id':'manuscript-source-'+str(len(sources)+1),'title':title,'publisher':pub,'url':url,'eventDate':'依课内事实日期；历史事件与报道日期分开','publishedAt':date,'checkedAt':'2026-10-17','locator':'第'+str(n)+'课「原文依据」或「案例」链接处','readScope':'课内所引相关段落；《纲要》具体范围见十九章选读记录','kind':'官方原文定位' if '12371.cn' in url else '案例或政策依据','applicability':'支持课内对应概念、事件或工作做法，不自动支持全国性成效','reviewScope':'已读所引段落；不是整站或全书逐条审核'}
    sources.append(s);byurl[url]=s
   ids.append(byurl[url]['id'])
 lessons.append({'id':u['lessonId'],'unit':n,'title':x['title'],'question':u['question'],'status':u['status'],'core':core,'prompt':prompt,'example':example,'check':['是否回应题目限定的对象与关系？','是否写出具体动作及其作用环节？','有无把课外知识当成题内事实，或把政策目标当成既有成效？'],'uses':old['uses'],'sourceIds':list(dict.fromkeys(ids)),'manuscript':text,'file':x['file'],'chapters':x['chapters']})
d['stage']='八课正文初稿 · Markdown / Word 已备齐';d['lessons']=lessons;d['chapterIndex']=(M/'00-章节与来源对照.md').read_text();d['readingScope']=json.loads((M/'reading-scope.json').read_text())
P.write_text('window.COURSE = '+json.dumps(d,ensure_ascii=False,indent=2)+';\n')
print(json.dumps({'lessons':len(lessons),'source_records':len(sources),'chapters':len(d['readingScope']['chapters'])}))
