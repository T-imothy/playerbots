"""Existing hunter routing and actual native-dispel-type trigger; no boss cheats."""
from pathlib import Path
import re
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
triggers = (root / 'playerbot/strategy/triggers/GenericTriggers.cpp').read_text()
method = block(triggers, 'bool DispelOnTargetTrigger::IsActive(')
strategy = (root / 'playerbot/strategy/hunter/HunterStrategy.cpp').read_text()
starts = [m.start() for m in re.finditer('void HunterStrategy::InitReactionTriggers\\(', strategy)]
assert len(starts) == 3
for start in starts:
    body = block(strategy[start:], 'void HunterStrategy::InitReactionTriggers(')
    assert '"dispel enrage"' in body and 'new NextAction("tranquilizing shot", ACTION_INTERRUPT)' in body
assert 'CastTranquilizingShotAction' in (root / 'playerbot/strategy/hunter/HunterAiObjectContext.cpp').read_text()
assert 'DispelOnTargetTrigger(ai, name, DISPEL_ENRAGE)' in (root / 'playerbot/strategy/triggers/GenericTriggers.h').read_text()

code = r'''
#include <cassert>
#include <iostream>
#include <vector>
using uint32=unsigned;
struct SpellEntry{unsigned Id=0,Dispel=0;};
struct Aura{const SpellEntry* info;const SpellEntry* GetSpellProto()const{return info;}};
struct Unit{std::vector<Aura*> auras;};
struct PlayerbotAI{std::vector<Aura*> GetAuras(Unit* u){return u->auras;}};
unsigned GetDispellMask(unsigned type){return 1u<<type;}
struct DispelOnTargetTrigger{PlayerbotAI* ai;Unit* target;unsigned dispelType=9;
 Unit* GetTarget(){return target;}bool IsActive();};
__METHOD__
int main(){PlayerbotAI ai;Unit target;DispelOnTargetTrigger trigger{&ai,&target};
 assert(!trigger.IsActive());trigger.target=nullptr;assert(!trigger.IsActive());trigger.target=&target;
 // Read-only spell-template evidence shared by Classic, TBC and Wrath.
 SpellEntry magmadar{19451,9},flamegor{23342,9},chromaggus{23128,9},finalEnrage{23537,0},magic{1,1};
 Aura aura{&finalEnrage};target.auras={&aura};assert(!trigger.IsActive());
 for(const auto* frenzy:{&magmadar,&flamegor,&chromaggus}){aura.info=frenzy;assert(trigger.IsActive());}
 aura.info=&magic;assert(!trigger.IsActive());aura.info=nullptr;assert(!trigger.IsActive());
 std::cout<<"PASS: existing all-era hunter reaction routing; actual enrage type check excludes final enrage/magic\n";
}
'''.replace('__METHOD__', method)
with tempfile.TemporaryDirectory(prefix='mantech-frenzy-routing-') as folder:
    tmp = Path(folder)
    (tmp / 'test.cpp').write_text(code)
    subprocess.run(['cl', '/nologo', '/EHsc', '/std:c++17', 'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
    subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
