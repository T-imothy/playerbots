"""Check bot integration against all three native cores; no compilation or DB writes."""
import argparse
from pathlib import Path
from behavior_regression import block

p = argparse.ArgumentParser()
p.add_argument('--cores-dir', type=Path, required=True)
cores = p.parse_args().cores_dir
root = Path(__file__).resolve().parents[1]
source = (root/'playerbot/strategy/actions/BlackwingLairDungeonActions.cpp').read_text()
control = block(source, 'bool RazorgoreOrbAction::UpdateControl(')
select = block(source, 'GameObject* RazorgoreOrbAction::SelectOrb(')
assert '!dragon->HasCharmer(bot->GetObjectGuid())' in control
assert 'UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL' not in control
assert 'hasUnitState(UNIT_STAT_CAN_NOT_REACT)' in control
assert 'GetGoState() != GO_STATE_READY' in control
assert 'GetLootState() != GO_READY' in control
assert 'IsSpellReady(*destroy)' in control
assert 'HandlePetCastSpellOpcode(packet)' in control
assert 'SetData(' not in control and 'SetData64(' not in control
assert 'SetHealth(' not in control and 'RemoveAurasDueToSpell' not in control
assert 'dragon->HasCharmer()' in select and 'HasAura(23958)' in select
assert 'ai->IsTank(member) || ai->IsHeal(member)' in select
assert '>= 30000' in control and '< 15000' in control
assert 'if (movingToEgg != egg->GetObjectGuid()) eggMoveStarted = now;' in control
assert 'uint8(0) << uint32(19873) << uint8(0)' in control
assert 'targets.setGOTarget(egg)' in control
for era in ('classic', 'tbc', 'wotlk'):
    game = cores/era/'src/game'
    handler = block((game/'Entities/PetHandler.cpp').read_text(),
                    'void WorldSession::HandlePetCastSpellOpcode(')
    assert '_player->HasCharm(guid)' in handler
    assert 'IsSpellReady(*spellInfo)' in handler and 'HasSpell(spellid)' in handler
    assert 'targets.ReadForCaster(petUnit)' in handler
    if era == 'wotlk':
        assert 'recvPacket >> guid >> cast_count >> spellid >> cast_flags;' in handler
    else:
        assert 'recvPacket >> guid >> spellid;' in handler
    unit = (game/'Entities/Unit.h').read_text()
    assert 'bool HasCharmer(ObjectGuid const& exactGuid) const' in unit
    go = (game/'Entities/GameObject.h').read_text()
    if era == 'classic':
        assert 'float GetInteractionDistance() const' in go
        assert 'orb->IsWithinDistInMap(bot, orb->GetInteractionDistance())' in source
    else:
        assert 'bool IsAtInteractDistance(Player const* player' in go
    assert 'dragon->GetCharmerGuid()' not in control
    # Regression: possession belongs to LOST_CONTROL; never use that aggregate
    # to reject the dragon that this very action is meant to possess.
    lost = unit.split('UNIT_STAT_LOST_CONTROL    =', 1)[1].split(',', 1)[0]
    assert 'UNIT_STAT_POSSESSED' in lost
    native = game/'AI/ScriptDevAI/scripts/eastern_kingdoms/blackwing_lair'
    boss = (native/'boss_razorgore.cpp').read_text()
    assert '19873' in boss and '23958' in boss and 'SetData64' in boss
    instance = (native/'blackwing_lair.cpp').read_text()
    assert 'SetData(TYPE_RAZORGORE, SPECIAL)' in instance
    print('PASS native Razorgore ownership, spell packet and phase contracts:', era)
print('Source checks only; compile and live possession/egg handoff tests remain required.')
