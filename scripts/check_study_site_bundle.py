"""Verify private build provenance and immutable first answers; copy validated output to the private checkout."""
import base64,copy,hashlib,json,re,shutil
from pathlib import Path
r=Path('本地作答/学习网站');p=r/'preview';b=json.loads((r/'公考学习资料包.json').read_text());old=Path('本地资料/网站发布/dist/index.html').read_text();ob=json.loads(re.search(r'<script id="study-bundle" type="application/json">(.*?)</script>',old,re.S)[1]);assert len(b['xingce'])==len(ob['xingce'])==135
def restore_paper_images(payload,folder):
 restored=copy.deepcopy(payload)
 def restore(value):
  if value.startswith('data:'):return value
  assert re.fullmatch(r'paper-images/[a-f0-9]{24}\.jpg',value),value
  raw=(folder/value).read_bytes()
  assert hashlib.sha256(raw).hexdigest()[:24]==Path(value).stem
  return 'data:image/jpeg;base64,'+base64.b64encode(raw).decode()
 restored['paper']['pages']=[restore(value) for value in restored['paper']['pages']]
 for question in restored['xingce']:
  for field in ['questionImage','contextImage']:
   if question.get(field):question[field]=restore(question[field])
 return restored
# Compare immutable records after restoring storage representation only.
ob=restore_paper_images(ob,Path('本地资料/网站发布/dist'))
changes=[]
for new,previous in zip(b['xingce'],ob['xingce']):
 assert new['题号']==previous['题号'] and new['首答']==previous['首答'] and new['机构参考']==previous['机构参考']
 if new!=previous:
  assert new['题号']==96
  fields={k for k in new if new.get(k)!=previous.get(k)}
  assert fields <= {'教学路径','停止条件'}
  if '停止条件' in fields:
   assert previous['停止条件']=='一个符合定义的反例足以否定由定义推出该大小关系。'
   assert new['停止条件']=='口径核对后，D的回报程度与通常大小关系缺少题内依据；与其余项比较后相对选择D并保留边界，不能凭一个反例就停止。'
  changes.append(96)

pages={};cases=None
for f in sorted(p.glob('strategy-evidence-*.js'),key=lambda f:int(f.stem.split('-')[-1])):
 t=f.read_text()
 if t.startswith('window.STUDY_STRATEGY_EVIDENCE='): cases=json.loads(t.split('=',1)[1].split(';\n',1)[0])['cases']
 q=json.loads(t.split('Object.assign(window.STUDY_STRATEGY_EVIDENCE.pages,',1)[1].rsplit(');',1)[0]);assert not pages.keys()&q.keys();pages.update(q)
# Byte equality proves externalizing does not recompress or drop original pages.
import base64
assert pages.keys()==b['strategyEvidence']['pages'].keys() and cases==b['strategyEvidence']['cases']
for key,page in pages.items():
 original=b['strategyEvidence']['pages'][key]
 assert page['label']==original['label'] and re.fullmatch(r'strategy-pages/[a-f0-9]{24}\.jpg',page['image'])
 assert (p/page['image']).read_bytes()==base64.b64decode(original['image'].split(',',1)[1])
assert all(k in pages for v in cases.values() for k in v)

# Hosted practice assets must preserve every original field and image byte.
hosted=json.loads(re.search(r'<script id="study-bundle" type="application/json">(.*?)</script>',(p/'index.html').read_text(),re.S)[1])
restored_paper=restore_paper_images(hosted,p)
assert restored_paper['xingce']==b['xingce'] and restored_paper['paper']==b['paper']
assert len(hosted['paper']['pages'])==26
# The portable edition keeps embedded images and the same complete bundle.
portable_html=(r/'公考解题研习室.html').read_text()
portable=json.loads(re.search(r'<script id="study-bundle" type="application/json">(.*?)</script>',portable_html,re.S)[1])
assert portable==b and all(value.startswith('data:image/') for value in portable['paper']['pages'])
del portable_html,portable
print(json.dumps({'paper_pages':26,'question_crops':sum(bool(q.get('questionImage')) for q in hosted['xingce']),'shared_context_crops':len({q['contextImage'] for q in hosted['xingce'] if q.get('contextImage')}),'all_paper_bytes_preserved':True}))
restored=copy.deepcopy(hosted.get('strategyPractice',{}));hosted_practice_assets=set()
for key,group in restored.items():
 original_group=b['strategyPractice'][key]
 for q,original in zip(group['questions'],original_group['questions']):
  if not original.get('image'):continue
  name=q['image'];assert re.fullmatch(r'practice-images/[a-f0-9]{24}\.(jpg|png|webp)',name)
  raw=base64.b64decode(original['image'].split(',',1)[1]);assert (p/name).read_bytes()==raw
  assert Path(name).stem==hashlib.sha256(raw).hexdigest()[:24]
  q['image']=original['image'];hosted_practice_assets.add(name)
