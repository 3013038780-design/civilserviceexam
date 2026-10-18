"""Check provenance/state boundaries and diagram references, without re-solving questions."""
from pathlib import Path
import collections,hashlib,json
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'本地资料/真题策略研究'
def read(p):return json.loads(p.read_text())
cat=read(R/'主版本阅读目录.json');inventory=read(R/'逐题策略检验清单.json')['items'];summary=read(R/'策略检验盘点汇总.json');reviews=read(R/'定义80题_策略执行审阅.json')['cases'];cards=read(ROOT/'web/content/xingce-branches.json');by={c['id']:c for c in cards}
assert len(cat)==len(summary['units'])==50
assert len(by)==len(cards)==26
assert len(inventory)==len({x['source_id'] for x in inventory})
assert len(reviews)==len({x['source_id'] for x in reviews})==80
reviewed={x['source_id'] for x in reviews}
for p in R.glob('定义策略检验_*.json'):reviewed.update(x['source_id'] for x in read(p)['cases'])
for x in inventory:
 if x['status'] in ['已有策略检验','存在争议']:
  assert x['source_id'] in reviewed and x['method'] and x['decisive_basis']
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
  if m['version']!=by[m['id']]['version']:assert audit_by[x['source_id']]['status']=='需要回查'

practice=read(R/'定义样板_试用入口.json')
assert set(practice)=={'definition-conditions','definition-relations'}
for group in practice.values():
 assert len(group['questions'])==3
 assert all(set(q)=={'source_id','label','pages','image'} and q['image'].startswith('data:image/jpeg;base64,') for q in group['questions'])
print(json.dumps({'units':50,'indexed_positions':len(inventory),'reviewed_definition_positions':80,'assessment':dict(collections.Counter(x['assessment'] for x in reviews)),'visual_branches':sum('teaching' in c for c in cards),'auto_read_or_validation_promotion':False},ensure_ascii=False))
