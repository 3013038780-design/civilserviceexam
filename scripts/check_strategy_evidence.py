"""Check provenance/state boundaries and diagram references, without re-solving questions."""
from pathlib import Path
import collections,hashlib,json
from definition_source_checks import load_no_definition_inspections
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'本地资料/真题策略研究'
def read(p):return json.loads(p.read_text())
for name in ['策略实施_首答保护哈希.json','策略实施_新增首答保护哈希.json']:
 manifest=R/name
 if manifest.exists():
  for path,digest in read(manifest).items():
   assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
cat=read(R/'主版本阅读目录.json');inventory=read(R/'逐题策略检验清单.json')['items'];summary=read(R/'策略检验盘点汇总.json');reviews=read(R/'定义80题_策略执行审阅.json')['cases'];cards=read(ROOT/'web/content/xingce-branches.json');by={c['id']:c for c in cards}
assert len(cat)==len(summary['units'])==50
assert len(by)==len(cards)==26
assert len(inventory)==len({x['source_id'] for x in inventory})
assert len(reviews)==len({x['source_id'] for x in reviews})==80
reviewed={x['source_id'] for x in reviews}
latest_reviews={x['source_id']:x for x in reviews}
for p in R.glob('定义策略检验_*.json'):reviewed.update(x['source_id'] for x in read(p)['cases'])
for p in sorted(R.glob('定义策略检验_*.json'),key=lambda path:read(path).get('saved_at','')):
 for case in read(p)['cases']:latest_reviews[case['source_id']]=case
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
 ids={x['id'] for x in t['flow']};assert len(ids)==len(t['flow'])
 for node in t['flow']:
  assert node['question'] and node['choices']
  for edge in node['choices']:assert edge['to'] in ids or edge['to'] in ['完成','相对选择；复核保留争议','相对选择；保留竞争']
 for ex in [t['success'],t['failure']]:
  assert all(s['node'] in ids and s['text'] for s in ex['steps'])
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
if not next_batch['items'] and expected_discovery:
 assert next_batch['stage']=='读取并分流尚未登记定义的来源'
if not next_batch['items'] and not expected_discovery:
 assert next_batch['stage']=='来源分流已登记，待教学与遗留回查'
assert set(practice)=={'definition-conditions','definition-relations'}
for group in practice.values():
 assert len(group['questions'])==3
 assert all(set(q)=={'source_id','label','pages','image'} and q['image'].startswith('data:image/jpeg;base64,') for q in group['questions'])
print(json.dumps({'units':50,'indexed_positions':len(inventory),'reviewed_definition_positions':len(reviewed),'old80_assessment':dict(collections.Counter(x['assessment'] for x in reviews)),'review_states':dict(collections.Counter(x['status'] for x in inventory if x['method'])),'visual_branches':sum('teaching' in c for c in cards),'auto_read_or_validation_promotion':False},ensure_ascii=False))
