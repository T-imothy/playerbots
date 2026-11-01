"""Execute native-phase-gated wave selection, including idle alcove exclusion."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
code=r'''
#include <cassert>
#include <list>
#include <map>
#include <vector>
#include <string>
#include <iostream>
#include <type_traits>
using uint32=unsigned;using ObjectGuid=unsigned;
constexpr unsigned IN_PROGRESS=1,UNIT_CREATED_BY_SPELL=1;
enum class BotState{BOT_STATE_COMBAT};
struct Unit{unsigned guid=1,entry=15990,owner=0,spell=0;bool live=true,channel=true,friendly=false,engaged=false,possible=true,cc=false;float distance=30;
 bool player=false;Unit*victim=nullptr;Unit*master=nullptr;bool IsPlayer(){return player;}Unit*GetVictim(){return victim;}Unit*GetMaster(){return master;}
 bool HasAura(unsigned s){return channel&&s==29423;}unsigned GetObjectGuid(){return guid;}unsigned GetEntry(){return entry;}unsigned GetSpawnerGuid(){return owner;}
 unsigned GetUInt32Value(unsigned){return spell;}float GetDistance(Unit*){return distance;}};
struct Instance{virtual ~Instance()=default;};
struct ScriptedInstance:Instance{unsigned state=1;Unit*boss=nullptr;unsigned GetData(unsigned key){assert(key==14);return state;}
 Unit*GetSingleCreatureFromStorage(unsigned e,bool){assert(e==15990);return boss;}};
struct Map{Instance*instance;std::vector<Unit*>triggers;bool available=true;Instance*GetInstanceData(){return instance;}
 const std::vector<Unit*>*GetCreatures(const char*name){assert(std::string(name)=="KEL_THUZAD_WORLD_TRIGGERS_ADDS");return available?&triggers:nullptr;}};
struct Player:Unit{unsigned map=533;bool alive=true,world=true,transfer=false,charmed=false,group=true;Map*ptr=nullptr;
 unsigned GetMapId(){return map;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsBeingTeleported(){return transfer;}bool HasCharmer(){return charmed;}bool GetGroup(){return group;}Map*GetMap(){return ptr;}};
std::list<unsigned> nearby;unsigned currentGuid=0;std::map<unsigned,Unit*> units;
template<class T>struct Value{T Get(){if constexpr(std::is_same_v<T,unsigned>)return currentGuid;else return nearby;}};
struct Context{template<class T>Value<T>*GetValue(const char*,const char* =nullptr){static Value<T> v;return &v;}};
struct PlayerbotAI{Player*bot;Player*master=nullptr;bool real=false,heal=false,ranged=true,tank=false,dungeon=true;Context context;
 Player*GetBot(){return bot;}Player*GetMaster(){return master;}bool IsRealPlayer(){return real;}bool IsHeal(Player*){return heal;}bool IsRanged(Player*){return ranged;}bool IsTank(Player*){return tank;}
 bool HasStrategy(const char*,BotState){return dungeon;}Context*GetAiObjectContext(){return &context;}Unit*GetUnit(unsigned g){return units[g];}};
bool Live(Player*,Unit*u){return u&&u->live;}bool Member(Player*,Player*p){return p&&p->live&&p->world&&p->alive&&!p->transfer&&p->group;}
bool Engaged(Player*,Unit*u){return u&&u->engaged;}
struct {bool IsFriendlyTo(Player*,Unit*u){return u->friendly;}}sServerFacade;
struct {float sightDistance=60;}sPlayerbotAIConfig;
struct PossibleAttackTargetsValue{static bool IsPossibleTarget(Unit*u,Player*,float,bool){return u->possible;}static bool HasBreakableCC(Unit*u,Player*){return u->cc;}static bool HasUnBreakableCC(Unit*,Player*){return false;}};
#define AI_VALUE(type,key) currentGuid
namespace ai{Unit*KelthuzadOpeningTarget(PlayerbotAI*);bool KelthuzadDormantAdd(Player*,Unit*);}
'''+block(source,'bool ai::KelthuzadDormantAdd(')+'\n'+block(source,'Unit* ai::KelthuzadOpeningTarget(PlayerbotAI* ai)')+r'''
int main(){
 Player bot;Unit boss,soldier,abom,weaver,idle,foreign,trigger;ScriptedInstance instance;Map map{&instance};instance.boss=&boss;bot.ptr=&map;
 trigger.guid=10;trigger.entry=15384;map.triggers={&trigger};
 PlayerbotAI brain{&bot};
 soldier.guid=2;soldier.entry=16427;soldier.owner=10;soldier.spell=28421;
 abom=soldier;abom.guid=3;abom.entry=16428;abom.spell=28422;abom.distance=10;
 weaver=soldier;weaver.guid=4;weaver.entry=16429;weaver.spell=28423;
 idle=soldier;idle.guid=5;idle.owner=1;idle.spell=0;idle.distance=5;
 foreign=soldier;foreign.guid=6;foreign.owner=9;foreign.distance=5;
 for(Unit*u:{&soldier,&abom,&weaver,&idle,&foreign})units[u->guid]=u;
 nearby={5,6,2,3,4};
#ifdef MANGOSBOT_ZERO
 assert(ai::KelthuzadOpeningTarget(&brain)==&weaver); // Boss is deliberately not engaged.
 soldier.distance=19;assert(ai::KelthuzadOpeningTarget(&brain)==&soldier);
 soldier.distance=30;weaver.possible=false;assert(ai::KelthuzadOpeningTarget(&brain)==&soldier);
 soldier.cc=true;assert(ai::KelthuzadOpeningTarget(&brain)==&abom);soldier.cc=false;weaver.possible=true;
 brain.ranged=false;assert(ai::KelthuzadOpeningTarget(&brain)==&abom);abom.distance=16;assert(!ai::KelthuzadOpeningTarget(&brain));abom.distance=10;
 brain.ranged=true;brain.tank=true;assert(ai::KelthuzadOpeningTarget(&brain)==&abom);brain.tank=false;
 nearby={5,6};assert(!ai::KelthuzadOpeningTarget(&brain));
 idle.engaged=true;assert(ai::KelthuzadDormantAdd(&bot,&idle)); // Our own stale assist selection does not wake an alcove.
 assert(!ai::KelthuzadOpeningTarget(&brain));bot.player=true;idle.victim=&bot;
 assert(!ai::KelthuzadDormantAdd(&bot,&idle));assert(ai::KelthuzadOpeningTarget(&brain)==&idle);
 Unit pet;pet.master=&bot;idle.victim=&pet;assert(!ai::KelthuzadDormantAdd(&bot,&idle));
 bot.group=false;assert(!ai::KelthuzadDormantAdd(&bot,&idle));bot.group=true;
 idle.victim=nullptr;idle.engaged=false;
 assert(!ai::KelthuzadDormantAdd(&bot,&soldier));assert(!ai::KelthuzadDormantAdd(&bot,&foreign));
 boss.channel=false;assert(!ai::KelthuzadDormantAdd(&bot,&idle));boss.channel=true;
 nearby={2};soldier.distance=46;assert(!ai::KelthuzadOpeningTarget(&brain));soldier.distance=30;
 map.available=false;assert(!ai::KelthuzadOpeningTarget(&brain));map.available=true;
 trigger.entry=999;assert(!ai::KelthuzadOpeningTarget(&brain));trigger.entry=15384;
 trigger.live=false;assert(!ai::KelthuzadOpeningTarget(&brain));trigger.live=true;
 soldier.spell=28422;assert(!ai::KelthuzadOpeningTarget(&brain));soldier.spell=28421;
 for(unsigned fault=0;fault<13;++fault){
  Player b=bot;PlayerbotAI a=brain;a.bot=&b;Unit saved=boss;
  if(fault==0)b.map=469;if(fault==1)b.world=false;if(fault==2)b.alive=false;if(fault==3)b.transfer=true;if(fault==4)b.charmed=true;
  if(fault==5)b.group=false;if(fault==6)a.real=true;if(fault==7)a.heal=true;if(fault==8)a.dungeon=false;
  if(fault==9)instance.state=0;if(fault==10)boss.channel=false;if(fault==11)boss.friendly=true;if(fault==12)boss.live=false;
  assert(!ai::KelthuzadOpeningTarget(&a));instance.state=1;boss=saved;
 }
 Unit second=soldier;second.guid=7;second.distance=25;units[7]=&second;nearby={7,2};currentGuid=2;
 assert(ai::KelthuzadOpeningTarget(&brain)==&soldier); // Do not cancel casts for equal-priority closer adds.
 second.distance=10;assert(ai::KelthuzadOpeningTarget(&brain)==&second); // Imminent explosion can override.
#else
 assert(!ai::KelthuzadDormantAdd(&bot,&idle));
 assert(!ai::KelthuzadOpeningTarget(&brain));
#endif
 std::cout<<"PASS phase-one incoming ownership, alcove exclusion, roles, CC, lifecycle, stable target and era gates\n";
}
'''
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='kt-opening-') as folder:
  path=Path(folder);(path/'test.cpp').write_text(code)
  r=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
  if r.returncode:print(r.stdout,r.stderr)
  r.check_returncode();subprocess.run([str(path/'test.exe')],cwd=path,check=True)
strategy=(root/'playerbot/strategy/generic/NaxxramasDungeonStrategies.cpp').read_text()
assert '"kelthuzad opening target"' in block(strategy,'void NaxxramasDungeonStrategy::InitNonCombatTriggers')
assert 'creators["kelthuzad opening target"]' in (root/'playerbot/strategy/triggers/TriggerContext.h').read_text()
