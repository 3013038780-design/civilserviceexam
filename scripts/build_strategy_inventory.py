"""Conservative evidence linkage; no reading/validation inferred from extraction or answers."""
from pathlib import Path
import json,re,unicodedata,hashlib,collections,datetime
from definition_source_checks import load_no_definition_inspections
from data_source_checks import load_no_data_inspections
from research_scope import MINIMUM_YEAR, in_current_scope, can_schedule
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
# Explicit task routing is independent of adopting a candidate solving rule.
# Only human-confirmed original-question decisions can change navigation;
# these links never promote reading or strategy status.
routing_path=R/'主旨新版候选_回查清单.json'
if routing_path.exists():
 for index,decision in enumerate(read(routing_path).get('routed_out',[])):
  if not decision.get('classification_confirmed'):continue
  assert decision['target_category'] in ['中心句与排序','阅读理解']
  evidence=read(R/decision['classification_evidence'])
  assert any(x['source_id']==decision['source_id'] for x in evidence['routed_out'])
  row=rows[decision['source_id']]
  row['category']=decision['target_category'];row['actual_task']=decision['actual_task']
  row['classification_status']='实际题面审阅确认分流，未据此提升策略检验'
  row['evidence_links'].append({'file':routing_path.name,'pointer':'/routed_out/'+str(index),'role':'实际设问分流审阅，非策略检验'})
# Only reviewed explicit evidence can promote strategy status.
def link_review_metadata(row,case):
 if case.get('actual_task'):
  row['actual_task']=case['actual_task']
  row['classification_status']='逐题策略审阅确认实际任务'
 # Explicit reviewed links take precedence over filename guesses, including
 # a documented missing first answer. This changes the index, never originals.
 if 'first_answer' not in case:return
 row['first_answer']=case['first_answer']
 first=case['first_answer']
 if isinstance(first,dict) and first.get('file'):
  link={k:first[k] for k in ['file','pointer','question'] if k in first}
  link['role']='逐题审阅确认的首答来源（接触情况见原记录）'
  if link not in row['evidence_links']:row['evidence_links'].append(link)
p=R/'定义80题_策略执行审阅.json'
if p.exists():
 for c in read(p)['cases']:
  key=c['source_id'];row=rows[key];row.update(status=c['inventory_status'],method=c['methods'],decisive_basis=c['execution'],result=c['assessment'],reference_exposure='已接触目标参考；本轮复用旧首答及已存核验作机制审阅，不称新独立作答',issues=c['issues']);row['evidence_links'].append({'file':p.name,'question':row['question'],'role':'逐题策略机制审阅'});link_review_metadata(row,c)
for p in sorted(R.glob('*策略检验_*.json'),key=lambda path:read(path).get('saved_at','')):
 for c in read(p)['cases']:
  row=rows[c['source_id']];row.update(status=c['inventory_status'],method=c['methods'],decisive_basis=c['execution'],result=c['assessment'],reference_exposure=c.get('review_type','接触状态见该检验原记录'),issues=c['issues']);row['evidence_links'].append({'file':p.name,'question':row['question'],'role':'逐题策略机制审阅'});link_review_metadata(row,c)
cards=read(ROOT/'web/content/xingce-branches.json')
current_versions={c['id']:c.get('version') for c in cards}
for row in rows.values():
 stale=[m for m in (row['method'] or []) if current_versions.get(m['id'])!=m['version']]
 if stale:
  row['previous_review_status']=row['status'];row['status']='需要回查';row['issues']=list(row['issues'])+['已存方法版本不同于当前规则，保留原记录，完成回查前不自动继承有效性']
 row['candidate_methods']=[c['id'] for c in cards if c['category']=={'定义判断':'definition','资料分析':'data','中心句与排序':'structure','阅读理解':'reading','选词填空':'cloze','逻辑判断':'logic','类比推理':'analogy'}.get(row['category'])]
 row['candidate_method_note']='仅按已有导航提供候选，不是方法执行或效果证据'
items=sorted(rows.values(),key=lambda x:(order[x['unit_id']],x['question']))
for row in items:
 row['research_scope']='当前年份范围' if in_current_scope(row['year']) else '历史已分析成果保留' if row['method'] else '范围外未分析，停止推进'
