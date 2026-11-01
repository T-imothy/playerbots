"""The explicit mobile observer admits only native avoidance, never combat help."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
source=(Path(__file__).resolve().parents[1]/'playerbot/strategy/tests/TestStrategy.cpp').read_text()
code=r'''
#include <cassert>
#include <string>
#include <iostream>
#include <cmath>
using uint32=unsigned;
struct Player{bool combat=true,gm=false;unsigned map=409;
 bool IsInCombat(){return combat;}bool IsGameMaster(){return gm;}unsigned GetMapId(){return map;}};
struct AI{Player bot;Player*GetBot(){return &bot;}};
struct Action{std::string name;std::string getName(){return name;}};
namespace RaidLab{bool controlled=true;bool Controlled(Player*){return controlled;}}
__POLICY__
__PREREQUISITE__
__CLEAR_ROOM__
struct Observer{AI*ai;std::string scenario;
 __VALUE__
};
int main(){
 AI ai;Observer o{&ai,"raidlab_409_11982_leader_mobile_cleared_room"};Action a;
 const std::string isolated="raidlab_409_11982_leader_mobile_post_lucifron_cleared_room";
 for(unsigned entry:{12118u,12119u}){
  assert(RaidLabRemovedPrerequisite(409,11982,isolated,entry));
  assert(!RaidLabRemovedPrerequisite(409,11982,o.scenario,entry));
  assert(!RaidLabRemovedPrerequisite(469,11982,isolated,entry));
  assert(!RaidLabRemovedPrerequisite(409,12118,isolated,entry));
 }
 for(unsigned entry:{11982u,12056u,12057u,11658u})assert(!RaidLabRemovedPrerequisite(409,11982,isolated,entry));
 // Actual native Lucifron placement is outside the ambient-trash clearing
 // radius. Named prior-boss removal must not silently retain that encounter.
 assert(RaidLabClearRoomActor(409,11982,isolated,12118,158.54f));
 assert(RaidLabClearRoomActor(409,11982,isolated,12119,158.0f));
 assert(!RaidLabClearRoomActor(409,11982,o.scenario,12118,158.54f));
 assert(!RaidLabClearRoomActor(409,11982,isolated,11982,0));
 assert(!RaidLabClearRoomActor(409,11982,isolated,12056,100));
 assert(RaidLabClearRoomActor(409,11982,isolated,11658,149));
 assert(!RaidLabClearRoomActor(409,11982,isolated,11658,151));
 assert(!RaidLabClearRoomActor(409,11982,isolated,12118,NAN));
 const std::string jindo="raidlab_309_11380_leader_cleared_room";
 assert(RaidLabStagingAllowed(309,11380,"cleared-room"));
 assert(!RaidLabStagingAllowed(309,11380,"")&&!RaidLabStagingAllowed(469,11380,"cleared-room"));
 assert(!RaidLabStagingAllowed(309,15082,"cleared-room")&&!RaidLabStagingAllowed(0,11380,"cleared-room"));
 assert(RaidLabStagingAllowed(409,11982,"")&&RaidLabStagingAllowed(469,12017,"cleared-room"));
 for(unsigned entry:{14883u,14882u,14825u}){
  assert(RaidLabClearRoomActor(309,11380,jindo,entry,99));
  assert(!RaidLabClearRoomActor(309,11380,jindo,entry,100));
  assert(!RaidLabClearRoomActor(309,11380,"raidlab_309_11380_leader",entry,50));
  assert(!RaidLabClearRoomActor(309,14515,jindo,entry,50));
  assert(!RaidLabClearRoomActor(533,11380,jindo,entry,50));
 }
 for(unsigned entry:{11380u,14826u,14986u,14987u,14988u,15101u,15091u})
  assert(!RaidLabClearRoomActor(309,11380,jindo,entry,20));
 for(const char*name:{"molten core safe position","move away from hazard","boss cast safe position","enable molten core strategy"}){
  a.name=name;assert(o.GetValue(&a)==1);
  ai.bot.combat=false;assert(o.GetValue(&a)==0);ai.bot.combat=true;
  ai.bot.gm=true;assert(o.GetValue(&a)==0);ai.bot.gm=false;
  for(unsigned map:{0u,249u,469u,489u,533u,309u,509u,531u}){ai.bot.map=map;assert(o.GetValue(&a)==0);}ai.bot.map=409;
 }
 for(const char*name:{"frostbolt","heal","attack","pull","follow","flee","teleport","ossirian crystal","test::wrong","enable blackwing lair strategy"}){
  a.name=name;assert(o.GetValue(&a)==0);
 }
 a.name="test";assert(o.GetValue(&a)==1);assert(o.GetValue(nullptr)==1);
 o.scenario="raidlab_409_11982_leader_mobile_post_lucifron_cleared_room";
 a.name="move away from hazard";assert(o.GetValue(&a)==1);
 a.name="attack";assert(o.GetValue(&a)==0);
 a.name="move away from hazard";
 for(const char*scenario:{"raidlab_409_11982_leader_cleared_room","raidlab_409_11982_bot_cleared_room","raidlab_409_11982_leader_mobile","raidlab_469_11982_leader_mobile_cleared_room"}){
  o.scenario=scenario;assert(o.GetValue(&a)==0);
 }
 o.scenario="raidlab_533_15936_leader_mobile_cleared_room";ai.bot.map=533;
 for(const char*name:{"heigan dance","move away from hazard","boss cast safe position"}){a.name=name;assert(o.GetValue(&a)==1);}
 for(const char*name:{"attack","heal","frostbolt","pull","follow","flee","classic raid position","molten core safe position"}){a.name=name;assert(o.GetValue(&a)==0);}
 a.name="heigan dance";o.scenario="raidlab_533_15936_leader_cleared_room";assert(o.GetValue(&a)==0);
 o.scenario="raidlab_533_15936_leader_mobile_cleared_room";ai.bot.map=469;assert(o.GetValue(&a)==0);
 RaidLab::controlled=false;a.name="attack";assert(o.GetValue(&a)==1);
 std::cout<<"PASS explicit local mobile leader: native avoidance only, stationary and other contexts unchanged\n";
}
'''
code=code.replace('__POLICY__',block(source,'bool MobileRaidLeaderAction('))
setup=(Path(__file__).resolve().parents[1]/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=code.replace('__PREREQUISITE__',block(setup,'bool RaidLabRemovedPrerequisite('))
code=code.replace('__CLEAR_ROOM__',block(setup,'bool RaidLabRoomTrash(')+'\n'+block(setup,'bool RaidLabClearRoomActor(')+'\n'+block(setup,'bool RaidLabStagingAllowed('))
assert 'lucifron!=1 || protectors!=2' in setup
code=code.replace('__VALUE__',block(source,'float GetValue(').replace(' override',''))
with tempfile.TemporaryDirectory(prefix='raid-mobile-leader-') as directory:
 p=Path(directory);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
