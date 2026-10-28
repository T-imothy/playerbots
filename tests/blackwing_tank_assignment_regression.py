"""Exercise the production BWL tank branch separately from DPS marking."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/BlackwingLairDungeonActions.cpp').read_text()
target=block(source,'Unit* BlackwingLairPriorityTargetAction::GetTarget(')
branch=block(target,'if (ai->IsTank(bot))')
methods=block(source,'bool BwlMember(')+'\n'+block(source,'unsigned BwlAddPriority(')
code=r'''
#include <algorithm>
#include <cassert>
#include <iostream>
#include <list>
#include <map>
#include <vector>
using uint32=unsigned;using ObjectGuid=unsigned;
struct PlayerbotAI;struct Group;
struct Unit{virtual ~Unit(){}unsigned guid=0,entry=0;bool world=true,alive=true,combat=true,cc=false;unsigned instance=1;Unit* victim=nullptr;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return false;}
 unsigned GetObjectGuid(){return guid;}unsigned GetEntry(){return entry;}Unit* GetVictim(){return victim;}
 bool IsInMap(Unit* b){return b&&b->instance==instance;}float GetDistance(Unit*){return 10;}};
struct Player:Unit{bool tank=true,transfer=false;Group* group=nullptr;PlayerbotAI* brain=nullptr;
 Group* GetGroup(){return group;}bool IsBeingTeleported(){return transfer;}PlayerbotAI* GetPlayerbotAI(){return brain;}};
struct GroupReference{Player* p;GroupReference* n=nullptr;Player* getSource(){return p;}GroupReference* next(){return n;}};
struct Group{GroupReference* first;GroupReference* GetFirstMember(){return first;}};
std::list<ObjectGuid> targets;std::map<ObjectGuid,Unit*> units;
struct PlayerbotAI{Player* bot;bool real=false;bool IsRealPlayer(){return real;}bool IsTank(Player* p){return p&&p->tank;}
 Unit* GetUnit(ObjectGuid id){return units[id];}};
#define AI_VALUE(type,name) targets
__METHODS__
Unit* choose(PlayerbotAI* ai){Player* bot=ai->bot;
 auto valid=[bot](Unit* u){return u&&u->world&&u->alive&&u->combat&&!u->cc&&bot->IsInMap(u);};
 bool broodlordActive=false;for(auto id:targets)if(valid(units[id])&&units[id]->entry==12017)broodlordActive=true;
 __BRANCH__
 return nullptr;
}
int main(){
 Player a,b,healer; a.guid=1;b.guid=2;healer.guid=3;healer.tank=false;
 PlayerbotAI aa{&a},bb{&b};a.brain=&aa;b.brain=&bb;
 GroupReference r3{&healer},r2{&b,&r3},r1{&a,&r2};Group group{&r1};a.group=b.group=healer.group=&group;
 Unit x,y,boss;x.guid=10;x.entry=12468;x.victim=&healer;y.guid=11;y.entry=12461;y.victim=&healer;
 boss.guid=12;boss.entry=12435;units={{10,&x},{11,&y},{12,&boss}};targets={11,10};
 assert(choose(&aa)==&x&&choose(&bb)==&y);
 x.victim=&a;a.victim=&x;assert(choose(&aa)==&x&&choose(&bb)==&y);
 y.victim=&b;b.victim=&y;assert(choose(&aa)==&x&&choose(&bb)==&y);
 y.cc=true;assert(!choose(&bb));y.cc=false;
 b.alive=false;y.victim=&healer;assert(choose(&aa)==&y);b.alive=true;
 targets={12,10,11};boss.victim=&a;a.victim=&boss;x.victim=&healer;
 assert(choose(&aa)==&boss&&choose(&bb)==&x);
 boss.alive=false;assert(choose(&aa)!=&boss);boss.alive=true;
 for(unsigned entry:{12435u,13020u,12017u,11983u,14601u,11981u,14020u,11583u}){
 boss.entry=entry;assert(choose(&aa)==&boss);}
 boss.victim=nullptr;a.victim=nullptr;x.victim=&a;y.victim=&b;
 bb.real=true;assert(choose(&aa)==&x); // human holder is not stolen
 boss.entry=12017;boss.victim=&a;a.victim=&boss;x.entry=14022;y.entry=14023;
 assert(choose(&aa)==&boss&&!choose(&bb)); // spare tanks don't chase endlessly respawning whelps
 assert(BwlAddPriority(12468)>BwlAddPriority(13996));
 std::cout<<"PASS BWL split adds, preserved holders, all eight bosses, CC, death and human tank ownership\n";
}
'''.replace('__METHODS__',methods).replace('__BRANCH__',branch)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='bwl-tanks-') as folder:
  tmp=Path(folder);(tmp/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
  subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
