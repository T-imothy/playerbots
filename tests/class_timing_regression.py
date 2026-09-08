"""Compile actual combat methods against controlled native interfaces."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
ROOT=Path(__file__).resolve().parents[1]/'playerbot/strategy'
def src(p):return (ROOT/p).read_text(encoding='utf-8')
def run(code,label,era='ZERO'):
 with tempfile.TemporaryDirectory(prefix='class-combat-') as td:
  p=Path(td);(p/'test.cpp').write_text(code,encoding='utf-8')
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
 print('PASS',label,era,flush=True)
common='''
#include <cassert>
#include <cstdint>
#include <ctime>
#include <map>
#include <string>
using uint8=uint8_t;using uint32=uint32_t;using uint64=uint64_t;
struct Event{};
'''
wait=src('generic/CombatStrategy.cpp')
run(common+r'''
struct Unit {virtual ~Unit(){};float health=100;float GetHealthPercent(){return health;}};
struct Player:Unit {bool grouped=true;void* GetGroup(){return grouped?this:nullptr;}};
struct Value{Unit* target=nullptr;Unit* Get(){return target;}};
struct AiObjectContext {Value v;template<class T>Value* GetValue(const char*){return &v;}};
enum class BotState{BOT_STATE_COMBAT};
struct PlayerbotAI {Player bot;AiObjectContext ctx;bool strategy=true,master=true;time_t start=time(nullptr);uint8 wait=10;
 bool HasStrategy(const char*,BotState){return strategy;}Player* GetBot(){return &bot;}AiObjectContext* GetAiObjectContext(){return &ctx;}bool HasRealPlayerMaster(){return master;}};
struct Facade{bool friendly=false;bool IsFriendlyTo(Unit* a,Unit* b){return a==b||friendly;}}sServerFacade;
struct Config{float lowHealth=40;}sPlayerbotAIConfig;
#define AI_VALUE(type,key) (ai->start)
struct WaitForAttackStrategy{static bool ShouldWait(PlayerbotAI*);static uint8 GetWaitTime(PlayerbotAI* ai){return ai->wait;}};
enum class ActionThreatType{ACTION_THREAT_NONE,ACTION_THREAT_SINGLE};
struct Action {virtual ~Action(){};std::string name="attack";Unit* patient=nullptr;ActionThreatType threat=ActionThreatType::ACTION_THREAT_SINGLE;
 virtual Unit* GetTarget(){return patient;}std::string& getName(){return name;}ActionThreatType getThreatType(){return threat;}};
struct CastHealingSpellAction:Action{};
struct WaitForAttackMultiplier{PlayerbotAI* ai;float GetValue(Action*);};
'''+block(wait,'bool WaitForAttackStrategy::ShouldWait')+block(wait,'float WaitForAttackMultiplier::GetValue')+r'''
int main(){PlayerbotAI ai;Player enemy;Unit mob,patient;ai.ctx.v.target=&mob;assert(WaitForAttackStrategy::ShouldWait(&ai));
 ai.ctx.v.target=&enemy;assert(!WaitForAttackStrategy::ShouldWait(&ai));sServerFacade.friendly=true;assert(WaitForAttackStrategy::ShouldWait(&ai));
 ai.ctx.v.target=&mob;ai.strategy=false;assert(!WaitForAttackStrategy::ShouldWait(&ai));ai.strategy=true;
 ai.master=false;assert(!WaitForAttackStrategy::ShouldWait(&ai));ai.master=true;ai.bot.grouped=false;assert(!WaitForAttackStrategy::ShouldWait(&ai));ai.bot.grouped=true;
 ai.start=0;assert(!WaitForAttackStrategy::ShouldWait(&ai));ai.start=time(nullptr)-20;assert(!WaitForAttackStrategy::ShouldWait(&ai));ai.start=time(nullptr);
 WaitForAttackMultiplier mul{&ai};Action damage;CastHealingSpellAction heal;heal.patient=&patient;patient.health=20;
 assert(mul.GetValue(&damage)==0);assert(mul.GetValue(&heal)==1);patient.health=90;assert(mul.GetValue(&heal)==0);
 heal.patient=nullptr;assert(mul.GetValue(&heal)==0);assert(mul.GetValue(nullptr)==1);
 damage.name="pull action";assert(mul.GetValue(&damage)==1);damage.name="cc";damage.threat=ActionThreatType::ACTION_THREAT_NONE;assert(mul.GetValue(&damage)==1);
}
''','PvP versus PvE opening wait, real master, expiry, urgent healing and pull exemptions')
run(common+r'''
struct CastSpellAction{bool success=true;uint32 duration=0,nativeDuration=2000;bool Execute(Event&){if(!success)return false;duration=nativeDuration;return true;}};
struct CastSteadyShotAction:CastSpellAction{bool Execute(Event&);};
'''+block(src('hunter/HunterActions.cpp'),'bool CastSteadyShotAction::Execute')+r'''
int main(){CastSteadyShotAction a;Event e;assert(a.Execute(e)&&a.duration==2000);a.nativeDuration=1;assert(a.Execute(e)&&a.duration==1);a.success=false;a.duration=0;assert(!a.Execute(e)&&a.duration==0);}
''','Steady Shot native duration, speed override and failed cast')
prep=block(src('rogue/RogueActions.cpp'),'bool CastPreparationAction::isUseful')
for era in ('ZERO','ONE','TWO'):
 run(common+r'''
enum {SPELLFAMILY_ROGUE=8};
struct SpellEntry{uint32 Id,SpellFamilyName,RecoveryTime;uint64 SpellFamilyFlags;};
struct Player{std::map<uint32,bool> spells,ready;bool glyph=false;auto& GetSpellMap(){return spells;}bool HasSpell(uint32 id){return spells[id];}bool HasAura(uint32){return glyph;}bool IsSpellReady(uint32 id){return ready[id];}};
struct Facade{std::map<uint32,SpellEntry> spells;const SpellEntry* LookupSpellInfo(uint32 id){auto i=spells.find(id);return i==spells.end()?nullptr:&i->second;}}sServerFacade;
struct CastBuffSpellAction{bool useful=true;bool isUseful(){return useful;}};
struct CastPreparationAction:CastBuffSpellAction{Player* bot;bool isUseful();};
'''+prep+r'''
int main(){Player b;CastPreparationAction a;a.bot=&b;assert(!a.isUseful());
 b.spells[2983]=true;sServerFacade.spells[2983]={2983,8,180000,0x40};b.ready[2983]=true;assert(!a.isUseful());b.ready[2983]=false;assert(a.isUseful());
 a.useful=false;assert(!a.isUseful());a.useful=true;b.spells[2983]=false;assert(!a.isUseful());b.spells.clear();
 b.spells[2094]=true;sServerFacade.spells[2094]={2094,8,180000,0x1000000};
#ifdef MANGOSBOT_ZERO
 assert(a.isUseful());
#else
 assert(!a.isUseful());
#endif
 b.spells.clear();b.spells[1776]=true;sServerFacade.spells[1776]={1776,8,10000,0x8};assert(!a.isUseful());
 b.spells.clear();b.spells[14185]=true;sServerFacade.spells[14185]={14185,8,600000,0x40};assert(!a.isUseful());
#ifdef MANGOSBOT_TWO
 b.spells.clear();b.spells[51722]=true;sServerFacade.spells[51722]={51722,8,60000,0x0010000000000000};assert(!a.isUseful());b.glyph=true;assert(a.isUseful());
#endif
}
''','Preparation learned cooldowns, native reset pool and glyph',era)
# Era-specific strategy contracts: these catch active passive-talents and missing fillers.
wl=src('warlock/AfflictionWarlockStrategy.cpp').split('#ifdef MANGOSBOT_TWO')
assert 'new NextAction("siphon life"' in wl[0] and 'new NextAction("siphon life"' not in wl[1]
assert 'new NextAction("amplify curse"' not in src('warlock/WarlockStrategy.cpp').split('#ifdef MANGOSBOT_TWO')[1]
hunter=src('hunter/HunterStrategy.cpp').split('#ifdef MANGOSBOT_TWO')
assert 'new NextAction("steady shot", ACTION_NORMAL)' in block(hunter[1],'NextAction** HunterStrategy::GetDefaultCombatActions')
assert 'new NextAction("steady shot", ACTION_NORMAL)' not in hunter[0]
assert 'new NextAction("unholy blight"' not in src('deathknight/GenericDKStrategy.cpp')
print('PASS expansion-specific passive talent and hunter filler contracts')

assert 'new NextAction("auto shot", ACTION_NORMAL + 1)' in block(hunter[1],'NextAction** HunterStrategy::GetDefaultCombatActions')
