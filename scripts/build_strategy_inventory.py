"""Conservative evidence linkage; no reading/validation inferred from extraction or answers."""
from pathlib import Path
import json,re,unicodedata,hashlib,collections,datetime
ROOT=Path(__file__).resolve().parents[1]; R=ROOT/'本地资料/真题策略研究'
def read(p):return json.loads(p.read_text())
def write(p,d):
 t=p.with_suffix('.tmp');t.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');t.replace(p)
cat=read(R/'主版本阅读目录.json');units={x['id']:x for x in cat};order={x['id']:i for i,x in enumerate(cat)};ledger={x['id']:x for x in read(R/'阅读账本.json')['rows']};queue=read(R/'题型优先研究队列.json')['items'];rows={};gaps=[]
for x in queue:
 u,n=x['source_id'].rsplit(':',1)
 if u not in units:gaps.append({'source_id':x['source_id'],'reason':'队列卷标不匹配主目录，待人工关联'});continue
 rows[x['source_id']]={'source_id':x['source_id'],'unit_id':u,'year':units[u]['year'],'question':int(n),'pages':[x['page']] if isinstance(x.get('page'),int) else x.get('pages',[]),'actual_task':x['actual_task'],'category':x['queue_category'],'classification_status':x.get('classification_basis'),'reading':'已有实际任务标签；范围见账本','status':'已读待策略检验','evidence_links':[{'file':x['record_file'],'question':int(n),'role':'任务标签'}],'method':None,'first_answer':None,'reference_exposure':'尚未统一，查原冻结记录','decisive_basis':None,'result':None,'issues':[],'candidate_methods':[]}
# Add machine-located positions only; never promote them to reading or validation.
for u in cat:
 pages=read(R/'抽取'/u['id']/'pages.json');located={};uncertain=[]
 for pn,text in enumerate(pages,1):
  text=unicodedata.normalize('NFKC',text)
  starts=list(re.finditer(r'(?m)^\s*(\d{1,3})\s*[、.．)）]\s*(?=\S)',text))
  for i,m in enumerate(starts):
   n=int(m.group(1));block=text[m.end():starts[i+1].start() if i+1<len(starts) else len(text)]
   if not 1<=n<=160:continue
   if len(block)<8:continue
   # Item lists/formula numbers are not treated as confirmed questions.
   option=bool(re.search(r'(?:^|\s)[ABＡＢ][、.．:：)）]',block))
   if not option and not (u['id']+':'+str(n) in rows):
    uncertain.append({'page':pn,'number':n,'reason':'无明确选项，可能跨页题/子条目，不自动入题'});continue
   located.setdefault(n,[]).append(pn)
 for n,pg in located.items():
  key=u['id']+':'+str(n)
  if key in rows:
   rows[key]['located_pages']=pg;continue
  rows[key]={'source_id':key,'unit_id':u['id'],'year':u['year'],'question':n,'pages':pg,'actual_task':None,'category':'待人工分流','classification_status':'机器定位候选，不代表已读或题号完整','reading':'定位自抽取文本，未人工确认','status':'尚未阅读','evidence_links':[{'file':'抽取/'+u['id']+'/pages.json','pages':pg,'role':'候选定位'}],'method':None,'first_answer':None,'reference_exposure':'未核；正文例题/附带答案需实际阅读时登记','decisive_basis':None,'result':None,'issues':[],'candidate_methods':[]}
 if uncertain:gaps.append({'unit_id':u['id'],'reason':'自动定位有未确认编号；不作为真题完整性审计','positions':uncertain})
# Find only explicit identities or unique filename identities; ambiguous links remain unresolved.
skip={'续接检查点.json','阅读账本.json','题型优先研究队列.json','主版本阅读目录.json','逐题策略检验清单.json','策略检验盘点汇总.json','定义80题_策略执行审阅.json','策略下一批.json'}
def unit_from_filename(name):
 ids=[u['id'] for u in cat if u['id'] in name]
 if len(ids)==1:return ids[0]
 m=re.match(r'(20\d{2})(副省级|地市级|行政执法|主卷|卷一|卷二|A|B)',name)
 if not m:return None
 y=int(m[1]);kind=m[2];want=[u['id'] for u in cat if u['year']==y and ((kind in ['副省级','地市级','行政执法'] and u['kind']==kind) or (kind=='主卷' and u['variant']=='主卷' and '旧' in u['kind']) or (kind.startswith('卷') and u['variant']==kind[-1]) or (kind in ['A','B'] and u['variant']==kind))]
 return want[0] if len(want)==1 else None
def walk(v,unit,path,ptr=''):
 if isinstance(v,list):
  for i,x in enumerate(v):walk(x,unit,path,ptr+'/'+str(i))
 elif isinstance(v,dict):
  unit=v.get('unit_id') or unit
  if not unit and isinstance(v.get('year'),int) and v.get('kind'):
   want=[u['id'] for u in cat if u['year']==v['year'] and u['kind']==v['kind'] and u['variant']==v.get('variant','主卷')]
   if len(want)==1:unit=want[0]
  n=v.get('question',v.get('题号',v.get('q')))
  if isinstance(n,int) and unit in units:
   row=rows.get(f'{unit}:{n}')
   if row:
    role='冻结首答候选' if '首答' in path.name else '核验候选' if re.search('核验|修订',path.name) else '关联记录'
    link={'file':str(path.relative_to(R)) if path.is_relative_to(R) else str(path.relative_to(ROOT)),'pointer':ptr,'role':role}
    if link not in row['evidence_links']:row['evidence_links'].append(link)
    if role=='冻结首答候选' and isinstance(v.get('answer'),str) and v['answer'] in ['A','B','C','D'] and not row['first_answer']:
     row['first_answer']={'answer':v['answer'],'file':link['file'],'pointer':ptr,'status':'旧首答关联，接触情况见原记录'}
  for k,x in v.items():
   if isinstance(x,(dict,list)):walk(x,unit,path,ptr+'/'+k)
