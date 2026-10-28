"""Compile production device assignment with native-state/multi-rogue fixtures."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/BlackwingLairDungeonActions.cpp').read_text()
method=block(source,'GameObject* ai::AssignedSuppressionDevice(')
code=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <list>
#include <vector>
using uint32=unsigned;
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
struct Player:Object{bool teleport=false,charmed=false,learned=true,combat=false,stealth=false;unsigned cls=CLASS_ROGUE;
 Group* group=nullptr;PlayerbotAI* ai=nullptr;bool IsBeingTeleported(){return teleport;}bool HasCharmer(){return charmed;}
 Group* GetGroup(){return group;}unsigned getClass(){return cls;}bool HasSpell(unsigned){return learned;}
 PlayerbotAI* GetPlayerbotAI(){return ai;}bool IsInCombat(){return combat;}bool HasAuraType(unsigned){return stealth;}
 bool IsWithinLOSInMap(GameObject* go){return go->los;}};
struct GroupReference{Player* p;GroupReference* n=nullptr;Player* getSource(){return p;}GroupReference* next(){return n;}};
struct Group{GroupReference* first=nullptr;unsigned leader=100;GroupReference* GetFirstMember(){return first;}unsigned GetLeaderGuid(){return leader;}};
struct PlayerbotAI{Player* bot;bool real=false,movable=true,vanish=true;Player* GetBot(){return bot;}
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
 first.state=2;assert(ai::AssignedSuppressionDevice(&aa)==&second);assert(!ai::AssignedSuppressionDevice(&bb));
 first.state=GO_READY;second.spawned=false;assert(!ai::AssignedSuppressionDevice(&bb));second.spawned=true;
 a.alive=false;assert(ai::AssignedSuppressionDevice(&bb)==&first);assert(!ai::AssignedSuppressionDevice(&aa));a.alive=true;
 a.teleport=true;assert(ai::AssignedSuppressionDevice(&bb)==&first);a.teleport=false;
 a.instance=2;assert(!ai::AssignedSuppressionDevice(&aa));a.instance=1;
 first.z=9;assert(ai::AssignedSuppressionDevice(&aa)==&second);first.z=0;
 first.los=false;assert(ai::AssignedSuppressionDevice(&aa)==&second);first.los=true;
 first.flags=GO_FLAG_IN_USE;assert(ai::AssignedSuppressionDevice(&aa)==&second);first.flags=0;
 a.map=409;assert(!ai::AssignedSuppressionDevice(&aa));a.map=469;
 aa.real=true;assert(!ai::AssignedSuppressionDevice(&aa));aa.real=false;
 a.learned=false;assert(ai::AssignedSuppressionDevice(&bb)==&first);a.learned=true;
 leader.x=100;assert(!ai::AssignedSuppressionDevice(&aa));leader.x=0;
 a.combat=true;aa.vanish=false;sServerFacade.spell.Attributes=SPELL_ATTR_ONLY_STEALTHED;
 assert(!ai::AssignedSuppressionDevice(&aa));assert(ai::AssignedSuppressionDevice(&bb)==&first);
 a.stealth=true;assert(ai::AssignedSuppressionDevice(&aa)==&first);a.stealth=false;
 aa.vanish=true;assert(ai::AssignedSuppressionDevice(&aa)==&first);
 sServerFacade.spell.Attributes=0;aa.vanish=false;assert(ai::AssignedSuppressionDevice(&aa)==&first);
 first.state=second.state=2;assert(!ai::AssignedSuppressionDevice(&aa));
 first.state=GO_READY;assert(ai::AssignedSuppressionDevice(&aa)==&first);
 std::cout<<"PASS: active state, unique ownership, raid leash, floors/LOS, eligibility and per-era stealth\n";
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
