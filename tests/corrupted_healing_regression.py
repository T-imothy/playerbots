"""Compile actual encounter policy and cast wrappers in all three expansion modes.

Controlled native interfaces test decisions, not a simulated raid clear.
"""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
policy = (root / 'playerbot/strategy/actions/EncounterSpellPolicy.cpp').read_text()
assert '#include "playerbot/ServerFacade.h"' in policy
policy = '\n'.join(line for line in policy.splitlines() if not line.startswith('#include'))
generic = (root / 'playerbot/strategy/actions/GenericSpellActions.cpp').read_text()
methods = '\n'.join(block(generic, name) for name in
                    ('bool CastSpellAction::isUseful(', 'bool CastSpellAction::Execute('))
strategy = (root / 'playerbot/strategy/generic/BlackwingLairDungeonStrategies.cpp').read_text()
for method in ('InitCombatTriggers', 'InitReactionTriggers'):
    assert 'stop corrupted healing' in block(strategy, f'void BlackwingLairDungeonStrategy::{method}(')
action = block((root / 'playerbot/strategy/actions/BlackwingLairDungeonActions.h').read_text(),
               'class StopCorruptedHealingAction')
assert 'InterruptCorruptedHealingCast(bot)' in action
assert 'ShouldReactionInterruptCast' not in action  # Base flags stay false.

