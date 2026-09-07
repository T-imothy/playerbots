"""Execute actual heal trigger and interrupt action against changed cast/health state."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

repo = Path(__file__).resolve().parents[1]
methods = '\n'.join(block((repo / path).read_text(), marker) for path, marker in (
    ('playerbot/strategy/triggers/HealthTriggers.cpp', 'bool HealTargetFullHealthTrigger::IsActive('),
    ('playerbot/strategy/actions/GenericSpellActions.cpp', 'bool InterruptCurrentSpellAction::Execute(')))
code = r'''
#include <cassert>
#include <cstdint>
#include <string>
#include <iostream>
using uint32=uint32_t;
enum CurrentSpellTypes{CURRENT_MELEE_SPELL,CURRENT_GENERIC_SPELL,CURRENT_CHANNELED_SPELL};
enum{SPELL_STATE_CASTING,SPELL_STATE_FINISHED};
enum class BotState{BOT_STATE_NON_COMBAT};
struct Unit{uint32 hp=100,maxhp=100,absorb=0;bool fullHealWound=false;uint32 GetHealth(){return hp;}uint32 GetMaxHealth(){return maxhp;}float GetHealthPercent(){return hp*100.f/maxhp;}};
bool NeedsFullHealingToRemoveAura(Unit* u){return u && u->fullHealWound && u->hp < u->maxhp;}
unsigned RemainingHealingAbsorb(Unit* u){return u?u->absorb:0;}
struct SpellEntry{uint32 Id=10;bool heal=true;};
struct Targets{Unit* target=nullptr;Unit* getUnitTarget(){return target;}};
struct Spell{SpellEntry* m_spellInfo;Targets m_targets;int state=SPELL_STATE_CASTING;unsigned casted=1,damage=40;bool interruptible=true;
 int getState(){return state;}unsigned GetCastedTime(){return casted;}unsigned GetDamage(){return damage;}unsigned GetPowerCost(){return 20;}bool CanBeInterrupted(){return interruptible;}};
struct Player{Spell* spells[3]={};unsigned interrupted[3]={};SpellEntry replacement{99,false};
 Spell* GetCurrentSpell(CurrentSpellTypes t){return spells[t];}
 void InterruptSpell(CurrentSpellTypes t){++interrupted[t];spells[t]->m_spellInfo=&replacement;spells[t]=nullptr;}};
struct Trigger{virtual bool IsActive()=0;};
struct Context{Trigger* trigger=nullptr;Trigger* GetTrigger(const char*){return trigger;}};
struct PlayerbotAI{Context context;unsigned notified=0;
 static bool IsHealSpell(SpellEntry* info){return info->heal;}bool HasStrategy(const char*,BotState){return false;}
 void TellPlayerNoFacing(Player*,const std::string&){}void SpellInterrupted(unsigned id){notified=id;}Context* GetAiObjectContext(){return &context;}};
struct HealTargetFullHealthTrigger:Trigger{Player* bot;PlayerbotAI* ai;bool IsActive()override;Player* GetMaster(){return nullptr;}};
struct Event{std::string source;std::string getSource(){return source;}};
struct InterruptCurrentSpellAction{Player* bot;PlayerbotAI* ai;bool Execute(Event&);};
__METHODS__
int main(){
 Player bot;PlayerbotAI ai;HealTargetFullHealthTrigger trigger;trigger.bot=&bot;trigger.ai=&ai;ai.context.trigger=&trigger;
 InterruptCurrentSpellAction action{&bot,&ai};Unit patient;SpellEntry heal{10,true},damage{20,false};Spell spell{&heal,{&patient}};
 Event automatic{"heal target full health"},manual{"manual"};bot.spells[CURRENT_GENERIC_SPELL]=&spell;
 assert(trigger.IsActive());patient.hp=20;
 patient.hp=100;patient.absorb=60000;assert(!trigger.IsActive()&&!action.Execute(automatic));patient.absorb=0;patient.hp=20;
 assert(!action.Execute(automatic));assert(bot.interrupted[CURRENT_GENERIC_SPELL]==0); // The queued event is stale after fresh damage.
 patient.hp=100;spell.m_spellInfo=&damage;assert(!action.Execute(automatic)); // A replacement damage cast is not the queued heal.
 spell.m_spellInfo=&heal;Spell melee{&damage,{&patient}},channel{&heal,{&patient}};
 bot.spells[CURRENT_MELEE_SPELL]=&melee;bot.spells[CURRENT_CHANNELED_SPELL]=&channel;
 assert(action.Execute(automatic));assert(ai.notified==10); // Capture ID before native cancellation callbacks.
 assert(bot.interrupted[CURRENT_MELEE_SPELL]==0&&bot.interrupted[CURRENT_CHANNELED_SPELL]==0);
 assert(action.Execute(manual));assert(ai.notified==20);assert(bot.interrupted[CURRENT_CHANNELED_SPELL]==0);
 spell.m_spellInfo=&heal;bot.spells[CURRENT_GENERIC_SPELL]=&spell;patient.hp=95;assert(action.Execute(automatic));
 spell.m_spellInfo=&heal;bot.spells[CURRENT_GENERIC_SPELL]=&spell;patient.fullHealWound=true;
 assert(!action.Execute(automatic));patient.hp=100;assert(action.Execute(automatic));
 patient.hp=95;patient.fullHealWound=false;
 spell.m_spellInfo=&heal;bot.spells[CURRENT_GENERIC_SPELL]=&spell;spell.interruptible=false;assert(!action.Execute(automatic));
 spell.interruptible=true;spell.m_targets.target=nullptr;assert(!action.Execute(automatic));
 spell.m_targets.target=&patient;ai.context.trigger=nullptr;assert(!action.Execute(automatic));
 std::cout<<"PASS: fresh heal/target recheck, replacement casts, overheal threshold, manual scope and pre-callback spell ID\n";
}
'''.replace('__METHODS__', methods)
with tempfile.TemporaryDirectory(prefix='mantech-heal-interrupt-') as folder:
    tmp = Path(folder)
    (tmp / 'test.cpp').write_text(code)
    for era in ('ZERO', 'ONE', 'TWO'):
        subprocess.run(['cl', '/nologo', '/std:c++17', '/EHsc', '/DMANGOSBOT_' + era, 'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
