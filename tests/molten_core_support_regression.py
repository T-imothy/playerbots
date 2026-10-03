"""Actual MC support, tank allocation and frontal-position bodies across all eras."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
r=Path(__file__).resolve().parents[1]
s=(r/'playerbot/strategy/actions/MoltenCoreDungeonActions.cpp').read_text()
methods='\n'.join(block(s,m) for m in ('bool RaidMember(', 'bool RaidEnemy(', 'bool MoltenCoreBoss(', 'Unit* RaidBoss(', 'uint32 RaidAdd(', 'std::vector<Unit*> RaidAdds(', 'Unit* ai::MoltenCoreAssignedTankTarget(', 'bool MoltenCoreSupportAction::Select(', 'bool MoltenCoreSupportAction::Execute(', 'bool ai::PlanMoltenCoreTrash('))
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
using uint32=unsigned;constexpr float M_PI=3.14159265358979323846f;
enum{CURRENT_GENERIC_SPELL,SPELL_STATE_CASTING,SPELL_STATE_FINISHED,CLASS_MAGE=8,CLASS_WARLOCK=9};
struct ObjectGuid{unsigned id=0;ObjectGuid(unsigned v=0):id(v){}operator unsigned()const{return id;}};
struct SpellEntry{unsigned Id=19775;};struct Spell{SpellEntry*m_spellInfo=nullptr;int state=SPELL_STATE_CASTING;bool interrupt=true;int getState(){return state;}bool CanBeInterrupted(){return interrupt;}};
struct Player;struct PlayerbotAI;struct Group;
struct Unit{virtual ~Unit()=default;unsigned entry=0,map=409,instance=1,phase=1;ObjectGuid guid;bool world=true,alive=true,combat=true,charmed=false,friendly=false,cc=false,hardCC=false,attackable=true;
 float x=0,y=0,z=0,o=0,health=100;Unit*victim=nullptr;Spell*cast=nullptr;std::set<unsigned>auras;
 virtual bool IsPlayer(){return false;}unsigned GetEntry(){return entry;}ObjectGuid GetObjectGuid(){return guid;}
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 bool IsInMap(Unit*u){return world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}
 float GetDistance(Unit*u){return std::hypot(x-u->x,y-u->y);}float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetOrientation(){return o;}float GetAngle(Unit*u){return std::atan2(u->y-y,u->x-x);}float GetCombatReach(){return 1.5f;}float GetHealthPercent(){return health;}
 bool HasAura(unsigned a){return auras.count(a);}Unit*GetVictim(){return victim;}Spell*GetCurrentSpell(int){return cast;}};
struct Player:Unit{bool teleport=false,tank=false,ranged=false,healer=false;unsigned cls=1;Group*group=nullptr;PlayerbotAI*ai=nullptr;
 bool IsPlayer()override{return true;}unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}bool IsBeingTeleported(){return teleport;}
 unsigned getClass(){return cls;}Group*GetGroup(){return group;}PlayerbotAI*GetPlayerbotAI(){return ai;}};
struct GroupReference{Player*p;GroupReference*following=nullptr;Player*getSource(){return p;}GroupReference*next(){return following;}};
struct Group{std::list<GroupReference>refs;ObjectGuid skull;void Add(Player*p){p->group=this;if(!refs.empty()){refs.push_back({p});auto i=refs.end();--i;auto previous=i;--previous;previous->following=&*i;}else refs.push_back({p});}
 GroupReference*GetFirstMember(){return refs.empty()?nullptr:&refs.front();}ObjectGuid GetTargetIcon(unsigned i){assert(i==7);return skull;}};
template<class T>struct Cached{T value;T Get(){return value;}};
struct Context{Cached<std::list<ObjectGuid>>possible;Cached<ObjectGuid>attack;template<class T>Cached<T>*GetValue(const char*){if constexpr(std::is_same_v<T,ObjectGuid>)return &attack;else return &possible;}};
std::vector<Unit*>units;
struct PlayerbotAI{Player*bot;Context context;bool real=false,path=true,castOK=true;unsigned casts=0;Unit*lastTarget=nullptr;std::string lastSpell;std::set<std::string>learned;
 PlayerbotAI(Player*p):bot(p){p->ai=this;}Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool IsTank(Player*p){return p->tank;}bool IsRanged(Player*p){return p->ranged;}bool IsHeal(Player*p){return p->healer;}
 Context*GetAiObjectContext(){return &context;}Unit*GetUnit(ObjectGuid g){for(auto*u:units)if(u->guid==g)return u;return nullptr;}
 bool CanCastSpell(const std::string&n,Unit*u,unsigned){return learned.count(n)&&u->world&&u->alive&&bot->IsInMap(u)&&bot->GetDistance(u)<=100;}
 bool HasSpell(const std::string&n){return learned.count(n);}bool HasAura(const std::string&,Player*){return false;}
 bool CastSpell(const std::string&n,Unit*u,void*,bool,uint32*d){lastSpell=n;lastTarget=u;++casts;*d=1500;return castOK;}};
struct Facade{bool IsFriendlyTo(Player*,Unit*u){return u->friendly;}}sServerFacade;
struct{unsigned globalCoolDown=1500;}sPlayerbotAIConfig;
namespace MaNGOS{struct AllCreaturesOfEntryInRangeCheck{Unit*center;unsigned entry;float range;AllCreaturesOfEntryInRangeCheck(Unit*c,unsigned e,float r):center(c),entry(e),range(r){}bool operator()(Unit*u){return u->entry==entry&&center->GetDistance(u)<=range;}};
 template<class Check>struct UnitListSearcher{std::list<Unit*>&out;Check&check;UnitListSearcher(std::list<Unit*>&o,Check&c):out(o),check(c){}};}
namespace Cell{template<class Check>void VisitAllObjects(Unit*,MaNGOS::UnitListSearcher<Check>&s,float){for(auto*u:units)if(s.check(u))s.out.push_back(u);}}
namespace ai{namespace encounter{struct Point{float x=0,y=0,z=0;};}struct EncounterPosition{bool active=false;unsigned map=0,instance=0,spell=0;ObjectGuid boss;encounter::Point destination;};
 struct PossibleAttackTargetsValue{static bool IsValid(Unit*u,Player*p,float range,bool,bool){return u->attackable&&p->GetDistance(u)<=range;}static bool HasBreakableCC(Unit*u,Player*){return u->cc;}static bool HasUnBreakableCC(Unit*u,Player*){return u->hardCC;}};
 bool ValidateEncounterDestination(PlayerbotAI*ai,EncounterPosition&){return ai->path;}float NativeEncounterSpellRadius(unsigned id){assert(id==19408);return 30;}
 Unit*MoltenCoreAssignedTankTarget(PlayerbotAI*);bool PlanMoltenCoreTrash(PlayerbotAI*,EncounterPosition&);
 struct Event{};struct MoltenCoreSupportAction{PlayerbotAI*ai;Player*bot;bool Select(std::string&,Unit*&);bool Execute(Event&);void SetDuration(unsigned){}};
}
using namespace ai;
__METHODS__
int main(){
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
 bot.x=-34;assert(PlanMoltenCoreTrash(&ai,plan)&&plan.destination.x==-34); // safe rear hold
 ai.path=false;assert(!PlanMoltenCoreTrash(&ai,plan));ai.path=true;
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

