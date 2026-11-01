"""Exercise the real Onyxia movement action, including rejected route side effects."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/OnyxiasLairDungeonActions.cpp').read_text()
safety=(root/'playerbot/strategy/actions/MovementPathSafety.h').read_text()
code=r'''
#include <cassert>
#include <cmath>
#include <algorithm>
#include <list>
#include <vector>
#include <iostream>
using uint32=unsigned;
struct Point {float x=0,y=0,z=0;};
struct Player;
struct WorldPosition {unsigned map=249;float x=0,y=0,z=0;static std::vector<WorldPosition> path;
 WorldPosition()=default;WorldPosition(unsigned m,float a,float b,float c):map(m),x(a),y(b),z(c){}
 WorldPosition(Player*);
 unsigned getMapId()const{return map;}float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}
 auto getPathStepFrom(const WorldPosition&,Player*,bool normal)const{assert(normal);return path;}
 bool isPathTo(const std::vector<WorldPosition>& p,float xy,float zz)const{return !p.empty()&&p.back().map==map&&std::hypot(p.back().x-x,p.back().y-y)<xy&&std::fabs(p.back().z-z)<zz;}
 auto toPointsArray(const std::vector<WorldPosition>& p){return p;}
};
std::vector<WorldPosition> WorldPosition::path;
struct Spline {bool done=true;Point end;bool Finalized(){return done;}Point FinalDestination(){return end;}};
struct Motion {unsigned clears=0,routes=0;std::vector<WorldPosition> sent;
 void Clear(bool,bool){++clears;}void MovePath(const std::vector<WorldPosition>& p,int,bool,bool){++routes;sent=p;}};
struct Player {bool casting=false,transport=false;unsigned interrupts=0,stands=0;Spline spline;Spline*movespline=&spline;Motion motion;
 unsigned GetMapId(){return 249;}unsigned GetObjectGuid(){return 7;}bool GetTransport(){return transport;}
 bool IsNonMeleeSpellCasted(bool,bool=false,bool=false){return casting;}
 void InterruptNonMeleeSpells(bool){++interrupts;casting=false;}void SetStandState(int){++stands;}
 float GetDistance(float x,float y,float z){return std::sqrt(x*x+y*y+z*z);}Motion*GetMotionMaster(){return &motion;}
};
WorldPosition::WorldPosition(Player*){}
using HazardPosition=std::pair<WorldPosition,float>;
struct Store{std::list<HazardPosition> hazards;auto Get(){return hazards;}};
struct Context {Store value;template<class T>Store*GetValue(const char*){return &value;}};
namespace encounter {struct Circle{Point center;float radius;};}
struct EncounterPosition {unsigned map=249,spell=0,source=0;bool exclusive=true;Point destination{10,0,0};};
struct PlayerbotAI{bool canMove=true,valid=true,active=true;unsigned stops=0;EncounterPosition plan;Context context;
 bool CanMove(){return canMove;}Context*GetAiObjectContext(){return &context;}void StopMoving(){++stops;}};
bool ValidateEncounterDestination(PlayerbotAI*a,EncounterPosition&){return a->valid;}
bool EncounterMovementRequired(Player*,const Point&,float){return false;}
std::vector<encounter::Circle> breath;
bool OnyxiaBreathThreats(unsigned id,std::vector<encounter::Circle>& out){if(id!=17086)return false;out=breath;return !out.empty();}
bool RaidLabMovementResult(Player*,const char*,unsigned,bool result){return result;}
constexpr int UNIT_STAND_STATE_STAND=0,FORCED_MOVEMENT_RUN=1;
struct Event{};
struct MovementAction {static bool ShouldReactionInterruptMovement(){return true;}};
struct OnyxiaPositionAction {PlayerbotAI*ai;Player*bot;unsigned generic=0;
 static bool GetPlan(PlayerbotAI*a,EncounterPosition&p){p=a->plan;return a->active;}
 bool IsReaction(){return true;}void SetDuration(unsigned){}
 bool MoveTo(unsigned,float,float,float,bool,bool,bool,bool){++generic;return true;}
 bool Execute(Event&);
 bool ShouldReactionInterruptCast()const;bool ShouldReactionInterruptMovement()const;
};
'''
code+='\n'.join(block(safety,s) for s in ('inline bool IsFiniteMovementPoint(', 'inline bool IsHazardSafeSegment(', 'inline bool IsHazardSafeGroundProjection(', 'inline bool IsOnyxiaBreathSafeSegment('))
code+=block(source,'bool OnyxiaPositionAction::Execute(')
code+=block(source,'bool OnyxiaPositionAction::ShouldReactionInterruptCast(')
code+=block(source,'bool OnyxiaPositionAction::ShouldReactionInterruptMovement(')
code+=r'''
int main(){
 // Actual first-breath route rejected for healer 140255 in native trial
 // 171160278. The peripheral circle gets closer, but union penetration falls.
 std::list<HazardPosition> nativeBreath={
  {{249,-37.7285f,-188.617f,-88.0749f},31},{{249,-37.0673f,-195.759f,-87.7458f},31},
  {{249,-36.6117f,-202.685f,-85.6538f},31},{{249,-32.0816f,-214.917f,-88.3274f},31},
  {{249,-34.0457f,-224.715f,-85.5295f},31},{{249,-35.8053f,-232.029f,-87.7492f},31},
  {{249,-37.7439f,-243.668f,-88.2177f},31}};
 WorldPosition trapped(249,-34.8508f,-223.422f,-84.2187f),outward(249,-50.8349f,-224.135f,-85.0933f);
 assert(!IsHazardSafeSegment(trapped,outward,nativeBreath));
 assert(IsOnyxiaBreathSafeSegment(trapped,outward,nativeBreath));
 assert(!IsOnyxiaBreathSafeSegment(outward,trapped,nativeBreath));
 assert(!IsOnyxiaBreathSafeSegment({249,-80,-224,-85},{249,10,-224,-85},nativeBreath)); // outside-to-outside crossing
 assert(!IsOnyxiaBreathSafeSegment({249,-80,-224,-85},trapped,nativeBreath)); // re-entry
 assert(!IsOnyxiaBreathSafeSegment(trapped,{469,-60,-224,-85},nativeBreath)); // other map
 assert(!IsOnyxiaBreathSafeSegment(trapped,outward,{}));
 auto bad=nativeBreath;bad.front().second=NAN;assert(!IsOnyxiaBreathSafeSegment(trapped,outward,bad));
 bad=nativeBreath;bad.front().first.x=NAN;assert(!IsOnyxiaBreathSafeSegment(trapped,outward,bad));
 assert(!IsOnyxiaBreathSafeSegment({249,-34.0457f,-224.715f,-53},{249,-34.0457f,-224.715f,-85},nativeBreath,true)); // different floor
 Player bot;PlayerbotAI brain;OnyxiaPositionAction action{&brain,&bot};Event event;
 auto& path=WorldPosition::path;path={{249,0,0,0},{249,10,0,0}};
#ifdef MANGOSBOT_ZERO
 assert(!action.ShouldReactionInterruptMovement()&&!action.ShouldReactionInterruptCast());
 bot.casting=true;brain.plan.spell=18392;
 assert(!action.Execute(event)&&bot.interrupts==0&&bot.motion.routes==0); // ordinary spread waits for heal/channel
 brain.plan.source=7;brain.valid=false;assert(!action.Execute(event)&&bot.interrupts==0);
 brain.valid=true;path={{249,0,0,0},{249,5,0,0}};
 assert(!action.Execute(event)&&bot.interrupts==0); // incomplete route cannot stop a cast
 path={{249,0,0,0},{249,10,0,0}};brain.plan.spell=17086;breath={{{5,0,0},3}};
 assert(!action.Execute(event)&&bot.motion.routes==0&&bot.interrupts==0); // clear endpoint, unsafe middle
 breath={{{-1,0,0},3}}; // outward escape is valid
 assert(action.Execute(event)&&bot.motion.routes==1&&bot.interrupts==1&&action.generic==0);
 assert(bot.motion.sent.size()==path.size()&&bot.motion.sent.back().x==10);
 brain.context.value.hazards={{{249,5,0,0},2}};
 assert(!action.Execute(event)&&bot.motion.routes==1); // union escape cannot bypass ordinary hazards
 brain.context.value.hazards.clear();
 bot.spline.done=false;bot.spline.end={10,0,0};bot.casting=true;
 for(unsigned repeat=0;repeat<20;++repeat) {
  if(action.ShouldReactionInterruptMovement()){brain.StopMoving();bot.spline.done=true;}
  if(action.ShouldReactionInterruptCast())bot.InterruptNonMeleeSpells(false);
  assert(action.Execute(event)&&bot.motion.routes==1&&bot.interrupts==1);
 } // native reaction selection retains the same admitted spline across ticks
 assert(brain.stops==0);
 breath={{{5,0,0},3}};assert(!action.Execute(event)&&bot.motion.routes==1); // newly unsafe route not retained
 breath.clear();bot.spline.done=true;bot.transport=true;
 assert(!action.Execute(event)&&bot.interrupts==1&&bot.motion.routes==1);
 bot.transport=false;brain.canMove=false;assert(!action.Execute(event)&&bot.motion.routes==1);
#else
 assert(action.ShouldReactionInterruptMovement());
 assert(action.Execute(event)&&action.generic==1&&bot.motion.routes==0); // other versions unchanged
#endif
 std::cout<<"PASS actual Onyxia route admission, cast preservation, spline reuse and era isolation\n";
}
'''
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='ony-route-') as folder:
  path=Path(folder);(path/'test.cpp').write_text(code)
  result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
  if result.returncode:print(result.stdout,result.stderr)
  result.check_returncode()
  subprocess.run([str(path/'test.exe')],cwd=path,check=True)
