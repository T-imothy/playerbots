"""Actual Classic raid policy and movement admission; no realm/DB mutation."""
from pathlib import Path
import subprocess,tempfile,sys
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
if len(sys.argv)>1:source=Path(sys.argv[1]).read_text()
methods='\n'.join(block(source,'bool ClassicRaidPositionAction::'+name+'(')
                  for name in ('GetPlan','isUseful','ShouldReactionInterruptCast','Execute'))
receipt='void ClassicRaidPlanValue::RecordSapphironFormation(Unit*){}\nbool ClassicRaidPlanValue::OwnedSapphironTankStop(ClassicRaidPlan&){return false;}'
if 'void ClassicRaidPlanValue::RecordSapphironFormation(' in source:
 receipt=block(source,'void ClassicRaidPlanValue::RecordSapphironFormation(')+'\n'+block(source,'bool ClassicRaidPlanValue::OwnedSapphironTankStop(')
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
struct Unit;constexpr unsigned PATH_MOTION_TYPE=7;
constexpr unsigned IN_PROGRESS=1;
struct NativeInstance{unsigned state=IN_PROGRESS;unsigned GetData(unsigned id){assert(id==12);return state;}};
struct NativeMap{NativeInstance instance;NativeInstance*GetInstanceData(){return &instance;}};
struct Motion{unsigned type=PATH_MOTION_TYPE;unsigned GetCurrentMovementGeneratorType(){return type;}};
struct Spline{unsigned id=1;bool done=true;ai::encounter::Point end{};unsigned GetId(){return id;}bool Finalized(){return done;}auto FinalDestination(){return end;}};
struct Player{bool world=true,alive=true,combat=true,transfer=false,charmed=false,casting=false;
 NativeMap nativeMap;NativeMap*GetMap(){return &nativeMap;}
 unsigned map=533,instance=17;float x=0;bool melee=true;Motion motion;Spline spline;Spline*movespline=&spline;std::set<unsigned>auras;
 float GetPositionX(){return x;}float GetPositionY(){return 0;}float GetPositionZ(){return 0;}Motion*GetMotionMaster(){return &motion;}bool CanReachWithMeleeAttack(Unit*){return melee;}
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 bool IsBeingTeleported(){return transfer;}bool HasCharmer(){return charmed;}bool HasAura(unsigned id){return auras.count(id);}
 unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}void*GetGroup(){return this;}Guid GetObjectGuid(){return {1};}
 void*GetCharm(){return nullptr;}bool IsNonMeleeSpellCasted(bool){return casting;}
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+b*b+c*c);}void AttackStop(){}void*GetPet(){return nullptr;}
};
namespace ai {struct EncounterPosition{bool active=false;unsigned map=533,instance=17,spell=0;Guid boss,source;ai::encounter::Point destination{};};
struct ClassicRaidPlan{Guid boss{1},target;EncounterPosition position;bool emergency=false,holdDamage=false;};
bool EncounterMovementRequired(Player*,const encounter::Point&,float=1.5f);}
using namespace ai;
struct WorldPosition{WorldPosition(unsigned,float,float,float){}};
struct Unit{bool engaged=true;unsigned entry=15990;Guid GetObjectGuid(){return {1};}Player*victim=nullptr;Player*GetVictim(){return victim;}unsigned GetEntry(){return entry;}};
struct Value{virtual ~Value()=default;ClassicRaidPlan plan;ClassicRaidPlan Get(){return plan;}};
struct PlayerbotAI;struct ClassicRaidPlanValue:Value{PlayerbotAI*ai=nullptr;Player*bot=nullptr;Guid sapphironFormationBoss;unsigned sapphironFormationInstance=0,sapphironFormationSpline=0;void RecordSapphironFormation(Unit*);bool OwnedSapphironTankStop(ClassicRaidPlan&);};
struct Context{ClassicRaidPlanValue value;template<class T>Value*GetValue(const char*){return &value;}};
struct PositionEntry{void Set(float,float,float,unsigned){}};using PositionMap=std::map<std::string,PositionEntry>;
struct Event{};
struct PlayerbotAI{Player bot;Unit boss;Context context;PositionMap positions;bool real=false,special=false,move=true,valid=true,jumpAccepted=true,room=true,leader=true,route=true;unsigned moves=0,jumps=0,stops=0,admissions=0,interrupts=0;
 bool tank=false;PlayerbotAI(){context.value.ai=this;context.value.bot=&bot;}bool IsTank(Player*){return tank;}
 Player*GetBot(){return &bot;}bool IsRealPlayer(){return real;}Context*GetAiObjectContext(){return &context;}
 Unit*GetUnit(Guid guid){return guid.id==1?&boss:nullptr;}bool CanMove(){return move;}
 bool DoSpecificAction(const char*,Event,bool){++jumps;return jumpAccepted;}void StopMoving(){++stops;bot.spline.done=true;}};
