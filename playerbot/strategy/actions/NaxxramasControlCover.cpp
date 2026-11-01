#include "playerbot/playerbot.h"
#include "NaxxramasControlCommands.h"
#include "playerbot/strategy/values/EncounterPositionValue.h"
#include "playerbot/RaidLabTrace.h"

using namespace ai;

bool ai::RazuviousControlCover(PlayerbotAI* ai, Unit* boss, Unit* student, EncounterPosition& plan)
{
#ifdef MANGOSBOT_ZERO
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->GetMapId()!=533 || !bot->IsInCombat() ||
        bot->IsBeingTeleported() || bot->HasCharmer() || bot->GetCharm() || !bot->GetGroup() ||
        ai->IsRealPlayer() || bot->getClass()!=CLASS_PRIEST || !NaxxramasControlAllowed(ai) ||
        !boss || !boss->IsInWorld() || !boss->IsAlive() || boss->GetEntry()!=16061 ||
        boss->HasCharmer() || !bot->IsInMap(boss) || !NaxxramasEncounterEngaged(bot,boss) ||
        !student || !student->IsInWorld() || !student->IsAlive() || student->GetEntry()!=16803 ||
        student->HasCharmer() || !bot->IsInMap(student) || student->GetDistance(boss)>80) return false;
    float controlRange = 0;
    const float shout = NativeEncounterSpellRadius(29107);
    if (!ai->GetSpellRange("mind control", &controlRange) || !std::isfinite(controlRange) ||
        controlRange<=2 || controlRange>40 || !std::isfinite(shout) || shout<=0 || shout>100) return false;
    const encounter::Point here{bot->GetPositionX(),bot->GetPositionY(),bot->GetPositionZ()};
    const encounter::Point bossPoint{boss->GetPositionX(),boss->GetPositionY(),boss->GetPositionZ()};
    const auto covered = [&](const encounter::Point& point) {
        // Native spell LOS ignores decorative M2 objects. The student must
        // remain visible and in native control range from the chosen station.
        return student->GetDistance(point.x,point.y,point.z)<=controlRange-1 &&
            student->IsWithinLOS(point.x,point.y,point.z+bot->GetCollisionHeight(),true) &&
            (encounter::Distance2d(point,bossPoint)>=shout+boss->GetCombatReach()+bot->GetCombatReach()+1 ||
             !boss->IsWithinLOS(point.x,point.y,point.z+bot->GetCollisionHeight(),true));
    };
    plan.active=true;plan.map=533;plan.instance=bot->GetInstanceId();
    plan.boss=boss->GetObjectGuid();plan.source=student->GetObjectGuid();plan.spell=29107;
    plan.destination=here;
    if (covered(here)) return true;
    if (!ai->CanMove() || bot->GetTransport()) { plan.active=false;return false; }
    unsigned paths=0;
    for (float radius:{2.0f,4.0f,8.0f,12.0f}) for (unsigned sector=0;sector<16;++sector)
    {
        const float angle=sector*(2.0f*M_PI_F/16.0f);
        plan.destination={here.x+radius*std::cos(angle),here.y+radius*std::sin(angle),here.z};
        bot->UpdateAllowedPositionZ(plan.destination.x,plan.destination.y,plan.destination.z);
        if (!std::isfinite(plan.destination.z) || std::fabs(plan.destination.z-here.z)>3 || !covered(plan.destination)) continue;
        if (++paths>8) break;
        if (ValidateEncounterDestination(ai,plan) && covered(plan.destination))
        {
#ifdef MANTECH_RAID_LAB
            RaidLab::Count(bot,"razuvious_control_cover",1,1,student->GetObjectGuid().GetRawValue());
#endif
            return true;
        }
    }
    plan.active=false;
#ifdef MANTECH_RAID_LAB
    RaidLab::Count(bot,"razuvious_control_cover",paths?2:3,0,student->GetObjectGuid().GetRawValue());
#endif
#endif
    return false;
}
