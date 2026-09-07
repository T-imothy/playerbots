#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

namespace
{
    struct BurstRule { uint32 map, boss, aura, payload, link; };
    const BurstRule rules[] = {
#ifndef MANGOSBOT_ZERO
        {543, 17308, 30695, 30697, 0}, {543, 17308, 37566, 39298, 0},
        {555, 18708, 33711, 33686, 0}, {555, 18708, 38794, 33686, 0},
        {564, 22947, 41001, 40871, 40870},
#endif
        {0, 0, 0, 0, 0}
    };

    const BurstRule* Rule(Player* member, Unit*& boss)
    {
        for (const auto& rule : rules)
        {
            if (!rule.map || member->GetMapId() != rule.map) continue;
            const SpellAuraHolder* aura = member->GetSpellAuraHolder(rule.aura);
            Unit* caster = aura ? aura->GetCaster() : nullptr;
            if (caster && caster->IsInWorld() && caster->IsAlive() && caster->IsInCombat() &&
                !caster->HasCharmer() && member->IsInMap(caster) && caster->GetEntry() == rule.boss)
            { boss = caster; return &rule; }
        }
        return nullptr;
    }
}

bool ai::LinkedBurstThreats(PlayerbotAI* ai, EncounterPosition& plan, std::vector<encounter::Circle>& threats)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || !bot->GetGroup() ||
        bot->HasCharmer() || bot->IsBeingTeleported() || ai->IsRealPlayer() || !ai->CanMove()) return false;
    if (bot->GetMapId() != 543 && bot->GetMapId() != 555 && bot->GetMapId() != 564) return false;
    Unit* ownBoss = nullptr;
    const BurstRule* own = Rule(bot, ownBoss);
    if (ownBoss && ownBoss->GetVictim() == bot) return false;
    plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    if (own) { plan.source = bot->GetObjectGuid(); plan.boss = ownBoss->GetObjectGuid(); plan.spell = own->aura; }
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    bool relevant = own != nullptr;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!member || member == bot || !member->IsInWorld() || !member->IsAlive() ||
            !bot->IsInMap(member) || member->GetGroup() != bot->GetGroup() || member->IsBeingTeleported() ||
            member->HasCharmer() || std::fabs(here.z - member->GetPositionZ()) >= 8) continue;
        Unit* memberBoss = nullptr;
        const BurstRule* other = Rule(member, memberBoss);
        if (!own && !other) continue;
        if (memberBoss && memberBoss->GetVictim() == bot) return false;
        if (own && other && ownBoss != memberBoss) return false;
        float radius = std::max(own ? NativeEncounterSpellRadius(own->payload) : 0.0f,
            other ? NativeEncounterSpellRadius(other->payload) : 0.0f);
        // Fatal Attraction ends only when linked players separate beyond the
        // native link check. Its splash payload has a different radius.
        if (own && other && own->link && own->aura == other->aura)
            radius = std::max(radius, NativeEncounterSpellRadius(own->link));
        if (!std::isfinite(radius) || radius <= 0 || radius > 45) return false;
        const encounter::Point point{member->GetPositionX(), member->GetPositionY(), member->GetPositionZ()};
        threats.push_back({point, radius + 2});
        relevant = relevant || encounter::Distance2d(here, point) < radius + 10;
        if (!own && (plan.source.IsEmpty() || member->GetObjectGuid() < plan.source))
        { plan.source = member->GetObjectGuid(); plan.boss = memberBoss->GetObjectGuid(); plan.spell = other->aura; }
    }
    return relevant && !threats.empty();
}

EncounterPosition LinkedBurstPositionValue::Calculate()
{
    EncounterPosition plan;
    std::vector<encounter::Circle> threats;
    if (!LinkedBurstThreats(ai, plan, threats)) return plan;
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    uint64 seed = uint64(bot->GetObjectGuid().GetCounter()) * 2654435761ULL;
    Unit* boss = nullptr;
    const BurstRule* own = Rule(bot, boss);
    if (own && own->link)
    {
        // Native attraction teleports the linked players to one spot. Give
        // that set evenly spaced GUID-ordered directions, including humans,
        // rather than assuming random headings will separate adjacent bots.
        unsigned count = 1, rank = 0;
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (!member || member == bot || !member->IsInWorld() || !member->IsAlive() ||
                !bot->IsInMap(member) || member->IsBeingTeleported() || member->HasCharmer()) continue;
            Unit* source = nullptr;
            const BurstRule* other = Rule(member, source);
            if (!other || other->aura != own->aura || source != boss) continue;
            ++count;
            if (member->GetObjectGuid() < bot->GetObjectGuid()) ++rank;
        }
        seed = uint64(rank) * 997 / count;
    }
    unsigned checked = 0;
    for (const auto& point : encounter::SpreadCandidates(here, threats, seed, 40.0f))
    {
        if (!encounter::OutsideCircles(point, threats)) continue;
        if (++checked > 8) break;
        plan.active = true; plan.destination = point;
        if (ValidateEncounterDestination(ai, plan) && encounter::OutsideCircles(plan.destination, threats)) return plan;
    }
    plan.active = false;
    return plan;
}
