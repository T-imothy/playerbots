"""Production CC, spell-target, expansion-interrupt and heal-search regressions."""
from pvp_warsong_regression import COMMON, ROOT, source, run
from behavior_regression import block

def code():
    common=COMMON.replace('struct Unit;struct Player;', 'struct Group;struct Unit;struct Player;')
    common=common.replace('Unit* GetUnit(ObjectGuid g){return bot->bg->map.GetPlayer(g);}', '')
    common=common.replace('Unit* victim=nullptr;', 'bool periodic=false,mana=true,immobile=false;std::map<std::string,bool> ownAuras;Unit* victim=nullptr;')
    common=common.replace('bool IsInWorld(){', '''bool HasAuraType(int){return periodic;}bool HasMana(){return mana;}
 bool IsImmobilizedState(){return immobile;}uint32 GetMaxHealth(){return 100;}
 int GetMaxNegativeAuraModifier(int){return 0;}bool IsInWorld(){''')
    common=common.replace('struct Player:Unit{', '''struct Group{struct Member{ObjectGuid guid;};using MemberSlotList=std::list<Member>;using member_citerator=MemberSlotList::const_iterator;
 MemberSlotList slots;auto& GetMemberSlots(){return slots;}};
struct Player:Unit{Group* group=nullptr;Group* GetGroup(){return group;}''')
    common=common.replace('bool real=false,master=false,canMove=true;', '''bool real=false,master=false,canMove=true,cast=true,cc=true;float range=25;
 std::map<ObjectGuid,Unit*> units;bool CanCastSpell(std::string,Unit*,int,void*,bool,bool){return cast;}
 bool IsTank(Player*){return false;}bool HasStrategy(std::string,int){return cc;}
 float GetRange(std::string){return range;}Unit* GetUnit(ObjectGuid g){return units[g];}
 bool HasAura(std::string name,Unit* u,bool,bool){return u&&u->ownAuras[name];}
 bool HasMyAura(std::string name,Unit* u){return u&&u->ownAuras[name];}''')
    common=common.replace('struct Facade{', '''struct Facade{
 float GetDistance2d(Unit* a,float x,float y){return std::sqrt((a->x-x)*(a->x-x)+(a->y-y)*(a->y-y));}
 bool IsDistanceLessOrEqualThan(float a,float b){return a<=b;}bool IsAlive(Unit* u){return u->alive;}''')
    common=common.replace('struct Config{float lowHealth=40;}', 'struct Config{float lowHealth=40,mediumHealth=50,sightDistance=75,aoeRadius=10;}')
    declarations=r'''
enum{SPELL_AURA_PERIODIC_DAMAGE,SPELL_AURA_MOD_HEALING_PCT};
namespace BotState{constexpr int BOT_STATE_COMBAT=1;}
struct WorldLocation{float coord_x=0,coord_y=0;};
struct ThreatManager{};
struct RtiTargetValue{static int GetRtiIndex(std::string s){return s=="none"?-1:0;}};
struct FindTargetStrategy{PlayerbotAI* ai;Unit* result=nullptr;FindTargetStrategy(PlayerbotAI* a):ai(a){}
 virtual void CheckAttacker(Unit*,ThreatManager*)=0;};
struct ObjectMgr{Player* GetPlayer(ObjectGuid){return nullptr;}}sObjectMgr;
struct CastSpellAction{PlayerbotAI* ai;AiObjectContext* context;std::string name;bool useful=true;
 CastSpellAction(PlayerbotAI* a,std::string n):ai(a),context(a->GetAiObjectContext()),name(n){}virtual ~CastSpellAction(){}
 virtual Unit* GetTarget();virtual std::string GetTargetName(){return "current target";}
 virtual std::string GetTargetQualifier(){return "";}virtual std::string GetSpellName(){return name;}
 virtual bool isUseful(){return useful;}virtual std::string getName(){return name;}};
struct CastMeleeSpellAction:CastSpellAction{using CastSpellAction::CastSpellAction;};
struct CastSpellOnEnemyHealerAction:CastSpellAction{using CastSpellAction::CastSpellAction;
 std::string GetTargetName()override{return "enemy healer target";}std::string GetTargetQualifier()override{return name;}};
struct InterruptSpellTrigger{std::string name;InterruptSpellTrigger(PlayerbotAI*,std::string n):name(n){}};
struct InterruptEnemyHealerTrigger:InterruptSpellTrigger{using InterruptSpellTrigger::InterruptSpellTrigger;};
struct NoCurseTrigger{PlayerbotAI* ai;Unit* target;Unit* GetTarget(){return target;}bool IsActive();};
struct NoCurseOnAttackerTrigger{PlayerbotAI* ai;AiObjectContext* context;bool IsActive();};
struct DebuffTrigger{bool active=true;virtual bool IsActive(){return active;}};
struct EntanglingRootsKiteTrigger:DebuffTrigger{PlayerbotAI* ai;Player* bot;AiObjectContext* context;Unit* target=nullptr;
 Unit* GetTarget(){return target;}bool HasMaxDebuffs(){return false;}bool IsActive()override;};
bool UpcomingEncounterHealingWindow(Unit*,Unit*){return false;}
struct PartyMemberToHeal{Player* bot;PlayerbotAI* ai;bool Check(Unit*);};
'''
    bodies=block(source('values/CcTargetValue.cpp'),'class FindTargetForCcStrategy')+';\n'
    bodies+=block(source('rogue/RogueActions.h'),'    class CastSapAction')+';\n'
    bodies+=block(source('actions/GenericSpellActions.cpp'),'Unit* CastSpellAction::GetTarget')+'\n'
    bodies+='#include "playerbot/strategy/shaman/ShamanInterrupt.h"\n'
    for file,names in (('shaman/ShamanActions.h',['CastWindShearAction','CastWindShearOnEnemyHealerAction']),
        ('shaman/ShamanTriggers.h',['WindShearInterruptSpellTrigger','WindShearInterruptEnemyHealerSpellTrigger'])):
        for name in names:bodies+=block(source(file),'    class '+name)+';\n'
    for file,method in (('warlock/WarlockTriggers.cpp','bool NoCurseTrigger::IsActive'),
        ('warlock/WarlockTriggers.cpp','bool NoCurseOnAttackerTrigger::IsActive'),
        ('druid/DruidTriggers.cpp','bool EntanglingRootsKiteTrigger::IsActive'),
        ('values/PartyMemberToHeal.cpp','bool PartyMemberToHeal::Check')):
        bodies+=block(source(file),method)+'\n'
    cases=r'''
int main(){
 Player bot,current,secondary;bot.guid=1;current.guid=2;secondary.guid=3;Group group;bot.group=&group;
 PlayerbotAI a{&bot};bot.ai=&a;AiObjectContext* context=&a.context;
 context->GetValue<std::string>("rti cc")->Set("none");context->GetValue<Unit*>("current target")->Set(&current);
 FindTargetForCcStrategy cc(&a,"polymorph");cc.CheckAttacker(&secondary,nullptr);assert(cc.result==&secondary);
 FindTargetForCcStrategy skipCurrent(&a,"polymorph");skipCurrent.CheckAttacker(&current,nullptr);assert(!skipCurrent.result);
 a.cast=false;FindTargetForCcStrategy immune(&a,"polymorph");immune.CheckAttacker(&secondary,nullptr);assert(!immune.result);a.cast=true;
 secondary.periodic=true;FindTargetForCcStrategy dotted(&a,"polymorph");dotted.CheckAttacker(&secondary,nullptr);assert(!dotted.result);secondary.periodic=false;
 secondary.alive=false;FindTargetForCcStrategy dead(&a,"polymorph");dead.CheckAttacker(&secondary,nullptr);assert(!dead.result);secondary.alive=true;
 secondary.map=1;FindTargetForCcStrategy otherMap(&a,"polymorph");otherMap.CheckAttacker(&secondary,nullptr);assert(!otherMap.result);secondary.map=489;
 context->GetValue<Unit*>("rti cc target")->Set(&secondary);a.cc=false;
 FindTargetForCcStrategy marked(&a,"polymorph");marked.CheckAttacker(&secondary,nullptr);assert(marked.result==&secondary);
 a.cast=false;FindTargetForCcStrategy markedImmune(&a,"polymorph");markedImmune.CheckAttacker(&secondary,nullptr);assert(!markedImmune.result);a.cast=true;
 CastSapAction sap(&a);context->GetValue<Unit*>("cc target::sap")->Set(&secondary);
 assert(sap.GetTarget()==&secondary);sap.useful=false;assert(!sap.isUseful());
 CastWindShearAction interrupt(&a);CastWindShearOnEnemyHealerAction healerInterrupt(&a);
 WindShearInterruptSpellTrigger trigger(&a);WindShearInterruptEnemyHealerSpellTrigger healerTrigger(&a);
#ifdef MANGOSBOT_TWO
 const std::string native="wind shear";
#else
 const std::string native="earth shock";
#endif
 assert(interrupt.name==native&&trigger.name==native&&healerInterrupt.name==native&&healerTrigger.name==native);
 context->GetValue<Unit*>("enemy healer target::"+native)->Set(&secondary);assert(healerInterrupt.GetTarget()==&secondary);
 NoCurseTrigger curse{&a,&current};assert(curse.IsActive());current.ownAuras["curse of exhaustion"]=true;assert(!curse.IsActive());
 current.ownAuras.clear();current.ownAuras["curse of agony"]=true;assert(!curse.IsActive());
 NoCurseOnAttackerTrigger curseOther{&a,context};a.units[secondary.guid]=&secondary;
 context->GetValue<std::list<ObjectGuid>>("possible attack targets")->Set({secondary.guid});assert(curseOther.IsActive());
 secondary.ownAuras["curse of exhaustion"]=true;assert(!curseOther.IsActive());
 EntanglingRootsKiteTrigger root;root.ai=&a;root.bot=&bot;root.context=context;root.target=&secondary;
 secondary.mana=false;secondary.victim=&bot;secondary.x=10;assert(root.IsActive());
 secondary.victim=nullptr;assert(!root.IsActive());secondary.victim=&bot;secondary.immobile=true;assert(!root.IsActive());
 secondary.immobile=false;secondary.x=30;assert(!root.IsActive());root.active=false;assert(!root.IsActive());
 PartyMemberToHeal heal{&bot,&a};a.range=100;sServerFacade.friendly=true;secondary.x=80;assert(heal.Check(&secondary));
 secondary.x=101;assert(!heal.Check(&secondary));secondary.x=20;secondary.alive=false;assert(!heal.Check(&secondary));
 secondary.alive=true;secondary.map=1;assert(!heal.Check(&secondary));secondary.map=489;secondary.teleport=true;assert(!heal.Check(&secondary));
 assert(!heal.Check(nullptr));assert(!heal.Check(&bot));
}
'''
    return common+declarations+bodies+cases

if __name__=='__main__':
    for era in ('ZERO','ONE','TWO'):run(code(),'CC legality, Sap routing, native shaman interrupts, curses, roots and heal range',era)
