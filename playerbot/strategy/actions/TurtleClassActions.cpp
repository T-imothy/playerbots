#include "playerbot/playerbot.h"
#include "TurtleClassActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/AiFactory.h"
#include "Spells/SpellAuras.h"
#include "Objects/Pet.h"
#include "playerbot/strategy/CasterCombatPolicy.h"

using namespace ai;

bool TurtleClassSpellAction::IsMelee() const
{
    switch (ability)
    {
    case TurtleAbility::MasterStrike: case TurtleAbility::SurpriseAttack:
    case TurtleAbility::NoxiousAssault: case TurtleAbility::ShadowOfDeath:
    case TurtleAbility::MarkForDeath: case TurtleAbility::LightningStrike:
    case TurtleAbility::Carve: case TurtleAbility::Bulwark:
    case TurtleAbility::EarthshakerSlam: case TurtleAbility::SavageBite:
        return true;
    default: return false;
    }
}

std::string TurtleClassSpellAction::GetTargetName()
{
    switch (ability)
    {
    case TurtleAbility::SmokeBomb: case TurtleAbility::Enlighten:
    case TurtleAbility::Ascendance: case TurtleAbility::AncestralSwiftness:
    case TurtleAbility::TreeOfLife: case TurtleAbility::FeralBarkskin:
    case TurtleAbility::Detection: case TurtleAbility::Reshift:
        return "self target";
    case TurtleAbility::PowerOverwhelming: return "pet target";
    case TurtleAbility::SpiritLink: return "party member to heal";
    default: return "current target";
    }
}

std::string TurtleClassSpellAction::GetReachActionName()
{
    return IsMelee() ? "reach melee" : CastSpellAction::GetReachActionName();
}

ActionThreatType TurtleClassSpellAction::getThreatType()
{
    if (ability == TurtleAbility::Earthquake || ability == TurtleAbility::Carve)
        return ActionThreatType::ACTION_THREAT_AOE;
    return CastSpellAction::getThreatType();
}

