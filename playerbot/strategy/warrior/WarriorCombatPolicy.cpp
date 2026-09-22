#include "playerbot/playerbot.h"
#include "WarriorCombatPolicy.h"
#include "playerbot/strategy/MeleeCombatPolicy.h"
#include "playerbot/ServerFacade.h"

std::string ai::WarriorStancePrerequisite(PlayerbotAI* ai, const SpellEntry* spell)
{
    Player* bot = ai->GetBot();
    if (bot->getClass() != CLASS_WARRIOR || !spell || !spell->Stances ||
        GetErrorAtShapeshiftedCast(spell, bot->GetShapeshiftForm()) == SPELL_CAST_OK)
        return "";
    // Read this expansion's native form rules; do not copy spell IDs between eras.
    const uint32 forms[] = { FORM_BATTLESTANCE, FORM_DEFENSIVESTANCE, FORM_BERSERKERSTANCE };
    const char* names[] = { "battle stance", "defensive stance", "berserker stance" };
    for (unsigned i = 0; i < 3; ++i)
        if (GetErrorAtShapeshiftedCast(spell, forms[i]) == SPELL_CAST_OK &&
            ai->HasSpell(names[i]) && ai->CanCastSpell(names[i], bot, 0))
            return names[i];
    return "";
}

bool ai::CanPlanWarriorSpell(PlayerbotAI* ai, const std::string& name, Unit* target)
{
    if (!target) return false;
    SpellCastResult reason = SPELL_CAST_OK;
    if (ai->CanCastSpell(name, target, 0, nullptr, true, false, false, &reason))
        return true;
    if (ai->GetBot()->getClass() != CLASS_WARRIOR ||
        (reason != SPELL_FAILED_ONLY_SHAPESHIFT && reason != SPELL_FAILED_NOT_SHAPESHIFT))
        return false;
    const uint32 id = ai->GetAiObjectContext()->GetValue<uint32>("spell id", name)->Get();
    const SpellEntry* spell = sServerFacade.LookupSpellInfo(id);
    // Native CheckCast tests form before reactive/proc state. Do not stance-dance
    // toward Overpower/Revenge unless their native reactive state exists.
    if (!spell || (spell->CasterAuraState && !ai->GetBot()->HasAuraState(AuraState(spell->CasterAuraState))))
        return false;
    if (spell->powerType == POWER_RAGE)
    {
        Player* bot = ai->GetBot();
        uint32 retained = 0;
        if (bot->GetShapeshiftForm() == FORM_DEFENSIVESTANCE)
            if (Aura* aura = bot->GetOverrideScript(831))
                retained += aura->GetModifier()->m_amount * 10;
#ifdef MANGOSBOT_ZERO
        for (Aura* aura : bot->GetAurasByType(SPELL_AURA_OVERRIDE_CLASS_SCRIPTS))
        {
            const int script = aura->GetModifier()->m_miscvalue;
            if (script >= 831 && script <= 835)
            {
                retained += (script - 830) * 50;
                break;
            }
        }
#else
        for (const auto& entry : bot->GetSpellMap())
        {
            if (entry.second.state == PLAYERSPELL_REMOVED) continue;
            const SpellEntry* passive = sServerFacade.LookupSpellInfo(entry.first);
            if (passive && passive->SpellFamilyName == SPELLFAMILY_WARRIOR && passive->SpellIconID == 139)
                retained += bot->CalculateSpellEffectValue(bot, passive, EFFECT_INDEX_0) * 10;
        }
#endif
        if (std::min(bot->GetPower(POWER_RAGE), retained) < Spell::CalculatePowerCost(spell, bot))
            return false;
    }
    return !WarriorStancePrerequisite(ai, spell).empty();
}

