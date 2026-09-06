"""Compile the actual cube planner/action in all eras with controlled native objects.

Tests bot policy and lifecycle, not live pathfinding or five-beam spell delivery.
The two core repositories separately execute the actual native GO-use handler.
"""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
value = (root/'playerbot/strategy/values/MagtheridonPositionValue.cpp').read_text()
action = (root/'playerbot/strategy/actions/MagtheridonCubeAction.cpp').read_text()
multiplier = (root/'playerbot/strategy/generic/DungeonMultipliers.cpp').read_text()
methods = '\n'.join(block(value, name) for name in (
    'bool ai::HasMagtheridonChannel(', 'bool ai::IsMagtheridonNova(',
    'bool ai::IsMagtheridonCubeUser(', 'bool ai::IsMagtheridonCube(',
    'Unit* ai::FindMagtheridonCubeTrigger(', 'EncounterPosition MagtheridonPositionValue::Calculate('))
methods += '\n' + '\n'.join(block(action, name) for name in (
    'Unit* MagtheridonCubeAction::GetBoss(', 'bool MagtheridonCubeAction::GetPlan(',
    'bool MagtheridonCubeAction::isUseful(', 'bool MagtheridonCubeAction::isPossible(',
    'bool MagtheridonCubeAction::ShouldReactionInterruptCast(', 'bool MagtheridonCubeAction::Execute('))
