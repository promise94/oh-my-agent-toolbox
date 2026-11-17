#!/usr/bin/env python3
from __future__ import annotations
import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from core.skill_registry import load_registry,resolve_skill,UnknownSkillError

def main():
 p=argparse.ArgumentParser(); p.add_argument('--project',type=Path,required=True); p.add_argument('--registry',type=Path); p.add_argument('--source-root',type=Path); p.add_argument('--name'); a=p.parse_args()
 if a.registry and a.source_root: print('BLOCKED: --registry and --source-root are mutually exclusive'); return 2
 if a.name:
  try:
   root=a.registry or ((a.source_root/'skill-registry.json') if a.source_root and a.source_root.name == 'skills' else (a.source_root/'skills'/'skill-registry.json') if a.source_root else None); cid,_=resolve_skill(a.name,load_registry(root)); print(f'name={cid}'); print('migration=canonical'); return 0
  except (ValueError,UnknownSkillError) as e: print(f'BLOCKED: {e}'); return 2
 print(f'skills={"available" if (a.project/"skills").is_dir() else "manual"}'); print('cli=available'); print('mcp=manual'); print('review=manual'); print('audit=manual'); print('gate=manual'); return 0
if __name__=='__main__': raise SystemExit(main())
