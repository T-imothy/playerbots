"""Exercise production PvP decision bodies against controlled native interfaces.

Run from an MSVC developer shell. Temporary harness builds are removed on exit;
this does not start a realm or change a database.
"""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block

ROOT = Path(__file__).resolve().parents[1]
def source(name): return (ROOT / 'playerbot/strategy' / name).read_text(encoding='utf-8-sig')
def run(code, label, era):
    with tempfile.TemporaryDirectory(prefix='pvp-wsg-') as td:
        path=Path(td);(path/'test.cpp').write_text(code,encoding='utf-8')
        result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}',
            '/I'+str(ROOT),'test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
        if result.returncode: raise RuntimeError(label+' '+era+'\n'+result.stdout+result.stderr)
        subprocess.run([str(path/'test.exe')],cwd=path,check=True)
    print('PASS',era,label,flush=True)

COMMON=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <map>
#include <memory>
#include <string>
#include <vector>
#include <list>
#include <type_traits>
#include "playerbot/strategy/values/WarsongPolicy.h"
using uint8=uint8_t;using uint32=uint32_t;using int32=int32_t;
enum Team{ALLIANCE,HORDE};
enum BattleGroundTypeId{BATTLEGROUND_TYPE_NONE,BATTLEGROUND_WS,BATTLEGROUND_EY,BATTLEGROUND_AB,BATTLEGROUND_RB};
enum{STATUS_WAIT_JOIN,STATUS_IN_PROGRESS,STATUS_WAIT_LEAVE,TEAM_INDEX_ALLIANCE=0,TEAM_INDEX_HORDE=1,
 DIST_CALC_NONE=0,POWER_MANA=0,BG_WS_FLAG_STATE_ON_BASE=0,BG_WS_FLAG_STATE_ON_PLAYER=1,BG_WS_FLAG_STATE_ON_GROUND=-1};
int GetTeamIndexByTeamId(Team t){return int(t);}
struct ObjectGuid{uint32 id=0;ObjectGuid(uint32 id=0):id(id){}bool IsEmpty()const{return !id;}
 bool operator<(ObjectGuid b)const{return id<b.id;}bool operator==(ObjectGuid b)const{return id==b.id;}
 bool operator!=(ObjectGuid b)const{return id!=b.id;}};
struct Unit;struct Player;struct PlayerbotAI;struct BattleGround;
struct Position{float x,y,z,o;};
namespace ai{
struct PositionEntry{float x=0,y=0,z=0;uint32 mapId=0;bool valueSet=false;
 void Set(float a,float b,float c,uint32 m){x=a;y=b;z=c;mapId=m;valueSet=true;}bool isSet(){return valueSet;}};
using PositionMap=std::map<std::string,PositionEntry>;
}
struct Unit{ObjectGuid guid;float x=0,y=0,z=0,health=100;uint32 map=489;bool alive=true,world=true,combat=false,teleport=false,casting=false,los=true;
 Unit* victim=nullptr;ObjectGuid selection;virtual ~Unit(){};virtual bool IsPlayer(){return false;}
 bool IsWithinLOSInMap(Unit* u){return u && los && u->los;} bool IsNonMeleeSpellCasted(bool){return casting;}
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 bool IsBeingTeleported(){return teleport;}bool IsInMap(Unit* u){return u&&map==u->map;}
 bool IsWithinDistInMap(Unit* u,float d){return IsInMap(u)&&GetDistance(u->x,u->y,u->z,0)<=d*d;}
 float GetDistance(float a,float b,float c,int){return (x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c);}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetHealthPercent(){return health;}uint32 GetMapId(){return map;}ObjectGuid GetObjectGuid(){return guid;}
 uint32 GetGUIDLow(){return guid.id;}Unit* GetVictim(){return victim;}ObjectGuid GetSelectionGuid(){return selection;}};
struct Player:Unit{Team team=ALLIANCE;PlayerbotAI* ai=nullptr;BattleGround* bg=nullptr;bool healer=false;uint32 maxMana=100;
 bool IsPlayer()override{return true;}Team GetTeam(){return team;}BattleGround* GetBattleGround(){return bg;}
 PlayerbotAI* GetPlayerbotAI(){return ai;}uint32 GetMaxPower(int){return maxMana;}};
