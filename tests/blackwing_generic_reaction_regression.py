"""The generic BWL flank action must preserve its admitted native movement and casts until Execute."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
movement='bool ClassicRaidPositionAction::ShouldReactionInterruptMovement('
has_movement=movement in source
methods=block(source,'bool ClassicRaidPositionAction::ShouldReactionInterruptCast(')
if has_movement:methods+='\n'+block(source,movement)
code=r'''
#include <cassert>
struct Player {unsigned map=469;unsigned GetMapId(){return map;}};
struct Unit{unsigned entry=15990;unsigned GetEntry(){return entry;}};
struct Position {int destination=1;unsigned spell=0;};struct ClassicRaidPlan {bool emergency=false;Position position;unsigned boss=1;};
struct AI {bool admitted=true;ClassicRaidPlan plan;Unit boss;Unit*GetUnit(unsigned id){return id?&boss:nullptr;}};
struct MovementAction {bool ShouldReactionInterruptMovement() const{return true;}};
bool EncounterMovementRequired(Player*,int destination){return destination!=0;}
struct ClassicRaidPositionAction:MovementAction {
 Player*bot;AI*ai;bool ShouldReactionInterruptCast() const;
 __MOVEMENT__
 bool GetPlan(AI* value,ClassicRaidPlan& p)const {p=value->plan;return value->admitted;}
};
__METHODS__
int main(){
 Player player;AI ai;ClassicRaidPositionAction action;action.bot=&player;action.ai=&ai;
 ai.plan.emergency=true;
#ifdef MANGOSBOT_ZERO
 assert(!action.ShouldReactionInterruptMovement());
 assert(!action.ShouldReactionInterruptCast());
#else
 assert(action.ShouldReactionInterruptMovement());assert(action.ShouldReactionInterruptCast());
#endif
 // Neither open world, dungeons, BGs nor other raid maps inherit this BWL fix.
 for(unsigned map:{0u,1u,30u,489u,529u,33u,409u,533u}) {
  player.map=map;assert(action.ShouldReactionInterruptMovement());assert(action.ShouldReactionInterruptCast());
  ai.plan.emergency=false;assert(!action.ShouldReactionInterruptCast());ai.plan.emergency=true;
 }
 // Twin holder relocation must not destroy an already admitted safe spline
 // before Execute can retain it. Scope this to the actual Twin plan.
 player.map=531;ai.plan.position.spell=7393;
#ifdef MANGOSBOT_ZERO
 assert(!action.ShouldReactionInterruptMovement());assert(!action.ShouldReactionInterruptCast());
#else
 assert(action.ShouldReactionInterruptMovement());assert(action.ShouldReactionInterruptCast());
#endif
 ai.plan.position.spell=123;assert(action.ShouldReactionInterruptMovement());assert(action.ShouldReactionInterruptCast());
 ai.plan.position.spell=7393;ai.admitted=false;assert(action.ShouldReactionInterruptMovement());assert(!action.ShouldReactionInterruptCast());
 player.map=533;ai.admitted=true;ai.boss.entry=15989;
#ifdef MANGOSBOT_ZERO
 assert(!action.ShouldReactionInterruptMovement()&&!action.ShouldReactionInterruptCast());
#else
 assert(action.ShouldReactionInterruptMovement()&&action.ShouldReactionInterruptCast());
#endif
 ai.plan.boss=0;assert(action.ShouldReactionInterruptMovement()&&action.ShouldReactionInterruptCast());
}
'''.replace('__MOVEMENT__','bool ShouldReactionInterruptMovement() const;' if has_movement else '').replace('__METHODS__',methods)
code='#include <initializer_list>\n'+code
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='bwl-generic-reaction-') as folder:
        path=Path(folder);(path/'test.cpp').write_text(code)
        result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
        if result.returncode:print(result.stdout,result.stderr)
        result.check_returncode();subprocess.run([str(path/'test.exe')],cwd=path,check=True)
print('PASS generic BWL reaction preserves movement/casts until checked path dispatch; other maps and eras unchanged')
