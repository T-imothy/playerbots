"""Native spell LOS predicate, including Garfrost's heroic data correction."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
core=root.parent/'mangos-wotlk-behavior'
source=(core/'src/game/Spells/SpellMgr.h').read_text()
method=block(source,'inline bool IsIgnoreLosSpell(')
code=r'''
#include <cassert>
#include <iostream>
enum SpellAttributesEx2{SPELL_ATTR_EX2_IGNORE_LINE_OF_SIGHT=4};
enum SpellAttributesEx5{SPELL_ATTR_EX5_ALWAYS_LINE_OF_SIGHT=0x02000000};
struct SpellEntry{unsigned Id,ex2,ex5;
 bool HasAttribute(SpellAttributesEx2 mask)const{return ex2&mask;}
 bool HasAttribute(SpellAttributesEx5 mask)const{return ex5&mask;}
};
__METHOD__
int main(){
 SpellEntry normal{68786,4,101220352},heroic{70336,4,67665920};
 assert(!IsIgnoreLosSpell(&normal));assert(IsIgnoreLosSpell(&heroic));
 unsigned original=heroic.ex5;heroic.ex5|=33554432;
 assert(!IsIgnoreLosSpell(&heroic));assert((heroic.ex5&original)==original);
 assert(heroic.ex5==(heroic.ex5|33554432));
 std::cout<<"PASS: actual native LOS predicate admits normal rock cover and repaired heroic cover\n";
}
'''.replace('__METHOD__',method)
with tempfile.TemporaryDirectory(prefix='mantech-native-cover-') as directory:
 tmp=Path(directory);(tmp/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
 subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
spell=(core/'src/game/Spells/Spell.cpp').read_text()
assert '!IsIgnoreLosSpellEffect(m_spellInfo, eff, targetB)' in spell
assert 'IsWithinLOSInMap(caster, true)' in spell
value=(root/'playerbot/strategy/values/BossCoverPositionValue.cpp').read_text()
cover=block(value,'bool ai::IsBossCoverPosition(')
assert 'GetCollisionHeight(), true)' in cover
for era in ('classic','tbc','wotlk'):
 peer=root.parent/f'mangos-{era}-behavior'
 header=(peer/'src/game/Entities/Object.h').read_text()
 assert 'bool ignoreM2Model = false' in header
 print(era,'PASS: explicit spell LOS flag avoids default movement visibility')