#define AI_VALUE(type,name) ai->positions
struct Pet{Guid GetObjectGuid(){return {};}};
struct WorldPacket{WorldPacket(int){}template<class T>WorldPacket&operator<<(T){return *this;}};
constexpr int CMSG_PET_ACTION=0,ACT_COMMAND=0,COMMAND_FOLLOW=0;
// Pet-specific mutation branches are not part of this movement admission fixture.
__READY__
bool SpecialPosition(PlayerbotAI*a){return a->special;}
// Native Buru egg selection is independently exercised by buru_egg_regression.
bool BuruEggPhase(PlayerbotAI*,Unit*){return false;}Unit* BuruEgg(PlayerbotAI*,Unit*){return nullptr;}
bool Engaged(Player*,Unit*u){return u&&u->engaged;}
// Dedicated Gothik/CThun tests execute these native helpers. This movement
// fixture exercises other encounter plans with those policies inactive.
void* GothikClosedGate(PlayerbotAI*,Unit*){return nullptr;}
float CthunEyeBeamSpacing(PlayerbotAI*,Unit*){return 0;}
Player*pickupTank=nullptr;Player*SapphironPickupTank(PlayerbotAI*,Unit*){return pickupTank;}
bool NefariusWaveTarget(PlayerbotAI*,Unit*){return false;}
bool CthunPlanCurrent(PlayerbotAI*,const ClassicRaidPlan&){return false;}
Player*SuppressionLeader(PlayerbotAI*a){return a->leader?&a->bot:nullptr;}
bool SuppressionStationActive(PlayerbotAI*a){return a->room;}
bool SuppressionTrash(Unit*u){return u&&u->entry==12458;}
bool ValidateEncounterDestination(PlayerbotAI*a,EncounterPosition&,bool=true){return a->valid;}
struct ClassicRaidPositionAction{PlayerbotAI*ai;Player*bot;
 static bool GetPlan(PlayerbotAI*,ClassicRaidPlan&);bool isUseful();bool ShouldReactionInterruptCast()const;bool Execute(Event&);
 bool MoveAdmittedRaidEscape(WorldPosition){++ai->admissions;if(!ai->route)return false;++ai->moves;if(bot->casting){++ai->interrupts;bot->casting=false;}return true;}
 bool IsReaction(){return false;}bool MoveTo(unsigned,float,float,float,bool,bool,bool,bool){++ai->moves;return true;}};
__ARRIVAL__
__RECEIPT__
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
 // Native Sapphiron failure: reject repeated reposition attempts without
 // cancelling the current heal; successful native admission may move.
 brain.boss.entry=15989;brain.route=false;
#ifdef MANGOSBOT_ZERO
 for(unsigned i=0;i<11;++i){assert(!action.ShouldReactionInterruptCast());assert(!action.Execute(event)&&bot.casting&&brain.interrupts==0&&brain.moves==0);}
 brain.route=true;assert(action.Execute(event)&&!bot.casting&&brain.interrupts==1&&brain.moves==1);
 brain.moves=0;brain.interrupts=0;bot.casting=true;
#else
 assert(action.ShouldReactionInterruptCast());assert(action.Execute(event)&&brain.moves==1&&brain.admissions==0);brain.moves=0;