struct GameObject:Unit{bool spawned=true;};
struct FakeMap{std::map<ObjectGuid,Player*> players;std::map<ObjectGuid,GameObject*> objects;
 Player* GetPlayer(ObjectGuid g){auto i=players.find(g);return i==players.end()?nullptr:i->second;}
 GameObject* GetGameObject(ObjectGuid g){auto i=objects.find(g);return i==objects.end()?nullptr:i->second;}};
struct BattleGroundPlayer{Team playerTeam;};
struct BattleGround{BattleGroundTypeId type=BATTLEGROUND_WS,actual=BATTLEGROUND_WS;int status=STATUS_IN_PROGRESS;FakeMap map;
 std::map<ObjectGuid,BattleGroundPlayer> players;virtual ~BattleGround(){};
 BattleGroundTypeId GetTypeId(bool random=false){return random?actual:type;}int GetStatus(){return status;}
 uint32 GetMapId(){return 489;}FakeMap* GetBgMap(){return &map;}auto& GetPlayers(){return players;}
 Team GetOtherTeam(Team t){return t==ALLIANCE?HORDE:ALLIANCE;}};
struct BattleGroundWS:BattleGround{ObjectGuid carriers[2],drops[2];int states[2]={0,0};
 ObjectGuid GetFlagCarrierGuid(int t){return carriers[t];}ObjectGuid GetDroppedFlagGuid(Team t){return drops[t];}
 int GetFlagState(Team t){return states[t];}};
struct BattleGroundEY:BattleGround{ObjectGuid carrier;ObjectGuid GetFlagCarrierGuid(){return carrier;}};
struct ValueBase{virtual ~ValueBase(){}};
template<class T>struct Value:ValueBase{std::remove_reference_t<T> value{};T Get(){return value;}void Set(T v){value=v;}};
struct AiObjectContext{std::map<std::string,std::unique_ptr<ValueBase>> values;
 template<class T>Value<T>* GetValue(std::string k){auto& p=values[k];if(!p)p=std::make_unique<Value<T>>();return static_cast<Value<T>*>(p.get());}};
struct PlayerbotAI{Player* bot;AiObjectContext context;bool real=false,master=false,canMove=true;
 Player* GetBot(){return bot;}AiObjectContext* GetAiObjectContext(){return &context;}bool IsHeal(Player* p){return p->healer;}
 Unit* GetUnit(ObjectGuid g){return bot->bg->map.GetPlayer(g);}
 bool IsRealPlayer(){return real;}bool HasRealPlayerMaster(){return master;}bool CanMove(){return canMove;}};
enum {MAX_EFFECT_INDEX=3,SPELL_EFFECT_INTERRUPT_CAST=1,SPELL_AURA_MOD_DECREASE_SPEED=2,
 SPELL_AURA_MOD_ROOT,SPELL_AURA_MOD_STUN,SPELL_AURA_MOD_FEAR,SPELL_AURA_MOD_CONFUSE,SPELL_AURA_MOD_SILENCE};
struct SpellEntry{bool positive=false,channel=false,interrupt=false;uint32 time=0;int EffectApplyAuraName[3]={};};
SpellEntry testSpell;
bool IsPositiveSpell(const SpellEntry* s,Unit*,Unit*){return s->positive;}
bool IsSpellHaveEffect(const SpellEntry* s,int){return s->interrupt;}
uint32 GetSpellCastTime(const SpellEntry* s,Player*){return s->time;}
bool IsChanneledSpell(const SpellEntry* s){return s->channel;}
struct Facade{const SpellEntry* LookupSpellInfo(uint32){return &testSpell;}
 float GetDistance2d(Unit* a,Unit* b){return std::sqrt(a->GetDistance(b->x,b->y,a->z,0));}
 bool friendly=false;bool IsFriendlyTo(Unit*,Unit*){return friendly;}bool isSpawned(GameObject* g){return g->spawned;}}sServerFacade;
struct Config{float lowHealth=40;}sPlayerbotAIConfig;
namespace WorldTimer{uint32 now=10000;uint32 getMSTime(){return now;}}
uint32 urand(uint32 a,uint32){return a;}float frand(float a,float b){return (a+b)*.5f;}
#define AI_VALUE(T,K) context->GetValue<T>(K)->Get()
#define AI_VALUE2(T,K,Q) context->GetValue<T>(std::string(K)+"::"+Q)->Get()
using namespace ai;
'''

def wsg_code():
    values=source('values/PvpValues.cpp'); tactics=source('actions/BattleGroundTactics.cpp')
    objective=block(source('values/PvpValues.h'),'    struct WarsongObjective')+';'
    declarations=r'''
