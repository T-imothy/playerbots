"""Exercise actual class proc checks, including passive-name collisions."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]/'playerbot/strategy'
checks=[('warrior/WarriorTriggers.cpp','SwordAndBoardTrigger',46951,50227),
        ('warrior/WarriorTriggers.cpp','SuddenDeathTrigger',29723,52437),
        ('warrior/WarriorTriggers.cpp','TasteForBloodTrigger',56636,60503),
        ('mage/MageTriggers.cpp','FingersOfFrostTrigger',44543,44544),
        ('deathknight/DKTriggers.cpp','KillingMachineTrigger',51123,51124)]
methods='\n'.join(block((root/path).read_text(),f'bool {name}::IsActive(') for path,name,_,_ in checks)
methods+='\n'+block((root/'hunter/HunterActions.cpp').read_text(),'bool CastExplosiveShotAction::isUseful(')
declarations='\n'.join(f'struct {name}:Trigger{{using Trigger::Trigger;bool IsActive();}};' for _,name,_,_ in checks)
cases='\n'.join(f'''{{{name} trigger(&bot);bot.auras={{{talent}}};assert(!trigger.IsActive());
bot.auras.insert({proc});assert(trigger.IsActive()==wrath);bot.auras.erase({proc});assert(!trigger.IsActive());}}''' for _,name,talent,proc in checks)
code=r'''
#include <set>
#include <string>
#include <cassert>
#include <iostream>
struct Unit{};struct Player {std::set<unsigned> auras;bool HasAura(unsigned id){return auras.count(id);}};
struct Trigger {Player* bot;Trigger(Player* p):bot(p){}};
struct Holder {int duration=2000;int GetAuraDuration(){return duration;}};
struct Aura {Holder holder;Holder* GetHolder(){return &holder;}};
struct PlayerbotAI {bool own=false,base=true;Aura aura;Aura* GetAura(std::string,Unit*,bool owner){assert(owner);return own?&aura:nullptr;}};
struct CastSpellAction {PlayerbotAI* ai;CastSpellAction(PlayerbotAI* a):ai(a){}bool isUseful(){return ai->base;}Unit* GetTarget(){return nullptr;}};
struct CastExplosiveShotAction:CastSpellAction {using CastSpellAction::CastSpellAction;bool isUseful();};
__DECLARATIONS__
__METHODS__
int main(){
#ifdef MANGOSBOT_TWO
 const bool wrath=true;
#else
 const bool wrath=false;
#endif
 Player bot;
 __CASES__
 PlayerbotAI ai;CastExplosiveShotAction action(&ai);assert(action.isUseful()==wrath);
 ai.own=true;assert(!action.isUseful());ai.aura.holder.duration=1;assert(!action.isUseful());
 ai.aura.holder.duration=0;assert(action.isUseful()==wrath);ai.base=false;assert(!action.isUseful());
 std::cout<<"PASS: actual proc identity rejects passive talents; Explosive Shot preserves owned ticks and native base eligibility\n";
}
'''.replace('__DECLARATIONS__',declarations).replace('__METHODS__',methods).replace('__CASES__',cases)
for expansion in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-proc-test-') as tmp:
        tmp=Path(tmp);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{expansion}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],check=True)
shadow=(root/'priest/ShadowPriestStrategy.cpp').read_text()
wrath=shadow[shadow.index('#ifdef MANGOSBOT_TWO // WOTLK'):]
combat=block(wrath,'void ShadowPriestStrategy::InitCombatTriggers(')
assert combat.count('new NextAction("dispersion"')==2
assert 'new NextAction("dispersion"' not in shadow[:shadow.index('#ifdef MANGOSBOT_TWO // WOTLK')]
hunter=(root/'hunter/SurvivalHunterStrategy.cpp').read_text()
assert '"black arrow on snare target",\n        NextAction::array(0, new NextAction("black arrow on snare target"' in hunter
print('PASS: Dispersion scheduling is Wrath-only; Black Arrow retains its selected secondary target')
