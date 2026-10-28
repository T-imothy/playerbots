"""Exercise Classic's actual demon summon call with its actual TempSpawnSettings constructor."""
from pathlib import Path
import subprocess
import sys
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
core=root.parent/'classic'
effects=(core/'src/game/Spells/SpellEffects.cpp').read_text()
if '--before' in sys.argv:
    effects=subprocess.check_output(['git','-C',str(core),'show','HEAD:src/game/Spells/SpellEffects.cpp'],text=True)
settings=block((core/'src/game/Entities/Object.h').read_text(),'struct TempSpawnSettings')+';'
method=block(effects,'void Spell::EffectSummonDemon(')
code=r'''
#include <cassert>
#include <vector>
#include <iostream>
using uint32=unsigned;using int32=int;using SpellEffectIndex=unsigned;
struct ObjectGuid{};struct WorldObject;struct Creature;
enum TempSpawnType{TEMPSPAWN_TIMED_OR_DEAD_DESPAWN=6};
__SETTINGS__
struct Map{};
struct WorldObject{static Creature*SummonCreature(TempSpawnSettings,Map*);};
struct Creature:WorldObject{unsigned level=60;Map map;float GetOrientation(){return 1.25f;}Map*GetMap(){return &map;}
 unsigned GetLevel(){return level;}void SetLevel(unsigned value){level=value;}};
Creature summoned;std::vector<TempSpawnSettings>captured;
Creature*WorldObject::SummonCreature(TempSpawnSettings settings,Map*){captured.push_back(settings);return &summoned;}
struct SpellEntry{unsigned Id=24670,EffectMiscValue[3]={89,0,0};};
bool IsSpellSetRun(const SpellEntry*){return true;}
struct Spell{int m_currentBasePoints[3]={1,0,0};struct{struct{float x=12,y=24,z=36;}m_destPos;}m_targets;
 Creature*m_caster;SpellEntry*m_spellInfo;unsigned hooks=0;void OnSummon(Creature*){++hooks;}void EffectSummonDemon(SpellEffectIndex);};
__METHOD__
int main(){Creature caster;SpellEntry info;Spell spell;spell.m_caster=&caster;spell.m_spellInfo=&info;
 spell.EffectSummonDemon(0);assert(captured.size()==1);
 const auto&settings=captured.front();assert(settings.spawner==&caster&&settings.entry==89);
 assert(settings.spellId==24670&&!settings.forcedOnTop&&!settings.spawnCounting&&settings.modelId==0);
 assert(settings.setRun&&settings.x==12&&settings.y==24&&settings.z==36);
 assert(settings.despawnTime==3600000&&settings.spawnType==TEMPSPAWN_TIMED_OR_DEAD_DESPAWN);
 assert(spell.hooks==1&&summoned.level==caster.level);
 captured.clear();spell.m_currentBasePoints[0]=0;spell.EffectSummonDemon(0);assert(captured.empty());
 spell.m_currentBasePoints[0]=2;spell.EffectSummonDemon(0);assert(captured.size()==2);
 for(const auto&settings:captured)assert(settings.spellId==24670&&!settings.forcedOnTop);
 std::cout<<"PASS: actual Classic demon summon constructor keeps spell identity and intended spawn options\n";}
'''.replace('__SETTINGS__',settings).replace('__METHOD__',method)
with tempfile.TemporaryDirectory(prefix='mantech-native-demon-') as folder:
    temp=Path(folder);(temp/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=temp,check=True)
    subprocess.run([str(temp/'test.exe')],cwd=temp,check=True)
objects=(core/'src/game/Entities/Object.cpp').read_text()
assert 'creature->SetUInt32Value(UNIT_CREATED_BY_SPELL, settings.spellId);' in objects