namespace ai{
BattleGroundTypeId ActualBattlegroundType(Player*);
bool IsBattlegroundFlagCarrier(Player*);bool ShouldAdvanceWarsongObjective(PlayerbotAI*);
bool IsWarsongLocalThreat(PlayerbotAI*,Unit*,Unit*);Unit* SelectWarsongCombatTarget(PlayerbotAI*);
struct WarsongObjectiveValue{PlayerbotAI* ai;Player* bot;WarsongObjective Calculate();};
}
struct AttackEnemyFlagCarrierAction{Player* bot;AiObjectContext* context;PlayerbotAI* ai;bool isUseful();};
struct BGTactics{PlayerbotAI* ai;Player* bot;AiObjectContext* context;uint32 warsongRetryUntil=0;
 std::string name="move to objective";bool moved=true;int requests=0;Position last{};
 std::string getName(){return name;}bool MoveTo(uint32,float x,float y,float z,bool=false,bool=false,bool=false){++requests;last={x,y,z,0};return moved;}
 bool refreshWarsongObjective();bool isUseful();bool flagTaken();bool teamFlagTaken();bool wsgPaths();bool wsgRoofJump();};
enum{ACTION_INTERRUPT=40};
struct Action{std::string name;float relevance=20;Unit* target=nullptr;virtual ~Action(){}
 std::string getName(){return name;}float getRelevance(){return relevance;}Unit* GetTarget(){return target;}};
struct AttackAction:Action{};
struct CastSpellAction:Action{bool movement=false;uint32 GetDecisionSpellId(){return 1;}bool HasMovementEffect(){return movement;}};
struct JumpAction:Action{std::string qualifier;std::string getQualifier(){return qualifier;}};
struct Multiplier{PlayerbotAI* ai;Player* bot;AiObjectContext* context;
 Multiplier(PlayerbotAI* a,std::string):ai(a),bot(a->bot),context(&a->context){}virtual float GetValue(Action*){return 1;}};
'''
    constants='\n'.join(l for l in tactics.splitlines() if l.startswith('Position const WS_') or l.startswith('std::vector<Position> const WS_'))
    methods='\n'.join(block(values,m) for m in ('BattleGroundTypeId ai::ActualBattlegroundType','bool ai::IsBattlegroundFlagCarrier',
        'bool ai::IsWarsongLocalThreat','Unit* ai::SelectWarsongCombatTarget','WarsongObjective WarsongObjectiveValue::Calculate','bool ai::ShouldAdvanceWarsongObjective'))
    methods+='\n'+block(source('actions/ChooseTargetActions.cpp'),'bool AttackEnemyFlagCarrierAction::isUseful')
    methods+='\n'+'\n'.join(block(tactics,'bool BGTactics::'+m) for m in ('refreshWarsongObjective()','isUseful()','flagTaken()','teamFlagTaken()','wsgPaths()','wsgRoofJump()'))
    methods+='\n'+block(source('generic/BattlegroundStrategy.cpp'),'    class WarsongObjectiveMultiplier')+';\n'
    cases=r'''