#endif
 brain.route=true;brain.boss.entry=15990;
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
 bot.map=469;plan.position.map=469;plan.position.spell=179784;plan.position.source={1};
 plan.position.destination={bot.x,0,0};brain.boss.entry=12458;brain.boss.victim=&bot;
 bot.spline.done=false;bot.spline.end={bot.x+15,0,0};const auto moves=brain.moves;
 assert(action.isUseful()&&action.Execute(event)&&brain.stops==1&&brain.moves==moves); // obsolete room leg stops at safe station
 assert(!action.isUseful());bot.spline.done=false;brain.room=false;assert(!action.isUseful());brain.room=true;
 plan.position.source={2};assert(!action.isUseful());plan.position.source={1};
 brain.leader=false;assert(!action.isUseful());plan.position.source={};assert(action.isUseful()); // missing leader current-station hold remains admitted
 brain.leader=true;assert(!action.isUseful());plan.position.source={1};
 plan.position.spell=12017;brain.boss.entry=12017;plan.position.destination={bot.x+10,0,0};assert(action.isUseful()); // actual Broodlord holder may reposition
 // Sapphiron tank takes aggro halfway through a previously admitted flank
 // route. Cancel only our exact native spline, before a cached flank plan can
 // rotate the boss further; no blanket cancellation of another movement.
 bot.map=533;bot.instance=17;bot.x=6;brain.boss.entry=15989;brain.boss.victim=nullptr;brain.tank=true;
 plan=ClassicRaidPlan();plan.position.active=true;plan.position.destination={20,0,0};
 bot.spline.id=42;bot.spline.done=false;bot.spline.end={20,0,0};bot.casting=false;
 assert(action.Execute(event));brain.boss.victim=&bot;
#ifdef MANGOSBOT_ZERO
 assert(action.isUseful());const unsigned oldMoves=brain.moves,oldStops=brain.stops;
 assert(action.Execute(event)&&brain.stops==oldStops+1&&brain.moves==oldMoves);assert(!action.isUseful());
 // The elected pickup tank must also release its own stale flank before
 // native stance/taunt actions; other/newer hazard splines stay protected.
 brain.boss.victim=nullptr;pickupTank=&bot;bot.spline.done=false;
 assert(action.isUseful());assert(action.Execute(event)&&brain.stops==oldStops+2);
 assert(!action.isUseful());pickupTank=nullptr;
 for(unsigned fault=0;fault<11;++fault){
  bot.spline.id=42;bot.spline.done=false;bot.motion.type=PATH_MOTION_TYPE;bot.instance=17;bot.map=533;
  brain.boss.entry=15989;brain.boss.victim=&bot;brain.boss.engaged=true;brain.valid=true;brain.tank=true;brain.move=true;bot.melee=true;bot.transfer=false;
  if(fault==0)bot.spline.id=43; // New blizzard escape must finish untouched.
  if(fault==1)bot.motion.type=99; // Native forced movement.
  if(fault==2)bot.instance=18;if(fault==3)brain.boss.victim=nullptr;
  if(fault==4)brain.valid=false;if(fault==5)brain.boss.engaged=false;
  if(fault==6)brain.tank=false;if(fault==7)bot.melee=false;
  if(fault==8)bot.transfer=true;if(fault==9)brain.move=false;if(fault==10)brain.boss.entry=15990;
  ClassicRaidPlan stop;assert(!brain.context.value.OwnedSapphironTankStop(stop));
 }
#else
 assert(!action.isUseful());
#endif
 {
  PlayerbotAI phase;phase.boss.entry=15929;phase.boss.victim=&phase.bot;
  auto&cached=phase.context.value.plan;cached.position.active=true;cached.position.spell=15929;
  ClassicRaidPlan result;
#ifdef MANGOSBOT_ZERO
  assert(ClassicRaidPositionAction::GetPlan(&phase,result));
  phase.bot.nativeMap.instance.state=0;assert(!ClassicRaidPositionAction::GetPlan(&phase,result));
  phase.bot.nativeMap.instance.state=IN_PROGRESS;phase.boss.engaged=false;assert(!ClassicRaidPositionAction::GetPlan(&phase,result));
#else
  assert(!ClassicRaidPositionAction::GetPlan(&phase,result));
#endif
 }
 std::cout<<"PASS raid policy/admission, native Thaddius tank phase, exact owned Sapphiron spline stop and other eras\n";
}
'''
# Strip only the pet-follow branch from Execute; separately tested in controller fixture/native compile.
start=methods.index('    if (plan.holdDamage)')
end=methods.index('    if (!EncounterMovementRequired',start)
methods=methods[:start]+methods[end:]
code=code.replace('__POLICY__',(root/'playerbot/strategy/ClassicRaidPolicy.h').as_posix()).replace('__GEOMETRY__',(root/'playerbot/strategy/EncounterGeometry.h').as_posix())
code=code.replace('__READY__',ready).replace('__ARRIVAL__',arrival).replace('__RECEIPT__',receipt).replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='classic-raid-adapters-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
