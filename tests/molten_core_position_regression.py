"""Exercise actual MC positioning/plan validation, including post-kill Living Bomb."""
from pathlib import Path
import subprocess,sys
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
value = (root/'playerbot/strategy/values/MoltenCorePositionValue.cpp').read_text()
action = (root/'playerbot/strategy/actions/MoltenCoreDungeonActions.cpp').read_text()
if '--before-mag' in sys.argv or '--before-fire-hold' in sys.argv:
 value=subprocess.check_output(['git','-C',str(root),'show','HEAD:playerbot/strategy/values/MoltenCorePositionValue.cpp'],text=True)
 oldAction=subprocess.check_output(['git','-C',str(root),'show','HEAD:playerbot/strategy/actions/MoltenCoreDungeonActions.cpp'],text=True)
 if '--before-mag' in sys.argv: action=oldAction
 else: action=action.replace(block(action,'bool MoltenCorePositionAction::Execute('),block(oldAction,'bool MoltenCorePositionAction::Execute('))
methods = '\n'.join((block(value, 'bool Casting('),
                     block(value, 'bool ai::MoltenCoreThreats('),
                     block(value, 'EncounterPosition MoltenCorePositionValue::Calculate('),
                     block(action, 'bool MoltenCorePositionAction::GetPlan('),
                     block(action, 'bool MoltenCorePositionAction::Execute(')))
