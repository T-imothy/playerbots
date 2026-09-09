"""Target-selection source contracts. Does not compile or run a realm."""
from pathlib import Path
import argparse

def block(text, marker):
    start=text.index(marker);opening=text.index('{',start);depth=0
    for i in range(opening,len(text)):
        depth+=(text[i]=='{')-(text[i]=='}')
        if depth==0:return text[start:i+1]
    raise ValueError(marker)

parser=argparse.ArgumentParser()
parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
parser.add_argument('--core-root',type=Path)
args=parser.parse_args()
root=args.root/'playerbot/strategy'
def read(p):return (root/p).read_text(encoding='utf-8')

basic=block(read('values/PossibleTargetsValue.cpp'),'bool PossibleTargetsValue::IsValid')
assert 'player->IsInMap(target)' in basic and 'IsInEvadeMode()' in basic
assert basic.index('UnitIsDead') < basic.index('IsFriendly') < basic.index('IsAttackable')
assert '!ignoreLos && !isInCombatWithTarget' in basic
possible=block(read('values/PossibleAttackTargetsValue.cpp'),'bool PossibleAttackTargetsValue::IsPossibleTarget')
assert possible.index('PossibleTargetsValue::IsValid(target, player, true)') < possible.index('IsImmuneToDamage')
find=block(read('values/TargetValue.cpp'),'Unit* TargetValue::FindTarget')
assert find.index('PossibleTargetsValue::IsValid') < find.index('strategy->CheckAttacker')
invalid=block(read('values/InvalidTargetValue.cpp'),'bool InvalidTargetValue::Calculate')
assert invalid.index('PossibleTargetsValue::IsValid') < invalid.index('duelTarget')
assert 'MeleeCcCheck(ai).Protected(target)' in invalid
assert 'PossibleAttackTargetsValue::IsPossibleTarget' in invalid
assert 'PossibleTargetsValue::IsValid' in read('values/RtiTargetValue.h')
for filename in ('DpsTargetValue.cpp','TankTargetValue.cpp'):
    text=read('values/'+filename)
    assert 'IsPossibleTarget(rti, bot' in text and 'MeleeCcCheck(ai).Protected(rti)' in text
assert 'MeleeCcCheck(ai).Protected(attacker)' in read('values/DpsTargetValue.cpp')
assert 'HasBreakableByDamageCrowdControlAura() || IsCcTarget(attacker)' in read('values/LeastHpTargetValue.h')
tank=read('values/TankTargetValue.cpp')
assert 'victim->GetGroup() == bot->GetGroup()' in tank and '!ai->IsTank(victim)' in tank
assert '(rescue && !rescueTarget)' in tank and 'rescue == rescueTarget' in tank
assert block(tank,'Unit* TankTargetValue::Calculate').index('return rti') < block(tank,'Unit* TankTargetValue::Calculate').index('FindTargetForTankStrategy')
enemy=read('values/EnemyPlayerValue.cpp')
assert 'firstTarget' not in block(enemy,'Unit* EnemyPlayerValue::Calculate')
assert 'EnemyPlayersValue::IsValid(target, bot)' in block(enemy,'Unit* EnemyPlayerValue::Calculate')
assert 'PossibleTargetsValue::IsFriendly(target, player)' in block(enemy,'bool EnemyPlayersValue::IsValid')
attack=read('actions/AttackAction.cpp')
assert 'MeleeCcCheck(ai).Protected(target)' in block(attack,'bool AttackAction::Execute')
assert 'PossibleTargetsValue::IsValid' in block(attack,'bool AttackAction::IsTargetValid')
recover=block(read('actions/ChooseTargetActions.cpp'),'bool SelectNewTargetAction::Execute')
assert 'BOT_STATE_NON_COMBAT' not in recover
assert recover.index('HasStrategy("tank assist"') < recover.index('HasStrategy("dps assist"')
assert recover.rstrip().endswith('return selectedReplacement || clearedSelection;\n}')
assert 'const bool clearedSelection' in recover
assert 'selectedReplacement = ai->DoSpecificAction' in recover
assert 'ai->InterruptSpell();' not in recover
assert 'type <= CURRENT_CHANNELED_SPELL' in recover and 'IsPositiveSpell(spell->m_spellInfo)' in recover
assert recover.index('const uint32 spellId') < recover.index('bot->InterruptSpell') < recover.index('ai->SpellInterrupted')
assert 'spell->m_targets.getUnitTargetGuid() != previousSelection' in recover
for name in ('dps target','dps aoe target','tank target','enemy player target'):
    assert 'GetValue<Unit*>("'+name+'")->Reset()' in recover
trigger=read('triggers/GenericTriggers.cpp')
dps=block(trigger,'bool DpsAssistTrigger::IsActive')
assert 'bot->GetVictim() != target' in dps and 'pet->GetVictim() == target' in dps
assert 'strategy->ShouldWait(ai)' in dps and 'stealthed' in dps
assert 'HasAura(4511)' in dps and 'HasReactState(REACT_PASSIVE)' in dps
for fn in ('TankAssistTrigger','NotDpsTargetActiveTrigger','NotDpsAoeTargetActiveTrigger'):
    body=block(trigger,'bool '+fn+'::IsActive')
    assert 'return false;' in block(body,'if (enemy)')
print('PASS: source contracts for eligibility, CC, rescue, assist ownership and recovery.')

if args.core_root:
    for era in ('classic','tbc','wotlk'):
        core=args.core_root/('mangos-'+era+'-behavior')/'src/game'
        unit=(core/'Entities/Unit.h').read_text(encoding='utf-8')
        spell=(core/'Spells/Spell.h').read_text(encoding='utf-8')
        assert 'HasBreakableByDamageCrowdControlAura' in unit
        assert 'CURRENT_CHANNELED_SPELL' in unit and 'CURRENT_AUTOREPEAT_SPELL' in unit
        assert 'getUnitTargetGuid() const' in spell and 'CanBeInterrupted' in spell
        print('PASS: referenced native interface declarations:',era)
print('NOT RUN: C++ compilation, gameplay tests, live target/latency measurements.')
