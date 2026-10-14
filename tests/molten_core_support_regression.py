"""Actual MC support, tank allocation and frontal-position bodies across all eras."""
from pathlib import Path
import subprocess,tempfile,sys
from behavior_regression import block
r=Path(__file__).resolve().parents[1]
s=(r/'playerbot/strategy/actions/MoltenCoreDungeonActions.cpp').read_text()
if '--before-firelord' in sys.argv:
 old=subprocess.check_output(['git','-C',str(r),'show','HEAD:playerbot/strategy/actions/MoltenCoreDungeonActions.cpp'],text=True)
 s=s.replace(block(s,'bool ai::PlanMoltenCoreTrash('),block(old,'bool ai::PlanMoltenCoreTrash('))
methods='\n'.join(block(s,m) for m in ('bool ai::MoltenCoreRecoverableImp(', 'bool ai::MoltenCoreImpUnderPressure(', 'bool ai::MoltenCoreImpPack(', 'bool ai::MoltenCoreImpTauntAllowed(', 'const char* MoltenCoreRangeSpell(', 'bool PlanCoreHoundRanged(', 'void PreserveMoltenCoreTank(', 'std::vector<Unit*> MoltenCorePack(', 'std::vector<Player*> MoltenCorePackTanks(', 'bool ai::MoltenCorePackStackRequired(', 'Unit* ai::MoltenCorePackTankTarget(', 'bool ai::PlanMoltenCorePack(', 'bool PlanMagmadarTank(', 'bool PlanMagmadarFormation(', 'bool ai::PlanGeddonFormation(', 'bool RaidMember(', 'bool RaidEnemy(', 'bool MoltenCoreBoss(', 'Unit* RaidBoss(', 'std::vector<Unit*> ai::MoltenCoreGroupTrash(', 'Unit* MoltenCoreTrashTankTarget(', 'bool ai::PlanMoltenCoreGiants(', 'uint32 RaidAdd(', 'std::vector<Unit*> RaidAdds(', 'Unit* MajordomoFocus(', 'ObjectGuid MajordomoSheepOwner(', 'Unit* MajordomoAssignedHealer(', 'bool MajordomoSupport(', 'bool ai::PlanMajordomoFormation(', 'Unit* ai::MoltenCoreAssignedTankTarget(', 'bool MoltenCoreSupportAction::Select(', 'bool MoltenCoreSupportAction::Execute(', 'bool ai::PlanGolemaggFormation(', 'Unit* ai::MoltenCoreRagnaros(', 'std::vector<Player*> RagnarosRanged(', 'const char* RagnarosRangeSpell(', 'bool ai::RagnarosSameCluster(', 'bool ai::PlanRagnarosFormation(', 'std::pair<float,float> FirelordRangedBounds(', 'bool PlanFirelordRanged(', 'bool ai::PlanMoltenCoreTrash('))
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
enum{DIST_CALC_NONE,CURRENT_GENERIC_SPELL,SPELL_STATE_CASTING,SPELL_STATE_FINISHED,CLASS_WARRIOR=1,CLASS_PALADIN=2,CLASS_HUNTER=3,CLASS_PRIEST=5,CLASS_SHAMAN=7,CLASS_MAGE=8,CLASS_WARLOCK=9,CLASS_DRUID=11};
namespace BotState{enum{BOT_STATE_COMBAT};}
struct ObjectGuid{unsigned id=0;ObjectGuid(unsigned v=0):id(v){}operator unsigned()const{return id;}bool IsEmpty()const{return !id;}};
constexpr unsigned SPELL_AURA_MOD_CONFUSE=5,MECHANIC_POLYMORPH=17;struct SpellEntry{unsigned Id=19775,Mechanic=MECHANIC_POLYMORPH;};struct Spell{SpellEntry*m_spellInfo=nullptr;int state=SPELL_STATE_CASTING;bool interrupt=true;int getState(){return state;}bool CanBeInterrupted(){return interrupt;}};
struct Player;struct PlayerbotAI;struct Group;
struct SheepHolder{ObjectGuid owner;ObjectGuid GetCasterGuid(){return owner;}};
struct Aura{SpellEntry proto;SheepHolder holder;const SpellEntry*GetSpellProto(){return &proto;}SheepHolder*GetHolder(){return &holder;}unsigned stacks=5;unsigned GetStackAmount(){return stacks;}};
struct Unit{virtual ~Unit()=default;unsigned entry=0,map=409,instance=1,phase=1;ObjectGuid guid;bool world=true,alive=true,combat=true,charmed=false,friendly=false,cc=false,hardCC=false,attackable=true;
 float x=0,y=0,z=0,o=0,health=100;bool mobile=true;bool CanReactInCombat(){return mobile&&alive&&!charmed;}bool IsImmobilizedState(){return !mobile;}
 std::vector<Aura*>sheeps;const auto&GetAurasByType(unsigned){return sheeps;}std::vector<Unit*>attackers;const auto&getAttackers(){return attackers;}
 Unit*owner=nullptr;Unit*GetOwner(void*,bool){return owner;}Unit*victim=nullptr;Spell*cast=nullptr;std::set<unsigned>auras;
 virtual bool IsPlayer(){return false;}unsigned GetEntry(){return entry;}ObjectGuid GetObjectGuid(){return guid;}unsigned GetGUIDLow(){return guid;}unsigned GetInstanceId(){return instance;}
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 bool IsSpellReady(unsigned){return true;}bool IsInMap(Unit*u){return world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}
 float GetDistance(Unit*u,bool,int){float dx=x-u->x,dy=y-u->y,dz=z-u->z;return dx*dx+dy*dy+dz*dz;}float GetDistance(Unit*u){return std::hypot(x-u->x,y-u->y);}float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 bool visible=true;bool IsWithinLOS(float,float,float,bool){return visible;}float GetCollisionHeight(){return 2;}float GetReflectChance(unsigned){return HasAura(20619)?50:0;}float GetOrientation(){return o;}float GetAngle(Unit*u){return std::atan2(u->y-y,u->x-x);}float GetCombatReach(){return 1.5f;}float GetObjectBoundingRadius(){return 1.5f;}float GetHealthPercent(){return health;}
 bool HasAura(unsigned a){return auras.count(a);}Unit*GetVictim(){return victim;}Spell*GetCurrentSpell(int){return cast;}};
