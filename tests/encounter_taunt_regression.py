"""Actual Ebonroc policy, generic lose-aggro trigger and native RD recipient.

Native threat/casts remain mocked; no raid clear or taunt hit is implied.
"""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
policy=(root/'playerbot/strategy/actions/EncounterTauntPolicy.cpp').read_text()
policy='\n'.join(line for line in policy.splitlines() if not line.startswith('#include'))
trigger=block((root/'playerbot/strategy/triggers/GenericTriggers.cpp').read_text(),'bool LoseAggroTrigger::IsActive(')
target=block((root/'playerbot/strategy/values/RighteousDefenseTargetValue.cpp').read_text(),'Unit* RighteousDefenseTargetValue::Calculate(')
code=r'''
#include <cassert>
#include <iostream>
#include <map>
#include <set>
#include <string>
using uint32=unsigned;
enum{MAX_EFFECT_INDEX=3,SPELL_EFFECT_ATTACK_ME=114,SPELL_EFFECT_APPLY_AURA=6,SPELL_AURA_MOD_TAUNT=11};
struct ObjectGuid{unsigned id=0;ObjectGuid(unsigned v=0):id(v){}operator unsigned()const{return id;}};
struct SpellEntry{unsigned Effect[3]={114,6,0},EffectApplyAuraName[3]={0,11,0};};
struct Map{bool regular=true;bool IsRegularDifficulty(){return regular;}};
struct Player;struct PlayerbotAI;
struct GroupReference{Player* member;GroupReference* following=nullptr;Player*getSource(){return member;}GroupReference*next(){return following;}};
struct Group{GroupReference*first=nullptr;GroupReference*GetFirstMember(){return first;}};
struct SpellAuraHolder{unsigned stacks=1;unsigned GetStackAmount()const{return stacks;}};
struct Unit{virtual ~Unit()=default;Map* map=nullptr;unsigned mapId=469,entry=14601,phase=1;ObjectGuid guid;
 bool world=true,alive=true,combat=true,charmed=false,player=false;Unit* victim=nullptr;std::set<Unit*> attackers;
 std::set<unsigned> auras;std::map<unsigned,unsigned> auraOwners;SpellAuraHolder holder;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}
 bool HasCharmer(){return charmed;}bool IsPlayer(){return player;}unsigned GetEntry(){return entry;}Unit* GetVictim(){return victim;}
 bool IsInMap(Unit* u){return u&&world&&u->world&&map==u->map&&phase==u->phase;}unsigned GetMapId(){return mapId;}
 Map* GetMap(){return map;}ObjectGuid GetObjectGuid(){return guid;}bool HasAura(unsigned id){return auras.count(id);}
 SpellAuraHolder* GetSpellAuraHolder(unsigned id,ObjectGuid owner){return HasAura(id)&&auraOwners[id]==owner?&holder:nullptr;}
 const auto& getAttackers(){return attackers;}};
struct Session{bool logout=false;bool isLogingOut(){return logout;}};
struct Player:Unit{Group* group=nullptr;bool teleport=false,tank=true,assist=true,hasSession=true,ready=true,melee=true;Session session;PlayerbotAI*ai=nullptr;std::set<unsigned>spells{355};
 Player(){player=true;}bool IsBeingTeleported(){return teleport;}Group* GetGroup(){return group;}
 bool HasSpell(unsigned id){return spells.count(id);}bool IsSpellReady(unsigned){return ready;}PlayerbotAI*GetPlayerbotAI(){return ai;}bool CanReachWithMeleeAttack(Unit*){return melee;}
 Session* GetSession(){return hasSession?&session:nullptr;}bool CanAssistSpell(Unit*,const SpellEntry*){return assist;}};
struct PlayerbotAI{Player* bot;Unit* target=nullptr;bool aggro=false,real=false;Player* GetBot(){return bot;}bool IsTank(Player* p){return p->tank;}bool IsRealPlayer(){return real;}};
struct Facade{SpellEntry spell;bool found=true;const SpellEntry* LookupSpellInfo(unsigned id){assert(id==31789);return found?&spell:nullptr;}}sServerFacade;
namespace ai{
 bool ShouldSwapEncounterTank(PlayerbotAI*,Unit*);bool ShouldAvoidEncounterTaunt(PlayerbotAI*,const SpellEntry*,Unit*);
 struct LoseAggroTrigger{PlayerbotAI* ai;Player* bot;bool IsActive();};
 struct RighteousDefenseTargetValue{PlayerbotAI* ai;Player* bot;Unit* Calculate();};
}
using namespace ai;
__POLICY__
#define AI_VALUE2(type,key,qualifier) ai->aggro
#define AI_VALUE(type,key) ai->target
__TRIGGER__
__TARGET__
int main(){
 Map map,otherMap;Group group,otherGroup;Player bot,tank,healer;Unit boss;boss.guid=1;bot.guid=2;tank.guid=3;healer.guid=4;
 bot.map=tank.map=healer.map=boss.map=&map;bot.group=tank.group=healer.group=&group;healer.tank=false;
 boss.victim=&tank;PlayerbotAI ai{&bot,&boss};LoseAggroTrigger trigger{&ai,&bot};RighteousDefenseTargetValue target{&ai,&bot};
 bot.ai=&ai;GroupReference botRef{&bot};group.first=&botRef;
 SpellEntry taunt,damage;damage.Effect[0]=2;damage.Effect[1]=0;
 assert(!trigger.IsActive()&&!ShouldSwapEncounterTank(&ai,&boss)&&ShouldAvoidEncounterTaunt(&ai,&taunt,&boss));
 assert(!ShouldAvoidEncounterTaunt(&ai,&damage,&boss)&&!ShouldAvoidEncounterTaunt(&ai,nullptr,&boss));
 tank.auras.insert(23340);tank.auraOwners[23340]=boss.guid;
 assert(trigger.IsActive()&&ShouldSwapEncounterTank(&ai,&boss)&&!ShouldAvoidEncounterTaunt(&ai,&taunt,&boss));
 // Another tank's taunt changes the victim before queued dispatch: reject a
 // second taunt without fabricating threat or changing either player's aura.
 boss.victim=&bot;assert(!ShouldSwapEncounterTank(&ai,&boss)&&ShouldAvoidEncounterTaunt(&ai,&taunt,&boss));boss.victim=&tank;
 bot.auras.insert(23340);assert(!trigger.IsActive()&&ShouldAvoidEncounterTaunt(&ai,&taunt,&boss));bot.auras.clear();
 tank.auraOwners[23340]=999;assert(!trigger.IsActive());tank.auraOwners[23340]=1;
 tank.group=&otherGroup;assert(!ShouldSwapEncounterTank(&ai,&boss));tank.group=&group;
 tank.teleport=true;assert(!ShouldSwapEncounterTank(&ai,&boss));tank.teleport=false;
 tank.phase=2;assert(!ShouldSwapEncounterTank(&ai,&boss));tank.phase=1;tank.alive=false;assert(!ShouldSwapEncounterTank(&ai,&boss));tank.alive=true;
 boss.entry=11982;assert(!ShouldSwapEncounterTank(&ai,&boss)&&!ShouldAvoidEncounterTaunt(&ai,&taunt,&boss));boss.entry=14601;
 bot.mapId=533;assert(!ShouldSwapEncounterTank(&ai,&boss));bot.mapId=469;
 boss.world=false;assert(!ShouldSwapEncounterTank(&ai,&boss));boss.world=true;boss.charmed=true;assert(!ShouldSwapEncounterTank(&ai,&boss));boss.charmed=false;
 boss.combat=false;assert(!ShouldSwapEncounterTank(&ai,&boss));boss.combat=true;bot.teleport=true;assert(!ShouldSwapEncounterTank(&ai,&boss));bot.teleport=false;
 bot.charmed=true;assert(!ShouldSwapEncounterTank(&ai,&boss));bot.charmed=false;bot.tank=false;assert(!ShouldSwapEncounterTank(&ai,&boss));bot.tank=true;
 boss.victim=&healer;assert(trigger.IsActive()&&!ShouldAvoidEncounterTaunt(&ai,&taunt,&boss)); // ordinary rescue preserved
 ai.aggro=true;assert(!trigger.IsActive());ai.aggro=false;
 healer.attackers.insert(&boss);
#ifdef MANGOSBOT_ZERO
 assert(!target.Calculate());
#else
 assert(target.Calculate()==&healer&&target.Calculate()!=&boss);
 healer.attackers.clear();assert(!target.Calculate());healer.attackers.insert(&boss);
 healer.group=&otherGroup;assert(!target.Calculate());healer.group=&group;
 healer.teleport=true;assert(!target.Calculate());healer.teleport=false;
 healer.charmed=true;assert(!target.Calculate());healer.charmed=false;
 healer.phase=2;assert(!target.Calculate());healer.phase=1;
 healer.session.logout=true;assert(!target.Calculate());healer.session.logout=false;
 healer.hasSession=false;assert(!target.Calculate());healer.hasSession=true;
 bot.assist=false;assert(!target.Calculate());bot.assist=true;
 sServerFacade.found=false;assert(!target.Calculate());sServerFacade.found=true;
 boss.victim=&bot;assert(!target.Calculate());boss.victim=&tank;tank.attackers.insert(&boss);
 assert(target.Calculate()==&tank);tank.auras.clear();assert(!target.Calculate()); // healthy tank not stolen
 boss.victim=&healer;bot.tank=false;assert(!target.Calculate());bot.tank=true;
 boss.alive=false;assert(!target.Calculate());boss.alive=true;
 ai.target=nullptr;assert(!target.Calculate());ai.target=&boss;boss.map=&otherMap;assert(!target.Calculate());boss.map=&map;
 boss.player=true;assert(!target.Calculate());boss.player=false;
#endif
 // All additions exercise the actual table and dispatch gate. Thresholds are
 // tactical choices; aura/phase/source/difficulty matching is native data.
 boss.player=false;boss.victim=&tank;tank.auras.clear();tank.auraOwners.clear();
 auto checkRule=[&](unsigned mapId,unsigned entry,unsigned aura,unsigned threshold,unsigned phaseAura=0){
  bot.mapId=mapId;boss.entry=entry;boss.auras.clear();tank.auras={aura};tank.auraOwners[aura]=boss.guid;
  tank.holder.stacks=threshold;boss.auras.insert(phaseAura);
  assert(ShouldSwapEncounterTank(&ai,&boss));
  assert(!ShouldAvoidEncounterTaunt(&ai,&taunt,&boss));
  if(threshold>1){tank.holder.stacks=threshold-1;assert(!ShouldSwapEncounterTank(&ai,&boss));tank.holder.stacks=threshold;}
  tank.auraOwners[aura]=999;assert(!ShouldSwapEncounterTank(&ai,&boss));tank.auraOwners[aura]=boss.guid;
  bot.auras.insert(aura);assert(!ShouldSwapEncounterTank(&ai,&boss));bot.auras.clear();
  if(phaseAura){boss.auras.clear();assert(!ShouldSwapEncounterTank(&ai,&boss));boss.auras.insert(phaseAura);}
  bot.ready=false;assert(!ShouldSwapEncounterTank(&ai,&boss));bot.ready=true;
  bot.melee=false;assert(!ShouldSwapEncounterTank(&ai,&boss));bot.melee=true;
  bot.spells.clear();assert(!ShouldSwapEncounterTank(&ai,&boss));bot.spells.insert(355);
  ai.real=true;assert(!ShouldSwapEncounterTank(&ai,&boss));ai.real=false;
  boss.victim=&bot;assert(!ShouldSwapEncounterTank(&ai,&boss)&&ShouldAvoidEncounterTaunt(&ai,&taunt,&boss));boss.victim=&tank;
 };
 checkRule(469,14601,23340,1);
 checkRule(509,15348,25646,3);checkRule(531,15510,25646,3);
#ifdef MANGOSBOT_TWO
 checkRule(533,15932,54378,3);
 checkRule(603,32865,62130,1);checkRule(603,32871,64412,4);
 checkRule(603,32930,63355,1);map.regular=false;checkRule(603,32930,64002,2);map.regular=true;
 for(unsigned aura:{66331u,67477u,67478u,67479u})checkRule(649,34796,aura,2);
 checkRule(631,37813,72410,1);
 for(unsigned aura:{72219u,72551u,72552u,72553u})checkRule(631,36626,aura,8);
#else
 checkRule(533,15932,25646,3);
 bot.mapId=631;boss.entry=36626;TankSwapRule missing;assert(!EncounterTankRule(&bot,&boss,missing));
#endif
#ifndef MANGOSBOT_ZERO
 checkRule(568,23576,42389,1,42377);
#else
 bot.mapId=568;boss.entry=23576;TankSwapRule noZa;assert(!EncounterTankRule(&bot,&boss,noZa));
#endif
 checkRule(469,14601,23340,1);
 Player spare;PlayerbotAI spareAi{&spare,&boss};spare.ai=&spareAi;spare.map=&map;spare.group=&group;spare.guid=1;
 GroupReference spareRef{&spare,&botRef};group.first=&spareRef;
 assert(!ShouldSwapEncounterTank(&ai,&boss)&&ShouldSwapEncounterTank(&spareAi,&boss));
 spare.ready=false;assert(ShouldSwapEncounterTank(&ai,&boss));spare.ready=true;
 spareAi.real=true;assert(ShouldSwapEncounterTank(&ai,&boss));spareAi.real=false;
 spare.teleport=true;assert(ShouldSwapEncounterTank(&ai,&boss));spare.teleport=false;
 spare.auras.insert(23340);assert(ShouldSwapEncounterTank(&ai,&boss));spare.auras.clear();
 spare.alive=false;assert(ShouldSwapEncounterTank(&ai,&boss));spare.alive=true;
 group.first=&botRef;
 std::cout<<"PASS: actual Ebonroc swap/dispatch policy and Righteous Defense friendly recipient/lifecycle across eras\n";
}
'''.replace('__POLICY__',policy).replace('__TRIGGER__',trigger).replace('__TARGET__',target)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-encounter-taunt-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
for era in ('classic','tbc','wotlk'):
    core=root.parent/f'mangos-{era}-behavior'
    native=(core/'src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/blackwing_lair/boss_ebonroc.cpp').read_text()
    assert 'SPELL_SHADOW_OF_EBONROC' in native and '23340' in native and 'm_creature->GetVictim()' in native
    if era!='classic':
        paladin=(core/'src/game/Spells/Scripts/Scripting/ClassScripts/Paladin.cpp').read_text()
        rd=block(paladin,'struct RighteousDefense')
        assert 'unitTarget->getAttackers()' in rd and '31790' in rd and 'size_t(3)' in rd
generic=(root/'playerbot/strategy/actions/GenericSpellActions.cpp').read_text()
for method in ('bool CastSpellAction::isUseful(','bool CastSpellAction::Execute('):
    assert 'ShouldAvoidEncounterTaunt' in block(generic,method)
action=block((root/'playerbot/strategy/paladin/PaladinActions.h').read_text(),'class CastRighteousDefenseAction')
assert '"righteous defense target"' in action and 'GetTarget() && CastSpellAction::Execute(event)' in action
prereq=block(generic,'NextAction** CastSpellAction::getPrerequisites(')
assert 'GetTargetName()' in prereq and 'spellName, targetName' in prereq
print('PASS: native class/encounter contracts and shared cast/recipient/reach wiring; live taunt outcomes still native')
