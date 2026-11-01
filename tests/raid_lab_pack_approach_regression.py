"""Actual local pack preflight checks the route to shooting range, not just its landing."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/tests/CommandRaidLab.cpp').read_text()
code=r'''
#include <cassert>
#include <algorithm>
#include <cmath>
#include <map>
#include <set>
#include <vector>
#include <limits>
#include <iostream>
#include <string>
using uint32=unsigned;
using ObjectGuid=unsigned;
struct Creature;struct Store{std::map<unsigned,Creature*>values;template<class T>auto begin(){return values.begin();}template<class T>auto end(){return values.end();}};
struct Map{Store store;Store&GetObjectsStore(){return store;}};
struct Player{float GetObjectBoundingRadius(){return .5f;}float GetCombatReach(){return 1.5f;}float GetCollisionHeight(){return 2;}};
struct Creature{unsigned guid;float x,y,z=0;Map*map;bool hostile=true,los=true,wander=false,patrol=false;float aggro=20,visibleDistance=1000;
 unsigned GetObjectGuid(){return guid;}Map*GetMap(){return map;}float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetAttackDistance(Player*){return aggro;}float GetCombatReach(){return 1.5f;}bool IsWithinLOS(float px,float,float,bool){return los&&std::fabs(px-x)<visibleDistance;}};
struct WorldPosition{float x,y,z=0;float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}};
bool RaidLabBodyPullRisk(Creature*c,Player*,bool){return c->hostile;}
bool RaidLabInsideWanderEnvelope(Creature*c,float,float,float,float){return c->wander;}
bool RaidLabInsidePatrolEnvelope(Creature*c,float,float,float,float){return c->patrol;}
'''+block(source,'float RaidLabPackApproachRange(')+'\n'+block(source,'bool RaidLabCoveredBossPull(')+'\n'+block(source,'bool RaidLabPackPullCorridor(')+r'''
int main(){
 Map map;Player reference,puller;Creature target{1,0,0,0,&map},neighbor{2,45,20,0,&map};
 assert(RaidLabCoveredBossPull(533,16028,"raidlab_533_16028_leader"));
 assert(RaidLabCoveredBossPull(533,16028,"raidlab_533_16028_bot"));
 assert(RaidLabCoveredBossPull(533,15954,"raidlab_533_15954_leader"));
 assert(RaidLabCoveredBossPull(533,15954,"raidlab_533_15954_bot"));
 assert(!RaidLabCoveredBossPull(533,15954,"raidlab_533_16028_leader"));
 assert(!RaidLabCoveredBossPull(533,15954,"raidlab_533_15954_leader_cleared_room"));
 assert(!RaidLabCoveredBossPull(409,16028,"raidlab_533_16028_leader"));
 assert(!RaidLabCoveredBossPull(533,15936,"raidlab_533_16028_leader"));
 assert(!RaidLabCoveredBossPull(533,16028,"raidlab_533_16028_leader_cleared_room"));
 map.store.values={{1,&target},{2,&neighbor}};std::set<unsigned>pack{1};
 std::vector<WorldPosition>direct{{0,0,0},{70,0,0}};
 auto admit=[&](const std::vector<WorldPosition>&path){return RaidLabPackPullCorridor(&target,&reference,&puller,30,pack,path);};
 assert(RaidLabPackApproachRange(30)==25&&RaidLabPackApproachRange(.5f)==.5f);
 assert(!RaidLabPackApproachRange(0)&&!RaidLabPackApproachRange(61)&&!RaidLabPackApproachRange(NAN));
 // A corridor that is safe at maximum shooting range may be unsafe at the
 // native ReachPullAction's five-yard movement margin.
 neighbor.x=7;neighbor.y=0;
 assert(admit(direct));
 assert(!RaidLabPackPullCorridor(&target,&reference,&puller,RaidLabPackApproachRange(30),pack,direct));
 neighbor.x=45;neighbor.y=20;
 // Landing70 is outside the neighboring aggro circle; crossing45 is not.
 assert(!admit(direct));
 std::vector<WorldPosition>opposite{{0,0,0},{-70,0,0}};assert(admit(opposite));
 neighbor.hostile=false;assert(admit(direct));neighbor.hostile=true;
 pack.insert(2);assert(admit(direct));pack.erase(2); // exact bound pack membership only
 neighbor.los=false;assert(admit(direct));neighbor.los=true;
 neighbor.x=0;neighbor.y=0;assert(admit(direct)); // stop at range, not at boss feet
 neighbor.patrol=true;assert(!admit(direct));neighbor.patrol=false;
 target.los=false;assert(!admit(direct));target.los=true;
 // Party waits behind a corner at70yd, while the tank can walk to a native
 // visible shooting position at30yd. The same corridor still protects packs.
 target.visibleDistance=31;assert(!target.IsWithinLOS(70,0,2,true));assert(admit(direct));
 neighbor.x=45;neighbor.y=20;assert(!admit(direct));assert(admit(opposite));
 target.visibleDistance=0;assert(!admit(opposite));target.visibleDistance=1000;
 assert(!RaidLabPackPullCorridor(&target,&reference,&puller,0,pack,direct));
 assert(!RaidLabPackPullCorridor(&target,&reference,&puller,61,pack,direct));
 assert(!RaidLabPackPullCorridor(&target,&reference,&puller,30,{},direct));
 assert(!admit({}));assert(!admit({{0,0,0},{1e30f,0,0}}));
 assert(!admit({{0,0,0},{std::numeric_limits<float>::quiet_NaN(),0,0}}));
 std::cout<<"PASS native pack approach: safe landing with unsafe corridor refused, valid alternate accepted, exact pack/LOS/patrol and bounded path guards\n";
}
'''
with tempfile.TemporaryDirectory(prefix='raid-pack-approach-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 r=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
 if r.returncode:print(r.stdout,r.stderr)
 r.check_returncode();subprocess.run([str(path/'test.exe')],cwd=path,check=True)
assert '!coveredEyePull && !ctx.raidLabPackId && !suppressionStart &&' in source
assert '(ctx.raidLabPackId || coveredBossPull) && !RaidLabPackPullCorridor' in source
assert 'if(coveredBossPull)pullMembers.insert(boss->GetObjectGuid())' in source
fight=block(source,'TestResult CommandRaidLabPack::Execute(')
assert fight.index('waiting.isPathTo(route,1.0f,2.0f)')<fight.index('RaidLab::Begin(')
assert '>=180000' in fight and 'Waiting for native patrol to return' in fight
reach=(root/'playerbot/strategy/actions/ReachTargetActions.h').read_text()
assert 'range = strategy->GetRange();' in reach and 'if (range > 5.0f) range -= 5.0f;' in reach
