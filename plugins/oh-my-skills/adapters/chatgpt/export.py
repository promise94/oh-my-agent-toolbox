#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, shutil, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from core.skill_registry import load_registry

def roots(source, registry):
 source=source.resolve(); skills=source/'skills' if (source/'skills').is_dir() else source
 reg=registry.resolve() if registry else skills/'skill-registry.json'; return skills,reg

def portable_ids(reg): return sorted(e['id'] for e in reg.get('skills',[]) if isinstance(e,dict) and 'chatgpt' in e.get('portable_hosts',[]))
def files_to_export(source, adapter, registry_path=None):
 skills,regpath=roots(source,registry_path); ids=portable_ids(load_registry(regpath)); files={'plugin.json':adapter/'plugin.json','mcp.json':adapter/'mcp.json','marketplace.json':adapter/'marketplace.json'}
 for cid in ids:
  skill=skills/cid
  if (skill/'SKILL.md').is_file():
   for path in skill.rglob('*'):
    if path.is_file(): files[str(Path('skills')/cid/path.relative_to(skill))]=path
 return files

def main():
 p=argparse.ArgumentParser(); p.add_argument('--source-root',type=Path); p.add_argument('--registry',type=Path); p.add_argument('--target',type=Path,required=True); a=p.parse_args()
 if not a.source_root and not a.registry: p.error('one of --source-root or --registry is required')
 if a.source_root and a.registry and (a.source_root.resolve()/'skills'/'skill-registry.json').resolve()!=a.registry.resolve(): print('BLOCKED: --source-root and --registry conflict'); return 2
 source=a.source_root or a.registry.parent.parent; adapter=Path(__file__).resolve().parent
 try: files=files_to_export(source,adapter,a.registry)
 except ValueError as e: print(f'BLOCKED: {e}'); return 2
 target=a.target.resolve()
 for rel,src in files.items():
  dst=target/rel
  if dst.exists() and (not dst.is_file() or dst.read_bytes()!=src.read_bytes()): print(f'BLOCKED: target conflict: {dst}'); return 2
 target.mkdir(parents=True,exist_ok=True)
 for rel,src in files.items():
  dst=target/rel; dst.parent.mkdir(parents=True,exist_ok=True)
  if not dst.exists(): shutil.copyfile(src,dst)
 print(f'PASS: exported portable skills to {target}'); return 0
if __name__=='__main__': raise SystemExit(main())
