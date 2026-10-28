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
            if (!brain || brain->IsRealPlayer() || !strategy || !strategy->IsEncounterPreparationAllowed() || !strategy->IsPullPendingToStart() ||
                !strategy->HasPullStarted() || strategy->HasPullActionIssued() ||
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
        const unsigned side = member == request.puller ? 0u : (roles[category][0] <= roles[category][1] ? 0u : 1u);
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
    return NaxxramasGothikPreparationPlan(ai, plan, ready) && EncounterMovementRequired(bot, plan.destination);
}
bool NaxxramasGothikPrepareAction::Execute(Event&)
{
    EncounterPosition plan; bool ready;
    if (!NaxxramasGothikPreparationPlan(ai, plan, ready) || !ai->CanMove() || bot->IsNonMeleeSpellCasted(false) ||
        !EncounterMovementRequired(bot, plan.destination) || !ValidateEncounterDestination(ai, plan)) return false;
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
    return NaxxramasGothikPreparationPlan(ai, plan, ready) ? 0.0f : 1.0f;
}