code = r'''
#include <cassert>
#include <cstdint>
#include <iostream>
#include <list>
#include <map>
#include <set>
#include <string>
using uint32=unsigned;using uint64=uint64_t;
constexpr unsigned CLASS_PRIEST=5,CLASS_HUNTER=3,SPELL_EFFECT_HEAL=10,SPELL_EFFECT_APPLY_AURA=6,
 SPELL_EFFECT_DUMMY=3,SPELL_EFFECT_CREATE_ITEM=24,SPELL_AURA_PERIODIC_TRIGGER_SPELL=23,
 MAX_EFFECT_INDEX=3,SPELLFAMILY_PRIEST=6,ATTACK_DISTANCE=5,SPELL_AURA_DAMAGE_SHIELD=15,EQUIP_ERR_OK=0;
enum CurrentSpellTypes{CURRENT_MELEE_SPELL,CURRENT_GENERIC_SPELL,CURRENT_AUTOREPEAT_SPELL,CURRENT_CHANNELED_SPELL};
enum SpellState{SPELL_STATE_CREATED,SPELL_STATE_CASTING,SPELL_STATE_CHANNELING,SPELL_STATE_TRAVELING,SPELL_STATE_FINISHED};
struct SpellEntry{uint32 Id=1,Effect[3]{},EffectApplyAuraName[3]{},EffectTriggerSpell[3]{},EffectItemType[3]{};
 uint32 SpellFamilyName=0;uint64 SpellFamilyFlags=0;const char* SpellName[1]{"spell"};bool channel=false,passive=false;};
bool IsSpellHaveEffect(const SpellEntry* s,unsigned effect){for(unsigned e:s->Effect)if(e==effect)return true;return false;}
bool IsChanneledSpell(const SpellEntry* s){return s->channel;}
bool IsPassiveSpell(const SpellEntry* s){return s->passive;}
bool IsReflectableSpell(const SpellEntry*){return false;}
unsigned GetSpellSchoolMask(const SpellEntry*){return 1;}
struct Aura{struct Mod{unsigned m_amount=0;}mod;Mod* GetModifier(){return &mod;}};
struct Unit{using AuraList=std::list<Aura*>;AuraList shields;bool world=true,friendly=true;unsigned map=469,phase=1;
 bool IsInWorld(){return world;}unsigned GetMapId(){return map;}bool IsInMap(Unit* u){return u&&world&&u->world&&map==u->map&&phase==u->phase;}
 const AuraList& GetAurasByType(unsigned){return shields;}float GetReflectChance(unsigned){return 0;}};
struct Spell{const SpellEntry* m_spellInfo=nullptr;SpellState state=SPELL_STATE_CASTING;
 struct Targets{Unit* target=nullptr;Unit* getUnitTarget(){return target;}}m_targets;
 SpellState getState(){return state;}};
using PlayerSpellMap=std::map<uint32,unsigned>;
struct ItemPrototype{};
struct Player:Unit{bool alive=true,teleport=false,charmed=false,corrupted=true;unsigned klass=CLASS_PRIEST,stops=0;
 Spell* casts[4]{};PlayerSpellMap spellMap;bool IsAlive(){return alive;}bool IsBeingTeleported(){return teleport;}
 bool HasCharmer(){return charmed;}unsigned getClass(){return klass;}bool HasAura(unsigned id){return id==23401&&corrupted;}
 bool CanAssistSpell(Unit* u,const SpellEntry*){return u&&u->friendly;}Spell* GetCurrentSpell(CurrentSpellTypes s){return casts[s];}
 void InterruptSpell(CurrentSpellTypes s){++stops;casts[s]=nullptr;}
 unsigned GetMaxHealth(){return 1000;}void AttackStop(){}PlayerSpellMap& GetSpellMap(){return spellMap;}
 unsigned CanUseItem(const ItemPrototype*){return EQUIP_ERR_OK;}};
struct Facade{std::map<unsigned,SpellEntry> spells;unsigned lookups=0;
 const SpellEntry* LookupSpellInfo(unsigned id){++lookups;auto i=spells.find(id);return i==spells.end()?nullptr:&i->second;}
 float GetDistance2d(Unit*,Unit*){return 0;}}sServerFacade;
struct ObjectMgr{const ItemPrototype* GetItemPrototype(unsigned){return nullptr;}}sObjectMgr;
void strToLower(std::string&){}
enum class BotCheatMask{attackspeed};
struct PlayerbotAI{bool learned=true;unsigned casts=0;bool HasSpell(unsigned){return learned;}
 bool IsInVehicle(bool=false,bool=false,bool=false){return false;}bool HasCheat(BotCheatMask){return false;}
 template<class T>bool CastSpell(T,Unit*,void* =nullptr,bool=false,unsigned* =nullptr){++casts;return true;}};
struct Config{unsigned globalCoolDown=1500;}sPlayerbotAIConfig;
struct Event{std::string getSource(){return "test";}};
struct CombatDiagnostics{static bool Select(PlayerbotAI*){return false;}
 static void Record(PlayerbotAI*,std::string,std::string,const char*,int,unsigned){}};
namespace ai{bool ShouldAvoidCorruptedHealing(Player*,const SpellEntry*,Unit*);
 bool denyDispel=false;bool ShouldAvoidEncounterDispel(PlayerbotAI*,const SpellEntry*,Unit*){return denyDispel;}
 bool denyTaunt=false;bool ShouldAvoidEncounterTaunt(PlayerbotAI*,const SpellEntry*,Unit*){return denyTaunt;}
 bool HasCorruptedHealingCast(Player*);bool InterruptCorruptedHealingCast(Player*);}
__POLICY__
using namespace ai;
struct CastSpellAction{Player* bot;PlayerbotAI* ai;Unit* target;unsigned spellId=1;float range=30;
 std::string spellName="heal";bool useful=true;void RefreshSpellId(){}Unit* GetTarget(){return target;}
 std::string GetTargetName(){return "party target";}std::string getName(){return spellName;}
 void SetDuration(unsigned){}bool isUseful();bool Execute(Event&);};
#define AI_VALUE2(type,key,value) useful
__METHODS__
int main(){
 Player bot;Unit target;PlayerbotAI ai;Event event;
 SpellEntry heal;heal.Effect[0]=SPELL_EFFECT_HEAL;sServerFacade.spells[1]=heal;
 CastSpellAction action{&bot,&ai,&target};
 assert(ShouldAvoidCorruptedHealing(&bot,&heal,&target));
 assert(!action.isUseful()&&!action.Execute(event)&&ai.casts==0);
 bot.corrupted=false;assert(action.isUseful());bot.corrupted=true;
 assert(!action.Execute(event)&&ai.casts==0);  // Aura arrived after selection.
 bot.corrupted=false;assert(action.isUseful()&&action.Execute(event)&&ai.casts==1);
 denyDispel=true;assert(!action.isUseful()&&!action.Execute(event)&&ai.casts==1);denyDispel=false;bot.corrupted=true;
 bot.corrupted=false;assert(action.isUseful());denyTaunt=true;
 assert(!action.isUseful()&&!action.Execute(event)&&ai.casts==1);denyTaunt=false;bot.corrupted=true;
 SpellEntry renew;renew.Effect[0]=SPELL_EFFECT_APPLY_AURA;renew.EffectApplyAuraName[0]=8;
 SpellEntry shield=renew;shield.EffectApplyAuraName[0]=69;
 assert(!ShouldAvoidCorruptedHealing(&bot,&renew,&target));assert(!ShouldAvoidCorruptedHealing(&bot,&shield,&target));
 sServerFacade.spells[1]=renew;assert(action.isUseful()&&action.Execute(event));sServerFacade.spells[1]=heal;
 // Direct heal in a non-first slot still matches the core's effect predicate.
 heal.Effect[0]=0;heal.Effect[2]=SPELL_EFFECT_HEAL;assert(ShouldAvoidCorruptedHealing(&bot,&heal,&target));
 SpellEntry channel;channel.channel=true;channel.Effect[1]=SPELL_EFFECT_APPLY_AURA;
 channel.EffectApplyAuraName[1]=SPELL_AURA_PERIODIC_TRIGGER_SPELL;channel.EffectTriggerSpell[1]=1;
 assert(ShouldAvoidCorruptedHealing(&bot,&channel,&target)); // Native Penance/Hymn tick shape.
 channel.channel=false;assert(!ShouldAvoidCorruptedHealing(&bot,&channel,&target));channel.channel=true;
 channel.EffectTriggerSpell[1]=999;assert(!ShouldAvoidCorruptedHealing(&bot,&channel,&target));
 sServerFacade.spells[999]=channel;sServerFacade.lookups=0;
 assert(!ShouldAvoidCorruptedHealing(&bot,&channel,&target)&&sServerFacade.lookups==1); // Bounded, even for a cycle.
 channel.EffectTriggerSpell[1]=1;
 SpellEntry penance;penance.Effect[0]=SPELL_EFFECT_DUMMY;penance.SpellFamilyName=SPELLFAMILY_PRIEST;
 penance.SpellFamilyFlags=uint64(0x0080000000000000);
#ifdef MANGOSBOT_TWO
 assert(ShouldAvoidCorruptedHealing(&bot,&penance,&target));
#else
 assert(!ShouldAvoidCorruptedHealing(&bot,&penance,&target));
#endif
 target.friendly=false;assert(!ShouldAvoidCorruptedHealing(&bot,&penance,&target));target.friendly=true;
 target.phase=2;assert(!ShouldAvoidCorruptedHealing(&bot,&penance,&target));target.phase=1;
 assert(!ShouldAvoidCorruptedHealing(&bot,&penance,nullptr));
 target.world=false;assert(!ShouldAvoidCorruptedHealing(&bot,&penance,&target));target.world=true;
 assert(!ShouldAvoidCorruptedHealing(nullptr,&heal,&target));assert(!ShouldAvoidCorruptedHealing(&bot,nullptr,&target));
 // State changes are freshly evaluated, with no sticky per-bot encounter state.
 for(unsigned state=0;state<7;++state){Player altered=bot;
  if(state==0)altered.klass=1;if(state==1)altered.world=false;if(state==2)altered.alive=false;
  if(state==3)altered.teleport=true;if(state==4)altered.charmed=true;if(state==5)altered.map=0;if(state==6)altered.corrupted=false;
  assert(!ShouldAvoidCorruptedHealing(&altered,&heal,&target));
  assert(!HasCorruptedHealingCast(&altered)&&!InterruptCorruptedHealingCast(&altered));}
 Spell direct{&heal,SPELL_STATE_CASTING,{&target}},hot{&renew,SPELL_STATE_CASTING,{&target}},
  ticking{&channel,SPELL_STATE_CHANNELING,{&target}};
 bot.casts[CURRENT_GENERIC_SPELL]=&direct;bot.casts[CURRENT_CHANNELED_SPELL]=&hot;
 assert(HasCorruptedHealingCast(&bot));bot.corrupted=false;
 assert(!InterruptCorruptedHealingCast(&bot)&&bot.stops==0);bot.corrupted=true;
 assert(InterruptCorruptedHealingCast(&bot)&&bot.stops==1&&bot.casts[CURRENT_CHANNELED_SPELL]==&hot);
 assert(!HasCorruptedHealingCast(&bot));
 bot.casts[CURRENT_GENERIC_SPELL]=&hot;bot.casts[CURRENT_CHANNELED_SPELL]=&ticking;
 assert(InterruptCorruptedHealingCast(&bot)&&bot.stops==2&&bot.casts[CURRENT_GENERIC_SPELL]==&hot);
 for(auto state:{SPELL_STATE_CREATED,SPELL_STATE_TRAVELING,SPELL_STATE_FINISHED}){
  direct.state=state;bot.casts[CURRENT_GENERIC_SPELL]=&direct;
  assert(!HasCorruptedHealingCast(&bot)&&!InterruptCorruptedHealingCast(&bot));}
 std::cout<<"PASS: actual Corrupted Healing policy, spell wrappers, expansion gate, channels and fresh selective interruption\n";
}
'''.replace('__POLICY__', policy).replace('__METHODS__', methods)

for era in ('ZERO', 'ONE', 'TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-corrupted-healing-') as folder:
        tmp = Path(folder)
        (tmp / 'test.cpp').write_text(code)
        subprocess.run(['cl', '/nologo', '/EHsc', '/std:c++17', f'/DMANGOSBOT_{era}',
                        'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
