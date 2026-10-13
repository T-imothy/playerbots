"""Actual MC support, tank allocation and frontal-position bodies across all eras."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
r=Path(__file__).resolve().parents[1]
s=(r/'playerbot/strategy/actions/MoltenCoreDungeonActions.cpp').read_text()
methods='\n'.join(block(s,m) for m in ('bool ai::MoltenCoreImpPack(', 'bool PlanHunterStack(', 'const char* MoltenCoreRangeSpell(', 'bool PlanCoreHoundRanged(', 'void PreserveMoltenCoreTank(', 'std::vector<Unit*> MoltenCorePack(', 'std::vector<Player*> MoltenCorePackTanks(', 'bool ai::MoltenCorePackStackRequired(', 'Unit* ai::MoltenCorePackTankTarget(', 'bool ai::PlanMoltenCorePack(', 'bool PlanMagmadarFormation(', 'bool ai::PlanGeddonFormation(', 'bool RaidMember(', 'bool RaidEnemy(', 'bool MoltenCoreBoss(', 'Unit* RaidBoss(', 'Unit* MoltenCoreTrashTankTarget(', 'uint32 RaidAdd(', 'std::vector<Unit*> RaidAdds(', 'Unit* MajordomoFocus(', 'Unit* MajordomoAssignedHealer(', 'bool MajordomoSupport(', 'bool ai::PlanMajordomoFormation(', 'Unit* ai::MoltenCoreAssignedTankTarget(', 'bool MoltenCoreSupportAction::Select(', 'bool MoltenCoreSupportAction::Execute(', 'bool ai::PlanGolemaggFormation(', 'Unit* ai::MoltenCoreRagnaros(', 'std::vector<Player*> RagnarosRanged(', 'const char* RagnarosRangeSpell(', 'bool ai::RagnarosSameCluster(', 'bool ai::PlanRagnarosFormation(', 'bool ai::PlanMoltenCoreTrash('))
code=r'''
#include <cassert>
#include <ctime>
#include <cmath>
#include <map>
#include <set>
#include <list>
#include <vector>
#include <algorithm>
#include <string>
#include <iostream>
using uint32=unsigned;using int32=int;constexpr unsigned SPELL_SCHOOL_MASK_ALL=127;constexpr float M_PI=3.14159265358979323846f;
enum{CURRENT_GENERIC_SPELL,SPELL_STATE_CASTING,SPELL_STATE_FINISHED,CLASS_WARRIOR=1,CLASS_PALADIN=2,CLASS_HUNTER=3,CLASS_PRIEST=5,CLASS_SHAMAN=7,CLASS_MAGE=8,CLASS_WARLOCK=9,CLASS_DRUID=11};
namespace BotState{enum{BOT_STATE_COMBAT};}
struct ObjectGuid{unsigned id=0;ObjectGuid(unsigned v=0):id(v){}operator unsigned()const{return id;}};
struct SpellEntry{unsigned Id=19775;};struct Spell{SpellEntry*m_spellInfo=nullptr;int state=SPELL_STATE_CASTING;bool interrupt=true;int getState(){return state;}bool CanBeInterrupted(){return interrupt;}};
struct Player;struct PlayerbotAI;struct Group;
struct Aura{unsigned stacks=5;unsigned GetStackAmount(){return stacks;}};
struct Unit{virtual ~Unit()=default;unsigned entry=0,map=409,instance=1,phase=1;ObjectGuid guid;bool world=true,alive=true,combat=true,charmed=false,friendly=false,cc=false,hardCC=false,attackable=true;
 float x=0,y=0,z=0,o=0,health=100;Unit*victim=nullptr;Spell*cast=nullptr;std::set<unsigned>auras;
 virtual bool IsPlayer(){return false;}unsigned GetEntry(){return entry;}ObjectGuid GetObjectGuid(){return guid;}unsigned GetGUIDLow(){return guid;}unsigned GetInstanceId(){return instance;}
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 bool IsInMap(Unit*u){return world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}
 float GetDistance(Unit*u){return std::hypot(x-u->x,y-u->y);}float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetReflectChance(unsigned){return HasAura(20619)?50:0;}float GetOrientation(){return o;}float GetAngle(Unit*u){return std::atan2(u->y-y,u->x-x);}float GetCombatReach(){return 1.5f;}float GetObjectBoundingRadius(){return 1.5f;}float GetHealthPercent(){return health;}
 bool HasAura(unsigned a){return auras.count(a);}Unit*GetVictim(){return victim;}Spell*GetCurrentSpell(int){return cast;}};
struct Creature:Unit{void*formation=nullptr;void*GetCreatureGroup(){return formation;}};
struct Player:Unit{bool teleport=false,tank=false,ranged=false,healer=false;unsigned cls=1;Group*group=nullptr;PlayerbotAI*ai=nullptr;
 bool los=true;bool IsWithinLOSInMap(Unit*){return los;}bool IsPlayer()override{return true;}unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}bool IsBeingTeleported(){return teleport;}
 unsigned getClass(){return cls;}Group*GetGroup(){return group;}PlayerbotAI*GetPlayerbotAI(){return ai;}};
struct GroupReference{Player*p;GroupReference*following=nullptr;Player*getSource(){return p;}GroupReference*next(){return following;}};
struct Group{std::list<GroupReference>refs;ObjectGuid skull;void Add(Player*p){p->group=this;if(!refs.empty()){refs.push_back({p});auto i=refs.end();--i;auto previous=i;--previous;previous->following=&*i;}else refs.push_back({p});}
 GroupReference*GetFirstMember(){return refs.empty()?nullptr:&refs.front();}ObjectGuid GetTargetIcon(unsigned i){assert(i==7);return skull;}};
namespace ai{namespace encounter{struct Point{float x=0,y=0,z=0;};}struct GeddonControl{ObjectGuid boss,tank;encounter::Point tankPosition,rangedPosition;};}
template<class T>struct Cached{T value;T Get(){return value;}void Set(T v){value=v;}};
struct Context{Cached<ai::GeddonControl>geddon;Cached<std::list<ObjectGuid>>possible;Cached<ObjectGuid>attack,current;std::map<std::string,Cached<int32>>owners;template<class T>Cached<T>*GetValue(const char*name,const std::string&key=""){if constexpr(std::is_same_v<T,ai::GeddonControl>)return &geddon;else if constexpr(std::is_same_v<T,ObjectGuid>)return std::string(name)=="current target"?&current:&attack;else if constexpr(std::is_same_v<T,int32>)return &owners[key];else return &possible;}};
std::vector<Unit*>units;
struct PlayerbotAI{Player*bot;Context context;bool rejectFarPaths=false,real=false,path=true,castOK=true;float spellRange=40;bool fireBlocked=false,rangeUnavailable=false;std::string lastRangeSpell;unsigned casts=0;Unit*lastTarget=nullptr;std::string lastSpell;std::set<std::string>learned;
 time_t combatStart=time(0)-12;time_t GetCombatStartTime(){return combatStart;}
 PlayerbotAI(Player*p):bot(p){p->ai=this;}Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool IsTank(Player*p){return p->tank;}bool IsRanged(Player*p){return p->ranged;}bool IsHeal(Player*p){return p->healer;}
 Context*GetAiObjectContext(){return &context;}Unit*GetUnit(ObjectGuid g){for(auto*u:units)if(u->guid==g)return u;return nullptr;}
 float minimum=8;bool GetSpellRange(const std::string&n,float*r,float*min=nullptr){if(min)*min=minimum;lastRangeSpell=n;if(rangeUnavailable)return false;if(n=="fear ward"&&!learned.count(n))return false;*r=spellRange;return true;}float GetRange(const char*){return 40;}bool HasStrategy(const char*,int){return false;}bool CanCastSpell(const std::string&n,Unit*u,unsigned,void*item=nullptr,bool ignoreRange=false){if(u->HasAura(20619)&&(n=="frostbolt"||n=="fireball"||n=="polymorph"||n=="counterspell"||n=="silence"||n=="earth shock"))return false;return learned.count(n)&&u->world&&u->alive&&bot->IsInMap(u)&&bot->GetDistance(u)<=100;}
 Aura splash;Aura*GetAura(unsigned id,Unit*u){return u->HasAura(id)?&splash:nullptr;}
 bool HasSpell(const std::string&n){return learned.count(n);}bool HasAura(const std::string&,Unit*){return false;}
 bool CastSpell(const std::string&n,Unit*u,void*,bool,uint32*d){lastSpell=n;lastTarget=u;++casts;*d=1500;return castOK;}};
struct Facade{bool IsFriendlyTo(Player*,Unit*u){return u->friendly;}}sServerFacade;
struct{unsigned globalCoolDown=1500;}sPlayerbotAIConfig;
namespace MaNGOS{struct AllCreaturesOfEntryInRangeCheck{Unit*center;unsigned entry;float range;AllCreaturesOfEntryInRangeCheck(Unit*c,unsigned e,float r):center(c),entry(e),range(r){}bool operator()(Unit*u){return u->entry==entry&&center->GetDistance(u)<=range;}};
 template<class Check>struct UnitListSearcher{std::list<Unit*>&out;Check&check;UnitListSearcher(std::list<Unit*>&o,Check&c):out(o),check(c){}};}
namespace Cell{template<class Check>void VisitAllObjects(Unit*,MaNGOS::UnitListSearcher<Check>&s,float){for(auto*u:units)if(s.check(u))s.out.push_back(u);}}
namespace ai{struct EncounterPosition{bool active=false;unsigned map=0,instance=0,spell=0;ObjectGuid boss,source;encounter::Point destination;};
 struct PossibleAttackTargetsValue{static bool IsValid(Unit*u,Player*p,float range,bool,bool){return u->attackable&&p->GetDistance(u)<=range;}static bool HasBreakableCC(Unit*u,Player*){return u->cc;}static bool HasUnBreakableCC(Unit*u,Player*){return u->hardCC;}};
 bool ValidateEncounterDestination(PlayerbotAI*ai,EncounterPosition&p,bool walking=true){if(p.spell==19364)assert(p.active&&p.map==ai->bot->GetMapId()&&p.instance==ai->bot->GetInstanceId());return (!walking||ai->path)&&!ai->fireBlocked&&(!ai->rejectFarPaths||std::hypot(p.destination.x,p.destination.y)<40);}float NativeEncounterSpellRadius(unsigned id){assert(id==19364||id==19408||id==20602||id==20556||id==19798||id==21155||id==20566);return id==19364?45.0f:id==20566?25.0f:id==21155?20.0f:id==19408?45.0f:id==20556?30.0f:id==19798?18.0f:10.0f;}
 Unit*LavaTrashBanishTarget(PlayerbotAI*){return nullptr;}bool LavaTrashReservedTarget(PlayerbotAI*,Unit*){return false;}bool PlanLavaTrashCarrier(PlayerbotAI*,EncounterPosition&){return false;}bool PlanLavaTrashBanish(PlayerbotAI*,EncounterPosition&){return false;}
 Unit* MoltenCoreRagnaros(PlayerbotAI*);bool RagnarosSameCluster(PlayerbotAI*,Player*);bool PlanRagnarosFormation(PlayerbotAI*,EncounterPosition&);bool PlanMajordomoFormation(PlayerbotAI*,EncounterPosition&);bool PlanGolemaggFormation(PlayerbotAI*,EncounterPosition&);bool PlanGeddonFormation(PlayerbotAI*,Unit*,EncounterPosition&);Unit*GarrTankTarget(PlayerbotAI*){return nullptr;}Unit*GarrBanishTarget(PlayerbotAI*){return nullptr;}bool GarrTankHandoff(PlayerbotAI*,Unit*){return false;}bool PlanGarrPosition(PlayerbotAI*,EncounterPosition&){return false;}bool MoltenCorePackStackRequired(PlayerbotAI*);Unit*MoltenCorePackTankTarget(PlayerbotAI*);bool PlanMoltenCorePack(PlayerbotAI*,EncounterPosition&);Unit*MoltenCoreAssignedTankTarget(PlayerbotAI*);inline const char* MagePrimaryDamageSpell(PlayerbotAI*){return "frostbolt";}bool PlanMoltenCoreTrash(PlayerbotAI*,EncounterPosition&);bool MoltenCoreImpPack(PlayerbotAI*);
 struct Event{};struct MoltenCoreSupportAction{PlayerbotAI*ai;Player*bot;bool Select(std::string&,Unit*&);bool Execute(Event&);void SetDuration(unsigned){}};
}
using namespace ai;
__METHODS__
int main(){

 {
 Player tanks[3],members[37];Group group;std::vector<PlayerbotAI*> brains;
 for(unsigned i=0;i<3;++i){tanks[i].guid=1+i;tanks[i].tank=true;tanks[i].x=2;group.Add(&tanks[i]);brains.push_back(new PlayerbotAI(&tanks[i]));}
 for(unsigned i=0;i<37;++i){members[i].guid=100+i;members[i].cls=i<8?CLASS_PRIEST:CLASS_MAGE;members[i].healer=i<8;members[i].ranged=i<29;group.Add(&members[i]);brains.push_back(new PlayerbotAI(&members[i]));}
 Unit boss;boss.entry=11502;boss.guid=500;boss.victim=&tanks[0];units={&boss};
 for(auto* brain:brains)units.push_back(brain->bot);
 std::vector<EncounterPosition> plans(40);
 for(unsigned i=0;i<40;++i)assert(PlanRagnarosFormation(brains[i],plans[i]));
 for(unsigned i=3;i<32;++i)for(unsigned j=i+1;j<32;++j){
  const float d=std::hypot(plans[i].destination.x-plans[j].destination.x,plans[i].destination.y-plans[j].destination.y);
  if((i-3)/3==(j-3)/3)assert(d<=1.61f);else assert(d>20.0f);
 }
 // Stable tank station survives a knockback onto a high rock. A missing walk
 // does not authorize walking: only a separately checked jump can use it.
 tanks[0].x=20;tanks[0].z=30;brains[0]->path=false;
 EncounterPosition p;assert(PlanRagnarosFormation(brains[0],p)&&p.destination.x==2&&p.destination.z==0);
 brains[0]->fireBlocked=true;assert(!PlanRagnarosFormation(brains[0],p));brains[0]->fireBlocked=false;brains[0]->path=true;
 boss.auras.insert(21859);boss.attackable=false;
 assert(MoltenCoreRagnaros(brains[3])==&boss);assert(PlanRagnarosFormation(brains[0],p)&&p.destination.x==2);
 assert(PlanRagnarosFormation(brains[3],p)); // immune boss still yields Sons phase formation
 boss.auras.clear();boss.attackable=true;brains[3]->spellRange=10;assert(!PlanRagnarosFormation(brains[3],p));
 brains[3]->spellRange=40;members[0].teleport=true;assert(!PlanRagnarosFormation(brains[3],p));members[0].teleport=false;
 tanks[0].z=0;tanks[0].x=2;tanks[0].health=40;brains[0]->learned={"shield wall"};brains[0]->context.possible.value={500};
 std::string spell;Unit*target=nullptr;MoltenCoreSupportAction defence{brains[0],&tanks[0]};assert(defence.Select(spell,target)&&spell=="shield wall");
 brains[3]->learned={"flash heal"};brains[3]->context.possible.value={500};MoltenCoreSupportAction healing{brains[3],&members[0]};assert(healing.Select(spell,target)&&target==&tanks[0]);
 boss.instance=2;assert(!MoltenCoreRagnaros(brains[3]));boss.instance=1;
 for(auto* brain:brains)delete brain;
 }

 {
 Player mt,ot,mages[6];mt.guid=1;ot.guid=2;mt.tank=ot.tank=true;mt.x=3;
 Group group;group.Add(&mt);group.Add(&ot);PlayerbotAI mainAI(&mt),tankAI(&ot);
 std::vector<PlayerbotAI*> brains;
 for(unsigned i=0;i<6;++i){mages[i].guid=100+i;mages[i].cls=CLASS_MAGE;mages[i].ranged=true;group.Add(&mages[i]);auto* a=new PlayerbotAI(&mages[i]);a->learned={"polymorph","frostbolt","counterspell"};brains.push_back(a);}
 Unit boss,healers[4],elites[4];boss.entry=12018;boss.guid=10;boss.victim=&mt;units={&mt,&ot,&boss};
 for(unsigned i=0;i<4;++i){healers[i].entry=11663;healers[i].guid=20+i;elites[i].entry=11664;elites[i].guid=30+i;elites[i].victim=&ot;units.push_back(&healers[i]);units.push_back(&elites[i]);}
 for(auto* a:brains)a->context.possible.value={10};tankAI.context.possible.value={10};
 std::string spell;Unit* target=nullptr;
 for(unsigned i=0;i<6;++i){bool casts=MajordomoSupport(brains[i],&boss,spell,target);assert(casts==(i<4));if(casts)assert(spell=="polymorph"&&target==&healers[i]);}
 EncounterPosition sheepPlan;assert(PlanMajordomoFormation(brains[3],sheepPlan));assert(std::hypot(sheepPlan.destination.x-healers[3].x,sheepPlan.destination.y-healers[3].y)<=40.01f);
 for(auto& healer:healers)healer.cc=true;assert(!PlanMajordomoFormation(brains[3],sheepPlan));
 for(auto* a:brains)assert(MajordomoFocus(a,&boss)==&elites[0]);
 group.skull=healers[3].guid;assert(MajordomoFocus(brains[0],&boss)==&elites[0]);
 EncounterPosition p;assert(PlanMajordomoFormation(&tankAI,p));for(auto& healer:healers)assert(std::hypot(p.destination.x-healer.x,p.destination.y-healer.y)>19);
 tankAI.fireBlocked=true;assert(!PlanMajordomoFormation(&tankAI,p));tankAI.fireBlocked=false;
 elites[0].alive=false;assert(MajordomoFocus(brains[1],&boss)==&elites[1]);
 for(auto& elite:elites)elite.alive=false;
 for(auto& healer:healers)healer.auras.insert(21087);
 assert(MajordomoFocus(brains[0],&boss)==&healers[0]);
 assert(PlanMajordomoFormation(&tankAI,p)&&std::hypot(p.destination.x-healers[0].x,p.destination.y-healers[0].y)<=4.01f);
 ot.x=4;assert(MajordomoSupport(brains[0],&boss,spell,target)&&spell=="frostbolt"&&target==&healers[0]);
 assert(!MajordomoSupport(brains[1],&boss,spell,target));
 healers[0].auras.insert(20619);assert(!MajordomoSupport(brains[0],&boss,spell,target));healers[0].auras.erase(20619);
 healers[0].cc=false;healers[0].alive=false;assert(MajordomoFocus(brains[2],&boss)==&healers[1]);
 for(auto& healer:healers)healer.cc=false;
 SpellEntry info;info.Id=21077;Spell cast;cast.m_spellInfo=&info;healers[3].cast=&cast;
 assert(MajordomoSupport(brains[5],&boss,spell,target)&&spell=="counterspell"&&target==&healers[3]);
 healers[3].auras.insert(20619);assert(!MajordomoSupport(brains[5],&boss,spell,target));
 tankAI.learned={"pummel"};assert(MajordomoSupport(&tankAI,&boss,spell,target)&&spell=="pummel");healers[3].auras.erase(20619);
 cast.interrupt=false;assert(!MajordomoSupport(brains[5],&boss,spell,target));
 for(auto* a:brains)delete a;
 }

 {
 Player mt,ot1,ot2,mage,healer;mt.guid=1;ot1.guid=2;ot2.guid=3;mage.guid=4;healer.guid=5;
 mt.tank=ot1.tank=ot2.tank=true;mt.x=3;mage.x=-10;mage.ranged=true;mage.cls=CLASS_MAGE;healer.cls=CLASS_PRIEST;healer.healer=true;healer.ranged=true;healer.x=-25;
 Group g;for(auto*p:{&mt,&ot1,&ot2,&mage,&healer})g.Add(p);
 PlayerbotAI mainAI(&mt),firstAI(&ot1),secondAI(&ot2),mageAI(&mage),healAI(&healer);
 Unit boss,dog1,dog2;boss.entry=11988;boss.guid=10;boss.victim=&mt;dog1.entry=dog2.entry=11672;dog1.guid=20;dog2.guid=21;dog1.victim=&ot1;dog2.victim=&ot2;
 units={&mt,&ot1,&ot2,&mage,&healer,&boss,&dog1,&dog2};for(auto*a:{&mainAI,&firstAI,&secondAI,&mageAI,&healAI})a->context.possible.value={10,20,21};
 assert(MoltenCoreAssignedTankTarget(&mainAI)==&boss);assert(MoltenCoreAssignedTankTarget(&firstAI)==&dog1);assert(MoltenCoreAssignedTankTarget(&secondAI)==&dog2);
 EncounterPosition p,q;assert(PlanGolemaggFormation(&firstAI,p)&&p.destination.y>39);assert(PlanGolemaggFormation(&secondAI,q)&&q.destination.y<-39);
 assert(!PlanGolemaggFormation(&mainAI,q));boss.o=1.5f;assert(PlanGolemaggFormation(&firstAI,q)&&std::hypot(p.destination.x-q.destination.x,p.destination.y-q.destination.y)<0.1f); // Pyroblast facing cannot rotate dog stations.
 assert(PlanGolemaggFormation(&mageAI,q)&&std::hypot(q.destination.x,q.destination.y)>=40);mageAI.spellRange=20;assert(PlanGolemaggFormation(&mageAI,q)&&std::hypot(q.destination.x,q.destination.y)<=21.01f);
 mageAI.fireBlocked=true;assert(!PlanGolemaggFormation(&mageAI,q));mageAI.fireBlocked=false;
 dog1.victim=&healer;assert(!PlanGolemaggFormation(&firstAI,q));dog1.victim=&ot1;
 mt.health=70;ot1.health=30;healAI.learned={"flash heal"};MoltenCoreSupportAction support{&healAI,&healer};std::string spell;Unit*target=nullptr;
 assert(support.Select(spell,target)&&target==&ot1);ot1.health=90;assert(support.Select(spell,target)&&target==&mt);
 ot1.instance=2;ot1.health=20;assert(support.Select(spell,target)&&target==&mt);ot1.instance=1;
 healAI.context.attack.value=2;assert(PlanGolemaggFormation(&healAI,q)&&std::hypot(q.destination.x-ot1.x,q.destination.y-ot1.y)<=41.01f);
 mt.auras.insert(13880);mainAI.learned={"shield wall"};MoltenCoreSupportAction tankSupport{&mainAI,&mt};assert(tankSupport.Select(spell,target)&&spell=="shield wall"&&target==&mt);
 mt.auras.clear();mt.health=100;assert(!tankSupport.Select(spell,target));mt.teleport=true;assert(!PlanGolemaggFormation(&mainAI,q));mt.teleport=false;
 }

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
 // All healers receive sheep while an elite is alive, even with a healer skull.
 boss.entry=12018;add.entry=second.entry=third.entry=fourth.entry=11663;bot.cls=other.cls=CLASS_MAGE;ai.learned=otherAI.learned={"polymorph"};
 Unit elite;elite.entry=11664;elite.guid=60;units.push_back(&elite);
 assert(pick()&&target==&add);add.cc=true;assert(!pick());add.cc=false;add.auras={21087};assert(!pick());add.auras.clear();
 group.skull=second.guid;assert(pick()&&target==&add);group.skull=0;elite.alive=false;
 assert(!pick()); // The selected healer is released, never immediately re-sheeped.
  // Tank allocation retains established main tank and distributes uncontrollable adds.
 bot.tank=true;secondTank.tank=true;bot.cls=1;ai.learned.clear();boss.entry=12118;add.entry=second.entry=third.entry=fourth.entry=12119;
 assert(MoltenCoreAssignedTankTarget(&ai)==&add);PlayerbotAI mainAI(&mainTank);mainAI.context.possible.value={10};assert(MoltenCoreAssignedTankTarget(&mainAI)==&boss);
 PlayerbotAI secondAI(&secondTank);secondAI.context.possible.value={10};assert(MoltenCoreAssignedTankTarget(&secondAI)==&second);
 add.cc=true;assert(MoltenCoreAssignedTankTarget(&ai)==&third);add.cc=false;ai.context.attack.value=20;assert(!MoltenCoreAssignedTankTarget(&ai));ai.context.attack.value=0;
 // Magmadar uses the frontal-facing movement, without removing the fear spacing.
 boss.entry=11982;ai.context.possible.value={10};mainTank.tank=false;boss.victim=&bot;other.x=10;bot.x=2;bot.tank=true;
 EncounterPosition plan;assert(PlanMoltenCoreTrash(&ai,plan)&&plan.spell==19272&&plan.destination.x<0);
 boss.victim=&mainTank;bot.tank=true;bot.x=2;assert(PlanMoltenCoreTrash(&ai,plan)&&plan.destination.x<0);bot.tank=false;bot.ranged=false;assert(PlanMoltenCoreTrash(&ai,plan)&&plan.destination.x<0);
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
 // Five native-group hounds keep stable slots through fake death/reignite.
 Creature h4,h5,foreignHound;h4.entry=h5.entry=foreignHound.entry=11671;h4.guid=43;h5.guid=44;foreignHound.guid=45;
 int formation,foreignFormation;h1.formation=h2.formation=h3.formation=h4.formation=h5.formation=&formation;foreignHound.formation=&foreignFormation;
 units.insert(units.end(),{&h4,&h5,&foreignHound});h4.victim=&mainTank;h5.victim=&other;
 ai.context.possible.value={40,41,42,43,44,45};ai.context.attack.value=40;
 auto pack=MoltenCorePack(&ai);assert(pack.size()==5&&pack.front()==&h1);assert(MoltenCorePackStackRequired(&ai));
 h1.auras={19951};h1.hardCC=true;pack=MoltenCorePack(&ai);assert(pack.size()==5&&pack.front()==&h1);
 assert(MoltenCorePackTankTarget(&ai)==&h5); // assigned tank recovers its second mob rather than all attacking commanded h1
 h1.auras.clear();h1.hardCC=false;h1.victim=&other;assert(MoltenCorePackTankTarget(&mainAI)==nullptr); // mainAI has no matching possible snapshot yet
 mainAI.context.possible.value=ai.context.possible.value;mainAI.context.attack.value=40;assert(MoltenCorePackTankTarget(&mainAI)==&h1);
 ai.context.attack.value=0;mainAI.context.possible.value.clear();mainAI.context.attack.value=0;h1.victim=&mainTank;
 ai.context.possible.value={40,41,42,43,44};
 // Hunters cluster at their native minimum shooting range, not inside the dead zone.
 bot.cls=CLASS_HUNTER;bot.tank=false;bot.ranged=true;h2.victim=&mainTank;ai.context.current.value=40;
 assert(PlanMoltenCorePack(&ai,plan)&&std::hypot(plan.destination.x-h1.x,plan.destination.y-h1.y)>=ai.minimum);
 auto hunterStation=plan.destination;bot.x=hunterStation.x;bot.y=hunterStation.y;
 assert(PlanMoltenCorePack(&ai,plan)&&plan.destination.x==bot.x&&plan.destination.y==bot.y); // no arrival jitter
 h2.victim=&bot;assert(PlanMoltenCorePack(&ai,plan)&&plan.source==bot.guid&&plan.destination.x==secondTank.x);h2.victim=&mainTank; // carrier still runs to tank
 ai.minimum=5;bot.x=bot.y=0;assert(PlanMoltenCorePack(&ai,plan)&&std::hypot(plan.destination.x-h1.x,plan.destination.y-h1.y)>=5);
 ai.minimum=0;assert(PlanMoltenCorePack(&ai,plan)&&plan.destination.x==mainTank.x);ai.minimum=8;
 ai.path=false;assert(!PlanMoltenCorePack(&ai,plan));ai.path=true;ai.rangeUnavailable=true;assert(!PlanMoltenCorePack(&ai,plan));ai.rangeUnavailable=false;
 bot.cls=CLASS_WARRIOR;bot.ranged=false;bot.x=bot.y=0;ai.context.current.value=0;
 // Loose assigned hounds outrank gathering and native taunt restores ownership.
 h5.victim=&other;bot.tank=true;ai.learned={"taunt"};
 assert(!PlanMoltenCorePack(&ai,plan));assert(pick()&&target==&h5&&spell=="taunt");
 h5.victim=&bot;assert(PlanMoltenCorePack(&ai,plan)&&plan.destination.x==mainTank.x);
 // Every regular-pack role stacks; aggro carriers first return to their assigned tank.
 bot.tank=false;h2.victim=&secondTank;h5.victim=&mainTank;
 for(unsigned role=0;role<3;++role){bot.ranged=role==1;bot.healer=role==2;
  assert(PlanMoltenCorePack(&ai,plan)&&plan.destination.x==mainTank.x&&plan.destination.y==mainTank.y);}
 h2.victim=&bot;assert(PlanMoltenCorePack(&ai,plan)&&plan.source==bot.guid);
 assert(plan.destination.x==secondTank.x&&plan.destination.y==secondTank.y);
 h2.auras={19951};assert(PlanMoltenCorePack(&ai,plan)&&plan.destination.x==mainTank.x);h2.auras.clear();
 ai.path=false;assert(!PlanMoltenCorePack(&ai,plan));ai.path=true;bot.healer=false;ai.learned.clear();
 ai.context.possible.value={40,41,42};

 h1.entry=h2.entry=h3.entry=11669;bot.tank=false;bot.ranged=false;h2.victim=&mainTank;
 assert(PlanMoltenCoreTrash(&ai,plan)&&std::hypot(plan.destination.x,plan.destination.y)>=12);
 h2.victim=&bot;assert(PlanMoltenCoreTrash(&ai,plan)&&plan.spell==20602);
 assert(plan.destination.x==secondTank.x&&plan.destination.y==secondTank.y); // carry the imp to its assigned tank
 h2.victim=&mainTank;
 // A hunter in the Surger stack retains native shooting room close to the tank.
 boss.entry=12101;boss.victim=&mainTank;ai.context.possible.value={10};bot.cls=CLASS_HUNTER;bot.ranged=true;
 assert(PlanMoltenCoreTrash(&ai,plan)&&plan.spell==19196&&std::hypot(plan.destination.x-boss.x,plan.destination.y-boss.y)>=ai.minimum);
 assert(std::hypot(plan.destination.x-mainTank.x,plan.destination.y-mainTank.y)<=ai.minimum+6);
 bot.cls=CLASS_WARRIOR;bot.ranged=false;
 // Mixed imp/surger admission: one loose imp cannot deadlock the whole raid.
 boss.entry=12101;boss.victim=&mainTank;ai.context.current.value=10;ai.context.possible.value={10,40,41,42};
 h1.victim=&mainTank;h2.victim=&bot;h3.victim=&mainTank;assert(MoltenCoreImpPack(&ai));
 ai.combatStart=time(0)-1;assert(!MoltenCoreImpPack(&ai));ai.combatStart=time(0)-12;
 h3.cc=true;assert(!MoltenCoreImpPack(&ai));h3.cc=false;h3.combat=false;assert(!MoltenCoreImpPack(&ai));h3.combat=true;
 h1.victim=h2.victim=h3.victim=&bot;assert(!MoltenCoreImpPack(&ai));ai.context.current.value=0;
 // Ranged stay back even if already behind a patrol hound. Other tanks isolate their mob.
 boss.entry=11673;boss.victim=&mainTank;boss.o=0;ai.context.possible.value={10};bot.x=-2;bot.ranged=true;
 assert(PlanMoltenCoreTrash(&ai,plan)&&std::hypot(plan.destination.x,plan.destination.y)>=40);
 bot.x=-25;assert(PlanMoltenCoreTrash(&ai,plan)&&plan.destination.x<-39); // old station is no longer retained
 bot.x=-41;assert(PlanMoltenCoreTrash(&ai,plan)&&plan.destination.x==-41); // stable native-range rear hold
 ai.rejectFarPaths=true;bot.x=-25;assert(PlanMoltenCoreTrash(&ai,plan)&&std::hypot(plan.destination.x,plan.destination.y)<40);ai.rejectFarPaths=false;
 ai.spellRange=30;bot.x=-25;assert(PlanMoltenCoreTrash(&ai,plan)&&std::hypot(plan.destination.x,plan.destination.y)<=31.01f);
 // Some classes cannot outrange the native 45-yard stun and still cast.
 ai.spellRange=60;assert(PlanMoltenCoreTrash(&ai,plan)&&std::hypot(plan.destination.x,plan.destination.y)>50);
 ai.rangeUnavailable=true;assert(!PlanMoltenCoreTrash(&ai,plan));ai.rangeUnavailable=false;
 ai.spellRange=40;bot.healer=true;bot.cls=CLASS_PRIEST;mainTank.x=8;
 assert(PlanMoltenCoreTrash(&ai,plan)&&ai.lastRangeSpell=="flash heal");
 assert(std::hypot(plan.destination.x-mainTank.x,plan.destination.y)<=41.01f);
 assert(std::cos(std::atan2(plan.destination.y,plan.destination.x))<-0.25f);
 for(auto cls : {CLASS_PALADIN,CLASS_SHAMAN,CLASS_DRUID}) {bot.cls=cls;assert(PlanMoltenCoreTrash(&ai,plan));
 assert(ai.lastRangeSpell==(cls==CLASS_PALADIN?"flash of light":cls==CLASS_SHAMAN?"healing wave":"healing touch"));}
 bot.healer=false;
 for(auto cls : {CLASS_HUNTER,CLASS_WARLOCK,CLASS_PRIEST,CLASS_SHAMAN,CLASS_DRUID,CLASS_MAGE}) {bot.cls=cls;assert(PlanMoltenCoreTrash(&ai,plan));
 assert(ai.lastRangeSpell==(cls==CLASS_HUNTER?"auto shot":cls==CLASS_WARLOCK?"shadow bolt":cls==CLASS_PRIEST?"mind blast":cls==CLASS_SHAMAN?"lightning bolt":cls==CLASS_DRUID?"wrath":"frostbolt"));}
 ai.fireBlocked=true;assert(!PlanMoltenCoreTrash(&ai,plan));ai.fireBlocked=false;
 ai.context.current.value=20;add.entry=11661;add.victim=&bot;bot.tank=true;bot.ranged=false;bot.x=-3;
 assert(PlanMoltenCoreTrash(&ai,plan)&&std::hypot(plan.destination.x,plan.destination.y)>=25);
 bot.tank=false;assert(!PlanMoltenCoreTrash(&ai,plan));ai.context.current.value=0;
 // A healer's legal distance is to the tank, not the huge boss. Hazards can veto every slot.
 boss.entry=11982;boss.victim=&mainTank;mainTank.x=8;bot.healer=true;bot.cls=CLASS_PRIEST;bot.x=-2;
 assert(PlanMoltenCoreTrash(&ai,plan)&&std::hypot(plan.destination.x-mainTank.x,plan.destination.y)<=41.01f);
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
