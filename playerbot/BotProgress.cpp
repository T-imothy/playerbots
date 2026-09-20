#include "playerbot/playerbot.h"
#include "PlayerbotDiagnostics.h"
#include "BotProgress.h"

using namespace ai;

bool PlayerbotAI::IgnoreUnreachableTarget(Unit* target)
{
    if (!sPlayerbotAIConfig.unreachableTargetTimeout || !target || HasActivePlayerMaster() ||
        target->GetTypeId()!=TYPEID_UNIT || target->GetVictim()) return false;
    unreachableTargets.SetDomain(bot->GetMapId(),bot->GetInstanceId());
    return unreachableTargets.Contains(target->GetObjectGuid().GetRawValue(),WorldTimer::getMSTime());
}

bool PlayerbotAI::ObserveTargetProgress(Unit* target, float distance, bool inLos)
{
    unreachableTargets.SetDomain(bot->GetMapId(),bot->GetInstanceId());
    bool permitted=target && bot->IsAlive() && !HasActivePlayerMaster() &&
        target->GetTypeId()==TYPEID_UNIT && !target->GetVictim() &&
        bot->IsValidAttackTarget(target) && !inLos && !bot->IsBeingTeleported() &&
        !bot->IsTaxiFlying() && !bot->GetTransport() && !bot->HasCharmer() &&
        !bot->IsNonMeleeSpellCasted(true);
    uint32 now=WorldTimer::getMSTime();
    bool blocked=unreachableTargets.Observe(target ? target->GetObjectGuid().GetRawValue() : 0,
        now,bot->GetPositionX(),bot->GetPositionY(),distance,permitted,
        sPlayerbotAIConfig.unreachableTargetTimeout,sPlayerbotAIConfig.unreachableTargetRetry);
    if(blocked && sPlayerbotDiagnostics.IncidentsEnabled()) {
        incidentBotGuid=bot->GetGUIDLow();
        incidentTracker.Observe(BotIncidentKind::Unreachable,true,target->GetObjectGuid().GetRawValue(),now,0,
            [&](BotIncidentKind kind,bool open,uint64 guid,uint32 age) {
                sPlayerbotDiagnostics.RecordBotIncident(incidentBotGuid,kind,open,guid,age,bot->GetMapId(),bot->GetZoneId(),"reach target");
            });
    }
    return blocked;
}

void PlayerbotAI::RecordBotActionFailure(std::string const& action, Unit* target)
{
    if (!sPlayerbotDiagnostics.IncidentsEnabled()) return;
    uint32 now=WorldTimer::getMSTime();
    uint64 guid=target ? target->GetObjectGuid().GetRawValue() : 0;
    if (incidentFailureAction!=action || incidentFailureTarget!=guid) {
        incidentFailureAction=action.substr(0,96); incidentFailureTarget=guid;
        incidentFailureSince=now; incidentFailureCount=0;
    }
    incidentFailureLast=now;
    if(incidentFailureCount<100000) ++incidentFailureCount;
}

void PlayerbotAI::RecordBotActionSuccess()
{
    incidentFailureAction.clear(); incidentFailureCount=0;
}

void PlayerbotAI::ResetBotProgress()
{
    unreachableTargets.Reset();
    incidentTracker=BotIncidentTracker();
    incidentSample=0; incidentFailureCount=0; incidentFailureAction.clear();
    if(incidentBotGuid) sPlayerbotDiagnostics.CloseBotIncidents(incidentBotGuid);
}

void PlayerbotAI::ObserveBotIncidents()
{
    if (!sPlayerbotDiagnostics.IncidentsEnabled()) {
        if(incidentSample) ResetBotProgress();
        return;
    }
    if(!bot->IsInWorld() || bot->IsBeingTeleported()) { ResetBotProgress(); return; }
    uint32 now=WorldTimer::getMSTime();
    if(incidentSample && uint32(now-incidentSample)<1000) return;
    incidentBotGuid=bot->GetGUIDLow();
    auto emit=[&](BotIncidentKind kind,bool open,uint64 target,uint32 duration) {
        sPlayerbotDiagnostics.RecordBotIncident(incidentBotGuid,kind,open,target,duration,
            bot->GetMapId(),bot->GetZoneId(),kind==BotIncidentKind::ActionLoop ? incidentFailureAction : "");
    };
    bool gap=incidentSample && (uint32(now-incidentSample)>10000 ||
        incidentMap!=bot->GetMapId() || incidentInstance!=bot->GetInstanceId());
    if(gap) { incidentTracker.Reset(now,emit); RecordBotActionSuccess(); unreachableTargets.Reset(); }
    bool first=!incidentSample || gap;
    incidentSample=now; incidentMap=bot->GetMapId(); incidentInstance=bot->GetInstanceId();
    float dx=bot->GetPositionX()-incidentX,dy=bot->GetPositionY()-incidentY;
    bool moved=first || dx*dx+dy*dy>=4.0f;
    if(moved) { incidentX=bot->GetPositionX();incidentY=bot->GetPositionY();RecordBotActionSuccess(); }
    bool suspended=!bot->IsInWorld() || bot->IsBeingTeleported() || bot->IsTaxiFlying() ||
        bot->GetTransport() || bot->HasCharmer();
    if(suspended) { incidentTracker.Reset(now,emit); unreachableTargets.Reset(); return; }
    Unit* target=GetUnit(aiObjectContext->GetValue<ObjectGuid>("current target")->Get());
    uint64 targetId=target ? target->GetObjectGuid().GetRawValue() : 0;
    bool movingIntent=bot->IsAlive() && !bot->IsNonMeleeSpellCasted(true) &&
        bot->GetMotionMaster()->GetCurrentMovementGeneratorType()==POINT_MOTION_TYPE;
    incidentTracker.Observe(BotIncidentKind::Stuck,movingIntent && !moved,0,now,60000,emit);
    incidentTracker.Observe(BotIncidentKind::DeadLong,!bot->IsAlive(),0,now,120000,emit);
    bool loop=bot->IsAlive() && incidentFailureCount>=10 && uint32(now-incidentFailureLast)<10000;
    incidentTracker.Observe(BotIncidentKind::ActionLoop,loop,incidentFailureTarget,now,60000,emit);
    incidentTracker.Observe(BotIncidentKind::Unreachable,targetId && IgnoreUnreachableTarget(target),targetId,now,0,emit);
}
