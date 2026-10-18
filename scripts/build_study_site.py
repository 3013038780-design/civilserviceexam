"""Build the public reader and a private, self-contained local study edition.
Run with the bundled Python (Pillow, pdfplumber, pypdf). Private files stay ignored.
"""
from pathlib import Path
import argparse,base64,copy,hashlib,io,json,logging,re,shutil,subprocess
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import pdfplumber
ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'web';OUT=ROOT/'本地作答/学习网站'
DOCS=[
('strategy-research','真题阅读与分类策略研究.md','全量阅读与分类修订进度','研究与记录','实际已读、待读、题型差异和证据限制分别记录。'),
('task-branches','.agents/skills/xingce-strategy/references/task-branches.md','规则执行与图表分支','行测方法','自定规则、算法、趋势图及共享约束等候选规则。'),
('general-methods','行测分类通用方法.md','十一类通用解题方法','行测方法','九类首选流程、细分分流、白话示例与适用边界；数量图推暂缓。'),
('reading-map','行测十一类读题地图.md','十一类读题地图','学习起点','不同题型先看哪里、执行什么、何时停止。'),
('xingce-cards','行测首轮方法卡.md','四张最简方法卡','行测方法','对象与机制、题内定义、口径还原和精度停止。'),
('cross-validation','行测方法跨卷验证摘要.md','方法在哪里经过检验','行测方法','助手样例与用户掌握分开，包含失效边界。'),
('shenlun-cards','申论首轮策略卡.md','申论起手与组织','申论方法','从任务、材料到观点与论证，按题型选用。'),
('policy-cards','2026政策原文与申论机制卡.md','十张政策机制卡','申论方法','政策如何起作用、何时适用、不能推出什么。'),
('fanwen','申论范文阅读与迁移.md','30篇范文怎样迁移','申论方法','共性与反例一起看，不背万能模板。'),
('xingce-review','资料/2026副省级/AI首答核验摘要.md','2026行测核验摘要','研究与记录','128/135与参考一致，错误与限制保留。'),
('shenlun-summary','资料/2026副省级/申论首答与策略试点摘要.md','2026申论示范说明','申论方法','字数、材料依据及改进记录，不虚构评分。'),
('goal','备考目标与2026对照协议.md','目标与对照约定','研究与记录','稳定65分目标、取舍与独立作答方式。'),
('schedule','国考副省级44天备考节奏.md','备考节奏与调整','研究与记录','用真实表现调整，不以工具和阅读量验收。'),
('external-skills','外部Skills参考索引.md','公开方法来源','研究与记录','花生十三、白鹭等社区方法的具体阅读与取舍。'),
('official','2027国考官方依据与2026年变化.md','2027官方依据与变化','政策与依据','公告、大纲与指南的核对范围。'),
('policies','2026时政与政策原文索引.md','2026政策原文入口','政策与依据','真实来源和阅读范围，时点与成效分开。'),
('market','公考备考工具调研.md','市场与开源项目调研','研究与记录','产品功能声明、实际体验和效果证据分开。'),
('research','AI辅助公考提分研究与案例.md','AI辅助提分研究','研究与记录','直接证据与跨学科研究，明确适用限制。'),
('materials','资料权威性与覆盖审计.md','资料覆盖与来源','研究与记录','名师机构、真题与教材的来源分层。'),
('handoff','当前交付核对与下一步.md','当前成果与下一步','学习起点','已具备什么、仍需要哪些真实作答。'),
('modules','.agents/skills/xingce-strategy/references/modules.md','十一类模块协议','行测方法','六个观察维度的文字依据。'),
]
def image_url(im):
 b=io.BytesIO();im.convert('RGB').save(b,format='JPEG',quality=85,optimize=True)
 return 'data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()
