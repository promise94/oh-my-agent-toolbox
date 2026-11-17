#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, hashlib, json, os, subprocess
from pathlib import Path

def sha(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def kind(p: Path):
    if not os.path.lexists(p): return 'missing'
    if p.is_symlink(): return 'symlink'
    if p.is_dir(): return 'dir'
    return 'file'
def record(root: Path, rel: str):
    p=root/rel; k=kind(p); item={'path':rel,'kind':k,'exists':k!='missing'}
    if k=='missing': return item
    item['mode']=oct(p.lstat().st_mode & 0o7777)
    if k=='symlink': item['symlink_target']=os.readlink(p)
    elif k=='file':
        data=p.read_bytes(); item['sha256']=sha(data); encoded=base64.b64encode(data).decode(); item['content']=encoded; item['blob']=sha(data); item['content_b64']=encoded
    return item

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',type=Path,required=True); ap.add_argument('--map',type=Path,required=False); ap.add_argument('--affected-files',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--post',action='store_true'); a=ap.parse_args()
    root=a.root.resolve(); rels=[x.strip() for x in a.affected_files.read_text().splitlines() if x.strip() and not x.startswith('#')]
    if len(rels)!=len(set(rels)): raise SystemExit('duplicate affected path')
    for rel in rels:
        if rel.startswith('/') or rel.startswith('.git/') or rel in {str(a.output.relative_to(root)) if a.output.is_absolute() and root in a.output.parents else str(a.output), str(a.affected_files)}: raise SystemExit(f'invalid affected path: {rel}')
    try: commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    except Exception: commit='unknown'
    map_sha=None
    if a.map:
        map_sha=sha(a.map.read_bytes())
    out={'schema_version':1,'kind':'post' if a.post else 'pre','root':str(root),'baseline_commit':commit,'map_sha256':map_sha,'paths':[record(root,r) for r in rels]}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(f"PASS: wrote {'post' if a.post else 'pre'} snapshot for {len(rels)} paths to {a.output}")
if __name__=='__main__': main()