for p in sorted(R.glob('*.json')):
 if p.name in skip or '任务标签' in p.name or p.name.startswith('策略'):continue
 try:walk(read(p),unit_from_filename(p.name),p)
 except (TypeError,ValueError) as e:gaps.append({'file':p.name,'reason':'记录格式待关联：'+str(e)})
# Baseline teaching is already checked, but needs method-version execution linkage.
p=ROOT/'本地作答/2026副省级/核验与教学/逐题核验与教学.json'
for i,c in enumerate(read(p)):
 row=rows.get(f'2026-副省级-主卷:{c["题号"]}')
 if row:
  row['evidence_links'].append({'file':str(p.relative_to(ROOT)),'pointer':'/'+str(i),'role':'已有逐题核验教学；版本化策略执行待关联'})
  row['first_answer']={'answer':c['首答'],'file':str(p.relative_to(ROOT)),'pointer':'/'+str(i),'status':'既有冻结首答的教学副本，原件保持'}
# Only reviewed explicit evidence can promote strategy status.
p=R/'定义80题_策略执行审阅.json'
if p.exists():
 for c in read(p)['cases']:
  key=c['source_id'];row=rows[key];row.update(status=c['inventory_status'],method=c['methods'],decisive_basis=c['execution'],result=c['assessment'],reference_exposure='已接触目标参考；本轮复用旧首答及已存核验作机制审阅，不称新独立作答',issues=c['issues']);row['evidence_links'].append({'file':p.name,'question':row['question'],'role':'逐题策略机制审阅'})
for p in sorted(R.glob('定义策略检验_*.json')):
 for c in read(p)['cases']:
  row=rows[c['source_id']];row.update(status=c['inventory_status'],method=c['methods'],decisive_basis=c['execution'],result=c['assessment'],reference_exposure='复用旧首答及既有参考，非新独立作答',issues=c['issues']);row['evidence_links'].append({'file':p.name,'question':row['question'],'role':'逐题策略机制审阅'})
cards=read(ROOT/'web/content/xingce-branches.json')
current_versions={c['id']:c.get('version') for c in cards}
for row in rows.values():
 stale=[m for m in (row['method'] or []) if current_versions.get(m['id'])!=m['version']]
 if stale:
  row['previous_review_status']=row['status'];row['status']='需要回查';row['issues']=list(row['issues'])+['已存方法版本不同于当前规则，保留原记录，完成回查前不自动继承有效性']
 row['candidate_methods']=[c['id'] for c in cards if c['category']=={'定义判断':'definition','资料分析':'data','中心句与排序':'structure','阅读理解':'reading','选词填空':'cloze','逻辑判断':'logic','类比推理':'analogy'}.get(row['category'])]
 row['candidate_method_note']='仅按已有导航提供候选，不是方法执行或效果证据'
items=sorted(rows.values(),key=lambda x:(order[x['unit_id']],x['question']))
summary=[]
for u in cat:
 xs=[x for x in items if x['unit_id']==u['id']];l=ledger[u['id']];summary.append({'unit_id':u['id'],'source':u['path'],'text_read_pages':l.get('text_read_pages',[]),'visual_read_pages':l.get('visual_read_pages',[]),'reading_stage':l.get('stage'),'indexed_positions':len(xs),'manual_task_positions':sum(x['actual_task'] is not None for x in xs),'states':dict(collections.Counter(x['status'] for x in xs)),'completeness':'仅索引定位和已有证据关联，不证明自动题号无遗漏；不开展版本审计'})
write(R/'逐题策略检验清单.json',{'schema':'strategy-audit/v1','saved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'policy':'抽取/标签不提升策略状态；候选关联待人工；已有首答不覆盖','items':items})
write(R/'策略检验盘点汇总.json',{'units':summary,'counts':{'units':len(cat),'indexed_positions':len(items),'manual_task_positions':sum(x['actual_task'] is not None for x in items),'states':dict(collections.Counter(x['status'] for x in items))},'unresolved_links_and_locations':gaps,'cards':[{'id':c['id'],'category':c['category'],'title':c['title'],'version':c.get('version'),'note':'例题扩展保持同一方法id，语义合并须人工判断'} for c in cards]})
# Explicit next 20 already-read definition positions, year descending, catalogue order.
xs=[x for x in items if x['category']=='定义判断' and x['status'] in ['已读待策略检验','需要回查']];xs.sort(key=lambda x:(0 if x['status']=='需要回查' else 1,-x['year'],order[x['unit_id']],x['question']))
write(R/'策略下一批.json',{'capacity':20,'question':'检验当前分支是否能识别并执行近年自定规则、过程与案例任务；先复用已有首答，缺完整依据则补审，不将旧参考接触当盲测','items':[{'source_id':x['source_id'],'pages':x['pages'],'actual_task':x['actual_task'],'evidence_links':x['evidence_links']} for x in xs[:20]],'rule':'20题默认；复杂共享减10，实际原题题组不拆；未读题另排，不跳过全50范围'})
print(json.dumps({'units':len(summary),'positions':len(items),'states':dict(collections.Counter(x['status'] for x in items)),'unresolved_groups':len(gaps),'next':[x['source_id'] for x in xs[:20]]},ensure_ascii=False))
