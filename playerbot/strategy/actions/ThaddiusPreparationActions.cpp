#include "playerbot/playerbot.h"
#include "NaxxramasPreparationActions.h"
#include "BotCommandAccess.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/generic/PullStrategy.h"
#include "playerbot/strategy/values/PositionValue.h"
#include "AI/ScriptDevAI/include/sc_instance.h"
#include "MotionGenerators/PathFinder.h"
#include "playerbot/RaidLabTrace.h"

using namespace ai;

namespace
{
    bool ThaddiusMember(Player* bot, Player* member)
    {
        return member && member->IsInWorld() && member->IsAlive() && !member->HasCharmer() &&
            !member->IsBeingTeleported() && bot->IsInMap(member) && member->GetGroup()==bot->GetGroup();
    }
    struct ThaddiusRequest { Player* puller=nullptr; PullStrategy* pull=nullptr; Creature* adds[2]={}; Creature* boss=nullptr; };
    bool ThaddiusSavedStation(PlayerbotAI* ai, const ThaddiusRequest& request, Creature* add, encounter::Point& point)
    {
        auto* context=ai->GetAiObjectContext();
        if (context->GetValue<int32>("manual int","thaddius station request")->Get()!=int32(request.pull->GetPullStartTime()) ||
            context->GetValue<int32>("manual int","thaddius station instance")->Get()!=int32(ai->GetBot()->GetInstanceId()) ||
            context->GetValue<int32>("manual int","thaddius station entry")->Get()!=int32(add->GetEntry())) return false;
        PositionMap& positions=context->GetValue<PositionMap&>("position")->Get();
        const auto found=positions.find("thaddius preparation");
        if (found==positions.end() || !found->second.isSet() || found->second.mapId!=533) return false;
        point={found->second.x,found->second.y,found->second.z};
        return std::isfinite(point.x) && std::isfinite(point.y) && std::isfinite(point.z);
    }
    void RememberThaddiusStation(PlayerbotAI* ai, const ThaddiusRequest& request, Creature* add, const encounter::Point& point)
    {
        auto* context=ai->GetAiObjectContext();
        context->GetValue<PositionMap&>("position")->Get()["thaddius preparation"].Set(point.x,point.y,point.z,533);
        context->GetValue<int32>("manual int","thaddius station request")->Set(int32(request.pull->GetPullStartTime()));
        context->GetValue<int32>("manual int","thaddius station instance")->Set(int32(ai->GetBot()->GetInstanceId()));
        context->GetValue<int32>("manual int","thaddius station entry")->Set(int32(add->GetEntry()));
    }
    ThaddiusRequest ThaddiusPending(PlayerbotAI* ai)
    {
        ThaddiusRequest result;
#ifdef MANGOSBOT_ZERO
        Player* bot=ai->GetBot();
        if (!bot->IsInWorld() || !bot->IsAlive() || bot->GetMapId()!=533 || bot->IsInCombat() ||
            bot->HasCharmer() || bot->IsBeingTeleported() || !bot->GetGroup() || ai->IsRealPlayer() ||
            !ai->HasStrategy("dungeon",BotState::BOT_STATE_COMBAT)) return result;
        auto* instance=dynamic_cast<ScriptedInstance*>(bot->GetMap()->GetInstanceData());
        if (!instance || instance->GetData(12)!=NOT_STARTED) return result;
        Creature* boss=instance->GetSingleCreatureFromStorage(15928,true);
        Creature* adds[2]={instance->GetSingleCreatureFromStorage(15930,true),instance->GetSingleCreatureFromStorage(15929,true)};
        for (Creature* unit : {boss,adds[0],adds[1]})
            if (!unit || !unit->IsInWorld() || !unit->IsAlive() || unit->HasCharmer() ||
                !bot->IsInMap(unit) || unit->IsInCombat() || bot->GetDistance(unit)>180) return result;
        for (auto ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next())
        {
            Player* member=ref->getSource();
            if (!ThaddiusMember(bot,member) || member->IsInCombat()) continue;
            PlayerbotAI* brain=member->GetPlayerbotAI();
            PullStrategy* pull=PullStrategy::Get(brain);
            if (!brain || brain->IsRealPlayer() || !ai->IsTank(member) || !pull ||
                !pull->IsEncounterPreparationAllowed() || !pull->HasPullStarted() ||
                time(nullptr)-pull->GetPullStartTime()>=pull->GetMaxPullTime() ||
                (pull->GetTarget()!=adds[0] && pull->GetTarget()!=adds[1])) continue;
            Unit* requester=brain->GetUnit(pull->GetRequester());
            if (!requester || !requester->IsPlayer() || !ThaddiusMember(bot,static_cast<Player*>(requester)) ||
                !CanManageBotCommands(brain,static_cast<Player*>(requester))) continue;
            if (!result.puller || member->GetObjectGuid()<result.puller->GetObjectGuid())
                result={member,pull,{adds[0],adds[1]},boss};
        }
#endif
        return result;
    }
}

