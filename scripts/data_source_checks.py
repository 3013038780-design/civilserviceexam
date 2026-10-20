"""Require explicit source-bound evidence before accepting a zero-data section."""
import hashlib
import json
from pathlib import Path


def load_no_data_inspections(research_dir, catalogue):
    path = research_dir / '资料来源无题检查.json'
    if not path.exists():
        return {}
    units = {unit['id']: unit for unit in catalogue}
    result = {}
    for record in json.loads(path.read_text())['records']:
        uid = record['unit_id']
        assert uid in units and uid not in result
        unit = units[uid]
        assert record['decision'] == '实际任务范围检查后未发现资料分析'
        assert record['scope'] == '模块与边界任务分流检查，不等于整卷作答或完整阅读'
        assert record['data_positions'] == []
        assert record['source_sha256'] == hashlib.sha256(Path(unit['path']).read_bytes()).hexdigest()
        extracted = research_dir / '抽取' / uid / 'pages.json'
        assert record['extraction_sha256'] == hashlib.sha256(extracted.read_bytes()).hexdigest()
        page_count = len(json.loads(extracted.read_text()))
        assert record['inspection_pages'] == list(range(1, page_count + 1))
        assert record['sections'] and record['boundary_reviews'] and record['classification_basis']
        numbers = []
        for section in record['sections']:
            first, last = section['questions']
            assert 1 <= first <= last
            assert section['category'] and section['category'] != '资料分析'
            assert section['pages'] and all(1 <= page <= page_count for page in section['pages'])
            numbers.extend(range(first, last + 1))
        assert numbers == list(range(1, max(numbers) + 1))
        for image in [record['visual_overview'], *record['detail_images']]:
            assert (research_dir / image).is_file()
        for review in record['boundary_reviews']:
            assert review['actual_task'] and review['basis']
        result[uid] = record
    return result