struct Creature:Unit{void*formation=nullptr;void*GetCreatureGroup(){return formation;}};
struct Player:Unit{bool teleport=false,tank=false,ranged=false,healer=false;unsigned cls=1;Group*group=nullptr;PlayerbotAI*ai=nullptr;
 bool los=true;bool IsWithinLOSInMap(Unit*){return los;}bool IsPlayer()override{return true;}unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}bool IsBeingTeleported(){return teleport;}
 unsigned getClass(){return cls;}Group*GetGroup(){return group;}PlayerbotAI*GetPlayerbotAI(){return ai;}};
struct GroupReference{Player*p;GroupReference*following=nullptr;Player*getSource(){return p;}GroupReference*next(){return following;}};
struct Group{std::list<GroupReference>refs;ObjectGuid skull;void Add(Player*p){p->group=this;if(!refs.empty()){refs.push_back({p});auto i=refs.end();--i;auto previous=i;--previous;previous->following=&*i;}else refs.push_back({p});}
 GroupReference*GetFirstMember(){return refs.empty()?nullptr:&refs.front();}ObjectGuid GetTargetIcon(unsigned i){assert(i==7);return skull;}};
namespace ai{namespace encounter{struct Point{float x=0,y=0,z=0;};}struct MagmadarControl{ObjectGuid boss,tank;encounter::Point tankPosition;float facing=0;time_t combatStart=0;};struct GeddonControl{ObjectGuid boss,tank;encounter::Point tankPosition,rangedPosition;};}
template<class T>struct Cached{T value;T Get(){return value;}void Set(T v){value=v;}};
struct Context{Cached<ai::MagmadarControl>magmadar;Cached<ai::GeddonControl>geddon;Cached<std::list<ObjectGuid>>possible;Cached<ObjectGuid>attack,current;std::map<std::string,Cached<int32>>owners;template<class T>Cached<T>*GetValue(const char*name,const std::string&key=""){if constexpr(std::is_same_v<T,ai::MagmadarControl>)return &magmadar;else if constexpr(std::is_same_v<T,ai::GeddonControl>)return &geddon;else if constexpr(std::is_same_v<T,ObjectGuid>)return std::string(name)=="current target"?&current:&attack;else if constexpr(std::is_same_v<T,int32>)return &owners[key];else return &possible;}};
std::vector<Unit*>units;
struct PlayerbotAI{Player*bot;Context context;bool owned=true;bool HasRealPlayerMaster(){return owned;}bool rejectFrontLane=false,rejectFarPaths=false,real=false,path=true,castOK=true;float spellRange=40;bool fireBlocked=false,rangeUnavailable=false;std::string lastRangeSpell;unsigned casts=0;Unit*lastTarget=nullptr;std::string lastSpell;std::set<std::string>learned;
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
struct WorldPosition{float x=0,y=0,z=0;float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}};
using HazardPosition=std::pair<WorldPosition,float>;
std::list<HazardPosition> liveFire;
namespace ai{void AppendMoltenCoreGroundHazards(PlayerbotAI*,std::list<HazardPosition>&out){out=liveFire;}struct EncounterPosition{bool active=false;unsigned map=0,instance=0,spell=0;ObjectGuid boss,source;encounter::Point destination,anchor;bool anchored=false,groundOnly=false;};
 struct PossibleAttackTargetsValue{static bool IsValid(Unit*u,Player*p,float range,bool,bool){return u->attackable&&p->GetDistance(u)<=range;}static bool HasBreakableCC(Unit*u,Player*){return u->cc;}static bool HasUnBreakableCC(Unit*u,Player*){return u->hardCC;}};
 bool ValidateEncounterDestination(PlayerbotAI*ai,EncounterPosition&p,bool walking=true){if(p.spell==19364)assert(p.active&&p.map==ai->bot->GetMapId()&&p.instance==ai->bot->GetInstanceId());for(const auto& h:liveFire)if(std::hypot(p.destination.x-h.first.x,p.destination.y-h.first.y)<h.second)return false;return (!walking||ai->path)&&!ai->fireBlocked&&(!ai->rejectFrontLane||p.destination.y>5)&&(!ai->rejectFarPaths||std::hypot(p.destination.x,p.destination.y)<40);}float NativeEncounterSpellRadius(unsigned id){assert(id==1161||id==5209||id==19364||id==19408||id==20602||id==20556||id==19798||id==21155||id==20566);return id==19364?45.0f:id==20566?25.0f:id==21155?20.0f:id==19408?45.0f:id==20556?30.0f:id==19798?18.0f:10.0f;}
 Unit*LavaTrashBanishTarget(PlayerbotAI*){return nullptr;}bool LavaTrashReservedTarget(PlayerbotAI*,Unit*){return false;}bool PlanLavaTrashCarrier(PlayerbotAI*,EncounterPosition&){return false;}bool PlanLavaTrashBanish(PlayerbotAI*,EncounterPosition&){return false;}
 std::vector<Unit*>MoltenCoreGroupTrash(PlayerbotAI*);bool PlanMoltenCoreGiants(PlayerbotAI*,EncounterPosition&);bool MoltenCoreGroupEnemy(PlayerbotAI*a,Unit*u){return u&&u->world&&u->alive&&u->combat&&!u->charmed&&!u->friendly&&a->bot->IsInMap(u)&&u->victim&&u->victim->IsPlayer()&&static_cast<Player*>(u->victim)->group==a->bot->group;}bool MoltenCoreRecoveryTrash(unsigned e){return e!=11502&&e!=12099&&e!=11672&&e!=11663&&e!=11664&&e!=12143;}
 Unit* MoltenCoreRagnaros(PlayerbotAI*);bool RagnarosSameCluster(PlayerbotAI*,Player*);bool PlanRagnarosFormation(PlayerbotAI*,EncounterPosition&);bool PlanMajordomoFormation(PlayerbotAI*,EncounterPosition&);bool PlanGolemaggFormation(PlayerbotAI*,EncounterPosition&);bool PlanGeddonFormation(PlayerbotAI*,Unit*,EncounterPosition&);Unit*GarrTankTarget(PlayerbotAI*){return nullptr;}Unit*GarrBanishTarget(PlayerbotAI*){return nullptr;}bool GarrTankHandoff(PlayerbotAI*,Unit*){return false;}bool PlanGarrPosition(PlayerbotAI*,EncounterPosition&){return false;}bool MoltenCorePackStackRequired(PlayerbotAI*);Unit*MoltenCorePackTankTarget(PlayerbotAI*);bool PlanMoltenCorePack(PlayerbotAI*,EncounterPosition&);Unit*MoltenCoreAssignedTankTarget(PlayerbotAI*);inline const char* MagePrimaryDamageSpell(PlayerbotAI*){return "frostbolt";}bool PlanMoltenCoreTrash(PlayerbotAI*,EncounterPosition&);bool PlanMoltenCoreMageCleave(PlayerbotAI*,EncounterPosition&){return false;}bool MoltenCoreRecoverableImp(PlayerbotAI*,Unit*);bool MoltenCoreImpUnderPressure(PlayerbotAI*);bool MoltenCoreImpPack(PlayerbotAI*);bool MoltenCoreImpTauntAllowed(PlayerbotAI*,const std::string&);
 struct Event{};struct MoltenCoreSupportAction{PlayerbotAI*ai;Player*bot;bool Select(std::string&,Unit*&);bool Execute(Event&);void SetDuration(unsigned){}};
}
using namespace ai;
namespace ai{std::pair<float,float> HunterShotRange(PlayerbotAI*a,Unit*t){if(a->rangeUnavailable)return {0.0f,0.0f};return {a->minimum,a->spellRange+a->bot->GetCombatReach()+t->GetCombatReach()};}}
__METHODS__
int main(){

 {
 Player tanks[3],members[37];Group group;std::vector<PlayerbotAI*> brains;
 for(unsigned i=0;i<3;++i){tanks[i].guid=1+i;tanks[i].tank=true;tanks[i].x=2;group.Add(&tanks[i]);brains.push_back(new PlayerbotAI(&tanks[i]));}
 for(unsigned i=0;i<37;++i){members[i].guid=100+i;members[i].cls=i<8?CLASS_PRIEST:CLASS_MAGE;members[i].healer=i<8;members[i].ranged=i<29;group.Add(&members[i]);brains.push_back(new PlayerbotAI(&members[i]));}
 Unit boss;boss.entry=11502;boss.guid=500;boss.victim=&tanks[0];tanks[0].attackers={&boss};units={&boss};
 for(auto* brain:brains)units.push_back(brain->bot);
 assert(RaidBoss(brains[1])==&boss);boss.combat=false;assert(!RaidBoss(brains[1]));boss.combat=true;
 std::vector<EncounterPosition> plans(40);
 for(unsigned i=0;i<40;++i)assert(PlanRagnarosFormation(brains[i],plans[i]));
 for(unsigned i=1;i<3;++i)assert(std::hypot(plans[i].destination.x-boss.x,plans[i].destination.y-boss.y)<=3.01f&&plans[i].destination.x<0); // spare tanks remain in rear melee range
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
 Aura humanSheep;humanSheep.holder.owner=900;healers[0].sheeps={&humanSheep};
 assert(MajordomoAssignedHealer(brains[0],&boss)==&healers[1]);
 Aura ownedSheep;ownedSheep.holder.owner=mages[1].guid;healers[2].sheeps={&ownedSheep};
 assert(MajordomoAssignedHealer(brains[1],&boss)==&healers[2]);assert(MajordomoAssignedHealer(brains[0],&boss)==&healers[1]);
 healers[0].sheeps.clear();healers[2].sheeps.clear();
 assert(sheepPlan.destination.x==mages[3].x&&sheepPlan.destination.y==mages[3].y);
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
 mainTank.auras={19408};ai.learned={"dispel magic"};assert(pick()&&target==&mainTank&&spell=="dispel magic");
 mainTank.auras={19428};assert(!pick()); // native undispellable fire is a movement problem
 mainTank.auras.clear();bot.auras={19408};ai.learned={"berserker rage"};assert(pick()&&target==&bot);bot.auras.clear();ai.learned.clear();
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
 // Hunter stacks are identical to every other role, regardless of shot minimum.
 bot.cls=CLASS_HUNTER;bot.tank=false;bot.ranged=true;h2.victim=&mainTank;ai.context.current.value=40;
 for(float minimum:{8.0f,5.0f,0.0f}){ai.minimum=minimum;assert(PlanMoltenCorePack(&ai,plan)&&plan.destination.x==mainTank.x&&plan.destination.y==mainTank.y);}
 ai.rangeUnavailable=true;assert(PlanMoltenCorePack(&ai,plan));ai.rangeUnavailable=false;
 bot.x=mainTank.x;bot.y=mainTank.y;assert(PlanMoltenCorePack(&ai,plan)&&plan.destination.x==bot.x&&plan.destination.y==bot.y);
 h2.victim=&bot;assert(PlanMoltenCorePack(&ai,plan)&&plan.source==bot.guid&&plan.destination.x==secondTank.x);h2.victim=&mainTank;
 ai.path=false;assert(!PlanMoltenCorePack(&ai,plan));ai.path=true;ai.minimum=8;
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
 // Surger hunters share the exact tank stack and can enter melee there.
 boss.entry=12101;boss.victim=&mainTank;ai.context.possible.value={10};bot.cls=CLASS_HUNTER;bot.ranged=true;
 assert(PlanMoltenCoreTrash(&ai,plan)&&plan.spell==19196&&std::hypot(plan.destination.x-mainTank.x,plan.destination.y-mainTank.y)<=3);
 assert(MoltenCorePackStackRequired(&ai));boss.entry=11673;assert(!MoltenCorePackStackRequired(&ai));boss.entry=12101;
 bot.cls=CLASS_WARRIOR;bot.ranged=false;
 // Mixed imp/surger admission: one loose imp cannot deadlock the whole raid.
 boss.entry=12101;boss.victim=&mainTank;ai.context.current.value=10;ai.context.possible.value={10,40,41,42};
 h1.victim=&mainTank;h2.victim=&bot;h3.victim=&mainTank;assert(MoltenCoreImpPack(&ai));
 ai.combatStart=time(0)-1;assert(MoltenCoreImpPack(&ai)); // live pressure bypasses the opening hold
 h2.victim=&mainTank;assert(!MoltenCoreImpPack(&ai));h2.victim=&bot;ai.combatStart=time(0)-12;
 h3.cc=true;assert(!MoltenCoreImpPack(&ai));h3.cc=false;h3.combat=false;assert(!MoltenCoreImpPack(&ai));h3.combat=true;
 h1.victim=h2.victim=h3.victim=&bot;assert(MoltenCoreImpPack(&ai)); // nearby reactive tanks still recover a loose pack
 mainTank.mobile=secondTank.mobile=false;assert(!MoltenCoreImpPack(&ai));mainTank.mobile=secondTank.mobile=true;ai.context.current.value=0;
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

 {
 // Magmadar: a blocked preferred lane still yields maximum usable range;
 // other ranged members are at least five yards away, with an eight-yard goal.
 Player tank,mage,peer;Group g;tank.guid=900;tank.tank=true;tank.x=2;mage.guid=901;mage.ranged=true;mage.cls=CLASS_MAGE;peer.guid=902;peer.ranged=true;peer.x=-41;
 g.Add(&tank);g.Add(&mage);g.Add(&peer);PlayerbotAI tankBrain(&tank),brain(&mage);Creature b;b.guid=903;b.entry=11982;b.victim=&tank;
 units={&tank,&mage,&peer,&b};EncounterPosition p;brain.rejectFrontLane=true;
 assert(PlanMagmadarFormation(&brain,&b,p));assert(std::hypot(p.destination.x,p.destination.y)>=40.9f&&p.destination.y>5);
 assert(std::hypot(p.destination.x-peer.x,p.destination.y-peer.y)>=5);
 mage.x=p.destination.x;mage.y=p.destination.y;auto station=p.destination;
 assert(PlanMagmadarFormation(&brain,&b,p)&&p.destination.x==station.x&&p.destination.y==station.y);
 brain.rejectFrontLane=false;brain.rejectFarPaths=true;mage.x=-30;assert(PlanMagmadarFormation(&brain,&b,p)&&std::hypot(p.destination.x,p.destination.y)<40&&std::hypot(p.destination.x,p.destination.y)>30);brain.rejectFarPaths=false;
 mage.cls=CLASS_HUNTER;mage.ranged=false;assert(PlanMagmadarFormation(&brain,&b,p)&&std::hypot(p.destination.x,p.destination.y)>40);mage.cls=CLASS_MAGE;mage.ranged=true;
 b.o=3.141592653589793f;brain.rejectFrontLane=false;
 assert(PlanMagmadarFormation(&brain,&b,p)&&p.destination.x>0); // fear has turned the boss; never retain its front
 mage.x=-30;mage.y=0;peer.x=-30;peer.y=10;b.o=0;
 assert(PlanMagmadarTank(&tankBrain,&b,p));auto original=p.destination;
 tank.x=-12;b.o=3.141592653589793f; // feared away; stable tank anchor restores orientation
 assert(PlanMagmadarTank(&tankBrain,&b,p)&&p.destination.x==original.x&&p.destination.y==original.y);
 tank.x=original.x;tank.y=original.y;b.o=0;
 liveFire={{{original.x,original.y,0},8}};
 assert(PlanMagmadarTank(&tankBrain,&b,p)&&std::hypot(p.destination.x-original.x,p.destination.y-original.y)>=8);
 auto relocated=p.destination;tank.x=relocated.x;tank.y=relocated.y;liveFire.clear();
 assert(PlanMagmadarTank(&tankBrain,&b,p)&&p.destination.x==relocated.x&&p.destination.y==relocated.y);
 }
 {
 // Double-pull imps retain all engaged members, elect one ready AoE taunt,
 // reject overlap while its native aura runs, then hand off after cooldown.
 Player t1,t2,healer;Group g;t1.guid=910;t2.guid=911;healer.guid=912;t1.tank=t2.tank=true;t1.cls=CLASS_WARRIOR;t2.cls=CLASS_DRUID;
 g.Add(&t1);g.Add(&t2);g.Add(&healer);PlayerbotAI a1(&t1),a2(&t2);a1.learned={"challenging shout"};a2.learned={"challenging roar"};
 Creature imps[4],unpulled;units={&t1,&t2,&healer};for(unsigned i=0;i<4;++i){imps[i].guid=920+i;imps[i].entry=11669;imps[i].victim=&healer;units.push_back(&imps[i]);a1.context.possible.value.push_back(imps[i].guid);a2.context.possible.value.push_back(imps[i].guid);}
 imps[3].x=35;int firstPack,secondPack;imps[0].formation=&firstPack;imps[3].formation=&secondPack;
 assert(MoltenCorePack(&a1).size()==4);
 assert(MoltenCoreImpTauntAllowed(&a1,"challenging shout")&&!MoltenCoreImpTauntAllowed(&a2,"challenging roar"));
 imps[0].auras={1161};assert(!MoltenCoreImpTauntAllowed(&a2,"challenging roar"));imps[0].auras.clear();
 a1.learned.clear();assert(MoltenCoreImpTauntAllowed(&a2,"challenging roar"));
 imps[0].victim=imps[1].victim=imps[2].victim=&t1;assert(!MoltenCoreImpTauntAllowed(&a2,"challenging roar"));
 imps[0].victim=imps[1].victim=&healer;unpulled.guid=930;unpulled.entry=11671;unpulled.combat=false;units.push_back(&unpulled);a2.context.possible.value.push_back(930);
 assert(!MoltenCoreImpTauntAllowed(&a2,"challenging roar"));unpulled.combat=true;unpulled.cc=true;assert(!MoltenCoreImpTauntAllowed(&a2,"challenging roar"));
 t2.map=530;assert(MoltenCoreImpTauntAllowed(&a2,"challenging roar"));t2.map=409;
 }
 {
 // The leader/caster has not attacked. Actual tank engagement admits the
 // hound stack and leaves it as soon as native pack combat ends.
 Player tank,mage,off;Group group;tank.guid=1001;tank.tank=true;mage.guid=1002;mage.cls=CLASS_MAGE;mage.ranged=true;mage.combat=false;mage.x=-30;
 off.guid=1003;off.tank=true;off.ranged=true;group.Add(&tank);group.Add(&mage);group.Add(&off);
 PlayerbotAI brain(&mage),offBrain(&off);Creature hounds[2];units={&tank,&mage,&off};
 for(unsigned i=0;i<2;++i){hounds[i].guid=1010+i;hounds[i].entry=11671;hounds[i].victim=&tank;units.push_back(&hounds[i]);brain.context.possible.value.push_back(hounds[i].guid);}
 EncounterPosition p;assert(PlanMoltenCoreTrash(&brain,p)&&p.active&&p.destination.x==tank.x);
#ifdef MANGOSBOT_ZERO
 Creature ancient;ancient.guid=1019;ancient.entry=11673;ancient.victim=&tank;units.push_back(&ancient);brain.context.possible.value.push_back(ancient.guid);
 assert(PlanMoltenCoreTrash(&brain,p)&&p.spell==19364&&std::hypot(p.destination.x,p.destination.y)>=40);
 ancient.combat=false;
#endif
 hounds[0].combat=hounds[1].combat=false;assert(!PlanMoltenCoreTrash(&brain,p));
 Creature boss;boss.guid=1020;boss.entry=11982;boss.victim=&tank;off.x=-25;units.push_back(&boss);
 assert(PlanMagmadarFormation(&offBrain,&boss,p));assert(std::hypot(p.destination.x,p.destination.y)<=3.1f);
 off.x=p.destination.x;off.y=p.destination.y;auto melee=p.destination;
 assert(PlanMagmadarFormation(&offBrain,&boss,p)&&p.destination.x==melee.x&&p.destination.y==melee.y);
}

 {
 Player tank,hunter,lock;Group group;tank.guid=2001;tank.tank=true;hunter.guid=2002;hunter.cls=CLASS_HUNTER;hunter.ranged=true;
 lock.guid=2003;lock.cls=CLASS_WARLOCK;lock.ranged=true;group.Add(&tank);group.Add(&hunter);group.Add(&lock);
 PlayerbotAI hunt(&hunter),warlock(&lock);Creature firelord,dog,dog2;firelord.guid=2010;firelord.entry=11668;firelord.victim=&tank;
 dog.guid=2011;dog.entry=11671;dog.victim=&tank;dog.combat=false;dog2.guid=2012;dog2.entry=11671;dog2.victim=&tank;dog2.combat=false;units={&tank,&hunter,&lock,&firelord,&dog,&dog2};
 hunt.context.current.value=warlock.context.current.value=firelord.guid;hunt.context.possible.value=warlock.context.possible.value={firelord.guid,dog.guid,dog2.guid};
 EncounterPosition p;
 assert(PlanMoltenCoreTrash(&hunt,p)&&p.active&&p.boss==firelord.guid&&p.spell==19630);
 auto bounds=FirelordRangedBounds(&hunt,&firelord);float radial=std::hypot(p.destination.x-firelord.x,p.destination.y-firelord.y);
 assert(radial>bounds.first+1&&radial<=bounds.second-2+0.01f); // hunter at boss feet gains native shooting room
 hunter.x=p.destination.x;hunter.y=p.destination.y;assert(PlanFirelordRanged(&hunt,p)&&p.destination.x==hunter.x&&p.destination.y==hunter.y);
 lock.x=80;assert(PlanMoltenCoreTrash(&warlock,p)&&p.boss==firelord.guid);
 assert(std::hypot(p.destination.x,p.destination.y)<=warlock.spellRange+1.01f); // caster approaches without leader DPS
 dog.combat=dog2.combat=true;assert(MoltenCorePackStackRequired(&hunt)&&!PlanFirelordRanged(&hunt,p));
 assert(PlanMoltenCoreTrash(&hunt,p)&&p.boss==dog.guid&&p.destination.x==tank.x); // mandatory pack still wins
 dog.combat=dog2.combat=false;assert(!MoltenCorePackStackRequired(&hunt)&&PlanFirelordRanged(&hunt,p)); // next pull releases stack
 for(unsigned f=0;f<12;++f){firelord.visible=true;hunt.rangeUnavailable=false;firelord.world=firelord.alive=firelord.combat=true;firelord.instance=1;firelord.cc=firelord.hardCC=false;firelord.victim=&tank;
 hunter.teleport=false;hunter.los=true;hunt.owned=true;hunt.path=true;tank.tank=true;
 if(f==0)firelord.world=false;if(f==1)firelord.alive=false;if(f==2)firelord.combat=false;if(f==3)firelord.instance=2;
 if(f==4)firelord.cc=true;if(f==5)firelord.hardCC=true;if(f==6)hunter.teleport=true;if(f==7)hunt.owned=false;if(f==8)hunt.path=false;if(f==9)tank.tank=false;if(f==10){firelord.visible=false;hunter.los=false;}if(f==11)hunt.rangeUnavailable=true;
 assert(!PlanFirelordRanged(&hunt,p));}
 }

 {
 // A multiboss pull must not hold a melee DPS bot at an unrelated lower-GUID
 // trash mob while its real attack target is elsewhere.
 Player tank,melee;Group group;tank.guid=3001;tank.tank=true;melee.guid=3002;group.Add(&tank);group.Add(&melee);
 PlayerbotAI brain(&melee);Creature guard,boss,other;guard.guid=3010;guard.entry=11661;guard.victim=&tank;
 boss.guid=3020;boss.entry=12259;boss.victim=&tank;other.guid=3030;other.entry=11661;other.victim=&tank;other.x=20;
 units={&tank,&melee,&guard,&boss,&other};brain.context.possible.value={guard.guid,other.guid};brain.context.current.value=boss.guid;
 EncounterPosition p;assert(!PlanMoltenCoreTrash(&brain,p));
 brain.context.current.value=other.guid;assert(PlanMoltenCoreTrash(&brain,p)&&p.boss==other.guid);
 }
std::cout<<"PASS: actual MC off-target interrupts, native era abilities, dispels, frenzy, mind control, sheep assignments, tank allocation and Magmadar positioning\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='mc-support-') as directory:
  d=Path(directory);(d/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=d,check=True)
  subprocess.run([str(d/'test.exe')],cwd=d,check=True)
