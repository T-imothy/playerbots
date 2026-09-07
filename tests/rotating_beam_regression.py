"""Actual beam planning/execution against controlled native world and route fixtures."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block
root = Path(__file__).resolve().parents[1]
base = root / 'playerbot/strategy'
methods = '\n'.join(block((base/path).read_text(), name) for path, names in (
    ('values/RotatingBeamPositionValue.cpp', ('bool ai::ReadRotatingBeam(',
        'bool ai::ValidateRotatingBeamDestination(', 'EncounterPosition RotatingBeamPositionValue::Calculate(')),
    ('actions/RotatingBeamAction.cpp', tuple('bool RotatingBeamAction::'+name+'(' for name in
        ('GetPlan','isUseful','ShouldReactionInterruptCast','Execute'))),
    ('generic/DungeonMultipliers.cpp', ('float PreserveRotatingBeamMultiplier::GetValue(',)),
) for name in names)
code = r'''
#include <cassert>
#include <iostream>
#include <list>
#include <map>
#include <set>
#include <limits>
#include <string>
#include "__GEOMETRY__"
using uint32=unsigned;using ObjectGuid=unsigned;
constexpr float M_PI_F=3.14159265358979323846f;
enum{EFFECT_INDEX_0,IDLE_MOTION_TYPE=0,MOVE_RUN=1};enum class BotState{BOT_STATE_COMBAT};
struct PlayerbotAI;
struct Unit{unsigned entry=0,guid=10,map=531,instance=1;float x=0,y=0,z=0,o=0;
 bool world=true,alive=true,combat=true,charm=false,ownAura=true;std::set<unsigned>auras;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charm;}
 bool IsInMap(Unit*u){return map==u->map&&instance==u->instance;}unsigned GetMapId(){return map;}unsigned GetInstanceId(){return instance;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}float GetOrientation(){return o;}
 unsigned GetEntry(){return entry;}unsigned GetObjectGuid(){return guid;}
 Unit*GetSpellAuraHolder(unsigned id,unsigned owner){return ownAura&&owner==guid&&auras.count(id)?this:nullptr;}
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}
 float GetDistance(Unit*u){return GetDistance(u->x,u->y,u->z);}};
struct Motion{int kind=0;int GetCurrentMovementGeneratorType(){return kind;}};
struct Player:Unit{bool teleport=false,group=true,water=false,deep=false,stopped=true,casting=false;float speed=7;Motion motion;
 bool IsBeingTeleported(){return teleport;}bool GetGroup(){return group;}bool IsInWater(){return water;}
#ifndef MANGOSBOT_ZERO
 bool IsInHighLiquid(){return deep;}
#endif
 bool IsStopped(){return stopped;}Motion*GetMotionMaster(){return &motion;}bool IsNonMeleeSpellCasted(bool){return casting;}
 float GetSpeed(int){return speed;}};
struct SpellEntry{unsigned EffectAmplitude[3]={1000,0,0};};struct SpellCone{float coneAngle=5;};
std::map<unsigned,SpellEntry>spells;std::map<unsigned,SpellCone>cones;
struct SpellStore{template<class T>const T*LookupEntry(unsigned id){auto it=spells.find(id);return it==spells.end()?nullptr:&it->second;}}sSpellTemplate;
struct ConeStore{template<class T>const T*LookupEntry(unsigned id){auto it=cones.find(id);return it==cones.end()?nullptr:&it->second;}}sSpellCones;
struct SpellMgr{unsigned GetFirstSpellInChain(unsigned id){return id;}}sSpellMgr;
namespace ai{
 struct EncounterPosition{bool active=false;unsigned map=0,instance=0,boss=0,spell=0;encounter::Point destination;};
 bool ReadRotatingBeam(PlayerbotAI*,Unit*,EncounterPosition&,encounter::RotatingBeam&);
 bool ValidateRotatingBeamDestination(PlayerbotAI*,EncounterPosition&,const encounter::RotatingBeam&);
 float radius=100;float NativeEncounterSpellRadius(unsigned){return radius;}
}
template<class T>struct Stored{T data{};T Get(){return data;}};
struct Context{Stored<ai::EncounterPosition>plan;template<class T>Stored<T>*GetValue(const char*){return &plan;}};
std::vector<Unit*>units;
struct PlayerbotAI{Player*bot;Context context;bool real=false,dungeon=true,move=true,valid=true;unsigned checks=0,moves=0,stops=0,interrupts=0;
 Player*GetBot(){return bot;}Context*GetAiObjectContext(){return &context;}bool IsRealPlayer(){return real;}
 bool HasStrategy(std::string name,BotState){assert(name=="dungeon");return dungeon;}bool CanMove(){return move;}
 Unit*GetUnit(unsigned id){for(auto*u:units)if(u->guid==id)return u;return nullptr;}
 void StopMoving(){++stops;bot->stopped=true;bot->motion.kind=0;}void InterruptSpell(){++interrupts;bot->casting=false;}};
bool pathComplete=true;unsigned paths=0;std::vector<ai::encounter::Point>detour;
struct WorldPosition{unsigned map;float x,y,z;WorldPosition(unsigned m,float a,float b,float c):map(m),x(a),y(b),z(c){}
 WorldPosition(Unit*u):WorldPosition(u->map,u->x,u->y,u->z){}
 float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}
 std::vector<WorldPosition>getPathStepFrom(WorldPosition start,Player*,bool)const{
  ++paths;std::vector<WorldPosition>out{start};for(auto p:detour)out.emplace_back(map,p.x,p.y,p.z);out.push_back(*this);return out;}
 bool isPathTo(const std::vector<WorldPosition>&,float,float)const{return pathComplete;}};
namespace MaNGOS{
 struct AllCreaturesOfEntryInRangeCheck{Unit*bot;unsigned entry;float range;AllCreaturesOfEntryInRangeCheck(Unit*b,unsigned e,float r):bot(b),entry(e),range(r){}
  bool operator()(Unit*u){return u->entry==entry&&bot->GetDistance(u)<=range;}};
 template<class C>struct UnitListSearcher{std::list<Unit*>&out;C&check;UnitListSearcher(std::list<Unit*>&o,C&c):out(o),check(c){}
  void Run(){for(auto*u:units)if(check(u))out.push_back(u);}};
}
namespace Cell{template<class S>void VisitAllObjects(Unit*,S&s,float){s.Run();}}
struct Event{};
namespace ai{
 bool ValidateEncounterDestination(PlayerbotAI*a,EncounterPosition&p){++a->checks;return a->valid&&p.active;}
 struct Action{virtual ~Action()=default;};
 struct MovementAction:Action{PlayerbotAI*ai;Player*bot;MovementAction(PlayerbotAI*a):ai(a),bot(a->bot){}
  bool MoveTo(unsigned m,float,float,float,bool idle,bool reaction,bool noPath,bool ignore){assert(m==bot->map&&!idle&&reaction&&!noPath&&ignore);++ai->moves;return true;}
  bool IsReaction(){return true;}void SetDuration(unsigned){}};
 struct CastSpellAction:Action{bool movement=false;bool HasMovementEffect(){return movement;}};
 struct MoveAwayFromHazard:MovementAction{using MovementAction::MovementAction;};
 struct AttackAction:MovementAction{using MovementAction::MovementAction;};
 struct RotatingBeamPositionValue{PlayerbotAI*ai;Player*bot;EncounterPosition Calculate();};
 struct RotatingBeamAction:MovementAction{using MovementAction::MovementAction;
  static bool GetPlan(PlayerbotAI*,EncounterPosition&,encounter::RotatingBeam&);bool isUseful();bool ShouldReactionInterruptCast()const;bool Execute(Event&);};
 struct PreserveRotatingBeamMultiplier{PlayerbotAI*ai;float GetValue(Action*);};
}
using namespace ai;
__METHODS__
int main(){
 using namespace encounter;
 RotatingBeam geometry;geometry.radius=100;geometry.halfAngle=.044f;geometry.sweep=.3f;
 assert(!OutsideRotatingBeam({20,0,0},geometry));assert(!OutsideRotatingBeam({20,4,0},geometry));
 assert(OutsideRotatingBeam({20,-10,0},geometry));assert(OutsideRotatingBeam({-20,0,0},geometry));
 assert(!RotatingBeamRouteSafe({20,-10,0},{{20,10,0}},geometry,7)); // Endpoints safe, crossing unsafe.
 assert(RotatingBeamRouteSafe({20,0,0},{{20,-10,0}},geometry,7)); // Escape existing danger.
 assert(!RotatingBeamRouteSafe({20,0,0},{{20,-10,0},{20,0,0}},geometry,7));
 assert(!RotatingBeamRouteSafe({20,-10,0},{},geometry,7));
 assert(!RotatingBeamRouteSafe({20,-10,0},{{20,-20,0}},geometry,0));
 geometry.sweep=-.3f;assert(!OutsideRotatingBeam({20,-4,0},geometry));assert(OutsideRotatingBeam({20,10,0},geometry));
 geometry.sweep=0;geometry.angularSpeed=.4f;
 assert(!RotatingBeamRouteSafe({10,10,0},{{10,20,0}},geometry,2)); // Beam catches slow route.
 assert(RotatingBeamRouteSafe({10,10,0},{{10,20,0}},geometry,20));
 geometry.orientation=2*M_PI_F;geometry.angularSpeed=0;assert(!OutsideRotatingBeam({20,0,0},geometry));
 geometry.halfAngle=-1;assert(!OutsideRotatingBeam({-20,0,0},geometry));
 for(bool lurker:{false,true}){
  Player bot;bot.guid=1;bot.x=20;bot.map=lurker?548:531;
  Unit boss;boss.entry=lurker?21217:15589;boss.map=bot.map;unsigned left=lurker?37429:26009,right=lurker?37430:26136,payload=lurker?37433:26029;
  boss.auras={left};spells[left].EffectAmplitude[0]=spells[right].EffectAmplitude[0]=lurker?200:1000;cones[payload].coneAngle=lurker?10:5;
  units={&boss};PlayerbotAI ai{&bot};RotatingBeamPositionValue value{&ai,&bot};RotatingBeamAction action(&ai);
  PreserveRotatingBeamMultiplier multiplier{&ai};MovementAction chase(&ai);AttackAction attack(&ai);MoveAwayFromHazard hazard(&ai);CastSpellAction heal,charge;charge.movement=true;
  Event event;EncounterPosition p;RotatingBeam beam;
  auto load=[&](){return ai.context.plan.data=value.Calculate();};
#ifdef MANGOSBOT_ZERO
  if(lurker){assert(!load().active&&!ReadRotatingBeam(&ai,&boss,p,beam));continue;}
#endif
  assert(ReadRotatingBeam(&ai,&boss,p,beam)&&beam.sweep>0);
  assert(std::fabs(beam.halfAngle-(lurker?5:2.5f)*M_PI_F/180)<.00001f);
  boss.auras={right};assert(ReadRotatingBeam(&ai,&boss,p,beam)&&beam.sweep<0);boss.auras={left,right};assert(!ReadRotatingBeam(&ai,&boss,p,beam));boss.auras={left};
  auto plan=load();assert(plan.active&&action.isUseful()&&action.ShouldReactionInterruptCast());
  bot.casting=true;assert(action.Execute(event)&&ai.moves==1&&ai.interrupts==1);
  bot.x=-20;load();bot.casting=true;bot.motion.kind=1;
  assert(action.isUseful()&&!action.ShouldReactionInterruptCast());assert(action.Execute(event)&&ai.stops==1&&ai.interrupts==1&&bot.casting);
  assert(!action.isUseful());assert(multiplier.GetValue(&chase)==0&&multiplier.GetValue(&attack)==0&&multiplier.GetValue(&charge)==0);
  assert(multiplier.GetValue(&heal)==1&&multiplier.GetValue(&hazard)==1);
  boss.auras.clear();assert(!action.Execute(event)&&multiplier.GetValue(&chase)==1);boss.auras={left};
  boss.ownAura=false;assert(!load().active);boss.ownAura=true;
  for(bool*flag:{&boss.alive,&boss.world,&boss.combat,&bot.alive,&bot.world,&bot.combat,&bot.group,&ai.dungeon}){*flag=false;assert(!load().active);*flag=true;}
  for(bool*flag:{&boss.charm,&bot.charm,&bot.teleport,&ai.real}){*flag=true;assert(!load().active);*flag=false;}
  boss.instance=2;assert(!load().active);boss.instance=1;
  load();bot.instance=2;assert(!action.Execute(event));bot.instance=1;
  Unit duplicate=boss;duplicate.guid=11;units.push_back(&duplicate);assert(!load().active);units.pop_back();
  radius=0;assert(!load().active);radius=100;spells[left].EffectAmplitude[0]=0;assert(!load().active);spells[left].EffectAmplitude[0]=lurker?200:1000;
  cones[payload].coneAngle=0;assert(!load().active);cones[payload].coneAngle=lurker?10:5;
  bot.x=20;ai.valid=false;ai.checks=0;assert(!load().active&&ai.checks<=4);ai.valid=true;
  pathComplete=false;paths=0;assert(!load().active&&paths<=4);pathComplete=true;
  if(lurker){bot.water=true;bot.deep=true;load();assert(!action.ShouldReactionInterruptCast());
   assert(ReadRotatingBeam(&ai,&boss,p,beam)&&beam.shelteredInWater);bot.deep=false;
   assert(ReadRotatingBeam(&ai,&boss,p,beam)&&!beam.shelteredInWater);load();assert(action.ShouldReactionInterruptCast());}
 }
 std::cout<<"PASS: native rotating beam direction, cone, route timing, phase/lifetime, holds and water exemption\n";
}
'''
code=code.replace('__GEOMETRY__',(base/'RotatingBeamGeometry.h').as_posix()).replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='rotating-beam-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
strategy=(base/'generic/DungeonStrategy.cpp').read_text()
for name in ('InitCombatTriggers','InitReactionTriggers'):
    assert 'new NextAction("avoid rotating beam", 108.0f)' in block(strategy,'void DungeonStrategy::'+name+'(')
for name in ('InitCombatMultipliers','InitReactionMultipliers'):
    assert 'new PreserveRotatingBeamMultiplier(ai)' in block(strategy,'void DungeonStrategy::'+name+'(')
for file,entry in (('actions/ActionContext.h','creators["avoid rotating beam"]'),
                   ('triggers/TriggerContext.h','creators["avoid rotating beam"]'),
                   ('values/ValueContext.h','creators["rotating beam position"]')):
    assert entry in (base/file).read_text()
