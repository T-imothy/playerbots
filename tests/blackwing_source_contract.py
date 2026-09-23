"""Source/native contracts only. Does not compile, start a realm or modify its DB."""
import argparse
import ast
import re
from pathlib import Path
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--cores-dir',type=Path,required=True)
args=parser.parse_args()
def read(path): return (root/path).read_text()
a=read('playerbot/strategy/actions/BlackwingLairDungeonActions.cpp')
protected=block(a,'bool ai::IsProtectedBlackwingTarget(')
assert 'GetData(0) != SPECIAL' in protected
assert 'GetEntry() == 10162' in protected and 'HasAura(22663)' in protected
assert 'SetData' not in protected and 'CastSpell' not in protected
priority=block(a,'Unit* BlackwingLairPriorityTargetAction::GetTarget(')
for guard in ('BwlReady(ai)','ai->IsHeal(bot)','"attack target"','"rti target"','HasBreakableCC','HasUnBreakableCC','unit->GetVictim() == bot'):
    assert guard in priority,guard
support=block(a,'bool BlackwingLairSupportAction::Select(')
assert 'CanCastSpell(name, unit, 0)' in support and 'info->Dispel' in support
assert '23342' in support and '23128' in support
assert 'for (uint32 aura : {22687u, 23153u, 23154u, 23155u, 23169u})' in support
assert 'if (!Select(spell, target)) return false;' in a
flank=block(a,'bool ai::BlackwingMeleeFlankAngle(')
assert 'target->GetEntry() != 13020 && target->GetEntry() != 11583' in flank
assert 'ai->IsTank(bot)' in flank and 'target->GetVictim() == bot' in flank
movement=read('playerbot/strategy/actions/MovementActions.cpp')
assert 'BlackwingMeleeFlankAngle(ai, target, angle)' in movement
assert 'flankAngle - obj->GetOrientation()' in movement
assert 'BlackwingMeleeFlankAngle(ai, target, flankAngle)' in movement
assert 'blackwing lair flank' in read('playerbot/strategy/triggers/TriggerContext.h')
for path in ('actions/ActionContext.h','triggers/TriggerContext.h','generic/BlackwingLairDungeonStrategies.cpp'):
    for key in ('blackwing lair support','blackwing lair priority target'):
        assert key in read('playerbot/strategy/'+path),(path,key)
assert 'rule = {{23341}, 5}' in read('playerbot/strategy/actions/EncounterTauntPolicy.cpp')
assert 'IsProtectedBlackwingTarget(player, target)' in read('playerbot/strategy/values/PossibleAttackTargetsValue.cpp')
assert 'IsProtectedBlackwingTarget(bot, target)' in read('playerbot/strategy/actions/AttackAction.cpp')
assert 'IsProtectedBlackwingTarget(bot, target)' in read('playerbot/strategy/actions/EncounterDamagePolicy.cpp')
for name in ('blackwing_position_regression.py','encounter_taunt_regression.py','encounter_damage_pause_regression.py','blackwing_target_policy_regression.py'):
    ast.parse(read('tests/'+name),filename=name)
contracts={
 'boss_razorgore.cpp':(12435,19873), # entry is declared in the common header
 'boss_vaelastrasz.cpp':(13020,18173),
 'boss_broodlord_lashlayer.cpp':(12017,23331),
 'boss_firemaw.cpp':(11983,23341),
 'boss_ebonroc.cpp':(14601,23340),
 'boss_flamegor.cpp':(11981,23342),
 'boss_chromaggus.cpp':(14020,23128),
 'boss_nefarian.cpp':(11583,22687,14605),
 'boss_victor_nefarius.cpp':(10162,22663),
}
for era in ('classic','tbc','wotlk'):
    core=args.cores_dir/era/'src/game'
    native=core/'AI/ScriptDevAI/scripts/eastern_kingdoms/blackwing_lair'
    header=(native/'blackwing_lair.h').read_text()
    instance=(native/'blackwing_lair.cpp').read_text()
    assert re.search(r'TYPE_RAZORGORE\s*=\s*0',header)
    assert re.search(r'SPECIAL\s*=\s*4',(core/'AI/ScriptDevAI/include/sc_instance.h').read_text())
    assert 'm_lUsedEggsGuids.size() == m_lDragonEggsGuids.size()' in instance
    assert 'SetData(TYPE_RAZORGORE, SPECIAL)' in instance
    for name,ids in contracts.items():
        text=header+(native/name).read_text()
        for value in ids: assert re.search(r'\b'+str(value)+r'\b',text),(era,name,value)
    for entry in (12557,12420,12416,14456,12422,14261,14262,14263,14264,14265,14302):
        assert re.search(r'\b'+str(entry)+r'\b',header),(era,entry)
    print('PASS BWL native phase, entry and spell contracts:',era)
print('PASS BWL source admission, registries, support guards and regression syntax; no compilation/live tests')
