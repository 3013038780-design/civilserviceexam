"""Prepare local reading copies of existing main papers; extraction is NOT reading.
No source files are moved, compared for authenticity, or published.
"""
from pathlib import Path
from pypdf import PdfReader
import argparse,json,re,hashlib,logging
logging.getLogger('pypdf').setLevel(logging.ERROR)
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('/Users/olivialee/Desktop/国考/已分类资料/02_下载资料/行测/真题')
OUT=ROOT/'本地资料/真题策略研究'
def choose():
 rows=[]
 for y in sorted(SOURCE.iterdir()):
  if not y.name.isdigit():continue
  for d in sorted(y.glob('*/题面候选')):
   fs=sorted(d.glob('*.pdf'),key=lambda p:('__' in p.name,'【' in p.name,'录用考试《行测》题（' not in p.name,len(p.name),p.name))
   if not fs:continue
   # Old A/B and I/II are distinct papers, not duplicate editions.
   groups={}
   for p in fs:
    m=re.search(r'(?:[（(]?([AB])卷[）)]?|卷[（(]([一二])[）)])',p.name)
    variant=(m[1] or m[2]) if m else '主卷'
    groups.setdefault(variant,p)
   for v,p in groups.items():
    rows.append(dict(id=f'{y.name}-{d.parent.name}-{v}',year=int(y.name),kind=d.parent.name,variant=v,path=str(p)))
 return rows

def main():
 a=argparse.ArgumentParser();a.add_argument('--years',nargs='*',type=int);args=a.parse_args();OUT.mkdir(parents=True,exist_ok=True)
 manifest=choose();(OUT/'主版本阅读目录.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
 for row in manifest:
  if args.years and row['year'] not in args.years:continue
  dest=OUT/'抽取'/row['id'];dest.mkdir(parents=True,exist_ok=True)
  source=Path(row['path']);stamp=dict(size=source.stat().st_size,mtime_ns=source.stat().st_mtime_ns)
  meta=dest/'抽取状态.json'
  previous=json.loads(meta.read_text()) if meta.exists() else {}
  if previous.get('source_stat')==stamp and previous.get('parser_revision')==2:continue
  if previous.get('source_stat')==stamp and (dest/'pages.json').exists():
   pages=json.loads((dest/'pages.json').read_text())
  else:
   pages=[p.extract_text() or '' for p in PdfReader(source).pages]
  (dest/'pages.json').write_text(json.dumps(pages,ensure_ascii=False))
  text='\n'.join(f'\n[PDF页 {i+1}]\n{t}' for i,t in enumerate(pages))
  (dest/'全文.txt').write_text(text)
  # Layout may place question number on its own line; retain text in full for manual reading.
  anchors=[]
  for i,t in enumerate(pages):
   for m in re.finditer(r'(?m)(?<![\d.])(\d{1,3})[.．](?!\d)',t):
    n=int(m[1])
    if 1<=n<=150:anchors.append(dict(n=n,page=i+1,offset=m.start()))
  status={**row,'source_stat':stamp,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'pages':len(pages),'text_characters':sum(map(len,pages)),'anchors':anchors,'parser_revision':2,'anchor_note':'仅为题号候选；实际题号、页码与语义分类需阅读确认','stage':'全文已抽取，尚未据此标记已读','image_note':'图形、表格与公式须另做视觉核对；文字抽取不能证明已读图表'}
  meta.write_text(json.dumps(status,ensure_ascii=False,indent=2));print(row['id'],len(pages),len(text),flush=True)
 print('Prepared main-paper reading copies; no comprehension status automatically advanced.',flush=True)
if __name__=='__main__':main()