code = r'''
#include <cassert>
#include <set>
#include <map>
#include <list>
#include <iostream>
#include "__GEOMETRY__"
using uint32=unsigned;
struct ObjectGuid {unsigned id=0;ObjectGuid(unsigned i=0):id(i){}operator unsigned()const{return id;}
 bool IsEmpty()const{return id==0;}};
enum CurrentSpellTypes {CURRENT_GENERIC_SPELL,CURRENT_CHANNELED_SPELL};
enum {CLASS_HUNTER=3,SPELL_STATE_CASTING,SPELL_STATE_FINISHED};
struct SpellEntry {unsigned Id=19695;};
struct Spell {SpellEntry* m_spellInfo=nullptr;int state=SPELL_STATE_CASTING;int getState()const{return state;}};
struct Map {};
struct Aura { unsigned stacks=0; unsigned GetStackAmount(){return stacks;} };
struct PlayerbotAI;
struct Unit {virtual ~Unit()=default;virtual bool IsPlayer(){return false;}bool charmed=false;bool HasCharmer(){return charmed;}
 unsigned entry=0,phase=1;ObjectGuid guid;bool world=true,alive=true,combat=true;Map* map=nullptr;
 bool visible=true;bool IsWithinLOS(float,float,float,bool){return visible;}float GetOrientation(){return 0;}float health=100; float GetHealthPercent(){return health;} float GetCombatReach(){return 1.5f;}
 float x=0,y=0,z=0;std::set<unsigned> auras;Unit* victim=nullptr;Spell* cast=nullptr;
 unsigned GetEntry(){return entry;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}
 bool IsInCombat(){return combat;}Map* GetMap(){return map;}ObjectGuid GetObjectGuid(){return guid;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 bool HasAura(unsigned id){return auras.count(id);}Unit* GetVictim(){return victim;}
 Spell* GetCurrentSpell(CurrentSpellTypes type){return type==CURRENT_GENERIC_SPELL?cast:nullptr;}
};
struct Group;
struct Spline{bool Finalized(){return true;}struct Point{float x=0,y=0,z=0;};Point FinalDestination(){return {};}};
struct Player:Unit {unsigned cls=8;unsigned getClass(){return cls;}bool tankRole=false;bool IsWithinLOSInMap(Unit*){return true;}float GetCollisionHeight(){return 2;}bool teleport=false;unsigned mapId=409,instance=1;Group* group=nullptr;
 Spline*movespline=nullptr;bool IsNonMeleeSpellCasted(bool,bool,bool){return false;}
 bool IsPlayer()override{return true;}
 PlayerbotAI* GetPlayerbotAI(){return nullptr;}
 float GetDistance(Unit* unit){return GetDistance(unit->x,unit->y,unit->z);}
 float GetDistance(float a,float b,float c){return std::sqrt((x-a)*(x-a)+(y-b)*(y-b)+(z-c)*(z-c));}
 bool HasCharmer(){return charmed;}bool IsBeingTeleported(){return teleport;}unsigned GetMapId(){return mapId;}
 unsigned GetInstanceId(){return instance;}Group* GetGroup(){return group;}
 bool IsInMap(Unit* other){return world&&other->world&&map==other->map&&phase==other->phase;}
};
struct GroupReference {Player* source=nullptr;GroupReference* following=nullptr;
 Player* getSource(){return source;}GroupReference* next(){return following;}};
struct Group {GroupReference* first=nullptr;GroupReference* GetFirstMember(){return first;}};
namespace ai {
 struct EncounterPosition {bool active=false;unsigned map=0,instance=0,spell=0;ObjectGuid boss,source;encounter::Point destination,anchor;bool anchored=false,groundOnly=false;};
}
struct WorldPosition {float x,y,z; float getX()const{return x;} float getY()const{return y;} float getZ()const{return z;}};
using HazardPosition=std::pair<WorldPosition,float>;
using namespace ai;
struct Facade{bool IsFriendlyTo(Player*,Unit*){return false;}}sServerFacade;
template<class T>struct Cached {T value;T Get(){return value;}void Reset(){value=T{};}void Set(T v){value=v;}};
struct Context {Cached<EncounterPosition> cached;Cached<ObjectGuid>current;Cached<std::list<ObjectGuid>> attackers;
 template<class T>Cached<T>* GetValue(const char*){if constexpr(std::is_same_v<T,EncounterPosition>)return &cached;else if constexpr(std::is_same_v<T,ObjectGuid>)return &current;else return &attackers;}};
struct PlayerbotAI {Player* bot=nullptr;Context context;std::list<ObjectGuid> attackers;std::map<unsigned,Unit*> units;
 Aura splash; bool tank=false; bool IsTank(Player*p){return p==bot?tank:p->tankRole;} bool IsRealPlayer(){return false;}
 Aura* GetAura(unsigned id,Player* p){return p->HasAura(id)?&splash:nullptr;}
 bool formation=false;bool GetSpellRange(const char*,float*r){*r=40;return true;}bool validPath=true,ranged=false,healer=false,canMove=true;unsigned checked=0,moves=0;bool CanMove(){return canMove;}
 unsigned stops=0;void StopMoving(){++stops;}
 Player* GetBot(){return bot;}Context* GetAiObjectContext(){return &context;}
 bool IsRanged(Player*){return ranged;}bool IsHeal(Player*){return healer;}
 Unit* GetUnit(ObjectGuid guid){auto it=units.find(guid);return it==units.end()?nullptr:it->second;}
};
namespace ai {
 std::list<HazardPosition> ground;
 void AppendMoltenCoreGroundHazards(PlayerbotAI*,std::list<HazardPosition>& hazards){hazards.insert(hazards.end(),ground.begin(),ground.end());}
 std::map<unsigned,float> radii{{20475,10.0f},{19698,10.0f},{20478,20.0f},{19712,10.0f},{20566,25.0f},{21154,1.0f},{21155,20.0f},{19497,15.0f},{20483,15.0f}};
 float NativeEncounterSpellRadius(unsigned id){return radii[id];} // controlled fixture, not replacement data
 bool ValidateEncounterDestination(PlayerbotAI* ai,EncounterPosition&,bool walking=true){++ai->checked;return ai->validPath;}
 struct MoltenCorePositionValue {Player* bot;PlayerbotAI* ai;EncounterPosition Calculate();};
 bool MoltenCoreThreats(PlayerbotAI*,EncounterPosition&,std::vector<encounter::Circle>&);
 // This fixture isolates the existing boss hazards; trash is checked separately.
 const char* MoltenCoreRangeSpell(PlayerbotAI*,Player*){return "frostbolt";}
 unsigned magmadarReplans=0;bool PlanMagmadarFormation(PlayerbotAI*,Unit*b,EncounterPosition& p){++magmadarReplans;p.destination={b->x-41,b->y,b->z};p.anchor={b->x,b->y,b->z};p.anchored=true;return true;}
 struct PossibleAttackTargetsValue{static bool HasBreakableCC(Unit*,Player*){return false;}static bool HasUnBreakableCC(Unit*,Player*){return false;}};
 bool MoltenCorePackStackRequired(PlayerbotAI*){return false;}std::pair<float,float> FirelordRangedBounds(PlayerbotAI*,Unit*){return {8.0f,43.0f};}
 unsigned firelordReplans=0;bool PlanFirelordRanged(PlayerbotAI*,EncounterPosition&){++firelordReplans;return false;}
 bool PlanMoltenCoreTrash(PlayerbotAI*a,EncounterPosition&p) {if(!a->formation)return false;Unit*b=a->GetUnit(1);p.active=true;p.map=a->bot->mapId;p.instance=a->bot->instance;p.spell=19272;p.boss=b->guid;p.destination={b->x-41,b->y,b->z};p.anchor={b->x,b->y,b->z};p.anchored=true;return a->validPath;}Unit*MoltenCorePackTankTarget(PlayerbotAI*){return nullptr;}Unit*MoltenCoreAssignedTankTarget(PlayerbotAI*){return nullptr;}
 Unit*LavaTrashBanishTarget(PlayerbotAI*){return nullptr;}bool PlanLavaTrashCarrier(PlayerbotAI*,EncounterPosition&){return false;}
 bool PlanMoltenCoreGiants(PlayerbotAI*,EncounterPosition&){return false;}bool MoltenCoreRecoveryTrash(unsigned){return true;}
 bool RagnarosSameCluster(PlayerbotAI*,Player*){return false;}
 bool PlanMajordomoFormation(PlayerbotAI*,EncounterPosition&){return false;}
bool PlanRagnarosFormation(PlayerbotAI*,EncounterPosition&){return false;}
 struct Event{};
 struct JumpAction {JumpAction(PlayerbotAI*){} void Qualify(const char*){} bool Execute(Event&){return false;}};
 struct MoltenCorePositionAction {PlayerbotAI* ai;Player*bot=ai->bot;static bool GetPlan(PlayerbotAI*,EncounterPosition&);bool Execute(Event&);
 bool ShouldReactionInterruptCast(){return true;}
 void SetDuration(unsigned){}
 bool IsReaction(){return true;}
 bool MoveTo(unsigned,float,float,float,bool idle,bool reaction,bool noPath,bool ignoreEnemies){assert(!idle&&reaction&&!noPath&&ignoreEnemies);++ai->moves;return true;}};
}
#define AI_VALUE(type,name) ai->attackers
bool PlanMoltenCoreMageCleave(PlayerbotAI*,EncounterPosition&){return false;}
__METHODS__
int main(){
 Player bot,other;Map map,otherMap;bot.map=other.map=&map;bot.guid=2;other.guid=3;other.x=1;
 Unit boss;boss.entry=12056;boss.guid=1;boss.map=&map;
 PlayerbotAI ai;ai.bot=&bot;ai.attackers={1};ai.units={{1,&boss},{2,&bot},{3,&other}};
 Group group;GroupReference member{&other};group.first=&member;bot.group=other.group=&group;
 MoltenCorePositionValue value{&bot,&ai};EncounterPosition resolved;
 auto get=[&](){ai.context.attackers.value=ai.attackers;ai.context.cached.value=value.Calculate();return MoltenCorePositionAction::GetPlan(&ai,resolved);};
 assert(!get()); // no actual danger
 bot.auras={20475};assert(get()&&resolved.spell==20475&&resolved.source==bot.guid);
 assert(encounter::Distance2d(resolved.destination,{other.x,0,0})>=12);
 MoltenCorePositionAction movement{&ai};Event event;assert(movement.Execute(event)&&ai.moves==1);
 const auto saved=resolved.destination;other.x=saved.x;other.y=saved.y;
 assert(!movement.Execute(event)&&ai.moves==1);other.x=1;other.y=0;
 other.teleport=true;assert(!movement.Execute(event));other.teleport=false;
 other.charmed=true;assert(!movement.Execute(event));other.charmed=false;
 Group foreign;other.group=&foreign;assert(!movement.Execute(event));other.group=&group;
 // Boss death/despawn and combat exit do not erase a still-ticking native bomb.
 boss.alive=false;boss.combat=false;bot.combat=false;ai.attackers.clear();
 assert(get());ai.units.erase(1);assert(get());
 bot.auras.clear();assert(!MoltenCorePositionAction::GetPlan(&ai,resolved));assert(!get());
 // A nearby human/other bot's remaining bomb is also respected out of combat.
 other.auras={20475};assert(get()&&resolved.source==other.guid);
 other.teleport=true;assert(!MoltenCorePositionAction::GetPlan(&ai,resolved)&&!get());other.teleport=false;
 other.group=&foreign;assert(!get());other.group=&group;
 other.phase=2;assert(!MoltenCorePositionAction::GetPlan(&ai,resolved));assert(!get());other.phase=1;
 other.map=&otherMap;assert(!get());other.map=&map;
 other.alive=false;assert(!get());other.alive=true;
 other.x=60;assert(!get());other.x=1;
 other.z=20;assert(!get());other.z=0;
 ai.validPath=false;ai.checked=0;assert(!get()&&ai.checked<=32);ai.validPath=true;
 bot.teleport=true;assert(!get());bot.teleport=false;
 bot.charmed=true;assert(!get());bot.charmed=false;
 bot.mapId=0;assert(!get());bot.mapId=409;
 assert(get());++bot.instance;assert(!MoltenCorePositionAction::GetPlan(&ai,resolved));--bot.instance;
 other.auras.clear();assert(!get());
 // Existing Inferno uses its native damage spell radius, including cast start.
 ai.units[1]=&boss;ai.attackers={1};boss.alive=boss.combat=bot.combat=true;boss.auras={19695};
 assert(get()&&encounter::Distance2d(resolved.destination,{0,0,0})>=12);
 boss.victim=&bot;ai.tank=false;assert(get()); // a hunter/caster victim must still leave Inferno
 ai.tank=true;assert(!get());ai.tank=false;boss.victim=nullptr; // only the actual tank anchors
 boss.auras.clear();SpellEntry info;Spell cast;cast.m_spellInfo=&info;boss.cast=&cast;
 assert(get());cast.state=SPELL_STATE_FINISHED;assert(!get());boss.cast=nullptr;
 cast.state=SPELL_STATE_CASTING;cast.m_spellInfo=nullptr;boss.cast=&cast;assert(!get());boss.cast=nullptr;
 boss.phase=2;boss.auras={19695};assert(!get());boss.phase=1;boss.auras.clear();
 // Shazzrah stays scoped to ranged/healer roles and excludes his current victim.
 boss.entry=12264;assert(!get());ai.ranged=true;assert(get());boss.victim=&bot;assert(!get());
 // Golemagg: melee retreat at five stacks, tanks hold, ranged need not retreat.
 boss.victim=nullptr;boss.entry=11988;ai.ranged=false;ai.splash.stacks=4;bot.auras={13880};assert(!get());
 ai.splash.stacks=5;assert(get());ai.tank=true;assert(!get());ai.tank=false;
 ai.ranged=true;assert(!get());ai.ranged=false;bot.auras.clear();assert(!get());
 // Ragnaros: ranged stay outside knockback, the current tank stays in melee.
 boss.entry=11502;ai.ranged=true;assert(get());boss.victim=&bot;assert(!get());boss.victim=nullptr;
 ai.ranged=false;assert(!get());info.Id=20566;cast.m_spellInfo=&info;boss.cast=&cast;assert(get());boss.cast=nullptr;
 // Firesworn: avoid a dying add, including our own tanked add, excluding a banished add.
 boss.entry=12057;Unit add;add.entry=12099;add.guid=4;add.map=&map;add.health=9;ai.units[4]=&add;ai.attackers={1,4};
 assert(get());add.victim=&bot;assert(get());add.victim=nullptr;add.auras={710};assert(!get());
 add.auras.clear();add.health=100;assert(!get());
 // The native submerged/immune phase must not send sons-phase melee away.
 boss.entry=11502;ai.attackers={1};ai.ranged=true;boss.auras={21107};assert(!get());
 boss.auras={21859};assert(!get());boss.auras.clear();assert(get());ai.ranged=false;
 // Actual ground areas, not the caster's location. No attacker/target dependency.
 boss.entry=12259;boss.x=40;ground={{{0,0,0},9}};assert(get());
 assert(encounter::Distance2d(resolved.destination,{0,0,0})>=10);
 ground.push_back({{resolved.destination.x,resolved.destination.y,0},9});
 assert(!movement.Execute(event)); // newly overlapping fire invalidates the queued endpoint
 assert(get());for(const auto& h:ground)assert(encounter::Distance2d(resolved.destination,{h.first.x,h.first.y,0})>=10);
 ai.tank=true;assert(get());ai.tank=false;ai.healer=true;assert(get());ai.healer=false;
 ai.attackers.clear();boss.alive=false;bot.combat=false;assert(get()&&resolved.boss.IsEmpty());
 ground.clear();assert(!MoltenCorePositionAction::GetPlan(&ai,resolved)&&!movement.Execute(event));
 assert(!get()); // no stale movement hold after the native area expires
 ground={{{0,0,0},9}};assert(get());ai.canMove=false;assert(!movement.Execute(event));ai.canMove=true;
 // Ground-fire escape stops holding immediately after reaching real clearance,
 // while the native area can remain live nearby. Native route admission still
 // rejects walking back through it.
 auto escaped=resolved.destination;bot.x=escaped.x;bot.y=escaped.y;
 assert(!MoltenCorePositionAction::GetPlan(&ai,resolved));assert(!get());bot.x=bot.y=0;
 ai.validPath=false;ai.checked=0;assert(!get()&&ai.checked<=32);ai.validPath=true;ground.clear();
 // A living low-health Firesworn must not kite its own holding tank.
 Unit firesworn;firesworn.entry=12099;firesworn.guid=7;firesworn.map=&map;firesworn.health=25;firesworn.victim=&bot;
 ai.units[7]=&firesworn;ai.attackers={7};ai.tank=true;assert(!get());
 ai.tank=false;assert(get());ai.tank=true;firesworn.victim=&other;assert(get());
 firesworn.victim=&bot;SpellEntry eruption;eruption.Id=20483;Spell massive;massive.m_spellInfo=&eruption;firesworn.cast=&massive;assert(get());
 firesworn.cast=nullptr;firesworn.auras={710};ai.tank=false;assert(!get());
 // A fear-induced facing change invalidates a cached Magmadar front station
 // before the ordinary two-second position-value refresh.
 firesworn.auras.clear();boss.alive=boss.combat=bot.combat=true;boss.entry=11982;boss.x=0;
 ai.context.cached.value.active=true;ai.context.cached.value.map=409;ai.context.cached.value.instance=1;
 ai.context.cached.value.boss=boss.guid;ai.context.cached.value.spell=19272;ai.context.cached.value.destination={30,0,0};
 assert(MoltenCorePositionAction::GetPlan(&ai,resolved)&&magmadarReplans==1&&resolved.destination.x==-41);

 // Cached max-range station follows a boss relocation once, without per-frame replanning.
 ai.ranged=true;ai.context.cached.value=resolved;boss.x=4;
 assert(MoltenCorePositionAction::GetPlan(&ai,resolved)&&magmadarReplans==2&&resolved.destination.x==-37);
 assert(MoltenCorePositionAction::GetPlan(&ai,resolved)&&magmadarReplans==2);
 // A wall/ledge fallback can stay closer than maximum without being discarded every frame.
 ai.context.cached.value.destination.x=boss.x-37;assert(MoltenCorePositionAction::GetPlan(&ai,resolved)&&magmadarReplans==2);
 // Ground-fire approach band cannot manufacture an idle hold that blocks safe formation.
 boss.x=0;boss.victim=&other;other.tankRole=true;bot.x=bot.y=0;ai.tank=false;ai.formation=true;
 ground={{{8,0,0},5}};ai.attackers={1};assert(get()&&resolved.spell==19272&&resolved.destination.x==-41);
 auto beforeMoves=ai.moves;assert(movement.Execute(event)&&ai.moves==beforeMoves+1);
 // An actual fire overlap can use the same admitted clear route; native control still wins.
 ground={{{0,0,0},9}};assert(get()&&resolved.spell==19272&&resolved.destination.x==-41);
 assert(movement.Execute(event));ai.canMove=false;assert(!movement.Execute(event));ai.canMove=true;
 boss.entry=12101;assert(get()&&resolved.spell==19272);assert(movement.Execute(event)); // safe mandatory Surger stack also survives nearby fire
 boss.entry=11982;
 // A formation endpoint covered by another flame remains rejected in favor of escape.
 ground.push_back({{-41,0,0},9});assert(get()&&resolved.spell!=19272&&encounter::OutsideCircles(resolved.destination,{{{0,0,0},10},{{-41,0,0},10}}));
 ai.formation=false;ground={{{8,0,0},5}};bot.x=bot.y=0;
 assert(!get()); // ordinary safe melee/caster station is not an exclusive fire hold
 std::cout<<"PASS: actual MC bomb lifetime after boss death, friendly carriers, phase/map/role, native radius and bounded paths\n";
}
'''.replace('__GEOMETRY__',(root/'playerbot/strategy/EncounterGeometry.h').as_posix()).replace('__METHODS__',methods)
for expansion in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-mc-position-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{expansion}',
                        'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
strategy=(root/'playerbot/strategy/generic/MoltenCoreDungeonStrategies.cpp').read_text()
assert 'molten core safe position' in block(strategy,'void MoltenCoreDungeonStrategy::InitNonCombatTriggers(')
assert 'PreserveMoltenCorePositionMultiplier' in block(strategy,'void MoltenCoreDungeonStrategy::InitNonCombatMultipliers(')
