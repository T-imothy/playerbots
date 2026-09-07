#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "EncounterSpellPolicy.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleTargetsValue.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"

using namespace ai;

bool ai::IsViscidusShatterTarget(Unit* target, Player* bot)
{
    // His self-applied encounter freeze explicitly requires melee hits.
    // It is not player crowd control; explicit CC-marker checks remain separate.
    return bot && target && bot->IsInWorld() && bot->IsAlive() && bot->IsInCombat() &&
        bot->GetMapId() == 531 && target->GetEntry() == 15299 && target->IsInWorld() &&
        target->IsAlive() && target->IsInCombat() && !target->HasCharmer() && bot->IsInMap(target) &&
        target->GetSpellAuraHolder(25937, target->GetObjectGuid());
}

uint32 ViscidusFrostAction::GetFrostSpell()
{
    if (bot->GetMapId() != 531 || !bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() ||
        !bot->GetGroup() || bot->HasCharmer() || bot->IsBeingTeleported() || ai->IsRealPlayer() ||
        ai->IsHeal(bot) || ai->IsTank(bot)) return 0;
    Unit* target = AI_VALUE(Unit*, "current target");
    if (!target || target->GetEntry() != 15299 || !target->IsInWorld() || !target->IsAlive() ||
        !target->IsInCombat() || target->HasCharmer() || !bot->IsInMap(target) ||
        !target->GetSpellAuraHolder(25926, target->GetObjectGuid()) || target->HasAura(25937) ||
        !PossibleTargetsValue::IsValid(target, bot, false) ||
        !PossibleAttackTargetsValue::IsPossibleTarget(target, bot, sPlayerbotAIConfig.sightDistance, false)) return 0;
    uint32 spellId = 0;
    std::string spellName;
    // The native weakness counts pure frost hits, regardless of damage. These
    // learned first ranks conserve mana and avoid long high-rank Frostbolts.
    if (bot->getClass() == CLASS_MAGE) { spellId = 116; spellName = "frostbolt"; }
    else if (bot->getClass() == CLASS_SHAMAN) { spellId = 8056; spellName = "frost shock"; }
#ifdef MANGOSBOT_TWO
    else if (bot->getClass() == CLASS_DEATH_KNIGHT) { spellId = 45477; spellName = "icy touch"; }
#endif
    const SpellEntry* spell = spellId ? sServerFacade.LookupSpellInfo(spellId) : nullptr;
    if (!spell || !bot->HasSpell(spellId) || GetSpellSchoolMask(spell) != SPELL_SCHOOL_MASK_FROST ||
        !AI_VALUE2(bool, "spell cast useful", spellName) ||
        !ai->CanCastSpell(spellId, target, 0, true)) return 0;
    return spellId;
}

bool ViscidusFrostAction::isUseful()
{
    return GetFrostSpell() != 0;
}

bool ViscidusFrostAction::Execute(Event& event)
{
    uint32 spellId = GetFrostSpell();
    if (!spellId) return false;
    uint32 duration = 0;
    if (!ai->CastSpell(spellId, AI_VALUE(Unit*, "current target"), nullptr, false, &duration)) return false;
    SetDuration(duration);
    return true;
}
