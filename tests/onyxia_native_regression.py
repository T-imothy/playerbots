"""Execute Onyxia discovery, native footprints, planner and dispatch in every era.

Native spell/position fixtures are captured from the deployed world databases;
movement/path admission remains a controlled core boundary, not a live raid.
"""
from pathlib import Path
import json
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
value = (root / 'playerbot/strategy/values/OnyxiaPositionValue.cpp').read_text()
actions = (root / 'playerbot/strategy/actions/OnyxiasLairDungeonActions.cpp').read_text()
methods = '\n'.join(block(value, key).replace('ai::', '') for key in (
    'Unit* ai::FindOnyxiaBoss(', 'bool ai::OnyxiaBreathThreats(',
    'EncounterPosition OnyxiaPositionValue::Calculate('))
methods += '\n' + block(actions, 'bool OnyxiaPositionAction::GetPlan(')
for method in ('isUseful', 'ShouldReactionInterruptCast', 'Execute'):
    methods += '\n' + block(actions, 'bool OnyxiaPositionAction::' + method + '(')
methods += '\n' + block(actions, 'bool IsOnyxiaAddEntry(')
methods += '\n' + block(actions, 'Unit* OnyxiaAddsAction::GetTarget(')

code = r'''
#include <cassert>
#include <algorithm>
#include <cmath>
#include <ctime>
#include <iostream>
#include <list>
#include <map>
#include <set>
#include <string>
#include <vector>
#include <type_traits>
#include "__GEOMETRY__"
using namespace ai;
using uint32=unsigned;
struct ObjectGuid {unsigned v=0;ObjectGuid()=default;ObjectGuid(unsigned n):v(n){}void Clear(){v=0;}
 bool operator==(ObjectGuid b)const{return v==b.v;}bool operator!=(ObjectGuid b)const{return v!=b.v;}
 bool operator<(ObjectGuid b)const{return v<b.v;}};
struct EncounterPosition {bool active=false,exclusive=true;unsigned map=0,instance=0,spell=0;ObjectGuid boss,source;encounter::Point destination;};
enum {MAX_EFFECT_INDEX=3,SPELL_EFFECT_SCHOOL_DAMAGE=2,SPELL_EFFECT_TRIGGER_SPELL=64,
 TARGET_LOCATION_DATABASE=17,TARGET_ENUM_UNITS_ENEMY_AOE_AT_DEST_LOC=16,CURRENT_GENERIC_SPELL=0,SPELL_STATE_FINISHED=1};
struct SpellEntry {unsigned Id=0,Effect[3]={2,64,0},EffectImplicitTargetA[3]={17,1,0},EffectImplicitTargetB[3]={16,0,0},EffectRadiusIndex[3]={0,0,0},EffectTriggerSpell[3]={0,0,0};};
struct RadiusStore {std::map<unsigned,float> rows;const float* LookupEntry(unsigned id){auto i=rows.find(id);return i==rows.end()?nullptr:&i->second;}} sSpellRadiusStore;
float GetSpellRadius(const float* r){return r?*r:0;}
struct SpellTargetPosition{unsigned target_mapId=249;float target_X=0,target_Y=0,target_Z=0,target_Orientation=0;};
struct Facade{std::map<unsigned,SpellEntry> rows;const SpellEntry* LookupSpellInfo(unsigned id){auto i=rows.find(id);return i==rows.end()?nullptr:&i->second;}} sServerFacade;
struct SpellMgr{std::map<unsigned,SpellTargetPosition> rows;const SpellTargetPosition* GetSpellTargetPosition(unsigned id){auto i=rows.find(id);return i==rows.end()?nullptr:&i->second;}}sSpellMgr;
struct Unit;
struct Spell{SpellEntry* m_spellInfo=nullptr;int state=0;int getState()const{return state;}
 struct Targets {Unit* unit=nullptr;Unit* getUnitTarget()const{return unit;}}m_targets;};
struct Map{};
struct Unit{virtual ~Unit()=default;ObjectGuid guid;unsigned entry=0,phase=1;Map* map=nullptr;
 bool world=true,alive=true,combat=true,charm=false,levitate=false,attackable=true,cc=false;float x=0,y=0,z=0,o=0;Unit* victim=nullptr;Spell* cast=nullptr;
 bool IsInWorld()const{return world;}bool IsAlive()const{return alive;}bool IsInCombat()const{return combat;}bool HasCharmer()const{return charm;}
 unsigned GetEntry()const{return entry;}ObjectGuid GetObjectGuid()const{return guid;}Unit* GetVictim(){return victim;}
 float GetPositionX()const{return x;}float GetPositionY()const{return y;}float GetPositionZ()const{return z;}float GetOrientation()const{return o;}
 bool IsLevitating()const{return levitate;}float GetCombatReach()const{return 1.5f;}float GetAngle(Unit* u){return std::atan2(u->y-y,u->x-x);}
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}
 float GetDistance(Unit* u){return GetDistance(u->x,u->y,u->z);}Spell* GetCurrentSpell(int){return cast;}
};
struct Player;
struct GroupReference{Player* player=nullptr;GroupReference* following=nullptr;Player* getSource(){return player;}GroupReference* next(){return following;}};
struct Group{GroupReference* first=nullptr;GroupReference* GetFirstMember(){return first;}};
struct Player:Unit{unsigned mapId=249,instance=1;bool teleport=false,tank=false;Group* group=nullptr;
 bool IsBeingTeleported(){return teleport;}unsigned GetMapId(){return mapId;}unsigned GetInstanceId(){return instance;}Group* GetGroup(){return group;}
 bool IsInMap(Unit* u){return u&&map==u->map&&phase==u->phase;}void UpdateAllowedPositionZ(float,float,float&){}
};
struct PlayerbotAI;
template<class T>struct Value{PlayerbotAI* ai;std::string name;T Get();};
struct PlayerbotAI{Player* bot=nullptr;std::map<ObjectGuid,Unit*> units;std::list<ObjectGuid> raw,attackers,possible;
 ObjectGuid current,marked,ordered;EncounterPosition plan;bool ranged=false,healer=false,path=true,canMove=true,moving=false;unsigned pathChecks=0,moves=0,stops=0;
 bool CanMove(){return canMove;}void StopMoving(){++stops;moving=false;}
 Player* GetBot(){return bot;}PlayerbotAI* GetAiObjectContext(){return this;}bool IsTank(Player* p){return p->tank;}bool IsRanged(Player*){return ranged;}bool IsHeal(Player*){return healer;}
 Unit* GetUnit(ObjectGuid g){auto i=units.find(g);return i==units.end()?nullptr:i->second;}
 template<class T>Value<T>* GetValue(const char* name,const char* =nullptr){static Value<T>v;v={this,name};return &v;}
};
template<class T>T Value<T>::Get(){if constexpr(std::is_same_v<T,std::list<ObjectGuid>>)return name=="possible targets"?ai->raw:name=="attackers"?ai->attackers:ai->possible;
 else if constexpr(std::is_same_v<T,ObjectGuid>)return name=="current target"?ai->current:name=="rti target"?ai->marked:ai->ordered;else return ai->plan;}
#define AI_VALUE(type,key) ai->GetValue<type>(key)->Get()
#define AI_VALUE2(type,key,q) ai->GetValue<type>(key,q)->Get()
bool ValidateEncounterDestination(PlayerbotAI*a,EncounterPosition&p){++a->pathChecks;return a->path&&p.map==a->bot->mapId&&p.instance==a->bot->instance;}
bool EncounterMovementRequired(Player* b,const encounter::Point& p,float tolerance){return b->GetDistance(p.x,p.y,p.z)>tolerance;}
float NativeEncounterSpellRadius(unsigned id){return id==18392?8:id==68958?15:0;}
struct {float sightDistance=100;}sPlayerbotAIConfig;
struct PossibleAttackTargetsValue{static bool IsValid(Unit*u,Player*,float,bool,bool){return u->attackable&&!u->cc;}
 static bool HasBreakableCC(Unit*u,Player*){return u->cc;}static bool HasUnBreakableCC(Unit*,Player*){return false;}};
struct OnyxiaPositionValue{PlayerbotAI*ai;Player*bot;unsigned breath=0;time_t breathUntil=0,fireballUntil=0;ObjectGuid owner;unsigned instance=0;EncounterPosition Calculate();};
struct Event{};
struct OnyxiaPositionAction{PlayerbotAI*ai;Player*bot;static bool GetPlan(PlayerbotAI*,EncounterPosition&);
 bool isUseful();bool ShouldReactionInterruptCast()const;bool Execute(Event&);bool IsReaction(){return true;}void SetDuration(unsigned){}
 bool MoveTo(unsigned,float,float,float,bool,bool,bool,bool){++ai->moves;return true;}};
struct OnyxiaAddsAction{PlayerbotAI*ai;Player*bot;Unit*GetTarget();};
__METHODS__
void Native(unsigned id,unsigned next,float radius,float x,float y,float z){SpellEntry e;e.Id=id;e.EffectRadiusIndex[0]=id;e.EffectTriggerSpell[1]=next;
 if(!next)e.Effect[1]=0;sServerFacade.rows[id]=e;sSpellRadiusStore.rows[id]=radius;sSpellMgr.rows[id]={249,x,y,z,0};}
int main(){
 __DATA__
 __CHAINS__
 // Native 30-yard circles expose the former 22-yard line's unsafe hold.
 std::vector<encounter::Circle> circles;assert(OnyxiaBreathThreats(17086,circles));
 auto witness=circles.front().center;witness.y+=23;
#ifndef MANGOSBOT_TWO
 assert(!encounter::OutsideCircles(witness,circles));
#endif
 auto saved=sSpellMgr.rows.at(17087);sSpellMgr.rows.erase(17087);circles.clear();assert(!OnyxiaBreathThreats(17086,circles)&&circles.empty());sSpellMgr.rows[17087]=saved;
 sServerFacade.rows[17087].EffectTriggerSpell[1]=17086;assert(!OnyxiaBreathThreats(17086,circles));sServerFacade.rows[17087].EffectTriggerSpell[1]=17088;
 sSpellMgr.rows[17087].target_mapId=1;assert(!OnyxiaBreathThreats(17086,circles));sSpellMgr.rows[17087]=saved;
 Map map,other;Player bot,healer;Group group;GroupReference ref{&healer,nullptr};group.first=&ref;bot.group=healer.group=&group;
 bot.map=healer.map=&map;bot.guid=1;healer.guid=2;bot.z=healer.z=-86;
 Unit boss,whelp,guard;boss.map=whelp.map=guard.map=&map;boss.guid=3;whelp.guid=4;guard.guid=5;boss.entry=10184;whelp.entry=11262;guard.entry=36561;
 boss.z=-60;boss.levitate=true;whelp.z=guard.z=-86;PlayerbotAI a;a.bot=&bot;a.units={{3,&boss},{4,&whelp},{5,&guard}};a.raw={3,4,5};a.attackers={4};a.possible={4,5};
 assert(FindOnyxiaBoss(&a)==&boss);a.attackers.clear();assert(FindOnyxiaBoss(&a)==&boss);
 boss.map=&other;assert(!FindOnyxiaBoss(&a));boss.map=&map;boss.charm=true;assert(!FindOnyxiaBoss(&a));boss.charm=false;
 OnyxiaPositionValue planner{&a,&bot};Spell breath{&sServerFacade.rows.at(17086)};boss.cast=&breath;
 bot.x=circles.empty()?sSpellMgr.rows[17086].target_X:0;bot.y=sSpellMgr.rows[17086].target_Y;
 auto p=planner.Calculate();assert(p.active&&p.exclusive&&a.pathChecks);circles.clear();assert(OnyxiaBreathThreats(17086,circles));assert(encounter::OutsideCircles(p.destination,circles));
 // Missing walking/floor path cannot be converted into a fabricated move.
 a.path=false;assert(!planner.Calculate().active);a.path=true;
 // Actual Nova footprint participates with the native breath, Wrath only.
 SpellEntry novaInfo;novaInfo.Id=68958;Spell nova{&novaInfo};guard.cast=&nova;guard.x=p.destination.x;guard.y=p.destination.y;
 p=planner.Calculate();assert(p.active);
#ifdef MANGOSBOT_TWO
 assert(encounter::Distance2d(p.destination,{guard.x,guard.y,guard.z})>=17);
#endif
 boss.cast=nullptr;planner.breathUntil=0;
#ifdef MANGOSBOT_TWO
 bot.x=guard.x;bot.y=guard.y;p=planner.Calculate();assert(p.active&&p.spell==68958);
 a.plan=p;EncounterPosition novaDispatch;assert(OnyxiaPositionAction::GetPlan(&a,novaDispatch));
 guard.cast=nullptr;assert(!OnyxiaPositionAction::GetPlan(&a,novaDispatch));
#else
 assert(!planner.Calculate().active); // Wrath-only guardians never leak into the old encounter.
#endif
 guard.cast=nullptr;
 // Fireball isolation remains through a short projectile window, then releases.
 SpellEntry ballInfo;ballInfo.Id=18392;Spell ball{&ballInfo};ball.m_targets.unit=&bot;boss.cast=&ball;bot.x=bot.y=healer.x=healer.y=0;
 p=planner.Calculate();assert(p.active&&p.exclusive&&encounter::Distance2d(p.destination,{0,0,-86})>=10);
 boss.cast=nullptr;assert(planner.Calculate().active);planner.fireballUntil=time(nullptr)-1;assert(!planner.Calculate().active);
 boss.combat=false;assert(!planner.Calculate().active&&planner.breath==0&&planner.fireballUntil==0);boss.combat=true;
 boss.levitate=false;boss.z=-86;bot.x=4;bot.y=0;boss.o=0;a.current=3;
 p=planner.Calculate();assert(p.active&&!p.exclusive);a.plan=p;EncounterPosition dispatched;assert(OnyxiaPositionAction::GetPlan(&a,dispatched));
 OnyxiaPositionAction action{&a,&bot};Event event;assert(action.isUseful()&&action.ShouldReactionInterruptCast());
 a.canMove=false;assert(!action.Execute(event)&&a.moves==0);a.canMove=true;assert(action.Execute(event)&&a.moves==1);
 // Safe nonexclusive flank stations must not consume actions or cancel casts.
 bot.x=p.destination.x;bot.y=p.destination.y;assert(!action.isUseful()&&!action.ShouldReactionInterruptCast()&&!action.Execute(event));
 bot.x=4;bot.y=0;
 boss.victim=&bot;assert(!OnyxiaPositionAction::GetPlan(&a,dispatched));boss.victim=nullptr;
 boss.o=1.5707963268f;assert(!OnyxiaPositionAction::GetPlan(&a,dispatched));boss.o=0;
 boss.levitate=true;assert(!OnyxiaPositionAction::GetPlan(&a,dispatched));boss.levitate=false;
 bot.teleport=true;assert(!planner.Calculate().active&&!OnyxiaPositionAction::GetPlan(&a,dispatched));bot.teleport=false;
 bot.alive=false;assert(!FindOnyxiaBoss(&a));bot.alive=true;
 // A new pull/instance cannot reuse a former boss's breath/projectile state.
 planner.breath=17086;planner.breathUntil=time(nullptr)+8;planner.fireballUntil=time(nullptr)+2;planner.owner=99;
 planner.Calculate();assert(planner.breath==0&&planner.fireballUntil==0);
 planner.breath=17086;planner.breathUntil=time(nullptr)+8;bot.instance=2;planner.Calculate();assert(planner.breath==0);bot.instance=1;
 // Add rescue must outrank retention (and a DPS mark), with CC/order gates intact.
 Unit second=whelp;second.guid=6;second.victim=&healer;second.x=12;a.units[6]=&second;a.possible={4,6};a.raw={3,4,6};bot.tank=true;whelp.victim=&bot;a.current=4;a.marked=4;
 OnyxiaAddsAction adds{&a,&bot};assert(adds.GetTarget()==&second);second.cc=true;assert(adds.GetTarget()==&whelp);second.cc=false;
 a.ordered=3;assert(!adds.GetTarget());a.ordered=0;boss.victim=&bot;assert(!adds.GetTarget());boss.victim=nullptr;
 a.marked=0;bot.tank=false;assert(!adds.GetTarget());boss.levitate=true;assert(adds.GetTarget()==&whelp);
 a.healer=true;assert(!adds.GetTarget());a.healer=false;
 std::cout<<"PASS: Onyxia native footprints/all8 chains, raw discovery, joint safety, path refusal, projectile/reset, cached dispatch and tank rescue\n";
}
'''
data = json.loads((root / 'tests/onyxia_native_breath_fixture.json').read_text())
for era, macro in (('classic', 'ZERO'), ('tbc', 'ONE'), ('wotlk', 'TWO')):
    rows = data[era]['rows']
    native = '\n'.join('Native(%s);' % ','.join(str(x) + ('f' if isinstance(x, float) else '') for x in row) for row in rows)
    chains = '\n'.join('{std::vector<encounter::Circle> t;assert(OnyxiaBreathThreats(%s,t)&&t.size()==%s);}' % pair for pair in data[era]['counts'].items())
    source = code.replace('__GEOMETRY__', (root / 'playerbot/strategy/EncounterGeometry.h').as_posix()).replace('__METHODS__', methods).replace('__DATA__', native).replace('__CHAINS__', chains)
    with tempfile.TemporaryDirectory(prefix='mantech-onyxia-native-') as folder:
        folder = Path(folder)
        (folder / 'test.cpp').write_text(source)
        subprocess.run(['cl', '/nologo', '/std:c++17', '/EHsc', '/DMANGOSBOT_' + macro, 'test.cpp', '/Fe:test.exe'], cwd=folder, check=True)
        subprocess.run([str(folder / 'test.exe')], check=True)
