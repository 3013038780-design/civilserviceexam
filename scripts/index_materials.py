#!/usr/bin/env python3
"""Read-only incremental inventory. Never move sources or execute document macros."""
import argparse
import csv
import hashlib
import json
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def classify(relative):
    text = str(relative)
    if relative.parts[0] == '军队文职' or re.search(r'雅思|考研|复试|MOOD|报名照片|准考证', text, re.I):
        return '其他考试或个人资料', '暂缓'
    if re.search(r'打印|包邮|进群|资源库|每日更新记录', relative.name):
        return '广告或辅助图片', '暂缓'
    if re.search(r'数量|图推|图形推理', text):
        return '行测-数量或图推', '暂缓专项'
    if re.search(r'申论|白鹭|袁东|作文|概括|对策|公文|词句理解|综合分析|启示分析|变化分析|推荐材料|发布词|简报', text):
        module = '作文' if re.search(r'作文|范文', text) else '材料与小题'
        return '申论-' + module, '优先候选'
    if re.search(r'资料分析|【资料】|比重|增长率|增长量', text):
        return '行测-资料分析', '优先候选'
    if re.search(r'言语|阅读|选词|填空', text):
        return '行测-言语', '优先候选'
    if re.search(r'政治|常识|时政', text):
        return '政治常识', '按需核验时点'
    if re.search(r'定义|类比|逻辑|判断', text):
        return '行测-判断', '优先候选'
    if re.search(r'行测|真题', text):
        return '行测-综合或真题', '先核卷别与答案隔离'
    return '待确认', '仅凭文件名不能归类'


def scan(source, output):
    output.mkdir(parents=True, exist_ok=True)
    previous_path = output / 'inventory.json'
    old = json.loads(previous_path.read_text()).get('files', []) if previous_path.exists() else []
    previous = {x['relative_path']: x for x in old}
    rows, failures = [], []
    now = time.time()
    for p in sorted(source.rglob('*')):
        if not p.is_file() or p.name.startswith(('.', '~$')):
            continue
        try:
            before = p.stat()
            rel = p.relative_to(source)
            key = str(rel)
            category, priority = classify(rel)
            row = {'relative_path': key, 'bytes': before.st_size, 'mtime_ns': before.st_mtime_ns,
                   'format': p.suffix.lower(), 'category': category, 'priority': priority,
                   'classification_basis': '文件名/目录，未核验正文', 'sha256': '', 'state': '待稳定'}
            downloading = p.name.lower().endswith(('.downloading', '.crdownload', '.part', '.tmp'))
            if downloading:
                row['state'] = '下载中，暂不读取'
            if not downloading and now - before.st_mtime >= 15:
                prior = previous.get(key, {})
                if prior.get('bytes') == before.st_size and prior.get('mtime_ns') == before.st_mtime_ns and prior.get('sha256'):
                    row['sha256'] = prior['sha256']
                else:
                    h = hashlib.sha256()
                    with p.open('rb') as stream:
                        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                            h.update(block)
                    row['sha256'] = h.hexdigest()
                after = p.stat()
                if (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns):
                    row['state'] = '已登记，正文未读'
                else:
                    row['sha256'] = ''
            row['change'] = '新增' if key not in previous else ('未变' if previous[key].get('bytes') == row['bytes'] and previous[key].get('mtime_ns') == row['mtime_ns'] else '变更或待稳定')
            rows.append(row)
        except (OSError, ValueError) as exc:
            failures.append({'path': str(p), 'error': str(exc)})
    groups = defaultdict(list)
    for row in rows:
        if row['sha256']:
            groups[row['sha256']].append(row['relative_path'])
    duplicates = {k: v for k, v in groups.items() if len(v) > 1}
    stamp = datetime.now().astimezone().isoformat(timespec='seconds')
    result = {'scanned_at': stamp, 'source': str(source), 'files': rows, 'exact_duplicates': duplicates,
              'missing_since_previous': sorted(set(previous) - {r['relative_path'] for r in rows}), 'errors': failures}
    tmp = output / 'inventory.json.tmp'
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    tmp.replace(previous_path)
    with (output / '资料清单.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ['relative_path'])
        writer.writeheader()
        writer.writerows(rows)
    category_counts = Counter(r['category'] for r in rows)
    changes = Counter(r['change'] for r in rows)
    report = ['# 桌面国考资料接收记录', '', f'扫描时间：{stamp}', f'来源：{source}', '',
              f'共 {len(rows)} 个非隐藏文件，{sum(r["bytes"] for r in rows)/1048576:.1f} MB。',
              f'完全相同内容的重复组：{len(duplicates)}；多余副本数：{sum(len(v)-1 for v in duplicates.values())}。不删除原件。',
              f'增量：{dict(changes)}。过于近期或扫描期间变化的文件暂不视为稳定。', '',
              '仅完成文件登记与内容指纹检查，不代表正文已读。分类依据是文件名与目录，须由实际阅读核验。',
              '阅读范围另记在“首批阅读记录.md”。同一文件内容变化后旧阅读记录仅适用于旧指纹。', '',
              '| 初步分类 | 数量 |', '| --- | --- |']
    report += [f'| {k} | {v} |' for k, v in sorted(category_counts.items())]
    report += ['', '详细清单见“资料清单.csv”；稳定状态、完整指纹、重复组和扫描错误见“inventory.json”。', '',
               '上传中可重复运行索引脚本：未变文件复用指纹，只处理新增或变化文件。不会移动原件、解压未知压缩包或运行宏。',
               '这是一次次增量扫描，不是已部署的后台监控。完整清单与个人笔记仅保留本地。']
    (output / '接收概览.md').write_text('\n'.join(report) + '\n')
    print(json.dumps({'files': len(rows), 'mb': round(sum(r['bytes'] for r in rows)/1048576, 1),
                      'duplicate_groups': len(duplicates), 'duplicate_copies': sum(len(v)-1 for v in duplicates.values()),
                      'changes': changes, 'errors': len(failures), 'categories': category_counts}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if not args.source.is_dir():
        parser.error('Source directory does not exist')
    if args.source.resolve() == args.output.resolve() or args.source.resolve() in args.output.resolve().parents:
        parser.error('Output must be outside source directory')
    scan(args.source.resolve(), args.output.resolve())
