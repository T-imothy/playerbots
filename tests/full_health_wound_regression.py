"""Exercise native full-health wound IDs and actual health-trigger decisions."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

repo=Path(__file__).resolve().parents[1]
policy=(repo/'playerbot/strategy/actions/EncounterHealingPolicy.cpp').read_text()
triggers=(repo/'playerbot/strategy/triggers/HealthTriggers.cpp').read_text()
methods=block(policy,'uint32 ai::RemainingHealingAbsorb(')+'\n'+block(policy,'bool ai::NeedsFullHealingToRemoveAura(')+'\n'+block(triggers,'bool HealthInRangeTrigger::IsActive(')
code=r'''
#include <cassert>
#include <string>
#include <set>
#include <iostream>
#include <algorithm>
#include <cstdint>
#include <vector>
using uint32=unsigned;using uint64=uint64_t;
constexpr unsigned SPELL_AURA_HEAL_ABSORB=301;
struct Modifier{int m_amount=0;};struct Aura{Modifier modifier;const Modifier* GetModifier()const{return &modifier;}};
enum class BotState{BOT_STATE_COMBAT,BOT_STATE_NON_COMBAT};
struct Unit{unsigned hp=98,maxhp=100;bool world=true,alive=true;std::set<unsigned> auras;std::vector<const Aura*> absorbs;
 const std::vector<const Aura*>& GetAurasByType(unsigned){return absorbs;}
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}unsigned GetHealth(){return hp;}unsigned GetMaxHealth(){return maxhp;}
 bool HasAura(unsigned id){return auras.count(id);}bool IsPlayer(){return true;}};
struct Player:Unit{};
struct PlayerbotAI{bool preheal=false;Unit* target;unsigned incoming=0;
 bool HasStrategy(std::string n,BotState){return n=="preheal"&&preheal;}
 bool IsTank(Player*,bool){return false;}void TellPlayerNoFacing(Player*,std::string){}
 template<class T>T value(std::string key){return T(key=="dead"?!target->alive:incoming);}};
namespace ai{bool NeedsFullHealingToRemoveAura(Unit*);unsigned RemainingHealingAbsorb(Unit*);}
using namespace ai;
struct ValueInRangeTrigger{float maxValue=80,minValue=50;Unit* target;
 float GetValue(){return target?100.f*target->hp/target->maxhp:0;}
 bool IsActive(){return GetValue()<maxValue&&GetValue()>=minValue;}};
struct HealthInRangeTrigger:ValueInRangeTrigger{PlayerbotAI* ai;std::string name="party member medium health";bool isTankRequired=false;
 Unit* GetTarget(){return target;}std::string GetTargetName(){return "party member to heal";}std::string getName(){return name;}
 Player* GetMaster(){return nullptr;}bool IsActive();};
#define AI_VALUE2(type,key,qualifier) ai->value<type>(key)
__METHODS__
int main(){
 Player patient;PlayerbotAI ai;ai.target=&patient;HealthInRangeTrigger t;t.target=&patient;t.ai=&ai;
 assert(!t.IsActive());
 for(unsigned id:{43093u,31956u,38801u,35321u,38363u,39215u,48920u}){
  patient.auras={id};
#ifdef MANGOSBOT_ZERO
  assert(!NeedsFullHealingToRemoveAura(&patient)&&!t.IsActive());
#else
  assert(NeedsFullHealingToRemoveAura(&patient)&&t.IsActive());
  t.name="medium health";assert(t.IsActive());t.name="party member medium health";
  ai.preheal=true;ai.incoming=1;assert(t.IsActive());ai.preheal=false;ai.incoming=0;
  patient.hp=100;assert(!NeedsFullHealingToRemoveAura(&patient)&&!t.IsActive());patient.hp=98;
  patient.world=false;assert(!NeedsFullHealingToRemoveAura(&patient));patient.world=true;
  patient.alive=false;assert(!t.IsActive());patient.alive=true;
  t.name="party member critical health";assert(!t.IsActive());t.name="target low health";assert(!t.IsActive());
  t.name="party member medium health";patient.hp=20;assert(!t.IsActive());patient.hp=98;
#endif
 }
 patient.auras={38772};assert(!t.IsActive()); // This native wound uses a different health threshold.
 patient.auras.clear();patient.hp=60;assert(t.IsActive());patient.hp=98;assert(!t.IsActive());
 assert(!NeedsFullHealingToRemoveAura(nullptr));
 Aura first{{60000}},empty{{0}},negative{{-1}},large{{INT32_MAX}};patient.hp=100;patient.absorbs={&first,&empty,&negative};
#ifdef MANGOSBOT_TWO
 assert(RemainingHealingAbsorb(&patient)==60000&&t.IsActive());
 patient.absorbs={&large,&large,&large};assert(RemainingHealingAbsorb(&patient)==UINT32_MAX);
 patient.alive=false;assert(RemainingHealingAbsorb(&patient)==0);patient.alive=true;
 patient.absorbs={&empty,&negative};assert(!RemainingHealingAbsorb(&patient)&&!t.IsActive());
#else
 assert(RemainingHealingAbsorb(&patient)==0&&!t.IsActive());
#endif
 std::cout<<"PASS: full-health wound finish, native IDs, trigger scope and ordinary health behavior\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-full-health-wound-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
for era in ('tbc','wotlk'):
    native=(repo.parent/f'mangos-{era}-behavior/src/game/Spells/SpellAuras.cpp').read_text()
    marker=native.index('case 43093: case 31956: case 38801:')
    section=native[marker:marker+600]
    assert 'target->GetHealth() == target->GetMaxHealth()' in section
    assert 'target->RemoveAurasDueToSpell(GetId())' in section
print('PASS: both native periodic-damage handlers confirm full-health removal')
native=(repo.parent/'mangos-wotlk-behavior/src/game/Entities/Unit.cpp').read_text()
assert 'GetAurasByType(SPELL_AURA_HEAL_ABSORB)' in native
assert 'AURA_REMOVE_BY_SHIELD_BREAK' in native
