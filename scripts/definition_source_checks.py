"""Validate explicit no-definition source inspections; absence is never inferred."""
import hashlib
import json
from pathlib import Path


def validate_inspection(record, unit, research_dir):
    assert record['unit_id'] == unit['id']
    assert record['decision'] == '实际任务检查后未发现定义判断'
    assert record['scope'] == '任务分流检查，不等于整卷作答或完整阅读'
    assert record['definition_positions'] == []
    assert record['source_sha256'] == hashlib.sha256(
        Path(unit['path']).read_bytes()).hexdigest()
    extracted = research_dir / '抽取' / unit['id'] / 'pages.json'
    assert record['extraction_sha256'] == hashlib.sha256(extracted.read_bytes()).hexdigest()
    page_count = len(json.loads(extracted.read_text()))
    questions = record['questions']
    assert len(questions) == record['question_count'] > 0
    assert {q['question'] for q in questions} == set(range(1, record['question_count'] + 1))
    assert len({q['question'] for q in questions}) == len(questions)
    for q in questions:
        assert q['actual_task'] and q['category'] and q['category'] != '定义判断'
        assert q['basis'] and q['opening']
        assert q['pages'] and all(1 <= p <= page_count for p in q['pages'])
    assert record['boundary_reviews'] and record['classification_basis']
    return record


def load_no_definition_inspections(research_dir, catalogue):
    path = research_dir / '定义来源无题检查.json'
    if not path.exists():
        return {}
    units = {u['id']: u for u in catalogue}
    result = {}
    for record in json.loads(path.read_text())['records']:
        unit_id = record['unit_id']
        assert unit_id not in result and unit_id in units
        result[unit_id] = validate_inspection(record, units[unit_id], research_dir)
    return result
