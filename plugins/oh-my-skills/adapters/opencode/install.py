#!/usr/bin/env python3
from __future__ import annotations
import argparse, shutil, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from core.skill_registry import load_registry, canonical_ids

def resolve_paths(source_root, registry):
    source_root=source_root.resolve()
    if (source_root/'skills').is_dir(): skills=source_root/'skills'
    elif source_root.name=='skills': skills=source_root
    else: skills=source_root/'skills'
    reg=Path(registry).resolve() if registry else skills/'skill-registry.json'
    return skills,reg

def main():
    p=argparse.ArgumentParser(); p.add_argument('--source-root',type=Path); p.add_argument('--registry',type=Path); p.add_argument('--target',type=Path,required=True); p.add_argument('--force',action='store_true'); a=p.parse_args()
    if not a.source_root and not a.registry: p.error('one of --source-root or --registry is required')
    if a.source_root and a.registry and (a.source_root.resolve()/'skills'/'skill-registry.json').resolve()!=a.registry.resolve(): print('BLOCKED: --source-root and --registry conflict'); return 2
    skills,reg=resolve_paths(a.source_root or a.registry.parent.parent, a.registry)
    try: ids=canonical_ids(load_registry(reg))
    except ValueError as e: print(f'BLOCKED: {e}'); return 2
    dest=a.target.resolve()/'.opencode'/'skills'
    if dest.exists() and any(dest.iterdir()) and not a.force: print(f'BLOCKED: target exists; pass --force to replace: {dest}'); return 2
    if dest.exists(): shutil.rmtree(dest)
    dest.mkdir(parents=True,exist_ok=True)
    for cid in sorted(ids):
        src=skills/cid
        if (src/'SKILL.md').is_file(): shutil.copytree(src,dest/cid)
    print(f'PASS: copied OpenCode skills to {dest}'); return 0
if __name__=='__main__': raise SystemExit(main())
