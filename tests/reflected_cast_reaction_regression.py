"""Actual reflection reaction keeps launched/positive/unreflectable casts and rechecks live shields."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

repo=Path(__file__).resolve().parents[1]
source=(repo/'playerbot/strategy/actions/EncounterSpellPolicy.cpp').read_text()
methods='\n'.join(block(source,s) for s in ('bool ai::HasUnsafeReflectedCast(', 'bool ai::InterruptUnsafeReflectedCast('))
code=r'''
#include <cassert>
#include <iostream>
using uint32=unsigned;
enum{CURRENT_GENERIC_SPELL,SPELL_STATE_CASTING,SPELL_STATE_CHANNELING,SPELL_STATE_FINISHED};
struct SpellEntry{unsigned Id=123,school=4;bool reflectable=true;};
struct Unit{bool world=true,alive=true,friendly=false;int map=1;float chance=0;unsigned mask=4;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}float GetReflectChance(unsigned school){return mask&school?chance:0;}};
struct Targets{Unit* target=nullptr;Unit* getUnitTarget()const{return target;}};
struct Spell{SpellEntry* m_spellInfo;Targets m_targets;unsigned state=SPELL_STATE_CASTING;bool interruptible=true;
 unsigned getState()const{return state;}bool CanBeInterrupted(){return interruptible;}};
struct PlayerbotAI{unsigned interrupted=0;void SpellInterrupted(unsigned spell){interrupted=spell;}};
struct Player:Unit{bool combat=true,teleport=false,charmed=false;Spell* current=nullptr;unsigned canceled=0;PlayerbotAI* ai=nullptr;
 bool IsInCombat(){return combat;}bool IsBeingTeleported(){return teleport;}bool HasCharmer(){return charmed;}
 bool IsInMap(Unit* target){return target->map==map;}Spell* GetCurrentSpell(int){return current;}
 void InterruptSpell(int){++canceled;current=nullptr;}PlayerbotAI* GetPlayerbotAI(){return ai;}};
struct Facade{bool IsFriendlyTo(Player*,Unit* target){return target->friendly;}}sServerFacade;
bool IsReflectableSpell(const SpellEntry* spell){return spell->reflectable;}unsigned GetSpellSchoolMask(const SpellEntry* spell){return spell->school;}
namespace ai {bool HasUnsafeReflectedCast(Player*);bool InterruptUnsafeReflectedCast(Player*);}
__METHODS__
int main(){
 Player bot;Unit enemy;SpellEntry entry;Spell cast{&entry,{&enemy}};PlayerbotAI ai;bot.ai=&ai;bot.current=&cast;
 assert(!ai::HasUnsafeReflectedCast(&bot));enemy.chance=49;assert(!ai::HasUnsafeReflectedCast(&bot));
 enemy.chance=50;assert(ai::HasUnsafeReflectedCast(&bot));enemy.chance=0;assert(!ai::InterruptUnsafeReflectedCast(&bot)&&bot.canceled==0);
 enemy.chance=100;entry.reflectable=false;assert(!ai::InterruptUnsafeReflectedCast(&bot));entry.reflectable=true;
 enemy.mask=2;assert(!ai::InterruptUnsafeReflectedCast(&bot));enemy.mask=4;
 cast.state=SPELL_STATE_FINISHED;assert(!ai::InterruptUnsafeReflectedCast(&bot));cast.state=SPELL_STATE_CHANNELING;assert(!ai::InterruptUnsafeReflectedCast(&bot));cast.state=SPELL_STATE_CASTING;
 enemy.friendly=true;assert(!ai::InterruptUnsafeReflectedCast(&bot));enemy.friendly=false;
 enemy.world=false;assert(!ai::HasUnsafeReflectedCast(&bot));enemy.world=true;enemy.map=2;assert(!ai::HasUnsafeReflectedCast(&bot));enemy.map=1;
 bot.teleport=true;assert(!ai::HasUnsafeReflectedCast(&bot));bot.teleport=false;bot.charmed=true;assert(!ai::HasUnsafeReflectedCast(&bot));bot.charmed=false;
 cast.interruptible=false;assert(!ai::InterruptUnsafeReflectedCast(&bot));cast.interruptible=true;
 assert(ai::InterruptUnsafeReflectedCast(&bot)&&bot.canceled==1&&ai.interrupted==123);
 assert(!ai::InterruptUnsafeReflectedCast(&bot));assert(!ai::HasUnsafeReflectedCast(nullptr));
 std::cout<<"PASS: reflection threshold/school, live shield/cast recheck, positive/finished/channel preservation and native interruption\n";
}
'''.replace('__METHODS__',methods)
with tempfile.TemporaryDirectory(prefix='mantech-reflection-reaction-') as folder:
    tmp=Path(folder);(tmp/'test.cpp').write_text(code)
    for era in ('ZERO','ONE','TWO'):
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
strategy=(repo/'playerbot/strategy/generic/DungeonStrategy.cpp').read_text()
for hook in ('InitCombatTriggers','InitReactionTriggers'):
    assert 'stop unsafe reflected cast' in block(strategy,'void DungeonStrategy::'+hook+'(')
assert 'creators["stop unsafe reflected cast"]' in (repo/'playerbot/strategy/actions/ActionContext.h').read_text()
assert 'creators["unsafe reflected cast"]' in (repo/'playerbot/strategy/triggers/TriggerContext.h').read_text()
