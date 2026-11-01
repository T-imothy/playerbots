#include "playerbot/playerbot.h"
#include "NaxxramasPreparationActions.h"
#include "BotCommandAccess.h"
#include "RazuviousPullActions.h"
#include "playerbot/strategy/generic/PullStrategy.h"
#include "AI/ScriptDevAI/include/sc_instance.h"

using namespace ai;

namespace
{
    bool Member(Player* bot, Player* member)
    {
        return member && member->IsInWorld() && member->IsAlive() && !member->HasCharmer() &&
            !member->IsBeingTeleported() && bot->IsInMap(member) && member->GetGroup() == bot->GetGroup();
    }
    struct Request { Player* puller = nullptr; PullStrategy* strategy = nullptr; Unit* boss = nullptr; };
    Request Pending(PlayerbotAI* ai)
    {
        Player* bot = ai->GetBot();
        Request selected;
        if (!bot->IsInWorld() || !bot->IsAlive() || bot->GetMapId() != 533 || bot->HasCharmer() ||
            bot->IsBeingTeleported() || !bot->GetGroup() || bot->IsInCombat() || ai->IsRealPlayer() ||
            !ai->HasStrategy("dungeon", BotState::BOT_STATE_COMBAT)) return selected;
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* puller = ref->getSource();
            if (!Member(bot, puller) || puller->IsInCombat()) continue;
            PlayerbotAI* brain = puller->GetPlayerbotAI();
            PullStrategy* strategy = PullStrategy::Get(brain);
            if (!brain || brain->IsRealPlayer() || !strategy || !strategy->IsEncounterPreparationAllowed() ||
#ifndef MANGOSBOT_ZERO
                !strategy->IsPullPendingToStart() || strategy->HasPullActionIssued() ||
#endif
                !strategy->HasPullStarted() ||
                time(nullptr) - strategy->GetPullStartTime() >= strategy->GetMaxPullTime()) continue;
            Unit* target = strategy->GetTarget();
            Unit* requester = brain->GetUnit(strategy->GetRequester());
            if (!target || target->GetEntry() != 16060 || !target->IsInWorld() || !target->IsAlive() ||
                target->IsInCombat() || target->HasCharmer() || !bot->IsInMap(target) ||
                !requester || !requester->IsPlayer() || !Member(bot, static_cast<Player*>(requester)) ||
                !CanManageBotCommands(brain, static_cast<Player*>(requester))) continue;
            if (!selected.puller || puller->GetObjectGuid() < selected.puller->GetObjectGuid())
                selected = {puller, strategy, target};
        }
        return selected;
    }
}

