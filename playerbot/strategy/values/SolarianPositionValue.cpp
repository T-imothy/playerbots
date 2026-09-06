#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/ServerFacade.h"

using namespace ai;

float ai::SolarianBurstRadius()
{
#ifndef MANGOSBOT_ZERO
    const SpellEntry* aura = sServerFacade.LookupSpellInfo(42783);
    // Native WrathOfTheAstromancer::OnApply dispatches the next effect's
    // simple value on expiry. EffectTriggerSpell is the application visual,
    // NOT the bomb. Pre-nerf 33045 has a different jumping mechanic.
    if (aura && aura->Effect[EFFECT_INDEX_0] == SPELL_EFFECT_APPLY_AURA &&
        aura->CalculateSimpleValue(EFFECT_INDEX_1) == 42787)
        return NativeEncounterSpellRadius(42787);
#endif
    return 0;
}

bool ai::SolarianBurstThreats(PlayerbotAI* ai, EncounterPosition& plan,
    std::vector<encounter::Circle>& threats)
{
#ifndef MANGOSBOT_ZERO
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        bot->GetMapId() != 550 || !bot->GetGroup()) return false;
    const bool own = bot->HasAura(42783);
    const float radius = SolarianBurstRadius();
    if (!std::isfinite(radius) || radius <= 0 || radius > 45) return false;
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId(); plan.spell = 42783;
    if (own) plan.source = bot->GetObjectGuid();
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!member || member == bot || !member->IsInWorld() || !member->IsAlive() ||
            member->IsBeingTeleported() || member->HasCharmer() || member->GetGroup() != bot->GetGroup() ||
            !bot->IsInMap(member) || std::fabs(member->GetPositionZ() - here.z) >= radius + 2) continue;
        if (!own && !member->HasAura(42783)) continue;
        threats.push_back({{member->GetPositionX(), member->GetPositionY(), member->GetPositionZ()}, radius + 2});
        if (!own && (plan.source.IsEmpty() || member->GetObjectGuid() < plan.source)) plan.source = member->GetObjectGuid();
    }
    if (threats.empty()) return false;
    // A live tank must not drag the boss after a fleeing carrier. The raid
    // separates from that tank; once native threat changes, it can move normally.
    for (const auto& guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("attackers")->Get())
    {
        Unit* boss = ai->GetUnit(guid);
        if (boss && boss->IsInWorld() && bot->IsInMap(boss) && boss->IsAlive() && !boss->HasCharmer() &&
            boss->IsInCombat() && boss->GetEntry() == 18805 && boss->GetVictim() == bot) return false;
    }
    bool relevant = own;
    for (const auto& threat : threats)
        relevant = relevant || encounter::Distance2d(here, threat.center) < threat.radius + 8;
    return relevant;
#else
    return false;
#endif
}

EncounterPosition SolarianPositionValue::Calculate()
{
    EncounterPosition plan;
    std::vector<encounter::Circle> threats;
    if (!SolarianBurstThreats(ai, plan, threats)) return plan;
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
