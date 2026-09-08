"""Execute Colossus/Elemental rejected transition and buff actions."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
source=(root/'mangos-wotlk-behavior/src/game/AI/ScriptDevAI/scripts/northrend/gundrak/boss_colossus.cpp').read_text()
colossus=source[source.index('struct boss_drakkari_colossusAI'):]
elemental=source[source.index('struct boss_drakkari_elementalAI'):]
code=r'''
#include <cassert>
#include <set>
#include <iostream>
using uint32=unsigned;
enum{CAST_OK=0,CAST_FAIL=1,CAST_INTERRUPT_PREVIOUS=2,CAST_TRIGGERED=4,UNIT_FIELD_FLAGS=0,
 UNIT_FLAG_UNINTERACTIBLE=1,UNIT_FLAG_IMMUNE_TO_PLAYER=2,UNIT_FLAG_STUNNED=4};
__ENUMS__
struct Motion{unsigned idles=0;void MoveIdle(){++idles;}};
struct Creature{float health=49;bool frozen=false;unsigned flags=0;Motion motion;
 float GetHealthPercent(){return health;}bool HasAura(unsigned){return frozen;}
 Motion*GetMotionMaster(){return &motion;}void SetFlag(unsigned,unsigned v){flags|=v;}};
struct Base{Creature*m_creature;bool m_isRegularMode=true,movement=true;unsigned result=CAST_OK,casts=0,lastSpell=0;
 std::set<unsigned>disabled;unsigned DoCastSpellIfCan(Creature*,unsigned spell,unsigned=0){++casts;lastSpell=spell;return result;}
 void DisableCombatAction(unsigned action){disabled.insert(action);}void SetCombatMovement(bool v){movement=v;}};
struct Colossus:Base{bool m_firstEmerge=true;__EMERGE__ __COLOSSUS__};
struct Elemental:Base{__ELEMENTAL__};
int main(){
 Creature creature;Colossus boss;boss.m_creature=&creature;boss.result=CAST_FAIL;
 boss.ExecuteAction(COLOSSUS_EMERGE);assert(!boss.disabled.count(COLOSSUS_EMERGE)&&boss.movement&&!creature.flags&&!creature.motion.idles);
 boss.result=CAST_OK;boss.ExecuteAction(COLOSSUS_EMERGE);assert(boss.disabled.count(COLOSSUS_EMERGE)&&!boss.movement&&creature.flags==7&&creature.motion.idles==1);
 creature.frozen=true;unsigned casts=boss.casts;assert(boss.DoEmergeElemental()&&boss.casts==casts);creature.frozen=false;
 Elemental add;add.m_creature=&creature;add.result=CAST_FAIL;add.ExecuteAction(ELEMENTAL_MERGE);assert(add.disabled.empty());
 add.result=CAST_OK;add.ExecuteAction(ELEMENTAL_MERGE);assert(add.disabled.count(ELEMENTAL_MERGE));
 creature.health=51;casts=add.casts;add.ExecuteAction(ELEMENTAL_MERGE);assert(add.casts==casts);
 for(bool regular:{true,false}){
  boss.disabled.clear();boss.m_isRegularMode=regular;boss.result=CAST_FAIL;boss.ExecuteAction(COLOSSUS_MORTAL_STRIKES);
  assert(boss.disabled.empty());boss.result=CAST_OK;boss.ExecuteAction(COLOSSUS_MORTAL_STRIKES);
  assert(boss.disabled.count(COLOSSUS_MORTAL_STRIKES)&&boss.lastSpell==(regular?SPELL_MORTAL_STRIKES:SPELL_MORTAL_STRIKES_H));
 }
 std::cout<<"PASS: Colossus rejected emerge/merge, existing frozen guard and normal/heroic buff retry\n";
}
'''.replace('__ENUMS__',';\n'.join(block(source,s) for s in ('enum\n','enum ElementalActions','enum ColossusActions'))+';')
code=code.replace('__EMERGE__',block(colossus,'    bool DoEmergeElemental()'))
code=code.replace('__COLOSSUS__',block(colossus,'    void ExecuteAction(').replace(' override',''))
code=code.replace('__ELEMENTAL__',block(elemental,'    void ExecuteAction(').replace(' override',''))
with tempfile.TemporaryDirectory(prefix='colossus-transition-') as directory:
    path=Path(directory);(path/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True)
    subprocess.run([str(path/'test.exe')],cwd=path,check=True)
