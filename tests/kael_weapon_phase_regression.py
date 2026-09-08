"""Run Kael's native opening cast, completion and partial weapon recovery."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
for era in ('tbc','wotlk'):
    source=next((root/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts').rglob('boss_kaelthas.cpp')).read_text()
    assert 'm_weaponSummons = 0;' in block(source,'    void Reset()')
    assert 'AddCustomAction(KAEL_WEAPON_SUMMON_RETRY' in source
    methods='\n'.join(block(source,s).replace(' override','') for s in ('    void HandlePhaseOne()', '    void SpellHit(Unit*', '    void HandleWeaponSummons()'))
    code=r'''
#include <cassert>
#include <map>
#include <iostream>
using uint32=unsigned;
enum{CAST_OK=0,CAST_FAIL=1,CAST_TRIGGERED=1,UNIT_FIELD_FLAGS=0,UNIT_FLAG_IMMUNE_TO_PLAYER=1,
 NPC_THALADRED=1,NPC_SANGUINAR=2,NPC_CAPERNIAN=3,NPC_TELONICUS=4};
__ENUMS__
struct Unit{};struct SpellEntry{unsigned Id;};
struct FakeAI{void AttackClosestEnemy(){}};
struct Creature:Unit{bool alive=true,combat=true;FakeAI ai;
 bool IsAlive(){return alive;}bool IsInCombat(){return combat;}void RemoveFlag(unsigned,unsigned){}void SetInCombatWithZone(){}FakeAI*AI(){return &ai;}};
struct Instance{Creature advisor;Creature*GetSingleCreatureFromStorage(unsigned){return &advisor;}};
void DoBroadcastText(int,Creature*){}
struct Boss{Creature*m_creature;Instance*m_instance;unsigned m_uiPhase=PHASE_1_ADVISOR,m_uiPhaseSubphase=8,m_weaponSummons=0,fail=0;
 std::map<unsigned,unsigned>timers,accepted;
 unsigned DoCastSpellIfCan(Creature*,unsigned id,unsigned=0){if(id==fail)return CAST_FAIL;++accepted[id];return CAST_OK;}
 void ResetTimer(unsigned id,unsigned delay){timers[id]=delay;}
 __METHODS__
};
int main(){Creature c;Instance instance;Boss b;b.m_creature=&c;b.m_instance=&instance;
 b.fail=SPELL_SUMMON_WEAPONS;b.HandlePhaseOne();assert(b.m_uiPhaseSubphase==8&&b.timers[KAEL_PHASE_ONE]==500);
 // An accepted cast with no completion callback must remain recoverable.
 b.fail=0;for(unsigned n=0;n<100;++n){b.HandlePhaseOne();assert(b.m_uiPhase==PHASE_1_ADVISOR&&b.m_uiPhaseSubphase==8&&b.timers[KAEL_PHASE_ONE]==4000);}
 SpellEntry spell{SPELL_SUMMON_WEAPONS};b.fail=m_spellSummonWeapon[2];b.SpellHit(&c,&spell);
 assert(b.m_uiPhase==PHASE_2_WEAPON&&b.m_uiPhaseSubphase==9&&b.m_weaponSummons==3&&b.timers[KAEL_WEAPON_SUMMON_RETRY]==500&&!b.timers.count(KAEL_PHASE_TWO));
 b.HandlePhaseOne();assert(b.m_uiPhaseSubphase==9);b.SpellHit(&c,&spell);assert(b.m_weaponSummons==3);
 for(unsigned index=3;index<MAX_WEAPONS;++index){b.fail=m_spellSummonWeapon[index];b.HandleWeaponSummons();assert(b.m_weaponSummons==(1u<<index)-1);}
 b.fail=0;b.HandleWeaponSummons();assert(b.m_weaponSummons==(1u<<MAX_WEAPONS)-1);
 for(unsigned id:m_spellSummonWeapon)assert(b.accepted[id]==1);
#ifdef FAST_TIMERS
 assert(b.timers[KAEL_PHASE_TWO]==10000);
#elif defined(PRENERF_2_0_3)
 assert(b.timers[KAEL_PHASE_TWO]==90000);
#else
 assert(b.timers[KAEL_PHASE_TWO]==120000);
#endif
 b.timers[KAEL_PHASE_TWO]=123;b.HandleWeaponSummons();assert(b.timers[KAEL_PHASE_TWO]==123);
 b.m_weaponSummons=0;c.combat=false;b.HandleWeaponSummons();assert(b.m_weaponSummons==0);c.combat=true;c.alive=false;b.HandleWeaponSummons();assert(b.m_weaponSummons==0);
 b.m_uiPhase=PHASE_0_NOT_BEGUN;b.SpellHit(&c,&spell);assert(b.m_uiPhase==PHASE_0_NOT_BEGUN);
 std::cout<<"PASS: Kael interrupted opening, all seven partial summons exactly once, stale callbacks and phase timers\n";
}
'''.replace('__ENUMS__',block(source,'enum\n')+';\n'+block(source,'enum KaelThasActions')+';\n'+block(source,'static const uint32 m_spellSummonWeapon')+';').replace('__METHODS__',methods)
    for defines in ([],['/DPRENERF_2_0_3'],['/DFAST_TIMERS']):
        with tempfile.TemporaryDirectory(prefix='kael-weapons-') as directory:
            path=Path(directory);(path/'test.cpp').write_text(code)
            subprocess.run(['cl','/nologo','/EHsc','/std:c++17',*defines,'test.cpp','/Fe:test.exe'],cwd=path,check=True)
            subprocess.run([str(path/'test.exe')],cwd=path,check=True)
