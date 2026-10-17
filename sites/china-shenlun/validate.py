"""检查来源可追溯、状态与发布边界；不代替语义核查或学习效果验证。"""
from pathlib import Path
import json
from urllib.parse import urlparse
root = Path(__file__).parent
raw = (root/'dist/content.js').read_text()
data = json.loads(raw.removeprefix('window.COURSE = ').rstrip(';\n'))
assert len(data['units']) == 8
assert len(data['lines']) == 3
assert len(data['lessons']) == 8
assert all(u['lessonId'] for u in data['units'])
required = {'id','title','publisher','url','eventDate','publishedAt','checkedAt','locator','readScope','kind','applicability','reviewScope'}
ids = set()
for s in data['sources']:
    assert required <= s.keys() and all(s[k] for k in required)
    assert s['id'] not in ids
    ids.add(s['id'])
    host = urlparse(s['url']).hostname
    assert s['url'].startswith('https://')
    assert host == 'www.12371.cn' or host.endswith('.gov.cn')
for lesson in data['lessons']:
    assert set(lesson['sourceIds']) <= ids
    assert len(lesson['uses']) == 5
    assert '待用户迁移' in lesson['status']
    assert lesson['manuscript'] == (root/'manuscripts'/lesson['file']).read_text()
    assert len(lesson['manuscript']) > 1500
    for heading in ['核心知识讲解','案例及机制','从知识到申论写法','最小记忆与独立输出']:
        assert '## '+heading in lesson['manuscript']
    assert (root/'dist/downloads'/lesson['file'].replace('.md','.docx')).is_file()
for f in ['README.md','AGENTS.md','docs/requirements.md','docs/content-standard.md']:
    assert (root/f).is_file()
manifest = json.loads((root/'.openai/hosting.json').read_text())
assert manifest['project_id'] and manifest['static']['directory'] == 'dist'
assert not any(p.suffix.lower() in {'.pdf','.epub','.tar','.gz'} for p in (root/'dist').rglob('*'))
print(json.dumps({'units':8,'full_manuscripts':8,'pending_units':0,'sources':len(ids),'content_contract':'passed'},ensure_ascii=False))

assert {c for l in data['lessons'] for c in l['chapters']} == set(range(1,20))
assert next(l for l in data['lessons'] if l['unit']==2)['id'] == 'leadership-in-action'
