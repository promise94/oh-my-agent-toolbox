from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
PLUGIN = ROOT / 'plugins' / 'oh-my-skills'
VALIDATOR = ROOT / 'scripts' / 'validate-skills.py'
CANONICAL = {
    'planning-workflow', 'plan-review', 'plan-audit',
    'code-review',
}
OLD_NAMES = {
    'plan-standard', 'codex-plan-review', 'codex-plan-audit',
    'code-review-gitlab', 'fe-rules', 'xkills-bot-mr-review',
}

class SkillNamingTests(unittest.TestCase):
    def test_registry_contains_only_canonical_ids_without_aliases(self):
        data=json.loads((PLUGIN/'skills/skill-registry.json').read_text())
        entries=data['skills']
        self.assertEqual({x['id'] for x in entries}, CANONICAL)
        self.assertTrue(all('aliases' not in x for x in entries))
        self.assertEqual({p.parent.name for p in (PLUGIN/'skills').glob('*/SKILL.md')}, CANONICAL)
        self.assertEqual(next(x for x in entries if x['id']=='planning-workflow')['version'], '2.0.0')

    def test_old_names_are_unknown(self):
        for name in OLD_NAMES:
            result=subprocess.run([sys.executable,str(PLUGIN/'scripts/resolve-skill.py'),'--name',name],capture_output=True,text=True)
            self.assertEqual(result.returncode,2,name)
            self.assertEqual(result.stdout,'',name)

    def test_canonical_names_resolve(self):
        for name in CANONICAL:
            result=subprocess.run([sys.executable,str(PLUGIN/'scripts/resolve-skill.py'),'--name',name],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,name)
            self.assertEqual(result.stdout.strip(),name)
            self.assertEqual(result.stderr,'',name)

    def test_validator_rejects_alias_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); skills=root/'plugins/oh-my-skills/skills'; (skills/'planning-workflow').mkdir(parents=True)
            (skills/'planning-workflow'/'SKILL.md').write_text('---\nname: planning-workflow\ndescription: x\n---\n')
            (skills/'skill-registry.json').write_text(json.dumps({'schema_version':1,'skills':[{'id':'planning-workflow','version':'2.0.0','hosts':['claude'],'dependencies':[],'allow_implicit_invocation':True}]})+'\n')
            (skills/'planning-workflow'/'SKILL.md').write_text('---\nname: planning-workflow\ndescription: x\nalias_for: old\n---\n')
            result=subprocess.run([sys.executable,str(VALIDATOR),'--root',str(root),'--registry',str(skills/'skill-registry.json')],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertIn('aliases are not supported',result.stdout)

    def test_fixture_root_and_registry_are_supported(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); skills=root/'plugins/oh-my-skills/skills'; skills.mkdir(parents=True)
            (skills/'skill-registry.json').write_text(json.dumps({'schema_version':1,'skills':[]})+'\n')
            result=subprocess.run([sys.executable,str(VALIDATOR),'--root',str(root),'--registry',str(skills/'skill-registry.json')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout)

if __name__ == '__main__': unittest.main()
