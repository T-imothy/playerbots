"""Compile the actual MC native fire collector with controlled core object boundaries."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
r=Path(__file__).resolve().parents[1]
method=block((r/'playerbot/strategy/values/MoltenCorePositionValue.cpp').read_text(),'void ai::AppendMoltenCoreGroundHazards(')
code=r'''
#include <cassert>
#include <cmath>
#include <list>
#include <vector>
#include <algorithm>
#include <limits>
#include <iostream>
using uint32=unsigned;
enum {TYPEID_UNIT,TYPEID_DYNAMICOBJECT,TYPEID_GAMEOBJECT,DYNAMIC_OBJECT_AREA_SPELL=1,GAMEOBJECT_TYPE_TRAP=6};
struct WorldObject{virtual ~WorldObject()=default;unsigned type=TYPEID_UNIT,map=409,instance=1,phase=1;bool world=true;float x=0,y=0,z=0;
 bool IsInWorld(){return world;}unsigned GetTypeId(){return type;}float GetPositionZ(){return z;}};
struct Unit:WorldObject{unsigned entry=12259;bool charmed=false,alive=true,combat=true;unsigned GetEntry(){return entry;}bool HasCharmer(){return charmed;}};
struct Player:Unit{bool teleport=false;unsigned GetMapId(){return map;}bool IsAlive(){return alive;}bool IsBeingTeleported(){return teleport;}
 bool IsInMap(WorldObject*o){return o->world&&o->map==map&&o->instance==instance&&o->phase==phase;}};
struct DynamicObject:WorldObject{DynamicObject(){type=TYPEID_DYNAMICOBJECT;}Unit*caster=nullptr;unsigned spell=19717,kind=DYNAMIC_OBJECT_AREA_SPELL,duration=5000;
 float radius=8;bool enemy=true,canAttack=true;
 unsigned GetSpellId(){return spell;}unsigned GetType(){return kind;}unsigned GetDuration(){return duration;}float GetRadius(){return radius;}
 Unit*GetCaster(){return caster;}bool IsEnemy(Player*){return enemy;}bool CanAttackSpell(Player*,const void*,bool aoe){assert(aoe);return canAttack;}};
struct GameObject:WorldObject{GameObject(){type=TYPEID_GAMEOBJECT;}unsigned entry=177704,kind=GAMEOBJECT_TYPE_TRAP;bool spawned=true;
 struct Info{struct Trap{unsigned spellId=19428,diameter=10;}trap;}info;
 unsigned GetEntry(){return entry;}unsigned GetGoType(){return kind;}bool IsSpawned(){return spawned;}Info*GetGOInfo(){return &info;}};
struct WorldPosition{float x,y,z;WorldPosition(WorldObject*o):x(o->x),y(o->y),z(o->z){}};
using HazardPosition=std::pair<WorldPosition,float>;using WorldObjectList=std::list<WorldObject*>;
struct PlayerbotAI{Player*bot;Player*GetBot(){return bot;}};
struct Facade{const void*LookupSpellInfo(unsigned id){assert(id==19717);return this;}}sServerFacade;
std::vector<WorldObject*>objects;
namespace MaNGOS{template<class Check>struct WorldObjectListSearcher{WorldObjectList&out;Check&check;WorldObjectListSearcher(WorldObjectList&o,Check&c):out(o),check(c){}};}
namespace Cell{template<class Check>void VisitAllObjects(Player*bot,MaNGOS::WorldObjectListSearcher<Check>&s,float range){assert(range==60);for(auto*o:objects)if(std::hypot(o->x-bot->x,o->y-bot->y)<=range&&s.check(o))s.out.push_back(o);}}
namespace ai{float trapRadius=5;float NativeEncounterSpellRadius(unsigned id){assert(id==19428);return trapRadius;}void AppendMoltenCoreGroundHazards(PlayerbotAI*,std::list<HazardPosition>&);}
using namespace ai;
__METHOD__
int main(){
 Player bot;PlayerbotAI ai{&bot};Unit boss;boss.x=40;DynamicObject fire;fire.caster=&boss;GameObject bomb;bomb.x=10;
 objects={&fire};std::list<HazardPosition>out;auto collect=[&](){out.clear();AppendMoltenCoreGroundHazards(&ai,out);};
 collect();assert(out.size()==1&&out.front().first.x==0&&out.front().second==9); // actual location and live radius
 fire.x=5;collect();assert(out.front().first.x==5);fire.x=0;
 DynamicObject second=fire;second.x=6;objects.push_back(&second);collect();assert(out.size()==2);objects.pop_back();
 for(bool DynamicObject::*flag:{&DynamicObject::enemy,&DynamicObject::canAttack}){fire.*flag=false;collect();assert(out.empty());fire.*flag=true;}
 fire.spell=5740;collect();assert(out.empty());fire.spell=19717; // player Rain of Fire is not Gehennas fire
 fire.kind=2;collect();assert(out.empty());fire.kind=DYNAMIC_OBJECT_AREA_SPELL;
 fire.duration=0;collect();assert(out.empty());fire.duration=5000;
 fire.radius=0;collect();assert(out.empty());fire.radius=26;collect();assert(out.empty());
 fire.radius=std::numeric_limits<float>::quiet_NaN();collect();assert(out.empty());fire.radius=8;
 fire.world=false;collect();assert(out.empty());fire.world=true;
 fire.map=1;collect();assert(out.empty());fire.map=409;fire.instance=2;collect();assert(out.empty());fire.instance=1;
 fire.phase=2;collect();assert(out.empty());fire.phase=1;fire.z=9;collect();assert(out.empty());fire.z=0;
 boss.entry=12056;collect();assert(out.empty());boss.entry=12259;boss.charmed=true;collect();assert(out.empty());boss.charmed=false;
 boss.instance=2;collect();assert(out.empty());boss.instance=1;fire.caster=nullptr;collect();assert(out.empty());fire.caster=&boss;
 // Fire remains dangerous while its native object exists, even after combat/caster death.
 boss.alive=boss.combat=bot.combat=false;collect();assert(out.size()==1);
 objects={&bomb};collect();assert(out.size()==1&&out.front().second==6);
 trapRadius=8;collect();assert(out.front().second==9);trapRadius=5;
 bomb.spawned=false;collect();assert(out.empty());bomb.spawned=true;bomb.info.trap.spellId=21158;collect();assert(out.empty());bomb.info.trap.spellId=19428;
 bomb.kind=0;collect();assert(out.empty());bomb.kind=GAMEOBJECT_TYPE_TRAP;bomb.entry=178088;collect();assert(out.empty());bomb.entry=177704;
 bomb.instance=2;collect();assert(out.empty());bomb.instance=1;
 bot.teleport=true;collect();assert(out.empty());bot.teleport=false;bot.charmed=true;collect();assert(out.empty());bot.charmed=false;
 bot.alive=false;collect();assert(out.empty());bot.alive=true;bot.map=1;collect();assert(out.empty());bot.map=409;
 objects.clear();collect();assert(out.empty());
 std::cout<<"PASS: actual MC ground fire collection, overlapping objects, native radii, hostility, phase, expiry and post-combat lifetime\n";
}
'''.replace('__METHOD__',method)
with tempfile.TemporaryDirectory(prefix='mc-ground-') as directory:
 d=Path(directory);(d/'test.cpp').write_text(code)
 for era in ('ZERO','ONE','TWO'):
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=d,check=True)
  subprocess.run([str(d/'test.exe')],cwd=d,check=True)
