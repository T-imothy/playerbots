"""Exercise actual cast selection/movement lifetime against native-interface fixtures.

The fixture cannot establish encounter success or replace real map path testing.
"""
from pathlib import Path
import subprocess
import tempfile
import sys
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
base = root / "playerbot/strategy"
extract = (
    ("values/BossCastPositionValue.cpp", ("bool ai::IsBossEscapeMap(",
        "uint32 ai::NativeBossEscapeSpell(", "const Spell* ai::CurrentBossEscapeCast(",
        "EncounterPosition BossCastPositionValue::Calculate(")),
    ("actions/DungeonActions.cpp", ("bool BossCastPositionAction::GetPlan(",
        "bool BossCastPositionAction::isUseful(", "bool BossCastPositionAction::ShouldReactionInterruptCast(",
        "bool BossCastPositionAction::Execute(")),
    ("generic/DungeonMultipliers.cpp", ("float PreserveBossCastPositionMultiplier::GetValue(",)),
)
def source(path):
    if '--before-aura-escape' in sys.argv and path in ('values/BossCastPositionValue.cpp', 'actions/DungeonActions.cpp'):
        return subprocess.check_output(['git','-c','safe.directory='+root.as_posix(),'-C',str(root),
            'show','ae802751:playerbot/strategy/'+path],text=True)
    if '--before-dungeon-escapes' in sys.argv and path == 'values/BossCastPositionValue.cpp':
        return subprocess.check_output(['git','-c','safe.directory='+root.as_posix(),'-C',str(root),
            'show','88f43c09:playerbot/strategy/'+path],text=True)
    return (base / path).read_text()
methods = "\n".join(block(source(path), name) for path, names in extract for name in names)
methods = block((base/'values/AQWhirlwindPositionValue.cpp').read_text(), 'bool ai::AQWhirlwindThreats(') + '\n' + methods
methods = '\n'.join(block((base/'values/LokenPositionValue.cpp').read_text(), name) for name in
    ('bool ai::IsLokenClosePhase(', 'bool ai::PlanLokenClosePosition(')) + '\n' + methods
if 'uint32 ai::CurrentBossEscapeSpell(' in source('values/BossCastPositionValue.cpp'):
    methods = block(source('values/BossCastPositionValue.cpp'), 'uint32 ai::CurrentBossEscapeSpell(') + '\n' + methods
