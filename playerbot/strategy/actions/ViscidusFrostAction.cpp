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
    Unit* target = ai->GetUnit(AI_VALUE(ObjectGuid, "current target"));
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
    if (!ai->CastSpell(spellId, ai->GetUnit(AI_VALUE(ObjectGuid, "current target")), nullptr, false, &duration)) return false;
    SetDuration(duration);
    return true;
}

uint32 ViscidusPoisonAction::SelectPoisonRemoval(Unit*& target)
{
    target = nullptr;
#ifdef MANGOSBOT_ZERO
    if (bot->GetMapId() != 531 || !bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() ||
        !bot->GetGroup() || bot->HasCharmer() || bot->IsBeingTeleported() || ai->IsRealPlayer()) return 0;
    Unit* boss = nullptr;
    for (ObjectGuid guid : AI_VALUE2(std::list<ObjectGuid>, "possible targets", "100:1"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit || unit->GetEntry() != 15299 || !unit->IsInWorld() || !unit->IsAlive() ||
            !unit->IsInCombat() || unit->HasCharmer() || !bot->IsInMap(unit) ||
            !unit->GetSpellAuraHolder(25926, unit->GetObjectGuid())) continue;
        boss = unit;
        break;
    }
    if (!boss) return 0;
    std::vector<Player*> patients;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!member || !member->IsInWorld() || !member->IsAlive() || !bot->IsInMap(member) ||
            member->GetGroup() != bot->GetGroup() || member->IsBeingTeleported() || member->HasCharmer() ||
            !member->GetSpellAuraHolder(25991, boss->GetObjectGuid())) continue;
        // An active Abolish Poison already has native periodic removal. Do not
        // refresh it every decision while another patient remains untreated.
        if (member->HasAura(2893)) continue;
        patients.push_back(member);
    }
    std::sort(patients.begin(), patients.end(), [](Player* a, Player* b) {
        return a->GetHealthPercent() != b->GetHealthPercent() ? a->GetHealthPercent() < b->GetHealthPercent() :
            a->GetObjectGuid() < b->GetObjectGuid();
    });
    for (Player* patient : patients)
        for (uint32 id : {2893u, 4987u, 8946u, 526u, 1152u})
            if (bot->HasSpell(id) && ai->CanCastSpell(id, patient, 0, true))
            {
                target = patient;
                return id;
            }
#endif
    return 0;
}

bool ViscidusPoisonAction::isUseful()
{
    Unit* target = nullptr;
    return SelectPoisonRemoval(target) != 0;
}

bool ViscidusPoisonAction::Execute(Event& event)
{
    // Selection never cancels an existing heal. Recheck the actual poison,
    // learned spell, native range/LOS, resource and cooldown at dispatch.
    if (bot->IsNonMeleeSpellCasted(false)) return false;
    Unit* target = nullptr;
    const uint32 spell = SelectPoisonRemoval(target);
    uint32 duration = 0;
    if (!spell || !ai->CastSpell(spell, target, nullptr, false, &duration)) return false;
    SetDuration(duration);
    return true;
}
