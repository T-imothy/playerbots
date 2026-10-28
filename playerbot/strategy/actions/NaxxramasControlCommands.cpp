#include "playerbot/playerbot.h"
#include "NaxxramasControlCommands.h"
#include "BotCommandAccess.h"
#include "playerbot/strategy/generic/PullStrategy.h"
#include "playerbot/strategy/generic/ChatCommandHandlerStrategy.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/EncounterPositionValue.h"

using namespace ai;

namespace
{
    Unit* OwnedNaxxControl(PlayerbotAI* ai)
    {
        Player* bot = ai->GetBot();
        if (!bot || !bot->IsInWorld() || bot->GetMapId() != 533 || bot->IsBeingTeleported() ||
            bot->HasCharmer() || ai->IsRealPlayer()) return nullptr;
        Unit* charm = bot->GetCharm();
        return charm && charm->IsInWorld() && bot->IsInMap(charm) &&
            (charm->GetEntry() == 16803 || charm->GetEntry() == 16506) &&
            charm->HasCharmer(bot->GetObjectGuid()) ? charm : nullptr;
    }
    bool ReplacesControl(const std::string& command)
    {
        return command == "follow" || command == "stay" || command == "guard" || command == "free" ||
            command == "wander" || command == "flee" || command == "goaway" || command == "leave" ||
            command == "logout" || command == "reset ai";
    }
}

bool ai::NaxxramasControlAllowed(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    auto* context = ai->GetAiObjectContext();
    auto* blocked = context->GetValue<bool>("manual bool", "naxx control human override");
    auto* instance = context->GetValue<int32>("manual int", "naxx control override instance");
    const int32 currentInstance = bot->GetMapId() == 533 ? static_cast<int32>(bot->GetInstanceId()) : 0;
    if (bot->GetMapId() != 533 || !bot->IsInCombat() || instance->Get() != currentInstance)
        blocked->Set(false);
    instance->Set(currentInstance);
    return !blocked->Get();
}

void ai::ProcessNaxxramasControlCommands(PlayerbotAI* ai, bool commandsPending)
{
    Player* bot = ai->GetBot();
    if (!bot || !ai->GetAiObjectContext()) return;
    const bool suspended = !NaxxramasControlAllowed(ai);
    if (!bot->IsInWorld() || bot->GetMapId() != 533 || bot->IsBeingTeleported() || ai->IsRealPlayer()) return;
    const bool owned = OwnedNaxxControl(ai) != nullptr;
    // The owned-student controller returns before ordinary pull triggers. Retire
    // only its accepted native encounter request, through the normal end action.
    if (PullStrategy* pull = owned ? PullStrategy::Get(ai) : nullptr)
        if (pull->IsEncounterPreparationAllowed() && pull->HasPullStarted())
        {
            Unit* target = pull->GetTarget();
            const bool invalid = !target || !target->IsInWorld() || !target->IsAlive() || !bot->IsInMap(target);
            const bool expired = time(nullptr) - pull->GetPullStartTime() >= pull->GetMaxPullTime();
            const bool engaged = !invalid && NaxxramasEncounterEngaged(bot, target);
            if (invalid || expired || engaged) ai->DoSpecificAction("pull end", Event("naxx pull lifecycle"), true);
        }
    // A follow/stay order has already released the charm. Its later explicit
    // attack/pull must still reach the dispatcher and lift that human override.
    if (!commandsPending || (!owned && !suspended)) return;

    // HandleCommands only arms external triggers. Dispatch the real chat
    // strategy's mappings here; running the ordinary reaction engine could
    // select an unrelated movement/cast and cancel possession every update.
    ai->HandleCommands();
    ChatCommandHandlerStrategy commands(ai);
    std::list<TriggerNode*> nodes;
    commands.InitTriggers(nodes, BotState::BOT_STATE_REACTION);
    for (TriggerNode* node : nodes)
    {
        Trigger* trigger = ai->GetAiObjectContext()->GetTrigger(node->getName());
        if (!trigger) continue;
        node->setTrigger(trigger);
        Event event = trigger->Check();
        if (event.getSource().empty()) continue;
        // Consume before actions can reset strategy/context state. No duplicate
        // external command remains armed for the normal reaction engine.
        trigger->Reset();
        Player* requester = event.getOwner();
        if (!requester || !requester->isRealPlayer() || !CanManageBotCommands(ai, requester)) continue;
        const bool release = ReplacesControl(event.getSource());
        const bool resume = event.getSource() == "attack" || event.getSource() == "attack rti" ||
            event.getSource() == "pull" || event.getSource() == "pull rti";
        if (release)
        {
            if (PullStrategy* pull = PullStrategy::Get(ai)) pull->OnPullEnded();
            if (Unit* charm = OwnedNaxxControl(ai)) bot->BreakCharmOutgoing(charm);
        }
        NextAction** handlers = node->getHandlers();
        for (unsigned i = 0; handlers && handlers[i]; ++i)
            ai->DoSpecificAction(handlers[i]->getName(), event, true);
        NextAction::destroy(handlers);
        if (release || resume)
            ai->GetAiObjectContext()->GetValue<bool>("manual bool", "naxx control human override")->Set(release);
    }
    for (TriggerNode* node : nodes) delete node;
}
