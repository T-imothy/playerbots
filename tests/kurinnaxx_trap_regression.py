"""Actual Classic Sand Trap collector: pre-blast warning and native ownership/lifetime."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
method=block((root/'playerbot/strategy/values/HazardsValue.cpp').read_text(),'void ai::AppendKurinnaxxTrapHazards(')
front=block((root/'playerbot/strategy/ClassicRaidPolicy.h').read_text(),'inline bool Front(')
trigger=block((root/'playerbot/strategy/triggers/HostileGroundDamageTrigger.cpp').read_text(),'bool HostileGroundDamageTrigger::IsActive(')
code=r'''
#include <cassert>
#include <cmath>
#include <list>
#include <vector>
#include <map>
#include <string>
#include <iostream>
enum{TYPEID_UNIT,TYPEID_GAMEOBJECT,GAMEOBJECT_TYPE_TRAP,GO_READY,GO_NOT_READY,GO_JUST_DEACTIVATED,IN_PROGRESS};
namespace BotState{enum{BOT_STATE_COMBAT};}
struct InstanceData{unsigned state=IN_PROGRESS;unsigned GetData(unsigned id){assert(id==0);return state;}};
struct Map{InstanceData instance;bool present=true;bool IsDungeon(){return true;}InstanceData*GetInstanceData(){return present?&instance:nullptr;}};
struct WorldObject{virtual ~WorldObject()=default;unsigned type=TYPEID_UNIT,map=509,instance=1;bool world=true;float x=0,y=0,z=0;
 bool IsInWorld(){return world;}unsigned GetTypeId(){return type;}float GetPositionZ(){return z;}};
struct Unit:WorldObject{bool charm=false,player=false;unsigned entry=15348,guid=1;
 bool HasCharmer(){return charm;}bool IsPlayer(){return player;}unsigned GetEntry(){return entry;}unsigned GetObjectGuid(){return guid;}};
struct Group{bool member=true;bool IsMember(unsigned){return member;}};
struct Player:Unit{bool alive=true,teleport=false,grouped=true,combat=true;Map room;Group group;unsigned GetMapId(){return map;}
 bool IsInCombat(){return combat;}float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}
 bool IsAlive(){return alive;}bool IsBeingTeleported(){return teleport;}Group*GetGroup(){return grouped?&group:nullptr;}
 Map*GetMap(){return &room;}bool IsInMap(WorldObject*o){return o&&o->world&&map==o->map&&instance==o->instance;}};
struct GameObject:WorldObject{GameObject(){type=TYPEID_GAMEOBJECT;}unsigned entry=180647,spell=25648,kind=GAMEOBJECT_TYPE_TRAP,uses=0,state=GO_READY,spawner=1;bool spawned=true;
 unsigned GetEntry(){return entry;}unsigned GetSpellId(){return spell;}unsigned GetGoType(){return kind;}
 unsigned GetUseCount(){return uses;}unsigned GetLootState(){return state;}unsigned GetSpawnerGuid(){return spawner;}bool IsSpawned(){return spawned;}};
struct WorldPosition{float x,y,z;WorldPosition(WorldObject*o):x(o->x),y(o->y),z(o->z){}float distance(WorldPosition p)const{return std::sqrt((x-p.x)*(x-p.x)+(y-p.y)*(y-p.y)+(z-p.z)*(z-p.z));}};
using HazardPosition=std::pair<WorldPosition,float>;using WorldObjectList=std::list<WorldObject*>;
struct PlayerbotAI{Player*bot;Unit*owner;bool real=false,dungeon=true;Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}
 bool HasStrategy(const char*,int){return dungeon;}Unit*GetUnit(unsigned id){return id==1?owner:nullptr;}};
float radius=8;float NativeEncounterSpellRadius(unsigned id){assert(id==25656);return radius;}
std::vector<WorldObject*>objects;
namespace MaNGOS{template<class Check>struct WorldObjectListSearcher{WorldObjectList&out;Check&check;WorldObjectListSearcher(WorldObjectList&o,Check&c):out(o),check(c){}};}
namespace Cell{template<class Check>void VisitAllObjects(Player*bot,MaNGOS::WorldObjectListSearcher<Check>&s,float range){assert(range==60||range==30);for(auto*o:objects)if(std::hypot(o->x-bot->x,o->y-bot->y)<=range&&s.check(o))s.out.push_back(o);}}
namespace ai{void AppendKurinnaxxTrapHazards(PlayerbotAI*,std::list<HazardPosition>&);}
using ai::AppendKurinnaxxTrapHazards;
void AppendNativeEncounterActorHazards(PlayerbotAI*,std::list<HazardPosition>&){}
struct HostileDamageAreaCheck{Player*bot;bool operator()(WorldObject*){return false;}};
struct DynamicObject:WorldObject{float GetRadius(){return 1;}unsigned GetDuration(){return 1;}unsigned GetObjectGuid(){return 1;}float GetPositionX(){return x;}float GetPositionY(){return y;}};
#define SET_AI_VALUE(...) assert(false)
struct HostileGroundDamageTrigger{Player*bot;PlayerbotAI*ai;bool IsActive();};
bool Dragon(unsigned){return false;}
__FRONT__
__METHOD__
__TRIGGER__
int main(){
 Player bot;Unit owner;PlayerbotAI ai{&bot,&owner};GameObject trap;objects={&trap};std::list<HazardPosition>h;
 auto collect=[&](){h.clear();ai::AppendKurinnaxxTrapHazards(&ai,h);};
 HostileGroundDamageTrigger warning{&bot,&ai};
#ifdef MANGOSBOT_ZERO
 assert(Front(15348));collect();assert(h.size()==1&&h.front().second==9);
 assert(warning.IsActive());trap.x=20;assert(!warning.IsActive());trap.x=0;
 bot.combat=false;assert(!warning.IsActive());bot.combat=true;
 owner.player=true;owner.entry=0;collect();assert(h.size()==1); // native target summons trap
 bot.group.member=false;collect();assert(h.empty());bot.group.member=true;
 owner.player=false;owner.entry=1;collect();assert(h.empty());owner.entry=15348;
 owner.charm=true;collect();assert(h.empty());owner.charm=false;
 owner.instance=2;collect();assert(h.empty());owner.instance=1;
 trap.spawner=99;collect();assert(h.empty());trap.spawner=1;
 trap.uses=1;collect();assert(h.empty()&&!warning.IsActive());trap.uses=0;
 trap.state=GO_JUST_DEACTIVATED;collect();assert(h.empty());trap.state=GO_NOT_READY;collect();assert(h.size()==1);trap.state=GO_READY;
 trap.spawned=false;collect();assert(h.empty());trap.spawned=true;
 trap.spell=26524;collect();assert(h.empty());trap.spell=25648;
 trap.entry=1;collect();assert(h.empty());trap.entry=180647;
 trap.kind=0;collect();assert(h.empty());trap.kind=GAMEOBJECT_TYPE_TRAP;
 trap.world=false;collect();assert(h.empty());trap.world=true;
 trap.instance=2;collect();assert(h.empty());trap.instance=1;trap.z=9;collect();assert(h.empty());trap.z=0;
 for(float r:{0.0f,36.0f,float(NAN)}){radius=r;collect();assert(h.empty());}radius=8;
 bot.room.instance.state=0;collect();assert(h.empty());bot.room.instance.state=IN_PROGRESS;
 bot.room.present=false;collect();assert(h.empty());bot.room.present=true;
 bot.teleport=true;collect();assert(h.empty());bot.teleport=false;
 bot.map=409;collect();assert(h.empty());bot.map=509;
 bot.grouped=false;collect();assert(h.empty());bot.grouped=true;
 ai.real=true;collect();assert(h.empty());ai.real=false;ai.dungeon=false;collect();assert(h.empty());ai.dungeon=true;
 GameObject second=trap;second.x=5;objects.push_back(&second);collect();assert(h.size()==2);
 objects.clear();collect();assert(h.empty());
#else
 assert(!Front(15348));collect();assert(h.empty()&&!warning.IsActive());
#endif
 std::cout<<"PASS native Sand Trap lifetime, overlap, owner/map/instance/strategy guards and Classic-only frontal policy\n";
}
'''.replace('__METHOD__',method).replace('__FRONT__',front).replace('__TRIGGER__',trigger)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='kurinnaxx-trap-') as folder:
  path=Path(folder);(path/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=path,check=True)
  subprocess.run([str(path/'test.exe')],cwd=path,check=True)
