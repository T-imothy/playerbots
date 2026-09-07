"""Actual native wave/target-mask interpretation, floor planning and fresh dispatch."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
value=(root/'playerbot/strategy/values/HeiganPositionValue.cpp').read_text()
action=(root/'playerbot/strategy/actions/HeiganDanceAction.cpp').read_text()
methods='\n'.join(block(value,s) for s in ('uint32 ai::HeiganNextWave(', 'bool ai::HeiganCloudSafe(', 'uint32 ai::HeiganUpcomingWave(', 'namespace\n', 'bool ai::HeiganFloorThreats(', 'EncounterPosition HeiganPositionValue::Calculate('))
methods+='\n'+'\n'.join(block(action,'bool HeiganDanceAction::'+s+'(') for s in ('GetPlan','isUseful','ShouldReactionInterruptCast','Execute'))
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
struct Player:Unit{bool teleport=false,group=true,stopped=true;Motion motion;
 bool IsBeingTeleported(){return teleport;}bool GetGroup(){return group;}unsigned GetInstanceId(){return instance;}
 bool IsInMap(Unit*u){return u&&world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}
 bool IsStopped(){return stopped;}Motion*GetMotionMaster(){return &motion;}
};
namespace ai{struct EncounterPosition{bool active=false;unsigned map=0,instance=0,spell=0,boss=0,source=0;encounter::Point destination;};}
using namespace ai;
template<class T>struct Value{T data;bool dirty=false;unsigned resets=0;std::function<T()>calculate;T Get(){if(dirty){dirty=false;data=calculate();}return data;}void Reset(){++resets;dirty=true;}};
struct Context{Value<EncounterPosition>position;template<class T>Value<T>*GetValue(const char*){return &position;}};
struct PlayerbotAI{Player*bot;Context context;bool real=false,canMove=true,path=true;unsigned paths=0,moves=0,stops=0;std::map<unsigned,Unit*>units;std::list<ObjectGuid>attackers;
 Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool CanMove(){return canMove;}Context*GetAiObjectContext(){return &context;}
 Unit*GetUnit(unsigned id){auto i=units.find(id);return i==units.end()?nullptr:i->second;}void StopMoving(){++stops;bot->stopped=true;bot->motion.type=0;}
};
bool ValidateEncounterDestination(PlayerbotAI*ai,EncounterPosition&p){++ai->paths;return ai->path&&ai->bot->GetDistance(p.destination.x,p.destination.y,p.destination.z)<=60;}
float NativeEncounterSpellRadius(unsigned id){assert(id==29371||id==30122);return id==29371?6:20;}
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
namespace ai{
 uint32 HeiganNextWave(Unit*);uint32 HeiganUpcomingWave(Unit*,Unit*);bool HeiganCloudSafe(Player*,Unit*,const encounter::Point&);
 bool HeiganFloorThreats(PlayerbotAI*,const EncounterPosition&,std::vector<encounter::Circle>&,std::vector<encounter::Point>&);
 struct HeiganPositionValue{PlayerbotAI*ai;Player*bot;EncounterPosition Calculate();};
 struct HeiganDanceAction{PlayerbotAI*ai;Player*bot;static bool GetPlan(PlayerbotAI*,EncounterPosition&);bool isUseful();bool ShouldReactionInterruptCast()const;bool Execute(Event&);
 bool IsReaction(){return false;}void SetDuration(unsigned){}bool MoveTo(unsigned,float,float,float,bool,bool,bool,bool){++ai->moves;return true;}};
}
#define AI_VALUE(type,key) ai->attackers
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
 auto p=calculate();assert(p.active&&p.destination.x==0&&action.ShouldReactionInterruptCast()&&action.Execute(event));
 bot.x=0;calculate();assert(action.isUseful()&&!action.ShouldReactionInterruptCast());assert(action.Execute(event)&&ai.stops==1&&!action.isUseful());
 wave.ticks=1;assert(action.isUseful()&&ai.context.position.resets==1&&ai.context.position.data.destination.x==20);
 assert(action.isUseful()&&ai.context.position.resets==1); // no repeated grid/path reset at same wave
 ai.path=false;wave.ticks=2;assert(!action.Execute(event));ai.path=true;
 // Platform cloud starts before the fast controller. Route to the first safe band immediately.
 controller.slow=nullptr;boss.cloud=true;bot.x=-40;p=calculate();assert(p.active&&p.spell==30116&&p.destination.x==0&&!HeiganCloudSafe(&bot,&boss,{-40,0,0}));
 controller.fast=&wave;wave.ticks=0;assert(action.Execute(event));controller.slow=&wave;assert(!action.Execute(event));controller.slow=nullptr;
 wave.caster=99;assert(!calculate().active);wave.caster=2;
 controller.fast=nullptr;boss.cloud=false;assert(!calculate().active);controller.slow=&wave;
 bot.x=20;assert(calculate().active);sSpellScriptTargetStorage.rows[30116].push_back({0,100,6});assert(!action.Execute(event));sSpellScriptTargetStorage.rows[30116].pop_back();
 boss.combat=false;assert(!calculate().active);boss.combat=true;controller.phase=2;assert(!calculate().active);controller.phase=1;
 bot.teleport=true;assert(!calculate().active);bot.teleport=false;ai.real=true;assert(!calculate().active);ai.real=false;
 nativeFissures.clear();assert(!calculate().active);
 std::cout<<"PASS: native six-wave sequence/effect masks, actual floor anchors, immediate wave refresh, platform prelude and stale/lifecycle gates\n";
}
'''.replace('__GEOMETRY__',str(root/'playerbot/strategy/EncounterGeometry.h').replace('\\','/')).replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-dance-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
for era in ('classic','tbc','wotlk'):
    zone='northrend' if era=='wotlk' else 'eastern_kingdoms'
    core=root.parent/f'mangos-{era}-behavior'
    native=(core/f'src/game/AI/ScriptDevAI/scripts/{zone}/naxxramas/boss_heigan.cpp').read_text()
    assert '{ 30116, 30117, 30118, 30119, 30118, 30117 }' in native
    assert '(aura->GetAuraTicks() - 1) % 6' in native
