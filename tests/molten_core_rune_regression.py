"""Compile the actual rune eligibility, selection and execution bodies in all eras."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
source = (root / 'playerbot/strategy/actions/MoltenCoreDungeonActions.cpp').read_text()
methods = '\n'.join(block(source, marker) for marker in (
    'bool ai::MoltenCoreDouseItemAvailable(', 'GameObject* ai::MoltenCoreRuneTarget(',
    'bool MoveToMCRuneAction::isUseful(', 'bool MoveToMCRuneAction::Execute(',
    'bool DouseMCRuneAction::isPossible(', 'bool DouseMCRuneAction::isUseful(',
    'bool DouseMCRuneAction::Execute('))
code = r'''
#include <cassert>
#include <list>
#include <map>
#include <set>
#include <iostream>
#include <cmath>
using uint32=unsigned;using int32=int;using ObjectGuid=unsigned;
enum {DONE=2,SPECIAL=3,GAMEOBJECT_FLAGS=0,GO_FLAG_IN_USE=1,GO_STATE_READY=0,GO_READY=0};
constexpr float INTERACTION_DISTANCE=5;
struct InstanceData {std::map<unsigned,unsigned> states;unsigned GetData(unsigned id){return states[id];}};
struct Map {InstanceData*instance;InstanceData*GetInstanceData(){return instance;}};
struct Object {bool world=true;unsigned guid=0,phase=1,instance=1;Map*map=nullptr;float x=0,y=0,z=0;
 bool IsInWorld(){return world;}ObjectGuid GetObjectGuid(){return guid;}float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}};
struct GameObject:Object {unsigned entry=176956;bool spawned=true,inUse=false,trapped=false;int state=0,loot=0;GameObject*trap=nullptr;
 unsigned GetEntry(){return entry;}bool HasFlag(int,int){return inUse;}int GetGoState(){return state;}int GetLootState(){return loot;}
 GameObject*GetLinkedTrap(){return trap?trap:(trapped?this:nullptr);}};
struct Group;struct Player:Object {bool alive=true,teleport=false,charmed=false,combat=false,casting=false,eligible=true,skip=false,itemCheat=true;
 unsigned mapId=409;Group*group=nullptr;std::map<unsigned,unsigned>bag;std::set<unsigned>cooldown;
 unsigned used=0,usedItem=0,usedRune=0,moves=0;
 bool IsAlive(){return alive;}bool IsBeingTeleported(){return teleport;}bool HasCharmer(){return charmed;}bool IsInCombat(){return combat;}
 bool IsNonMeleeSpellCasted(bool,bool,bool){return casting;}unsigned GetMapId(){return mapId;}Map*GetMap(){return map;}Group*GetGroup(){return group;}
 bool HasItemCount(unsigned item,unsigned count){return bag[item]>=count;}bool IsInMap(Object*o){return world&&o->world&&map==o->map&&phase==o->phase&&instance==o->instance;}
 float GetDistance(Object*o){return std::hypot(x-o->x,y-o->y);}};
struct GroupReference {Player*p;GroupReference*following=nullptr;Player*getSource(){return p;}GroupReference*next(){return following;}};
struct Group {GroupReference first,second;Group(Player*a,Player*b):first{a,&second},second{b}{a->group=b->group=this;}GroupReference*GetFirstMember(){return &first;}};
template<class T>struct Cached {T value;T Get(){return value;}};
struct Context {Cached<std::list<ObjectGuid>>objects;template<class T>Cached<T>*GetValue(const char*){return &objects;}};
struct PlayerbotAI {Player*bot;bool real=false,move=true;Context context;std::map<unsigned,GameObject*>objects;
 Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool CanMove(){return move;}Context*GetAiObjectContext(){return &context;}
 GameObject*GetGameObject(unsigned guid){auto p=objects.find(guid);return p==objects.end()?nullptr:p->second;}};
struct Facade {bool isSpawned(GameObject*go){return go->spawned;}}sServerFacade;
struct {float sightDistance=60;}sPlayerbotAIConfig;
namespace ai {
 struct Event {Player*getOwner(){return nullptr;}};
 struct UseItemIdAction {PlayerbotAI*ai;Player*bot;unsigned item=0;UseItemIdAction(PlayerbotAI*a):ai(a),bot(a->bot){}
  void Qualify(int32 i){item=i;}bool isPossible(){return bot->eligible&&!bot->cooldown.count(item)&&(bot->itemCheat||bot->HasItemCount(item,1));}
  bool isUseful(){return !bot->skip;}
  bool UseItem(Player*,unsigned id,GameObject*go){++bot->used;bot->usedItem=id;bot->usedRune=go->guid;go->state=1;
   if(id==17333)--bot->bag[id];else bot->cooldown.insert(id);return true;}};
 bool MoltenCoreDouseItemAvailable(PlayerbotAI*,uint32=0);GameObject*MoltenCoreRuneTarget(PlayerbotAI*,bool);
 struct MoveToMCRuneAction {PlayerbotAI*ai;Player*bot;bool isUseful();bool Execute(Event&);
  bool MoveTo(unsigned,float,float,float){++bot->moves;return true;}};
 struct DouseMCRuneAction:UseItemIdAction {DouseMCRuneAction(PlayerbotAI*a,unsigned id):UseItemIdAction(a){Qualify(id);}unsigned GetItemId(){return item;}
  bool isPossible();bool isUseful();bool Execute(Event&);};
}
using namespace ai;
__METHODS__
int main(){
 InstanceData instance;Map map{&instance},otherMap{&instance};Player bot,member;bot.map=member.map=&map;Group group(&bot,&member);
 PlayerbotAI ai{&bot};GameObject rune;rune.guid=10;rune.map=&map;rune.x=10;ai.objects={{10,&rune}};ai.context.objects.value={10};
 MoveToMCRuneAction movement{&ai,&bot};DouseMCRuneAction eternal{&ai,22754},aqual{&ai,17333};Event event;instance.states[1]=DONE;
 // Item cheats must never grant a douse item or make an empty bot chase runes.
 assert(!MoltenCoreDouseItemAvailable(&ai)&&!movement.isUseful()&&!movement.Execute(event)&&!aqual.Execute(event));
 assert(bot.used==0&&bot.moves==0);bot.bag[22754]=1;
#ifdef MANGOSBOT_TWO
 assert(!MoltenCoreDouseItemAvailable(&ai)&&!MoltenCoreRuneTarget(&ai,false)&&!movement.Execute(event)&&!eternal.Execute(event));
#else
 assert(MoltenCoreDouseItemAvailable(&ai)&&movement.isUseful()&&movement.Execute(event));
 bot.cooldown.insert(22754);assert(!movement.isUseful());bot.bag[17333]=1;assert(movement.isUseful());
 assert(!eternal.isPossible()&&aqual.isPossible());bot.cooldown.clear();
 bot.eligible=false;assert(!movement.isUseful());bot.eligible=true;bot.skip=true;assert(!movement.isUseful());bot.skip=false;
 bot.casting=true;assert(!movement.isUseful());bot.casting=false;
 member.combat=true;assert(!movement.isUseful());member.instance=2;assert(movement.isUseful());member.instance=1;member.combat=false;
 bot.combat=true;assert(!movement.isUseful());bot.combat=false;bot.teleport=true;assert(!movement.isUseful());bot.teleport=false;
 bot.alive=false;assert(!movement.isUseful());bot.alive=true;ai.real=true;assert(!movement.isUseful());ai.real=false;
 instance.states[1]=0;assert(!movement.isUseful());instance.states[1]=SPECIAL;assert(!movement.isUseful());instance.states[1]=DONE;
 rune.trapped=true;assert(!movement.isUseful());rune.trapped=false;
 GameObject flames; rune.trap=&flames;assert(!movement.isUseful());
 flames.spawned=false;assert(movement.isUseful());flames.spawned=true;flames.loot=2;assert(movement.isUseful());rune.trap=nullptr;
 rune.inUse=true;assert(!movement.isUseful());rune.inUse=false;
 rune.state=1;assert(!movement.isUseful());rune.state=0;rune.loot=1;assert(!movement.isUseful());rune.loot=0;
 rune.phase=2;assert(!movement.isUseful());rune.phase=1;rune.instance=2;assert(!movement.isUseful());rune.instance=1;
 rune.map=&otherMap;assert(!movement.isUseful());rune.map=&map;rune.spawned=false;assert(!movement.isUseful());rune.spawned=true;
 rune.x=70;assert(!movement.isUseful());rune.x=4;assert(!movement.isUseful()&&eternal.isUseful());
 // A trigger may have fired before an inventory/cooldown change: execution rechecks.
 bot.bag.clear();assert(!eternal.Execute(event)&&bot.used==0);bot.bag[22754]=1;
 assert(eternal.Execute(event)&&bot.usedItem==22754&&bot.usedRune==10&&bot.bag[22754]==1);
 assert(!eternal.Execute(event)&&bot.used==1); // already doused/cooldown, no loop
 rune.state=0;bot.cooldown.clear();bot.bag.clear();bot.bag[17333]=1;
 assert(aqual.Execute(event)&&bot.bag[17333]==0);rune.state=0;assert(!aqual.Execute(event));
 bot.bag[22754]=1;instance.states.clear();
 for(auto pair:{std::pair<unsigned,unsigned>{176956,1},{176957,2},{176955,3},{176953,4},{176952,5},{176954,6},{176951,7}}){
  rune.entry=pair.first;instance.states[pair.second]=DONE;assert(MoltenCoreRuneTarget(&ai,true)==&rune);
  instance.states[pair.second]=SPECIAL;assert(!MoltenCoreRuneTarget(&ai,true));instance.states.clear();}
#endif
 std::cout<<"PASS actual MC rune bodies: real inventory, both items, cooldown/eligibility, combat/cast guards, native encounter state, object lifecycle, execution race, Wrath disabled\n";
}
'''.replace('__METHODS__', methods)
for era in ('ZERO', 'ONE', 'TWO'):
    with tempfile.TemporaryDirectory(prefix='mc-runes-') as directory:
        path = Path(directory)
        (path / 'test.cpp').write_text(code)
        subprocess.run(['cl', '/nologo', '/std:c++17', '/EHsc', '/DMANGOSBOT_' + era, 'test.cpp', '/Fe:test.exe'], cwd=path, check=True)
        subprocess.run([str(path / 'test.exe')], cwd=path, check=True)
