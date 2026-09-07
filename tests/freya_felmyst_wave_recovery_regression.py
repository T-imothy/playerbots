"""Native wave counters only advance for successful casts; Freya retries stay bounded."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
felmyst=r'''
#include <cassert>
#include <iostream>
enum{CAST_OK=0,CAST_FAIL=1,SUBPHASE_VAPOR,SPELL_SUMMON_VAPOR,FELMYST_DEMONIC_VAPOR};
unsigned urand(unsigned lo,unsigned){return lo;}
struct Creature{bool hover=true,immobilized=false;bool HasHoverAura(){return hover;}void SetHover(bool v){hover=v;}void SetImmobilizedState(bool v){immobilized=v;}};
struct AI{Creature*m_creature;bool m_instance=true,m_bIsLeftSide=false;unsigned m_uiDemonicVaporCount=0,m_uiCorruptionCount=0,m_uiSubPhase=0;
 unsigned result=CAST_OK,calls=0,timer=0,sideMoves=0;unsigned DoCastSpellIfCan(void*,unsigned){++calls;return result;}
 void ResetTimer(unsigned id,unsigned ms){assert(id==FELMYST_DEMONIC_VAPOR);timer=ms;}void HandleSideMove(){++sideMoves;}
 __METHOD__
};
int main(){
 Creature boss;AI ai{&boss};ai.result=CAST_FAIL;ai.HandleDemonicVapor();assert(ai.m_uiDemonicVaporCount==0&&ai.timer==1000);
 ai.result=CAST_OK;ai.HandleDemonicVapor();assert(ai.m_uiDemonicVaporCount==1&&ai.timer==11000);
 ai.result=CAST_FAIL;ai.HandleDemonicVapor();assert(ai.m_uiDemonicVaporCount==1&&ai.timer==1000);
 ai.result=CAST_OK;ai.HandleDemonicVapor();assert(ai.m_uiDemonicVaporCount==2&&ai.timer==11000);
 unsigned calls=ai.calls;ai.HandleDemonicVapor();assert(ai.calls==calls&&ai.sideMoves==1&&boss.hover&&!boss.immobilized);
 std::cout<<"PASS: Felmyst failed vapor retains its slot and native inter-phase timing\n";
}
'''
freya=r'''
#include <cassert>
#include <algorithm>
#include <random>
#include <vector>
#include <iostream>
using uint8=unsigned char;using uint32=unsigned;using AIEventType=unsigned;
enum{CAST_OK=0,CAST_FAIL=1,CAST_TRIGGERED=2,AI_EVENT_CUSTOM_A=1,AI_EVENT_CUSTOM_B=2,
 MAX_ALLIES_SPELLS=3,MAX_ALLIES_WAVES=6,SPELL_SUMMON_WAVE_1=10,SPELL_SUMMON_WAVE_3=11,SPELL_SUMMON_WAVE_10=12,
 SAY_ADDS_CONSERVATOR=20,SAY_ADDS_TRIO,SAY_ADDS_LASHER};
struct Unit{};struct Creature:Unit{bool alive=true,combat=true;bool IsAlive(){return alive;}bool IsInCombat(){return combat;}};
std::mt19937 rng(4);std::mt19937*GetRandomGenerator(){return &rng;}unsigned urand(unsigned lo,unsigned hi){return std::uniform_int_distribution<unsigned>(lo,hi)(rng);}
struct AI{Creature*m_creature;unsigned m_uiAlliesWaveCount=0,m_uiThreeAlliesTimer=0,m_uiAllyRetryTimer=0,result=CAST_OK;
 bool m_bEventFinished=false;std::vector<unsigned>spawnSpellsVector{10,11,12},casts,lines;
 unsigned DoCastSpellIfCan(Unit*,unsigned id,unsigned){casts.push_back(id);return result;}
 void DoScriptText(unsigned id,Unit*){lines.push_back(id);}
 __METHOD__
 void Tick(unsigned uiDiff){__RETRY__}
};
int main(){
 for(unsigned seed=0;seed<100;++seed){
  rng.seed(seed);Creature boss;AI ai{&boss};ai.result=CAST_FAIL;ai.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&boss,&boss,0);
  assert(ai.m_uiAlliesWaveCount==0&&ai.m_uiAllyRetryTimer==1000&&ai.lines.empty());
  ai.Tick(999);assert(ai.casts.size()==1&&ai.m_uiAllyRetryTimer==1);ai.Tick(1);
  assert(ai.casts.size()==2&&ai.m_uiAllyRetryTimer==1000&&ai.m_uiAlliesWaveCount==0);
  ai.result=CAST_OK;ai.Tick(1000);assert(ai.m_uiAlliesWaveCount==1&&ai.lines.size()==1&&!ai.m_uiAllyRetryTimer);
  for(unsigned i=1;i<6;++i)ai.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&boss,&boss,0);
  assert(ai.m_uiAlliesWaveCount==6&&ai.casts.size()==8&&ai.lines.size()==6);
  std::vector<unsigned>first(ai.casts.begin()+2,ai.casts.begin()+5),last(ai.casts.begin()+5,ai.casts.end());
  std::sort(first.begin(),first.end());std::sort(last.begin(),last.end());assert(first==last&&first==std::vector<unsigned>({10,11,12}));
  assert(ai.casts[4]!=ai.casts[5]);
  for(unsigned extra=0;extra<10;++extra)ai.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&boss,&boss,0);
  assert(ai.casts.size()==8&&ai.m_uiAlliesWaveCount==6); // No out-of-range seventh-wave access.
 }
 Creature boss;AI invalid{&boss};boss.alive=false;invalid.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&boss,&boss,0);assert(invalid.casts.empty());
 boss.alive=true;boss.combat=false;invalid.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&boss,&boss,0);assert(invalid.casts.empty());
 boss.combat=true;invalid.m_bEventFinished=true;invalid.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&boss,&boss,0);assert(invalid.casts.empty());
 invalid.m_bEventFinished=false;invalid.spawnSpellsVector.clear();invalid.ReceiveAIEvent(AI_EVENT_CUSTOM_A,&boss,&boss,0);assert(invalid.casts.empty());
 invalid.ReceiveAIEvent(AI_EVENT_CUSTOM_B,&boss,&boss,0);assert(invalid.m_uiThreeAlliesTimer==12000);
 std::cout<<"PASS: Freya native failure retry, six-wave cap, bounded reshuffle and lifecycle\n";
}
'''
def run(code):
    with tempfile.TemporaryDirectory(prefix='native-wave-recovery-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
for era in ('tbc','wotlk'):
    source=(root.parent/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/sunwell_plateau/boss_felmyst.cpp').read_text()
    run(felmyst.replace('__METHOD__',block(source,'void HandleDemonicVapor(')))
source=(root.parent/'mangos-wotlk-behavior/src/game/AI/ScriptDevAI/scripts/northrend/ulduar/ulduar/boss_freya.cpp').read_text()
actor=block(source,'struct boss_freyaAI')
update=block(actor,'void UpdateAI(')
run(freya.replace('__METHOD__',block(actor,'void ReceiveAIEvent(').replace(' override','')).replace('__RETRY__',block(update,'if (m_uiAllyRetryTimer)')))
assert 'm_uiAllyRetryTimer          = 0;' in block(actor,'void Reset(')
assert update.index('if (m_uiAllyRetryTimer)') > update.index('if (!m_creature->SelectHostileTarget()')