int main(){
 using F=WarsongFlagState;using G=WarsongGoal;
 // Native state permutations: split recovery, retain a carrier's return task.
 assert(SelectWarsongGoal(F::Base,F::Base,false,true,false)==G::Fetch);
 assert(SelectWarsongGoal(F::Dropped,F::Dropped,false,true,false)==G::Return);
 assert(SelectWarsongGoal(F::Dropped,F::Dropped,false,false,false)==G::Recover);
 assert(SelectWarsongGoal(F::Carried,F::Carried,false,true,false)==G::Escort);
 assert(SelectWarsongGoal(F::Carried,F::Carried,false,false,false)==G::Intercept);
 assert(SelectWarsongGoal(F::Carried,F::Base,false,true,true)==G::Intercept);
 assert(SelectWarsongGoal(F::Dropped,F::Carried,true,false,false)==G::Hold);
 assert(SelectWarsongGoal(F::Base,F::Carried,true,false,false)==G::Capture);
 for(Team team:{ALLIANCE,HORDE}){
  BattleGroundWS bg;Player bot,other,friendFC,enemyFC;
  bot.guid=1;other.guid=2;friendFC.guid=3;enemyFC.guid=4;
  bot.team=other.team=friendFC.team=team;enemyFC.team=bg.GetOtherTeam(team);bot.healer=true;
  PlayerbotAI a{&bot},b{&other};bot.ai=&a;other.ai=&b;
  for(Player* p:{&bot,&other,&friendFC,&enemyFC}){p->bg=&bg;bg.players[p->guid]={p->team};bg.map.players[p->guid]=p;}
  const int own=team,enemy=bg.GetOtherTeam(team);
  WarsongObjectiveValue v{&a,&bot},otherV{&b,&other};auto* context=&a.context;
  BGTactics action{&a,&bot,context};
  auto sample=[&](){auto o=v.Calculate();context->GetValue<WarsongObjective>("warsong objective")->Set(o);action.refreshWarsongObjective();return o;};
  assert(sample().goal==G::Fetch);
  auto pos=context->GetValue<PositionMap&>("position")->Get()["bg objective"];
  assert(pos.x==(team==ALLIANCE?WS_FLAG_POS_HORDE.x:WS_FLAG_POS_ALLIANCE.x));
  bg.states[own]=1;bg.carriers[own]=enemyFC.guid;enemyFC.x=1200;
  assert(sample().goal==G::Fetch);assert(otherV.Calculate().goal==G::Intercept);
  bg.states[enemy]=1;bg.carriers[enemy]=friendFC.guid;friendFC.x=1300;
  assert(sample().goal==G::Escort);assert(otherV.Calculate().goal==G::Intercept);
  friendFC.x=1350;assert(sample().position.x==1350); // moving target refresh
  other.alive=false;assert(sample().goal==G::Escort);other.alive=true; // stable jobs across deaths
  GameObject ownDrop,enemyDrop;ownDrop.guid=10;enemyDrop.guid=11;ownDrop.x=1111;enemyDrop.x=1222;
  bg.map.objects[10]=&ownDrop;bg.map.objects[11]=&enemyDrop;bg.drops[own]=10;bg.drops[enemy]=11;
  bg.states[own]=bg.states[enemy]=-1;bg.carriers[own]=bg.carriers[enemy]=0;
  assert(sample().goal==G::Return&&sample().position.x==1111);
  assert(otherV.Calculate().goal==G::Recover&&otherV.Calculate().position.x==1222);
  bg.map.objects.erase(10);assert(sample().goal==G::None);
  assert(!context->GetValue<PositionMap&>("position")->Get()["bg objective"].isSet());
  bg.map.objects[10]=&ownDrop;
  bg.states[enemy]=1;bg.carriers[enemy]=bot.guid;assert(sample().goal==G::Hold);
  auto hold=context->GetValue<PositionMap&>("position")->Get()["bg objective"];
  sample();assert(context->GetValue<PositionMap&>("position")->Get()["bg objective"].x==hold.x);
  bg.states[own]=0;assert(sample().goal==G::Capture);
  assert(context->GetValue<PositionMap&>("position")->Get()["bg objective"].x==(team==ALLIANCE?WS_FLAG_POS_ALLIANCE.x:WS_FLAG_POS_HORDE.x));
  assert(IsBattlegroundFlagCarrier(&bot));
  bg.type=BATTLEGROUND_AB;assert(!action.flagTaken()&&!action.teamFlagTaken());assert(!IsBattlegroundFlagCarrier(&bot));assert(v.Calculate().goal==G::None);
#ifdef MANGOSBOT_TWO
  bg.type=BATTLEGROUND_RB;bg.actual=BATTLEGROUND_WS;assert(IsBattlegroundFlagCarrier(&bot));assert(v.Calculate().goal==G::Capture);
#endif
  bg.type=BATTLEGROUND_WS;bg.states[enemy]=0;bg.carriers[enemy]=0;bg.states[own]=1;bg.carriers[own]=enemyFC.guid;
  enemyFC.x=bot.x+30;context->GetValue<Unit*>("enemy flag carrier")->Set(&enemyFC);
  context->GetValue<std::list<ObjectGuid>>("enemy player targets")->Set({enemyFC.guid});
  context->GetValue<Unit*>("enemy player target")->Set(&enemyFC);
  AttackEnemyFlagCarrierAction attack{&bot,context,&a};assert(attack.isUseful());
  context->GetValue<Unit*>("current target")->Set(&enemyFC);assert(!attack.isUseful());context->GetValue<Unit*>("current target")->Set(nullptr);
  enemyFC.alive=false;assert(!attack.isUseful());enemyFC.alive=true;
  bg.carriers[enemy]=bot.guid;assert(!attack.isUseful());bg.carriers[enemy]=0;
  enemyFC.map=1;assert(!attack.isUseful());enemyFC.map=489;
  enemyFC.x=1000;assert(!attack.isUseful());enemyFC.x=100;
  // Tactical movement yields to pressure, low health and player control.
  bg.states[own]=bg.states[enemy]=0;bg.carriers[own]=0;sample();assert(ShouldAdvanceWarsongObjective(&a));
  WarsongObjectiveMultiplier multiplier(&a);Action combat;combat.name="attack enemy player";combat.target=&enemyFC;
  assert(multiplier.GetValue(&combat)==0);combat.name="flash heal";assert(multiplier.GetValue(&combat)==1);
  combat.name="sprint";combat.relevance=20;assert(multiplier.GetValue(&combat)==2);
  combat.relevance=90;assert(multiplier.GetValue(&combat)==1); // never demote an emergency
  combat.name="health potion";assert(multiplier.GetValue(&combat)==1);
  bot.health=20;assert(!ShouldAdvanceWarsongObjective(&a));bot.health=100;
  a.master=true;assert(!ShouldAdvanceWarsongObjective(&a));a.master=false;
  enemyFC.x=bot.x+10;enemyFC.combat=true;enemyFC.selection=bot.guid;enemyFC.casting=true;
  assert(sample().pressured);assert(!ShouldAdvanceWarsongObjective(&a));
  combat.name="attack enemy player";assert(multiplier.GetValue(&combat)==1); // self-defense restored
  bot.combat=true;assert(!action.isUseful());bot.combat=false;enemyFC.combat=false;sample();
  context->GetValue<uint8>("mana::self target")->Set(100);assert(action.isUseful());
  a.canMove=false;assert(!action.isUseful());a.canMove=true;
  action.warsongRetryUntil=WorldTimer::now+1000;assert(!action.isUseful());action.warsongRetryUntil=0;
  pos=context->GetValue<PositionMap&>("position")->Get()["bg objective"];bot.x=pos.x;bot.y=pos.y;bot.z=pos.z;
  assert(!action.isUseful());assert(!ShouldAdvanceWarsongObjective(&a));
  JumpAction jump;jump.qualifier="position bg objective";assert(multiplier.GetValue(&jump)==0);
  jump.qualifier="random";assert(multiplier.GetValue(&jump)==1);
  bg.status=STATUS_WAIT_LEAVE;assert(v.Calculate().goal==G::None);bg.status=STATUS_IN_PROGRESS;
  bot.alive=false;assert(v.Calculate().goal==G::None);bot.alive=true;
 }
 // Objective-specific threat recognition and carrier pursuit protection.
 for(Team team:{ALLIANCE,HORDE}){
  BattleGroundWS bg;Player bot,carrier,enemy,farEnemy;PlayerbotAI a{&bot};bot.ai=&a;bot.healer=true;
  bot.guid=1;carrier.guid=2;enemy.guid=3;farEnemy.guid=4;
  bot.team=carrier.team=team;enemy.team=farEnemy.team=bg.GetOtherTeam(team);
  bot.x=100;carrier.x=125;enemy.x=120;farEnemy.x=139;farEnemy.health=1;
  for(Player* p:{&bot,&carrier,&enemy,&farEnemy}){p->bg=&bg;bg.players[p->guid]={p->team};bg.map.players[p->guid]=p;}
  auto* context=&a.context;context->GetValue<std::list<ObjectGuid>>("enemy player targets")->Set({enemy.guid,farEnemy.guid});
  bg.states[bg.GetOtherTeam(team)]=1;bg.carriers[bg.GetOtherTeam(team)]=carrier.guid;
  WarsongObjectiveValue value{&a,&bot};enemy.combat=true;enemy.victim=&carrier;
  assert(value.Calculate().pressured); // defend carrier, not just self
  assert(SelectWarsongCombatTarget(&a)==&enemy); // local threat beats distant 1-HP opponent
  enemy.victim=nullptr;enemy.selection=carrier.guid;
  assert(!value.Calculate().pressured); // selection alone does not claim an attack
  enemy.casting=true;assert(value.Calculate().pressured);
  enemy.los=false;assert(!value.Calculate().pressured);enemy.los=true;
  carrier.x=150;assert(!value.Calculate().pressured);carrier.x=125;
  bg.states[team]=1;bg.carriers[team]=farEnemy.guid;
  assert(SelectWarsongCombatTarget(&a)==&farEnemy); // eligible enemy carrier wins
  context->GetValue<std::list<ObjectGuid>>("enemy player targets")->Set({enemy.guid});
  assert(SelectWarsongCombatTarget(&a)==&enemy); // never inject excluded carrier
  bg.carriers[bg.GetOtherTeam(team)]=bot.guid;bg.carriers[team]=0;bg.states[team]=0;
  auto objective=value.Calculate();context->GetValue<WarsongObjective>("warsong objective")->Set(objective);
  BGTactics move{&a,&bot,context};move.refreshWarsongObjective();
  WarsongObjectiveMultiplier multiplier(&a);JumpAction chase;chase.qualifier="chase";
  assert(multiplier.GetValue(&chase)==0);AttackAction attack;attack.target=&enemy;assert(multiplier.GetValue(&attack)==0);
  Action reach;reach.name="reach melee";assert(multiplier.GetValue(&reach)==0);
  reach.name="reach party member to heal";assert(multiplier.GetValue(&reach)==1);
  CastSpellAction cast;cast.target=&enemy;testSpell={};assert(multiplier.GetValue(&cast)==0); // damage
  testSpell.positive=true;cast.target=&bot;assert(multiplier.GetValue(&cast)==1); // heal/buff
  testSpell={};testSpell.EffectApplyAuraName[0]=SPELL_AURA_MOD_ROOT;cast.target=&enemy;
  enemy.victim=&bot;assert(multiplier.GetValue(&cast)==2); // instant defensive root above travel
  testSpell.time=1500;assert(multiplier.GetValue(&cast)==0);testSpell.time=0;
  cast.movement=true;assert(multiplier.GetValue(&cast)==0);cast.movement=false;
  enemy.victim=&carrier;enemy.casting=false;assert(multiplier.GetValue(&cast)==0); // no remote control detour
  a.master=true;assert(multiplier.GetValue(&chase)==1);a.master=false;
  bg.type=BATTLEGROUND_AB;assert(multiplier.GetValue(&chase)==1);assert(multiplier.GetValue(&cast)==1);
  assert(!SelectWarsongCombatTarget(&a));bg.type=BATTLEGROUND_WS;
  // Carrier route uses same existing exit for every stored preference.
  auto& pos=context->GetValue<PositionMap&>("position")->Get()["bg objective"];
  pos.Set(team==ALLIANCE?1540.f:916.f,1450,350,489);
  bot.x=team==ALLIANCE?940.f:1515.f;bot.y=1450;bot.z=350;
  Position expected{};
  for(uint32 role=0;role<10;++role){context->GetValue<uint32>("bg role")->Set(role);assert(move.wsgPaths());
   if(!role)expected=move.last;assert(move.last.x==expected.x&&move.last.y==expected.y&&move.last.z==expected.z);
   assert(context->GetValue<uint32>("bg role")->Get()==role);}
 }
 // Actual route bodies must propagate failure, and Alliance descent uses the lower point.
 BattleGroundWS bg;Player bot;PlayerbotAI a{&bot};bot.bg=&bg;bot.ai=&a;auto* context=&a.context;BGTactics move{&a,&bot,context};
 for(uint32 role=0;role<10;++role) for(float x:{920.f,1000.f,1150.f,1300.f,1400.f,1530.f}) for(bool east:{false,true}){
  context->GetValue<uint32>("bg role")->Set(role);auto& pos=context->GetValue<PositionMap&>("position")->Get()["bg objective"];
  pos.Set(east?1540.f:916.f,1450,350,489);bot.x=x;bot.y=1450;bot.z=345;move.requests=0;move.moved=false;
  assert(!move.wsgPaths());assert(move.requests>0);move.moved=true;assert(move.wsgPaths());
 }
 bot.x=1529;bot.y=1468;bot.z=362;bot.combat=false;move.moved=true;
 assert(move.wsgRoofJump());assert(move.last.z==WS_FLAG_ALLIANCE_FLOOR_JUMP_LOWER.z);
 bot.x=1523;bot.y=1460;assert(move.wsgRoofJump());assert(move.last.z==WS_FLAG_ALLIANCE_FLOOR_JUMP_UPPER.z);
 move.moved=false;assert(!move.wsgRoofJump());
}
'''
    return COMMON+'\nnamespace ai{\n'+objective+'\n}\n'+declarations+constants+methods+cases

if __name__=='__main__':
    for era in ('ZERO','ONE','TWO'):run(wsg_code(),'WSG states, team jobs, transitions, pursuit, route results and exits',era)
