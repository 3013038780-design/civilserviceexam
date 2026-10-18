"""将已人工审阅的填句批次保存到既有证据链；不解题、不按答案相等认定有效。"""
import argparse
import collections
import datetime
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '本地资料/真题策略研究'


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def resolve(file, pointer):
    path = LOCAL / file
    value = read(path if path.exists() else ROOT / file)
    for key in pointer.strip('/').split('/'):
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def reference_section(text, question):
    # 三种既有抽取格式：方括号、题号带标点、上一行末尾附题号。
    patterns = [rf'【\s*{question}\s*】',
                rf'(?m)^\s*{question}\s*[.、．]',
                rf'(?<!\d){question}[ \t]*\n']
    for style, pattern in enumerate(patterns):
        match = re.search(pattern, text)
        if match:
            end_pattern = [r'【\s*\d{1,3}\s*】',
                           r'(?m)^\s*\d{1,3}\s*[.、．]',
                           rf'(?<!\d){question + 1}[ \t]*\n'][style]
            end = re.search(end_pattern, text[match.end():])
            section = text[match.start():match.end() + end.start() if end else len(text)]
            answer = re.search(r'(?:正确答案为|选择)\s*([ABCD])', section)
            assert answer, f'参考段未找到答案：{question}'
            return section, answer[1]
    raise ValueError(f'参考未定位到题号 {question}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('review_input', help='忽略目录内的人工审阅输入JSON')
    args = parser.parse_args()
    spec = read(LOCAL / args.review_input)
    first_path = LOCAL / spec['first_file']
    first = read(first_path)
    protection = read(LOCAL / '策略实施_新增首答保护哈希.json')
    assert protection[str(first_path.relative_to(ROOT))] == hashlib.sha256(first_path.read_bytes()).hexdigest()
    refs_path, output_path = (LOCAL / spec[key] for key in ['reference_file', 'formal_file'])
    assert not refs_path.exists() and not output_path.exists(), '拒绝覆盖已保存批次，请续接已有结果'
    manual = {row['source_id']: row for row in spec['cases']}
    assert len(manual) == len(spec['cases']) == len(first['cases'])
    assert set(manual) == {row['source_id'] for row in first['cases']}
    inventory = {row['source_id'] for row in read(LOCAL / '逐题策略检验清单.json')['items']}
    assert set(manual) <= inventory, '新来源须先登记到既有逐题清单'
    ledger = read(LOCAL / '阅读账本.json')
    assert {row['unit_id'] for row in first['cases']} <= {row['id'] for row in ledger['rows']}
    cards = {row['id']: row for row in read(ROOT / 'web/content/xingce-branches.json')}
    minimum_year = read(ROOT / 'research-scope.json')['minimum_year_inclusive']
    refs, cases, cached = [], [], {}
    for index, old in enumerate(first['cases']):
        row = manual[old['source_id']]
        assert int(old['source_id'][:4]) >= minimum_year
        assert old['method']['version'] == cards[old['method']['id']]['version']
        assert row['status'] in ['已有策略检验', '存在争议']
        assert row['actual_task'] and row['assessment'] and row['addendum']
        assert isinstance(row['issues'], list) and (row['status'] != '存在争议' or row['issues'])
        assert row['working_answer'] in 'ABCD' and len(row['working_answer']) == 1
        origin = old.get('origin')
        if origin:
            value = resolve(origin['file'], origin['pointer'])
            answer = value['answer'] if isinstance(value, dict) else value
            assert answer == origin['answer']
            if isinstance(value, dict) and value.get('source_id'):
                assert value['source_id'] == origin['source_id']
            mapping = old.get('choice_mapping')
            if mapping:
                assert mapping['old_letter'] == answer and mapping['current_letter'] == old['answer']
            else:
                assert answer == old['answer']
        source = row['reference_source']
        if source not in cached:
            cached[source] = (LOCAL / source).read_text()
        q = row.get('reference_question', old['question'])
        text, original_answer = reference_section(cached[source], q)
        answer = row.get('reference_choice_mapping', {}).get(original_answer, original_answer)
        refs.append(dict(source_id=old['source_id'], answer=answer,
                         original_answer=original_answer, source_file=source,
                         section=str(q), text=text,
                         choice_mapping=row.get('reference_choice_mapping')))
        link = dict(file=spec['first_file'], pointer=f'/cases/{index}',
                    answer=old['answer'], status=old['first_mode'],
                    origin=origin, reused_from=old.get('reused_from'))
        if old.get('choice_mapping'):
            link['choice_mapping'] = old['choice_mapping']
        cases.append(dict(source_id=old['source_id'], actual_task=row['actual_task'],
                          methods=[old['method']], first_answer=link,
                          reference=answer,
                          reference_evidence=dict(file=spec['reference_file'], pointer=f'/cases/{index}'),
                          working_answer=row['working_answer'],
                          letter_match=old['answer'] == answer,
                          execution=old['basis'] + ' 核验补充：' + row['addendum'],
                          inventory_status=row['status'], assessment=row['assessment'],
                          issues=row['issues'],
                          review_type=old['reference_exposure'] + ' 冻结后核验目标参考；状态由人工执行判断提供。',
                          visual_pages=old['visual_pages'], text_pages=old['text_pages'],
                          duplicate_of=old.get('reused_from'), rule_changed=False))
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    write(refs_path, dict(saved_at=now, first_answer_file=spec['first_file'],
                         first_answer_sha256=hashlib.sha256(first_path.read_bytes()).hexdigest(),
                         count=len(refs), cases=refs))
    write(output_path, dict(saved_at=now, category='中心句与排序', count=len(cases),
                           scope=spec['scope'], methods_changed=False, cases=cases))
    for unit in {row['unit_id'] for row in first['cases']}:
        group = [row for row in first['cases'] if row['unit_id'] == unit]
        entry = next(row for row in ledger['rows'] if row['id'] == unit)
        entry.setdefault('partial_type_batches', []).append(dict(
            batch=spec['batch'],
            text_pages=sorted({p for row in group for p in row['text_pages']}),
            visual_pages=sorted({p for row in group for p in row['visual_pages']}),
            questions=[row['question'] for row in group],
            shared_material_groups=[row['material_questions'] for row in group if len(row['material_questions']) > 1],
            evidence=spec['formal_file'], note=spec['reading_note']))
    write(LOCAL / '阅读账本.json', ledger)
    queue = read(LOCAL / '题型优先研究队列.json')
    for row in queue['items']:
        if row['source_id'] in manual:
            row.update(actual_task=manual[row['source_id']]['actual_task'],
                       classification_basis=spec['batch'] + '原题及材料人工检查')
    queue['saved_at'] = now
    write(LOCAL / '题型优先研究队列.json', queue)
    print(json.dumps(dict(saved=len(cases),
                          states=dict(collections.Counter(c['inventory_status'] for c in cases)),
                          reference_matches=sum(c['letter_match'] for c in cases),
                          judgment_source='人工输入，非答案相等自动晋升'), ensure_ascii=False))


if __name__ == '__main__':
    main()
