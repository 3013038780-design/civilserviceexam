"""Check provenance/state boundaries and diagram references, without re-solving questions."""
from pathlib import Path
import collections,hashlib,json
from definition_source_checks import load_no_definition_inspections
from data_source_checks import load_no_data_inspections
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'本地资料/真题策略研究'
def read(p):return json.loads(p.read_text())
for name in ['策略实施_首答保护哈希.json','策略实施_新增首答保护哈希.json']:
 manifest=R/name
 if manifest.exists():
  for path,digest in read(manifest).items():
   assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
cat=read(R/'主版本阅读目录.json');inventory=read(R/'逐题策略检验清单.json')['items'];summary=read(R/'策略检验盘点汇总.json');reviews=read(R/'定义80题_策略执行审阅.json')['cases'];cards=read(ROOT/'web/content/xingce-branches.json');by={c['id']:c for c in cards}
assert len(cat)==len(summary['units'])==50
assert cards and len(by)==len(cards)
assert len(inventory)==len({x['source_id'] for x in inventory})
assert {x['source_id'] for x in summary['first_answer_gaps']}=={x['source_id'] for x in inventory if x['method'] and x['first_answer'] is None}
assert len(reviews)==len({x['source_id'] for x in reviews})==80
reviewed={x['source_id'] for x in reviews}
latest_reviews={x['source_id']:x for x in reviews}
for p in R.glob('*策略检验_*.json'):reviewed.update(x['source_id'] for x in read(p)['cases'])
for p in sorted(R.glob('*策略检验_*.json'),key=lambda path:read(path).get('saved_at','')):
 for case in read(p)['cases']:
  revision=case.get('classification_revision')
  if revision:
   prior=next(x for x in read(R/revision['prior_evidence'])['cases'] if x['source_id']==case['source_id'])
   assert revision['from_methods']==prior['methods']
   for field in ['actual_task','first_answer','reference','working_answer','letter_match','execution','inventory_status','issues']:
    assert case.get(field)==prior.get(field),(case['source_id'],field)
  latest_reviews[case['source_id']]=case
for x in inventory:
 if x['status'] in ['已有策略检验','存在争议']:
  assert x['source_id'] in reviewed and x['method'] and x['decisive_basis']
  assert all(m['id'] in by and by[m['id']]['version']==m['version'] for m in x['method'])
  case=latest_reviews[x['source_id']]
  if case.get('actual_task'):
   assert x['actual_task']==case['actual_task'] and x['classification_status']=='逐题策略审阅确认实际任务',x['source_id']
  if 'first_answer' in case:
   assert x['first_answer']==case['first_answer'],x['source_id']
   if x['first_answer']:
    link=x['first_answer'];assert (R/link['file']).is_file() or (ROOT/link['file']).is_file(),link
    assert any(e['file']==link['file'] and e['role'].startswith('逐题审阅确认') for e in x['evidence_links'])
 if x['reading'].startswith('定位自抽取'):assert x['status']=='尚未阅读' and not x['method']
