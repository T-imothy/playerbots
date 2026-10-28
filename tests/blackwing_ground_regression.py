"""Compile the production BWL hazard collector against native object interfaces."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
method = block((root/'playerbot/strategy/values/HazardsValue.cpp').read_text(),
               'void ai::AppendBlackwingGroundHazards(')
code = r'''
#include <cassert>
#include <cmath>
#include <list>
#include <vector>
#include <limits>
#include <iostream>
using uint32=unsigned;
enum {TYPEID_UNIT,TYPEID_DYNAMICOBJECT,DYNAMIC_OBJECT_AREA_SPELL=1};
struct WorldObject{virtual ~WorldObject()=default;unsigned type=TYPEID_UNIT,map=469,instance=1,phase=1;bool world=true;float x=0,y=0,z=0;
 bool IsInWorld(){return world;}unsigned GetTypeId(){return type;}float GetPositionZ(){return z;}};
struct Unit:WorldObject{bool charmed=false;bool HasCharmer(){return charmed;}};
struct Player:Unit{bool alive=true,teleport=false;unsigned GetMapId(){return map;}bool IsAlive(){return alive;}bool IsBeingTeleported(){return teleport;}
 bool IsInMap(WorldObject*o){return o->world&&o->map==map&&o->instance==instance&&o->phase==phase;}};
struct DynamicObject:WorldObject{DynamicObject(){type=TYPEID_DYNAMICOBJECT;}Unit*caster=nullptr;unsigned spell=19717,kind=DYNAMIC_OBJECT_AREA_SPELL,duration=5000;
 float radius=8;bool enemy=true,canAttack=true;
 unsigned GetSpellId(){return spell;}unsigned GetType(){return kind;}unsigned GetDuration(){return duration;}float GetRadius(){return radius;}
 Unit*GetCaster(){return caster;}bool IsEnemy(Player*){return enemy;}bool CanAttackSpell(Player*,const void*,bool aoe){assert(aoe);return canAttack;}};
struct WorldPosition{float x,y,z;WorldPosition(WorldObject*o):x(o->x),y(o->y),z(o->z){}};
using HazardPosition=std::pair<WorldPosition,float>;using WorldObjectList=std::list<WorldObject*>;
struct PlayerbotAI{Player*bot;Player*GetBot(){return bot;}};
struct Facade{const void*LookupSpellInfo(unsigned id){assert(id==19717||id==22275);return this;}}sServerFacade;
std::vector<WorldObject*>objects;
namespace MaNGOS{template<class Check>struct WorldObjectListSearcher{WorldObjectList&out;Check&check;WorldObjectListSearcher(WorldObjectList&o,Check&c):out(o),check(c){}};}
namespace Cell{template<class Check>void VisitAllObjects(Player*bot,MaNGOS::WorldObjectListSearcher<Check>&s,float range){assert(range==60);for(auto*o:objects)if(std::hypot(o->x-bot->x,o->y-bot->y)<=range&&s.check(o))s.out.push_back(o);}}
namespace ai{void AppendBlackwingGroundHazards(PlayerbotAI*,std::list<HazardPosition>&);}
__METHOD__
int main(){
 Player bot;PlayerbotAI ai{&bot};Unit caster;DynamicObject fire;fire.caster=&caster;
 objects={&fire};std::list<HazardPosition>out;auto collect=[&](){out.clear();ai::AppendBlackwingGroundHazards(&ai,out);};
 for(unsigned id:{19717u,22275u}){fire.spell=id;collect();assert(out.size()==1&&out.front().second==9);}
 fire.x=5;collect();assert(out.front().first.x==5);fire.x=0;
 DynamicObject second=fire;second.x=6;objects.push_back(&second);collect();assert(out.size()==2);objects.pop_back();
 for(bool DynamicObject::*flag:{&DynamicObject::enemy,&DynamicObject::canAttack}){fire.*flag=false;collect();assert(out.empty());fire.*flag=true;}
 fire.spell=5740;collect();assert(out.empty());fire.spell=19717;
 fire.kind=2;collect();assert(out.empty());fire.kind=DYNAMIC_OBJECT_AREA_SPELL;
 fire.duration=0;collect();assert(out.empty());fire.duration=5000;
 for(float radius:{0.0f,26.0f,std::numeric_limits<float>::quiet_NaN()}){fire.radius=radius;collect();assert(out.empty());}fire.radius=8;
 fire.world=false;collect();assert(out.empty());fire.world=true;
 fire.map=1;collect();assert(out.empty());fire.map=469;fire.instance=2;collect();assert(out.empty());fire.instance=1;
 fire.phase=2;collect();assert(out.empty());fire.phase=1;fire.z=9;collect();assert(out.empty());fire.z=0;
 caster.charmed=true;collect();assert(out.empty());caster.charmed=false;
 caster.instance=2;collect();assert(out.empty());caster.instance=1;fire.caster=nullptr;collect();assert(out.empty());fire.caster=&caster;
 bot.teleport=true;collect();assert(out.empty());bot.teleport=false;bot.charmed=true;collect();assert(out.empty());bot.charmed=false;
 bot.alive=false;collect();assert(out.empty());bot.alive=true;bot.map=409;collect();assert(out.empty());bot.map=469;
 objects.clear();collect();assert(out.empty());
 std::cout<<"PASS BWL native ground hazards: overlapping fire, expiry, hostility, instance, phase and MC isolation\n";
}
'''.replace('__METHOD__', method)
with tempfile.TemporaryDirectory(prefix='bwl-ground-') as directory:
    d=Path(directory); (d/'test.cpp').write_text(code)
    for era in ('ZERO','ONE','TWO'):
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=d,check=True)
        subprocess.run([str(d/'test.exe')],cwd=d,check=True)
