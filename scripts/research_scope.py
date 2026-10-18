"""Shared year boundary for future work; historical evidence is never deleted."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / 'research-scope.json').read_text())
MINIMUM_YEAR = POLICY['minimum_year_inclusive']
assert isinstance(MINIMUM_YEAR, int)


def in_current_scope(year):
    return year >= MINIMUM_YEAR


def can_schedule(item):
    return in_current_scope(item['year']) or (
        POLICY['allow_existing_record_dependency_rechecks']
        and item.get('status') == '需要回查'
        and bool(item.get('method'))
    )
