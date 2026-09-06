"""Exercise actual cast selection/movement lifetime against native-interface fixtures.

The fixture cannot establish encounter success or replace real map path testing.
"""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
base = root / "playerbot/strategy"
extract = (
    ("values/BossCastPositionValue.cpp", ("bool ai::IsBossEscapeMap(",
        "uint32 ai::NativeBossEscapeSpell(", "EncounterPosition BossCastPositionValue::Calculate(")),
    ("actions/DungeonActions.cpp", ("bool BossCastPositionAction::GetPlan(",
        "bool BossCastPositionAction::isUseful(", "bool BossCastPositionAction::ShouldReactionInterruptCast(",
        "bool BossCastPositionAction::Execute(")),
    ("generic/DungeonMultipliers.cpp", ("float PreserveBossCastPositionMultiplier::GetValue(",)),
)
methods = "\n".join(block((base / path).read_text(), name) for path, names in extract for name in names)
code = r'''
#include <cassert>
#include <list>
#include <map>
#include <limits>
#include <type_traits>
#include <iostream>
#include "__GEOMETRY__"
using uint32=unsigned;using ObjectGuid=unsigned;
constexpr int CURRENT_GENERIC_SPELL=1,SPELL_STATE_FINISHED=2,IDLE_MOTION_TYPE=0;
struct SpellEntry {unsigned Id=0;};
struct Spell {SpellEntry* m_spellInfo=nullptr;int state=0;int getState()const{return state;}};
struct Map {};
struct Unit {unsigned entry=0,guid=1,phase=1;bool world=true,alive=true,combat=true,charmed=false;Map* map=nullptr;
 float x=0,y=0,z=0;Spell* current=nullptr;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 bool HasCharmer(){return charmed;}unsigned GetEntry(){return entry;}Map* GetMap(){return map;}
 unsigned GetObjectGuid(){return guid;}Spell* GetCurrentSpell(int){return current;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}
 float GetDistance(Unit* u){return GetDistance(u->x,u->y,u->z);}};
struct Motion {int kind=0;int GetCurrentMovementGeneratorType(){return kind;}};
struct Player:Unit {bool teleport=false,stopped=true;unsigned mapId=532,instance=1;Motion motion;
 bool IsInMap(Unit* unit){return map==unit->map&&phase==unit->phase;}
 bool IsBeingTeleported(){return teleport;}unsigned GetMapId(){return mapId;}unsigned GetInstanceId(){return instance;}
 bool IsStopped(){return stopped;}Motion* GetMotionMaster(){return &motion;}};
namespace ai {
 struct EncounterPosition {bool active=false;unsigned map=0,instance=0,boss=0,spell=0;encounter::Point destination;};
 bool IsBossEscapeMap(unsigned);unsigned NativeBossEscapeSpell(unsigned,unsigned,unsigned);
 std::map<unsigned,float> radii{{29973,21},{33666,34},{38795,34},{52960,20},{59835,20},{63631,15},{68989,15}};
 float NativeEncounterSpellRadius(unsigned id){return radii[id];}
}
template<class T>struct Stored {T value{};T Get(){return value;}};
struct Context {Stored<ai::EncounterPosition> plan;Stored<bool> wreath;unsigned reads=0;
 template<class T>Stored<T>* GetValue(const char*) {++reads;
  if constexpr(std::is_same_v<T,bool>)return &wreath;else return &plan;}};
struct PlayerbotAI {Player* bot;Context context;std::list<ObjectGuid> attackers;std::map<unsigned,Unit*> units;
 bool validPath=true,canMove=true;unsigned checked=0,stops=0,moves=0;ai::encounter::Point moved;
 Player* GetBot(){return bot;}Context* GetAiObjectContext(){return &context;}
 Unit* GetUnit(unsigned id){auto it=units.find(id);return it==units.end()?nullptr:it->second;}
 template<class T>T Value(const char*){if constexpr(std::is_same_v<T,bool>)return context.wreath.value;else return attackers;}
 bool CanMove(){return canMove;}void StopMoving(){++stops;bot->stopped=true;bot->motion.kind=0;}};
struct Event {};
namespace ai {
 bool ValidateEncounterDestination(PlayerbotAI* ai,EncounterPosition&){++ai->checked;return ai->validPath;}
 struct Action {virtual ~Action()=default;};
 struct MovementAction:Action {Player* bot;PlayerbotAI* ai;MovementAction(PlayerbotAI* a):bot(a->bot),ai(a){}
  bool MoveTo(unsigned map,float x,float y,float z,bool idle,bool reaction,bool noPath,bool ignoreEnemies){
   assert(map==bot->mapId && !idle && reaction && !noPath && ignoreEnemies);++ai->moves;ai->moved={x,y,z};return true;}
  bool IsReaction(){return true;}void SetDuration(unsigned){}};
 struct AttackAction:MovementAction {using MovementAction::MovementAction;};
 struct MoveAwayFromHazard:MovementAction {using MovementAction::MovementAction;};
 struct CastSpellAction:Action {bool movement=false;bool HasMovementEffect(){return movement;}};
 struct BossCastPositionValue {Player* bot;PlayerbotAI* ai;EncounterPosition Calculate();};
 struct BossCastPositionAction:MovementAction {using MovementAction::MovementAction;
  static bool GetPlan(PlayerbotAI*,EncounterPosition&);bool isUseful();bool Execute(Event&);
  bool ShouldReactionInterruptCast()const;};
 struct PreserveBossCastPositionMultiplier {PlayerbotAI* ai;float GetValue(Action*);};
}
using namespace ai;
#define AI_VALUE(type,name) ai->Value<type>(name)
__METHODS__
int main(){
 Map map,otherMap;Player bot;bot.map=&map;Unit boss;boss.map=&map;boss.entry=16524;
 SpellEntry entry{29973};Spell cast{&entry};boss.current=&cast;
 PlayerbotAI ai{&bot};ai.attackers={1};ai.units[1]=&boss;
 BossCastPositionValue value{&bot,&ai};BossCastPositionAction action(&ai);
 PreserveBossCastPositionMultiplier multiplier{&ai};MovementAction chase(&ai);AttackAction attack(&ai);
 MoveAwayFromHazard hazard(&ai);CastSpellAction heal,charge;charge.movement=true;Event event;
 auto load=[&](){return ai.context.plan.value=value.Calculate();};
#ifdef MANGOSBOT_ZERO
 for(unsigned id:{532u,555u,602u,603u,658u})assert(!IsBossEscapeMap(id));
 assert(!load().active && ai.checked==0);assert(!action.isUseful() && !action.Execute(event));
 assert(multiplier.GetValue(&chase)==1 && multiplier.GetValue(&charge)==1 && ai.context.reads==0);
 assert(NativeBossEscapeSpell(532,16524,29973)==0);
#else
 assert(IsBossEscapeMap(532) && IsBossEscapeMap(555) && !IsBossEscapeMap(0));
 auto plan=load();assert(plan.active && encounter::Distance2d(plan.destination,{0,0,0})>=23);
 assert(action.isUseful() && action.ShouldReactionInterruptCast());assert(action.Execute(event) && ai.moves==1);
 assert(multiplier.GetValue(&chase)==0 && multiplier.GetValue(&charge)==0);
 assert(multiplier.GetValue(&heal)==1 && multiplier.GetValue(&attack)==1 && multiplier.GetValue(&hazard)==1);
 // Already safe: stop an old chase, retain a stationary heal, then let casting proceed.
 bot.x=30;load();bot.motion.kind=1;assert(action.isUseful() && !action.ShouldReactionInterruptCast());
 assert(action.Execute(event) && ai.stops==1 && ai.moves==1 && !action.isUseful());
 // No cached hold survives completion/interruption, spell replacement, reset or map transfer.
 cast.state=SPELL_STATE_FINISHED;assert(!action.isUseful() && multiplier.GetValue(&chase)==1);
 cast.state=0;entry.Id=30004;assert(!action.Execute(event));entry.Id=29973;
 boss.current=nullptr;assert(!action.Execute(event));boss.current=&cast;
 boss.alive=false;assert(!action.Execute(event));boss.alive=true;
 boss.combat=false;assert(!action.Execute(event));boss.combat=true;
 boss.map=&otherMap;assert(!action.Execute(event));boss.map=&map;
 boss.phase=2;assert(!action.Execute(event)&&!load().active);boss.phase=1;load();
 boss.charmed=true;assert(!action.Execute(event));boss.charmed=false;
 bot.instance=2;assert(!action.Execute(event));bot.instance=1;
 bot.teleport=true;assert(!load().active && !action.Execute(event));bot.teleport=false;
 bot.charmed=true;assert(!load().active);bot.charmed=false;
 bot.alive=false;assert(!load().active);bot.alive=true;
 bot.world=false;assert(!load().active);bot.world=true;
 bot.combat=false;assert(!load().active);bot.combat=true;
 bot.mapId=0;assert(!load().active);bot.mapId=532;
 boss.z=20;assert(!load().active);boss.z=0;
 ai.context.wreath.value=true;assert(!load().active && !action.Execute(event));ai.context.wreath.value=false;
 bot.x=0;ai.validPath=false;ai.checked=0;assert(!load().active && ai.checked<=8);ai.validPath=true;
 radii[29973]=0;assert(!load().active);radii[29973]=200;assert(!load().active);
 radii[29973]=std::numeric_limits<float>::quiet_NaN();assert(!load().active);radii[29973]=21;
 load();boss.x=ai.context.plan.value.destination.x;boss.y=ai.context.plan.value.destination.y;
 assert(!action.Execute(event));boss.x=boss.y=0; // moving caster invalidates stale safety
 load();ai.canMove=false;assert(!action.Execute(event));ai.canMove=true;
 // Murmur uses the native dummy's damage spell, not the zero-radius dummy.
 bot.mapId=555;boss.entry=18708;entry.Id=33923;
 assert(NativeBossEscapeSpell(555,18708,33923)==33666);
 plan=load();assert(plan.active && encounter::Distance2d(plan.destination,{0,0,0})>=36);
 entry.Id=38796;assert(NativeBossEscapeSpell(555,18708,38796)==38795 && load().active);
 assert(!NativeBossEscapeSpell(532,18708,33923) && !NativeBossEscapeSpell(555,1,33923));
#ifdef MANGOSBOT_TWO
 const unsigned cases[][3]={{602,28923,52960},{602,28923,59835},{603,33432,63631},{658,36476,68989}};
 for(const auto& c:cases){bot.mapId=c[0];boss.entry=c[1];entry.Id=c[2];plan=load();
  assert(plan.active && encounter::Distance2d(plan.destination,{0,0,0})>=radii[c[2]]+2);}
#else
 assert(!IsBossEscapeMap(602) && !IsBossEscapeMap(603) && !IsBossEscapeMap(658));
 assert(!NativeBossEscapeSpell(602,28923,52960));
#endif
#endif
 std::cout<<"PASS: actual native cast/difficulty/expansion/radius selection, bounded escape, safe hold, cast lifetime and movement arbitration\n";
}
'''.replace('__GEOMETRY__', (base / 'EncounterGeometry.h').as_posix()).replace('__METHODS__', methods)
for expansion in ('ZERO', 'ONE', 'TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-boss-cast-test-') as tmp:
        tmp = Path(tmp)
        (tmp / 'test.cpp').write_text(code)
        subprocess.run(['cl', '/nologo', '/EHsc', '/std:c++17', f'/DMANGOSBOT_{expansion}',
            'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], check=True)
for path in ('actions/ActionContext.h', 'triggers/TriggerContext.h', 'generic/DungeonStrategy.cpp'):
    assert 'boss cast safe position' in (base / path).read_text()
strategy = (base / 'generic/DungeonStrategy.cpp').read_text()
for hook in ('InitCombatMultipliers', 'InitReactionMultipliers', 'InitCombatTriggers', 'InitReactionTriggers'):
    body = block(strategy, f'void DungeonStrategy::{hook}(')
    assert ('PreserveBossCastPositionMultiplier' if 'Multipliers' in hook else 'boss cast safe position') in body
header = (base / 'generic/DungeonStrategy.h').read_text()
for hook in ('InitCombatMultipliers', 'InitReactionMultipliers'):
    assert header.count(f'void {hook}(') == 1
print('PASS: native boss-cast registry and combat/reaction strategy wiring')
