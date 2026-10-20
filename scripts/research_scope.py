"""Shared year and active-category boundaries; historical evidence is never deleted."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / 'research-scope.json').read_text())
MINIMUM_YEAR = POLICY['minimum_year_inclusive']
assert isinstance(MINIMUM_YEAR, int)


def in_current_scope(year):
    return year >= MINIMUM_YEAR


def can_schedule(item):
    active = POLICY.get('active_categories')
    if active is not None and item.get('category', item.get('queue_category')) not in active:
        return False
    return in_current_scope(item['year']) or (
        POLICY['allow_existing_record_dependency_rechecks']
        and item.get('status') == '需要回查'
        and bool(item.get('method'))
    )
