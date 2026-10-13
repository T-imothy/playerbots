"""Actual native-vendor delegation, warrior threat selection and Classic hybrid choice."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
R=Path(__file__).resolve().parents[1]
repair=(R/'playerbot/strategy/actions/RepairAllAction.cpp').read_text()
warrior=(R/'playerbot/strategy/warrior/WarriorActions.h').read_text()
mage=(R/'playerbot/strategy/mage/ArcaneMageStrategy.cpp').read_text()
methods='\n'.join(block(repair,x) for x in ('Creature* RaidRepairAction::GetRepairNpc(', 'bool RaidRepairAction::isUseful(', 'bool RaidRepairAction::Execute('))
methods+='\n'+block(warrior,'class CastBattleShoutTauntAction')+';\n'+block(warrior,'class CastWhirlwindAction')+';'
methods+='\n'+block((R/'playerbot/strategy/mage/MageCombatPolicy.h').read_text(),'inline bool ClassicMageFrostPrimary(')
methods+='\n'+block((R/'playerbot/strategy/generic/MoltenCoreDungeonStrategies.cpp').read_text(),'void MoltenCoreDungeonStrategy::InitCombatTriggers(')
classic=block(mage,'NextAction** ArcaneMageStrategy::GetDefaultCombatActions(')
code=r'''
#include <cassert>
#include <cmath>
#include <list>
#include <map>
#include <string>
#include <set>
#include <iostream>
using uint8=unsigned char;using uint32=unsigned;using ObjectGuid=unsigned;
enum {EQUIPMENT_SLOT_START=0,EQUIPMENT_SLOT_END=2,INVENTORY_SLOT_BAG_0=0,ITEM_FIELD_MAXDURABILITY=0,ITEM_FIELD_DURABILITY=1,TYPEID_UNIT=1,UNIT_NPC_FLAGS=1,UNIT_NPC_FLAG_REPAIR=2};
enum {CLASS_WARRIOR=1,CLASS_PALADIN=2,CLASS_HUNTER=3,CLASS_ROGUE=4,CLASS_PRIEST=5,CLASS_DEATH_KNIGHT=6,CLASS_SHAMAN=7,CLASS_MAGE=8,CLASS_WARLOCK=9,CLASS_DRUID=11};
constexpr float INTERACTION_DISTANCE=5;struct Event{};
struct Unit{virtual ~Unit()=default;bool world=true,alive=true,charm=false,friendly=true,repair=true;float distance=10;unsigned guid=1,type=TYPEID_UNIT;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool HasCharmer(){return charm;}unsigned GetTypeId(){return type;}bool HasFlag(unsigned,unsigned){return repair;}ObjectGuid GetObjectGuid(){return guid;}};
struct Creature:Unit{};struct Item{unsigned maximum=100,durability=0;unsigned GetUInt32Value(unsigned i){return i==0?maximum:durability;}};
struct Player;struct GroupReference{Player*p;GroupReference*nextRef=nullptr;Player*getSource(){return p;}GroupReference*next(){return nextRef;}};
struct Group{bool raid=true;GroupReference*first=nullptr;bool IsRaidGroup(){return raid;}GroupReference*GetFirstMember(){return first;}};
struct Player:Unit{bool combat=false,transfer=false,same=true,tank=false;unsigned cls=1;unsigned getClass(){return cls;}unsigned money=1000;Group*group=nullptr;Item*items[2]={};Creature*vendor=nullptr;std::set<unsigned>spells;
 bool IsInCombat(){return combat;}bool IsBeingTeleported(){return transfer;}Group*GetGroup(){return group;}unsigned GetMoney(){return money;}bool IsInMap(Unit*){return same;}float GetDistance(Unit*u){return u->distance;}
 Item*GetItemByPos(unsigned,unsigned slot){return items[slot];}Creature*GetNPCIfCanInteractWith(unsigned,unsigned){return vendor&&vendor->distance<5?vendor:nullptr;}
 bool HasSpell(unsigned id){return spells.count(id);}};
std::list<ObjectGuid>npcs;template<class T>struct Cached{T Get(){return npcs;}};struct Context{template<class T>Cached<T>*GetValue(const char*){static Cached<T>v;return &v;}};
struct PlayerbotAI{Context context;Context*GetAiObjectContext(){return &context;}Player*bot;PlayerbotAI(Player*p):bot(p){}bool human=false,owned=true,movable=true,pvp=false;unsigned frost=0,nearCalls=0,repairs=0;std::set<std::string>ready,known;unsigned targets=1;
 Player*GetBot(){return bot;}bool IsRanged(Player*){return true;}bool IsRealPlayer(){return human;}bool HasRealPlayerMaster(){return owned;}bool CanMove(){return movable;}bool IsTank(Player*p){return p->tank;}bool HasSpell(const char*n){return known.count(n);}bool CanCastSpell(const char*n,Unit*,int){return ready.count(n);}bool IsInPvp(){return pvp;}std::map<unsigned,Unit*>units;Unit*GetUnit(unsigned id){return units.count(id)?units[id]:nullptr;}};
struct AiFactory{static std::map<unsigned,int>GetPlayerSpecTabs(Player*p){return {{2,int(p->spells.count(999)?20:0)}};}};
struct Facade{bool IsFriendlyTo(Player*,Unit*u){return u->friendly;}}sServerFacade;
struct{unsigned reactDelay=100;}sPlayerbotAIConfig;
template<class T>T value(const char*){return npcs;}
#define AI_VALUE(T,n) value<T>(n)
struct MovementAction{PlayerbotAI*ai;Player*bot;bool stay=false;MovementAction(PlayerbotAI*a):ai(a),bot(a->bot){}bool isUseful(){return !stay;}bool MoveNear(Creature*,float r){assert(r==4);++ai->nearCalls;return true;}void SetDuration(unsigned d){assert(d==100);}};
struct RaidRepairAction:MovementAction{using MovementAction::MovementAction;Creature*GetRepairNpc();bool isUseful();bool Execute(Event&);};
// The existing RepairAllAction is unchanged; this boundary records delegation,
// not a substitute repair implementation. Native costs remain in the core.
struct RepairAllAction{PlayerbotAI*ai;RepairAllAction(PlayerbotAI*a):ai(a){}bool Execute(Event&){++ai->repairs;return true;}};
enum class ActionThreatType{ACTION_THREAT_SINGLE,ACTION_THREAT_AOE};
struct CastMeleeSpellAction{PlayerbotAI*ai;Player*bot;CastMeleeSpellAction(PlayerbotAI*a,const char*):ai(a),bot(a->bot){}virtual bool isUseful(){return true;}Unit*GetTarget(){return bot;}};
struct CastSafeMeleeAreaAction:CastMeleeSpellAction{float radius,range=0;CastSafeMeleeAreaAction(PlayerbotAI*a,const char*n,float r):CastMeleeSpellAction(a,n),radius(r){}virtual std::string GetTargetName(){return "self target";}virtual ActionThreatType getThreatType(){return ActionThreatType::ACTION_THREAT_AOE;}};
bool MeleeOpportunity(PlayerbotAI*a){return a->movable;}unsigned SafeMeleeTargetCount(PlayerbotAI*a,float){return a->targets;}
struct NextAction{std::string name;NextAction(const char*n,float):name(n){}static NextAction**array(int,NextAction*p,void*){return new NextAction*[2]{p,nullptr};}};constexpr float ACTION_IDLE=1,ACTION_HIGH=40,ACTION_DISPEL=60;
struct TriggerNode{std::string name;NextAction**actions;TriggerNode(const char*n,NextAction**a):name(n),actions(a){}~TriggerNode(){delete actions[0];delete[]actions;}};
struct MoltenCoreDungeonStrategy{PlayerbotAI*ai;void InitCombatTriggers(std::list<TriggerNode*>&);};
struct ArcaneMageStrategy{PlayerbotAI*ai;Player*bot;NextAction**GetDefaultCombatActions();};
__METHODS__
#ifdef MANGOSBOT_ZERO
__CLASSIC__
#endif
int main(){Player bot,member;Group group;GroupReference one{&bot},two{&member};one.nextRef=&two;group.first=&one;bot.group=member.group=&group;
 Item damaged,cosmetic;cosmetic.maximum=0;bot.items[0]=&damaged;bot.items[1]=&cosmetic;PlayerbotAI ai{&bot};Creature vendor;ai.units={{1,&vendor}};bot.vendor=&vendor;npcs={1};RaidRepairAction repair(&ai);Event event;
 assert(repair.isUseful()&&repair.Execute(event)&&ai.nearCalls==1&&ai.repairs==0); // approach normal vendor first
 vendor.distance=4;assert(repair.Execute(event)&&ai.repairs==1&&bot.money==1000); // delegate; never synthesize money or gear
 for(unsigned fault=0;fault<10;++fault){bot.world=bot.alive=bot.same=group.raid=ai.owned=true;bot.combat=member.combat=bot.transfer=bot.charm=ai.human=false;bot.money=1000;vendor.friendly=vendor.repair=true;vendor.distance=4;
  if(fault==0)bot.world=false;if(fault==1)bot.alive=false;if(fault==2)bot.transfer=true;if(fault==3)bot.charm=true;if(fault==4)bot.combat=true;if(fault==5)member.combat=true;if(fault==6)group.raid=false;if(fault==7)ai.owned=false;if(fault==8)bot.money=0;if(fault==9)vendor.friendly=false;
  assert(!repair.isUseful()&&!repair.Execute(event));}
 vendor.friendly=true;bot.money=1000;repair.stay=true;assert(!repair.isUseful());repair.stay=false;damaged.durability=100;assert(!repair.isUseful());damaged.durability=0;
 bot.combat=false;CastBattleShoutTauntAction shout(&ai);assert(!shout.isUseful());bot.tank=true;assert(!shout.isUseful());bot.combat=true;assert(shout.isUseful());
 ai.known={"bloodthirst"};ai.ready={"bloodthirst"};assert(!shout.isUseful());ai.ready.clear();assert(shout.isUseful());bot.tank=false;assert(!shout.isUseful());
 CastWhirlwindAction ww(&ai);ai.targets=1;assert(ww.getThreatType()==ActionThreatType::ACTION_THREAT_SINGLE);ai.targets=2;assert(ww.getThreatType()==ActionThreatType::ACTION_THREAT_AOE);
#ifdef MANGOSBOT_ZERO
 ArcaneMageStrategy mage{&ai,&bot};assert(mage.GetDefaultCombatActions()[0]->name=="arcane missiles");bot.spells={12042,999};assert(mage.GetDefaultCombatActions()[0]->name=="frostbolt");ai.pvp=true;assert(mage.GetDefaultCombatActions()[0]->name=="arcane missiles");
#endif
 MoltenCoreDungeonStrategy strategy{&ai};
#ifdef MANGOSBOT_ZERO
 const char*warlockArea="rain of fire";
#else
 const char*warlockArea="seed of corruption";
#endif
 for(auto cls:{CLASS_WARRIOR,CLASS_PALADIN,CLASS_HUNTER,CLASS_ROGUE,CLASS_SHAMAN,CLASS_MAGE,CLASS_WARLOCK,CLASS_DRUID}){
  bot.cls=cls;std::list<TriggerNode*>triggers;strategy.InitCombatTriggers(triggers);auto t=triggers.front();assert(t->name=="molten core imp pack"&&t->actions[0]->name!="arcane missiles"&&t->actions[0]->name!="frostbolt"&&t->actions[0]->name!="shadow bolt");
  assert(t->actions[0]->name==(cls==CLASS_WARRIOR?"whirlwind":cls==CLASS_PALADIN?"consecration":cls==CLASS_HUNTER?"volley":cls==CLASS_ROGUE?"blade flurry":cls==CLASS_SHAMAN?"chain lightning":cls==CLASS_MAGE?"blizzard":cls==CLASS_DRUID?"hurricane":warlockArea));
  for(auto*x:triggers)delete x;
 }
 std::cout<<"PASS native raid vendor delegation and combat/faction/ownership guards, no DPS shout threat, single-target Whirlwind threat and Classic AP/Frost default\n";
}
'''.replace('__METHODS__',methods).replace('__CLASSIC__',classic)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='raid-maintenance-') as tmp:
  d=Path(tmp);(d/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=d,check=True)
  subprocess.run([str(d/'test.exe')],cwd=d,check=True)
