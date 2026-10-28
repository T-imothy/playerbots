"""Actual action bodies: an already-safe bot must cancel an old chase, not its heal."""
from pathlib import Path
import subprocess,sys,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
before='--before' in sys.argv
methods=[]
for name,path in [('MoltenCorePositionAction','MoltenCoreDungeonActions.cpp'),('MechanarPositionAction','MechanarDungeonActions.cpp'),('OnyxiaPositionAction','OnyxiasLairDungeonActions.cpp'),('BlackwingLairPositionAction','BlackwingLairDungeonActions.cpp'),('NaxxramasPositionAction','NaxxramasDungeonActions.cpp')]:
    source=(root/'playerbot/strategy/actions'/path).read_text()
    if before:
        source=subprocess.check_output(['git','-c','safe.directory='+root.as_posix(),'-C',str(root),'show',
            '88f43c09:playerbot/strategy/actions/'+path],text=True)
    for method in ['isUseful','Execute']+([] if before else ['ShouldReactionInterruptCast']):
        methods.append(block(source,'bool '+name+'::'+method+'('))
code=r'''
#include <cassert>
#include <cmath>
#include <vector>
#include <list>
#include <iostream>
constexpr int IDLE_MOTION_TYPE=0;
struct Point{float x=0,y=0,z=0;};
struct Guid{unsigned id=0;Guid(unsigned v=0):id(v){}bool IsEmpty()const{return !id;}operator unsigned()const{return id;}};
struct EncounterPosition{bool active=true,exclusive=true,groundOnly=false;unsigned map=1,boss=7,spell=0;Guid source;Point destination;};
struct Motion{int type=1;int GetCurrentMovementGeneratorType(){return type;}};
struct Spline{bool Finalized(){return true;}Point FinalDestination(){return {};}};
struct Player;struct Unit{unsigned GetEntry(){return 0;}bool IsInWorld(){return true;}bool IsAlive(){return true;}Player*GetVictim(){return nullptr;}float GetAngle(Player*){return 0;}float GetOrientation(){return 0;}};
struct Player{float x=0;bool stopped=true,casting=false;Motion motion;Spline* movespline=nullptr;
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+b*b+c*c);}
 bool IsNonMeleeSpellCasted(bool,bool=false,bool=false){return casting;}Guid GetObjectGuid(){return 1;}bool IsInMap(Unit*){return true;}
 bool IsStopped(){return stopped;}Motion* GetMotionMaster(){return &motion;}};
struct PlayerbotAI{Player bot;EncounterPosition plan;bool canMove=true,path=true,fresh=true;unsigned stops=0,moves=0;
 bool CanMove(){return canMove;}Player*GetBot(){return &bot;}Unit*GetUnit(unsigned){return nullptr;}bool IsRanged(Player*){return false;}bool IsHeal(Player*){return false;}
 void StopMoving(){++stops;bot.stopped=true;bot.motion.type=0;}};
struct Event{};
struct WorldPosition{WorldPosition(Player*){}float distance(const WorldPosition&)const{return 100;}};
using HazardPosition=std::pair<WorldPosition,float>;
void AppendMoltenCoreGroundHazards(PlayerbotAI*,std::list<HazardPosition>&){}
bool PlanRagnarosFormation(PlayerbotAI*,EncounterPosition&){return false;}
struct JumpAction{JumpAction(PlayerbotAI*){}void Qualify(const char*){}bool Execute(Event&){return false;}};
bool ValidateEncounterDestination(PlayerbotAI* ai,EncounterPosition&,bool=true){return ai->path;}
bool EncounterMovementRequired(Player* bot,Point p,float tolerance=1.5f){return bot->GetDistance(p.x,p.y,p.z)>tolerance||!bot->IsStopped()||bot->motion.type!=IDLE_MOTION_TYPE;}
namespace encounter{struct Circle{};bool OutsideCircles(Point,const std::vector<Circle>&){return true;}}
bool MechanarThreats(PlayerbotAI* ai,EncounterPosition& p,std::vector<encounter::Circle>&){p.boss=7;return ai->fresh;}
bool BlackwingLairBurstThreats(PlayerbotAI* ai,EncounterPosition&,std::vector<encounter::Circle>&){return ai->fresh;}
bool NaxxramasBurstThreats(PlayerbotAI* ai,EncounterPosition&,std::vector<encounter::Circle>&){return ai->fresh;}
bool MoltenCoreThreats(PlayerbotAI* ai,EncounterPosition&,std::vector<encounter::Circle>&){return ai->fresh;}
bool PlanMoltenCoreTrash(PlayerbotAI*,EncounterPosition&){return false;}
struct Base{PlayerbotAI* ai;Player* bot;Base(PlayerbotAI* a):ai(a),bot(&a->bot){}
 static bool GetPlan(PlayerbotAI* ai,EncounterPosition& p){p=ai->plan;return p.active;}
 bool MoveTo(unsigned,float,float,float,bool,bool,bool,bool){++ai->moves;return true;}
 void SetDuration(unsigned){}bool IsReaction(){return true;}};
struct MoltenCorePositionAction:Base{using Base::Base;bool isUseful();bool Execute(Event&);
#ifdef BEFORE
 bool ShouldReactionInterruptCast()const{return true;}
#else
 bool ShouldReactionInterruptCast()const;
#endif
};
struct MechanarPositionAction:Base{using Base::Base;bool isUseful();bool Execute(Event&);
#ifdef BEFORE
 bool ShouldReactionInterruptCast()const{return true;}
#else
 bool ShouldReactionInterruptCast()const;
#endif
};
struct OnyxiaPositionAction:Base{using Base::Base;bool isUseful();bool Execute(Event&);
#ifdef BEFORE
 bool ShouldReactionInterruptCast()const{return true;}
#else
 bool ShouldReactionInterruptCast()const;
#endif
};
struct BlackwingLairPositionAction:Base{using Base::Base;bool isUseful();bool Execute(Event&);
#ifdef BEFORE
 bool ShouldReactionInterruptCast()const{return true;}
#else
 bool ShouldReactionInterruptCast()const;
#endif
};
struct NaxxramasPositionAction:Base{using Base::Base;bool isUseful();bool Execute(Event&);
#ifdef BEFORE
 bool ShouldReactionInterruptCast()const{return true;}
#else
 bool ShouldReactionInterruptCast()const;
#endif
};
__METHODS__
template<class T>void check(){
 PlayerbotAI ai;T action(&ai);Event event;
 // An idle unit flag can coexist with an old chase generator.
 assert(action.isUseful());assert(!action.ShouldReactionInterruptCast());
 assert(action.Execute(event)&&ai.stops==1&&ai.moves==0);assert(!action.isUseful());
 ai.bot.stopped=false;assert(action.isUseful());assert(action.Execute(event)&&ai.stops==2);
 ai.bot.x=20;assert(action.isUseful()&&action.ShouldReactionInterruptCast());
 assert(action.Execute(event)&&ai.moves==1);
 ai.path=false;assert(!action.Execute(event)&&ai.moves==1);ai.path=true;
 ai.canMove=false;assert(!action.Execute(event));ai.canMove=true;
 ai.plan.active=false;assert(!action.isUseful()&&!action.ShouldReactionInterruptCast()&&!action.Execute(event));
}
int main(){check<MoltenCorePositionAction>();check<MechanarPositionAction>();check<OnyxiaPositionAction>();check<BlackwingLairPositionAction>();check<NaxxramasPositionAction>();
 PlayerbotAI ai;Event e;OnyxiaPositionAction onyxia(&ai);ai.plan.exclusive=false;
 assert(!onyxia.isUseful()&&!onyxia.Execute(e)&&ai.stops==0); // Flank guidance does not cancel chasing adds.
 ai.plan.exclusive=true;MechanarPositionAction mechanar(&ai);ai.fresh=false;
 assert(!mechanar.Execute(e)&&ai.stops==0); // No stop based on vanished hazards.
 std::cout<<"PASS: actual safe-point chase cancellation, stationary-heal preservation, movement and nonexclusive Onyxia guidance\n";
}
'''.replace('__METHODS__','\n'.join(methods))
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-safe-hold-') as folder:
        folder=Path(folder);(folder/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era]+(['/DBEFORE'] if before else [])+['test.cpp','/Fe:test.exe'],cwd=folder,check=True)
        subprocess.run([str(folder/'test.exe')],check=True)
