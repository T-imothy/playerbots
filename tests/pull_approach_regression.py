"""Execute extracted production pull methods against movement/cast outcomes.

This checks decision sequencing, not native pathfinding or an in-game Uldaman run.
Run from a Visual Studio developer shell; pass a source checkout to compare revisions.
"""
from pathlib import Path
import subprocess, tempfile, sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
def extract(rel, signature):
    s = (root/rel).read_text()
    start = s.index(signature)
    pos = s.index('{', start) + 1
    depth = 1
    while depth:
        depth += (s[pos] == '{') - (s[pos] == '}')
        pos += 1
    return s[start:pos]

code = r'''
#include <cassert>
#include <string>
using time_t = long long;
time_t now = 100;
time_t time(std::nullptr_t) { return now; }
struct Unit {
 bool alive=true,world=true,combat=false,los=false,moving=true,casting=false;
 float distance=25;
 bool IsAlive(){return alive;} bool IsInWorld(){return world;}
 bool IsInCombat(){return combat;} float GetDistance(Unit*){return distance;}
 bool IsInMap(Unit*){return true;} bool IsNonMeleeSpellCasted(bool){return casting;}
 bool CanReachWithMeleeAttack(Unit* u){return u->distance<=5;}
};
using Player=Unit;
struct Event {};
struct PlayerbotAI {
 Player* bot; Unit* selected=nullptr; bool castSucceeds=true; int stopped=0,attempts=0;
 bool IsMelee(Player*){return true;}
 void StopMoving(){bot->moving=false;++stopped;}
 bool DoSpecificAction(const std::string&, Event&, bool){++attempts;return castSucceeds;}
};
struct Facade {
 bool isMoving(Player* p){return p->moving;}
 bool IsWithinLOSInMap(Player* p,Unit*){return p->los;}
} sServerFacade;
struct PullStrategy {
 static PullStrategy* active; Unit* target=nullptr;
 bool pending=false,issued=false; time_t started=100;
 static PullStrategy* Get(PlayerbotAI*){return active;}
 Unit* GetTarget()const{return target;}
 bool HasTarget()const{return target;}
 bool HasPullStarted()const{return started>0;}
 bool IsPullPendingToStart()const{return pending;}
 bool HasPullActionIssued()const{return issued;}
 time_t GetPullStartTime()const{return started;}
 int GetMaxPullTime()const{return 15;}
 float GetRange()const{return 30;}
 std::string GetPullActionName()const{return "shoot";}
 void OnPullActionIssued(){issued=true;}
 void RequestPull(Unit* u,bool reset=true){target=u;pending=true;if(reset)started=now;}
};
PullStrategy* PullStrategy::active=nullptr;
struct PullAction {
 PlayerbotAI* ai; Player* bot;
 void InitPullAction(){} Unit* GetTarget(){return PullStrategy::active->target;}
 bool Execute(Event&);
};
struct PullActionTrigger {PlayerbotAI* ai;Player* bot;bool IsActive();};
#define SET_AI_VALUE(T,N,V) ai->selected=V
'''
code += extract('playerbot/strategy/actions/PullActions.cpp', 'bool PullAction::Execute')
code += extract('playerbot/strategy/triggers/PullTriggers.cpp', 'bool PullActionTrigger::IsActive')
code += r'''
int main(){
 Player tank;Unit mob;PlayerbotAI ai{&tank};PullStrategy pull;pull.target=&mob;
 PullStrategy::active=&pull;PullAction action{&ai,&tank};PullActionTrigger trigger{&ai,&tank};Event event;
 // Inside shooting range behind a pillar: the pending approach must not be stopped.
 assert(trigger.IsActive());assert(!action.Execute(event));assert(ai.stopped==0&&ai.attempts==0);
 assert(pull.started==100&&!pull.issued);
 // A failed/consumed queued action must remain eligible without another player command.
 pull.pending=false;assert(trigger.IsActive());assert(trigger.IsActive());
 // Clear LOS while still moving: stop, then fire on the next decision.
 tank.los=true;assert(!action.Execute(event));assert(ai.stopped==1&&ai.attempts==0);
 pull.pending=false;assert(trigger.IsActive());
 // One transient native cast failure does not lose the request.
 ai.castSucceeds=false;assert(!action.Execute(event));assert(trigger.IsActive());
 ai.castSucceeds=true;assert(action.Execute(event));assert(pull.issued&&!trigger.IsActive());
 // No second shot while an accepted shot is pending; casting also suppresses retries.
 pull.issued=false;tank.casting=true;assert(!trigger.IsActive());tank.casting=false;
 now=115;assert(!trigger.IsActive());assert(pull.started==100);
 now=110;mob.alive=false;assert(!trigger.IsActive());mob.alive=true;mob.world=false;assert(!trigger.IsActive());
 mob.world=true;pull.target=nullptr;assert(!trigger.IsActive());pull.target=&mob;
 // Melee fallback remains usable for a warrior already in melee reach.
 mob.distance=3;assert(action.Execute(event));assert(pull.issued);
}
'''
with tempfile.TemporaryDirectory(prefix='pull-approach-') as tmp:
    folder=Path(tmp); (folder/'test.cpp').write_text(code)
    for era in ('MANGOSBOT_ZERO','MANGOSBOT_ONE','MANGOSBOT_TWO'):
        built=subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/D'+era,'test.cpp','/Fe:test.exe'],cwd=folder,capture_output=True,text=True)
        if built.returncode: raise RuntimeError(built.stdout+built.stderr)
        subprocess.run([str(folder/'test.exe')],cwd=folder,check=True)
print('PASS: all eras; blocked LOS preserves approach, transient failure retries, no duplicate accepted shot, original deadline, invalid targets, melee fallback.')