bool TurtleClassSpellAction::isUseful()
{
    if (!bot->HasSpell(GetDecisionSpellId()) || !CastSpellAction::isUseful())
        return false;
    Unit* target = GetTarget();
    if (!target || !target->IsAlive() || !target->IsInWorld() || target->GetMap() != bot->GetMap())
        return false;
    if (bot->IsNonMeleeSpellCasted(true))
        return false; // A new cooldown must not repeatedly cancel ongoing casts.

    const float hp = bot->GetHealthPercent();
    const uint32 combo = bot->GetComboTargetGuid() == target->GetObjectGuid() ? bot->GetComboPoints() : 0;
    switch (ability)
    {
    case TurtleAbility::ArcaneSurge:
        // Native CheckCast enforces the resisted-spell aura state and ranks.
        return bot->IsInCombat();
    case TurtleAbility::PainSpike:
        // Its damage heals back shortly afterward; use as a finisher.
        return target->GetHealthPercent() < 20;
    case TurtleAbility::SearingShot:
    {
        Item* weapon = bot->GetWeaponForAttack(RANGED_ATTACK, true, true);
        return weapon && weapon->GetProto()->Class == ITEM_CLASS_WEAPON &&
            weapon->GetProto()->SubClass == ITEM_SUBCLASS_WEAPON_BOW;
    }
    case TurtleAbility::EarthshakerSlam:
        return ai->IsTank(bot) && target->IsInCombat() && target->GetVictim() && target->GetVictim() != bot;
    case TurtleAbility::SavageBite:
        return bot->GetPower(POWER_RAGE) >= 250;
    case TurtleAbility::FeralBarkskin:
        return hp < 60 && !bot->GetAttackers().empty() && !ai->HasAura(GetSpellName(), bot);
    case TurtleAbility::LightOfAnshe:
        return target->GetHealthPercent() > 30 && !ai->HasAura(GetSpellName(), target, false, true);
    case TurtleAbility::Detection:
        return !ai->HasAura(GetSpellName(), bot);
    case TurtleAbility::Reshift:
        return bot->IsInCombat() && (bot->HasAuraType(SPELL_AURA_MOD_ROOT) || bot->HasAuraType(SPELL_AURA_MOD_DECREASE_SPEED));
    case TurtleAbility::Icicles:
        // The native spell roots its caster and punishes damage taken.
        return hp > 80 && bot->GetAttackers().empty() && target->GetVictim() != bot &&
            target->GetHealthPercent() > 35;
    case TurtleAbility::ArcaneRupture:
        return bot->GetPower(POWER_MANA) * 100 > bot->GetMaxPower(POWER_MANA) * 35 &&
            !ai->HasAura(52502, bot);
    case TurtleAbility::SurpriseAttack:
    case TurtleAbility::NoxiousAssault:
    case TurtleAbility::MarkForDeath:
        return combo < 5 &&
            (ability != TurtleAbility::NoxiousAssault || bot->GetWeaponForAttack(OFF_ATTACK, true, true));
    case TurtleAbility::ShadowOfDeath:
        return combo >= 5 && target->GetHealthPercent() > 40 &&
            ai->HasAura("slice and dice", bot) && !ai->HasAura(GetSpellName(), target, false, true);
    case TurtleAbility::SmokeBomb:
        // Smoke also protects enemies standing in it; reserve it for escape.
        return hp < 30 && !bot->GetAttackers().empty() && ai->HasStrategy("flee", BotState::BOT_STATE_COMBAT);
    case TurtleAbility::Enlighten:
        return hp > 80 && !ai->HasAura(GetSpellName(), bot);
    case TurtleAbility::Ascendance:
    case TurtleAbility::AncestralSwiftness:
    {
        Unit* patient = AI_VALUE(Unit*, "party member to heal");
        return !ai->HasAura(GetSpellName(), bot) &&
            (hp < 40 || (patient && patient->IsAlive() && patient->GetMap() == bot->GetMap() && patient->GetHealthPercent() < 40));
    }
    case TurtleAbility::SpiritLink:
    {
        if (!bot->GetGroup() || target == bot || target->GetHealthPercent() >= 50 ||
            ai->HasAura(GetSpellName(), target))
            return false;
        uint32 healthyRecipients = 0;
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (!member || member == target || !member->IsInWorld() || !member->IsAlive() ||
                member->GetMap() != bot->GetMap() || member->GetDistance(target) > 35)
                continue;
            if (member->GetHealthPercent() < 70)
                return false;
            ++healthyRecipients;
        }
        return healthyRecipients >= 2;
    }
    case TurtleAbility::TreeOfLife:
        // Healing Touch is forbidden in this form. Enter during preparation;
        // native shapeshift/casting policy may leave it when another heal needs it.
        return !bot->IsInCombat() && bot->GetGroup() && ai->IsHeal(bot) &&
            hp > 80 && !ai->HasAura(GetSpellName(), bot);
    case TurtleAbility::DarkHarvest:
    {
        uint32 dots = 0;
        for (Aura* aura : target->GetAurasByType(SPELL_AURA_PERIODIC_DAMAGE))
            if (aura && aura->GetCasterGuid() == bot->GetObjectGuid())
                ++dots;
        return dots >= 2 && target->GetHealthPercent() > 20;
    }
    case TurtleAbility::PowerOverwhelming:
        return target == bot->GetPet() && target->IsInCombat() &&
            target->GetHealthPercent() > 75 && target->GetAttackers().empty() &&
            !ai->HasAura(GetSpellName(), target);
    case TurtleAbility::Earthquake:
    case TurtleAbility::Carve:
    {
        if (!ai->HasStrategy("aoe", BotState::BOT_STATE_COMBAT)) return false;
        const SpellEntry* spell = sServerFacade.LookupSpellInfo(GetDecisionSpellId());
        if (!spell) return false;
        float radius = 0.0f;
        for (unsigned i = 0; i < MAX_EFFECT_INDEX; ++i)
            radius = std::max(radius, GetSpellRadius(sSpellRadiusStore.LookupEntry(spell->EffectRadiusIndex[i])));
        // Earthquake's native aftershock uses the same radius as its ground
        // effect. Carve is a caster cone; conservatively check the whole circle.
        return radius > 0 && CasterAreaSafe(ai, ability == TurtleAbility::Carve ? bot : target, radius);
    }
    default:
        return true;
    }
}

namespace
{
uint32 CreatedStoneItem(PlayerbotAI* ai, std::string const& spellName)
{
    uint32 id = ai->GetAiObjectContext()->GetValue<uint32>("spell id", spellName)->Get();
    const SpellEntry* spell = sServerFacade.LookupSpellInfo(id);
    if (!spell || !ai->GetBot()->HasSpell(id)) return 0;
    for (unsigned i = 0; i < MAX_EFFECT_INDEX; ++i)
        if (spell->Effect[i] == SPELL_EFFECT_CREATE_ITEM && spell->EffectItemType[i])
            return spell->EffectItemType[i];
    return 0;
}
}

bool TurtleCreateStoneAction::isUseful()
{
    uint32 item = CreatedStoneItem(ai, GetSpellName());
    return item && !bot->IsInCombat() && !bot->HasItemCount(item, 1) && CastSpellAction::isUseful();
}
uint32 TurtleUseStoneAction::GetItemId()
{
    return CreatedStoneItem(ai, "create " + stone);
}
bool TurtleUseStoneAction::isUseful()
{
    if (!bot->IsInCombat() || !UseItemIdAction::isUseful()) return false;
    const ItemPrototype* proto = sObjectMgr.GetItemPrototype(GetItemId());
    if (!proto) return false;
    for (unsigned i = 0; i < MAX_ITEM_PROTO_SPELLS; ++i)
        if (proto->Spells[i].SpellId && bot->HasAura(proto->Spells[i].SpellId))
            return false;
    if (stone == "felstone")
        return bot->GetHealthPercent() < 65 || (bot->GetPet() && bot->GetPet()->GetHealthPercent() < 50);
    if (stone == "voidstone")
        return bot->GetGroup() && !ai->IsTank(bot) && !bot->GetAttackers().empty();
    // Wrathstone increases fire threat. Reserve it for an assigned tank.
    return stone == "wrathstone" && ai->IsTank(bot);
}
