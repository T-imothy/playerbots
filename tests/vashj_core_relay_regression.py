"""Exercise actual Vashj planning, item/loot admission and execution methods."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block
root = Path(__file__).resolve().parents[1]
value = (root/'playerbot/strategy/values/VashjCoreValue.cpp').read_text()
action = (root/'playerbot/strategy/actions/VashjCoreAction.cpp').read_text()
methods = '\n'.join(block(value, name) for name in (
    'Unit* ai::FindVashjCorePhase(', 'bool ai::IsVashjGenerator(', 'bool ai::CanReceiveVashjCore(',
    'bool ai::CanLootVashjCore(', 'bool ai::CanPassVashjCore(', 'VashjCorePlan VashjCoreValue::Calculate('))
methods += '\n'+'\n'.join(block(action,'bool VashjCoreAction::'+name+'(') for name in ('GetPlan','isUseful','Execute'))
methods += '\n'+block((root/'playerbot/strategy/values/VashjStriderHazards.cpp').read_text(),'void ai::AppendVashjStriderHazards(')
code = r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <list>
#include <map>
#include <set>
#include <string>
#include <vector>
using uint32=unsigned;using ItemPosCountVec=std::vector<int>;
struct ObjectGuid{unsigned id=0;ObjectGuid(unsigned i=0):id(i){}bool IsEmpty()const{return !id;}
 bool operator==(ObjectGuid g)const{return id==g.id;}bool operator!=(ObjectGuid g)const{return id!=g.id;}bool operator<(ObjectGuid g)const{return id<g.id;}};
enum{GAMEOBJECT_FLAGS,GO_FLAG_NO_INTERACT=1,GO_FLAG_IN_USE=2,UNIT_DYNAMIC_FLAGS=3,UNIT_DYNFLAG_LOOTABLE=4,
 NULL_BAG=0,NULL_SLOT=0,EQUIP_ERR_OK=0,LOOT_SLOT_NORMAL=0,LOOT_SLOT_OWNER=3,CMSG_LOOT=5,INTERACTION_DISTANCE=5};
enum class BotState{BOT_STATE_COMBAT};
class PlayerbotAI;struct Group;struct Player;struct Session;
struct Unit{virtual ~Unit(){}ObjectGuid guid,spawner;unsigned entry=0,map=548,instance=1;float x=0,y=0,z=0;
 bool world=true,alive=true,combat=true,charm=false,player=false,los=true;std::set<unsigned>auras;Unit*victim=nullptr;std::set<Unit*>attackers;
 Unit*GetVictim(){return victim;}std::set<Unit*>&getAttackers(){return attackers;}
 Unit*GetSpellAuraHolder(unsigned aura,ObjectGuid owner){return owner==guid&&HasAura(aura)?this:nullptr;}
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charm;}
 bool IsPlayer(){return player;}bool HasAura(unsigned id){return auras.count(id);}unsigned GetEntry(){return entry;}
 ObjectGuid GetObjectGuid(){return guid;}ObjectGuid GetSpawnerGuid(){return spawner;}unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}
 bool IsInMap(Unit*u){return u&&map==u->map&&instance==u->instance;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}
 float GetDistance(Unit*u){return GetDistance(u->x,u->y,u->z);}bool IsWithinLOSInMap(Unit*u){return los&&u->los;}
 bool IsWithinLOS(float,float,float,bool){return los;}float GetCollisionHeight(){return 2;}};
struct Creature:Unit{unsigned flags=UNIT_DYNFLAG_LOOTABLE;bool HasFlag(unsigned,unsigned f){return flags&f;}};
struct GOInfo{unsigned lock=1718;unsigned GetLockId(){return lock;}};
struct GameObject:Unit{bool spawned=true;unsigned flags=0;GOInfo info;bool IsSpawned(){return spawned;}
 bool HasFlag(unsigned,unsigned f){return flags&f;}GOInfo*GetGOInfo(){return &info;}
#ifndef MANGOSBOT_ZERO
 bool IsAtInteractDistance(Unit*p){return GetDistance(p)<=5;}
#endif
};
struct ItemPrototype{};struct Item{ItemPrototype proto;const ItemPrototype*GetProto(){return &proto;}};
struct Player:Unit{Player(){player=true;}Group*group=nullptr;PlayerbotAI*ai=nullptr;Session*session=nullptr;ObjectGuid loot;
 bool teleport=false,tank=false,heal=false,moving=false,casting=false,ready=true;unsigned cores=0,capacity=0;Item item;
 bool IsBeingTeleported(){return teleport;}Group*GetGroup(){return group;}PlayerbotAI*GetPlayerbotAI(){return ai;}
 bool HasItemCount(unsigned,unsigned){return cores>0;}unsigned CanStoreNewItem(int,int,ItemPosCountVec&,unsigned,unsigned){return capacity;}
 bool IsMoving(){return moving;}bool IsNonMeleeSpellCasted(bool){return casting;}ObjectGuid GetLootGuid(){return loot;}
 Item*GetItemByEntry(unsigned){return cores?&item:nullptr;}bool IsSpellReady(unsigned,const ItemPrototype*){return ready;}Session*GetSession(){return session;}};
struct GroupReference{Player*p;GroupReference*n=nullptr;Player*getSource(){return p;}GroupReference*next(){return n;}};
struct Group{std::vector<GroupReference>refs;GroupReference*GetFirstMember(){for(size_t i=0;i<refs.size();++i)refs[i].n=i+1<refs.size()?&refs[i+1]:nullptr;return refs.empty()?nullptr:&refs[0];}
 void Add(Player*p){refs.push_back({p});p->group=this;}};
namespace encounter{struct Point{float x=0,y=0,z=0;};}
struct WorldPosition{float x,y,z;WorldPosition(Unit*u):x(u->x),y(u->y),z(u->z){}};
namespace ai{
using HazardPosition=std::pair<WorldPosition,float>;
float panicRadius=8;float NativeEncounterSpellRadius(unsigned id){assert(id==38258);return panicRadius;}
void AppendVashjStriderHazards(PlayerbotAI*,std::list<HazardPosition>&);
struct EncounterPosition{bool active=false;unsigned map=0,instance=0,spell=0;ObjectGuid boss;encounter::Point destination;};
enum class VashjCoreTask{None,Collect,Receive,Deliver};
struct VashjCorePlan{VashjCoreTask task=VashjCoreTask::None;EncounterPosition position;ObjectGuid carrier,receiver,generator,corpse;};
}
template<class T>struct Value{T data{};T Get(){return data;}};
template<>struct Value<std::set<uint32>&>{std::set<uint32>data;std::set<uint32>&Get(){return data;}};
struct Context{Value<ObjectGuid>attack;Value<Unit*>marked;Value<std::set<uint32>&>skip;Value<ai::VashjCorePlan>plan;
 template<class T>Value<T>*GetValue(const char*){if constexpr(std::is_same_v<T,ObjectGuid>)return &attack;
 else if constexpr(std::is_same_v<T,Unit*>)return &marked;else if constexpr(std::is_same_v<T,std::set<uint32>&>)return &skip;else return &plan;}};
std::vector<Unit*>units;std::vector<GameObject*>objects;
class PlayerbotAI{public:Player*bot;Context context;bool real=false,move=true,dungeon=true,stay=false,guard=false;unsigned stops=0,interrupts=0;
 PlayerbotAI(Player*p):bot(p){p->ai=this;}Player*GetBot(){return bot;}Context*GetAiObjectContext(){return &context;}
 bool IsRealPlayer(){return real;}bool CanMove(){return move;}bool IsTank(Player*p){return p->tank;}bool IsHeal(Player*p){return p->heal;}
 bool HasStrategy(std::string s,BotState){return s=="dungeon"?dungeon:s=="stay"?stay:s=="guard"?guard:false;}
 Unit*GetUnit(ObjectGuid g){for(auto*u:units)if(u->guid==g)return u;return nullptr;}
 Creature*GetCreature(ObjectGuid g){return dynamic_cast<Creature*>(GetUnit(g));}
 GameObject*GetGameObject(ObjectGuid g){for(auto*gob:objects)if(gob->guid==g)return gob;return nullptr;}
 void StopMoving(){bot->moving=false;++stops;}void InterruptSpell(){bot->casting=false;++interrupts;}};
namespace MaNGOS{
struct AllCreaturesOfEntryInRangeCheck{Unit*focus;unsigned entry;float range;AllCreaturesOfEntryInRangeCheck(Unit*p,unsigned e,float r):focus(p),entry(e),range(r){}
 bool operator()(Unit*p){return p->entry==entry&&focus->GetDistance(p)<=range;}};
template<class C>struct UnitListSearcher{std::list<Unit*>&out;C&check;UnitListSearcher(std::list<Unit*>&o,C&c):out(o),check(c){}
 void Run(){for(auto*u:units)if(check(u))out.push_back(u);}};
template<class C>struct GameObjectListSearcher{std::list<GameObject*>&out;C&check;GameObjectListSearcher(std::list<GameObject*>&o,C&c):out(o),check(c){}
 void Run(){for(auto*u:objects)if(check(u))out.push_back(u);}};
}
namespace Cell{template<class S>void VisitAllObjects(Unit*,S&s,float){s.Run();}}
struct SpellEntry{unsigned rangeIndex=1;};SpellEntry passSpell;float passRange=30;bool haveSpell=true;
struct SpellStore{template<class T>const T*LookupEntry(unsigned){return haveSpell?&passSpell:nullptr;}}sSpellTemplate;
struct RangeStore{float*LookupEntry(unsigned){return &passRange;}}sSpellRangeStore;
float GetSpellMaxRange(float*r){return *r;}
struct Loot;struct LootItem{unsigned itemId=31088,slot=LOOT_SLOT_NORMAL;bool isBlocked=false;unsigned GetSlotTypeForSharedLoot(Player*,Loot*){return slot;}};
using LootItemList=std::vector<LootItem*>;
struct Loot{bool allowed=true;LootItemList items;bool CanLoot(Player*){return allowed;}void GetLootItemsListFor(Player*,LootItemList&out){out=items;}};
struct LootMgr{std::map<unsigned,Loot*>loot;Loot*GetLoot(Player*,ObjectGuid g){return loot[g.id];}}sLootMgr;
struct WorldPacket{ObjectGuid guid;WorldPacket(unsigned){}WorldPacket&operator<<(ObjectGuid g){guid=g;return *this;}};
struct Session{unsigned opened=0;ObjectGuid last;void HandleLootOpcode(WorldPacket&p){++opened;last=p.guid;}};
struct Event{};
bool pathValid=true;unsigned pathCalls=0,nativeCalls=0;bool nativeAllowed=true;GameObject*lastGO=nullptr;Unit*lastTarget=nullptr;
namespace ai{
bool ValidateEncounterDestination(PlayerbotAI*,EncounterPosition&){++pathCalls;return pathValid;}
bool UseNativeEncounterItem(Player*bot,Item*,Unit*target,GameObject*object){++nativeCalls;lastGO=object;lastTarget=target;
 if(!nativeAllowed)return false;bot->cores=0;if(target)static_cast<Player*>(target)->cores++;if(object)object->flags|=GO_FLAG_NO_INTERACT;return true;}
Unit*FindVashjCorePhase(PlayerbotAI*);bool IsVashjGenerator(Player*,GameObject*);bool CanReceiveVashjCore(PlayerbotAI*,Player*);
bool CanLootVashjCore(Player*,Creature*,Unit*);bool CanPassVashjCore(Player*,Player*,GameObject*);
struct VashjCoreValue{PlayerbotAI*ai;Player*bot;VashjCoreValue(PlayerbotAI*p):ai(p),bot(p->GetBot()){}VashjCorePlan Calculate();};
struct VashjCoreAction{PlayerbotAI*ai;Player*bot;unsigned moves=0,duration=0;encounter::Point destination;
 VashjCoreAction(PlayerbotAI*p):ai(p),bot(p->GetBot()){}static bool GetPlan(PlayerbotAI*,VashjCorePlan&);bool isUseful();bool Execute(Event&);
 bool IsReaction(){return false;}void SetDuration(unsigned d){duration=d;}
 bool MoveTo(unsigned,float x,float y,float z,bool,bool,bool,bool){destination={x,y,z};++moves;return true;}};
}
using namespace ai;
__METHODS__
int main(){Player carrier,receiver,other;carrier.guid=1;receiver.guid=2;other.guid=3;
 PlayerbotAI carrierAI(&carrier),receiverAI(&receiver),otherAI(&other);Group group;group.Add(&carrier);group.Add(&receiver);group.Add(&other);
 Creature boss;boss.guid=10;boss.entry=21212;boss.auras.insert(38112);boss.x=20;
 GameObject generator;generator.guid=20;generator.entry=185051;generator.x=60;objects={&generator};
 units={&carrier,&receiver,&other,&boss};carrier.cores=1;receiver.x=20;other.x=0;Event event;
 Session session;carrier.session=&session;receiver.session=&session;other.session=&session;
#ifdef MANGOSBOT_ZERO
 assert(!FindVashjCorePhase(&carrierAI));assert(VashjCoreValue(&carrierAI).Calculate().task==VashjCoreTask::None);
 std::cout<<"PASS: Vashj disabled in Classic\n";return 0;
#endif
 assert(FindVashjCorePhase(&carrierAI)==&boss);
 assert(CanPassVashjCore(&carrier,&receiver,&generator));receiver.x=0;assert(!CanPassVashjCore(&carrier,&receiver,&generator));
 receiver.x=-10;assert(!CanPassVashjCore(&carrier,&receiver,&generator));receiver.x=31;assert(!CanPassVashjCore(&carrier,&receiver,&generator));
 receiver.x=20;receiver.los=false;assert(!CanPassVashjCore(&carrier,&receiver,&generator));receiver.los=true;
 auto plan=VashjCoreValue(&carrierAI).Calculate();assert(plan.task==VashjCoreTask::Deliver&&plan.receiver==receiver.guid);
 carrierAI.context.plan.data=plan;VashjCoreAction deliver(&carrierAI);
 receiver.capacity=1;assert(!deliver.isUseful()&&!deliver.Execute(event));receiver.capacity=0;
 receiver.teleport=true;assert(!deliver.Execute(event));receiver.teleport=false;
 receiver.heal=true;assert(!CanReceiveVashjCore(&carrierAI,&receiver));receiver.heal=false;
 receiver.tank=true;assert(!CanReceiveVashjCore(&carrierAI,&receiver));receiver.tank=false;
 receiverAI.context.attack.data=boss.guid;assert(!CanReceiveVashjCore(&carrierAI,&receiver));receiverAI.context.attack.data={};
 receiverAI.context.skip.data.insert(31088);assert(!CanReceiveVashjCore(&carrierAI,&receiver));receiverAI.context.skip.data.clear();
 receiverAI.stay=true;assert(!CanReceiveVashjCore(&carrierAI,&receiver));receiverAI.stay=false;
 carrier.casting=true;assert(!deliver.Execute(event));carrier.casting=false;
 generator.flags=GO_FLAG_NO_INTERACT;assert(!deliver.Execute(event));generator.flags=0;
 boss.auras.clear();assert(!deliver.Execute(event));boss.auras.insert(38112);
 pathValid=false;assert(!deliver.Execute(event)&&carrier.cores==1);pathValid=true;
 nativeAllowed=false;assert(!deliver.Execute(event)&&carrier.cores==1);nativeAllowed=true;
 assert(deliver.Execute(event)&&carrier.cores==0&&receiver.cores==1&&lastTarget==&receiver&&!lastGO);
 assert(!deliver.Execute(event)); // An old cached plan cannot manufacture another core.
 receiver.x=58;receiverAI.context.plan.data=VashjCoreValue(&receiverAI).Calculate();VashjCoreAction open(&receiverAI);
 assert(open.Execute(event)&&receiver.cores==0&&lastGO==&generator&&!lastTarget);
 assert(!open.Execute(event)&&VashjCoreValue(&carrierAI).Calculate().task==VashjCoreTask::None);
 generator.flags=0;carrier.cores=1;receiver.x=0;other.heal=true;
 plan=VashjCoreValue(&receiverAI).Calculate();assert(plan.task==VashjCoreTask::Receive&&plan.position.destination.x==26);
 receiverAI.context.plan.data=plan;VashjCoreAction receive(&receiverAI);assert(receive.Execute(event)&&receive.moves==1);
 pathValid=false;assert(!receive.Execute(event));pathCalls=0;assert(VashjCoreValue(&receiverAI).Calculate().task==VashjCoreTask::None);assert(pathCalls==8);pathValid=true;
 receiver.x=20;plan=VashjCoreValue(&receiverAI).Calculate();assert(plan.task==VashjCoreTask::Receive&&plan.position.destination.x==20);
 receiverAI.context.plan.data=plan;assert(!receive.isUseful());receiver.moving=true;assert(receive.isUseful());assert(receive.Execute(event)&&!receiver.moving);
 carrier.cores=0;assert(!receive.Execute(event));
 // Two carriers reserve distinct receiving bots in GUID order.
 Player second,spare;second.guid=4;spare.guid=5;PlayerbotAI secondAI(&second),spareAI(&spare);group.Add(&second);group.Add(&spare);
 second.x=0;second.y=3;spare.x=15;spare.y=3;units.push_back(&second);units.push_back(&spare);carrier.cores=second.cores=1;
 auto one=VashjCoreValue(&carrierAI).Calculate(),two=VashjCoreValue(&secondAI).Calculate();
 assert(one.receiver==receiver.guid&&two.receiver==spare.guid&&one.receiver!=two.receiver);
 carrier.cores=second.cores=0;second.heal=spare.heal=true;receiver.x=10;
 Creature corpse;corpse.guid=30;corpse.entry=22009;corpse.alive=false;corpse.spawner=boss.guid;corpse.x=11;units.push_back(&corpse);
 LootItem key;Loot loot;loot.items={&key};sLootMgr.loot[corpse.guid.id]=&loot;
 assert(CanLootVashjCore(&receiver,&corpse,&boss));key.isBlocked=true;assert(!CanLootVashjCore(&receiver,&corpse,&boss));key.isBlocked=false;
 key.slot=1;assert(!CanLootVashjCore(&receiver,&corpse,&boss));key.slot=LOOT_SLOT_NORMAL;
 corpse.spawner=99;assert(!CanLootVashjCore(&receiver,&corpse,&boss));corpse.spawner=boss.guid;
 loot.allowed=false;assert(!CanLootVashjCore(&receiver,&corpse,&boss));loot.allowed=true;
 plan=VashjCoreValue(&receiverAI).Calculate();assert(plan.task==VashjCoreTask::Collect&&plan.corpse==corpse.guid);
 receiverAI.context.plan.data=plan;VashjCoreAction collect(&receiverAI);assert(collect.Execute(event)&&session.last==corpse.guid);
 receiver.loot=999;assert(!collect.Execute(event));receiver.loot={};loot.allowed=false;assert(!collect.Execute(event));loot.allowed=true;
 receiver.instance=2;assert(!collect.Execute(event));receiver.instance=1;
 Creature strider;strider.guid=40;strider.entry=22056;strider.spawner=boss.guid;strider.auras.insert(38257);strider.victim=&receiver;units.push_back(&strider);
 receiver.attackers.insert(&strider);assert(!CanReceiveVashjCore(&carrierAI,&receiver));receiver.attackers.clear();
 std::list<HazardPosition>hazards;AppendVashjStriderHazards(&receiverAI,hazards);assert(hazards.size()==1&&hazards.front().second==16);
 hazards.clear();AppendVashjStriderHazards(&carrierAI,hazards);assert(hazards.size()==1&&hazards.front().second==12);
 strider.x=35;hazards.clear();AppendVashjStriderHazards(&receiverAI,hazards);assert(hazards.front().first.x==35);
 strider.alive=false;hazards.clear();AppendVashjStriderHazards(&receiverAI,hazards);assert(hazards.empty());strider.alive=true;
 strider.spawner=99;AppendVashjStriderHazards(&receiverAI,hazards);assert(hazards.empty());strider.spawner=boss.guid;
 strider.auras.clear();AppendVashjStriderHazards(&receiverAI,hazards);assert(hazards.empty());strider.auras.insert(38257);
 boss.auras.clear();AppendVashjStriderHazards(&receiverAI,hazards);assert(hazards.empty());boss.auras.insert(38112);
 panicRadius=0;AppendVashjStriderHazards(&receiverAI,hazards);assert(hazards.empty());panicRadius=8;
 std::cout<<"PASS: native core relay, unique receivers, permissions, lifecycle, dispatch and moving Strider hazards\n";
}
'''
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='vashj-core-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code.replace('__METHODS__',methods))
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
strategy=(root/'playerbot/strategy/generic/DungeonStrategy.cpp').read_text()
assert strategy.count('new TriggerNode("vashj core relay"')==2
assert strategy.count('new PreserveVashjCoreMultiplier(ai)')==2
packet=(root/'playerbot/strategy/generic/WorldPacketHandlerStrategy.cpp').read_text()
assert 'InitNonCombatTriggers(triggers)' in block(packet,'void WorldPacketHandlerStrategy::InitCombatTriggers(')
assert '"loot response"' in packet and '"store loot"' in packet
loot=(root/'playerbot/strategy/actions/LootAction.cpp').read_text().split('bool StoreLootAction::IsLootAllowed(',1)[1].split('bool ReleaseLootAction::Execute(',1)[0]
assert loot.index('"skip loot list"')<loot.index('itemQualifier.GetId() == 31088')
print('PASS: combat/reaction wiring, combat loot response and explicit loot exclusions')