no_definition=load_no_definition_inspections(R,cat)
for unit_id in no_definition:
 assert not any(x['unit_id']==unit_id and x['category']=='定义判断' for x in items),unit_id
summary=[]
for u in cat:
 xs=[x for x in items if x['unit_id']==u['id']];l=ledger[u['id']];summary.append({'unit_id':u['id'],'source':u['path'],'text_read_pages':l.get('text_read_pages',[]),'visual_read_pages':l.get('visual_read_pages',[]),'reading_stage':l.get('stage'),'indexed_positions':len(xs),'manual_task_positions':sum(x['actual_task'] is not None for x in xs),'states':dict(collections.Counter(x['status'] for x in xs)),'completeness':'仅索引定位和已有证据关联，不证明自动题号无遗漏；不开展版本审计'})
write(R/'逐题策略检验清单.json',{'schema':'strategy-audit/v1','saved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'policy':'抽取/标签不提升策略状态；候选关联待人工；已有首答不覆盖','items':items})
first_answer_gaps=[{'source_id':x['source_id'],'status':'已有策略审阅但原首答来源未关联，不补造','issues':x['issues']} for x in items if x['method'] and x['first_answer'] is None]
write(R/'策略检验盘点汇总.json',{'units':summary,'first_answer_gaps':first_answer_gaps,'counts':{'units':len(cat),'indexed_positions':len(items),'manual_task_positions':sum(x['actual_task'] is not None for x in items),'states':dict(collections.Counter(x['status'] for x in items))},'unresolved_links_and_locations':gaps,'cards':[{'id':c['id'],'category':c['category'],'title':c['title'],'version':c.get('version'),'note':'例题扩展保持同一方法id，语义合并须人工判断'} for c in cards]})
# Advance only after the OpenSpec task and explicit coverage evidence agree.
plan=(ROOT/'openspec/changes/read-corpus-and-build-transferable-skills/tasks.md').read_text()
definition_finished=bool(re.search(r'(?m)^- \[x\] 4\.5 ',plan))
category='资料分析' if definition_finished else '定义判断'
if definition_finished:
 audit=read(R/'定义覆盖验收.json')
 assert audit['source_units']==len(cat) and audit['reviewed_positions']==sum(x['category']=='定义判断' for x in items)
 assert not read(R/'策略回查清单.json')['pending']
 assert not any(x['category']=='定义判断' and x['status'] in ['已读待策略检验','需要回查'] for x in items)
# Follow the explicitly selected next category only after both prior category
# coverage and the completed teaching unit have evidence. Empty queues alone
# never advance the research sequence.
requested=read(R/'续接检查点.json').get('next_batch',{}).get('category')
if requested=='中心句与排序':
 assert definition_finished
 data_coverage=read(R/'资料覆盖验收.json')
 data_rows=[x for x in items if x['category']=='资料分析']
 assert data_coverage['source_units']==len(cat)==50
 assert data_coverage['reviewed_positions']==len(data_rows)
 assert all(x['status'] in ['已有策略检验','存在争议'] for x in data_rows)
 teaching=read(R/'资料教学_15分支语义与来源核对.json')
 assert len(teaching['branches'])==15 and teaching.get('deployment')
 assert {x['id'] for x in teaching['branches']}=={c['id'] for c in cards if c['category']=='data'}
 category=requested
# Already-read positions first, year descending, catalogue order.
xs=[x for x in items if x['category']==category and x['status'] in ['已读待策略检验','需要回查'] and can_schedule(x)];xs.sort(key=lambda x:(0 if x['status']=='需要回查' else 1,-x['year'],order[x['unit_id']],x['question']))
discovery=[{'unit_id':u['id'],'source':u['path'],'action':'尚无人工确认的定义位置；读取实际题型段落后登记，不能按题号猜型或把机器未定位当无题'} for u in cat if u['id'] not in no_definition and not any(x['unit_id']==u['id'] and x['category']=='定义判断' for x in items)]
discovery=[x for x in discovery if in_current_scope(units[x['unit_id']]['year'])]
discovery.sort(key=lambda x:(-units[x['unit_id']]['year'],order[x['unit_id']]))
category_source_scope=[]
no_data=load_no_data_inspections(R,cat)
if category in ['资料分析','中心句与排序']:
 for u in cat:
  unit_items=[x for x in items if x['unit_id']==u['id']]
  data_items=[x for x in unit_items if x['category']=='资料分析']
  l=ledger[u['id']]
  text_covered=set(l.get('text_read_pages',[]))==set(range(1,l['pages']+1))
  baseline_covered=(u['id']=='2026-副省级-主卷' and len(read(ROOT/'本地作答/2026副省级/核验与教学/逐题核验与教学.json'))==135)
  all_located_classified=bool(unit_items) and all(x['actual_task'] is not None for x in unit_items)
  section_check=l.get('category_scope_checks',{}).get('资料分析')
  if section_check:
   assert (R/section_check['evidence']).is_file()
   if section_check['status']=='实际检查未见资料分析':
    assert u['id'] in no_data and section_check['questions']==[] and not data_items
    assert section_check['evidence']=='资料来源无题检查.json'
    assert section_check['inspection_pages']==no_data[u['id']]['inspection_pages']
   else:
    assert section_check['status']=='实际资料段已全量处理' and section_check['questions'] and section_check['material_pages']
    assert all(any(x['question']==n and x['status'] in ['已有策略检验','存在争议'] for x in data_items) for n in section_check['questions'])
  # Route partially read sources even when every previously labelled data
  # question was reviewed. Routing never promotes reading or strategy status.
  needs_reading=not (section_check or ((text_covered or baseline_covered) and all_located_classified))
  category_source_scope.append({'unit_id':u['id'],'source':u['path'],'reviewed_source_positions':sum(x['method'] is not None for x in data_items),'known_pending_positions':sum(x['status'] in ['已读待策略检验','需要回查'] for x in data_items),'needs_actual_section_reading':needs_reading,'no_data_inspected':u['id'] in no_data,'basis':'实际模块与边界检查未见资料；不增加阅读或策略检验题数' if u['id'] in no_data else '局部阅读不证明资料段已覆盖；读取实际段落核未登记题，旧答复用' if needs_reading else '实际资料段已人工登记全量处理；其他模块不据此标已读' if section_check else '已有整卷阅读或135题基线与实际任务标签；已读资料仍按逐题证据验收'})
data_source_scope=category_source_scope
if category=='中心句与排序':
 # Task words only prioritize already-read candidates. They never set a type,
 # mark a strategy valid, or establish a shared-material boundary.
 def structure_priority(row):
  task=row['actual_task'] or ''
  return 3 if '下文' in task else 2 if '排序' in task else 1 if ('填' in task or '插入' in task) else 0
 xs.sort(key=lambda x:(structure_priority(x),0 if x['status']=='需要回查' else 1,-x['year'],order[x['unit_id']],x['question']))
 category_source_scope=[]
 for u in cat:
  actual=[x for x in items if x['unit_id']==u['id'] and x['category']==category]
  check=ledger[u['id']].get('category_scope_checks',{}).get(category)
  scope_confirmed=bool(check and check.get('status')=='实际任务范围已逐题确认' and check.get('evidence') and (R/check['evidence']).is_file())
  category_source_scope.append({'unit_id':u['id'],'source':u['path'],
   'known_positions':len(actual),'reviewed_source_positions':sum(bool(x['method']) for x in actual),
   'known_pending_positions':sum(x['status'] in ['已读待策略检验','需要回查'] for x in actual),
   'needs_actual_section_reading':not scope_confirmed,
   'basis':'已有标签不是整类完整范围；须核实际言语/篇章任务和共享材料，不以固定题号推算'})
for scope_row in category_source_scope: scope_row['in_current_scope']=in_current_scope(units[scope_row['unit_id']]['year'])
category_discovery=[dict(x,action='读取原卷实际资料段，确认题目及材料组边界；不按题号猜型，不把机器未定位当无题') for x in category_source_scope if x['needs_actual_section_reading'] and x['in_current_scope']]
category_discovery.sort(key=lambda x:(-units[x['unit_id']]['year'],order[x['unit_id']]))
stage='检验已读'+category if xs else '读取并分流尚未覆盖的资料段' if category_discovery else '资料已读队列清空，待全量范围验收' if category=='资料分析' else '读取并分流尚未登记定义的来源' if discovery else '来源分流已登记，待教学与遗留回查'
if category=='中心句与排序':
 stage='主旨分支旧题检验；共享题组先核完整材料'
 for scope_row in category_source_scope: scope_row['in_current_scope']=in_current_scope(units[scope_row['unit_id']]['year'])
 category_discovery=[dict(x,action='核实际主旨、填句、排序与篇章任务范围；查共享材料，保留其他类别') for x in category_source_scope if x['needs_actual_section_reading'] and x['in_current_scope']]
 category_discovery.sort(key=lambda x:(-units[x['unit_id']]['year'],order[x['unit_id']]))
write(R/'策略下一批.json',{'capacity':20,'category':category,'stage':stage,'question':'先检主旨/意图/描述概括/标题是否同一路径，后填句再排序；复用首答与既有修订，共享材料边界先核' if category=='中心句与排序' else '资料分析先核统计对象、口径和可求性，再选择运算；复用旧首答，不能由答案一致代替策略执行' if definition_finished else '检验当前分支是否能识别并执行规则、过程与案例任务；先复用已有首答，未读来源先分流，不能把已读队列清空视为全量完成','minimum_year_inclusive':MINIMUM_YEAR,'items':[{'source_id':x['source_id'],'pages':x['pages'],'actual_task':x['actual_task'],'evidence_links':x['evidence_links']} for x in xs[:20]],'discovery_units':discovery,'category_source_scope':category_source_scope,'data_source_scope':data_source_scope,'batch_kind':'已读候选；执行前核共享材料，题组不得拆开' if category=='中心句与排序' else '逐题检验批','category_discovery_units':category_discovery,'no_definition_inspections':[{'unit_id':u,'evidence_file':'定义来源无题检查.json','scope':r['scope']} for u,r in no_definition.items()],'completion_note':str(sum(x['category']=='中心句与排序' for x in items))+'为历史标签数量，非全量题数；后续仅推进'+str(MINIMUM_YEAR)+'年及以后，早期已完成成果保留，个人迁移另计' if category=='中心句与排序' else '已读待检验队列清空不等于资料分析全量完成；尚未覆盖资料段继续阅读分流，争议、教学、个人迁移分别验收' if category=='资料分析' else '待检题清单为空不证明50来源定义检验完成；分流、争议、知识缺口及教学/个人迁移仍分别验收','rule':'20题默认；复杂共享减10，实际原题题组不拆；未读题另排，仅推进当前年份范围，已完成早期成果保留'})
print(json.dumps({'units':len(summary),'positions':len(items),'states':dict(collections.Counter(x['status'] for x in items)),'unresolved_groups':len(gaps),'next':[x['source_id'] for x in xs[:20]]},ensure_ascii=False))

# Scope statistics do not change any existing reading or validation state.
active=[x for x in items if in_current_scope(x["year"])]
legacy=[x for x in items if not in_current_scope(x["year"])]
scope_stats={"minimum_year_inclusive":MINIMUM_YEAR,"current_units":sum(in_current_scope(u["year"]) for u in cat),"historical_units_retained":sum(not in_current_scope(u["year"]) for u in cat),"current_positions":len(active),"current_states":dict(collections.Counter(x["status"] for x in active)),"historical_reviewed_retained":sum(bool(x["method"]) for x in legacy),"historical_unreviewed_not_scheduled":sum(not x["method"] for x in legacy),"current_by_category":{k:dict(collections.Counter(x["status"] for x in active if x["category"]==k)) for k in sorted({x["category"] for x in active})}}
for name in ["策略检验盘点汇总.json","策略下一批.json"]:
 value=read(R/name);value["research_scope"]=scope_stats;write(R/name,value)
print(json.dumps({"research_scope":scope_stats},ensure_ascii=False))
