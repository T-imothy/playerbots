"""Execute the scoped Ebonroc tank formation helper; native retest still required."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
helper=block(source,'    bool EbonrocTankFormation(')
code=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
struct Point{float x=0,y=0,z=0;};
struct Unit{unsigned map=469,instance=1,entry=14601,id=1,group=1;bool player=false,alive=true,engaged=true,tank=false,world=true;
 float x=0,y=0,z=0,reach=2;Unit*victim=nullptr;
 unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}unsigned GetEntry(){return entry;}unsigned GetObjectGuid(){return id;}
 bool IsPlayer(){return player;}Unit*GetVictim(){return victim;}float GetCombatReach(){return reach;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetAngle(Unit*u){return std::atan2(u->y-y,u->x-x);}
};
using Player=Unit;
struct EncounterPosition{bool active=false;unsigned map=0,instance=0,boss=0,source=0;Point destination;};
struct ClassicRaidPlan{EncounterPosition position;};
struct PlayerbotAI{Player*bot;bool path=true;unsigned validations=0;Player*GetBot(){return bot;}bool IsTank(Player*p){return p->tank;}};
bool Member(Player*b,Player*p){return p->world&&p->alive&&b->map==p->map&&b->instance==p->instance&&b->group==p->group;}
bool Engaged(Player*b,Unit*u){return u->world&&u->alive&&u->engaged&&b->map==u->map&&b->instance==u->instance;}
bool EncounterMovementRequired(Player*b,Point p){return std::hypot(b->x-p.x,b->y-p.y)>1.5f;}
bool ValidateEncounterDestination(PlayerbotAI*a,EncounterPosition&p){++a->validations;return a->path&&p.active&&p.map==a->bot->map&&p.instance==a->bot->instance;}
__HELPER__
int main(){Player incoming,active;Unit boss,other;incoming.player=active.player=true;incoming.tank=active.tank=true;
 incoming.id=2;active.id=3;incoming.x=-3;active.x=3;boss.victim=&active;PlayerbotAI ai{&incoming};ClassicRaidPlan plan;
#ifdef MANGOSBOT_ZERO
 assert(EbonrocTankFormation(&ai,&boss,&boss,plan)&&plan.position.active);
 assert(plan.position.destination.x==3&&plan.position.destination.y==0&&plan.position.source==3);
 incoming.x=3;plan={};assert(EbonrocTankFormation(&ai,&boss,&boss,plan)&&!plan.position.active);
 incoming.x=-3;ai.path=false;plan={};assert(EbonrocTankFormation(&ai,&boss,&boss,plan)&&!plan.position.active);ai.path=true;
 boss.victim=&incoming;assert(EbonrocTankFormation(&ai,&boss,&boss,plan)&&!plan.position.active);boss.victim=&active;
 incoming.tank=false;assert(!EbonrocTankFormation(&ai,&boss,&boss,plan));incoming.tank=true;
 assert(!EbonrocTankFormation(&ai,&boss,&other,plan));
 active.tank=false;assert(!EbonrocTankFormation(&ai,&boss,&boss,plan));active.tank=true;
 active.group=2;assert(!EbonrocTankFormation(&ai,&boss,&boss,plan));active.group=1;
 boss.entry=11981;assert(!EbonrocTankFormation(&ai,&boss,&boss,plan));boss.entry=14601;
 boss.engaged=false;assert(!EbonrocTankFormation(&ai,&boss,&boss,plan));boss.engaged=true;
 incoming.map=409;assert(!EbonrocTankFormation(&ai,&boss,&boss,plan));
#else
 assert(!EbonrocTankFormation(&ai,&boss,&boss,plan)&&!plan.position.active&&ai.validations==0);
#endif
 std::cout<<"PASS Ebonroc same-facing tank station, role/target/group/path and expansion scope\n";
}
'''.replace('__HELPER__',helper)
assert 'if (EbonrocTankFormation(ai,boss,target,plan)) return plan;' in source
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='ebonroc-station-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
