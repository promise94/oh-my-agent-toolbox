#!/usr/bin/env python3
from __future__ import annotations
import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.skill_registry import load_registry,resolve_skill,UnknownSkillError

def main():
 p=argparse.ArgumentParser(); p.add_argument('--name',required=True); p.add_argument('--registry',type=Path); a=p.parse_args()
 try: cid,alias=resolve_skill(a.name,load_registry(a.registry))
 except (UnknownSkillError,ValueError) as e: print(f'BLOCKED: unknown or invalid skill: {e}',file=sys.stderr); return 2
 print(cid); return 0
if __name__=='__main__': raise SystemExit(main())