for c in cards:
 version=hashlib.sha256(json.dumps({k:c[k] for k in ['signal','steps','stop','boundary']},sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:12]
 assert c['version']==version
 t=c.get('teaching')
 if not t:continue
 assert all(id in by for id in t.get('related_methods',[]))
 ids={x['id'] for x in t['flow']};assert len(ids)==len(t['flow'])
 for node in t['flow']:
  assert node['question'] and node['choices']
  for edge in node['choices']:
   assert edge['to'] in ids or edge['to'] in ['完成','相对选择；复核保留争议','相对选择；保留竞争','转比重变化分支','转部分数量分支','转构成图或图表定位分支','转趋势图或构成图分支']
   if edge['to']=='转趋势图或构成图分支':
    assert {'trend-chart','composition-chart'}<=set(t.get('related_methods',[]))
    assert all(by[id]['category']==c['category'] for id in ['trend-chart','composition-chart'])
   if edge['to']=='转构成图或图表定位分支':
    assert {'composition-chart','chart-reading'}<=set(t.get('related_methods',[]))
    assert all(by[id]['category']==c['category'] for id in ['composition-chart','chart-reading'])
 for ex in [t['success'],t['failure']]:
  assert all(s['node'] in ids and s['text'] for s in ex['steps'])
  if ex.get('source_id'):
   example=next(x for x in inventory if x['source_id']==ex['source_id'])
   assert any(m['id']==c['id'] for m in (example['method'] or [])),(c['id'],ex['source_id'])
   assert ex is not t['success'] or example['status']=='已有策略检验'
  if ex.get('authored'):assert not ex.get('source_id')
audit_by={x['source_id']:x for x in inventory}
for x in reviews:
 for m in x['methods']:
  if m['version']!=by[m['id']]['version']:assert audit_by[x['source_id']]['status']=='需要回查' or all(by[z['id']]['version']==z['version'] for z in audit_by[x['source_id']]['method'])

practice=read(R/'定义样板_试用入口.json')
next_batch=read(R/'策略下一批.json')
no_definition=load_no_definition_inspections(R,cat)
for unit_id in no_definition:
 assert not any(x['unit_id']==unit_id and x['category']=='定义判断' for x in inventory),unit_id
assert {u['unit_id'] for u in next_batch.get('no_definition_inspections',[])}==set(no_definition)
expected_discovery={u['id'] for u in cat if u['id'] not in no_definition and not any(x['unit_id']==u['id'] and x['category']=='定义判断' for x in inventory)}
assert {u['unit_id'] for u in next_batch['discovery_units']}==expected_discovery
if next_batch.get('category')=='定义判断' and not next_batch['items'] and expected_discovery:
 assert next_batch['stage']=='读取并分流尚未登记定义的来源'
if next_batch.get('category')=='定义判断' and not next_batch['items'] and not expected_discovery:
 assert next_batch['stage']=='来源分流已登记，待教学与遗留回查'
if next_batch.get('category') in ['资料分析','中心句与排序']:
 scope=next_batch.get('data_source_scope',next_batch['category_source_scope'])
 no_data=load_no_data_inspections(R,cat)
 assert {x['unit_id'] for x in scope if x.get('no_data_inspected')}==set(no_data)
 for uid in no_data:
  assert not any(x['unit_id']==uid and x['category']=='资料分析' for x in inventory)
  row=next(x for x in read(R/'阅读账本.json')['rows'] if x['id']==uid)
  check=row['category_scope_checks']['资料分析']
  assert check['status']=='实际检查未见资料分析' and check['questions']==[]
  assert not next(x for x in scope if x['unit_id']==uid)['needs_actual_section_reading']
 assert len(scope)==len(cat) and {x['unit_id'] for x in scope}=={x['id'] for x in cat}
 pending_sections=next_batch['category_discovery_units'] if next_batch['category']=='资料分析' else [x for x in scope if x['needs_actual_section_reading']]
 assert {x['unit_id'] for x in pending_sections}=={x['unit_id'] for x in scope if x['needs_actual_section_reading']}
 if next_batch['category']=='资料分析' and not next_batch['items']:
  assert next_batch['stage']==('读取并分流尚未覆盖的资料段' if pending_sections else '资料已读队列清空，待全量范围验收')
 audit=read(R/'定义覆盖验收.json')
 assert audit['source_units']==50 and audit['reviewed_positions']==sum(audit_by[sid]['category']=='定义判断' for sid in reviewed)
 assert not read(R/'策略回查清单.json')['pending']
 assert all(audit_by[x['source_id']]['category']==next_batch['category'] for x in next_batch['items'])
if next_batch.get('category')=='中心句与排序':
 scope=next_batch['category_source_scope']
 assert len(scope)==50 and {x['unit_id'] for x in scope}=={x['id'] for x in cat}
 assert next_batch['batch_kind']=='已读候选；执行前核共享材料，题组不得拆开'
 assert all(audit_by[x['source_id']]['category']=='中心句与排序' for x in next_batch['items'])
 assert {x['unit_id'] for x in next_batch['category_discovery_units']}=={x['unit_id'] for x in scope if x['needs_actual_section_reading']}
data_audit_path=R/'资料覆盖验收.json'
if data_audit_path.exists():
 data_audit=read(data_audit_path)
 data_items=[x for x in inventory if x['category']=='资料分析']
 assert data_audit['source_units']==len(cat)==50
 assert data_audit['reviewed_positions']==len(data_items)
 assert data_audit['states']==dict(collections.Counter(x['status'] for x in data_items))
 assert all(x['status'] in ['已有策略检验','存在争议'] and x['method'] and x['decisive_basis'] for x in data_items)
 assert set(data_audit['first_answer_source_gaps'])=={x['source_id'] for x in data_items if x['first_answer'] is None}
 assert data_audit['recheck_pending']==read(R/'策略回查清单.json')['pending']==[]
 assert {x['unit_id'] for x in data_audit['units']}=={x['id'] for x in cat}
 no_data_checked=load_no_data_inspections(R,cat)
 assert data_audit['no_data_units']==len(no_data_checked)
 assert data_audit['data_units']==len(cat)-len(no_data_checked)
 for row in data_audit['units']:
  actual=[x for x in data_items if x['unit_id']==row['unit_id']]
  assert row['actual_questions']==sorted(x['question'] for x in actual)
  assert row['states']==dict(collections.Counter(x['status'] for x in actual))
  assert row['method_versions']==sorted({m['id']+':'+m['version'] for x in actual for m in x['method']})
  assert row['no_data_inspected']==(row['unit_id'] in no_data_checked)
  assert bool(actual)!=row['no_data_inspected']
 if next_batch.get('category')=='资料分析':
  assert not next_batch['items'] and not next_batch['category_discovery_units']

data_practice_path=R/'资料分支_试用入口.json'
if data_practice_path.exists():
 import base64
 data_practice=read(data_practice_path);practice_review=read(R/'资料分支_试用核验.json')
 crops={x['source_id']:x for x in read(R/'资料分支_试用裁片来源.json')['cases']}
 assert not set(data_practice)&set(practice)
 data_practice={**data_practice,**practice}
 definition_review=read(R/'定义分支_试用核验.json')
 assert not set(practice_review)&set(definition_review)
 practice_review={**practice_review,**definition_review}
 crops.update({x['source_id']:x for x in read(R/'定义分支_试用裁片来源.json')['cases']})
 legacy=read(R/'定义试用_旧六题保护.json')
 assert len(legacy)==6
 assert set(legacy)<={q['source_id'] for g in practice.values() for q in g['questions']}
 for method,group in data_practice.items():
  assert by[method].get('teaching') and group['mode']=='guided-transfer/v1' and 3<=len(group['questions'])<=5
  assert len({q['source_id'] for q in group['questions']})==len(group['questions'])
  assert {q['source_id'] for q in group['questions']}==set(practice_review[method])
  for q in group['questions']:
   answer=practice_review[method][q['source_id']]
   if q['source_id'].startswith('authored:'):
    from fractions import Fraction
    assert set(q)=={'source_id','label','pages','questionText','hint'} and q['pages']==[]
    proof=read(R/'自拟迁移题_核验依据.json')[q['source_id']]
    assert proof['kind']==answer['kind']=='self-authored'
    assert proof['answer']==answer['answer'] and proof['questionText']==q['questionText'] and proof['execution']==answer['execution']
    assert answer['proof_id']==q['source_id'] and q['source_id'] not in audit_by
    if proof.get('proof_type')=='mixed-current':
     a,b,total_rate=(Fraction(proof['givens'][k]) for k in ['a','b','R'])
     w=Fraction(proof['base_share']);v=Fraction(proof['current_share'])
     assert a!=b and 0<w<1 and 1+total_rate>0
     assert total_rate==w*a+(1-w)*b and v==w*(1+a)/(1+total_rate)==Fraction(1,5)
     assert proof['answer']=='A'
    elif proof.get('proof_type')=='mixed-equal':
     rate=Fraction(proof['rate']);shares=set()
     for model in proof['models']:
      a,b,A,B=(Fraction(model[k]) for k in ['base_a','base_b','current_a','current_b'])
      assert a>0 and b>0 and A==a*(1+rate) and B==b*(1+rate)
      assert (A+B)/(a+b)-1==rate
      shares.add(A/(A+B))
     assert len(shares)>1 and proof['answer']=='D'
    elif proof.get('proof_type')=='part-direction':
     g={k:Fraction(v) for k,v in proof['givens'].items()}
     assert g['T1']*g['s1']-g['T0']*g['s0']==Fraction(proof['delta'])==25 and proof['answer']=='C'
    elif proof.get('proof_type')=='part-inverse':
     g={k:Fraction(v) for k,v in proof['givens'].items()}
     assert g['part_ratio']*g['s0']/g['s1']-1==Fraction(proof['growth'])==Fraction(4,5) and proof['answer']=='B'
    elif proof.get('proof_type')=='annual-unequal':
     a,b=proof['givens'];t=1+Fraction(proof['threshold'])
     assert Fraction(a['ratio'])<t**a['n'] and Fraction(b['ratio'])>t**b['n'] and proof['answer']=='B'
    elif proof.get('proof_type')=='annual-mean':
     rates=list(map(Fraction,proof['rates']));multiplier=Fraction(1)
     for rate in rates:multiplier*=1+rate
     assert sum(rates)/len(rates)==Fraction(proof['arithmetic'])==0
     assert multiplier==Fraction(proof['compound_multiplier'])<1 and proof['answer']=='A'
    elif 'exact_fraction' in proof:
     value=Fraction(proof['givens']['T_over_B'])/Fraction(proof['givens']['T_over_A'])-1
     assert proof['target']=='A/B−1' and str(value)==proof['exact_fraction']=='-1/6'
    else:
     assert proof['target']=='B/A' and len(proof['models'])>=2
     models=proof['models']
     assert all(Fraction(m['T1'],m['A'])==Fraction(6,5) and Fraction(m['T2'],m['B'])==Fraction(3,2) for m in models)
     assert len({Fraction(m['B'],m['A']) for m in models})>1 and proof['answer']=='D'
    continue
   assert set(q)=={'source_id','label','pages','image','hint'}
   original=audit_by[q['source_id']]
   assert original['status']=='已有策略检验' and method in {m['id'] for m in original['method']}
   expected_answer=latest_reviews[q['source_id']].get('working_answer',original['first_answer']['answer'])
   assert answer['answer']==expected_answer and answer['execution']==original['decisive_basis']
   assert answer['review_id']=='review-'+hashlib.sha256(q['source_id'].encode()).hexdigest()[:14]
   raw=base64.b64decode(q['image'].split(',',1)[1]);crop=crops[q['source_id']]
   assert hashlib.sha256(raw).hexdigest()==crop['jpeg_sha256'] and len(raw)==crop['image_bytes']
   if crop.get('origin')=='existing-private-practice':
    assert q['source_id'] in legacy and q['pages']==legacy[q['source_id']]['pages']==crop['pages']
    assert crop['jpeg_sha256']==legacy[q['source_id']]['jpeg_sha256']
   else:
    assert q['pages']==sorted({r['page'] for r in crop['regions']})

assert set(practice)=={'definition-conditions','definition-relations','given-rules','procedure','visual-description'}
for group in practice.values():
 assert len(group['questions'])==3
 assert group['mode']=='guided-transfer/v1' and all(set(q)=={'source_id','label','pages','image','hint'} and q['image'].startswith('data:image/jpeg;base64,') for q in group['questions'])
print(json.dumps({'units':50,'indexed_positions':len(inventory),'reviewed_definition_positions':sum(audit_by[sid]['category']=='定义判断' for sid in reviewed),'reviewed_by_category':dict(collections.Counter(audit_by[sid]['category'] for sid in reviewed)),'old80_assessment':dict(collections.Counter(x['assessment'] for x in reviews)),'review_states':dict(collections.Counter(x['status'] for x in inventory if x['method'])),'visual_branches':sum('teaching' in c for c in cards),'auto_read_or_validation_promotion':False},ensure_ascii=False))
