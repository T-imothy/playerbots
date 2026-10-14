"""Actual bot debuff admission above old display limits; native storage contract."""
from pathlib import Path
import subprocess,sys,tempfile
from behavior_regression import block
R=Path(__file__).resolve().parents[1]
s=(R/'playerbot/strategy/triggers/GenericTriggers.cpp').read_text()
if '--before' in sys.argv:
    s=subprocess.check_output(['git','-C',str(R),'show','HEAD:playerbot/strategy/triggers/GenericTriggers.cpp'],text=True)
body='\n'.join(block(s,name) for name in ('bool DebuffTrigger::IsActive(', 'bool DebuffTrigger::HasMaxDebuffs('))
code=r'''
#include <cassert>
#include <string>
#include <vector>
#include <iostream>
using uint32=unsigned;
struct Unit{bool alive=true;bool IsAlive(){return alive;}};
struct PlayerbotAI{bool has=false;unsigned count=0;bool HasAura(std::string,Unit*,bool,bool){return has;}
 std::vector<unsigned>GetAuras(Unit*,bool,bool){return std::vector<unsigned>(count);}};
struct DebuffTrigger{PlayerbotAI*ai;Unit*target;std::string spell="corruption";bool checkIsOwner=true;
 Unit*GetTarget(){return target;}bool IsActive();bool HasMaxDebuffs();};
__METHODS__
int main(){PlayerbotAI brain;Unit boss;DebuffTrigger trigger{&brain,&boss};
 for(unsigned n:{0u,12u,16u,17u,40u,41u,64u,100u}){brain.count=n;assert(!trigger.HasMaxDebuffs()&&trigger.IsActive());}
 brain.has=true;assert(!trigger.IsActive());brain.has=false;boss.alive=false;assert(!trigger.IsActive());
 boss.alive=true;trigger.target=nullptr;assert(!trigger.IsActive());
 std::cout<<"PASS debuff admission beyond 16/40/64, existing aura ownership and dead/null target guards\n";
}
'''.replace('__METHODS__',body)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='debuff-admission-') as directory:
        path=Path(directory);(path/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=path,check=True)
        subprocess.run([str(path/'test.exe')],cwd=path,check=True)
# Visible client slots are not a storage/application cap. Check the native
# contract without changing wire field sizes or pretending this is a realm test.
for era in ('classic','tbc','wotlk'):
    core=R.parent/era
    unit=(core/'src/game/Entities/Unit.cpp').read_text()
    add=block(unit,'bool Unit::AddSpellAuraHolder(')
    assert 'm_spellAuraHolders.insert(' in add and 'holder->ApplyAuraModifiers(true, true)' in add
    assert add.index('holder->_AddSpellAuraHolder()')<add.index('m_spellAuraHolders.insert(')<add.index('holder->ApplyAuraModifiers(true, true)')
    assert not any(term in add for term in ('MAX_AURAS','MAX_POSITIVE_AURAS','GetAuraSlot()','debuffLimit'))
    aura=(core/'src/game/Spells/SpellAuras.cpp').read_text()
    native=block(aura,'void SpellAuraHolder::_AddSpellAuraHolder(')
    assert 'SetAuraSlot(slot)' in native and 'if (slot < MAX_AURAS)' in native
print('PASS all three native aura-holder storage/application contracts; visible slot fields unchanged')
