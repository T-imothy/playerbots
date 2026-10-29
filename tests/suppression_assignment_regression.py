"""Compile production device assignment with native-state/multi-rogue fixtures."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/BlackwingLairDungeonActions.cpp').read_text()
method=block(source,'GameObject* ai::AssignedSuppressionDevice(').replace('state.device.Clear()', 'state.device = 0')
code=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <list>
#include <map>
#include <vector>
using uint32=unsigned;
unsigned tick=1000;
struct WorldTimer{static unsigned getMSTime(){return tick;}static unsigned getMSTimeDiff(unsigned a,unsigned b){return b-a;}};
enum{IN_PROGRESS=1,DONE=3};
struct InstanceData{unsigned phase=0;unsigned GetData(unsigned){return phase;}};
struct Map{InstanceData instance;InstanceData* GetInstanceData(){return &instance;}};
struct SuppressionDuty{unsigned device=0,anchor=0,instance=0,generation=0,progressAt=0,recoveryAt=0;float distance=0;bool returning=false,routeOwned=false,routeStealthed=false;std::map<unsigned,unsigned> rejected;};
struct StoredDuty{SuppressionDuty data;SuppressionDuty Get(){return data;}void Set(SuppressionDuty s){data=s;}};
struct Context{StoredDuty duty;template<class T>StoredDuty* GetValue(const char*){return &duty;}};
enum {CLASS_ROGUE=4,SPELL_DISARM_TRAP=1842,GO_READY=1,GO_FLAG_IN_USE=1,GO_FLAG_NO_INTERACT=2,
 SPELL_ATTR_ONLY_STEALTHED=0x20000,SPELL_AURA_MOD_STEALTH=16,GAMEOBJECT_FLAGS=0};
struct SpellEntry{unsigned Attributes=0;};
struct Group;struct PlayerbotAI;
struct Object{bool world=true,alive=true;unsigned map=469,instance=1,guid=1;float x=0,z=0;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}unsigned GetObjectGuid(){return guid;}
 unsigned GetMapId(){return map;}bool IsInMap(Object* b){return b&&map==b->map&&instance==b->instance;}
 float GetPositionX(){return x;}float GetPositionY(){return 0;}float GetPositionZ(){return z;}
 float GetDistance(Object* b){return std::hypot(x-b->x,z-b->z);}};
struct GameObject:Object{bool spawned=true,los=true;unsigned state=GO_READY,flags=0;
 unsigned GetLootState(){return state;}bool HasFlag(unsigned,unsigned f){return flags&f;}};
struct Player:Object{Map mapData;Map* GetMap(){return &mapData;}unsigned GetInstanceId(){return instance;}bool teleport=false,charmed=false,learned=true,combat=false,stealth=false;unsigned cls=CLASS_ROGUE;
 Group* group=nullptr;PlayerbotAI* ai=nullptr;bool IsBeingTeleported(){return teleport;}bool HasCharmer(){return charmed;}
 Group* GetGroup(){return group;}unsigned getClass(){return cls;}bool HasSpell(unsigned){return learned;}
 PlayerbotAI* GetPlayerbotAI(){return ai;}bool IsInCombat(){return combat;}bool HasAuraType(unsigned){return stealth;}
 bool IsWithinLOSInMap(GameObject* go){return go->los;}};
struct GroupReference{Player* p;GroupReference* n=nullptr;Player* getSource(){return p;}GroupReference* next(){return n;}};
struct Group{GroupReference* first=nullptr;unsigned leader=100;GroupReference* GetFirstMember(){return first;}unsigned GetLeaderGuid(){return leader;}};
struct PlayerbotAI{Player* bot;Context context;unsigned generation=1;Context* GetAiObjectContext(){return &context;}unsigned GetTransitionGeneration(){return generation;}bool real=false,movable=true,vanish=true;Player* GetBot(){return bot;}
 bool IsRealPlayer(){return real;}bool CanMove(){return movable;}bool CanCastSpell(const char*,Player*,int){return vanish;}};
struct Facade{SpellEntry spell;bool isSpawned(GameObject* go){return go->spawned;}
 SpellEntry* LookupSpellInfo(unsigned){return &spell;}}sServerFacade;
std::vector<GameObject*> grid;
namespace MaNGOS{
 struct GameObjectEntryInPosRangeCheck{Object& anchor;float range;
 GameObjectEntryInPosRangeCheck(Object& a,unsigned,float,float,float,float r):anchor(a),range(r){}};
 template<class T>struct GameObjectListSearcher{std::list<GameObject*>& out;T& check;
 GameObjectListSearcher(std::list<GameObject*>& o,T& c):out(o),check(c){}};
}
namespace Cell{template<class T>void VisitAllObjects(Object*,T& search,float){
 for(auto* go:grid)if(search.check.anchor.GetDistance(go)<=search.check.range)search.out.push_back(go);}}
namespace ai{GameObject* AssignedSuppressionDevice(PlayerbotAI*);}
__METHOD__
int main(){
 Player leader,a,b;leader.guid=100;leader.cls=1;a.guid=1;b.guid=2;
 PlayerbotAI aa{&a},bb{&b};a.ai=&aa;b.ai=&bb;
 GroupReference r3{&b},r2{&a,&r3},r1{&leader,&r2};Group group{&r1};a.group=b.group=leader.group=&group;
 GameObject first,second;first.guid=10;first.x=2;second.guid=11;second.x=5;grid={&second,&first};
 assert(ai::AssignedSuppressionDevice(&aa)==&first);assert(ai::AssignedSuppressionDevice(&bb)==&second);
 // Bounded look-ahead reaches devices without walking the raid into them.
 // Completing one job must not steal the other rogue's live lease.
 first.state=2;assert(!ai::AssignedSuppressionDevice(&aa));assert(ai::AssignedSuppressionDevice(&bb)==&second);
 auto reset=[&](){aa.context.duty.data={};bb.context.duty.data={};first.state=second.state=GO_READY;};
 reset();second.spawned=false;assert(!ai::AssignedSuppressionDevice(&bb));second.spawned=true;
 reset();a.alive=false;assert(ai::AssignedSuppressionDevice(&bb)==&first);assert(!ai::AssignedSuppressionDevice(&aa));a.alive=true;
 reset();a.teleport=true;assert(ai::AssignedSuppressionDevice(&bb)==&first);a.teleport=false;
 reset();a.instance=2;assert(!ai::AssignedSuppressionDevice(&aa));a.instance=1;
 reset();first.z=9;assert(ai::AssignedSuppressionDevice(&aa)==&second);first.z=0;
 reset();first.los=false;assert(ai::AssignedSuppressionDevice(&aa)==&second);first.los=true;
 reset();first.flags=GO_FLAG_IN_USE;assert(ai::AssignedSuppressionDevice(&aa)==&second);first.flags=0;
 reset();a.map=409;assert(!ai::AssignedSuppressionDevice(&aa));a.map=469;
 reset();aa.real=true;assert(!ai::AssignedSuppressionDevice(&aa));aa.real=false;
 reset();a.learned=false;assert(ai::AssignedSuppressionDevice(&bb)==&first);a.learned=true;
 reset();leader.x=100;assert(!ai::AssignedSuppressionDevice(&aa));leader.x=0;
 reset();a.combat=true;aa.vanish=false;sServerFacade.spell.Attributes=SPELL_ATTR_ONLY_STEALTHED;
 assert(!ai::AssignedSuppressionDevice(&aa));assert(ai::AssignedSuppressionDevice(&bb)==&first);
 reset();a.stealth=true;assert(ai::AssignedSuppressionDevice(&aa)==&first);a.stealth=false;
 reset();aa.vanish=true;assert(ai::AssignedSuppressionDevice(&aa)==&first);
 reset();sServerFacade.spell.Attributes=0;aa.vanish=false;assert(ai::AssignedSuppressionDevice(&aa)==&first);
 reset();first.state=second.state=2;assert(!ai::AssignedSuppressionDevice(&aa));
 first.state=GO_READY;assert(ai::AssignedSuppressionDevice(&aa)==&first);
 reset();grid={&first};first.x=39;assert(ai::AssignedSuppressionDevice(&aa)==&first);
 reset();first.x=41;assert(!ai::AssignedSuppressionDevice(&aa));first.x=2;grid={&first,&second};
 reset();aa.context.duty.data.anchor=leader.guid;aa.context.duty.data.instance=1;aa.context.duty.data.generation=aa.generation;
 aa.context.duty.data.returning=true;assert(!ai::AssignedSuppressionDevice(&aa));assert(ai::AssignedSuppressionDevice(&bb)==&first);
 reset();aa.context.duty.data.anchor=leader.guid;aa.context.duty.data.instance=1;aa.context.duty.data.generation=aa.generation;
 aa.context.duty.data.routeOwned=true;aa.context.duty.data.routeStealthed=true;
 assert(!ai::AssignedSuppressionDevice(&aa));assert(ai::AssignedSuppressionDevice(&bb)==&first);
 reset();a.mapData.instance.phase=IN_PROGRESS;assert(!ai::AssignedSuppressionDevice(&aa));
 a.mapData.instance.phase=DONE;assert(!ai::AssignedSuppressionDevice(&aa));a.mapData.instance.phase=0;
 reset();assert(ai::AssignedSuppressionDevice(&aa)==&first);
 tick+=10001;assert(ai::AssignedSuppressionDevice(&aa)==&second); // stalled lease bounded
 assert(aa.context.duty.data.rejected.count(first.guid));
 ++aa.generation;assert(ai::AssignedSuppressionDevice(&aa)==&first); // transition clears stale rejection
 reset();aa.context.duty.data.anchor=leader.guid;aa.context.duty.data.instance=1;
 aa.context.duty.data.generation=aa.generation;aa.context.duty.data.rejected[first.guid]=tick;
 assert(ai::AssignedSuppressionDevice(&aa)==&second); // route failure tries another device
 tick+=10001;assert(ai::AssignedSuppressionDevice(&aa)==&first); // bounded retry
 std::cout<<"PASS: active state, unique ownership, stable leases, timeout/recovery, boss transition, raid leash, floors/LOS, eligibility and per-era stealth\n";
}
'''.replace('__METHOD__',method)
strategy=(root/'playerbot/strategy/generic/BlackwingLairDungeonStrategies.cpp').read_text()
assert 'SuppressionRoomPassiveMultiplier' not in strategy
assert 'ChangeStrategy(' not in strategy
for state in ('Combat','NonCombat'):
 assert 'suppression device in sight' in block(strategy,f'void BlackwingLairDungeonStrategy::Init{state}Triggers(')
assert 'SetLootState' not in method and 'SetGoState' not in method
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='mantech-suppression-') as folder:
  tmp=Path(folder);(tmp/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
  subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
