"""Execute production damage-pause helpers and Wrath pet admission with native-shaped fixtures.

This is a deterministic policy/lifecycle test, not a live encounter clear.
"""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
source = (root/'playerbot/strategy/actions/EncounterDamagePolicy.cpp').read_text()
methods = '\n'.join(block(source, name) for name in (
    'bool ai::HasEncounterDamagePause(', 'bool ai::HasEncounterThreatPause(', 'bool ai::HasEncounterSpellBomb(', 'bool ai::ShouldAvoidEncounterOffense(',
    'bool ai::HasUnsafeEncounterOffense(', 'bool ai::StopUnsafeEncounterOffense('))
pet = (root.parent/'mangos-wotlk-behavior/src/game/AI/BaseAI/PetAI.cpp').read_text()
pet_methods = '\n'.join(block(pet, name) for name in (
    'Player* EncounterBotOwner(', 'void PetAI::AttackStart(', 'bool PetAI::Cast('))
update = block(pet, 'void PetAI::UpdateAI(')
pause_update = block(update, 'if (Player* botOwner = EncounterBotOwner(m_unit))')

code = r'''
#include <cassert>
#include <cmath>
#include <list>
#include <set>
#include <tuple>
#include <vector>
#include <functional>
#include <iostream>
using uint32=unsigned;
enum SpellEffectIndex {EFFECT_INDEX_0,EFFECT_INDEX_1,EFFECT_INDEX_2,MAX_EFFECT_INDEX};
enum CurrentSpellTypes {CURRENT_MELEE_SPELL,CURRENT_GENERIC_SPELL,CURRENT_AUTOREPEAT_SPELL,CURRENT_CHANNELED_SPELL};
enum {SPELL_STATE_CASTING,SPELL_STATE_CHANNELING,SPELL_STATE_TRAVELING,SPELL_STATE_FINISHED,
 UNIT_STAT_MELEE_ATTACKING=1,TRIGGERED_NORMAL_COMBAT_CAST=0x100,TRIGGERED_PET_CAST=0x80,
 SPELL_ATTR_EX_NO_THREAT=1,SPELL_ATTR_EX2_NO_INITIAL_THREAT=2,SPELL_ATTR_EX4_NO_HELPFUL_THREAT=4,
 SPELL_ATTR_EX3_SUPPRESS_CASTER_PROCS=8,SPELL_ATTR_EX2_AUTO_REPEAT=16,
 SPELL_DAMAGE_CLASS_MAGIC=1,SPELL_DAMAGE_CLASS_MELEE=2,SPELL_DAMAGE_CLASS_RANGED=3};
enum SpellCastResult {SPELL_CAST_OK,SPELL_FAILED};
struct Unit;struct Player;
struct SpellAuraHolder {Unit* caster=nullptr;Unit* GetCaster()const{return caster;}};
struct SpellEntry {uint32 Id=1;bool positive=false;unsigned attributes=0,DmgClass=SPELL_DAMAGE_CLASS_MAGIC;
 bool periodic[3]{},trigger[3]{},auraTrigger[3]{};bool HasAttribute(unsigned a)const{return attributes&a;}};
bool IsAuraApplyEffect(const SpellEntry*s,SpellEffectIndex i){return s->periodic[i]||s->auraTrigger[i];}
bool IsSpellEffectDamage(const SpellEntry&s,SpellEffectIndex i){return s.periodic[i];}
bool IsSpellEffectTriggerSpell(const SpellEntry*s,SpellEffectIndex i){return s->trigger[i];}
bool IsSpellEffectTriggerSpellByAura(const SpellEntry*s,SpellEffectIndex i){return s->auraTrigger[i];}
struct SpellCastTargets {Unit* target=nullptr;Unit* getUnitTarget()const{return target;}void setUnitTarget(Unit*u){target=u;}};
struct Spell {
 const SpellEntry* m_spellInfo;SpellCastTargets m_targets;int state=SPELL_STATE_CASTING;bool interruptible=true;
 static unsigned starts,lastFlags;
 Spell(Unit*,const SpellEntry*s,uint32 flags):m_spellInfo(s){lastFlags=flags;}
 bool CanBeInterrupted()const{return interruptible&&(state==SPELL_STATE_CASTING||state==SPELL_STATE_CHANNELING);}
 int getState()const{return state;}
 SpellCastResult SpellStart(SpellCastTargets*){++starts;delete this;return SPELL_CAST_OK;}
};unsigned Spell::starts=0,Spell::lastFlags=0;
struct BotAI {bool real=false;std::vector<unsigned> interrupted;bool IsRealPlayer(){return real;}void SpellInterrupted(unsigned id){interrupted.push_back(id);}};
struct Unit {
 bool world=true,alive=true,combat=true,charmed=false,melee=false,player=false,controlled=true,disabled=false;
 unsigned map=575,instance=1,phase=1,entry=0,stops=0,attacks=0,react=2;float z=0,dist=5;
 std::set<unsigned> auras;Spell* casts[4]{};Unit* master=nullptr;std::function<void()> onInterrupt;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 bool IsInMap(Unit*u){return u&&world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}
 unsigned GetEntry(){return entry;}unsigned GetMapId(){return map;}float GetDistance(Unit*u){return u->dist;}
 float GetPositionZ(){return z;}bool HasAura(unsigned id){return auras.count(id);}
 bool hasUnitState(unsigned){return melee;}void AttackStop(){++stops;melee=false;}
 Spell* GetCurrentSpell(CurrentSpellTypes s){return casts[s];}
 void InterruptSpell(CurrentSpellTypes s){casts[s]=nullptr;if(onInterrupt){auto f=onInterrupt;onInterrupt={};f();}}
 Unit* GetMaster(){return master;}bool IsPlayer(){return player;}bool HasActionsDisabled(){return disabled;}
 bool Attack(Unit*who,bool){if(!who)return false;++attacks;melee=true;return true;}
 bool IsPlayerControlled(){return controlled;}bool HasInArc(Unit*){return true;}void SetFacingToObject(Unit*){}
};
struct Player:Unit {bool teleport=false;BotAI* ai=nullptr;SpellAuraHolder* gaze=nullptr;SpellAuraHolder* bomb=nullptr;Player(){player=true;}
 bool IsBeingTeleported(){return teleport;}BotAI* GetPlayerbotAI(){return ai;}
 SpellAuraHolder* GetSpellAuraHolder(unsigned id){assert(id==24314||id==40303);return id==24314?gaze:bomb;}};
bool IsPositiveSpell(const SpellEntry*s,Unit*,Unit*){return s->positive;}
std::list<Unit*> worldUnits;
namespace MaNGOS {
 struct AllCreaturesOfEntryInRangeCheck {AllCreaturesOfEntryInRangeCheck(Player*,unsigned,float){}};
 template<class T>struct UnitListSearcher {std::list<Unit*>& list;UnitListSearcher(std::list<Unit*>&l,T&):list(l){}};
}
namespace Cell {template<class T>void VisitAllObjects(Player*,MaNGOS::UnitListSearcher<T>&s,float){s.list=worldUnits;}}
namespace ai {
 bool HasHakkarPoisonPreparation(Player*) { return false; } // actual coordination is exercised in hakkar_poison_regression.py
 bool HasEncounterDamagePause(Player*);bool HasEncounterThreatPause(Player*);bool HasEncounterSpellBomb(Player*);bool ShouldAvoidEncounterOffense(Player*,Unit*,const SpellEntry*,Unit*);
 bool HasUnsafeEncounterOffense(Player*);bool StopUnsafeEncounterOffense(Player*,Unit*);
}
__METHODS__
struct PetAI {
 Unit* m_unit;Unit* m_pet;Unit* m_creature;bool m_meleeEnabled=true,m_inCombat=false,scripted=false;unsigned moves=0;
 bool GetCombatScriptStatus(){return scripted;}void HandleMovementOnAttackStart(Unit*,bool){++moves;}
 void AttackStart(Unit*);bool Cast(std::tuple<const SpellEntry*,Unit*,bool>);
 void PauseUpdate(Unit*&victim){__UPDATE__}
};
__PET_METHODS__
int main(){
 BotAI botAI;Player bot;bot.ai=&botAI;Unit boss;boss.entry=26861;boss.auras={48294};worldUnits={&boss};
 SpellEntry damage{17,false},heal{18,true};Spell harmful(&bot,&damage,0),helpful(&bot,&heal,0);
 // Mandokir watches this player's threat, including helpful threat, in every era.
 bot.map=boss.map=309;boss.entry=11382;SpellAuraHolder gaze{&boss};bot.gaze=&gaze;
 assert(ai::HasEncounterThreatPause(&bot)&&!ai::HasEncounterDamagePause(&bot));
 assert(ai::ShouldAvoidEncounterOffense(&bot,&bot,&damage,&boss));
 assert(ai::ShouldAvoidEncounterOffense(&bot,&bot,&heal,&bot));
 for(unsigned flag:{SPELL_ATTR_EX_NO_THREAT,SPELL_ATTR_EX2_NO_INITIAL_THREAT,SPELL_ATTR_EX4_NO_HELPFUL_THREAT}){
  heal.attributes=flag;assert(!ai::ShouldAvoidEncounterOffense(&bot,&bot,&heal,&bot));
 }heal.attributes=0;
 damage.attributes=SPELL_ATTR_EX_NO_THREAT;assert(ai::ShouldAvoidEncounterOffense(&bot,&bot,&damage,&boss));damage.attributes=0;
 Unit companion;companion.map=309;assert(!ai::ShouldAvoidEncounterOffense(&bot,&companion,&damage,&boss));
 for(auto slot:{CURRENT_MELEE_SPELL,CURRENT_GENERIC_SPELL,CURRENT_AUTOREPEAT_SPELL,CURRENT_CHANNELED_SPELL}){
  bot.casts[slot]=&helpful;assert(ai::HasUnsafeEncounterOffense(&bot));
  assert(ai::StopUnsafeEncounterOffense(&bot,&bot)&&!bot.casts[slot]);
 }
 bot.casts[CURRENT_GENERIC_SPELL]=&helpful;heal.attributes=SPELL_ATTR_EX4_NO_HELPFUL_THREAT;
 assert(!ai::HasUnsafeEncounterOffense(&bot)&&!ai::StopUnsafeEncounterOffense(&bot,&bot));heal.attributes=0;
 // Expiry between detection and execution releases the hold without cancelling a replacement cast.
 assert(ai::HasUnsafeEncounterOffense(&bot));bot.gaze=nullptr;
 assert(!ai::StopUnsafeEncounterOffense(&bot,&bot)&&bot.casts[CURRENT_GENERIC_SPELL]==&helpful);bot.gaze=&gaze;
 boss.dist=300;boss.z=50;assert(ai::HasEncounterThreatPause(&bot));boss.dist=5;boss.z=0;
 auto unwatched=[&](){assert(!ai::HasEncounterThreatPause(&bot));};
 gaze.caster=nullptr;unwatched();gaze.caster=&boss;
 boss.entry=999;unwatched();boss.entry=11382;boss.instance=2;unwatched();boss.instance=1;
 boss.phase=2;unwatched();boss.phase=1;boss.alive=false;unwatched();boss.alive=true;
 boss.combat=false;unwatched();boss.combat=true;boss.world=false;unwatched();boss.world=true;
 botAI.real=true;unwatched();botAI.real=false;bot.teleport=true;unwatched();bot.teleport=false;
 bot.charmed=true;unwatched();bot.charmed=false;
 bot.gaze=nullptr;bot.map=boss.map=575;boss.entry=26861;
 bot.casts[CURRENT_GENERIC_SPELL]=nullptr;botAI.interrupted.clear();
#ifndef MANGOSBOT_ZERO
 bot.map=boss.map=556;boss.entry=23035;SpellAuraHolder bomb{&boss};bot.bomb=&bomb;
 assert(ai::HasEncounterSpellBomb(&bot)&&!ai::HasEncounterThreatPause(&bot));
 assert(ai::ShouldAvoidEncounterOffense(&bot,&bot,&damage,&boss));
 assert(ai::ShouldAvoidEncounterOffense(&bot,&bot,&heal,&bot));
 heal.attributes=SPELL_ATTR_EX4_NO_HELPFUL_THREAT;assert(ai::ShouldAvoidEncounterOffense(&bot,&bot,&heal,&bot));heal.attributes=0;
 damage.DmgClass=SPELL_DAMAGE_CLASS_MELEE;assert(!ai::ShouldAvoidEncounterOffense(&bot,&bot,&damage,&boss));
 for(unsigned index=0;index<3;++index){
  damage.periodic[index]=true;assert(ai::ShouldAvoidEncounterOffense(&bot,&bot,&damage,&boss));damage.periodic[index]=false;
  damage.trigger[index]=true;assert(ai::ShouldAvoidEncounterOffense(&bot,&bot,&damage,&boss));damage.trigger[index]=false;
  damage.auraTrigger[index]=true;assert(ai::ShouldAvoidEncounterOffense(&bot,&bot,&damage,&boss));damage.auraTrigger[index]=false;
 }
 damage.DmgClass=SPELL_DAMAGE_CLASS_RANGED;assert(ai::ShouldAvoidEncounterOffense(&bot,&bot,&damage,&boss));
 damage.attributes=SPELL_ATTR_EX2_AUTO_REPEAT;assert(!ai::ShouldAvoidEncounterOffense(&bot,&bot,&damage,&boss));
 damage.DmgClass=SPELL_DAMAGE_CLASS_MAGIC;assert(!ai::ShouldAvoidEncounterOffense(&bot,&bot,&damage,&boss)); // wands
 damage.attributes=SPELL_ATTR_EX3_SUPPRESS_CASTER_PROCS;assert(!ai::ShouldAvoidEncounterOffense(&bot,&bot,&damage,&boss));damage.attributes=0;
 bot.melee=true;assert(!ai::HasUnsafeEncounterOffense(&bot)&&!ai::StopUnsafeEncounterOffense(&bot,&bot)&&bot.melee);
 for(auto slot:{CURRENT_GENERIC_SPELL,CURRENT_CHANNELED_SPELL}){
  bot.casts[slot]=&helpful;assert(ai::HasUnsafeEncounterOffense(&bot));
  assert(ai::StopUnsafeEncounterOffense(&bot,&bot)&&bot.casts[slot]==nullptr&&bot.melee);
 }
 companion.map=556;assert(!ai::ShouldAvoidEncounterOffense(&bot,&companion,&damage,&boss));
 bot.casts[CURRENT_GENERIC_SPELL]=&harmful;bot.bomb=nullptr;
 assert(!ai::StopUnsafeEncounterOffense(&bot,&bot)&&bot.casts[CURRENT_GENERIC_SPELL]==&harmful);bot.bomb=&bomb;
 boss.instance=2;assert(!ai::HasEncounterSpellBomb(&bot));boss.instance=1;
 boss.entry=999;assert(!ai::HasEncounterSpellBomb(&bot));boss.entry=23035;
 bomb.caster=nullptr;assert(!ai::HasEncounterSpellBomb(&bot));bomb.caster=&boss;
 bot.bomb=nullptr;bot.melee=false;bot.casts[CURRENT_GENERIC_SPELL]=nullptr;botAI.interrupted.clear();
 bot.map=boss.map=575;boss.entry=26861;
#else
 assert(!ai::HasEncounterSpellBomb(&bot));
#endif
#ifdef MANGOSBOT_TWO
 assert(ai::HasEncounterDamagePause(&bot));
 assert(ai::ShouldAvoidEncounterOffense(&bot,&bot,&damage,&boss));
 assert(ai::ShouldAvoidEncounterOffense(&bot,&bot,&damage,nullptr)); // untargeted AoE
 assert(!ai::ShouldAvoidEncounterOffense(&bot,&bot,&heal,&bot));
 assert(!ai::ShouldAvoidEncounterOffense(&bot,nullptr,&damage,&boss));
 assert(!ai::HasEncounterDamagePause(nullptr));
 auto noPause=[&](){assert(!ai::HasEncounterDamagePause(&bot));assert(!ai::StopUnsafeEncounterOffense(&bot,&bot));};
 bot.world=false;noPause();bot.world=true;bot.alive=false;noPause();bot.alive=true;
 bot.combat=false;noPause();bot.combat=true;bot.charmed=true;noPause();bot.charmed=false;
 bot.teleport=true;noPause();bot.teleport=false;botAI.real=true;noPause();botAI.real=false;
 bot.ai=nullptr;noPause();bot.ai=&botAI;
 boss.world=false;noPause();boss.world=true;boss.alive=false;noPause();boss.alive=true;
 boss.combat=false;noPause();boss.combat=true;boss.charmed=true;noPause();boss.charmed=false;
 boss.instance=2;noPause();boss.instance=1;boss.phase=2;noPause();boss.phase=1;
 boss.dist=101;noPause();boss.dist=5;boss.z=9;noPause();boss.z=0;
 boss.entry=999;noPause();boss.entry=26861;boss.auras={59301};assert(ai::HasEncounterDamagePause(&bot));
 boss.auras.clear();noPause();boss.auras={48294};
 bot.map=1;boss.map=1;noPause();bot.map=boss.map=632;noPause();
 boss.entry=36502;boss.auras={69051};noPause(); // link aura belongs on player, not boss
 boss.auras={69023};assert(ai::HasEncounterDamagePause(&bot));
 for(auto slot:{CURRENT_MELEE_SPELL,CURRENT_GENERIC_SPELL,CURRENT_AUTOREPEAT_SPELL,CURRENT_CHANNELED_SPELL}){
  bot.casts[slot]=&harmful;assert(ai::HasUnsafeEncounterOffense(&bot));
  assert(ai::StopUnsafeEncounterOffense(&bot,&bot)&&!bot.casts[slot]);
  bot.casts[slot]=&helpful;assert(!ai::HasUnsafeEncounterOffense(&bot));
  assert(!ai::StopUnsafeEncounterOffense(&bot,&bot)&&bot.casts[slot]==&helpful);bot.casts[slot]=nullptr;
 }
 assert(botAI.interrupted.size()==4);
 bot.casts[CURRENT_GENERIC_SPELL]=&harmful;harmful.state=SPELL_STATE_TRAVELING;
 assert(!ai::HasUnsafeEncounterOffense(&bot)&&!ai::StopUnsafeEncounterOffense(&bot,&bot));
 harmful.state=SPELL_STATE_FINISHED;assert(!ai::HasUnsafeEncounterOffense(&bot));
 harmful.state=SPELL_STATE_CASTING;harmful.interruptible=false;assert(!ai::StopUnsafeEncounterOffense(&bot,&bot));harmful.interruptible=true;
 // The aura may expire or current spell may change after a reaction was queued.
 assert(ai::HasUnsafeEncounterOffense(&bot));boss.auras.clear();assert(!ai::StopUnsafeEncounterOffense(&bot,&bot));
 boss.auras={69023};bot.casts[CURRENT_GENERIC_SPELL]=&helpful;assert(!ai::StopUnsafeEncounterOffense(&bot,&bot));
 bot.casts[CURRENT_GENERIC_SPELL]=nullptr;bot.melee=true;assert(ai::StopUnsafeEncounterOffense(&bot,&bot)&&!bot.melee);
 // Re-read subsequent slots after native interrupt callbacks; never interrupt a newly installed heal.
 bot.casts[CURRENT_MELEE_SPELL]=&harmful;bot.casts[CURRENT_GENERIC_SPELL]=&harmful;
 bot.onInterrupt=[&](){bot.casts[CURRENT_GENERIC_SPELL]=&helpful;};
 assert(ai::StopUnsafeEncounterOffense(&bot,&bot)&&bot.casts[CURRENT_GENERIC_SPELL]==&helpful);
 bot.casts[CURRENT_GENERIC_SPELL]=nullptr;
 Unit pet;pet.map=632;pet.master=&bot;PetAI pai{&pet,&pet,&pet};
 unsigned callbacks=botAI.interrupted.size();pet.casts[CURRENT_GENERIC_SPELL]=&harmful;pet.melee=true;
 Unit* victim=&boss;pai.PauseUpdate(victim);assert(!victim&&!pet.melee&&!pet.casts[CURRENT_GENERIC_SPELL]);
 assert(botAI.interrupted.size()==callbacks&&pet.react==2); // do not persist temporary reaction changes
 pai.AttackStart(&boss);assert(pet.attacks==0&&pai.moves==0);
 assert(!pai.Cast({&damage,&boss,true})&&Spell::starts==0);
 assert(pai.Cast({&heal,&bot,false})&&Spell::starts==1);
 boss.auras.clear();pai.AttackStart(&boss);assert(pet.attacks==1&&pai.moves==1&&pai.m_inCombat);
 assert(pai.Cast({&damage,&boss,true})&&Spell::starts==2&&Spell::lastFlags==(TRIGGERED_NORMAL_COMBAT_CAST|TRIGGERED_PET_CAST));
 boss.auras={69023};botAI.real=true;pai.AttackStart(&boss);assert(pet.attacks==2);botAI.real=false;
 bot.ai=nullptr;pai.AttackStart(&boss);assert(pet.attacks==3);bot.ai=&botAI;
 pet.instance=2;assert(!ai::StopUnsafeEncounterOffense(&bot,&pet));
#else
 bot.melee=true;bot.casts[CURRENT_GENERIC_SPELL]=&harmful;
 assert(!ai::HasEncounterDamagePause(&bot)&&!ai::HasUnsafeEncounterOffense(&bot));
 assert(!ai::ShouldAvoidEncounterOffense(&bot,&bot,&damage,&boss));
 assert(!ai::StopUnsafeEncounterOffense(&bot,&bot)&&bot.melee&&bot.casts[CURRENT_GENERIC_SPELL]);
#endif
 std::cout<<"PASS: actual damage-pause policy, lifecycle, spell slots and native pet attack/cast admission\n";
}
'''.replace('__METHODS__', methods).replace('__PET_METHODS__', pet_methods).replace('__UPDATE__', pause_update)
# Forward declaration is needed because the extracted native helper is below the fixture class.
code = code.replace('struct PetAI {', 'Player* EncounterBotOwner(Unit*);\nstruct PetAI {')
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-encounter-damage-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','/DENABLE_PLAYERBOTS','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