bool ai::NaxxramasGothikPreparationPlan(PlayerbotAI* ai, EncounterPosition& plan, bool& groupReady)
{
    groupReady = false;
    const Request request = Pending(ai);
    if (!request.puller) return false;
    Player* bot = ai->GetBot();
#ifdef MANGOSBOT_ZERO
    // Followers must hold their prepared side through the tank's approach,
    // cast and projectile travel. The puller itself must remain free to shoot.
    // Cancellation, original deadline and actual boss engagement end this hold.
    if (bot == request.puller && !request.strategy->IsPullPendingToStart()) return false;
#endif
    auto* instance = dynamic_cast<ScriptedInstance*>(bot->GetMap()->GetInstanceData());
    GameObject* gate = instance ? instance->GetSingleGameObjectFromStorage(181170) : nullptr;
    if (!gate || !gate->IsInWorld() || !bot->IsInMap(gate) || gate->GetGoState() == GO_STATE_READY ||
        bot->GetDistance(gate) > 100.0f || request.boss->GetDistance(gate) > 100.0f) return false;

    std::vector<Player*> members;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        if (Member(bot, ref->getSource())) members.push_back(ref->getSource());
    std::sort(members.begin(), members.end(), [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
    bool allReady = true, assigned = false;
    unsigned roles[3][2] = {};
    const auto role = [&](Player* member) { return ai->IsTank(member) ? 0u : ai->IsHeal(member) ? 1u : 2u; };
    // Humans keep their chosen side. Balance controllable bots around them.
    for (Player* member : members)
        if (!member->GetPlayerbotAI() || member->GetPlayerbotAI()->IsRealPlayer())
            if (member->GetDistance(gate) < 50 && std::fabs(member->GetPositionY() - gate->GetPositionY()) >= 8)
                ++roles[role(member)][member->GetPositionY() > gate->GetPositionY() ? 1 : 0];
    // The commanded puller stays on the living side nearest Gothik's balcony.
    auto puller = std::find(members.begin(), members.end(), request.puller);
    if (puller != members.end()) std::rotate(members.begin(), puller, puller + 1);
    for (Player* member : members)
    {
        PlayerbotAI* brain = member->GetPlayerbotAI();
        if (!brain || brain->IsRealPlayer()) continue;
        const unsigned category = role(member);
        unsigned side = member == request.puller ? 0u : (roles[category][0] <= roles[category][1] ? 0u : 1u);
#ifdef MANGOSBOT_ZERO
        // Native Classic spectral adds are immune to all magic schools.
        // Keep physical DPS (including hunters) on that side, casters living;
        // tanks and healers remain balanced around humans' chosen positions.
        if (category == 2) side = member->getClass() == CLASS_HUNTER || !ai->IsRanged(member) ? 1u : 0u;
#endif
        const unsigned slot = roles[category][side]++;
        const encounter::Point destination{gate->GetPositionX() + 4.0f + float(slot % 3) * 2.0f,
            gate->GetPositionY() + (side ? 12.0f : -12.0f) + float(category) * (side ? 2.0f : -2.0f), gate->GetPositionZ()};
        if (member->IsInCombat() || member->GetDistance(destination.x, destination.y, destination.z) > 4.0f ||
            !brain->HasStrategy("dungeon", BotState::BOT_STATE_COMBAT)) allReady = false;
        if (member == bot)
        {
            assigned = true; plan.active = true; plan.map = 533; plan.instance = bot->GetInstanceId();
            plan.boss = request.boss->GetObjectGuid(); plan.source = gate->GetObjectGuid(); plan.spell = 16060;
            plan.destination = destination;
        }
    }
    groupReady = allReady && roles[0][0] && roles[0][1] && roles[1][0] && roles[1][1];
#ifdef MANGOSBOT_ZERO
    groupReady = groupReady && roles[2][0] && roles[2][1];
#endif
    return assigned;
}

bool ai::NaxxramasGothikPullReady(PlayerbotAI* ai)
{
    PullStrategy* strategy = PullStrategy::Get(ai);
    Unit* target = strategy ? strategy->GetTarget() : nullptr;
    if (!strategy || !strategy->IsEncounterPreparationAllowed()) return true;
    if (ai->GetBot()->GetMapId() != 533 || !target || target->GetEntry() != 16060 || target->IsInCombat()) return true;
    EncounterPosition plan; bool ready = false;
    return NaxxramasGothikPreparationPlan(ai, plan, ready) && ready;
}

bool NaxxramasGothikPrepareAction::isUseful()
{
    EncounterPosition plan; bool ready;
    return NaxxramasGothikPreparationPlan(ai, plan, ready) &&
#ifdef MANGOSBOT_ZERO
        bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 4.0f;
#else
        EncounterMovementRequired(bot, plan.destination);
#endif
}
bool NaxxramasGothikPrepareAction::Execute(Event&)
{
    EncounterPosition plan; bool ready;
    if (!NaxxramasGothikPreparationPlan(ai, plan, ready) || !ai->CanMove() || bot->IsNonMeleeSpellCasted(false) ||
        !EncounterMovementRequired(bot, plan.destination)) return false;
    const auto station = plan.destination;
    if (!ValidateEncounterDestination(ai, plan))
    {
#ifdef MANGOSBOT_ZERO
        // Preparation already admits a four-yard station. A single exact
        // coordinate can be outside the native navigation mesh even when a
        // nearby point on the same assigned side is walkable. Try a bounded
        // set inside that existing station; never accept a truncated path.
        bool found = false;
        for (const auto offset : {encounter::Point{0,-2,0}, encounter::Point{0,2,0},
            encounter::Point{-2,0,0}, encounter::Point{2,0,0}, encounter::Point{-2,-2,0},
            encounter::Point{2,-2,0}, encounter::Point{-2,2,0}, encounter::Point{2,2,0}})
        {
            EncounterPosition candidate = plan;
            candidate.destination = {station.x+offset.x, station.y+offset.y, station.z};
            if (ValidateEncounterDestination(ai, candidate))
            {
                const auto& p = candidate.destination;
                const float dx=p.x-station.x, dy=p.y-station.y, dz=p.z-station.z;
                if (dx*dx+dy*dy+dz*dz <= 16.0f) { plan=candidate; found=true; break; }
            }
        }
        if (!found) return false;
#else
        return false;
#endif
    }
    const auto& p = plan.destination;
    return MoveTo(plan.map, p.x, p.y, p.z, false, IsReaction(), false, true);
}
float PreserveNaxxramasPreparation::GetValue(Action* action)
{
    if (!action) return 1.0f;
    if (RazuviousPreparationMultiplier(ai, action) == 0.0f) return 0.0f;
    const auto& name = action->getName();
    if (name != "follow" && name != "reach melee" && name != "reach spell" && name != "set behind" &&
        name != "return to pull position") return 1.0f;
    EncounterPosition plan; bool ready;
    return NaxxramasGothikPreparationPlan(ai, plan, ready) || NaxxramasThaddiusPreparationPlan(ai, plan, ready) ? 0.0f : 1.0f;
}
