#include "ActionBasket.h"

#include <iterator>
#include <map>
#include <unordered_map>

#pragma once
namespace ai
{
class Queue
{
public:
    Queue(void) {}
public:
    ~Queue(void) {}
public:
	void Push(ActionBasket *action);
	ActionNode* Pop(ActionBasket* action = nullptr);
    ActionBasket* Peek();
	int Size();
	void RemoveExpired();
private:
    using RelevanceQueue = std::multimap<float, ActionBasket*>;
    RelevanceQueue actions;
    std::unordered_map<std::string, RelevanceQueue::iterator> actionsByName;
};
}
