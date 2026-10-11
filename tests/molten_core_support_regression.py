"""Actual MC support, tank allocation and frontal-position bodies across all eras."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
r=Path(__file__).resolve().parents[1]
s=(r/'playerbot/strategy/actions/MoltenCoreDungeonActions.cpp').read_text()
methods='\n'.join(block(s,m) for m in ('void PreserveMoltenCoreTank(', 'std::vector<Unit*> MoltenCorePack(', 'std::vector<Player*> MoltenCorePackTanks(', 'Unit* ai::MoltenCorePackTankTarget(', 'bool ai::PlanMoltenCorePack(', 'bool PlanMagmadarFormation(', 'bool ai::PlanGeddonFormation(', 'bool RaidMember(', 'bool RaidEnemy(', 'bool MoltenCoreBoss(', 'Unit* RaidBoss(', 'Unit* MoltenCoreTrashTankTarget(', 'uint32 RaidAdd(', 'std::vector<Unit*> RaidAdds(', 'Unit* ai::MoltenCoreAssignedTankTarget(', 'bool MoltenCoreSupportAction::Select(', 'bool MoltenCoreSupportAction::Execute(', 'bool ai::PlanMoltenCoreTrash('))
code=r'''
#include <cassert>
#include <cmath>
#include <map>
#include <set>
#include <list>
#include <vector>
#include <algorithm>
#include <string>
#include <iostream>
using uint32=unsigned;using int32=int;constexpr float M_PI=3.14159265358979323846f;
enum{CURRENT_GENERIC_SPELL,SPELL_STATE_CASTING,SPELL_STATE_FINISHED,CLASS_WARRIOR=1,CLASS_PALADIN=2,CLASS_HUNTER=3,CLASS_PRIEST=5,CLASS_SHAMAN=7,CLASS_MAGE=8,CLASS_WARLOCK=9,CLASS_DRUID=11};
namespace BotState{enum{BOT_STATE_COMBAT};}
struct ObjectGuid{unsigned id=0;ObjectGuid(unsigned v=0):id(v){}operator unsigned()const{return id;}};
struct SpellEntry{unsigned Id=19775;};struct Spell{SpellEntry*m_spellInfo=nullptr;int state=SPELL_STATE_CASTING;bool interrupt=true;int getState(){return state;}bool CanBeInterrupted(){return interrupt;}};
struct Player;struct PlayerbotAI;struct Group;
struct Unit{virtual ~Unit()=default;unsigned entry=0,map=409,instance=1,phase=1;ObjectGuid guid;bool world=true,alive=true,combat=true,charmed=false,friendly=false,cc=false,hardCC=false,attackable=true;
 float x=0,y=0,z=0,o=0,health=100;Unit*victim=nullptr;Spell*cast=nullptr;std::set<unsigned>auras;
 virtual bool IsPlayer(){return false;}unsigned GetEntry(){return entry;}ObjectGuid GetObjectGuid(){return guid;}unsigned GetGUIDLow(){return guid;}unsigned GetInstanceId(){return instance;}
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 bool IsInMap(Unit*u){return world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}
 float GetDistance(Unit*u){return std::hypot(x-u->x,y-u->y);}float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetOrientation(){return o;}float GetAngle(Unit*u){return std::atan2(u->y-y,u->x-x);}float GetCombatReach(){return 1.5f;}float GetHealthPercent(){return health;}
 bool HasAura(unsigned a){return auras.count(a);}Unit*GetVictim(){return victim;}Spell*GetCurrentSpell(int){return cast;}};
struct Creature:Unit{void*formation=nullptr;void*GetCreatureGroup(){return formation;}};
struct Player:Unit{bool teleport=false,tank=false,ranged=false,healer=false;unsigned cls=1;Group*group=nullptr;PlayerbotAI*ai=nullptr;
 bool IsPlayer()override{return true;}unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}bool IsBeingTeleported(){return teleport;}
 unsigned getClass(){return cls;}Group*GetGroup(){return group;}PlayerbotAI*GetPlayerbotAI(){return ai;}};
struct GroupReference{Player*p;GroupReference*following=nullptr;Player*getSource(){return p;}GroupReference*next(){return following;}};
struct Group{std::list<GroupReference>refs;ObjectGuid skull;void Add(Player*p){p->group=this;if(!refs.empty()){refs.push_back({p});auto i=refs.end();--i;auto previous=i;--previous;previous->following=&*i;}else refs.push_back({p});}
 GroupReference*GetFirstMember(){return refs.empty()?nullptr:&refs.front();}ObjectGuid GetTargetIcon(unsigned i){assert(i==7);return skull;}};
namespace ai{namespace encounter{struct Point{float x=0,y=0,z=0;};}struct GeddonControl{ObjectGuid boss,tank;encounter::Point tankPosition,rangedPosition;};}
template<class T>struct Cached{T value;T Get(){return value;}void Set(T v){value=v;}};
struct Context{Cached<ai::GeddonControl>geddon;Cached<std::list<ObjectGuid>>possible;Cached<ObjectGuid>attack,current;std::map<std::string,Cached<int32>>owners;template<class T>Cached<T>*GetValue(const char*name,const std::string&key=""){if constexpr(std::is_same_v<T,ai::GeddonControl>)return &geddon;else if constexpr(std::is_same_v<T,ObjectGuid>)return std::string(name)=="current target"?&current:&attack;else if constexpr(std::is_same_v<T,int32>)return &owners[key];else return &possible;}};
std::vector<Unit*>units;
struct PlayerbotAI{Player*bot;Context context;bool real=false,path=true,castOK=true;float spellRange=40;bool fireBlocked=false;unsigned casts=0;Unit*lastTarget=nullptr;std::string lastSpell;std::set<std::string>learned;
 PlayerbotAI(Player*p):bot(p){p->ai=this;}Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool IsTank(Player*p){return p->tank;}bool IsRanged(Player*p){return p->ranged;}bool IsHeal(Player*p){return p->healer;}
 Context*GetAiObjectContext(){return &context;}Unit*GetUnit(ObjectGuid g){for(auto*u:units)if(u->guid==g)return u;return nullptr;}
 bool GetSpellRange(const std::string&n,float*r){if(n=="fear ward"&&!learned.count(n))return false;*r=spellRange;return true;}float GetRange(const char*){return 40;}bool HasStrategy(const char*,int){return false;}bool CanCastSpell(const std::string&n,Unit*u,unsigned,void*item=nullptr,bool ignoreRange=false){return learned.count(n)&&u->world&&u->alive&&bot->IsInMap(u)&&bot->GetDistance(u)<=100;}
 bool HasSpell(const std::string&n){return learned.count(n);}bool HasAura(const std::string&,Unit*){return false;}
 bool CastSpell(const std::string&n,Unit*u,void*,bool,uint32*d){lastSpell=n;lastTarget=u;++casts;*d=1500;return castOK;}};
struct Facade{bool IsFriendlyTo(Player*,Unit*u){return u->friendly;}}sServerFacade;
struct{unsigned globalCoolDown=1500;}sPlayerbotAIConfig;
namespace MaNGOS{struct AllCreaturesOfEntryInRangeCheck{Unit*center;unsigned entry;float range;AllCreaturesOfEntryInRangeCheck(Unit*c,unsigned e,float r):center(c),entry(e),range(r){}bool operator()(Unit*u){return u->entry==entry&&center->GetDistance(u)<=range;}};
 template<class Check>struct UnitListSearcher{std::list<Unit*>&out;Check&check;UnitListSearcher(std::list<Unit*>&o,Check&c):out(o),check(c){}};}
namespace Cell{template<class Check>void VisitAllObjects(Unit*,MaNGOS::UnitListSearcher<Check>&s,float){for(auto*u:units)if(s.check(u))s.out.push_back(u);}}
namespace ai{struct EncounterPosition{bool active=false;unsigned map=0,instance=0,spell=0;ObjectGuid boss;encounter::Point destination;};
 struct PossibleAttackTargetsValue{static bool IsValid(Unit*u,Player*p,float range,bool,bool){return u->attackable&&p->GetDistance(u)<=range;}static bool HasBreakableCC(Unit*u,Player*){return u->cc;}static bool HasUnBreakableCC(Unit*u,Player*){return u->hardCC;}};
 bool ValidateEncounterDestination(PlayerbotAI*ai,EncounterPosition&){return ai->path&&!ai->fireBlocked;}float NativeEncounterSpellRadius(unsigned id){assert(id==19408||id==20602);return id==19408?45.0f:10.0f;}
 bool PlanGeddonFormation(PlayerbotAI*,Unit*,EncounterPosition&);Unit*GarrTankTarget(PlayerbotAI*){return nullptr;}Unit*GarrBanishTarget(PlayerbotAI*){return nullptr;}bool GarrTankHandoff(PlayerbotAI*,Unit*){return false;}bool PlanGarrPosition(PlayerbotAI*,EncounterPosition&){return false;}Unit*MoltenCorePackTankTarget(PlayerbotAI*);bool PlanMoltenCorePack(PlayerbotAI*,EncounterPosition&);Unit*MoltenCoreAssignedTankTarget(PlayerbotAI*);bool PlanMoltenCoreTrash(PlayerbotAI*,EncounterPosition&);
 struct Event{};struct MoltenCoreSupportAction{PlayerbotAI*ai;Player*bot;bool Select(std::string&,Unit*&);bool Execute(Event&);void SetDuration(unsigned){}};
}
using namespace ai;
__METHODS__
int main(){
 {
 Player tank,caster; tank.guid=801;caster.guid=802;tank.tank=true;caster.ranged=true;tank.x=2;caster.x=-30;
 Group group;group.Add(&tank);group.Add(&caster);PlayerbotAI brain(&caster);PlayerbotAI tankBrain(&tank);
 Unit boss;boss.entry=12056;boss.guid=803;boss.victim=&tank;units={&tank,&caster,&boss};EncounterPosition p;
 assert(PlanGeddonFormation(&brain,&boss,p)&&p.destination.x==-30);
 assert(!PlanGeddonFormation(&tankBrain,&boss,p));tank.x=12;
 assert(PlanGeddonFormation(&tankBrain,&boss,p)&&p.destination.x==2);
 caster.auras.insert(20475);assert(!PlanGeddonFormation(&brain,&boss,p));caster.auras.clear();
 assert(PlanGeddonFormation(&brain,&boss,p)&&p.destination.x==-30);
 brain.spellRange=20;assert(PlanGeddonFormation(&brain,&boss,p)&&p.destination.x>=-21);
 brain.path=false;assert(!PlanGeddonFormation(&brain,&boss,p));
 }

 {
 Player tank,caster; tank.guid=700;caster.guid=701;tank.tank=true;caster.ranged=true;tank.x=2;caster.x=8;
 Group party;party.Add(&tank);party.Add(&caster);PlayerbotAI brain(&caster);Unit flame;flame.entry=11667;flame.guid=702;flame.victim=&tank;flame.o=0;
 units={&tank,&caster,&flame};brain.context.possible.value={702};EncounterPosition p;
 assert(PlanMoltenCoreTrash(&brain,p)&&p.spell==19630&&p.destination.x<0&&std::hypot(p.destination.x,p.destination.y)>23);
 caster.x=-25;assert(PlanMoltenCoreTrash(&brain,p)&&p.destination.x==-25);
 brain.fireBlocked=true;assert(!PlanMoltenCoreTrash(&brain,p));
 PlayerbotAI tankBrain(&tank);tankBrain.context.possible.value={702};caster.x=25;
 assert(PlanMoltenCoreTrash(&tankBrain,p)&&p.destination.x<0); // tank faces away from ranged
 Unit walker;walker.guid=703;walker.entry=11666;walker.victim=&caster;units.push_back(&walker);
 tankBrain.context.possible.value={703};assert(MoltenCoreAssignedTankTarget(&tankBrain)==&walker);
 walker.cc=true;assert(!MoltenCoreAssignedTankTarget(&tankBrain));
 }

 Player bot,mainTank,other,secondTank;bot.guid=2;mainTank.guid=1;other.guid=3;secondTank.guid=4;mainTank.tank=true;mainTank.x=-2;other.x=5;
 Group group;for(auto*p:{&mainTank,&bot,&other,&secondTank})group.Add(p);PlayerbotAI ai(&bot);PlayerbotAI otherAI(&other);
 Unit boss,add,second,third,fourth;boss.guid=10;add.guid=20;second.guid=21;third.guid=22;fourth.guid=23;
 units={&bot,&mainTank,&other,&secondTank,&boss,&add,&second,&third,&fourth};ai.context.possible.value={10};boss.victim=&mainTank;
 MoltenCoreSupportAction support{&ai,&bot};std::string spell;Unit*target=nullptr;Event event;
 auto pick=[&](){spell.clear();target=nullptr;return support.Select(spell,target);};
 boss.entry=12118;other.auras={20604};ai.learned={"dispel magic"};assert(pick()&&target==&other);other.auras.clear();assert(!pick());
 mainTank.auras={19702};other.auras={19702};assert(pick()&&target==&mainTank);mainTank.auras.clear();
 assert(pick()&&target==&other);other.auras.clear();assert(!support.Execute(event)&&ai.casts==0);
 boss.entry=12259;other.auras={19716};assert(!pick());ai.learned={"remove lesser curse"};assert(pick()&&target==&other);assert(support.Execute(event)&&ai.lastTarget==&other);other.auras.clear();
 boss.entry=11982;boss.auras={19451};ai.learned={"tranquilizing shot"};assert(pick()&&target==&boss);boss.auras.clear();assert(!pick());
 ai.learned={"fear ward"};assert(pick()&&target==&mainTank);ai.learned.clear();assert(!pick());
 boss.entry=12098;add.entry=11662;SpellEntry info;Spell cast;cast.m_spellInfo=&info;add.cast=&cast;
 ai.learned={"kick"};assert(pick()&&target==&add&&spell=="kick");cast.interrupt=false;assert(!pick());cast.interrupt=true;
 cast.state=SPELL_STATE_FINISHED;assert(!pick());cast.state=SPELL_STATE_CASTING;info.Id=1234;assert(!pick());info.Id=19775;
#ifdef MANGOSBOT_TWO
 ai.learned={"wind shear"};assert(pick()&&spell=="wind shear");ai.learned={"earth shock"};assert(!pick());
#else
 ai.learned={"earth shock"};assert(pick()&&spell=="earth shock");ai.learned={"wind shear"};assert(!pick());
#endif
 add.cast=nullptr;ai.learned={"cleanse"};other.auras={20294};assert(pick()&&target==&other);other.auras={19776};assert(pick()&&target==&other);other.auras.clear();
 add.auras={19779};ai.learned={"purge"};assert(!pick());add.auras.clear();assert(!pick()); // Native Inspire has Dispel=0.
 boss.entry=12264;boss.auras={19714};assert(pick()&&target==&boss);boss.auras.clear();assert(!pick());
 // Firelord Soul Burn: remove silence without requiring a raid boss.
 boss.entry=11668;ai.learned={"dispel magic"};other.auras={19393};assert(pick()&&target==&other);
 other.instance=2;assert(!pick());other.instance=1;other.auras.clear();assert(!pick());
 // Stable sheep assignments, skip marked kill target, stop at native immunity.
 boss.entry=12018;add.entry=second.entry=third.entry=fourth.entry=11663;bot.cls=other.cls=CLASS_MAGE;ai.learned=otherAI.learned={"polymorph"};
 assert(pick()&&target==&second);second.cc=true;assert(!pick());second.cc=false;second.auras={21087};assert(!pick());second.auras.clear();
 group.skull=second.guid;assert(pick()&&target==&add);group.skull=0;
 // Tank allocation retains established main tank and distributes uncontrollable adds.
 bot.tank=true;secondTank.tank=true;bot.cls=1;ai.learned.clear();boss.entry=12118;add.entry=second.entry=third.entry=fourth.entry=12119;
 assert(MoltenCoreAssignedTankTarget(&ai)==&add);PlayerbotAI mainAI(&mainTank);mainAI.context.possible.value={10};assert(MoltenCoreAssignedTankTarget(&mainAI)==&boss);
 PlayerbotAI secondAI(&secondTank);secondAI.context.possible.value={10};assert(MoltenCoreAssignedTankTarget(&secondAI)==&second);
 add.cc=true;assert(MoltenCoreAssignedTankTarget(&ai)==&third);add.cc=false;ai.context.attack.value=20;assert(!MoltenCoreAssignedTankTarget(&ai));ai.context.attack.value=0;
 // Magmadar uses the frontal-facing movement, without removing the fear spacing.
 boss.entry=11982;ai.context.possible.value={10};mainTank.tank=false;boss.victim=&bot;other.x=10;bot.x=2;bot.tank=true;
 EncounterPosition plan;assert(PlanMoltenCoreTrash(&ai,plan)&&plan.spell==19272&&plan.destination.x<0);
 boss.victim=&mainTank;bot.tank=false;bot.x=2;bot.ranged=false;assert(PlanMoltenCoreTrash(&ai,plan)&&plan.destination.x<0);
 bot.ranged=true;assert(PlanMoltenCoreTrash(&ai,plan)&&std::hypot(plan.destination.x,plan.destination.y)>=32);
 bot.x=-2;assert(PlanMoltenCoreTrash(&ai,plan)&&std::hypot(plan.destination.x,plan.destination.y)>=32); // rear but inside fear range
 bot.x=-34;assert(PlanMoltenCoreTrash(&ai,plan)&&std::hypot(plan.destination.x,plan.destination.y)>=40); // safe rear hold
 ai.path=false;assert(!PlanMoltenCoreTrash(&ai,plan));ai.path=true;

 // Reacquire a real threat loss without assigning the boss to an unrelated tank.
 bot.tank=true;mainTank.tank=true;boss.entry=12259;boss.victim=&mainTank;
 ai.context.owners.clear();mainAI.context.owners.clear();
 assert(MoltenCoreAssignedTankTarget(&mainAI)==&boss);
 boss.victim=&other;assert(MoltenCoreAssignedTankTarget(&mainAI)==&boss);
 mainAI.learned={"taunt"};MoltenCoreSupportAction mainSupport{&mainAI,&mainTank};
 assert(mainSupport.Select(spell,target)&&target==&boss&&spell=="taunt");
 mainAI.learned={"shield slam"};assert(mainSupport.Select(spell,target)&&spell=="shield slam");
 boss.victim=&secondTank;assert(!mainSupport.Select(spell,target)); // do not steal from another tank
 boss.victim=&mainTank;add.entry=second.entry=11661;add.victim=&bot;
 assert(PlanMoltenCoreTrash(&ai,plan)&&plan.destination.x==mainTank.x);
 ai.fireBlocked=true;assert(!PlanMoltenCoreTrash(&ai,plan));ai.fireBlocked=false;
 // Pull small hounds off pets, retain tank-owned mobs and gather the pack.
 Creature h1,h2,h3;h1.entry=h2.entry=h3.entry=11671;h1.guid=40;h2.guid=41;h3.guid=42;
 h1.victim=&mainTank;h2.victim=&other;h3.victim=&secondTank;units.insert(units.end(),{&h1,&h2,&h3});
 ai.context.possible.value={40,41,42};ai.context.owners.clear();
 assert(MoltenCorePackTankTarget(&ai)==&h2);h2.victim=&bot;
 assert(PlanMoltenCoreTrash(&ai,plan)&&plan.destination.x==mainTank.x);
 h2.auras={19951};assert(MoltenCorePackTankTarget(&ai)!=&h2);h2.auras.clear();
 h1.entry=h2.entry=h3.entry=11669;bot.tank=false;bot.ranged=false;
 assert(PlanMoltenCoreTrash(&ai,plan)&&std::hypot(plan.destination.x,plan.destination.y)>=12);
 // Ranged stay back even if already behind a patrol hound. Other tanks isolate their mob.
 boss.entry=11673;boss.victim=&mainTank;boss.o=0;ai.context.possible.value={10};bot.x=-2;bot.ranged=true;
 assert(PlanMoltenCoreTrash(&ai,plan)&&std::hypot(plan.destination.x,plan.destination.y)>=25);
 ai.context.current.value=20;add.entry=11661;add.victim=&bot;bot.tank=true;bot.ranged=false;bot.x=-3;
 assert(PlanMoltenCoreTrash(&ai,plan)&&std::hypot(plan.destination.x,plan.destination.y)>=25);
 bot.tank=false;assert(!PlanMoltenCoreTrash(&ai,plan));ai.context.current.value=0;
 // A healer's legal distance is to the tank, not the huge boss. Hazards can veto every slot.
 boss.entry=11982;boss.victim=&mainTank;mainTank.x=8;bot.healer=true;bot.cls=CLASS_PRIEST;bot.x=-2;
 assert(PlanMoltenCoreTrash(&ai,plan)&&std::hypot(plan.destination.x-mainTank.x,plan.destination.y)<=41);
 ai.fireBlocked=true;assert(!PlanMoltenCoreTrash(&ai,plan));ai.fireBlocked=false;bot.healer=false;
 // Lifecycle guards stop stale support/assignments and foreign phases.
 boss.entry=12264;boss.auras={19714};ai.learned={"purge"};bot.teleport=true;assert(!pick());bot.teleport=false;
 bot.charmed=true;assert(!pick());bot.charmed=false;boss.instance=2;assert(!pick());boss.instance=1;
 std::cout<<"PASS: actual MC off-target interrupts, native era abilities, dispels, frenzy, mind control, sheep assignments, tank allocation and Magmadar positioning\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='mc-support-') as directory:
  d=Path(directory);(d/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=d,check=True)
  subprocess.run([str(d/'test.exe')],cwd=d,check=True)

