#pragma once
#include "Common.h"
#include "ObjectGuid.h"
#include "WorldPacket.h"
#include "strategy/Event.h"
#include <functional>
#include <future>
#include <memory>
#include <vector>

using BotChatPackets = std::vector<std::pair<WorldPacket, uint32>>;
// Identity only: workers must never dereference the owning AI/session.
struct BotChatLifetime {};
void StartPlayerbotChatWorkers(uint32 limit);
void StopPlayerbotChatWorkers();
std::future<BotChatPackets> SubmitPlayerbotChatGeneration(std::function<BotChatPackets()> work);
void QueuePlayerbotChatPackets(ObjectGuid guid, uint32 account,
    std::weak_ptr<BotChatLifetime> lifetime, std::future<BotChatPackets> packets, bool incoming, ai::EventOwner recipient = {});
void UpdatePlayerbotChatPackets();
