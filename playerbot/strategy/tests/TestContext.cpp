#include "TestContext.h"
#include "playerbot/PlayerbotMgr.h"

using namespace ai;

void TestContext::Reset()
{
    script.clear();
    pc = 0;
    observing = false;
    testStartTime = 0;
    monitorTime = 0;
    waitTime = 0;
    monitors.clear();
    deferredCleanups.clear();
    cleanupPc = 0;
    cleanupPrepared = false;
    combatSeen = false;
    whoResponded = false;
    result = TestResult::PENDING;
    resultMessage.clear();
    testName.clear();
    testStartPosition = WorldPosition();
    destinationPosition = GuidPosition();
    partyXpStart = 0;
    partyXpCaptured = false;
    observedDeadMobs.clear();
    resurrectMapId = 0;
    resurrectX = resurrectY = resurrectZ = 0.0f;
    hasResurrectRequest = false;
    groupMembersSeenOnMap.clear();

    for (ObjectGuid const& guid : spawnedBots)
    {
        if (guid && guid.IsPlayer())
        {
            sRandomPlayerbotMgr.DeleteBot(guid, true);
        }
    }
    spawnedBots.clear();
    deliveredGroupMembers.clear();
    groupOnMapExpected = 0;
    lootStackSeen = false;
    actionSpamArmed = false;
#ifdef MANTECH_RAID_LAB
    raidLabEventStarted = 0;
    raidLabEventFailureStarted = 0;
    raidLabEventStage = 0;
    raidLabStageStarted = 0;
    raidLabPostKillStarted = 0;
    raidLabProvisionStarted = 0;
    raidLabPatrolWaitStarted = 0;
    raidLabPullGuid.Clear();
    raidLabPullStarted = 0;
    raidLabPackId = 0;
    raidLabGridWarmups.clear();
    raidLabPackMembers.clear();
    raidLabPackDead.clear();
#endif
}

void TestContext::RecordDeliveredGroupMember(ObjectGuid guid)
{
    std::lock_guard<std::mutex> lock(groupDeliveryMutex);
    deliveredGroupMembers.insert(guid);
}

std::set<ObjectGuid> TestContext::GetDeliveredGroupMembers()
{
    std::lock_guard<std::mutex> lock(groupDeliveryMutex);
    return deliveredGroupMembers;
}
