"""Execute native partial-summon retries and split merge timer recovery."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
syth = r'''
#include <cassert>
#include <cstdint>
#include <map>
#include <set>
#include <iostream>
using uint32=unsigned;using uint8=uint8_t;
enum{SYTH_90,SYTH_55,SYTH_15,SYTH_ACTION_MAX};
enum{SPELL_SUMMON_SYTH_ARCANE=33538,SPELL_SUMMON_SYTH_FIRE=33537,SPELL_SUMMON_SYTH_FROST=33539,SPELL_SUMMON_SYTH_SHADOW=33540,
 SPELL_CAST_OK=0xFF,TRIGGERED_IGNORE_COOLDOWNS=1,SAY_SUMMON=2};
struct Creature{float hp=100;std::set<unsigned>fail;std::map<unsigned,unsigned>attempts,success;
 float GetHealthPercent(){return hp;}
 int CastSpell(void*,unsigned spell,unsigned flags){assert(flags==TRIGGERED_IGNORE_COOLDOWNS);++attempts[spell];if(fail.count(spell))return 1;++success[spell];return SPELL_CAST_OK;}};
struct CombatAI{void Reset(){}};
struct AI:CombatAI{Creature*m_creature;uint8 m_summonedElements[SYTH_ACTION_MAX]={};std::set<unsigned>disabled;unsigned texts=0;bool ready=true;
 bool CanExecuteCombatAction(){return ready;}
 void SetActionReadyStatus(unsigned action,bool state){assert(!state);disabled.insert(action);}
 void DoBroadcastText(unsigned,Creature*){++texts;}
 __METHODS__
 void Tick(unsigned action){if(!disabled.count(action))ExecuteAction(action);}
};
int main(){for(unsigned failed:{33537u,33538u,33539u,33540u}){
 Creature boss;AI ai;ai.m_creature=&boss;
 ai.Tick(SYTH_90);assert(boss.attempts.empty());boss.hp=89;boss.fail={failed};
 ai.Tick(SYTH_90);ai.Tick(SYTH_90);assert(ai.disabled.empty()&&ai.texts==0);
 for(unsigned spell:{33537u,33538u,33539u,33540u})assert(boss.success[spell]==(spell==failed?0u:1u));
 boss.fail.clear();ai.Tick(SYTH_90);ai.Tick(SYTH_90);assert(ai.disabled.count(SYTH_90)&&ai.texts==1);
 for(unsigned spell:{33537u,33538u,33539u,33540u})assert(boss.success[spell]==1);
 boss.hp=54;ai.Tick(SYTH_55);boss.hp=14;ai.Tick(SYTH_15);assert(ai.disabled.size()==3&&ai.texts==3);
 for(unsigned spell:{33537u,33538u,33539u,33540u})assert(boss.success[spell]==3);
 ai.Reset();for(auto mask:ai.m_summonedElements)assert(mask==0);
 ai.disabled.clear();ai.ready=false;ai.Tick(SYTH_90);assert(ai.m_summonedElements[0]==0);
 ai.ready=true;boss.fail={failed};ai.Tick(SYTH_90);assert(ai.m_summonedElements[0]!=0&&ai.m_summonedElements[0]!=15);
 ai.Reset();for(auto mask:ai.m_summonedElements)assert(mask==0);
 }
 std::cout<<"PASS: all four Syth failure slots, no duplicate partial waves, thresholds and reset\n";
}
'''
telestra = r'''
#include <cassert>
#include <set>
#include <iostream>
enum{SPELL_SUMMON_CLONES=47710,SPELL_FIRE_DIES=47711,SPELL_FROST_DIES=47712,SPELL_ARCANE_DIES=47713,SPELL_SPAWN_BACK_IN=47714,
 CAST_OK=0,CAST_TRIGGERED=1,UNIT_FIELD_FLAGS,UNIT_FLAG_UNINTERACTIBLE,TELESTRA_SPAWN_BACK_IN,SAY_MERGE};
struct Info{int EquipmentTemplateId=1;};
struct Creature{bool alive=true,combat=true,flag=true;std::set<unsigned>auras={47710,47711,47712,47713};Info info;unsigned equipment=0;
 bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasAura(unsigned id){return auras.count(id);}
 void RemoveAurasDueToSpell(unsigned id){auras.erase(id);}void RemoveFlag(int,int){flag=false;}
 Info*GetCreatureInfo(){return &info;}void LoadEquipment(int,bool){++equipment;}};
struct AI{Creature*m_creature;unsigned m_uiCloneDeadCount=3,casts=0,timer=0,cooldowns=0,texts=0;int result=1;bool movement=false,script=true;
 int DoCastSpellIfCan(void*,int spell,int flags){assert(spell==47714&&flags==CAST_TRIGGERED);++casts;return result;}
 void ResetTimer(int action,unsigned ms){assert(action==TELESTRA_SPAWN_BACK_IN);timer=ms;}
 void DoBroadcastText(int,Creature*){++texts;}void AddInitialCooldowns(){++cooldowns;}
 void SetCombatMovement(bool v){movement=v;}void SetCombatScriptStatus(bool v){script=v;}
 __METHOD__
};
int main(){for(unsigned count:{3u,6u}){Creature boss;AI ai;ai.m_creature=&boss;ai.m_uiCloneDeadCount=count;
 ai.HandlePersonalityMerge();assert(ai.casts==1&&ai.timer==500&&boss.flag&&boss.auras.size()==4&&ai.script);
 ai.timer=0;ai.result=0;ai.HandlePersonalityMerge();assert(ai.casts==2&&!ai.timer&&!boss.flag&&boss.auras.empty()&&!ai.script&&ai.movement);
 assert(ai.cooldowns==1&&ai.texts==1&&boss.equipment==1);ai.HandlePersonalityMerge();assert(ai.casts==2);
 }
 for(unsigned invalid=0;invalid<4;++invalid){Creature boss;AI ai;ai.m_creature=&boss;
 if(invalid==0)boss.alive=false;if(invalid==1)boss.combat=false;if(invalid==2)boss.auras.clear();if(invalid==3)ai.m_uiCloneDeadCount=2;
 ai.HandlePersonalityMerge();assert(!ai.casts&&!ai.timer);
 }
 std::cout<<"PASS: both Telestra splits recover failed casts and preserve native merge/lifecycle\n";
}
'''
def run(code):
    with tempfile.TemporaryDirectory(prefix='encounter-transitions-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)

for era in ('tbc','wotlk'):
    source=(root.parent/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/outland/auchindoun/sethekk_halls/boss_darkweaver_syth.cpp').read_text()
    actor=block(source,'struct boss_darkweaver_sythAI')
    methods='\n'.join(block(actor,name).replace(' override','') for name in ('void Reset()', 'bool SythSummoning(', 'void ExecuteAction('))
    run(syth.replace('__METHODS__',methods))
source=(root.parent/'mangos-wotlk-behavior/src/game/AI/ScriptDevAI/scripts/northrend/nexus/nexus/boss_telestra.cpp').read_text()
run(telestra.replace('__METHOD__',block(source,'void HandlePersonalityMerge(')))
