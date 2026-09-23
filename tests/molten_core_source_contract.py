"""Source-only MC contracts; no compiler, realm or database is started.

Run with --cores-dir pointing to sibling classic/tbc/wotlk checkouts to also
check the encounter spell/creature contracts against all three native cores.
This is not a substitute for the C++ regressions or live raid tests.
"""
from pathlib import Path
import argparse
import ast
import re

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--cores-dir', type=Path)
args = parser.parse_args()
def read(path):
    return (root / path).read_text()
actions = read('playerbot/strategy/actions/MoltenCoreDungeonActions.cpp')
position = read('playerbot/strategy/values/MoltenCorePositionValue.cpp')
for path in ('actions/ActionContext.h', 'triggers/TriggerContext.h', 'generic/MoltenCoreDungeonStrategies.cpp'):
    assert '"molten core support"' in read('playerbot/strategy/' + path), path
assert 'ACTION_DISPEL + 5' in read('playerbot/strategy/generic/MoltenCoreDungeonStrategies.cpp')
assert 'if (!Select(spell, target)) return false' in actions
assert 'ai->CanCastSpell(name, unit, 0)' in actions
assert 'if (slot == 0) return valid(boss) ? boss : nullptr;' in actions
assert actions.index('if (slot == 0)') < actions.index('const size_t offTanks')
assert '!PossibleAttackTargetsValue::HasBreakableCC(unit, bot)' in actions
assert '!PossibleAttackTargetsValue::HasUnBreakableCC(unit, bot)' in actions
assert 'healer->HasAura(21087)' in actions
assert '(markedHealer ? 0 : 1)' in actions
assert 'cast->m_spellInfo->Id != 19775' in actions
assert '#ifdef MANGOSBOT_TWO\n                "wind shear", "mind freeze"\n#else\n                "earth shock"' in actions
assert '!ai->IsTank(bot) && !ai->IsRanged(bot)' in position
assert 'boss->GetVictim() != bot' in position
assert 'member->GetObjectGuid() < bot->GetObjectGuid()' in position
assert 'if (++checked > 8) break' in position
assert 'ValidateEncounterDestination(ai, plan)' in position
for name in ('encounter_adds_regression.py', 'molten_core_position_regression.py', 'netherspite_runtime_regression.py'):
    ast.parse(read('tests/' + name), filename=name)
if args.cores_dir:
    # Native encounter scripts are the implementation under audit, not a web guide.
    required = {
        'boss_lucifron.cpp': (19702, 19703),
        'boss_magmadar.cpp': (19451, 19408),
        'boss_gehennas.cpp': (19716, 19717),
        'boss_garr.cpp': (19497, 20483),
        'boss_baron_geddon.cpp': (19659, 19695, 20475),
        'boss_shazzrah.cpp': (19712, 19713, 19714),
        'boss_sulfuron_harbinger.cpp': (19775,),
        'boss_golemagg.cpp': (13879, 20556),
        'boss_majordomo_executus.cpp': (20619, 21075, 21087),
        'boss_ragnaros.cpp': (20566, 21154),
    }
    for era in ('classic', 'tbc', 'wotlk'):
        native = args.cores_dir / era / 'src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/molten_core'
        for name, ids in required.items():
            text = (native / name).read_text()
            for spell in ids:
                assert re.search(r'\b' + str(spell) + r'\b', text), (era, name, spell)
        print('PASS native MC spell contracts:', era)
print('PASS MC source wiring, safety contracts and Python regression syntax (no compile/live test)')

# Trash decisions must preserve boss hazards and use real role/class actions.
assert 'MoltenCoreThreats(ai, current, threats) || !PlanMoltenCoreTrash(ai, current)' in actions
assert 'selected->GetEntry() == 12101' in actions and 'unit->GetEntry() != 11673' in actions
assert 'enemy->GetEntry() == 11669' in actions and 'return imps >= 3' in actions
assert 'ai->IsTank(static_cast<Player*>(victim))' in actions
assert 'PlanMoltenCoreTrash(ai, plan)' in position
assert 'molten core imp pack' in read('playerbot/strategy/triggers/TriggerContext.h')
assert 'MoltenCoreImpPack(ai)' in read('playerbot/strategy/mage/MageActions.h')
print('PASS MC trash source wiring, tank-held pack admission and hazard precedence')
