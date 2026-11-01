"""Execute the real Gothik owner selector through stun/recovery handoff."""
from pathlib import Path
import sys, tempfile, subprocess
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tests'))
from behavior_regression import block
source=(root/'playerbot/strategy/actions/NaxxramasRoleActions.cpp').read_text()
code=r'''
#include <algorithm>
#include <vector>
#include <cassert>
#include <cstdint>
#include <iostream>
#include "__POLICY__"
using namespace ai;
constexpr unsigned UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL=8;
struct Guid { uint64_t id; uint64_t GetRawValue()const{return id;} bool operator<(Guid b)const{return id<b.id;} };
struct PlayerbotAI;
struct Unit {
 uint64_t id=0; unsigned entry=0; float y=-10,hp=100; bool player=false,alive=true,tank=false,stunned=false;
 void* group=nullptr; Unit* victim=nullptr; PlayerbotAI* brain=nullptr;
 Guid GetObjectGuid(){return {id};} unsigned GetEntry(){return entry;} float GetPositionY(){return y;}
 float GetHealthPercent(){return hp;} bool IsPlayer(){return player;} bool IsAlive(){return alive;}
 Unit* GetVictim(){return victim;} void*GetGroup(){return group;}
 PlayerbotAI*GetPlayerbotAI(){return brain;} bool hasUnitState(unsigned){return stunned;}
};
using Player=Unit;struct GameObject{float GetPositionY(){return 0;}};
struct PlayerbotAI{Player*bot;bool human=false;Player*GetBot(){return bot;}bool IsRealPlayer(){return human;}bool IsTank(Player*p){return p->tank;}};
std::vector<Player*>members;
std::vector<Player*>Members(PlayerbotAI*,bool){return members;}
__HELPER__
int main(){
 int group;Player a,b,mage;PlayerbotAI aa{&a},bb{&b};GameObject gate;
 a.id=2;b.id=3;a.player=b.player=mage.player=true;a.tank=b.tank=true;
 a.group=b.group=mage.group=&group;a.brain=&aa;b.brain=&bb;members={&a,&b};
 Unit rider,trainee;rider.id=11;rider.entry=16126;rider.victim=&mage;
 trainee.id=12;trainee.entry=16124;trainee.victim=&a;std::vector<Unit*>adds{&trainee,&rider};
 // The GUID assignment normally elects B. When B is stunned, A starts rescue.
 b.stunned=true;assert(GothikTankTarget(&aa,&gate,adds)==&rider);a.victim=&rider;
 b.stunned=false;
 assert(GothikTankTarget(&aa,&gate,adds)==&rider); // recovery must not revoke the active pickup
 assert(GothikTankTarget(&bb,&gate,adds)!=&rider);
 b.victim=&rider;assert(GothikTankTarget(&aa,&gate,adds)==&rider);
 assert(GothikTankTarget(&bb,&gate,adds)!=&rider); // deterministic tie among two pursuers
 rider.victim=&b;
 assert(GothikTankTarget(&aa,&gate,adds)!=&rider); // actual other holder wins
 assert(GothikTankTarget(&bb,&gate,adds)==&rider);
 rider.victim=&mage;a.stunned=true;
 assert(GothikTankTarget(&bb,&gate,adds)==&rider); // lost-control rescuer cannot block relief
 a.stunned=false;a.y=10;b.victim=nullptr;
 assert(GothikTankTarget(&bb,&gate,adds)==&rider); // opposite-side pursuer cannot reserve our side's add
 a.y=-10;aa.human=true;assert(GothikTankTarget(&aa,&gate,adds)==nullptr);
 aa.human=false;a.victim=nullptr;b.victim=nullptr;
 assert(GothikTankTarget(&bb,&gate,adds)==&rider); // existing distribution when nobody is pursuing
 std::cout<<"Gothik rescue ownership passed\n";
}
'''
code=code.replace('__POLICY__',(root/'playerbot/strategy/ClassicRaidPolicy.h').as_posix())
code=code.replace('__HELPER__',block(source,'    Unit* GothikTankTarget('))
with tempfile.TemporaryDirectory(prefix='gothik-rescue-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_ZERO',str(p/'test.cpp'),'/Fe:'+str(p/'test.exe')],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],check=True)

