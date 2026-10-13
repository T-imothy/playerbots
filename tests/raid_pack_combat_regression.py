"""Run the actual raid AoE, pet-autocast and moving-fire admission bodies."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block
r = Path(__file__).resolve().parents[1]
aoe=(r/'playerbot/strategy/values/AoeValues.cpp').read_text()
policy=(r/'playerbot/strategy/MoltenCoreTrashPolicy.h').read_text()
pet=(r/'playerbot/RaidPetPolicy.h').read_text()
update=(r/'playerbot/PlayerbotAI.cpp').read_text()
fire=(r/'playerbot/strategy/values/MoltenCorePositionValue.cpp').read_text()
safety=(r/'playerbot/strategy/actions/MovementPathSafety.h').read_text()
methods='\n'.join(('namespace ai {\n'+block(pet,'inline bool RaidPetThreatSpell(')+'\n'+block(pet,'inline bool RaidPetThreatBlocked(')+'\n'+block(policy,'inline bool MoltenCoreImpAoeOpening(')+'\n}',
 block(aoe,'bool ai::ControlledRaidAoe('),block(update,'void PlayerbotAI::UpdateRaidPetThreat('),
 block(safety,'inline bool IsFiniteMovementPoint('),block(safety,'inline bool IsHazardSafeSegment('),
 block(fire,'bool ai::StopMoltenCoreUnsafeTravel(')))
code=r'''
#include <cassert>
#include <cmath>
#include <algorithm>
#include <list>
#include <map>
#include <set>
#include <vector>
#include <string>
#include <ctime>
#include <iostream>
using uint32=unsigned;using ObjectGuid=unsigned;
enum{CLASS_WARRIOR=1,CLASS_MAGE=8,MAX_EFFECT_INDEX=3,SPELL_EFFECT_ATTACK_ME=1,SPELL_EFFECT_APPLY_AURA,SPELL_AURA_MOD_TAUNT,SPELL_EFFECT_THREAT};
struct SpellEntry{unsigned Effect[3]={},EffectApplyAuraName[3]={};int EffectBasePoints[3]={};};
struct Map{bool raid=true;bool IsRaid(){return raid;}};
struct Group{bool raid=true;bool IsRaidGroup(){return raid;}};
struct Unit{virtual ~Unit()=default;virtual bool IsPlayer(){return false;}unsigned entry=0;unsigned GetEntry(){return entry;}
 bool world=true,alive=true,combat=true,charmed=false,cc=false,hardCC=false,friendly=false;unsigned instance=1;float x=0,y=0,z=0;
 Unit*victim=nullptr;bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}float GetCombatReach(){return 1.5f;}Unit*GetVictim(){return victim;}};
struct Charm{unsigned number=1;unsigned GetPetNumber(){return number;}};
struct Pet:Unit{ObjectGuid guid=2;Charm charm;std::vector<unsigned>m_autospells;std::set<unsigned>known;unsigned writes=0;
 ObjectGuid GetObjectGuid(){return guid;}ObjectGuid GetMasterGuid(){return 1;}Charm*GetCharmInfo(){return &charm;}
 bool HasSpell(unsigned id){return known.count(id);}void ToggleAutocast(unsigned id,bool on){++writes;
 m_autospells.erase(std::remove(m_autospells.begin(),m_autospells.end(),id),m_autospells.end());if(on)m_autospells.push_back(id);}};
struct Spline{bool done=false;struct Point{float x=10,y=0,z=0;}destination;bool Finalized(){return done;}Point CurrentDestination(){return destination;}};
struct Player:Unit{bool teleport=false,tank=false,healer=false,flying=false,transport=false;unsigned mapId=409,cls=CLASS_MAGE;Map map;Group*group=nullptr;Pet*pet=nullptr;Spline*movespline=nullptr;
 unsigned getClass(){return cls;}
 bool IsPlayer()override{return true;}bool IsBeingTeleported(){return teleport;}Map*GetMap(){return &map;}Group*GetGroup(){return group;}
 bool IsInMap(Unit*u){return u&&world&&u->world&&instance==u->instance;}ObjectGuid GetObjectGuid(){return 1;}unsigned GetMapId(){return mapId;}
 Pet*GetPet(){return pet;}bool GetTransport(){return transport;}bool IsFreeFlying(){return flying;}};
struct WorldLocation{float coord_x=0,coord_y=0,coord_z=0;};
struct WorldPosition{unsigned map;float x,y,z;WorldPosition(unsigned m,float a,float b,float c):map(m),x(a),y(b),z(c){}
 WorldPosition(Player*p):map(p->GetMapId()),x(p->x),y(p->y),z(p->z){}unsigned getMapId()const{return map;}
 float distance(const WorldPosition&p)const{return std::hypot(x-p.x,y-p.y);}
 float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}};
using HazardPosition=std::pair<WorldPosition,float>;
template<class T>struct Cached{T value;unsigned resets=0;T Get(){return value;}void Reset(){++resets;}};
struct Context{Cached<WorldLocation>center;Cached<std::list<ObjectGuid>>possible;Cached<std::list<HazardPosition>>hazards;Cached<int>position;
 template<class T>Cached<T>*GetValue(const char*){if constexpr(std::is_same_v<T,WorldLocation>)return &center;
 else if constexpr(std::is_same_v<T,std::list<ObjectGuid>>)return &possible;else if constexpr(std::is_same_v<T,std::list<HazardPosition>>)return &hazards;else return &position;}};
struct PlayerbotAI{Player*bot;Context context;bool movable=true;bool CanMove(){return movable;}bool real=false;unsigned stops=0,wakes=0;time_t start=time(0)-5;ObjectGuid raidPetGuid=0;unsigned raidPetNumber=0;std::set<unsigned>raidPetSuppressedSpells;
 std::map<ObjectGuid,Unit*>units;Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool IsHeal(Player*p){return p->healer;}bool IsTank(Player*p){return p->tank;}
 time_t GetCombatStartTime(){return start;}float GetRange(const char*){return 40;}Context*GetAiObjectContext(){return &context;}
 Unit*GetUnit(ObjectGuid id){return units.count(id)?units[id]:nullptr;}void StopMoving(){++stops;}void PrepareForUrgentHazard(){++wakes;}void UpdateRaidPetThreat();};
struct Facade{std::map<unsigned,SpellEntry>spells;bool IsFriendlyTo(Player*,Unit*u){return u->friendly;}
 const SpellEntry*LookupSpellInfo(unsigned id){auto i=spells.find(id);return i==spells.end()?nullptr:&i->second;}}sServerFacade;
namespace ai{ Unit* MoltenCoreNukeTarget(PlayerbotAI*){return nullptr;} bool MoltenCoreBossBurn(PlayerbotAI*){return false;}
 struct PossibleAttackTargetsValue{static bool HasBreakableCC(Unit*u,Player*){return u->cc;}static bool HasUnBreakableCC(Unit*u,Player*){return u->hardCC;}};
 struct EncounterPosition{};
 bool ControlledRaidAoe(PlayerbotAI*);bool StopMoltenCoreUnsafeTravel(PlayerbotAI*);
 std::list<HazardPosition>liveFire;
 void AppendMoltenCoreGroundHazards(PlayerbotAI*,std::list<HazardPosition>&out){out=liveFire;}
}
using namespace ai;
__METHODS__
int main(){
 Player bot,tank;Group group;bot.group=tank.group=&group;tank.tank=true;PlayerbotAI ai{&bot};
 Unit one,two,three,nearby;one.victim=two.victim=three.victim=&tank;one.x=-1;two.x=1;three.y=2;
 ai.units={{2,&one},{3,&two},{4,&three},{5,&nearby}};ai.context.possible.value={2,3,4};
 // Only DPS warriors admit a pair; one target, caster pairs and tank pairs
 // retain their existing behavior. All CC and tank-control guards still apply.
 ai.context.possible.value={2,3};assert(!ControlledRaidAoe(&ai));
 bot.cls=CLASS_WARRIOR;assert(ControlledRaidAoe(&ai));
 // The caster's cluster can be distant or stale; Whirlwind counts around the
 // warrior and protects CC/unpulled neighbours around that actual origin.
 bot.x=30;ai.context.center.value.coord_x=0;assert(!ControlledRaidAoe(&ai));
 one.x=29;two.x=31;assert(ControlledRaidAoe(&ai));
 nearby.x=20;nearby.cc=true;ai.context.possible.value.push_back(5);assert(!ControlledRaidAoe(&ai));
 nearby.cc=false;nearby.combat=false;assert(!ControlledRaidAoe(&ai));
 ai.context.possible.value={2,3};nearby.combat=true;bot.x=0;one.x=-1;two.x=1;
 two.x=9;assert(!ControlledRaidAoe(&ai));two.x=1;
 ai.context.possible.value={2};assert(!ControlledRaidAoe(&ai));ai.context.possible.value={2,3};
 bot.tank=true;assert(!ControlledRaidAoe(&ai));bot.tank=false;
 two.cc=true;assert(!ControlledRaidAoe(&ai));two.cc=false;
 two.hardCC=true;assert(!ControlledRaidAoe(&ai));two.hardCC=false;
 two.combat=false;assert(!ControlledRaidAoe(&ai));two.combat=true;
 two.victim=&bot;assert(!ControlledRaidAoe(&ai));two.victim=&tank;
 bot.cls=CLASS_MAGE;ai.context.possible.value={2,3,4};
 assert(ControlledRaidAoe(&ai));tank.tank=false;assert(!ControlledRaidAoe(&ai));tank.tank=true;
 one.entry=11669;assert(!ControlledRaidAoe(&ai));bot.tank=true;assert(ControlledRaidAoe(&ai));bot.tank=false;
 ai.start=time(0)-10;assert(ControlledRaidAoe(&ai));one.entry=0;ai.start=time(0)-5;
 three.victim=&bot;assert(!ControlledRaidAoe(&ai));three.victim=&tank;
 nearby.x=11;nearby.cc=true;ai.context.possible.value.push_back(5);assert(!ControlledRaidAoe(&ai));
 nearby.cc=false;nearby.combat=false;assert(!ControlledRaidAoe(&ai));nearby.x=50;assert(ControlledRaidAoe(&ai));
 bot.healer=true;assert(!ControlledRaidAoe(&ai));bot.healer=false;bot.map.raid=false;assert(!ControlledRaidAoe(&ai));bot.map.raid=true;
 bot.teleport=true;assert(!ControlledRaidAoe(&ai));bot.teleport=false;ai.context.center.value.coord_x=60;assert(!ControlledRaidAoe(&ai));ai.context.center.value={};
 ai.start=time(0);assert(!ControlledRaidAoe(&ai));ai.start=time(0)-5;
 SpellEntry growl,cower,taunt;growl.Effect[0]=cower.Effect[0]=SPELL_EFFECT_THREAT;growl.EffectBasePoints[0]=49;cower.EffectBasePoints[0]=-49;
 taunt.Effect[1]=SPELL_EFFECT_APPLY_AURA;taunt.EffectApplyAuraName[1]=SPELL_AURA_MOD_TAUNT;
 assert(RaidPetThreatSpell(&growl)&&RaidPetThreatSpell(&taunt)&&!RaidPetThreatSpell(&cower)&&!RaidPetThreatSpell(nullptr));
 Pet pet;bot.pet=&pet;pet.known={10,11,12};pet.m_autospells={10,11};sServerFacade.spells={{10,growl},{11,cower},{12,taunt}};
 ai.UpdateRaidPetThreat();assert(pet.m_autospells==std::vector<unsigned>{11});assert(ai.raidPetSuppressedSpells.count(10));
 unsigned writes=pet.writes;ai.UpdateRaidPetThreat();assert(pet.writes==writes);assert(RaidPetThreatBlocked(&ai,&growl));
 pet.guid=3;ai.UpdateRaidPetThreat();assert(ai.raidPetSuppressedSpells.count(10)); // same persistent pet, new summon GUID
 bot.map.raid=false;group.raid=false;ai.UpdateRaidPetThreat();assert(std::find(pet.m_autospells.begin(),pet.m_autospells.end(),10)!=pet.m_autospells.end());
 assert(std::find(pet.m_autospells.begin(),pet.m_autospells.end(),12)==pet.m_autospells.end()); // originally disabled stays disabled
 assert(!RaidPetThreatBlocked(&ai,&growl));bot.map.raid=true;ai.real=true;assert(!RaidPetThreatBlocked(&ai,&growl));ai.real=false;
 Spline spline;bot.movespline=&spline;bot.x=-10;assert(!StopMoltenCoreUnsafeTravel(&ai));
 liveFire={{{409,0,0,0},3}};assert(StopMoltenCoreUnsafeTravel(&ai)&&ai.stops==1);assert(ai.context.hazards.resets==1&&ai.context.position.resets==1);
 bot.x=1;spline.destination.x=10;assert(StopMoltenCoreUnsafeTravel(&ai)&&ai.wakes==1&&ai.stops==1); // wake stationary casts without stopping an outward spline
 spline.destination.x=-10;assert(StopMoltenCoreUnsafeTravel(&ai)&&ai.stops==2);ai.movable=false;assert(!StopMoltenCoreUnsafeTravel(&ai));ai.movable=true;bot.transport=true;assert(!StopMoltenCoreUnsafeTravel(&ai));bot.transport=false;
 bot.teleport=true;assert(!StopMoltenCoreUnsafeTravel(&ai));bot.teleport=false;spline.done=true;assert(StopMoltenCoreUnsafeTravel(&ai));bot.x=10;assert(!StopMoltenCoreUnsafeTravel(&ai));
 std::cout<<"PASS: self-centred two-target DPS Whirlwind, tank-controlled raid AoE, CC/unpulled exclusion, pet taunt suppression/restoration and newly spawned fire on active splines\n";
}
'''.replace('__METHODS__',methods).replace('GetValue<EncounterPosition>', 'GetValue<int>')
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='raid-pack-') as folder:
  d=Path(folder);(d/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=d,check=True)
  subprocess.run([str(d/'test.exe')],cwd=d,check=True)
