"""Read-only batch handoff: surface old answers AND corrections before solving.

Only known first-answer/correction records are opened. Target-reference files are
excluded; output is a locator, not an assertion of reading or strategy validity.
"""
from pathlib import Path
import argparse
import json

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '本地资料/真题策略研究'
def read(path):
    return json.loads(path.read_text())

batch = read(LOCAL / '策略下一批.json')
items = batch.get('items', [])
catalog = {x['id']: x for x in read(LOCAL / '主版本阅读目录.json')}
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--unit', help='Inspect one catalog unit in the current category instead of the next batch')
args = parser.parse_args()
if args.unit:
    if args.unit not in catalog:
        parser.error('Unknown catalog unit')
    items = [x for x in read(LOCAL / '逐题策略检验清单.json')['items']
             if x['unit_id'] == args.unit and x['category'] == batch.get('category')]
source_records = {}
for item in items:
    unit, question = item['source_id'].rsplit(':', 1)
    if unit not in source_records:
        info = catalog[unit]
        prefix = str(info['year']) + info['kind']
        candidates = sorted(LOCAL.glob(prefix + '*候选方法首答.json'))
        candidates += sorted(LOCAL.glob(prefix + '*核验与修订.json'))
        source_records[unit] = [(p, read(p)) for p in candidates]
    old_answers, corrections = [], []
    for path, record in source_records[unit]:
        if not isinstance(record, dict):
            continue
        for key in ['answers', 'after_image_before_target_reference']:
            answers = record.get(key, {})
            if isinstance(answers, dict) and question in answers:
                old_answers.append({'answer': answers[question], 'file': path.name,
                                    'pointer': '/' + key + '/' + question})
        for index, change in enumerate(record.get('corrections', [])):
            if str(change.get('q')) == question:
                corrections.append({'file': path.name, 'pointer': '/corrections/' + str(index),
                                    'record': change})
    print(json.dumps({'source_id': item['source_id'], 'actual_task': item.get('actual_task'),
                      'old_first_candidates': old_answers, 'known_corrections': corrections,
                      'scope': '仅本卷明确文件；同题跨卷仍须核题面关联，不凭空缺声称没有旧答'},
                     ensure_ascii=False))
