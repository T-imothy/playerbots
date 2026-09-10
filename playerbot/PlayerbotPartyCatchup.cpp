#include "playerbot/playerbot.h"
#include "PlayerbotPartyCatchup.h"
#include "PartyCatchupMath.h"
#include "PlayerbotAIConfig.h"
#include "Globals/ObjectMgr.h"
#include <chrono>
#include <mutex>
#include <unordered_map>

namespace ai
{
namespace
{
    using Clock = std::chrono::steady_clock;
    struct Pace
    {
        uint32 group = 0, leader = 0;
        uint64 gap = 0;
        double activeSeconds = 0, baseXP = 0;
        Clock::time_point lastAward, touched;
    };
    std::mutex paceMutex;
    std::unordered_map<uint32, Pace> paces;

    PartyCatchupStatus Inspect(Player* bot, Player*& leader, uint64& gap)
    {
        PartyCatchupStatus result;
        leader = nullptr; gap = 0;
        if (!bot || !bot->GetPlayerbotAI()) { result.reason = "human"; return result; }
        if (!sPlayerbotAIConfig.partyCatchupEnabled) { result.reason = "disabled"; return result; }
        Group* group = bot->GetGroup();
        if (!group) return result;
        leader = sObjectMgr.GetPlayer(group->GetLeaderGuid());
        if (!leader || !leader->IsInWorld()) { result.reason = "leader_offline"; return result; }
        result.leader = leader->GetName(); result.leaderLevel = leader->GetLevel();
        bool mixed = false;
        for (GroupReference* ref = group->GetFirstMember(); ref; ref = ref->next())
            if (Player* member = ref->getSource())
                if (!member->GetPlayerbotAI() && member->IsInWorld()) { mixed = true; break; }
        if (!mixed) { result.reason = "bot_only_party"; return result; }
        if (bot->GetLevel() >= leader->GetLevel()) { result.reason = "caught_up"; return result; }
        if (!bot->IsInWorld() || !bot->IsAlive() || !leader->IsAlive()) { result.reason = "dead"; return result; }
        if (bot->IsBeingTeleported() || leader->IsBeingTeleported() ||
            bot->IsTaxiFlying() || leader->IsTaxiFlying() || bot->GetTransport() || leader->GetTransport())
        { result.reason = "traveling"; return result; }
        if (bot->GetMapId() != leader->GetMapId() || bot->GetInstanceId() != leader->GetInstanceId() ||
            !bot->IsWithinDistInMap(leader, sPlayerbotAIConfig.partyCatchupRadiusYards))
        { result.reason = "too_far"; return result; }
        for (uint32 level = bot->GetLevel(); level < leader->GetLevel(); ++level)
            gap += sObjectMgr.GetXPForLevel(level);
        gap = gap > bot->GetUInt32Value(PLAYER_XP) ? gap - bot->GetUInt32Value(PLAYER_XP) : 0;
        result.reason = gap ? "active" : "caught_up";
        return result;
    }

    PartyCatchupStatus Calculate(Player* bot, uint64 normalXP, uint32* bonus)
    {
        Player* leader; uint64 gap;
        PartyCatchupStatus result = Inspect(bot, leader, gap);
        if (!bot || !bot->GetPlayerbotAI()) return result;
        auto now = Clock::now();
        std::lock_guard<std::mutex> lock(paceMutex);
        if (result.reason != "active")
        {
            paces.erase(bot->GetGUIDLow()); // No boost or clock continues outside eligibility.
            return result;
        }
        // Opportunistic bounded cleanup, no database activity or per-tick scan.
        if (paces.size() > 128)
            for (auto it = paces.begin(); it != paces.end();)
                if (now - it->second.touched > std::chrono::minutes(10)) it = paces.erase(it); else ++it;
        Pace& pace = paces[bot->GetGUIDLow()];
        if (pace.group != bot->GetGroup()->GetId() || pace.leader != leader->GetGUIDLow())
        {
            pace = Pace(); pace.group = bot->GetGroup()->GetId(); pace.leader = leader->GetGUIDLow();
        }
        pace.touched = now; pace.gap = gap;
        double elapsed = pace.lastAward.time_since_epoch().count() ?
            std::chrono::duration<double>(now - pace.lastAward).count() : 0;
        if (normalXP)
        {
            // Only short intervals between earned awards count as productive play.
            // Long travel/AFK gaps cannot mature an XP boost.
            if (elapsed > 0 && elapsed <= 120) pace.activeSeconds += elapsed;
            pace.lastAward = now;
        }
        double fallbackRate = std::max(1.0, double(sObjectMgr.GetXPForLevel(bot->GetLevel())) / 1800.0);
        double rate = pace.activeSeconds >= 60 ? std::max(0.1, pace.baseXP / pace.activeSeconds) : fallbackRate;
        double remaining = std::max(600.0, double(sPlayerbotAIConfig.partyCatchupTargetSeconds) - pace.activeSeconds);
        result.multiplier = PartyCatchupMultiplier(double(gap), rate, remaining,
            sPlayerbotAIConfig.partyCatchupMaximumMultiplier);
        if (bonus) *bonus = PartyCatchupBonus(normalXP, gap, result.multiplier);
        pace.baseXP += normalXP; // Never feed catch-up XP back into the estimator.
        return result;
    }
}
uint32_t AwardPartyCatchupBonus(Player* bot, uint64_t normalXP)
{
    uint32 bonus = 0;
    Calculate(bot, normalXP, &bonus);
    return bonus;
}
PartyCatchupStatus GetPartyCatchupStatus(Player* bot) { return Calculate(bot, 0, nullptr); }
void ClearPartyCatchup(Player* bot)
{
    if (!bot) return;
    std::lock_guard<std::mutex> lock(paceMutex);
    paces.erase(bot->GetGUIDLow());
}
}
