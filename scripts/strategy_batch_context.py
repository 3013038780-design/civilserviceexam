"""Read-only batch handoff: surface old answers AND corrections before solving.

Only known first-answer/correction records are opened. Target-reference files are
excluded; output is a locator, not an assertion of reading or strategy validity.
"""
from pathlib import Path
import argparse
import json
from research_scope import can_schedule, MINIMUM_YEAR

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '本地资料/真题策略研究'
def read(path):
    return json.loads(path.read_text())

batch = read(LOCAL / '策略下一批.json')
items = batch.get('items', [])
catalog = {x['id']: x for x in read(LOCAL / '主版本阅读目录.json')}
inventory = read(LOCAL / '逐题策略检验清单.json')['items']
by_id = {x['source_id']: x for x in inventory}
queue_source = '策略下一批.json'
category = batch.get('category')
teaching = read(LOCAL / '续接检查点.json').get('next_batch', {}) if (LOCAL / '续接检查点.json').exists() else {}
if not items or teaching.get('use_explicit_questions'):
    ids = teaching.get('questions', [])
    if teaching.get('use_explicit_questions') and not ids:
        raise ValueError('Explicit checkpoint batch has no source IDs')
    missing = [sid for sid in ids if sid not in by_id]
    if missing:
        raise ValueError('Checkpoint source IDs not found: ' + ', '.join(missing))
    items = [by_id[sid] for sid in ids]
    category = teaching.get('category', category)
    queue_source = '续接检查点.json/next_batch/questions'

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--unit', help='Inspect one catalog unit in the current category instead of the next batch')
args = parser.parse_args()
if args.unit:
    if args.unit not in catalog:
        parser.error('Unknown catalog unit')
    items = [x for x in inventory
             if x['unit_id'] == args.unit and x['category'] == category]
    queue_source = '--unit'
rejected=[x['source_id'] for x in items if not can_schedule(x)]
if rejected:
    raise ValueError('续接题单超出当前年份范围（'+str(MINIMUM_YEAR)+'年起）：'+', '.join(rejected))
print(json.dumps({'queue_source': queue_source, 'category': category, 'items': len(items)}, ensure_ascii=False))
source_records = {}
linked_review_cache = {}
for item in items:
    unit, question = item['source_id'].rsplit(':', 1)
    if unit not in source_records:
        info = catalog[unit]
        prefix = str(info['year']) + info['kind']
        if info['kind'] == '旧卷别或卷别待确认' and info['variant'] == '主卷':
            prefix = str(info['year']) + '主卷'
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
    indexed = by_id.get(item['source_id'], {})
    # Mixed-category batches may not start with a year in their filename.
    # Follow only indexed, already-saved review/correction links, never a new
    # target-reference file, and surface the exact note without inventing a
    # working answer from its wording.
    if indexed.get('first_answer'):
        for link in indexed.get('evidence_links', []):
            if link.get('role') != '核验候选' or '核验与修订' not in link['file']:
                continue
            path = LOCAL / link['file']
            if not path.exists():
                path = ROOT / link['file']
            if path not in linked_review_cache:
                linked_review_cache[path] = read(path)
            value = linked_review_cache[path]
            for token in link['pointer'].strip('/').split('/'):
                value = value[int(token)] if isinstance(value, list) else value[token]
            if not isinstance(value, dict) or value.get('unit_id') != unit or str(value.get('question')) != question:
                continue
            if value.get('review_note') or value.get('review'):
                correction = {'file': link['file'], 'pointer': link['pointer'], 'record': value}
                if correction not in corrections:
                    corrections.append(correction)
    known = {}
    if indexed.get('status') in ['已有策略检验', '存在争议', '需要回查']:
        links = [x for x in indexed.get('evidence_links', []) if x.get('role') == '逐题策略机制审阅']
        if links:
            path = LOCAL / links[-1]['file']
            record = next(x for x in read(path)['cases'] if x['source_id'] == item['source_id'])
            first = record.get('first_answer')
            known = {'first_answer': first, 'working_answer': record.get('working_answer', first.get('answer') if isinstance(first, dict) else None),
                     'issues': record.get('issues', []), 'file': path.name,
                     'reference_exposure': record.get('review_type', indexed.get('reference_exposure'))}
    # Existing baseline teaching has a frozen first answer and a later working
    # answer even before a versioned strategy review is linked. Surface both.
    first = indexed.get('first_answer') or {}
    if not known and first.get('file','').endswith('逐题核验与教学.json'):
        path = ROOT / first['file']
        index = int(first['pointer'].lstrip('/'))
        baseline = read(path)[index]
        assert baseline['题号'] == int(question)
        assert baseline['首答'] == first['answer']
        known = {'first_answer': first, 'working_answer': baseline['本轮工作答案'],
                 'issues': [baseline['边界与迁移提醒']], 'file': first['file'],
                 'reference_exposure': '复用已经保存的基线教学与核验；不是新首答或未接触参考'}
    print(json.dumps({'source_id': item['source_id'], 'actual_task': indexed.get('actual_task', item.get('actual_task')),
                      'indexed_first_answer': indexed.get('first_answer'), 'known_review': known,
                      'old_first_candidates': old_answers, 'known_corrections': corrections,
                      'scope': '已有记录定位及历史接触状态，不代表本轮新盲测；同题跨卷仍须核题面，缺首答保留'},
                     ensure_ascii=False))