code = r'''
#include <cassert>
#include <list>
#include <map>
#include <limits>
#include <type_traits>
#include <iostream>
#include "__GEOMETRY__"
using uint32=unsigned;using ObjectGuid=unsigned;
struct PlayerbotAI;
constexpr int CURRENT_GENERIC_SPELL=1,CURRENT_CHANNELED_SPELL=3,SPELL_STATE_FINISHED=2,IDLE_MOTION_TYPE=0;
struct SpellEntry {unsigned Id=0;};
struct Spell {SpellEntry* m_spellInfo=nullptr;int state=0;int getState()const{return state;}};
struct Map {bool regular=true;
#ifndef MANGOSBOT_ZERO
 bool IsRegularDifficulty(){return regular;}
#endif
};
struct Unit {unsigned entry=0,guid=1,phase=1;bool world=true,alive=true,combat=true,charmed=false;Map* map=nullptr;
 unsigned aura=0;bool auraOwner=true;bool HasAura(unsigned id){return aura==id;}
 bool GetSpellAuraHolder(unsigned id,unsigned caster){return auraOwner&&aura==id&&caster==guid;}
 float x=0,y=0,z=0;Spell* current=nullptr;Spell* channel=nullptr;Unit* victim=nullptr;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 bool HasCharmer(){return charmed;}unsigned GetEntry(){return entry;}Map* GetMap(){return map;}
 Unit* GetVictim(){return victim;}
 unsigned GetObjectGuid(){return guid;}Spell* GetCurrentSpell(int slot){return slot==CURRENT_GENERIC_SPELL?current:channel;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}
 float GetDistance(Unit* u){return GetDistance(u->x,u->y,u->z);}};
struct Motion {int kind=0;int GetCurrentMovementGeneratorType(){return kind;}};
struct Player:Unit {bool teleport=false,stopped=true,casting=false;unsigned mapId=532,instance=1;Motion motion;
 bool IsNonMeleeSpellCasted(bool,bool,bool){return casting;}
 bool IsInMap(Unit* unit){return map==unit->map&&phase==unit->phase;}
 bool IsBeingTeleported(){return teleport;}unsigned GetMapId(){return mapId;}unsigned GetInstanceId(){return instance;}
 bool IsStopped(){return stopped;}Motion* GetMotionMaster(){return &motion;}};
namespace ai {
 struct EncounterPosition {bool active=false;unsigned map=0,instance=0,boss=0,spell=0;encounter::Point destination;};
 bool IsBossEscapeMap(unsigned);unsigned NativeBossEscapeSpell(unsigned,unsigned,unsigned__DIFFICULTY__);
 bool AQWhirlwindThreats(PlayerbotAI*,EncounterPosition&,std::vector<encounter::Circle>&);
 bool IsLokenClosePhase(Player*,Unit*);
 bool PlanLokenClosePosition(PlayerbotAI*,Unit*,EncounterPosition&);
 unsigned CurrentBossEscapeSpell(Player*,Unit*);
 const Spell* CurrentBossEscapeCast(Player*,Unit*);
 std::map<unsigned,float> radii{{29973,21},{33666,34},{38795,34},{52960,20},{59835,20},{63631,15},{68989,15},{34164,18},
 {34660,15},{39132,15},{55081,15},{59842,15},{33775,20},{37371,20},{36142,8},{64216,20},{65279,100},{70123,25},{71047,25},{71048,25},{71049,25},{26084,10},{26686,10}};
 float NativeEncounterSpellRadius(unsigned id){return radii[id];}
}
template<class T>struct Stored {T value{};T Get(){return value;}};
struct Context {Stored<ai::EncounterPosition> plan;Stored<bool> wreath;Stored<std::list<unsigned>> attackers;unsigned reads=0;
 template<class T>Stored<T>* GetValue(const char*) {++reads;
  if constexpr(std::is_same_v<T,bool>)return &wreath;else if constexpr(std::is_same_v<T,std::list<unsigned>>)return &attackers;else return &plan;}};
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
 auto load=[&](){ai.context.attackers.value=ai.attackers;return ai.context.plan.value=value.Calculate();};
#ifdef MANGOSBOT_ZERO
 for(unsigned id:{532u,542u,550u,552u,553u,555u,602u,603u,604u,624u,658u})assert(!IsBossEscapeMap(id));
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
 // Native Pounding lives in the channeled slot, not CURRENT_GENERIC_SPELL.
 bot.mapId=550;boss.entry=19516;entry.Id=34162;boss.current=nullptr;boss.channel=&cast;
 assert(NativeBossEscapeSpell(550,19516,34162)==34164&&IsBossEscapeMap(550));
 plan=load();assert(plan.active&&encounter::Distance2d(plan.destination,{0,0,0})>=20);
 boss.victim=&bot;assert(!action.Execute(event)&&!load().active);boss.victim=nullptr;
 plan=load();assert(plan.active);cast.state=SPELL_STATE_FINISHED;assert(!action.Execute(event)&&!load().active);cast.state=0;
 assert(load().active);boss.channel=nullptr;assert(!action.Execute(event));boss.current=&cast;
 assert(load().active);entry.Id=34172;assert(!action.Execute(event)&&!load().active); // Orb isn't a caster-centred escape.
#ifdef MANGOSBOT_TWO
 const unsigned cases[][3]={{602,28923,52960},{602,28923,59835},{603,33432,63631},{658,36476,68989},{604,29304,55081},{604,29304,59842},{624,33993,64216},{631,36853,70123},{631,36853,71047},{631,36853,71048},{631,36853,71049}};
 for(const auto& c:cases){bot.mapId=c[0];boss.entry=c[1];entry.Id=c[2];plan=load();
  assert(plan.active && encounter::Distance2d(plan.destination,{0,0,0})>=radii[c[2]]+2);}
 bot.mapId=624;boss.entry=33993;entry.Id=65279;
 assert(!load().active); // Actual dev DBC radius is100; no imaginary25-yard safe point.
#else
 assert(!IsBossEscapeMap(602) && !IsBossEscapeMap(603) && !IsBossEscapeMap(604) && !IsBossEscapeMap(624) && !IsBossEscapeMap(658));
 assert(!NativeBossEscapeSpell(602,28923,52960));
 assert(!IsBossEscapeMap(631)&&!NativeBossEscapeSpell(631,36853,70123));
#endif
 // Botanica's Hellfire channel has a zero-radius parent and distinct native
 // normal/heroic damage payloads. Hold only for the actual ongoing channel.
 bot.mapId=553;boss.entry=17978;boss.current=nullptr;boss.channel=&cast;bot.x=bot.y=0;
 for(unsigned id:{34659u,39131u}){
  entry.Id=id;cast.state=0;
  assert(IsBossEscapeMap(553));plan=load();assert(plan.active);
  assert(encounter::Distance2d(plan.destination,{0,0,0})>=17);
  assert(NativeBossEscapeSpell(553,17978,id)==(id==34659?34660:39132));
  assert(!NativeBossEscapeSpell(554,17978,id)&&!NativeBossEscapeSpell(553,1,id));
  assert(action.Execute(event));cast.state=SPELL_STATE_FINISHED;
  assert(!action.Execute(event)&&multiplier.GetValue(&chase)==1);
 }
 cast.state=0;load();boss.channel=nullptr;assert(!action.Execute(event));
 // Keli'dan's instant warning has no current cast. Difficulty selects the
 // native payload; expiry must invalidate an already queued movement action.
 bot.mapId=542;boss.entry=17377;boss.aura=30940;boss.current=boss.channel=nullptr;
 for(bool regular:{true,false}){
  map.regular=regular;plan=load();assert(plan.active && plan.spell==30940);
  assert(encounter::Distance2d(plan.destination,{0,0,0})>=22);
  assert(action.Execute(event));boss.aura=0;
  assert(!action.Execute(event)&&!load().active&&multiplier.GetValue(&chase)==1);
  boss.aura=30940;
 }
 boss.entry=17378;assert(!load().active);boss.entry=17377;
 bot.mapId=543;assert(!load().active);bot.mapId=542;
 boss.combat=false;assert(!load().active);boss.combat=true;
 ai.validPath=false;ai.checked=0;assert(!load().active&&ai.checked<=8);ai.validPath=true;
 plan=load();boss.map=&otherMap;assert(!action.Execute(event));boss.map=&map;
 boss.aura=0;entry.Id=33775;boss.current=&cast;assert(!load().active);
 // Dalliah's periodic Whirlwind aura persists between ticks; her heal starts
 // when that aura expires, and must not inherit the movement hold.
 bot.mapId=552;boss.entry=20885;boss.aura=36142;boss.current=nullptr;
 plan=load();assert(plan.active&&plan.spell==36142);
 assert(encounter::Distance2d(plan.destination,{0,0,0})>=10&&action.Execute(event));
 boss.aura=0;entry.Id=36144;boss.current=&cast;
 assert(!action.Execute(event)&&!load().active&&multiplier.GetValue(&chase)==1);
#endif
 // Sartura and her guards are simultaneous moving hazards. Clear every active
 // whirlwind, and reject a cached point if another guard moves into it.
 bot.mapId=531;bot.x=bot.y=0;boss.x=boss.y=boss.z=0;boss.entry=15516;boss.aura=26083;
 boss.current=boss.channel=nullptr;Unit guard;guard.guid=2;guard.entry=15984;guard.aura=26038;guard.x=8;guard.map=&map;
 ai.units[2]=&guard;ai.attackers={1,2};auto aq=load();assert(aq.active&&aq.boss==1&&aq.spell==26083);
 assert(encounter::Distance2d(aq.destination,{0,0,0})>=12&&encounter::Distance2d(aq.destination,{8,0,0})>=12);
 assert(action.Execute(event));guard.x=aq.destination.x;guard.y=aq.destination.y;assert(!action.Execute(event));
 guard.x=8;guard.y=0;aq=load();boss.aura=0;assert(!action.Execute(event));aq=load();assert(aq.active&&aq.boss==2);
 guard.auraOwner=false;assert(!load().active);guard.auraOwner=true;guard.combat=false;assert(!load().active);guard.combat=true;
 guard.phase=2;assert(!load().active);guard.phase=1;guard.z=20;assert(!load().active);guard.z=0;
 ai.validPath=false;ai.checked=0;assert(!load().active&&ai.checked<=8);ai.validPath=true;
 guard.aura=0;assert(!load().active&&multiplier.GetValue(&chase)==1);
#ifdef MANGOSBOT_TWO
 // Native Shockwave damage scales with distance: close after Nova, escape
 // again on the next cast, and never clip a heal merely to return closer.
 ai.attackers={1};bot.mapId=602;bot.x=30;boss.entry=28923;boss.aura=52961;boss.current=boss.channel=nullptr;
 auto close=load();assert(close.active&&close.spell==59414&&encounter::Distance2d(close.destination,{0,0,0})<=5);
 assert(action.isUseful()&&!action.ShouldReactionInterruptCast()&&action.Execute(event));
 assert(multiplier.GetValue(&chase)==0&&multiplier.GetValue(&heal)==1);
 bot.casting=true;assert(!action.isUseful()&&!action.Execute(event));bot.casting=false;
 entry.Id=52960;cast.state=0;boss.current=&cast;
 assert(!action.Execute(event)); // Cached return-to-boss cannot survive Nova starting.
 bot.x=0;auto nova=load();assert(nova.active&&nova.spell==52960&&action.ShouldReactionInterruptCast());
 boss.current=nullptr;assert(!action.Execute(event));bot.x=30;
 for(unsigned aura:{52961u,59836u}){boss.aura=aura;assert(load().active);}
 boss.auraOwner=false;assert(!load().active);boss.auraOwner=true;
 boss.victim=&bot;assert(!load().active);boss.victim=nullptr;
 ai.validPath=false;ai.checked=0;assert(!load().active&&ai.checked==8);ai.validPath=true;
 close=load();boss.x=15;assert(!action.Execute(event));boss.x=0;
 bot.x=3;close=load();assert(close.active&&close.destination.x==3);bot.motion.kind=1;
 assert(action.isUseful()&&!action.ShouldReactionInterruptCast()&&action.Execute(event)&&!action.isUseful());
 boss.aura=0;assert(!action.Execute(event)&&!load().active&&multiplier.GetValue(&chase)==1);
 bot.mapId=603;boss.aura=52961;assert(!load().active);
#endif
 std::cout<<"PASS: actual native cast/difficulty/expansion/radius selection, bounded escape, safe hold, cast lifetime and movement arbitration\n";
}
'''.replace('__GEOMETRY__', (base / 'EncounterGeometry.h').as_posix()).replace('__METHODS__', methods).replace('__DIFFICULTY__', ',bool=true' if 'uint32 cast, bool regular' in source('values/BossCastPositionValue.cpp') else '')
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