bool ai::NaxxramasThaddiusPreparationPlan(PlayerbotAI* ai, EncounterPosition& plan, bool& groupReady)
{
    groupReady=false;
    const auto request=ThaddiusPending(ai);
    if (!request.puller) return false;
    Player* bot=ai->GetBot();
    // Hold both sides through the puller's shot; do not hold the puller itself.
    if (bot==request.puller && !request.pull->IsPullPendingToStart()) return false;
    std::vector<Player*> members;
    for (auto ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next())
        if (ThaddiusMember(bot,ref->getSource())) members.push_back(ref->getSource());
    std::sort(members.begin(),members.end(),[](Player* a,Player* b){return a->GetObjectGuid()<b->GetObjectGuid();});
    unsigned tankIndex=0;
    for (Player* member:members) { if (member==request.puller) break; if (ai->IsTank(member)) ++tankIndex; }
    const unsigned tankOffset=(tankIndex%2) ^ (request.pull->GetTarget()==request.adds[1]?1u:0u);
    unsigned roles[3]={},present[3][2]={};bool ready=true,assigned=false;
    for (Player* member:members)
    {
        const unsigned role=ai->IsTank(member)?0:ai->IsHeal(member)?1:2;
        const unsigned side=(roles[role]++%2) ^ (role==0?tankOffset:0u);
        PlayerbotAI* brain=member->GetPlayerbotAI();
        if (!brain || brain->IsRealPlayer()) continue; // Humans retain control of their own position.
        Creature* add=request.adds[side];
        const float angle=std::atan2(add->GetPositionY()-request.boss->GetPositionY(),add->GetPositionX()-request.boss->GetPositionX());
        const float radius=std::max(30.0f,add->GetAttackDistance(member)+9.0f);
        encounter::Point station{add->GetPositionX()+radius*std::cos(angle),
            add->GetPositionY()+radius*std::sin(angle),add->GetPositionZ()};
        ThaddiusSavedStation(brain,request,add,station);
        ++present[role][side];
        const uint32 waiting=(member->IsInCombat()?1u:0u) |
            (member->GetDistance(station.x,station.y,station.z)>4?2u:0u) |
            (!brain->HasStrategy("dungeon",BotState::BOT_STATE_COMBAT)?4u:0u);
        if (waiting) ready=false;
#ifdef MANTECH_RAID_LAB
        if (bot==request.puller)
            RaidLab::Count(bot,"thaddius_prepare_wait",member->GetObjectGuid().GetCounter(),waiting,add->GetObjectGuid().GetRawValue());
#endif
        if (member==bot)
        {
            assigned=true;plan.active=true;plan.map=533;plan.instance=bot->GetInstanceId();
            plan.boss=add->GetObjectGuid();plan.source=request.boss->GetObjectGuid();plan.spell=15928;plan.destination=station;
            if (bot->GetDistance(station.x,station.y,station.z)<=4)
                ai->GetAiObjectContext()->GetValue<ObjectGuid>("thaddius prepared target")->Set(add->GetObjectGuid());
        }
    }
    groupReady=ready && present[0][0] && present[0][1] && present[1][0] && present[1][1] && present[2][0] && present[2][1];
#ifdef MANTECH_RAID_LAB
    if (bot==request.puller)
        RaidLab::Count(bot,"thaddius_prepare_roles",present[0][0] | (present[0][1]<<8),
            present[1][0] | (present[1][1]<<8),present[2][0] | (present[2][1]<<8));
#endif
    return assigned;
}

bool ai::NaxxramasThaddiusPullReady(PlayerbotAI* ai)
{
#ifdef MANGOSBOT_ZERO
    PullStrategy* pull=PullStrategy::Get(ai);Unit* target=pull?pull->GetTarget():nullptr;
    if (pull && pull->IsEncounterPreparationAllowed() && ai->GetBot()->GetMapId()==533 && target &&
        (target->GetEntry()==15929 || target->GetEntry()==15930) && !target->IsInCombat())
    {
        EncounterPosition plan;bool ready=false;
        return NaxxramasThaddiusPreparationPlan(ai,plan,ready) && ready;
    }
#endif
    return true;
}

bool NaxxramasThaddiusPrepareAction::isUseful()
{
    EncounterPosition plan;bool ready=false;
    return NaxxramasThaddiusPreparationPlan(ai,plan,ready) && bot->GetDistance(plan.destination.x,plan.destination.y,plan.destination.z)>4;
}

