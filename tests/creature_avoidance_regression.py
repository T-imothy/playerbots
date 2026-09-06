"""Exercise the actual shared creature-avoidance helper, including healer shortcuts."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
text = (root / "playerbot/strategy/actions/DungeonActions.cpp").read_text()
methods = "\n".join(block(text, name) for name in (
    "bool MoveAwayFromCreature::CreatureSearchHelperFunction(Event& event, uint32 creatureId)",
    "bool MoveAwayFromCreature::CreatureSearchHelperFunction(Event& event, const std::set<uint32>& creatureIds)",
    "bool MoveAwayFromSpecificCreatures::Execute(",
    "bool MoveAwayFromCreature::IsValidPoint(",
    "bool MoveAwayFromCreature::HasCreaturesNearby(",
    "bool MoveAwayFromCreature::IsHazardNearby("))
code = r'''
#include <cassert>
#include <cmath>
#include <list>
#include <iostream>
#include <vector>
#include <utility>
#include <set>
#include <algorithm>
#include <type_traits>
using uint32=unsigned;using uint8=unsigned char;using std::advance;
constexpr float M_PI=3.14159265358979323846f;constexpr int TEMPSPAWN_TIMED_DESPAWN=0;
struct Map {};
struct Unit {unsigned entry=0;bool world=true,alive=true;float x=0,y=0,z=0;Map* map=nullptr;Unit* victim=nullptr;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}Map* GetMap(){return map;}Unit* GetVictim(){return victim;}
 float GetDistance(float a,float b,float c)const{return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}
 float GetDistance(Unit* u)const{return GetDistance(u->x,u->y,u->z);}float GetCombatReach(){return 1.5f;}};
struct Creature:Unit {};
struct Group;
struct Player:Unit {bool healer=false,charmed=false,teleport=false;Group* group=nullptr;
 bool HasCharmer(){return charmed;}bool IsBeingTeleported(){return teleport;}Group* GetGroup(){return group;}
 unsigned GetMapId(){return 532;}bool IsWithinLOS(float,float,float){return true;}float GetCollisionHeight(){return 1;}
 void SummonCreature(int,float,float,float,float,int,float){}};
struct GroupReference {Player* player=nullptr;GroupReference* following=nullptr;
 Player* getSource(){return player;}GroupReference* next(){return following;}};
struct Group {GroupReference* first=nullptr;GroupReference* GetFirstMember(){return first;}};
struct WorldPosition {unsigned map=0;float x=0,y=0,z=0;
 WorldPosition(unsigned m,float a,float b,float c):map(m),x(a),y(b),z(c){}
 WorldPosition(Unit* u):x(u->x),y(u->y),z(u->z){}
 WorldPosition operator+(WorldPosition other)const{return {map,x+other.x,y+other.y,z+other.z};}
 float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}
 void setZ(float height){z=height;}float getHeight(){return z;}
 float distance(WorldPosition other)const{return std::sqrt((x-other.x)*(x-other.x)+(y-other.y)*(y-other.y)+(z-other.z)*(z-other.z));}
 float fDist(WorldPosition other)const{return distance(other);}float getAngleTo(WorldPosition other){return std::atan2(other.y-y,other.x-x);}
 bool canPathTo(WorldPosition,Player*)const{return true;}};
using HazardPosition=std::pair<WorldPosition,float>;
enum class BotState {BOT_STATE_COMBAT};
struct PlayerbotAI {std::list<HazardPosition> hazards;std::set<uint32> avoid;
 template<class T>decltype(auto) Value(const char*){if constexpr(std::is_same_v<T,std::set<uint32>&>)return (avoid);else return (hazards);}
 bool IsHeal(Player* p,bool){return p->healer;}bool HasStrategy(const char*,BotState){return false;}};
struct Facade {bool IsAlive(Player* p){return p->alive;}}sServerFacade;
std::vector<Unit*> nearby;std::vector<unsigned> searchedEntries;unsigned searches=0;
namespace MaNGOS {
 struct AllCreaturesMatchingOneEntryInRange {Player* bot;std::vector<unsigned> entries;float range;
  AllCreaturesMatchingOneEntryInRange(Player* b,const std::vector<unsigned>& e,float r):bot(b),entries(e),range(r){searchedEntries=e;++searches;}};
 template<class T>struct UnitListSearcher {std::list<Unit*>& out;T& check;UnitListSearcher(std::list<Unit*>& o,T& t):out(o),check(t){}};
}
namespace Cell {template<class T>void VisitAllObjects(Player*,T& search,float){for(auto* u:nearby)
 if(std::find(search.check.entries.begin(),search.check.entries.end(),u->entry)!=search.check.entries.end() &&
 search.check.bot->GetDistance(u)<search.check.range)search.out.push_back(u);}}
struct Event {};
namespace ai {
 struct MoveAwayFromCreature {Player* bot;PlayerbotAI* ai;unsigned creatureID=0;float range=10;
 bool ignoreVictim=true,healersSafe=true;unsigned moves=0;WorldPosition destination{0,0,0,0};
 bool CreatureSearchHelperFunction(Event&,uint32);bool IsValidPoint(const WorldPosition&,const std::list<Creature*>&,const std::list<HazardPosition>&);
 bool CreatureSearchHelperFunction(Event&,const std::set<uint32>&);
 bool HasCreaturesNearby(const WorldPosition&,const std::list<Creature*>&)const;
 bool IsHazardNearby(const WorldPosition&,const std::list<HazardPosition>&)const;
 bool MoveTo(unsigned map,float x,float y,float z,bool,bool,bool,bool){++moves;destination={map,x,y,z};return true;}
 bool IsReaction(){return false;}void WaitForReach(float){}};
 struct MoveAwayFromSpecificCreatures:MoveAwayFromCreature {bool Execute(Event&);};
}
using namespace ai;
#define AI_VALUE(type,name) ai->Value<type>(name)
__METHODS__
int main(){
 Map map,otherMap;Player bot,unsafe,safe;bot.map=unsafe.map=safe.map=&map;
 unsafe.healer=safe.healer=true;unsafe.x=1;safe.x=15;
 Creature hazard;hazard.entry=17646;hazard.map=&map;hazard.x=1;nearby={&hazard};
 Group group;GroupReference safeRef{&safe},unsafeRef{&unsafe,&safeRef};group.first=&unsafeRef;bot.group=&group;
 PlayerbotAI ai;MoveAwayFromCreature action{&bot,&ai};Event event;
 // Configured multi-entry avoidance passes its requested ID, not the base member's zero.
 assert(action.CreatureSearchHelperFunction(event,17646) && searchedEntries==std::vector<unsigned>{17646});
 assert(action.destination.x==15 && action.moves==1); // never choose healer inside nearest hazard
 safe.map=&otherMap;assert(action.CreatureSearchHelperFunction(event,17646));
 assert(action.destination.x!=15 && hazard.GetDistance(action.destination.x,action.destination.y,action.destination.z)>10);
 safe.map=&map;hazard.alive=false;assert(!action.CreatureSearchHelperFunction(event,17646));hazard.alive=true;
 hazard.map=&otherMap;assert(!action.CreatureSearchHelperFunction(event,17646));hazard.map=&map;
 hazard.victim=&bot;action.ignoreVictim=false;assert(!action.CreatureSearchHelperFunction(event,17646));
 action.ignoreVictim=true;assert(action.CreatureSearchHelperFunction(event,17646));hazard.victim=nullptr;
 bot.charmed=true;assert(!action.CreatureSearchHelperFunction(event,17646));bot.charmed=false;
 bot.teleport=true;assert(!action.CreatureSearchHelperFunction(event,17646));bot.teleport=false;
 assert(!action.CreatureSearchHelperFunction(event,0));
 // A second configured entry beyond the bot's initial radius blocks an otherwise
 // attractive destination. One native query sees both; list order cannot select
 // a safe point for one hazard which lies inside the other.
 Creature second;second.entry=99999;second.map=&map;second.x=15;nearby={&hazard,&second};
 MoveAwayFromSpecificCreatures multi;multi.bot=&bot;multi.ai=&ai;ai.avoid={17646,99999};
 searches=0;assert(multi.Execute(event) && searches==1 && searchedEntries.size()==2);
 assert(hazard.GetDistance(multi.destination.x,multi.destination.y,multi.destination.z)>10);
 assert(second.GetDistance(multi.destination.x,multi.destination.y,multi.destination.z)>10);
 assert(multi.destination.x!=safe.x);ai.avoid={0};assert(!multi.Execute(event));ai.avoid.clear();assert(!multi.Execute(event));
 // Same-entry neighbors just beyond the original search radius must be included too.
 second.entry=17646;assert(action.CreatureSearchHelperFunction(event,17646));
 assert(second.GetDistance(action.destination.x,action.destination.y,action.destination.z)>10);
 std::cout<<"PASS: actual single/combined-entry avoidance, destination-neighbor coverage, native single query, safe healer and map/life/control/victim guards\n";
}
'''.replace("__METHODS__", methods)
with tempfile.TemporaryDirectory(prefix="mantech-creature-avoidance-") as tmp:
    tmp = Path(tmp)
    (tmp / "test.cpp").write_text(code)
    subprocess.run(["cl", "/nologo", "/EHsc", "/std:c++17", "test.cpp", "/Fe:test.exe"], cwd=tmp, check=True)
    subprocess.run([str(tmp / "test.exe")], check=True)
