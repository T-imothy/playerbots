"""Actual Majordomo damage admission: tank threat, reserved sheep, and native reflection."""
from pathlib import Path
import ast,subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
tree=ast.parse((root/'tests/encounter_damage_pause_regression.py').read_text())
code=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and '#include <cassert>' in n.value).split('__METHODS__')[0]
code=code.replace('SPELL_AURA_PERIODIC_HEAL=8,','SPELL_AURA_MOD_FEAR=7,SPELL_AURA_PERIODIC_HEAL=8,')
code+='\nnamespace ai { bool BlackwingSuppressionMovementActive(BotAI*){return false;} }\n'
source=(root/'playerbot/strategy/actions/EncounterDamagePolicy.cpp').read_text()
code+='\n'.join(block(source,s) for s in ('bool ai::HasMajordomoDamageShield(', 'bool ai::HasEncounterDamagePause(', 'bool ai::HasEncounterThreatPause(', 'bool ai::HasEncounterSpellBomb(', 'bool ai::HasEncounterWeaponPause(', 'bool ai::ShouldAvoidEncounterOffense(', 'bool ai::HasUnsafeEncounterOffense(', 'bool ai::StopUnsafeEncounterOffense('))
code+=r'''
int main(){BotAI brain;Player tank;tank.ai=&brain;Unit add;add.entry=11664;add.auras.insert(21075);tank.map=add.map=409;tank.victim=&add;tank.melee=true;
SpellEntry damage,heal;damage.DmgClass=SPELL_DAMAGE_CLASS_MELEE;heal.positive=true;
assert(ai::HasMajordomoDamageShield(&tank,&add));assert(ai::ShouldAvoidEncounterOffense(&tank,&tank,&damage,&add));
brain.tank=true;
#ifdef MANGOSBOT_ZERO
assert(!ai::HasMajordomoDamageShield(&tank,&add));assert(!ai::ShouldAvoidEncounterOffense(&tank,&tank,&damage,&add));assert(!ai::HasUnsafeEncounterOffense(&tank));
#else
assert(ai::HasMajordomoDamageShield(&tank,&add));
#endif
brain.tank=false;damage.DmgClass=SPELL_DAMAGE_CLASS_MAGIC;add.auras.clear();add.reflection=50;
assert(ai::ShouldAvoidEncounterOffense(&tank,&tank,&damage,&add));add.reflection=0;
ai::reserved=true;assert(ai::ShouldAvoidEncounterOffense(&tank,&tank,&damage,&add));assert(!ai::ShouldAvoidEncounterOffense(&tank,&tank,&heal,&tank));
assert(ai::HasUnsafeEncounterOffense(&tank));assert(ai::StopUnsafeEncounterOffense(&tank,&tank)&&!tank.melee);
ai::reserved=false;assert(!ai::ShouldAvoidEncounterOffense(&tank,&tank,&damage,&add));
std::cout<<"PASS: tank threat through native damage shield, DPS shield pause, sheep protection and magic reflection\n";}
'''
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='majordomo-shield-') as d:
  p=Path(d);(p/'test.cpp').write_text(code)
  result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
  if result.returncode:raise RuntimeError(result.stdout+result.stderr)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