bool NaxxramasThaddiusPrepareAction::Execute(Event&)
{
    EncounterPosition plan;bool ready=false;
    if (!NaxxramasThaddiusPreparationPlan(ai,plan,ready) || !ai->CanMove() || bot->IsNonMeleeSpellCasted(false)) return false;
    const auto request=ThaddiusPending(ai);
    if (!request.puller) return false;
    const auto station=plan.destination;
    Creature* assigned=plan.boss==request.adds[0]->GetObjectGuid()?request.adds[0]:request.adds[1];
    // The nominal outward point can be below a raised platform. Search a
    // bounded ring for real floor and a complete aggro-safe route, then retain
    // that admitted endpoint for readiness and later movement legs.
    std::vector<encounter::Point> candidates{station};
    encounter::Point saved;
    if (!ThaddiusSavedStation(ai,request,assigned,saved))
    {
        const float base=std::atan2(station.y-assigned->GetPositionY(),station.x-assigned->GetPositionX());
        const float radius=std::hypot(station.x-assigned->GetPositionX(),station.y-assigned->GetPositionY());
        for (unsigned i=1;i<16;++i)
        {
            const float angle=base+float((i+1)/2)*(i%2?1.0f:-1.0f)*M_PI_F/8;
            candidates.push_back({assigned->GetPositionX()+radius*std::cos(angle),
                assigned->GetPositionY()+radius*std::sin(angle),assigned->GetPositionZ()});
        }
    }
    const auto rejected=[&](uint32 reason,const encounter::Point& destination,PathFinder* finder=nullptr) {
#ifdef MANTECH_RAID_LAB
        RaidLab::Count(bot,"thaddius_prepare_reject",reason,0,finder?uint32(finder->getPathType()):0);
        const auto end=finder?finder->getActualEndPosition():G3D::Vector3();
        RaidLab::DestinationRejected(bot,200+reason,destination.x,destination.y,destination.z,station.z,
            finder?uint32(finder->getPath().size()):0,end.x,end.y,end.z);
#endif
    };
    for (auto destination:candidates)
    {
        bot->UpdateAllowedPositionZ(destination.x,destination.y,destination.z);
        if (!std::isfinite(destination.z) || std::fabs(destination.z-station.z)>3) {rejected(1,destination);continue;}
        PathFinder finder(bot);
        if (!finder.calculate(destination.x,destination.y,destination.z,false) || finder.getPathType()!=PATHFIND_NORMAL ||
            finder.getPath().size()<2 || finder.getPath().size()>256) {rejected(2,destination,&finder);continue;}
        const auto& end=finder.getPath().back();
        if (std::hypot(end.x-destination.x,end.y-destination.y)>1 || std::fabs(end.z-destination.z)>2) {rejected(3,destination,&finder);continue;}
        encounter::Point previous{bot->GetPositionX(),bot->GetPositionY(),bot->GetPositionZ()},leg=destination;
        float total=0;bool safe=true,haveLeg=false;
        for (const auto& point:finder.getPath())
        {
            if (!std::isfinite(point.x) || !std::isfinite(point.y) || !std::isfinite(point.z)) {safe=false;break;}
            const float segment=std::sqrt((point.x-previous.x)*(point.x-previous.x)+(point.y-previous.y)*(point.y-previous.y)+(point.z-previous.z)*(point.z-previous.z));
            total+=segment;if (!std::isfinite(total) || total>240) {safe=false;break;}
            for (Creature* add:request.adds)
            {
                const float dx=point.x-previous.x,dy=point.y-previous.y,dz=point.z-previous.z;
                const float length2=dx*dx+dy*dy+dz*dz;
                const float projection=length2>0?std::max(0.0f,std::min(1.0f,((add->GetPositionX()-previous.x)*dx+
                    (add->GetPositionY()-previous.y)*dy+(add->GetPositionZ()-previous.z)*dz)/length2)):0;
                if (add->GetDistance(previous.x+dx*projection,previous.y+dy*projection,previous.z+dz*projection)<
                    add->GetAttackDistance(bot)+3) safe=false;
            }
            if (!haveLeg && total>=30 && segment>0)
            {
                const float fraction=(30-(total-segment))/segment;
                leg={previous.x+(point.x-previous.x)*fraction,previous.y+(point.y-previous.y)*fraction,previous.z+(point.z-previous.z)*fraction};haveLeg=true;
            }
            previous={point.x,point.y,point.z};
        }
        if (!safe) {rejected(4,destination,&finder);continue;}
        plan.destination=leg;
        if (!ValidateEncounterDestination(ai,plan)) {rejected(5,plan.destination,&finder);continue;}
        RememberThaddiusStation(ai,request,assigned,destination);
        const auto& p=plan.destination;
        return MoveTo(plan.map,p.x,p.y,p.z,false,IsReaction(),false,true);
    }
    return false;
}
