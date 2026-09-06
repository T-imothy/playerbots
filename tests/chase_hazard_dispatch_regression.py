"""Execute the actual chase hazard branch, including its native-chase fallback boundary."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

repo=Path(__file__).resolve().parents[1]
chase=block((repo/'playerbot/strategy/actions/MovementActions.cpp').read_text(),'bool MovementAction::ChaseTo(')
start=chase.index('    MotionMaster& mm =')
end=chase.index('    if (bot->GetMotionMaster()->GetCurrentMovementGeneratorType()',start)
code=r'''
#include <cassert>
#include <iostream>
#include <list>
#include <vector>
namespace G3D{struct Vector3{};}
enum{FORCED_MOVEMENT_RUN};
struct MotionMaster{unsigned paths=0,clears=0;void Clear(bool,bool){++clears;}void MovePath(std::vector<G3D::Vector3>&,int,bool,bool=false){++paths;}};
struct Player{MotionMaster mm;MotionMaster* GetMotionMaster(){return &mm;}unsigned GetMapId(){return 1;}};
struct WorldPosition{bool finite=true;std::vector<WorldPosition> getPathTo(const WorldPosition&,Player*)const{return {*this};}
 float getPathLength(const std::vector<WorldPosition>&){return 10;}std::vector<G3D::Vector3> toPointsArray(const std::vector<WorldPosition>&){return {{}};}};
struct HazardPosition{};
struct PlayerbotAI{std::list<HazardPosition> hazards;unsigned stops=0;void StopMoving(){++stops;}};
bool IsFiniteMovementPoint(const WorldPosition& p,unsigned){return p.finite;}
#define AI_VALUE(type,name) ai->hazards
struct Action{Player* bot;PlayerbotAI* ai;bool destinationValid=true,pathSafe=true,adjusted=false;unsigned adjustments=0,checks=0,fallbacks=0;
 bool IsValidPosition(const WorldPosition&,const WorldPosition&){return destinationValid;}
 bool GeneratePathAvoidingHazards(std::vector<WorldPosition>&){++adjustments;return adjusted;}
 bool BuildSafeHazardPath(std::vector<WorldPosition>&,Player*){++checks;return pathSafe;}
 void WaitForReach(float){}
 bool Execute(WorldPosition endPosition={}){WorldPosition botPosition;
 __BRANCH__
 ++fallbacks;return true;
 }};
int main(){
 Player bot;PlayerbotAI ai;Action action{&bot,&ai};
 assert(action.Execute());assert(action.fallbacks==1&&action.checks==0); // No hazards: native follow-up remains available.
 ai.hazards.push_back({});action.pathSafe=false;
 assert(!action.Execute());assert(action.fallbacks==1&&bot.mm.paths==0&&ai.stops==1); // Unmodified unsafe path cannot fall through.
 action.adjusted=true;assert(!action.Execute());assert(action.fallbacks==1&&ai.stops==2); // Failed adjusted route also stops.
 action.pathSafe=true;assert(action.Execute());assert(bot.mm.paths==1&&action.fallbacks==1);
 action.adjusted=false;assert(action.Execute());assert(bot.mm.paths==2); // Safe unchanged route still gets checked and dispatched.
 action.destinationValid=false;auto checks=action.checks;assert(!action.Execute());assert(action.checks==checks&&action.fallbacks==1);
 action.destinationValid=true;WorldPosition invalid;invalid.finite=false;assert(!action.Execute(invalid));assert(action.checks==checks);
 std::cout<<"PASS: chase rejects invalid/unsafe routes without fallback; dispatches checked adjusted and unchanged routes\n";
}
'''.replace('__BRANCH__',chase[start:end])
with tempfile.TemporaryDirectory(prefix='mantech-chase-hazard-') as folder:
    tmp=Path(folder);(tmp/'test.cpp').write_text(code)
    for era in ('ZERO','ONE','TWO'):
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
