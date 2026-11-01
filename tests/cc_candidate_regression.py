"""Actual marked/automatic CC selector, with native castability supplied by a controlled interface."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/values/CcTargetValue.cpp').read_text()
selector=block(source,'class FindTargetForCcStrategy')+';'
calculate=block(source,'ObjectGuid CcTargetValue::Calculate(')
code=r'''
#include <cassert>
#include <cmath>
#include <iostream>
#include <list>
#include <map>
#include <string>
#include <vector>
using uint8=unsigned char;using ObjectGuid=unsigned;
constexpr unsigned SPELL_AURA_PERIODIC_DAMAGE=3,SPELL_AURA_MOD_FEAR=4;
enum class BotState {BOT_STATE_COMBAT};
struct Unit {
 virtual ~Unit()=default;unsigned id=1,map=409,instance=1,phase=1;float x=0;unsigned health=100;
 bool world=true,alive=true,teleport=false,player=false,dot=false,castable=true,ownAura=false,controlled=false,feared=false;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsBeingTeleported(){return teleport;}
 bool IsInMap(Unit* t){return world&&t->world&&map==t->map&&instance==t->instance
#ifndef MANGOSBOT_ZERO
  &&phase==t->phase
#endif
 ;}
 ObjectGuid GetObjectGuid(){return id;}unsigned GetHealthPercent(){return health;}bool IsPlayer(){return player;}
 bool HasAuraType(unsigned id){return id==SPELL_AURA_MOD_FEAR?feared:dot;}unsigned GetMapId(){return map;}
 bool HasBreakableByDamageCrowdControlAura(){return controlled;}
};
struct Member {ObjectGuid guid;};
struct Group {using MemberSlotList=std::vector<Member>;using member_citerator=MemberSlotList::const_iterator;
 MemberSlotList members;const MemberSlotList& GetMemberSlots(){return members;}};
struct PlayerbotAI;
struct Player:Unit {Group* group=nullptr;PlayerbotAI*brain=nullptr;unsigned selection=0;bool tank=false;Group* GetGroup(){return group;}PlayerbotAI*GetPlayerbotAI(){return brain;}unsigned GetSelectionGuid(){return selection;}};
struct {std::map<unsigned,Player*> players;Player* GetPlayer(unsigned id){return players[id];}} sObjectMgr;
struct WorldLocation {float coord_x=0,coord_y=0;};
template<class T>struct Cached {T data{};T Get(){return data;}};
struct AiObjectContext {Unit* marked=nullptr;Unit* current=nullptr;Unit* rti=nullptr;std::string rtiName="moon";uint8 aoe=0;Cached<ObjectGuid>selected;
 std::list<ObjectGuid> possible;
 template<class T>T Read(const std::string& name);
 template<class T>Cached<T>*GetValue(const char*){selected.data=current?current->id:0;return &selected;}
};
template<>ObjectGuid AiObjectContext::Read(const std::string& name){Unit*u=name=="rti cc target"?marked:name=="current target"?current:rti;return u?u->id:0;}
template<>std::string AiObjectContext::Read(const std::string&){return rtiName;}
template<>uint8 AiObjectContext::Read(const std::string&){return aoe;}
template<>WorldLocation AiObjectContext::Read(const std::string&){return {};}
template<>std::list<ObjectGuid> AiObjectContext::Read(const std::string&){return possible;}
#define AI_VALUE(type,name) context->Read<type>(name)
struct PlayerbotAI {Player* bot;AiObjectContext context;unsigned castChecks=0;bool cc=true,real=false;
 std::map<ObjectGuid,Unit*> units;
 Player* GetBot(){return bot;}AiObjectContext* GetAiObjectContext(){return &context;}
 float GetRange(std::string){return 30;}bool IsTank(Player* p){return p->tank;}
 bool HasStrategy(std::string,BotState){return cc;}
 bool IsRealPlayer(){return real;}
 Unit* GetUnit(ObjectGuid id){return units[id];}
 bool IsSafe(Unit* u){return u&&bot->map==u->map&&bot->instance==u->instance;}
 bool HasMyAura(std::string,Unit* u){return u->ownAura;}
 bool CanCastSpell(std::string,Unit* t,unsigned,void*,bool,bool){++castChecks;return t->castable;}
};
struct {float sightDistance=70,mediumHealth=50,aoeRadius=10;} sPlayerbotAIConfig;
struct {bool IsAlive(Unit* t){return t->alive;}bool IsDistanceLessOrEqualThan(float a,float b){return a<=b;}
 float GetDistance2d(Unit* a,Unit* b){return std::abs(a->x-b->x);}
 float GetDistance2d(Unit* a,float x,float){return std::abs(a->x-x);}} sServerFacade;
struct RtiTargetValue {static int GetRtiIndex(std::string name){return name=="none"?-1:4;}};
struct ThreatManager {};
struct FindTargetStrategy {PlayerbotAI* ai;Unit* result=nullptr;FindTargetStrategy(PlayerbotAI* a):ai(a){}
 virtual void CheckAttacker(Unit*,ThreatManager*)=0;Unit* GetResult(){return result;}};
__SELECTOR__
struct CcTargetValue {
 PlayerbotAI* ai;Player* bot;AiObjectContext* context;std::string qualifier="polymorph";
 ObjectGuid Calculate();
 Unit* FindTarget(FindTargetStrategy* strategy){for(auto pair:ai->units)if(pair.second)strategy->CheckAttacker(pair.second,nullptr);return strategy->GetResult();}
};
// Garr assignment is exercised with full native-state fixtures in its own
// regression. This fixture exercises the ordinary polymorph selector.
bool GarrBanishAssignment(PlayerbotAI*,const std::string& spell,Unit*&){assert(spell=="polymorph");return false;}
bool domoOwns=false;Unit*domoTarget=nullptr;
bool MajordomoPolymorphAssignment(PlayerbotAI*,Unit*&target){target=domoTarget;return domoOwns;}
__CALCULATE__
int main(){
 Player bot;Group group;bot.group=&group;PlayerbotAI ai{&bot};Unit target;ai.context.marked=&target;ai.units[1]=&target;
 auto select=[&](){FindTargetForCcStrategy selector(&ai,"polymorph");selector.CheckAttacker(&target,nullptr);return selector.GetResult();};
 target.castable=false;assert(select()==nullptr); // BEFORE FIX: mark bypasses every native castability check
 target.castable=true;assert(select()==&target);assert(ai.castChecks>=2);
 // Repeated successful native casts cannot justify reapplying a companion's
 // existing control. Exercise the actual selector, including marked targets.
 for(unsigned map:{249u,309u,409u,469u,509u,531u,533u}){
  bot.map=target.map=map;target.controlled=true;
#ifdef MANGOSBOT_ZERO
  assert(!select());target.controlled=false;target.feared=true;assert(!select());
  ai.real=true;assert(select()==&target);ai.real=false;
#else
  assert(select()==&target);
#endif
  target.controlled=target.feared=false;assert(select()==&target);
 }
 for(unsigned map:{0u,1u,429u,489u,529u,30u}){bot.map=target.map=map;target.controlled=true;assert(select()==&target);}
 target.controlled=false;bot.map=target.map=409;
 target.health=10;target.dot=true;ai.context.current=&target;ai.context.rti=&target;
 assert(select()==&target); // preserve explicit mark precedence over automatic heuristics
 target.world=false;assert(select()==nullptr);target.world=true;
 target.alive=false;assert(select()==nullptr);target.alive=true;
 target.instance=2;assert(select()==nullptr);target.instance=1;
#ifndef MANGOSBOT_ZERO
 target.phase=2;assert(select()==nullptr);target.phase=1;
#endif
 bot.teleport=true;assert(select()==nullptr);bot.teleport=false;
 ai.context.marked=nullptr;ai.context.current=nullptr;ai.context.rti=nullptr;ai.context.rtiName="none";
 target.dot=false;target.health=100;assert(select()==&target); // normal auto-CC still available
 target.castable=false;assert(select()==nullptr);target.castable=true;
 target.dot=true;assert(select()==nullptr);target.dot=false;
 ai.context.current=&target;assert(select()==nullptr);ai.context.current=nullptr;
 ai.context.rti=&target;assert(select()==nullptr);ai.context.rti=nullptr;
 target.health=10;assert(select()==nullptr);target.health=100;
 bot.group=nullptr;assert(select()==nullptr);
 bot.group=&group;ai.context.marked=&target;
 Unit previous;previous.id=2;previous.ownAura=true;
 ai.units={{1,&target},{2,&previous}};ai.context.possible={1,2};CcTargetValue value{&ai,&bot,&ai.context};
 assert(value.Calculate()==0); // preserve one owned CC at a time
 previous.alive=false;assert(value.Calculate()==target.id);previous.alive=true;
 previous.world=false;assert(value.Calculate()==target.id);previous.world=true;
 previous.instance=2;assert(value.Calculate()==target.id);previous.instance=1;
#ifndef MANGOSBOT_ZERO
 previous.phase=2;assert(value.Calculate()==target.id);previous.phase=1;
#endif
 ai.context.possible={1,99};assert(value.Calculate()==target.id); // unresolved GUID
 domoOwns=true;assert(value.Calculate()==0); // owned empty assignment must not auto-CC
 domoTarget=&target;assert(value.Calculate()==target.id);domoOwns=false;
 bot.teleport=true;assert(value.Calculate()==0);bot.teleport=false;
 bot.alive=false;assert(value.Calculate()==0);
 std::cout<<"PASS: actual CC mark precedence with native castability, lifecycle and automatic exclusions\n";
}
'''.replace('__SELECTOR__',selector).replace('__CALCULATE__',calculate)
for expansion in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-cc-candidate-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{expansion}',
                        'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
