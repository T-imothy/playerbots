"""Execute native resurrection lambdas and Chromaggus's one-shot enrage."""
from pathlib import Path
import subprocess,tempfile,re
from behavior_regression import block
root=Path(__file__).resolve().parents[2]
for era in ('classic','tbc','wotlk'):
    scripts=root/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/eastern_kingdoms'
    source=(scripts/'zulgurub/boss_thekal.cpp').read_text()
    def callback(struct,action):
        scope=source[source.index('struct '+struct):]
        text=block(scope,'AddCustomAction('+action)
        return text[text.index('{')+1:text.rindex('}')]
    chrom=(scripts/'blackwing_lair/boss_chromaggus.cpp').read_text()
    enrage=block(chrom,'            case CHROMAGGUS_ENRAGE:')
    spell=re.search(r'SPELL_ENRAGE\s*=\s*(\d+)',chrom)[1]
    code=r'''
#include <cassert>
#include <map>
#include <iostream>
using uint32=unsigned;
enum{CAST_OK=0,CAST_FAIL=1,TYPE_THEKAL=0,TYPE_LORKHAN=1,TYPE_ZATH=2,IN_PROGRESS=1,SPECIAL=4,
 THEKAL_RESS_PHASE_2_DELAY=20,THEKAL_TIGER_ENRAGE=0,UNIT_FIELD_FLAGS,UNIT_FLAG_UNINTERACTIBLE,
 UNIT_STAND_STATE_STAND,EMOTE_GENERIC_FRENZY};
__ENUM__
struct Creature{bool alive=true,combat=true;float hp=19;unsigned health=1,flags=1,list=0;
 bool IsAlive(){return alive;}bool IsInCombat(){return combat;}float GetHealthPercent(){return hp;}
 void RemoveFlag(unsigned,unsigned){flags=0;}void SetStandState(unsigned){}void RemoveAurasDueToSpell(unsigned){}
 void SetHealth(unsigned v){health=v;}unsigned GetMaxHealth(){return 100;}void SetSpellList(unsigned v){list=v;}};
struct Instance{unsigned states[3]={SPECIAL,SPECIAL,SPECIAL};unsigned GetData(unsigned id){return states[id];}void SetData(unsigned id,unsigned v){states[id]=v;}};
struct Base{
 Creature*m_creature;Instance*m_instance;unsigned m_uiPhase=PHASE_FAKE_DEATH,result=CAST_OK,casts=0,preventCalls=0;
 bool deathPrevention=true,script=true,melee=false,movement=false;std::map<unsigned,unsigned>timers;std::map<unsigned,bool>ready;
 unsigned DoCastSpellIfCan(Creature*,unsigned){++casts;return result;}
 void ResetTimer(unsigned id,unsigned delay){timers[id]=delay;}
 void SetDeathPrevention(bool v){deathPrevention=v;}void SetCombatScriptStatus(bool v){script=v;}void SetMeleeEnabled(bool v){melee=v;}
 void SetCombatMovement(bool v,bool=false){movement=v;}void SetActionReadyStatus(unsigned id,bool v){ready[id]=v;}
 void CanPreventAddsResurrect(){++preventCalls;}void DoResetThreat(){}void Reset(){timers.clear();}bool OnRevive(){return false;}
 __REVIVE__
};
struct Thekal:Base{void Resurrect(){__THEKAL__}void Tiger(){__TIGER__}};
struct Lorkhan:Base{void Resurrect(){__LORKHAN__}};
struct Zath:Base{void Resurrect(){__ZATH__}};
void DoScriptText(int,Creature*){}
namespace chrome{
constexpr unsigned CHROMAGGUS_ENRAGE=0,SPELL_ENRAGE=__CHROME_SPELL__;
struct Boss:Base{void ExecuteAction(unsigned action){switch(action){__ENRAGE__}}};
}
template<class Actor>void testZealot(unsigned who,unsigned other){
 Creature creature;Instance instance;instance.states[TYPE_THEKAL]=IN_PROGRESS;
 Actor actor;actor.m_creature=&creature;actor.m_instance=&instance;actor.result=CAST_FAIL;
 actor.Resurrect();assert(actor.timers.at(ACTION_RESSURECTION)==500&&instance.states[who]==SPECIAL);
 actor.result=CAST_OK;actor.Resurrect();assert(actor.timers.at(ACTION_RESSURECTION)==3000&&instance.states[who]==IN_PROGRESS);
 unsigned casts=actor.casts;actor.Resurrect();assert(actor.casts==casts+1); // Missed completion can retry.
 actor.Revive();assert(actor.m_uiPhase==PHASE_NORMAL&&actor.timers.empty()&&creature.health==100);
 casts=actor.casts;actor.Resurrect();assert(actor.casts==casts);
 actor.m_uiPhase=PHASE_FAKE_DEATH;instance.states[TYPE_THEKAL]=instance.states[other]=SPECIAL;
 actor.Resurrect();assert(actor.casts==casts); // Other two down: preserve the coordinated kill.
 actor.m_instance=nullptr;actor.Resurrect();assert(actor.casts==casts);
}
int main(){
 Creature creature;Instance instance;Thekal boss;boss.m_creature=&creature;boss.m_instance=&instance;
 boss.result=CAST_FAIL;boss.Resurrect();assert(boss.m_uiPhase==PHASE_FAKE_DEATH&&instance.states[TYPE_THEKAL]==SPECIAL);
 assert(boss.timers.at(ACTION_RESSURECTION)==500&&boss.preventCalls==0);
 boss.result=CAST_OK;boss.Resurrect();assert(boss.m_uiPhase==PHASE_WAITING&&boss.timers.at(ACTION_RESSURECTION)==3000);
 unsigned casts=boss.casts;boss.Resurrect();assert(boss.casts==casts+1);
 boss.Revive();assert(boss.m_uiPhase==PHASE_NORMAL&&boss.timers.empty());casts=boss.casts;
 boss.Resurrect();assert(boss.casts==casts);
 boss.result=CAST_FAIL;boss.Tiger();assert(boss.m_uiPhase==PHASE_NORMAL&&boss.deathPrevention&&boss.timers.at(THEKAL_RESS_PHASE_2_DELAY)==500);
 boss.result=CAST_OK;boss.Tiger();assert(boss.m_uiPhase==PHASE_TIGER&&!boss.deathPrevention&&creature.list==SPELL_LIST_PHASE_2);
 boss.m_uiPhase=PHASE_FAKE_DEATH;creature.combat=false;casts=boss.casts;boss.Resurrect();boss.Tiger();assert(boss.casts==casts);
 creature.combat=true;creature.alive=false;boss.Resurrect();boss.Tiger();assert(boss.casts==casts);
 testZealot<Lorkhan>(TYPE_LORKHAN,TYPE_ZATH);testZealot<Zath>(TYPE_ZATH,TYPE_LORKHAN);
 creature.alive=true;chrome::Boss chrom;chrom.m_creature=&creature;chrom.ready[0]=true;chrom.result=CAST_FAIL;
 chrom.ExecuteAction(0);assert(chrom.ready[0]);chrom.result=CAST_OK;chrom.ExecuteAction(0);assert(!chrom.ready[0]);
 creature.hp=21;casts=chrom.casts;chrom.ExecuteAction(0);assert(chrom.casts==casts);
 std::cout<<"PASS: Thekal/trio interrupted resurrection retries and native revive cleanup; tiger/enrage failure guards\n";
}
'''.replace('__ENUM__',block(source,'enum\n')+';').replace('__REVIVE__',block(source,'    void Revive('))
    for key,value in {'THEKAL':callback('boss_thekalAI','ACTION_RESSURECTION'),
        'TIGER':callback('boss_thekalAI','THEKAL_RESS_PHASE_2_DELAY'),
        'LORKHAN':callback('mob_zealot_lorkhanAI','ACTION_RESSURECTION'),
        'ZATH':callback('mob_zealot_zathAI','ACTION_RESSURECTION'),
        'CHROME_SPELL':spell,'ENRAGE':enrage}.items():code=code.replace('__'+key+'__',value)
    with tempfile.TemporaryDirectory(prefix='thekal-chromaggus-recovery-') as directory:
        path=Path(directory);(path/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True)
        subprocess.run([str(path/'test.exe')],cwd=path,check=True)
