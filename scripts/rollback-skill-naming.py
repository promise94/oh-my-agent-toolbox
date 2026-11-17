#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, hashlib, json, os, shutil
from pathlib import Path

def state(root,p):
    q=root/p; kind='missing' if not os.path.lexists(q) else ('symlink' if q.is_symlink() else 'dir' if q.is_dir() else 'file'); out={'kind':kind}
    if kind=='file': out['sha256']=hashlib.sha256(q.read_bytes()).hexdigest()
    elif kind=='symlink': out['symlink_target']=os.readlink(q)
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',type=Path,required=True); ap.add_argument('--snapshot',type=Path,required=True); ap.add_argument('--post',type=Path,required=True); mode=ap.add_mutually_exclusive_group(required=True); mode.add_argument('--check-only',action='store_true'); mode.add_argument('--apply',action='store_true'); a=ap.parse_args(); root=a.root.resolve(); pre=json.loads(a.snapshot.read_text()); post=json.loads(a.post.read_text())
    conflicts=[]
    for item in post['paths']:
        rel=item['path']; now=state(root,rel); expected={'kind':item['kind']};
        if item['kind']=='file': expected['sha256']=item.get('sha256')
        if item['kind']=='symlink': expected['symlink_target']=item.get('symlink_target')
        if now!=expected: conflicts.append(rel)
    if conflicts:
        print('BLOCKED: current files differ from post-image: '+', '.join(conflicts)); return 2
    if a.check_only: print('PASS: rollback check-only has no conflicts'); return 0
    for item in pre['paths']:
        rel=item['path']; q=root/rel; q.parent.mkdir(parents=True,exist_ok=True); k=item['kind']
        if os.path.lexists(q): shutil.rmtree(q) if q.is_dir() and not q.is_symlink() else q.unlink()
        if k=='missing': continue
        if k=='dir': q.mkdir(parents=True,exist_ok=True)
        elif k=='symlink': q.symlink_to(item['symlink_target'])
        elif k=='file': q.write_bytes(base64.b64decode(item['content_b64'])); os.chmod(q,int(item.get('mode','0o644'),8))
    print('PASS: restored pre-image'); return 0
if __name__=='__main__': raise SystemExit(main())