def json_script(o):return json.dumps(o,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
def cross_year_notes(cards):
 notes=[]
 for c in cards:
  for i,part in enumerate(re.split(r'\n\s*\n',c.get('worked',''))):
   prefix=part.split('：',1)[0]
   clean=re.sub(r'https?://[^\s)]+','',part)
   years=sorted(set(map(int,re.findall(r'20\d{2}',prefix))),reverse=True)
   if not years:
    source_year=re.search(r'(20\d{2})(?:副省|地市|执法|行政执法|主卷|卷一|卷二|A|B|第)',clean)
    if not source_year:continue
    years=[int(source_year[1])]
   title=prefix if len(prefix)<85 else f'{years[0]}年 · {c["title"]}'
   notes.append({'id':f'note-{c["id"]}-{i}','kind':'note','category':c['category'],'year':years[0],'years':years,'title':title,'execution':part,'methods':[{'id':c['id'],'version':c['version']}],'status':'已整理示范；此类别全量检验未完成'})
 return notes

def cross_year_records():
 root=ROOT/'本地资料/真题策略研究';inventory=json.loads((root/'逐题策略检验清单.json').read_text())['items'];catalog={x['id']:x for x in json.loads((root/'主版本阅读目录.json').read_text())};records=[];cache={};papers={}
 for x in inventory:
  if x['status'] not in ['已有策略检验','存在争议']:continue
  if x['category'] not in ['定义判断','资料分析']:continue
  unit=catalog[x['unit_id']];source=Path(unit['path']);paper_key=hashlib.sha256(source.read_bytes()).hexdigest()[:16];paper='cross-year-papers/'+paper_key+'.pdf';papers[paper]=source
  review={}
  for link in x.get('evidence_links',[]):
   if link.get('role')!='逐题策略机制审阅':continue
   name=link['file']
   if name not in cache:cache[name]=json.loads((root/name).read_text())
   data=cache[name]
   if isinstance(data,dict):
    match=next((r for r in data.get('cases',[]) if r.get('source_id')==x['source_id']),None)
    if match:review=match
  pages=sorted(set(review.get('visual_pages',[])+review.get('text_pages',[]))) or x.get('pages',[]) or x.get('located_pages',[])
  pages=[n for n in pages if isinstance(n,int) and n>0]
  kind=unit['kind'];variant=unit['variant'];edition=str(unit['year'])+(('主卷' if variant=='主卷' else variant) if kind=='旧卷别或卷别待确认' else kind+('' if variant=='主卷' else variant))
  records.append({'id':'review-'+hashlib.sha256(x['source_id'].encode()).hexdigest()[:14],'kind':'review','category':'definition' if x['category']=='定义判断' else 'data','year':x['year'],'years':[x['year']],'title':f'{edition} · 第{x["question"]}题','task':x['actual_task'],'status':x['status'],'execution':x['decisive_basis'],'result':x['result'],'issues':x.get('issues',[]),'methods':x.get('method',[]),'first':(x.get('first_answer') or {}).get('answer'),'exposure':x.get('reference_exposure','接触范围见原记录'),'paper':paper,'pages':pages,'reference':review.get('reference'),'source_id':x['source_id']})
 return records,papers

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--public-only',action='store_true');args=parser.parse_args()
 public={'docs':[dict(id=id,path=path,title=title,group=group,description=desc,content=(ROOT/path).read_text()) for id,path,title,group,desc in DOCS],'assets':{},'methods':json.loads((WEB/'content/xingce-methods.json').read_text()),'strategyCards':json.loads((WEB/'content/xingce-branches.json').read_text())}
 public['crossYearNotes']=cross_year_notes(public['strategyCards'])
 for p in [ROOT/'图示/行测十一类六维任务图.png',ROOT/'行策20题试做结果.jpg']:
  public['assets'][str(p.relative_to(ROOT))]='assets/'+p.name;(WEB/'assets').mkdir(exist_ok=True);shutil.copy2(p,WEB/'assets'/p.name)
 (WEB/'public-data.js').write_text('window.STUDY_PUBLIC='+json_script(public)+';\n')
 if args.public_only:print(f"Public reader: {len(DOCS)} documents, 11 method entries, no private original papers.");return
 source=Path('/Users/olivialee/Desktop/国考/已分类资料/02_下载资料/行测/真题/2026/副省级/题面候选/2026年国家公务员录用考试《行测》题（副省级）.pdf')
 cache=ROOT/'tmp/学习网页';cache.mkdir(parents=True,exist_ok=True)
 if len(list(cache.glob('原卷-*.jpg')))!=26:
  subprocess.run(['pdftoppm','-jpeg','-scale-to','1700','-jpegopt','quality=82',str(source),str(cache/'原卷')],check=True)
 imgs=[Image.open(p).convert('RGB') for p in sorted(cache.glob('原卷-*.jpg'))]
 assert len(imgs)==26
 logging.getLogger('pdfminer').setLevel(logging.ERROR)
 with pdfplumber.open(source) as pdf:
  idx={}
  for i,page in enumerate(pdf.pages):
   for w in page.extract_words():
    m=re.match(r'^(\d{1,3})[.．]',w['text'])
    if m and 1<=int(m[1])<=135 and w['x0']<65:idx.setdefault(int(m[1]),dict(page=i+1,top=w['top'],y=w['top']/page.height))
  assert set(idx)==set(range(1,136))
  def crop_image(page,top,bottom):
   p=pdf.pages[page-1];im=imgs[page-1];y0=max(0,int((top-4)/p.height*im.height));y1=min(im.height,int(bottom/p.height*im.height))
   return image_url(im.crop((int(im.width*.035),y0,int(im.width*.965),max(y0+4,y1))))
  rows=json.loads((ROOT/'本地作答/2026副省级/核验与教学/逐题核验与教学.json').read_text())
  for q in rows:
   n=q['题号'];m=idx[n];end=idx.get(n+1,dict(page=26,top=pdf.pages[-1].height*.97));parts=[]
   for k in range(m['page'],end['page']+1):
    p=pdf.pages[k-1];top=m['top']-2 if k==m['page'] else 0;bottom=end['top']-3 if k==end['page'] else p.height*.965
    if bottom>top:parts.append(p.crop((0,max(0,top),p.width,bottom)).extract_text() or '')
   text='\n'.join(parts);text=re.sub(r'2026年国家公务员录用考试《行测》（副省级）','',text).strip()
   q['questionText']=text
   q['questionImage']=crop_image(m['page'],m['top'],end['top']-3 if end['page']==m['page'] else pdf.pages[m['page']-1].height*.965)
   if isinstance(q['方法来源'],list):
    a=q['方法来源'];q['方法来源']=f'方法参考：[{a[0]}]({a[1]})。'+(a[2] if len(a)>2 else '')
  # Context groups for the data-analysis questions. Original page regions, not re-created numbers.
  groups=[(116,120,22,'一'),(121,125,23,'二'),(126,130,24,'三'),(131,135,25,'四')]
  for first,last,pnum,marker in groups:
   p=pdf.pages[pnum-1];matches=p.search('（'+marker+'）',regex=False) or p.search('('+marker+')',regex=False)
   top=matches[-1]['top'] if matches else 0
   end=idx[first]
   if end['page']==pnum and top<end['top']:
    context=crop_image(pnum,top,end['top']-4)
    for q in rows:
     if first<=q['题号']<=last:q['contextImage']=context
  mapping=(ROOT/'本地作答/2026副省级申论/核验与教学/策略教学与材料映射.md').read_text()
  sections={};parts=re.split(r'(?m)^## 第([1-5])题[^\n]*\n',mapping)
  for i in range(1,len(parts),2):sections[int(parts[i])]=parts[i+1].strip()
  b={'schema':'gongkao-study/v1','title':'2026副省级逐题研习','xingce':rows,'shenlun':json.loads((ROOT/'本地作答/2026副省级申论/首答/五题首答.json').read_text()),'shenlunSections':sections,'shenlunReview':(ROOT/'本地作答/2026副省级申论/核验与教学/五题核验报告.md').read_text(),'shenlunRevisions':(ROOT/'本地作答/2026副省级申论/核验与教学/核验后改进稿.md').read_text(),'paper':{'pages':[image_url(im) for im in imgs],'map':{n:{'page':m['page'],'y':round(m['y'],5)} for n,m in idx.items()}}}
 records,papers=cross_year_records()
 b['crossYearExamples']=records
 page_jobs={}
 for x in records:
  key=Path(x['paper']).stem
  x['pageImages']=[{'page':page,'image':f'cross-year-pages/{key}-{page}.jpg'} for page in x['pages']]
  for page in x['pageImages']:page_jobs[page['image']]=(papers[x['paper']],page['page'])
 profile={"height":2000,"jpeg_quality":78,"renderer":"pdftoppm-q78"}
 profile_file=OUT/"cross-year-render-profile.json"
 rerender=not profile_file.exists() or json.loads(profile_file.read_text())!=profile
 def render_original(item):
  name,(pdf_path,page)=item;target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True)
  if rerender or not target.exists():subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-scale-to','2000','-singlefile','-jpeg','-jpegopt',f'quality={profile["jpeg_quality"]}',str(pdf_path),str(target.with_suffix(''))],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 with ThreadPoolExecutor(max_workers=4) as workers:list(workers.map(render_original,page_jobs.items()))
 profile_file.write_text(json.dumps(profile))
 # Additional original pages belong only to the private bundle, never public-data.js.
 evidence_root=ROOT/'本地资料/真题策略研究/视觉阅读'
 case_specs={
  'direct-quantity':[('2026副省级',23),('2026副省级',24),('2026副省级',25)],
  'main-claim':[('2000主卷',1),('2000主卷',2),('2001主卷',2),('2001主卷',3),('2005卷一',1),('2005卷一',2),('2005卷一',3),('2006卷一',1),('2006卷一',3),('2006卷一',5),('2023副省级',6),('2023副省级',7),('2023副省级',8),('2024副省级',6),('2024副省级',7),('2024副省级',8),('2024副省级',9),('2025副省级',7),('2025副省级',8),('2025副省级',9)],
  'reading-evidence':[('2000主卷',2),('2001主卷',3),('2001主卷',4),('2001主卷',5)],
  'definition-conditions':[('2026行政执法',17),('2013主卷',10),('2013主卷',11),('2014主卷',10),('2014主卷',11),('2014主卷',12),('2009主卷',7),('2009主卷',8),('2010主卷',8),('2010主卷',9),('2011主卷',11),('2011主卷',12),('2012主卷',10),('2012主卷',11),('2012主卷',12),('2007主卷',7),('2007主卷',8),('2008主卷',6),('2008主卷',7),('2008主卷',8)],
  'definition-relations':[('2026行政执法',16),('2025副省级',19),('2013主卷',10),('2014主卷',10),('2014主卷',11),('2010主卷',8),('2010主卷',9),('2011主卷',10),('2011主卷',11),('2012主卷',12)],
  'visual-description':[('2015副省级',11),('2026副省级',19),('2025行政执法',17)],
  'sentence-role':[('2021副省级',5),('2020副省级',5),('2020地市级',6),('2018副省级',5),('2017副省级',5),('2017副省级',7),('2016副省级',5)],
  'truth-count':[('2017副省级',13)],
  'conditional-arrows':[('2022副省级',18),('2016副省级',12),('2016副省级',13)],
  'cloze-single':[('2011主卷',3),('2008主卷',3),('2012主卷',3),('2014主卷',2),('2007主卷',3),('2002B',6),('2002A',5)],
  'cloze-evidence':[('2023副省级',4),('2022副省级',5),('2010主卷',1),('2010主卷',2),('2009主卷',2),('2009主卷',3),('2009主卷',4),('2008主卷',3),('2008主卷',4),('2011主卷',3),('2011主卷',4),('2012主卷',3),('2012主卷',4),('2013主卷',2),('2013主卷',3),('2013主卷',4),('2007主卷',3),('2007主卷',4),('2014主卷',2),('2014主卷',3),('2014主卷',4),('2002A',4),('2002A',5),('2002B',5),('2002B',6),('2002B',7),('2003B',9)],
  'ordering-links':[('2023地市级',8),('2022副省级',6),('2019地市级',6)],
  'given-rules':[('2025副省级',17),('2025副省级',18),('2024副省级',19),('2019副省级',11),('2017副省级',11),('2016副省级',11)],
  'procedure':[('2025副省级',18),('2025行政执法',17)],
  'trend-chart':[('2025副省级',23),('2025副省级',24),('2022行政执法',19),('2022行政执法',20),('2020副省级',14),('2020副省级',15),('2016副省级',15),('2016副省级',16)],
  'shared-constraints':[('2026地市级',19),('2026地市级',20),('2022行政执法',17),('2021地市级',14),('2020地市级',12),('2020地市级',13),('2019地市级',12),('2018地市级',11),('2017地市级',12)],
  'denominator':[('2026行政执法',22),('2026行政执法',23),('2026行政执法',24),('2017副省级',14),('2017副省级',15),('2016副省级',14),('2016副省级',15),('2014主卷',14),('2014主卷',15),('2013主卷',14),('2012主卷',13),('2012主卷',14),('2011主卷',15),('2010主卷',14),('2007主卷',12),('2005卷一',16),('2006卷一',19)],
  'growth-amount':[('2006卷一',19),('2006卷一',20),('2020副省级',16),('2022副省级',20)],
  'growth-base':[('2003A',17),('2003A',18),('2004A',10),('2004A',11)],
  'annual-growth':[('2023副省级',24),('2010主卷',14),('2002A',14),('2002A',15)],
  'shared-endpoint':[('2023副省级',26),('2018副省级',16)],
  'growth-chain':[('2004A',9),('2004A',10),('2005卷一',16),('2017副省级',15)],
  'share-change':[('2020副省级',16),('2021副省级',19),('2023副省级',22),('2023副省级',23)],
  'part-change':[('2003B',15),('2003B',16),('2020副省级',16),('2022副省级',20)],
  'average-change':[('2025副省级',26),('2009主卷',13),('2009主卷',14),('2010主卷',14),('2005卷一',16),('2005卷一',17)],
  'identifiability':[('2006卷一',19),('2006卷一',20),('2026行政执法',22),('2026行政执法',23),('2026行政执法',24),('2019副省级',16),('2015副省级',14),('2013主卷',13),('2003B',15),('2003B',16)],
  'scope':[('2026行政执法',19),('2026行政执法',20),('2022行政执法',16),('2018副省级',13),('2017副省级',12),('2016副省级',13),('2015副省级',12)],
  'question-mechanism':[('2025地市级',9),('2025地市级',10),('2025地市级',11)],
  'three-word-relations':[('2024地市级',18),('2018副省级',12)],
  'added-batch':[('2024行政执法',22),('2024行政执法',23),('2024行政执法',24),('2021地市级',18)]}
 evidence_pages={};evidence_cases={}
 for case,sources in case_specs.items():
  ids=[]
  for edition,page in sources:
   key=f'{edition}-PDF{page:02}';ids.append(key)
   if key not in evidence_pages:
    im=Image.open(evidence_root/edition/f'PDF{page:02}.png');im.thumbnail((1100,1700))
    evidence_pages[key]={'label':f'{edition} · PDF第{page}页','image':image_url(im)}
  evidence_cases[case]=ids
 b['strategyEvidence']={'pages':evidence_pages,'cases':evidence_cases}
 practice_file=ROOT/'本地资料/真题策略研究/定义样板_试用入口.json'
 if practice_file.exists():
  b['strategyPractice']=json.loads(practice_file.read_text())
  b['strategyPracticeReview']=json.loads((ROOT/'本地资料/真题策略研究/定义分支_试用核验.json').read_text())
 data_practice_file=ROOT/'本地资料/真题策略研究/资料分支_试用入口.json'
 if data_practice_file.exists():
  practice=json.loads(data_practice_file.read_text())
  assert not set(practice)&set(b.get('strategyPractice',{}))
  b.setdefault('strategyPractice',{}).update(practice)
  review=json.loads((ROOT/'本地资料/真题策略研究/资料分支_试用核验.json').read_text())
  assert not set(review)&set(b.get('strategyPracticeReview',{}))
  b.setdefault('strategyPracticeReview',{}).update(review)
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/'公考学习资料包.json').write_text(json_script(b))
 html=(WEB/'index.html').read_text().replace('<link rel="stylesheet" href="app.css">','<style>'+(WEB/'app.css').read_text()+'</style>')
 public_inline=dict(public);public_inline['assets']={}
 for k,v in public['assets'].items():
  raw=(WEB/v).read_bytes();mime='image/png' if v.endswith('.png') else 'image/jpeg';public_inline['assets'][k]='data:'+mime+';base64,'+base64.b64encode(raw).decode()
 html=html.replace('<script src="public-data.js"></script>','<script>window.STUDY_PUBLIC='+json_script(public_inline)+';</script>')
 html=html.replace('<!-- STUDY_BUNDLE -->','<script id="study-bundle" type="application/json">'+json_script(b)+'</script>')
 html=html.replace('<script src="app.js"></script>','<script>'+(WEB/'app.js').read_text()+'</script>')
 (OUT/'公考解题研习室.html').write_text(html)
 # An HTTP preview with the same preloaded data, no need to import during QA.
 local=OUT/'preview';shutil.copytree(WEB,local,dirs_exist_ok=True)
 for name,source_paper in papers.items():
  target=local/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source_paper,target)
  portable=OUT/name;portable.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source_paper,portable)
 shutil.copytree(OUT/'cross-year-pages',local/'cross-year-pages',dirs_exist_ok=True)
 # Keep hosted files below the static host's per-file limit as evidence grows.
 # The portable single-file edition above retains the complete bundle.
 hosted_bundle={k:v for k,v in b.items() if k!='strategyEvidence'}
 hosted_bundle=copy.deepcopy(hosted_bundle)
 # Reuse exact bytes for 2026 pages/crops; shared context images get one asset.
 # Portable HTML and import JSON above remain fully self-contained.
 paper_images=local/'paper-images';paper_images.mkdir(exist_ok=True)
 used_paper_images=set()
 def externalize_paper_image(value):
  match=re.fullmatch(r'data:image/jpeg;base64,([A-Za-z0-9+/=]+)',value);assert match
  raw=base64.b64decode(match[1]);name=hashlib.sha256(raw).hexdigest()[:24]+'.jpg'
  (paper_images/name).write_bytes(raw);used_paper_images.add(name)
  return 'paper-images/'+name
 hosted_bundle['paper']['pages']=[externalize_paper_image(value) for value in hosted_bundle['paper']['pages']]
 for question in hosted_bundle['xingce']:
  for field in ['questionImage','contextImage']:
   if question.get(field):question[field]=externalize_paper_image(question[field])
 for stale in paper_images.iterdir():
  if stale.name not in used_paper_images:stale.unlink()
 # Exact existing bytes, loaded on demand; portable/import bundles stay embedded.
 practice_images=local/'practice-images';practice_images.mkdir(exist_ok=True)
 used_practice_images=set()
 for group in hosted_bundle.get('strategyPractice',{}).values():
  for q in group.get('questions',[]):
   if not q.get('image'):continue
   match=re.fullmatch(r'data:image/(jpeg|png|webp);base64,([A-Za-z0-9+/=]+)',q['image']);assert match
   raw=base64.b64decode(match[2]);ext={'jpeg':'jpg','png':'png','webp':'webp'}[match[1]]
   name=hashlib.sha256(raw).hexdigest()[:24]+'.'+ext
   (practice_images/name).write_bytes(raw);used_practice_images.add(name)
   q['image']='practice-images/'+name
 for stale in practice_images.iterdir():
  if stale.name not in used_practice_images:stale.unlink()

 # Split by complete page records; never split image data or omit a referenced page.
 # Scripts execute in order before app.js, preserving the existing reader contract.
 for stale in local.glob('strategy-evidence*.js'):stale.unlink()
 # Hosted pages keep exactly the same JPEG bytes as the portable bundle, but
 # avoid base64 expansion in JavaScript and load only when the user opens them.
 hosted_evidence={}
 strategy_pages=local/'strategy-pages';strategy_pages.mkdir(exist_ok=True)
 for key,value in evidence_pages.items():
  raw=base64.b64decode(value['image'].split(',',1)[1])
  image_name=hashlib.sha256(raw).hexdigest()[:24]+'.jpg'
  (strategy_pages/image_name).write_bytes(raw)
  hosted_evidence[key]={**value,'image':'strategy-pages/'+image_name}
 chunks=[];chunk={};size=0;chunk_limit=8*1024*1024
 for key,value in hosted_evidence.items():
  item_size=len(json_script({key:value}).encode('utf-8'))
  if chunk and size+item_size>chunk_limit:chunks.append(chunk);chunk={};size=0
  chunk[key]=value;size+=item_size
 if chunk:chunks.append(chunk)
 evidence_assets=[]
 for i,pages in enumerate(chunks):
  name=f'strategy-evidence-{i}.js';evidence_assets.append(name)
  init='window.STUDY_STRATEGY_EVIDENCE='+json_script({'pages':{},'cases':evidence_cases})+';\n' if i==0 else ''
  (local/name).write_text(init+'Object.assign(window.STUDY_STRATEGY_EVIDENCE.pages,'+json_script(pages)+');\n')
 scripts=''.join('<script src="'+name+'"></script>' for name in evidence_assets)
 preview=(WEB/'index.html').read_text().replace('<!-- STUDY_BUNDLE -->','<script id="study-bundle" type="application/json">'+json_script(hosted_bundle)+'</script>'+scripts)
 # Content fingerprints prevent a refreshed page from reusing an older UI or method library.
 for asset in ['app.css','app.js','public-data.js']+evidence_assets:
  digest=hashlib.sha256((local/asset).read_bytes()).hexdigest()[:12]
  preview=preview.replace('"'+asset+'"','"'+asset+'?v='+digest+'"')
 (local/'index.html').write_text(preview)
 assert all(p.stat().st_size<25*1024*1024 for p in local.rglob('*') if p.is_file()),'Hosted asset exceeds 25 MiB'
 summary={'xingce':len(rows),'shenlun':len(b['shenlun']),'paper_pages':26,'mapped_questions':len(idx),'public_documents':len(public['docs']),'bundle_bytes':(OUT/'公考学习资料包.json').stat().st_size,'html_bytes':(OUT/'公考解题研习室.html').stat().st_size,'source_pdf_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'cross_year_records':len(records),'cross_year_papers':len(papers),'cross_year_original_pages':len(page_jobs),'hosted_strategy_pages':len(set(v['image'] for v in hosted_evidence.values())),'hosted_strategy_image_bytes':sum(f.stat().st_size for f in strategy_pages.glob('*.jpg')),'context_groups':[{'questions':[a,z],'page':p} for a,z,p,_ in groups]}
 (OUT/'构建记录.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
