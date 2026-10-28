"""Actual Classic raid policy and movement admission; no realm/DB mutation."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
methods='\n'.join(block(source,'bool ClassicRaidPositionAction::'+name+'(')
                  for name in ('GetPlan','isUseful','ShouldReactionInterruptCast','Execute'))
ready=block(source,'    bool Ready(')
arrival=block((root/'playerbot/strategy/values/EncounterPositionValue.cpp').read_text(),'bool ai::EncounterMovementRequired(')
code=r'''
#include <cassert>
#include <iostream>
#include <set>
#include <cmath>
#include <string>
#include <map>
#include "__POLICY__"
#include "__GEOMETRY__"
using uint32=unsigned;
struct Guid{unsigned id=0;bool IsEmpty()const{return !id;}bool operator==(Guid b)const{return id==b.id;}};
struct Spline{bool done=true;ai::encounter::Point end{};bool Finalized(){return done;}auto FinalDestination(){return end;}};
struct Player{bool world=true,alive=true,combat=true,transfer=false,charmed=false,casting=false;
 unsigned map=533,instance=17;float x=0;Spline spline;Spline*movespline=&spline;std::set<unsigned>auras;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 bool IsBeingTeleported(){return transfer;}bool HasCharmer(){return charmed;}bool HasAura(unsigned id){return auras.count(id);}
 unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}void*GetGroup(){return this;}
 void*GetCharm(){return nullptr;}bool IsNonMeleeSpellCasted(bool){return casting;}
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+b*b+c*c);}void AttackStop(){}void*GetPet(){return nullptr;}
};
namespace ai {struct EncounterPosition{bool active=false;unsigned map=533,instance=17,spell=0;ai::encounter::Point destination{};};
struct ClassicRaidPlan{Guid boss{1},target;EncounterPosition position;bool emergency=false,holdDamage=false;};
bool EncounterMovementRequired(Player*,const encounter::Point&,float=1.5f);}
using namespace ai;
struct Unit{bool engaged=true;unsigned entry=15990;Player*victim=nullptr;Player*GetVictim(){return victim;}unsigned GetEntry(){return entry;}};
struct Value{ClassicRaidPlan plan;ClassicRaidPlan Get(){return plan;}};
struct Context{Value value;template<class T>Value*GetValue(const char*){return &value;}};
struct PositionEntry{void Set(float,float,float,unsigned){}};using PositionMap=std::map<std::string,PositionEntry>;
struct Event{};
struct PlayerbotAI{Player bot;Unit boss;Context context;PositionMap positions;bool real=false,special=false,move=true,valid=true,jumpAccepted=true;unsigned moves=0,jumps=0;
 Player*GetBot(){return &bot;}bool IsRealPlayer(){return real;}Context*GetAiObjectContext(){return &context;}
 Unit*GetUnit(Guid guid){return guid.id==1?&boss:nullptr;}bool CanMove(){return move;}
 bool DoSpecificAction(const char*,Event,bool){++jumps;return jumpAccepted;}};
#define AI_VALUE(type,name) ai->positions
struct Pet{Guid GetObjectGuid(){return {};}};
struct WorldPacket{WorldPacket(int){}template<class T>WorldPacket&operator<<(T){return *this;}};
constexpr int CMSG_PET_ACTION=0,ACT_COMMAND=0,COMMAND_FOLLOW=0;
// Pet-specific mutation branches are not part of this movement admission fixture.
__READY__
bool SpecialPosition(PlayerbotAI*a){return a->special;}
bool Engaged(Player*,Unit*u){return u&&u->engaged;}
bool ValidateEncounterDestination(PlayerbotAI*a,EncounterPosition&,bool=true){return a->valid;}
struct ClassicRaidPositionAction{PlayerbotAI*ai;Player*bot;
 static bool GetPlan(PlayerbotAI*,ClassicRaidPlan&);bool isUseful();bool ShouldReactionInterruptCast()const;bool Execute(Event&);
 bool IsReaction(){return false;}bool MoveTo(unsigned,float,float,float,bool,bool,bool,bool){++ai->moves;return true;}};
__ARRIVAL__
__METHODS__
int main(){using namespace ai::classicraid;
 for(unsigned map:{249u,309u,469u,509u,531u,533u})assert(Map(map));
 for(unsigned map:{0u,1u,409u,489u,529u,30u,532u,603u,631u})assert(!Map(map));
 assert(Boss(249,10184)&&Boss(469,11583)&&Boss(309,14834)&&Boss(509,15339)&&Boss(531,15727)&&Boss(533,15990));
 assert(!Boss(409,11982)&&!Boss(531,11982));
#ifdef MANGOSBOT_TWO
 assert(Boss(533,30549)&&HorsemanMark(30549)==28834);
#else
 assert(!Boss(533,30549)&&HorsemanMark(30549)==0);
#endif
 assert(AddPriority(15953,16506,true,false)==0); // native Classic worshipper reserved for Embrace
 assert(AddPriority(15953,16505,false,false)>0); // native follower killed first
 assert(AddPriority(15932,16360,false,false)==0&&AddPriority(15932,16360,false,true)>0);
 assert(AddPriority(15990,16428,false,false)>AddPriority(15990,16427,false,false));
 assert(HorsemanMark(16062)==28834);
 unsigned marks[4]={3,0,0,0};assert(ReliefCorner(marks,4,0)==1);
 marks[1]=3;assert(ReliefCorner(marks,4,0)==2);marks[2]=marks[3]=3;assert(ReliefCorner(marks,4,0)==-1);
 marks[0]=0;assert(ReliefCorner(marks,4,3)==0);assert(ReliefCorner(marks,4,-1)==-1);
 assert(EggZone(-36,-164,-90)&&EggZone(-34,-262,-90));
 assert(!EggZone(-36,-170.1f,-90)&&!EggZone(-36,-164,-80));
 for(unsigned id:{16062u,16063u,16064u,16065u}){float x,y;assert(Corner(id,x,y));
 assert(!((x>2577.3f&&y<-3024)||(x>2585.9f&&y<-3015.1f)||(x>2594.6f&&y<-3006.7f)));}
 float x1,y1,x2,y2;Corner(16063,x1,y1);Corner(16065,x2,y2);assert(std::hypot(x1-x2,y1-y2)>50);
 PlayerbotAI brain;auto&bot=brain.bot;auto&plan=brain.context.value.plan;plan.position.active=true;plan.position.destination={10,0,0};
 ClassicRaidPositionAction action{&brain,&bot};Event event;
 assert(action.isUseful());bot.casting=true;assert(!action.Execute(event)&&brain.moves==0); // preserve ordinary casts/channels
 assert(!action.ShouldReactionInterruptCast());plan.emergency=true;assert(action.ShouldReactionInterruptCast());
 assert(action.Execute(event)&&brain.moves==1);bot.casting=false;bot.x=10;assert(!action.isUseful());
 bot.spline.done=false;bot.spline.end={10,0,0};assert(!action.isUseful()); // facing-only/arrived spline
 bot.spline.end={20,0,0};assert(action.isUseful());bot.spline.done=true;
 plan.emergency=false;bot.x=0;brain.special=true;assert(!action.isUseful());brain.special=false;
 brain.boss.engaged=false;assert(!action.Execute(event));brain.boss.engaged=true;
 brain.boss.victim=&bot;assert(!action.isUseful());brain.boss.victim=nullptr;
 brain.boss.victim=&bot;brain.boss.entry=12460;plan.position.spell=12460;assert(action.isUseful());
 brain.boss.victim=nullptr;brain.boss.entry=15990;plan.position.spell=0;
 plan.position.instance=18;assert(!action.isUseful());plan.position.instance=17;
 bot.map=409;assert(!action.isUseful());bot.map=533;bot.transfer=true;assert(!action.isUseful());bot.transfer=false;
 bot.alive=false;assert(!action.isUseful());bot.alive=true;brain.real=true;assert(!action.isUseful());brain.real=false;
 brain.valid=false;assert(!action.Execute(event));brain.valid=true;
 plan.boss={2};plan.emergency=true;assert(!action.isUseful()); // missing boss cannot revive stale urgent plan
 plan.boss={};assert(!action.isUseful());bot.auras.insert(28832);assert(action.isUseful());bot.auras.clear();
 plan.boss={1};plan.emergency=false;plan.position.spell=15928;assert(action.Execute(event)&&brain.jumps==1&&brain.moves==1);
 brain.jumpAccepted=false;assert(!action.Execute(event)&&brain.jumps==2&&brain.moves==1); // native rejected trajectory is not a teleport/move success
 for (unsigned map : {249u,309u,469u,509u,531u,533u,409u,532u,631u}) {
  bot.map=map;
#ifdef MANGOSBOT_ZERO
  assert(Ready(&brain)==Map(map));
#elif defined(MANGOSBOT_ONE)
  assert(Ready(&brain)==(map==249||map==309||map==469||map==533));
#else
  assert(Ready(&brain)==(map==309||map==469||map==533));
#endif
 }
 std::cout<<"PASS actual Classic raid scope, native target/mark policy, movement/cast and lifecycle admission\n";
}
'''
# Strip only the pet-follow branch from Execute; separately tested in controller fixture/native compile.
start=methods.index('    if (plan.holdDamage)')
end=methods.index('    if (!EncounterMovementRequired',start)
methods=methods[:start]+methods[end:]
code=code.replace('__POLICY__',(root/'playerbot/strategy/ClassicRaidPolicy.h').as_posix()).replace('__GEOMETRY__',(root/'playerbot/strategy/EncounterGeometry.h').as_posix())
code=code.replace('__READY__',ready).replace('__ARRIVAL__',arrival).replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='classic-raid-adapters-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
