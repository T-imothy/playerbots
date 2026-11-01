"""Exercise actual Twin role/planning functions, including long native path legs."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
methods=block(source,'struct TwinRoleState')+';\n'+'\n'.join(block(source,name) for name in
    ('unsigned TwinNearestSide(', 'Player* TwinSideHolder(', 'bool TwinRoles(', 'bool TwinRolePlan('))
code=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <vector>
using ObjectGuid=unsigned;
constexpr unsigned IN_PROGRESS=1,CLASS_WARLOCK=9,CLASS_HUNTER=3;
namespace encounter {struct Point{float x=0,y=0,z=0;};struct Circle{Point center;float radius;};
float Distance2d(Point a,Point b){return std::hypot(a.x-b.x,a.y-b.y);}}
struct Spline{bool done=true;encounter::Point end;bool Finalized(){return done;}encounter::Point FinalDestination(){return end;}};
struct Unit{unsigned guid=0,entry=0,instance=1;bool live=true,combat=true,stunned=false;float x=0,y=0,z=0;Unit*victim=nullptr;
 unsigned GetObjectGuid(){return guid;}unsigned GetEntry(){return entry;}bool IsInCombat(){return combat;}
 Unit*GetVictim(){return victim;}bool HasAura(unsigned id){assert(id==800);return stunned;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}
 float GetDistance(Unit*u){return GetDistance(u->x,u->y,u->z);}float GetAngle(Unit*u){return std::atan2(u->y-y,u->x-x);}
 float GetCombatReach(){return 2;}float GetObjectBoundingRadius(){return 1;}};
struct Creature:Unit{encounter::Point home;void GetRespawnCoord(float&a,float&b,float&c){a=home.x;b=home.y;c=home.z;}};
struct Instance{virtual ~Instance()=default;};
struct ScriptedInstance:Instance{unsigned state=1;Creature*physical=nullptr,*magic=nullptr;
 unsigned GetData(unsigned id){assert(id==6);return state;}Creature*GetSingleCreatureFromStorage(unsigned id,bool){return id==15275?physical:magic;}};
struct Map{Instance*instance=nullptr;Instance*GetInstanceData(){return instance;}};
struct Player:Unit{unsigned map=531,cls=1;bool tank=false,heal=false,ranged=false;Map*world=nullptr;Spline spline;Spline*movespline=&spline;
 unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}Map*GetMap(){return world;}unsigned getClass(){return cls;}};
struct PlayerbotAI{Player*bot=nullptr;bool ready=true,movable=true,special=false;std::vector<Player*>members;
 Player*GetBot(){return bot;}bool IsTank(Player*p){return p->tank;}bool IsHeal(Player*p){return p->heal;}bool IsRanged(Player*p){return p->ranged;}bool CanMove(){return movable;}};
bool Ready(PlayerbotAI*a){return a->ready;}bool Live(Player*p,Unit*u){return u&&u->live&&u->instance==p->instance;}
bool Engaged(Player*p,Unit*u){return Live(p,u)&&u->combat&&u->victim;}
std::vector<Player*>Members(PlayerbotAI*a,bool tanks=false){std::vector<Player*>out;for(auto p:a->members)if(p->live&&p->instance==a->bot->instance&&(!tanks||p->tank))out.push_back(p);std::sort(out.begin(),out.end(),[](auto a,auto b){return a->guid<b->guid;});return out;}
bool SpecialPosition(PlayerbotAI*a){return a->special;}float Range(PlayerbotAI*,Unit*){return 30;}float NativeEncounterSpellRadius(unsigned id){assert(id==568);return 10;}
struct EncounterPosition{bool active=false;unsigned map=0,instance=0,boss=0,source=0,spell=0;encounter::Point destination;};
struct ClassicRaidPlan{unsigned boss=0,target=0;EncounterPosition position;bool emergency=false,holdDamage=false;};
bool pathComplete=true,pathSafe=true,circleGeometry=false;unsigned paths=0;
struct WorldPosition {unsigned map;float x,y,z;WorldPosition(unsigned m,float a,float b,float c):map(m),x(a),y(b),z(c){}
 explicit WorldPosition(Player*p):WorldPosition(p->map,p->x,p->y,p->z){}
 float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}
 std::vector<WorldPosition>getPathStepFrom(WorldPosition from,Player*,bool)const{++paths;return {from,*this};}
 bool isPathTo(const std::vector<WorldPosition>&,float,float)const{return pathComplete;}};
bool ValidateEncounterDestination(PlayerbotAI*a,EncounterPosition&p){return pathComplete&&std::isfinite(p.destination.x)&&a->bot->GetDistance(p.destination.x,p.destination.y,p.destination.z)<=60;}
bool LocalCircleRoute(PlayerbotAI*a,const EncounterPosition&p,const std::vector<encounter::Circle>&circles){
 if(!pathSafe)return false;if(!circleGeometry)return true;
 for(auto c:circles){const float x=a->bot->x-c.center.x,y=a->bot->y-c.center.y;
 const float dx=p.destination.x-a->bot->x,dy=p.destination.y-a->bot->y,len=dx*dx+dy*dy;
 const float t=len?std::clamp(-(x*dx+y*dy)/len,0.0f,1.0f):0;
 const float start=std::hypot(x,y),closest=std::hypot(x+t*dx,y+t*dy);
 if(closest+0.01f<std::min(start,c.radius))return false;}return true;}
__METHODS__
int main(){
 Creature physical,magic;physical.guid=1;physical.entry=15275;physical.x=-80;physical.home={-80,0,0};
 magic.guid=2;magic.entry=15276;magic.x=80;magic.home={80,0,0};
 ScriptedInstance instance;instance.physical=&physical;instance.magic=&magic;Map map;map.instance=&instance;
 Player t0,t1,t2,w0,w1,h0,h1,mage,hunter;PlayerbotAI ai;unsigned id=10;
 for(auto p:{&t0,&t1,&t2,&w0,&w1,&h0,&h1,&mage,&hunter}){p->guid=id++;p->world=&map;ai.members.push_back(p);}
 for(auto p:{&t0,&t1,&t2})p->tank=true;
 for(auto p:{&w0,&w1}){p->cls=CLASS_WARLOCK;p->ranged=true;}
 h0.heal=h1.heal=h0.ranged=h1.ranged=true;mage.ranged=hunter.ranged=true;mage.cls=8;hunter.cls=CLASS_HUNTER;
 physical.victim=&t0;magic.victim=&w1;
 auto roles=[&](Player*p){ai.bot=p;TwinRoleState s;assert(TwinRoles(&ai,s));return s;};
 auto s=roles(&t0);assert(s.physicalHolder==&t0&&s.magicalHolder==&w1&&s.side==0&&s.reserved);
 assert(roles(&w1).side==1);assert(roles(&h0).side==0&&roles(&h1).side==1);
 assert(roles(&hunter).side==0&&roles(&mage).side==1);
 // Native teleport exchanges bosses while the holder teams stay on their side.
 physical.x=80;magic.x=-80;s=roles(&t1);assert(s.physicalHolder==&t1&&s.magicalHolder==&w0&&s.side==1);
 assert(roles(&w1).reserved&&roles(&w1).side==1);
 // A sole surviving holder follows the duty rather than remaining assigned to an empty side.
 t1.live=t2.live=false;w1.live=false;s=roles(&t0);assert(s.physicalHolder==&t0&&s.side==1);
 assert(roles(&w0).magicalHolder==&w0&&roles(&w0).side==0);
 t1.live=t2.live=w1.live=true;physical.x=-80;magic.x=80;
 // Same-side convergence assigns opposite recovery stations and holds DPS.
 physical.x=magic.x=0;physical.victim=&t0;magic.victim=&h0;
 ai.bot=&w1;w1.x=-70;ClassicRaidPlan plan;assert(TwinRolePlan(&ai,plan));
 assert(plan.target==magic.guid&&plan.position.active&&plan.position.destination.x>w1.x&&plan.position.destination.x-w1.x<=35);
 ai.bot=&mage;mage.x=-50;plan={};assert(TwinRolePlan(&ai,plan)&&plan.holdDamage);
 // Reserved tank relief must not chase the physical-immune Emperor.
 ai.bot=&t1;t1.x=50;plan={};assert(TwinRolePlan(&ai,plan)&&plan.holdDamage&&plan.target==0);
 physical.x=-80;magic.x=80;physical.victim=&t0;magic.victim=&w1;
 ai.bot=&hunter;hunter.x=-50;plan={};assert(TwinRolePlan(&ai,plan));
 assert(plan.target==physical.guid&&plan.position.active&&std::fabs(plan.position.destination.x+50)<0.01f);
 // Native failure: the assigned warlock has threat but stops at casting range
 // on the wrong side. Damage must yield to its admitted separation route.
 ai.bot=&w1;w1.x=-60;plan={};assert(TwinRolePlan(&ai,plan));
 assert(plan.position.active&&plan.emergency&&plan.holdDamage);
 magic.victim=&h0;plan={};assert(TwinRolePlan(&ai,plan));
 assert(plan.position.active&&!plan.holdDamage); // acquire threat before dragging
 magic.victim=&w1;w1.x=60;plan={};assert(TwinRolePlan(&ai,plan));
 assert(plan.position.active&&!plan.emergency&&!plan.holdDamage); // cast at station
 w1.x=-60;pathSafe=false;plan={};assert(TwinRolePlan(&ai,plan));
 assert(!plan.position.active&&!plan.holdDamage);pathSafe=true; // no route, no damage deadlock
 // Existing valid native walking leg remains stable while its distant station is unchanged.
 ai.bot=&w1;w1.x=-60;w1.spline.done=false;w1.spline.end={-30,0,0};plan={};const unsigned before=paths;
 assert(TwinRolePlan(&ai,plan)&&plan.position.active&&plan.position.destination.x==-30&&paths==before);w1.spline.done=true;
 // Failed native path/hazard admission never creates a movement order.
 pathComplete=false;plan={};assert(TwinRolePlan(&ai,plan)&&!plan.position.active);pathComplete=true;
 pathSafe=false;plan={};assert(TwinRolePlan(&ai,plan)&&!plan.position.active);pathSafe=true;
 // Native failure: the assigned home lies beyond Vek'lor. Refusing that
 // inward path must still admit a local outward escape from Arcane Burst.
 circleGeometry=true;physical.x=-80;magic.x=0;w1.x=-4;w1.y=0;plan={};
 assert(TwinRolePlan(&ai,plan)&&plan.emergency&&plan.position.active);
 assert(plan.position.destination.x<0&&magic.GetDistance(plan.position.destination.x,plan.position.destination.y,plan.position.destination.z)>=14);
 assert(LocalCircleRoute(&ai,plan.position,{{{0,0,0},14}}));
 // Outside Burst, separation with held threat is still urgent. The tangent
 // stays native-safe and makes progress toward the assigned station.
 w1.x=-20;plan={};assert(TwinRolePlan(&ai,plan)&&plan.emergency&&plan.holdDamage&&plan.position.active);
 assert(encounter::Distance2d(plan.position.destination,{60,0,0})<80);
 circleGeometry=false;physical.x=-80;magic.x=80;w1.x=-60;
 ai.special=true;plan={};assert(TwinRolePlan(&ai,plan)&&!plan.position.active);ai.special=false;
 instance.state=0;s={};assert(!TwinRoles(&ai,s));instance.state=1;
 magic.instance=2;assert(!TwinRoles(&ai,s));magic.instance=1;magic.live=false;assert(!TwinRoles(&ai,s));magic.live=true;
 w1.map=409;assert(!TwinRoles(&ai,s));w1.map=531;ai.ready=false;assert(!TwinRoles(&ai,s));
 std::cout<<"PASS Twin holders, teleport sides, relief/death, caster/hunter separation, long native legs, retained paths and map/instance/phase guards\n";
}
'''.replace('__METHODS__',methods)
with tempfile.TemporaryDirectory(prefix='twin-roles-') as folder:
    p=Path(folder);(p/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=p,check=True)
    subprocess.run([str(p/'test.exe')],cwd=p,check=True)
