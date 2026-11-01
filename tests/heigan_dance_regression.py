"""Actual native wave/target-mask interpretation, floor planning and fresh dispatch."""
from pathlib import Path
from encounter_arrival_fixture import arrival_fixture
import os,subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
value=(root/'playerbot/strategy/values/HeiganPositionValue.cpp').read_text()
action=(root/'playerbot/strategy/actions/HeiganDanceAction.cpp').read_text()
methods='\n'.join(block(value,s) for s in ('uint32 ai::HeiganNextWave(', 'bool ai::HeiganManaBurnSafe(', 'bool ai::HeiganCloudSafe(', 'uint32 ai::HeiganUpcomingWave(', 'namespace\n', 'bool ai::HeiganFloorThreats(', 'float HeiganRoleSpellRange(', 'bool HeiganTankFloor(', 'bool HeiganCasterPlatform(', 'EncounterPosition HeiganPositionValue::Calculate('))
methods+='\n'+'\n'.join(block(action,'bool HeiganDanceAction::'+s+'(') for s in ('GetPlan','isUseful','ShouldReactionInterruptCast','ShouldReactionInterruptMovement','Execute'))
code=r'''
#include <cassert>
#include <functional>
#include <iostream>
#include <list>
#include <map>
#include <set>
#include <type_traits>
#include "__GEOMETRY__"
using uint32=unsigned;using ObjectGuid=unsigned;using SpellEffectIndex=unsigned;
enum{EFFECT_INDEX_0=0,MAX_EFFECT_INDEX=3,SPELL_EFFECT_ACTIVATE_OBJECT=86,SPELL_TARGET_TYPE_GAMEOBJECT=0,GAMEOBJECT_TYPE_TRAP=6,IDLE_MOTION_TYPE=0};
enum class GameObjectActions{DISTURB=5,OPEN=8};
struct Aura{unsigned caster=2,ticks=0;unsigned GetCasterGuid()const{return caster;}unsigned GetAuraTicks()const{return ticks;}};
struct Unit{unsigned guid=1,entry=15936,map=533,instance=1,phase=1;float x=0,y=0,z=0,reach=1.5f;bool world=true,alive=true,combat=true,charmed=false,cloud=false;Aura*slow=nullptr,*fast=nullptr;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 unsigned GetObjectGuid(){return guid;}unsigned GetEntry(){return entry;}unsigned GetMapId(){return map;}
 const Aura*GetAura(unsigned id,unsigned){return id==29351?slow:id==30114?fast:nullptr;}bool HasAura(unsigned id){return id==29350?cloud:GetAura(id,0)!=nullptr;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}float GetCombatReach(){return reach;}
 float GetDistance(Unit*u){return std::hypot(x-u->x,y-u->y);}float GetDistance(float a,float b,float c){return std::sqrt((a-x)*(a-x)+(b-y)*(b-y)+(c-z)*(c-z));}
};
struct GOInfo{struct{unsigned spellId=29371;}trap;};
struct GameObject:Unit{GOInfo info;bool spawned=true;bool IsSpawned(){return spawned;}unsigned GetGoType(){return GAMEOBJECT_TYPE_TRAP;}GOInfo*GetGOInfo(){return &info;}};
struct Motion{unsigned type=1;unsigned GetCurrentMovementGeneratorType(){return type;}};
enum{CLASS_WARRIOR=1,CLASS_PALADIN=2,CLASS_HUNTER=3,CLASS_ROGUE=4,CLASS_PRIEST=5,CLASS_SHAMAN=7,CLASS_MAGE=8,CLASS_WARLOCK=9,CLASS_DRUID=11};
struct Player:Unit{unsigned cls=CLASS_MAGE;unsigned getClass(){return cls;}bool teleport=false,group=true,stopped=true;Motion motion;
 bool IsBeingTeleported(){return teleport;}bool GetGroup(){return group;}unsigned GetInstanceId(){return instance;}
 bool IsInMap(Unit*u){return u&&world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}
 bool IsStopped(){return stopped;}Motion*GetMotionMaster(){return &motion;}
};
namespace ai{struct EncounterPosition{bool active=false;unsigned map=0,instance=0,spell=0,boss=0,source=0;encounter::Point destination;};}
using namespace ai;
template<class T>struct Value{T data;bool dirty=false;unsigned resets=0;std::function<T()>calculate;T Get(){if(dirty){dirty=false;data=calculate();}return data;}void Reset(){++resets;dirty=true;}};
struct Context{Value<EncounterPosition>position;template<class T>Value<T>*GetValue(const char*){return &position;}};
struct PlayerbotAI{Player*bot;Context context;bool real=false,canMove=true,path=true;unsigned paths=0,moves=0,stops=0;std::map<unsigned,Unit*>units;std::list<ObjectGuid>attackers;
 bool healer=false,ranged=false,tank=false;float range=40,spellRange=40;std::string rangeSpell;bool IsHeal(Player*){return healer;}bool IsRanged(Player*){return ranged;}bool IsTank(Player*){return tank;}float GetRange(const char*){return range;}
 bool GetSpellRange(const char*name,float*out){rangeSpell=name;*out=spellRange;return true;}
 Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool CanMove(){return canMove;}Context*GetAiObjectContext(){return &context;}
 Unit*GetUnit(unsigned id){auto i=units.find(id);return i==units.end()?nullptr:i->second;}void StopMoving(){++stops;bot->stopped=true;bot->motion.type=0;}
};
bool ValidateEncounterDestination(PlayerbotAI*ai,EncounterPosition&p){++ai->paths;return ai->path&&ai->bot->GetDistance(p.destination.x,p.destination.y,p.destination.z)<=60;}
float NativeEncounterSpellRadius(unsigned id){assert(id==29371||id==30122||id==29310);return id==29371?6:id==29310?25:20;}
struct SpellTargetPosition{unsigned target_mapId=533;float target_X=30,target_Y=0,target_Z=0;};
struct SpellMgr{SpellTargetPosition position;bool available=true;const SpellTargetPosition*GetSpellTargetPosition(unsigned id){assert(id==30211);return available?&position:nullptr;}}sSpellMgr;
struct SpellEntry{unsigned Effect[3]={86,86,86};unsigned EffectMiscValue[3]={5,5,5};};
struct SpellStore{SpellEntry spell;template<class T>const T*LookupEntry(unsigned){return &spell;}}sSpellTemplate;
struct SpellTargetEntry{unsigned type=0,targetEntry=0,mask=0;bool CanNotHitWithSpellEffect(unsigned effect)const{return mask&(1u<<effect);}};
struct TargetStorage{std::map<unsigned,std::vector<SpellTargetEntry>>rows;template<class T>auto getBounds(unsigned wave){auto&r=rows[wave];return std::make_pair(r.begin(),r.end());}}sSpellScriptTargetStorage;
std::list<Unit*>nativeControllers;std::list<GameObject*>nativeFissures;
namespace MaNGOS{
 struct AllCreaturesOfEntryInRangeCheck{AllCreaturesOfEntryInRangeCheck(Unit*,unsigned entry,float range){assert(entry==17293&&range==100);}};
 template<class T>struct UnitListSearcher{std::list<Unit*>&out;UnitListSearcher(std::list<Unit*>&o,T&):out(o){}};
 template<class T>struct GameObjectListSearcher{std::list<GameObject*>&out;T&check;GameObjectListSearcher(std::list<GameObject*>&o,T&c):out(o),check(c){}};
}
namespace Cell{
 template<class T>void VisitAllObjects(Unit*,MaNGOS::UnitListSearcher<T>&s,float){s.out=nativeControllers;}
 template<class T>void VisitAllObjects(Unit*,MaNGOS::GameObjectListSearcher<T>&s,float){for(auto*go:nativeFissures)if(s.check(go))s.out.push_back(go);}
}
struct Event{};
struct WorldPosition { unsigned map; float x,y,z; WorldPosition(unsigned m,float a,float b,float c):map(m),x(a),y(b),z(c){} };
struct MovementAction { static bool ShouldReactionInterruptMovement(){return true;} };
unsigned nativeMoves=0;
namespace ai{
 bool NaxxramasEncounterEngaged(Player*,Unit* u){return u&&u->combat;}
 uint32 HeiganNextWave(Unit*);uint32 HeiganUpcomingWave(Unit*,Unit*);bool HeiganCloudSafe(Player*,Unit*,const encounter::Point&);
 bool HeiganManaBurnSafe(PlayerbotAI*,Unit*,const encounter::Point&);
 bool HeiganFloorThreats(PlayerbotAI*,const EncounterPosition&,std::vector<encounter::Circle>&,std::vector<encounter::Point>&);
 struct HeiganPositionValue{PlayerbotAI*ai;Player*bot;EncounterPosition Calculate();};
 struct HeiganDanceAction{PlayerbotAI*ai;Player*bot;static bool GetPlan(PlayerbotAI*,EncounterPosition&);bool isUseful();bool ShouldReactionInterruptCast()const;bool ShouldReactionInterruptMovement()const;bool Execute(Event&);
 bool MoveBlackwingPath(const WorldPosition& p){assert(p.map==533);++nativeMoves;return ai->path;}
 bool IsReaction(){return false;}void SetDuration(unsigned){}bool MoveTo(unsigned,float,float,float,bool,bool,bool,bool){++ai->moves;return true;}};
}
#define AI_VALUE(type,key) ai->attackers
#define AI_VALUE2(type,key,qualifier) ai->attackers
__METHODS__
int main(){
 Player bot;bot.guid=10;bot.x=20;Unit boss,controller;boss.x=-40;controller.guid=2;controller.entry=17293;Aura wave;controller.slow=&wave;nativeControllers={&controller};
 GameObject floor[4];for(unsigned i=0;i<4;++i){floor[i].entry=100+i;floor[i].guid=100+i;floor[i].x=20.f*i;nativeFissures.push_back(&floor[i]);}
 for(unsigned w=0;w<4;++w)for(unsigned area=0;area<4;++area)if(area!=w)sSpellScriptTargetStorage.rows[30116+w].push_back({0,100+area,6});
 sSpellScriptTargetStorage.rows[30116].push_back({0,999,7});sSpellScriptTargetStorage.rows[30116].push_back({1,998,0});
 assert(HeiganFissureEntries(30116).size()==3);sSpellTemplate.spell.Effect[0]=0;assert(HeiganFissureEntries(30116).empty());sSpellTemplate.spell.Effect[0]=86;
 sSpellTemplate.spell.EffectMiscValue[0]=1;assert(HeiganFissureEntries(30116).empty());sSpellTemplate.spell.EffectMiscValue[0]=5;
 PlayerbotAI ai{&bot};ai.units={{1,&boss},{2,&controller}};ai.attackers={1};HeiganPositionValue planner{&ai,&bot};HeiganDanceAction action{&ai,&bot};Event event;
 ai.context.position.calculate=[&](){return planner.Calculate();};auto calculate=[&](){ai.paths=0;ai.context.position.data=planner.Calculate();return ai.context.position.data;};
 const unsigned expected[]={30116,30117,30118,30119,30118,30117,30116};for(unsigned i=0;i<7;++i){wave.ticks=i;assert(HeiganNextWave(&controller)==expected[i]);}wave.ticks=0;
 auto p=calculate();assert(p.active&&p.destination.x==0);
#ifdef MANGOSBOT_ZERO
 assert(!action.ShouldReactionInterruptCast()&&!action.ShouldReactionInterruptMovement());
 assert(action.Execute(event)&&nativeMoves==1&&ai.moves==0);
 // A repeated reaction must reach the native dispatcher with movement intact.
 assert(action.Execute(event)&&nativeMoves==2&&ai.moves==0);
 ai.path=false;assert(!action.Execute(event)&&nativeMoves==2);ai.path=true;
#else
 assert(action.ShouldReactionInterruptCast()&&action.ShouldReactionInterruptMovement());
 assert(action.Execute(event)&&nativeMoves==0&&ai.moves==1);
#endif
 bot.x=0;calculate();bot.movespline->done=false;bot.movespline->end={bot.x+10,bot.y,bot.z};assert(action.isUseful()&&!action.ShouldReactionInterruptCast());assert(action.Execute(event)&&ai.stops==1&&!action.isUseful());
 wave.ticks=1;assert(action.isUseful()&&ai.context.position.resets==1&&ai.context.position.data.destination.x==20);
 assert(action.isUseful()&&ai.context.position.resets==1); // no repeated grid/path reset at same wave
 ai.path=false;wave.ticks=2;assert(!action.Execute(event));ai.path=true;
 // Platform cloud starts before the fast controller. Route to the first safe band immediately.
 controller.slow=nullptr;boss.cloud=true;bot.x=-40;p=calculate();assert(p.active&&p.spell==30116&&p.destination.x==0&&!HeiganCloudSafe(&bot,&boss,{-40,0,0}));
 controller.fast=&wave;wave.ticks=0;assert(action.Execute(event));controller.slow=&wave;assert(!action.Execute(event));controller.slow=nullptr;
 wave.caster=99;assert(!calculate().active);wave.caster=2;
 controller.fast=nullptr;boss.cloud=false;
#ifdef MANGOSBOT_ZERO
 assert(calculate().active); // native five-second opening before slow controller starts
 boss.combat=false;assert(!HeiganUpcomingWave(&boss,&controller));boss.combat=true;
 boss.entry=15990;assert(!HeiganUpcomingWave(&boss,&controller));boss.entry=15936;
#else
 assert(!calculate().active);
#endif
 controller.slow=&wave;
 bot.x=20;assert(calculate().active);sSpellScriptTargetStorage.rows[30116].push_back({0,100,6});assert(!action.Execute(event));sSpellScriptTargetStorage.rows[30116].pop_back();
 boss.combat=false;assert(!calculate().active);boss.combat=true;controller.phase=2;assert(!calculate().active);controller.phase=1;
 bot.teleport=true;assert(!calculate().active);bot.teleport=false;ai.real=true;assert(!calculate().active);ai.real=false;
 nativeFissures.clear();assert(!calculate().active);
#ifdef MANGOSBOT_ZERO
 // Native Mana Burn radius is 25 yards (SpellRadius row20). A slow-wave
 // safe floor tile at the boss's feet is not safe for a caster/healer.
 for(auto&tile:floor)nativeFissures.push_back(&tile);
 boss.x=0;bot.x=0;ai.ranged=true;sSpellMgr.available=false;wave.ticks=0;
 p=calculate();assert(p.active&&HeiganManaBurnSafe(&ai,&boss,p.destination)); // escape need not end at a fissure centre
 ai.ranged=false;assert(calculate().active); // melee still uses the floor
 ai.healer=true;p=calculate();assert(p.active&&HeiganManaBurnSafe(&ai,&boss,p.destination));ai.healer=false;
 ai.ranged=true;ai.tank=true;assert(calculate().active);ai.tank=false;
 // The tank can invalidate a safe fissure centre with Mana Burn while
 // adjacent floor remains outside both hazards. Do not surrender movement.
 boss.x=28;bot.x=0;p=calculate();assert(p.active&&p.destination.x<0);
 std::vector<encounter::Circle> nativeThreats;std::vector<encounter::Point> nativeFloor;
 assert(HeiganFloorThreats(&ai,p,nativeThreats,nativeFloor));
 assert(encounter::OutsideCircles(p.destination,nativeThreats)&&HeiganManaBurnSafe(&ai,&boss,p.destination));
 ai.path=false;assert(!calculate().active);ai.path=true;boss.x=0;
 assert(!HeiganManaBurnSafe(&ai,&boss,{28,0,0}));assert(HeiganManaBurnSafe(&ai,&boss,{30,0,0}));
 ai.context.position.data={true,533,1,30116,1,2,{0,0,0}};ai.context.position.dirty=false;
 const auto before=ai.context.position.resets;EncounterPosition stale;
 assert(HeiganDanceAction::GetPlan(&ai,stale)&&ai.context.position.resets==before+1&&HeiganManaBurnSafe(&ai,&boss,stale.destination));
 nativeFissures.clear();sSpellMgr.available=true;
 boss.x=0;bot.x=30;boss.cloud=false;controller.slow=&wave;controller.fast=nullptr;ai.ranged=true;EncounterPosition station;
 assert(HeiganCasterPlatform(&ai,&boss,&controller,station,{}));assert(station.destination.x==30); // hold current safe platform cast station
 ai.range=26;assert(HeiganCasterPlatform(&ai,&boss,&controller,station,{}));ai.range=40; // recorded generic default must not replace native 40yd cast range
 for(unsigned cls:{CLASS_PRIEST,CLASS_DRUID,CLASS_SHAMAN,CLASS_PALADIN}){
  bot.cls=cls;ai.healer=true;ai.range=26;assert(HeiganCasterPlatform(&ai,&boss,&controller,station,{}));
  assert(ai.rangeSpell==(cls==CLASS_PRIEST?"flash heal":cls==CLASS_DRUID?"healing touch":cls==CLASS_SHAMAN?"healing wave":"flash of light"));
 }bot.cls=CLASS_MAGE;ai.healer=false;ai.range=40;
 ai.tank=true;assert(!HeiganCasterPlatform(&ai,&boss,&controller,station,{}));ai.tank=false;
 ai.ranged=false;assert(!HeiganCasterPlatform(&ai,&boss,&controller,station,{}));ai.healer=true;assert(HeiganCasterPlatform(&ai,&boss,&controller,station,{}));
 boss.cloud=true;assert(!HeiganCasterPlatform(&ai,&boss,&controller,station,{}));boss.cloud=false;
 controller.fast=&wave;assert(!HeiganCasterPlatform(&ai,&boss,&controller,station,{}));controller.fast=nullptr;
 controller.slow=nullptr;assert(HeiganCasterPlatform(&ai,&boss,&controller,station,{}));
 boss.combat=false;assert(!HeiganCasterPlatform(&ai,&boss,&controller,station,{}));boss.combat=true;controller.slow=&wave;
 boss.x=30;assert(!HeiganCasterPlatform(&ai,&boss,&controller,station,{}));boss.x=0; // platform isn't safe while boss remains on it
 ai.path=false;assert(!HeiganCasterPlatform(&ai,&boss,&controller,station,{}));ai.path=true;
 ai.range=12;ai.spellRange=12;assert(!HeiganCasterPlatform(&ai,&boss,&controller,station,{}));ai.range=40;ai.spellRange=40;
 sSpellMgr.available=false;assert(!HeiganCasterPlatform(&ai,&boss,&controller,station,{}));sSpellMgr.available=true;
 assert(!HeiganCasterPlatform(&ai,&boss,&controller,station,{{{30,0,0},10}})); // native eruption admission retained
 // Tank slow-phase stations must leave the native caster platform usable.
 ai.tank=true;ai.healer=false;ai.ranged=false;bot.x=0;bot.y=0;
 std::vector<encounter::Point> tankFloor{{-8,0,0}};
 assert(HeiganTankFloor(&ai,&boss,&controller,station,{},tankFloor));
 float platformDistance=encounter::Distance2d(station.destination,{30,0,0});
 assert(platformDistance>=34&&platformDistance<=43);
 bot.x=station.destination.x;bot.y=station.destination.y;
 assert(HeiganTankFloor(&ai,&boss,&controller,station,{},tankFloor));
 assert(station.destination.x==bot.x&&station.destination.y==bot.y); // no station churn
 ai.path=false;assert(!HeiganTankFloor(&ai,&boss,&controller,station,{},tankFloor));ai.path=true;
 assert(!HeiganTankFloor(&ai,&boss,&controller,station,{{{-8,0,0},30}},tankFloor));
 boss.cloud=true;assert(!HeiganTankFloor(&ai,&boss,&controller,station,{},tankFloor));boss.cloud=false;
 controller.fast=&wave;assert(!HeiganTankFloor(&ai,&boss,&controller,station,{},tankFloor));controller.fast=nullptr;
 ai.tank=false;assert(!HeiganTankFloor(&ai,&boss,&controller,station,{},tankFloor));ai.tank=true;
 sSpellMgr.available=false;assert(!HeiganTankFloor(&ai,&boss,&controller,station,{},tankFloor));sSpellMgr.available=true;
#else
 EncounterPosition unchanged;ai.tank=true;
 assert(!HeiganTankFloor(&ai,&boss,&controller,unchanged,{},{{0,0,0}}));
#endif
 std::cout<<"PASS: native six-wave sequence/effect masks, actual floor anchors, immediate wave refresh, platform prelude and stale/lifecycle gates\n";
}
'''.replace('__GEOMETRY__',str(root/'playerbot/strategy/EncounterGeometry.h').replace('\\','/')).replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-dance-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(arrival_fixture(code))
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
for era in os.environ.get('PLAYERBOT_TEST_NATIVE_ERAS','classic,tbc,wotlk').split(','):
    zone='northrend' if era=='wotlk' else 'eastern_kingdoms'
    core=root.parent/era
    native=(core/f'src/game/AI/ScriptDevAI/scripts/{zone}/naxxramas/boss_heigan.cpp').read_text()
    assert '{ 30116, 30117, 30118, 30119, 30118, 30117 }' in native
    assert '(aura->GetAuraTicks() - 1) % 6' in native
    print('PASS native wave contract:',era)