assert restored==b.get('strategyPractice',{})
assert hosted.get('strategyPracticeReview')==b.get('strategyPracticeReview')
print(json.dumps({'external_practice_images':len(hosted_practice_assets),'original_bytes_preserved':True}))
branches=json.loads(Path('web/content/xingce-branches.json').read_text());assert branches and len(branches)==len({x['id'] for x in branches})
assert all(f.stat().st_size<25*1024*1024 for f in p.rglob('*') if f.is_file())
dest=Path('本地资料/网站发布/dist')
for f in dest.glob('strategy-evidence-*.js'):
 if not (p/f.name).exists():f.unlink()
shutil.copytree(p,dest,dirs_exist_ok=True)
for dirname in ['paper-images','practice-images','strategy-pages']:
 if (dest/dirname).exists():
  for file in (dest/dirname).iterdir():
   if file.is_file() and not (p/dirname/file.name).exists():file.unlink()
print(json.dumps({'cards':len(branches),'pages':len(pages),'chunks':len(list(p.glob('strategy-evidence-*.js'))),'original135_first_answers_unchanged':True,'teaching_corrections':changes,'references_closed':True,'all_files_under_25MiB':True},ensure_ascii=False))

# Cross-year review records must match the actual inventory, including disputes.
import hashlib
inventory=json.loads(Path('本地资料/真题策略研究/逐题策略检验清单.json').read_text())['items']
expected={x['source_id']:x for x in inventory if x['status'] in ['已有策略检验','存在争议'] and x['category'] in ['定义判断','资料分析']}
examples=b['crossYearExamples'];assert len(examples)==len({x['id'] for x in examples})==len(expected)
assert {x['source_id'] for x in examples}==expected.keys()
catalog={x['id']:x for x in json.loads(Path('本地资料/真题策略研究/主版本阅读目录.json').read_text())}
for x in examples:
 old=expected[x['source_id']];assert x['execution']==old['decisive_basis'] and x['status']==old['status'] and x['methods']==old['method']
 assert x['year']==old['year'] and re.fullmatch(r'cross-year-papers/[a-f0-9]{16}\.pdf',x['paper'])
 source=Path(catalog[old['unit_id']]['path']);assert hashlib.sha256((p/x['paper']).read_bytes()).digest()==hashlib.sha256(source.read_bytes()).digest()
 page_count=len(json.loads((Path('本地资料/真题策略研究/抽取')/old['unit_id']/'pages.json').read_text()))
 assert all(1<=page<=page_count for page in x['pages'])
 assert (dest/x['paper']).exists()
public=(p/'public-data.js').read_text();assert 'crossYearExamples' not in public and 'cross-year-papers/' not in public
assert '看它怎样用于2026真题' not in (p/'app.js').read_text()
print(json.dumps({'cross_year_records':len(examples),'disputes_preserved':sum(x['status']=='存在争议' for x in examples),'years':sorted({x['year'] for x in examples}),'original_pdfs':len({x['paper'] for x in examples}),'private_public_boundary':True},ensure_ascii=False))
notes=json.loads(public.split('=',1)[1].rstrip(';\n'))['crossYearNotes']
url_year_case=next(x for x in notes if x['title'].startswith('2003B85'))
assert url_year_case['year']==2003 and 2016 not in url_year_case['years']
assert all(any(x['category']==category for x in notes) for category in ['cloze','structure','reading','logic','analogy'])

original_images=set()
for x in examples:
 assert [v['page'] for v in x['pageImages']]==x['pages'] and x['pageImages']
 for image in x['pageImages']:
  assert image['image']==f"cross-year-pages/{Path(x['paper']).stem}-{image['page']}.jpg"
  assert (p/image['image']).is_file() and (dest/image['image']).is_file()
  original_images.add(image['image'])
from PIL import Image
for name in original_images:
 with Image.open(p/name) as im:assert im.format=='JPEG' and max(im.size)==2000
assert 'cross-year-pages/' not in public
# Practice questions carry only original crops and optional hints; answers live
# in a separate private section and are not rendered until explicitly opened.
if 'strategyPracticeReview' in b:
 assert 'strategyPracticeReview' not in public and 'guided-transfer/v1' not in public
 guided={key:value for key,value in b['strategyPractice'].items() if value.get('mode')=='guided-transfer/v1'}
 expected_practice=json.loads(Path('本地资料/真题策略研究/资料分支_试用入口.json').read_text())
 assert guided==expected_practice
 assert b['strategyPracticeReview']==json.loads(Path('本地资料/真题策略研究/资料分支_试用核验.json').read_text())
 assert all('answer' not in q and 'execution' not in q for group in guided.values() for q in group['questions'])
print(json.dumps({'lazy_original_images':len(original_images),'every_review_has_original_pages':True},ensure_ascii=False))

assert sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) < 250*1024*1024, "Expanded static assets leave too little archive headroom"
