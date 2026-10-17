"""检查来源可追溯、状态与发布边界；不代替语义核查或学习效果验证。"""
from pathlib import Path
import json
from urllib.parse import urlparse
root = Path(__file__).parent
raw = (root/'dist/content.js').read_text()
data = json.loads(raw.removeprefix('window.COURSE = ').rstrip(';\n'))
assert len(data['units']) == 8
assert len(data['lines']) == 3
assert len(data['lessons']) == 1
assert sum(u['lessonId'] is None for u in data['units']) == 7
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
    assert set(lesson['case']['sourceIds']) <= ids
    assert lesson['case']['boundary'] and lesson['boundary']
    assert len(lesson['uses']) == 5
    assert '待用户迁移' in lesson['status']
    assert '原创' in lesson['memoryType']
for f in ['README.md','AGENTS.md','docs/requirements.md','docs/content-standard.md']:
    assert (root/f).is_file()
manifest = json.loads((root/'.openai/hosting.json').read_text())
assert manifest['project_id'] and manifest['static']['directory'] == 'dist'
assert not any(p.suffix.lower() in {'.pdf','.epub','.tar','.gz'} for p in (root/'dist').rglob('*'))
print(json.dumps({'units':8,'example_lessons':1,'pending_units':7,'sources':len(ids),'content_contract':'passed'},ensure_ascii=False))
