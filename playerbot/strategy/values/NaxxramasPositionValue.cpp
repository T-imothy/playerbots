#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

uint32 ai::NaxxramasBurstAura(Unit* unit)
{
    if (!unit) return 0;
    if (unit->HasAura(28169)) return 28169; // Grobbulus Mutating Injection
    return unit->HasAura(27819) ? 27819 : 0; // Kel'Thuzad Detonate Mana
}

float ai::NaxxramasBurstRadius(uint32 aura)
{
    // These payloads are dispatched by the native scripts/aura handlers, not
    // necessarily by EffectTriggerSpell in the aura's database record.
    if (aura == 28169)
        return std::max(NativeEncounterSpellRadius(28206), NativeEncounterSpellRadius(28322));
    return aura == 27819 ? NativeEncounterSpellRadius(27820) : 0.0f;
}

bool ai::NaxxramasBurstThreats(PlayerbotAI* ai, EncounterPosition& plan,
    std::vector<encounter::Circle>& threats)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        bot->GetMapId() != 533 || !bot->GetGroup()) return false;
    const uint32 ownAura = NaxxramasBurstAura(bot);
    const float ownRadius = NaxxramasBurstRadius(ownAura);
    if (ownAura && (!std::isfinite(ownRadius) || ownRadius <= 0 || ownRadius > 45)) return false;
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    if (ownAura) { plan.spell = ownAura; plan.source = bot->GetObjectGuid(); }
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!member || member == bot || !member->IsInWorld() || !member->IsAlive() ||
            member->IsBeingTeleported() || member->HasCharmer() || member->GetGroup() != bot->GetGroup() || !bot->IsInMap(member) ||
            std::fabs(member->GetPositionZ() - here.z) >= 8) continue;
        const uint32 aura = NaxxramasBurstAura(member);
        if (!ownAura && !aura) continue;
        const float memberRadius = NaxxramasBurstRadius(aura);
        if (aura && (!std::isfinite(memberRadius) || memberRadius <= 0 || memberRadius > 45)) continue;
        const float radius = std::max(ownRadius, memberRadius);
        threats.push_back({{member->GetPositionX(), member->GetPositionY(), member->GetPositionZ()}, radius + 2});
        if (!ownAura && (plan.source.IsEmpty() || member->GetObjectGuid() < plan.source))
        { plan.spell = aura; plan.source = member->GetObjectGuid(); }
    }
    if (threats.empty()) return false;

    // A tank must not pull a live boss through the group to avoid another
    // player's burst. Other bots still observe and separate from that tank.
    for (const auto& guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("attackers")->Get())
    {
        Unit* enemy = ai->GetUnit(guid);
        if (enemy && enemy->IsInWorld() && bot->IsInMap(enemy) && enemy->IsAlive() &&
            enemy->IsInCombat() && (enemy->GetEntry() == 15931 || enemy->GetEntry() == 15990) &&
            enemy->GetVictim() == bot) return false;
    }
    bool relevant = ownAura != 0;
    for (const auto& threat : threats)
        relevant = relevant || encounter::Distance2d(here, threat.center) < threat.radius + 8;
    return relevant;
}

EncounterPosition NaxxramasPositionValue::Calculate()
{
    EncounterPosition plan;
    std::vector<encounter::Circle> threats;
    if (!NaxxramasBurstThreats(ai, plan, threats)) return plan;
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    unsigned checked = 0;
    for (const auto& point : encounter::EscapeCircles(here, threats))
    {
        if (++checked > 8) break;
        plan.active = true; plan.destination = point;
        if (ValidateEncounterDestination(ai, plan) && encounter::OutsideCircles(plan.destination, threats)) return plan;
    }
    plan.active = false;
    return plan;
}