// Classic DPS fillers must not repeatedly consume the rage needed by core attacks.
// Tank threat is excluded; later expansions use their own policy below.
bool ai::WarriorFillerRageAllowed(PlayerbotAI* ai, const std::string& name, Unit* target)
{
#ifdef MANGOSBOT_ZERO
    Player* bot = ai->GetBot();
    const bool dump = name == "heroic strike" || name == "cleave";
    const bool execute = name == "execute";
    if (bot->getClass() != CLASS_WARRIOR || ai->IsTank(bot) ||
        (!dump && !execute && name != "sunder armor" && name != "rend")) return true;
    if (!target || !target->IsAlive()) return false;
    auto context = ai->GetAiObjectContext();
    if (name == "sunder armor")
    {
        if (ai->HasAura("expose armor", target)) return false;
        // Conservative longevity proxy, not a DPS/time-to-death prediction:
        // save DPS rage on players, ordinary mobs and nearly finished elites.
        if (target->IsPlayer()) return false;
        Creature* creature = static_cast<Creature*>(target);
        if ((!creature->IsElite() && !creature->IsWorldBoss()) ||
            target->GetHealthPercent() <= 20.0f ||
            target->GetHealth() <= bot->GetMaxHealth()) return false;
    }
    uint32 reserve = 0;
    for (const char* mainAttack : { "bloodthirst", "mortal strike", "whirlwind" })
    {
        const uint32 id = context->GetValue<uint32>("spell id", mainAttack)->Get();
        const SpellEntry* spell = sServerFacade.LookupSpellInfo(id);
        if (!spell || !ai->HasSpell(id)) continue;
        if (std::string(mainAttack) == "whirlwind" && SafeMeleeTargetCount(ai, 8.0f) == 0) continue;
        // Queued next-swing attacks can accompany a ready main ability.
        // GCD fillers, including Execute, must yield to that ability.
        if (!dump && CanPlanWarriorSpell(ai, mainAttack, target)) return false;
        const uint32 cost = uint32(Spell::CalculatePowerCost(spell, bot));
        reserve = dump ? reserve + cost : std::max(reserve, cost);
    }
    // Execute consumes extra rage; use it in gaps, not ahead of ready main attacks.
    if (execute) return true;
    if (dump && bot->GetPower(POWER_RAGE) <= 650) return false;
    const uint32 id = context->GetValue<uint32>("spell id", name)->Get();
    const SpellEntry* spell = sServerFacade.LookupSpellInfo(id);
    if (!spell) return false;
    return bot->GetPower(POWER_RAGE) >= reserve + uint32(Spell::CalculatePowerCost(spell, bot));
#else
    Player* bot = ai->GetBot();
    if (bot->getClass() != CLASS_WARRIOR || ai->IsTank(bot)) return true;
    const bool dump = name == "heroic strike" || name == "cleave";
    const bool sunder = name == "sunder armor";
    const bool fury = ai->HasSpell("bloodthirst");
    const bool arms = ai->HasSpell("mortal strike");
    const bool execute = name == "execute";
    const bool slam = name == "slam";
    if (!dump && !sunder && !execute && !slam && name != "rend") return true;
    if (!target || !target->IsAlive()) return false;
#ifdef MANGOSBOT_TWO
    // Arms needs Rend for Taste for Blood and retains its own Execute priority.
    if (name == "rend" && arms) return true;
    if (execute && !fury) return true;
    // A queued Bloodsurge action must not turn into a hard cast after expiration.
    if (slam && fury && !ai->HasAura("slam!", bot)) return false;
    if ((dump || sunder) && arms &&
        (CanPlanWarriorSpell(ai, "overpower", target) ||
         CanPlanWarriorSpell(ai, "execute", target))) return false;
#endif
    auto context = ai->GetAiObjectContext();
    uint32 reserve = 0;
    for (const char* mainAttack : { "bloodthirst", "mortal strike", "whirlwind" })
    {
#ifdef MANGOSBOT_TWO
        // Wrath Arms stays in Battle Stance; do not reserve for Fury's Whirlwind.
        if (arms && std::string(mainAttack) == "whirlwind") continue;
#endif
        const uint32 id = context->GetValue<uint32>("spell id", mainAttack)->Get();
        const SpellEntry* spell = sServerFacade.LookupSpellInfo(id);
        if (!spell || !ai->HasSpell(id)) continue;
        if (std::string(mainAttack) == "whirlwind" && SafeMeleeTargetCount(ai, 8.0f) == 0) continue;
        if (CanPlanWarriorSpell(ai, mainAttack, target)) return false;
        reserve = std::max(reserve, uint32(Spell::CalculatePowerCost(spell, bot)));
    }
    // Execute spends extra rage: native base cost is not its total cost. Allow
    // it only as a cooldown filler here, without pretending to reserve that rage.
    if (execute) return true;
    // Slam is a GCD filler; native cast checks still enforce cost and movement.
    if (slam) return true;
    const uint32 id = context->GetValue<uint32>("spell id", name)->Get();
    const SpellEntry* spell = sServerFacade.LookupSpellInfo(id);
    if (!spell) return false;
    // Queued strikes also replace rage-generating white swings. Require surplus
    // rage, not merely enough to pay the displayed ability cost.
    if (dump && (fury || arms) && bot->GetPower(POWER_RAGE) < 600) return false;
    return bot->GetPower(POWER_RAGE) >= reserve + uint32(Spell::CalculatePowerCost(spell, bot));
#endif
}
