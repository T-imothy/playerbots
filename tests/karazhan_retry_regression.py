"""Execute Netherspite threat preservation and Illhoof custom timer retries."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
for era in ('tbc','wotlk'):
    folder=root/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/karazhan'
    netherspite=(folder/'boss_netherspite.cpp').read_text()
    illhoof=(folder/'boss_terestian_illhoof.cpp').read_text()
    code=r'''
#include <cassert>
#include <map>
#include <set>
#include <iostream>
using uint32=unsigned;
enum{CAST_OK=0,CAST_FAIL=1,CAST_TRIGGERED=2,MINUTE=60,IN_MILLISECONDS=1000};
struct Unit{};struct Creature:Unit{Unit*victim=nullptr;unsigned removed=0;
 void RemoveAurasDueToSpell(unsigned){++removed;}void FixateTarget(Unit*){}Unit*GetVictim(){return victim;}void SetTarget(Unit*){}};
unsigned texts=0;void DoScriptText(int,Creature*){++texts;}void DoBroadcastText(int,Creature*){++texts;}
unsigned urand(unsigned a,unsigned){return a;}
struct Base{
 Creature*m_creature;unsigned result=CAST_OK,casts=0,threatResets=0,despawns=0,summons=0;bool movement=true,melee=true;
 std::map<unsigned,unsigned>timers;std::set<unsigned>disabled;
 unsigned DoCastSpellIfCan(Unit*,unsigned,unsigned=0){++casts;return result;}
 void ResetTimer(unsigned id,unsigned time){timers[id]=time;}void ResetCombatAction(unsigned id,unsigned time){timers[id]=time;}
 void DisableCombatAction(unsigned id){disabled.insert(id);}void SetCombatMovement(bool v){movement=v;}void SetMeleeEnabled(bool v){melee=v;}
 void DespawnPortals(){++despawns;}void DoSummonPortals(){++summons;}void DoResetThreat(){++threatResets;}void DoStartMovement(Unit*){}
};
namespace nether{
__NETHER_ENUMS__
struct Boss:Base{unsigned m_uiActivePhase=BEAM_PHASE;__SWITCH__};
}
namespace ill{
__ILL_ENUMS__
struct Boss:Base{__ILL_METHODS__};
}
int main(){
 Creature creature;nether::Boss boss;boss.m_creature=&creature;
 for(unsigned cycle=0;cycle<100;++cycle){
  unsigned threat=boss.threatResets,despawn=boss.despawns,removed=creature.removed;boss.result=CAST_FAIL;
  boss.SwitchPhases();assert(boss.m_uiActivePhase==nether::BEAM_PHASE&&boss.threatResets==threat&&boss.despawns==despawn);
  assert(creature.removed==removed&&boss.melee&&boss.movement);
  boss.result=CAST_OK;boss.SwitchPhases();assert(boss.m_uiActivePhase==nether::BANISH_PHASE&&boss.threatResets==threat+1);
  assert(boss.despawns==despawn+1&&!boss.melee&&!boss.movement&&boss.timers.at(nether::NETHERSPITE_PHASE_CHANGE)==30000);
  boss.SwitchPhases();assert(boss.m_uiActivePhase==nether::BEAM_PHASE&&boss.threatResets==threat+2&&boss.melee&&boss.movement);
  assert(boss.timers.at(nether::NETHERSPITE_PHASE_CHANGE)==60000&&boss.summons==cycle+1);
 }
 ill::Boss imp;imp.m_creature=&creature;
 using Method=void(ill::Boss::*)();
 for(auto row:{std::pair<unsigned,Method>{ill::ILLHOOF_ACTION_SUMMON,&ill::Boss::HandleSummonPortal},
     {ill::ILLHOOF_ACTION_SUMMON_KILREK,&ill::Boss::HandleSummonKilrek},{ill::ILLHOOF_ACTION_BERSERK,&ill::Boss::HandleBerserk}}){
  imp.result=CAST_FAIL;unsigned before=texts;(imp.*row.second)();
  assert(imp.timers.at(row.first)==500&&!imp.disabled.count(row.first)&&texts==before);
  imp.result=CAST_OK;(imp.*row.second)();assert(imp.disabled.count(row.first));
 }
 std::cout<<"PASS:100 Netherspite failed/successful phase cycles preserve threat; Illhoof one-shot timers retry\n";
}
'''.replace('__NETHER_ENUMS__',';\n'.join(block(netherspite,s) for s in ('enum\n','enum NetherspitePhases','enum NetherspiteActions'))+';')
    code=code.replace('__ILL_ENUMS__',block(illhoof,'enum\n')+';\n'+block(illhoof,'enum IllhoofActions')+';')
    code=code.replace('__SWITCH__',block(netherspite,'    void SwitchPhases()'))
    code=code.replace('__ILL_METHODS__','\n'.join(block(illhoof,s) for s in ('    void HandleSummonPortal()','    void HandleSummonKilrek()','    void HandleBerserk()')))
    for prenerf in (False,True):
        with tempfile.TemporaryDirectory(prefix='karazhan-retry-') as directory:
            path=Path(directory);(path/'test.cpp').write_text(code)
            subprocess.run(['cl','/nologo','/EHsc','/std:c++17',*(['/DPRENERF_2_0_3'] if prenerf else []),'test.cpp','/Fe:test.exe'],cwd=path,check=True)
            subprocess.run([str(path/'test.exe')],cwd=path,check=True)