methods += '\n' + block(multiplier, 'float PreserveMagtheridonCubeMultiplier::GetValue(')
code = r'''
#include <cassert>
#include <iostream>
#include <map>
#include <list>
#include <set>
#include <string>
#include "__GEOMETRY__"
using uint32=unsigned;
enum {CURRENT_GENERIC_SPELL, CURRENT_CHANNELED_SPELL, SPELL_STATE_FINISHED=10,
 GAMEOBJECT_TYPE_GOOBER, GAMEOBJECT_FLAGS, GO_FLAG_NO_INTERACT=1, GO_FLAG_IN_USE=2,
 GO_JUST_DEACTIVATED=3, IDLE_MOTION_TYPE=0, CMSG_GAMEOBJ_USE=77};
enum class BotState{BOT_STATE_COMBAT};
struct ObjectGuid{unsigned id=0;ObjectGuid(unsigned v=0):id(v){}operator unsigned()const{return id;}};
struct Map{};
struct WorldObject {virtual ~WorldObject()=default;Map* map=nullptr;unsigned mapId=544,phase=1,entry=0;ObjectGuid guid;
 bool world=true;float x=0,y=0,z=0;
 bool IsInWorld()const{return world;}Map* GetMap()const{return map;}unsigned GetMapId()const{return mapId;}
 unsigned GetEntry()const{return entry;}ObjectGuid GetObjectGuid()const{return guid;}
 bool IsInMap(WorldObject* o)const{return o&&world&&o->world&&map==o->map&&phase==o->phase;}
 float GetPositionX()const{return x;}float GetPositionY()const{return y;}float GetPositionZ()const{return z;}
 float GetDistance(float xx,float yy,float zz)const{return std::sqrt((x-xx)*(x-xx)+(y-yy)*(y-yy)+(z-zz)*(z-zz));}
 float GetDistance(const WorldObject* o)const{return GetDistance(o->x,o->y,o->z);}
 float GetAngle(const WorldObject* o)const{return std::atan2(o->y-y,o->x-x);}};
struct SpellEntry{unsigned Id=0;};struct Spell{const SpellEntry* m_spellInfo=nullptr;unsigned state=0;unsigned getState()const{return state;}};
struct Unit:WorldObject{bool alive=true,combat=true,charmed=false;std::set<unsigned> auras;Unit* victim=nullptr;Spell* casts[2]={};
 bool IsAlive()const{return alive;}bool IsInCombat()const{return combat;}bool HasCharmer()const{return charmed;}
 bool HasAura(unsigned id)const{return auras.count(id);}Unit* GetVictim()const{return victim;}
 Spell* GetCurrentSpell(unsigned type)const{return casts[type];}};
struct WorldPacket{unsigned opcode;ObjectGuid guid;WorldPacket(unsigned v):opcode(v){}
 WorldPacket& operator<<(ObjectGuid v){guid=v;return *this;}};
struct Session{bool logout=false;unsigned clicks=0;ObjectGuid clicked;
 bool isLogingOut(){return logout;}void HandleGameObjectUseOpcode(WorldPacket& p){assert(p.opcode==CMSG_GAMEOBJ_USE);++clicks;clicked=p.guid;}};
struct Motion{unsigned type=0;unsigned GetCurrentMovementGeneratorType(){return type;}};
struct Group;struct PlayerbotAI;
struct Player:Unit{PlayerbotAI* ai=nullptr;Group* group=nullptr;unsigned instance=1;bool teleport=false,tank=false,healer=false,ranged=true,stopped=true,los=true;
 Session session;bool haveSession=true;Motion motion;unsigned cancelled=0;
 PlayerbotAI* GetPlayerbotAI(){return ai;}Group* GetGroup(){return group;}Session* GetSession(){return haveSession?&session:nullptr;}
 bool IsBeingTeleported(){return teleport;}unsigned GetInstanceId(){return instance;}
 bool IsStopped(){return stopped;}Motion* GetMotionMaster(){return &motion;}
 bool IsWithinLOSInMap(WorldObject* o){return IsInMap(o)&&los;}
 bool IsNonMeleeSpellCasted(bool){return casts[0]||casts[1];}
 void InterruptSpell(unsigned type){assert(type==CURRENT_CHANNELED_SPELL);casts[type]=nullptr;auras.erase(30410);++cancelled;}};
struct GameObject:WorldObject{unsigned flags=0,kind=GAMEOBJECT_TYPE_GOOBER,loot=0;float reach=5;bool spawned=true;
 unsigned GetGoType(){return kind;}bool IsSpawned(){return spawned;}bool HasFlag(unsigned,unsigned f){return(flags&f)!=0;}
 unsigned GetLootState(){return loot;}float GetInteractionDistance(){return reach;}
 bool IsAtInteractDistance(Player* p){return GetDistance(p)<=reach;}};
using GameObjectList=std::list<GameObject*>;
std::vector<Unit*> allUnits;std::vector<GameObject*> allObjects;
namespace MaNGOS {
 struct AllCreaturesOfEntryInRangeCheck{WorldObject* focus;unsigned entry;float range;
  AllCreaturesOfEntryInRangeCheck(WorldObject* f,unsigned e,float r):focus(f),entry(e),range(r){}
  bool operator()(Unit* u){return u&&u->GetEntry()==entry&&focus->IsInMap(u)&&focus->GetDistance(u)<=range;}};
 template<class C>struct UnitListSearcher{std::list<Unit*>& out;C& check;UnitListSearcher(std::list<Unit*>& o,C& c):out(o),check(c){}
  void run(){for(auto u:allUnits)if(check(u))out.push_back(u);}};
 template<class C>struct GameObjectListSearcher{GameObjectList& out;C& check;GameObjectListSearcher(GameObjectList& o,C& c):out(o),check(c){}
  void run(){for(auto o:allObjects)if(check(o))out.push_back(o);}};
}
namespace Cell{template<class T>void VisitAllObjects(WorldObject*,T& s,float){s.run();}
 template<class T>void VisitGridObjects(WorldObject*,T& s,float){s.run();}}
struct GroupReference{Player* source=nullptr;GroupReference* following=nullptr;Player* getSource(){return source;}GroupReference* next(){return following;}};
struct Group{GroupReference* first=nullptr;GroupReference* GetFirstMember(){return first;}};
namespace ai {struct EncounterPosition{bool active=false,exclusive=true;unsigned map=0,instance=0,spell=0;ObjectGuid boss,source;encounter::Point destination;};}
using namespace ai;
template<class T>struct Value{T value{};T Get(){return value;}};
struct Context{Value<EncounterPosition> position;template<class T>Value<T>* GetValue(const char*){return &position;}};
struct PlayerbotAI{Player* bot=nullptr;Context context;bool real=false,dungeon=true,canMove=true,path=true,adjustBad=false;unsigned moves=0,stops=0,interrupts=0,paths=0;
 Player* GetBot(){return bot;}Context* GetAiObjectContext(){return &context;}bool IsRealPlayer(){return real;}
 bool HasStrategy(const char*,BotState){return dungeon;}bool CanMove(){return canMove;}
 bool IsTank(Player* p){return p->tank;}bool IsHeal(Player* p){return p->healer;}bool IsRanged(Player* p){return p->ranged;}
 Unit* GetUnit(ObjectGuid g){for(auto u:allUnits)if(u->guid==g)return u;return nullptr;}
 GameObject* GetGameObject(ObjectGuid g){for(auto o:allObjects)if(o->guid==g)return o;return nullptr;}
 void StopMoving(){++stops;bot->stopped=true;bot->motion.type=0;}
 void InterruptSpell(){++interrupts;bot->casts[0]=nullptr;bot->casts[1]=nullptr;}};
struct Event{};struct Action{virtual ~Action()=default;};struct MovementAction:Action{};struct AttackAction:MovementAction{};
struct MoveAwayFromHazard:MovementAction{};struct CastSpellAction:Action{bool movement=false;bool HasMovementEffect(){return movement;}};
namespace ai {
 bool HasMagtheridonChannel(Player*);bool IsMagtheridonNova(Unit*);bool IsMagtheridonCubeUser(PlayerbotAI*,Player*,Unit*);
 bool IsMagtheridonCube(Player*,GameObject*);Unit* FindMagtheridonCubeTrigger(Player*,GameObject*);
 bool ValidateEncounterDestination(PlayerbotAI* a,EncounterPosition& p){++a->paths;if(a->adjustBad)p.destination={9999,0,0};return a->path;}
 struct MagtheridonPositionValue{Player* bot;PlayerbotAI* ai;EncounterPosition Calculate();};
 struct MagtheridonCubeAction:MovementAction{PlayerbotAI* ai;Player* bot;unsigned duration=0;MagtheridonCubeAction(PlayerbotAI* a):ai(a),bot(a->bot){}
  static Unit* GetBoss(PlayerbotAI*);static bool GetPlan(PlayerbotAI*,EncounterPosition&);bool isUseful();bool isPossible();bool ShouldReactionInterruptCast()const;bool Execute(Event&);
  void SetDuration(unsigned n){duration=n;}bool IsReaction(){return true;}
  bool MoveTo(unsigned m,float,float,float,bool idle,bool react,bool noPath,bool ignore){assert(m==544&&!idle&&react&&!noPath&&ignore);++ai->moves;return true;}};
 struct PreserveMagtheridonCubeMultiplier{PlayerbotAI* ai;float GetValue(Action*);};
}
__METHODS__
int main(){
 Map map,otherMap;Group group,otherGroup;Unit boss;boss.map=&map;boss.guid=500;boss.entry=17257;
 SpellEntry novaInfo{30616},otherInfo{1},graspInfo{30410};Spell nova{&novaInfo},other{&otherInfo},grasp{&graspInfo};
 Player players[8];PlayerbotAI ais[8];GroupReference refs[8];Unit beams[5];GameObject cubes[5];
 for(unsigned i=0;i<8;++i){auto& p=players[i];p.map=&map;p.guid=i+1;p.group=&group;p.ai=&ais[i];ais[i].bot=&p;
  refs[i]={&p,i==7?nullptr:&refs[i+1]};}
 group.first=&refs[0];allUnits={&boss};
 for(unsigned i=0;i<5;++i){float a=float(i)*6.2831853f/5;float x=std::cos(a)*30,y=std::sin(a)*30;
  cubes[i].map=&map;cubes[i].guid=100+i;cubes[i].entry=181713;cubes[i].x=x;cubes[i].y=y;
  beams[i].map=&map;beams[i].guid=200+i;beams[i].entry=17376;beams[i].x=x;beams[i].y=y;beams[i].z=2;
  allObjects.push_back(&cubes[i]);allUnits.push_back(&beams[i]);}
 Player& bot=players[0];PlayerbotAI& ai=ais[0];MagtheridonPositionValue value{&bot,&ai};MagtheridonCubeAction action(&ai);Event event;EncounterPosition plan;
 auto refresh=[&](){ai.context.position.value=value.Calculate();return MagtheridonCubeAction::GetPlan(&ai,plan);};
#ifdef MANGOSBOT_ZERO
 assert(!refresh()&&!action.isUseful()&&!action.Execute(event));bot.casts[1]=&grasp;boss.casts[1]=&nova;
 assert(!HasMagtheridonChannel(&bot)&&!IsMagtheridonNova(&boss)&&!FindMagtheridonCubeTrigger(&bot,&cubes[0]));
#else
 assert(refresh()&&plan.source==100&&ai.paths==1);assert(action.isUseful()&&!action.ShouldReactionInterruptCast());
 assert(action.Execute(event)&&ai.moves==1&&bot.session.clicks==0);
 bot.x=plan.destination.x;bot.y=plan.destination.y;bot.z=plan.destination.z;assert(!action.isUseful());
 bot.stopped=false;assert(action.isUseful()&&action.Execute(event)&&bot.session.clicks==0);
 boss.casts[1]=&nova;assert(action.isUseful()&&action.ShouldReactionInterruptCast());
 bot.casts[0]=&other;assert(action.Execute(event)&&bot.session.clicks==1&&bot.session.clicked==100&&ai.interrupts==1&&action.duration==1000);
 // Core acceptance is separate: a submitted packet is not fabricated success.
 assert(!HasMagtheridonChannel(&bot));bot.casts[1]=&grasp;bot.auras.insert(30410);beams[0].auras.insert(30410);
 assert(HasMagtheridonChannel(&bot)&&!action.isUseful()&&!action.ShouldReactionInterruptCast()&&!action.Execute(event));
 MovementAction move;AttackAction attack;CastSpellAction cast;MoveAwayFromHazard hazard;PreserveMagtheridonCubeMultiplier mult{&ai};
 assert(mult.GetValue(&move)==0&&mult.GetValue(&attack)==0&&mult.GetValue(&cast)==0);
 assert(mult.GetValue(&hazard)==1&&mult.GetValue(&action)==1);
 // Native five-beam interruption ends Nova. Only native channel cancellation,
 // never aura deletion or cooldown reset, is submitted by the action.
 boss.casts[1]=nullptr;assert(action.isUseful()&&action.Execute(event)&&bot.cancelled==1&&action.duration==100);
 beams[0].auras.clear();bot.auras.insert(44032);assert(!refresh());bot.auras.clear();assert(refresh());
 assert(mult.GetValue(&move)==0&&mult.GetValue(&cast)==1&&mult.GetValue(&attack)==1);
 cast.movement=true;assert(mult.GetValue(&cast)==0);cast.movement=false;
 // Each eligible bot gets a distinct cube. Human/tank/healer roles and old
 // channels/exhaustion remove candidates, never forcibly recruit a player.
 std::set<unsigned> assigned;for(unsigned i=0;i<8;++i){MagtheridonPositionValue v{&players[i],&ais[i]};auto p=v.Calculate();if(p.active)assigned.insert(p.source);}
 assert(assigned.size()==5);
 players[1].tank=true;players[2].healer=true;ais[3].real=true;players[4].auras.insert(44032);ais[5].dungeon=false;
 for(unsigned i=1;i<=5;++i)assert(!IsMagtheridonCubeUser(&ai,&players[i],&boss));
 players[1].tank=false;players[2].healer=false;ais[3].real=false;players[4].auras.clear();ais[5].dungeon=true;
 boss.victim=&bot;assert(!refresh());boss.victim=nullptr;
 bot.ranged=false;assert(!refresh());boss.casts[1]=&nova; // six ranged means this melee bot is not selected even during Nova
 assert(!refresh());for(unsigned i=1;i<8;++i)players[i].ranged=false;assert(refresh());
 boss.casts[1]=nullptr;assert(!refresh());for(auto& p:players)p.ranged=true;assert(refresh());
 // Occupied human cube and short-lived GO flag do not allow overlapping clicks.
 beams[0].auras.insert(30410);assert(!MagtheridonCubeAction::GetPlan(&ai,plan)&&!action.Execute(event));
 assert(refresh()&&plan.source==101);beams[0].auras.clear();assert(refresh()&&plan.source==100);
 cubes[0].flags=GO_FLAG_IN_USE;assert(!action.Execute(event));cubes[0].flags=GO_FLAG_NO_INTERACT;assert(!action.Execute(event));cubes[0].flags=0;
 cubes[0].spawned=false;assert(!action.Execute(event));cubes[0].spawned=true;
 beams[0].world=false;assert(!action.Execute(event));beams[0].world=true;beams[0].phase=2;assert(!action.Execute(event));beams[0].phase=1;
 Unit duplicate=beams[0];duplicate.guid=999;allUnits.push_back(&duplicate);assert(!FindMagtheridonCubeTrigger(&bot,&cubes[0]));allUnits.pop_back();
 ai.path=false;assert(!refresh());ai.path=true;assert(refresh());ai.adjustBad=true;assert(!action.Execute(event));ai.adjustBad=false;
 boss.casts[1]=&nova;bot.los=false;assert(!action.Execute(event));bot.los=true;
 bot.x=0;bot.y=0;assert(refresh()&&action.Execute(event)&&bot.session.clicks==1); // walks, no remote click
 ai.canMove=false;assert(!refresh()&&!action.isPossible());ai.canMove=true;
 bot.teleport=true;assert(!refresh());bot.teleport=false;bot.charmed=true;assert(!refresh());bot.charmed=false;
 bot.group=&otherGroup;assert(!refresh());bot.group=&group;bot.session.logout=true;assert(!refresh());bot.session.logout=false;
 bot.haveSession=false;assert(!refresh());bot.haveSession=true;
 boss.combat=false;assert(!refresh());boss.combat=true;boss.alive=false;assert(!refresh());boss.alive=true;
 boss.auras.insert(30205);assert(!refresh());boss.auras.clear();boss.phase=2;assert(!refresh());boss.phase=1;assert(refresh());
 ++bot.instance;assert(!MagtheridonCubeAction::GetPlan(&ai,plan));--bot.instance;
 bot.mapId=1;assert(!refresh());bot.mapId=544;assert(refresh());
 // Dead encounter / group loss must release a still-native channel, including
 // out of combat. The default combat strategy cannot hold it forever.
 bot.casts[1]=&grasp;bot.auras.insert(30410);bot.combat=false;assert(action.isUseful()&&action.Execute(event)&&bot.cancelled==2);
 bot.combat=true;bot.casts[1]=&grasp;bot.group=nullptr;assert(action.Execute(event)&&bot.cancelled==3);bot.group=&group;
 assert(!IsMagtheridonNova(nullptr));nova.state=SPELL_STATE_FINISHED;assert(!IsMagtheridonNova(&boss));nova.state=0;
 boss.entry=1;assert(!IsMagtheridonNova(&boss));boss.entry=17257;
#endif
 std::cout<<"PASS: actual Magtheridon assignment, native click/channel policy, roles, stale occupancy, path gates and lifecycle\n";
}
'''.replace('__GEOMETRY__',(root/'playerbot/strategy/EncounterGeometry.h').as_posix()).replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-magtheridon-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
for realm in ('tbc','wotlk'):
    core=root.parent/f'mangos-{realm}-behavior'
    native=(core/'src/game/AI/ScriptDevAI/scripts/outland/hellfire_citadel/magtheridons_lair/boss_magtheridon.cpp').read_text()
    assert 'GetAuraCount(30166) == 5' in native and 'SetManticronCubeUser(player->GetObjectGuid())' in native
    assert 'SPELL_MIND_EXHAUSTION      = 44032' in native or '44032' in native
    assert 'TRIGGERED_NONE) == SPELL_CAST_OK' in native
for forbidden in ('TeleportTo(', 'RemoveAurasDueToSpell(', 'RemoveSpellCooldown(', 'CastSpell('):
    assert forbidden not in action
strategy=(root/'playerbot/strategy/generic/DungeonStrategy.cpp').read_text()
for state in ('Combat','NonCombat','Reaction'):
    assert 'magtheridon cube' in block(strategy,f'void DungeonStrategy::Init{state}Triggers(')
for state in ('Combat','Reaction'):
    assert 'PreserveMagtheridonCubeMultiplier' in block(strategy,f'void DungeonStrategy::Init{state}Multipliers(')
print('PASS: native five-beam/GO contracts and strategy cleanup wiring; live encounter validation still required')
