from __future__ import annotations
import json
from pathlib import Path
class UnknownSkillError(ValueError): pass

def default_registry_path() -> Path:
    return Path(__file__).resolve().parents[1] / 'skills' / 'skill-registry.json'
def load_registry(path=None):
    p=Path(path) if path else default_registry_path()
    try: data=json.loads(p.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError) as exc: raise ValueError(f'invalid skill registry: {exc}') from exc
    if not isinstance(data,dict) or not isinstance(data.get('skills'),list): raise ValueError('invalid skill registry: skills must be a list')
    return data
def canonical_ids(registry): return [e['id'] for e in registry.get('skills',[]) if isinstance(e,dict) and isinstance(e.get('id'),str)]
def alias_map(registry):
    return {}

def resolve_skill(name, registry):
    if name in set(canonical_ids(registry)):
        return name, False
    raise UnknownSkillError(name)
