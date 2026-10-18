"""Verify private build provenance and immutable first answers; copy validated output to the private checkout."""
import json,re,shutil
from pathlib import Path
r=Path('本地作答/学习网站');p=r/'preview';b=json.loads((r/'公考学习资料包.json').read_text());old=Path('本地资料/网站发布/dist/index.html').read_text();ob=json.loads(re.search(r'<script id="study-bundle" type="application/json">(.*?)</script>',old,re.S)[1]);assert len(b['xingce'])==len(ob['xingce'])==135
changes=[]
for new,previous in zip(b['xingce'],ob['xingce']):
 assert new['题号']==previous['题号'] and new['首答']==previous['首答'] and new['机构参考']==previous['机构参考']
 if new!=previous:
  assert new['题号']==96 and {k for k in new if new.get(k)!=previous.get(k)}=={'教学路径'}
  changes.append(96)

pages={};cases=None
for f in sorted(p.glob('strategy-evidence-*.js'),key=lambda f:int(f.stem.split('-')[-1])):
 t=f.read_text()
 if t.startswith('window.STUDY_STRATEGY_EVIDENCE='): cases=json.loads(t.split('=',1)[1].split(';\n',1)[0])['cases']
 q=json.loads(t.split('Object.assign(window.STUDY_STRATEGY_EVIDENCE.pages,',1)[1].rsplit(');',1)[0]);assert not pages.keys()&q.keys();pages.update(q)
assert pages==b['strategyEvidence']['pages'] and cases==b['strategyEvidence']['cases'];assert all(k in pages for v in cases.values() for k in v)
branches=json.loads(Path('web/content/xingce-branches.json').read_text());assert len(branches)==len({x['id'] for x in branches})==26
assert all(f.stat().st_size<25*1024*1024 for f in p.rglob('*') if f.is_file())
dest=Path('本地资料/网站发布/dist')
for f in dest.glob('strategy-evidence-*.js'):
 if not (p/f.name).exists():f.unlink()
shutil.copytree(p,dest,dirs_exist_ok=True)
print(json.dumps({'cards':len(branches),'pages':len(pages),'chunks':len(list(p.glob('strategy-evidence-*.js'))),'original135_first_answers_unchanged':True,'teaching_corrections':changes,'references_closed':True,'all_files_under_25MiB':True},ensure_ascii=False))
