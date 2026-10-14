"""Execute the production retry-readiness check through changing approach state."""
from pathlib import Path
import subprocess, tempfile, sys
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/Engine.cpp').read_text()
if '--before' in sys.argv:
    source=subprocess.check_output(['git','-C',str(root),'show','HEAD:playerbot/strategy/Engine.cpp'],text=True)
methods='\n'.join(block(source,m) for m in ('std::string Engine::GetFailureReadiness(', 'bool Engine::IsFailureBackedOff('))
code=r'''
#include <cassert>
#include <map>
#include <sstream>
#include <string>
#include <iostream>
using uint32=unsigned;using int32=int;
struct Unit{float x=0,y=0,z=0;float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}};
struct Player:Unit{unsigned power=0;unsigned GetPowerType(){return 0;}unsigned GetPower(unsigned){return power;}unsigned GetShapeshiftForm(){return 0;}};
struct PlayerbotAI{Player bot;bool move=false;Player*GetBot(){return &bot;}bool CanMove(){return move;}};
struct Event{};enum ActionResult{ACTION_RESULT_FAILED,ACTION_RESULT_IMPOSSIBLE};
struct Action{Unit*target=nullptr;virtual ~Action()=default;Unit*GetTarget(){return target;}};
struct MovementAction:Action{};
struct CastSpellAction:Action{bool native=false;bool isPossible(){return native;}};
bool IsExplicitPlayerCommand(Action*,const Event&){return false;}
struct WorldTimer{static unsigned getMSTime(){return 100;}};
struct Engine{PlayerbotAI*ai;struct Failure{unsigned retryAfter=5000;std::string readiness;};std::map<std::string,Failure>actionFailures;
 std::string GetFailureKey(Action*,const Event&,ActionResult)const{return "failure";}
 std::string GetFailureReadiness(Action*)const;bool IsFailureBackedOff(Action*,const Event&,ActionResult)const;
 void Remember(Action*a){actionFailures["failure"].readiness=GetFailureReadiness(a);}};
__METHODS__
int main(){PlayerbotAI ai;Unit enemy;Event event;MovementAction reach;reach.target=&enemy;Engine engine{&ai};
 engine.Remember(&reach);assert(engine.IsFailureBackedOff(&reach,event,ACTION_RESULT_FAILED));
 enemy.x=30;assert(!engine.IsFailureBackedOff(&reach,event,ACTION_RESULT_FAILED)); // arriving enemy wakes the previously failed approach
 engine.Remember(&reach);assert(engine.IsFailureBackedOff(&reach,event,ACTION_RESULT_FAILED));
 ai.bot.x=1;assert(!engine.IsFailureBackedOff(&reach,event,ACTION_RESULT_FAILED));
 engine.Remember(&reach);ai.move=true;assert(!engine.IsFailureBackedOff(&reach,event,ACTION_RESULT_FAILED)); // fear/root control restored
 engine.Remember(&reach);assert(engine.IsFailureBackedOff(&reach,event,ACTION_RESULT_FAILED)); // unchanged bad route remains bounded
 CastSpellAction cast;cast.target=&enemy;engine.Remember(&cast);assert(engine.IsFailureBackedOff(&cast,event,ACTION_RESULT_IMPOSSIBLE));
 cast.native=true;assert(!engine.IsFailureBackedOff(&cast,event,ACTION_RESULT_IMPOSSIBLE)); // native GCD readiness preserved
 engine.Remember(&cast);ai.bot.power=50;assert(!engine.IsFailureBackedOff(&cast,event,ACTION_RESULT_IMPOSSIBLE));
 Action ordinary;assert(engine.GetFailureReadiness(&ordinary).empty());
 engine.Remember(&reach);engine.actionFailures["failure"].retryAfter=99;assert(!engine.IsFailureBackedOff(&reach,event,ACTION_RESULT_FAILED));
 std::cout<<"PASS: actual approach retry readiness follows endpoints/control without removing bounded retry or native spell checks\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='movement-retry-readiness-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
