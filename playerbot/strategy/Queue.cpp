
#include "playerbot/playerbot.h"
#include "Action.h"
#include "Queue.h"

#include "playerbot/PlayerbotAIConfig.h"
using namespace ai;


void Queue::Push(ActionBasket *action)
{
    if (action)
    {
        const std::string actionName = action->getAction()->getName();
        auto existing = actionsByName.find(actionName);
        if (existing != actionsByName.end())
        {
            ActionBasket* basket = existing->second->second;
            if (basket->getRelevance() < action->getRelevance())
            {
                actions.erase(existing->second);
                basket->setRelevance(action->getRelevance());
                basket->setEvent(action->getEvent());
                existing->second = actions.emplace(basket->getRelevance(), basket);
            }

            ActionNode *actionNode = action->getAction();
            if (actionNode)
                delete actionNode;
            delete action;
            return;
        }

        auto inserted = actions.emplace(action->getRelevance(), action);
        actionsByName.emplace(actionName, inserted);
    }
}

ActionNode* Queue::Pop(ActionBasket* action)
{
    ActionBasket* selection = action;
    RelevanceQueue::iterator selectionIterator = actions.end();
    if (selection == nullptr)
    {
        if (!actions.empty())
            selectionIterator = std::prev(actions.end());
    }
    else
    {
        auto existing = actionsByName.find(selection->getAction()->getName());
        if (existing != actionsByName.end() && existing->second->second == selection)
            selectionIterator = existing->second;
    }

    if (selectionIterator != actions.end())
    {
        selection = selectionIterator->second;
        ActionNode* action = selection->getAction();
        actionsByName.erase(action->getName());
        actions.erase(selectionIterator);
        delete selection;
        return action;
    }

    return nullptr;
}

ActionBasket* Queue::Peek()
{
    return actions.empty() ? nullptr : std::prev(actions.end())->second;
}

int Queue::Size()
{
    return static_cast<int>(actions.size());
}

void Queue::RemoveExpired()
{
    for (auto iter = actions.begin(); iter != actions.end();)
    {
        ActionBasket* basket = iter->second;
        if (!sPlayerbotAIConfig.expireActionTime || !basket->isExpired(sPlayerbotAIConfig.expireActionTime / 1000))
        {
            ++iter;
            continue;
        }

        ActionNode* action = basket->getAction();
        actionsByName.erase(action->getName());
        iter = actions.erase(iter);
        if (action)
        {
            sLog.outDebug("Action %s is expired", action->getName().c_str());
            delete action;
        }
        delete basket;
    }
}
