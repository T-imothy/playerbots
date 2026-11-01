#include "playerbot/playerbot.h"
#include "CthunRoleActions.h"
#include "ClassicRaidActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"
#include "playerbot/ServerFacade.h"
#include "AI/ScriptDevAI/include/sc_instance.h"

using namespace ai;

#ifdef MANGOSBOT_ZERO
namespace
{
    // Native Classic C'Thun only. The stored body and its current group threat
    // remain identifiable while players are on the separate stomach floor.
    Creature* CthunBody(PlayerbotAI* ai)
    {
        Player* bot = ai->GetBot();
        if (!bot || !bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() ||
            bot->HasCharmer() || ai->IsRealPlayer() || bot->GetMapId() != 531 || !bot->GetGroup()) return nullptr;
        auto* instance = dynamic_cast<ScriptedInstance*>(bot->GetMap()->GetInstanceData());
        if (!instance || instance->GetData(8) != IN_PROGRESS) return nullptr;
        Creature* body = instance->GetSingleCreatureFromStorage(15727, true);
        if (!body || !body->IsInWorld() || !body->IsAlive() || !body->IsInCombat() ||
            body->HasCharmer() || !bot->IsInMap(body) || !body->HasAura(26232)) return nullptr;
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (!member || !member->IsInWorld() || !member->IsAlive() || member->IsBeingTeleported() ||
                member->HasCharmer() || !bot->IsInMap(member)) continue;
            if (body->GetVictim() == member || member->GetVictim() == body ||
                body->getThreatManager().getThreat(member) > 0) return body;
        }
        return nullptr;
    }
    bool InCthunStomach(Unit* unit)
    {
        return unit && unit->HasAura(26476) && unit->GetPositionZ() < 0;
    }
    bool CthunNativeFlesh(PlayerbotAI* ai, Creature* body, Unit* target)
    {
        Player* bot = ai->GetBot();
        return body && InCthunStomach(bot) && target && target->IsInWorld() && target->IsAlive() &&
            bot->IsInMap(target) && !target->HasCharmer() && target->GetEntry() == 15802 &&
            target->GetSpawnerGuid() == body->GetObjectGuid() &&
            std::fabs(bot->GetPositionZ() - target->GetPositionZ()) < 12 &&
            PossibleAttackTargetsValue::IsPossibleTarget(target, bot, sPlayerbotAIConfig.sightDistance, false) &&
            !PossibleAttackTargetsValue::HasBreakableCC(target, bot) &&
            !PossibleAttackTargetsValue::HasUnBreakableCC(target, bot);
    }
    unsigned CthunTentaclePriority(PlayerbotAI* ai, Creature* body, Unit* target)
    {
        Player* bot = ai->GetBot();
        if (!target || !target->IsInWorld() || !target->IsAlive() || !bot->IsInMap(target) ||
            target->HasCharmer() || std::fabs(bot->GetPositionZ() - target->GetPositionZ()) > 12 ||
            target->GetDistance(body) > 100 ||
            !PossibleAttackTargetsValue::IsPossibleTarget(target, bot, sPlayerbotAIConfig.sightDistance, false) ||
            PossibleAttackTargetsValue::HasBreakableCC(target, bot) ||
            PossibleAttackTargetsValue::HasUnBreakableCC(target, bot)) return 0;
        const uint32 entry = target->GetEntry(), spell = target->GetUInt32Value(UNIT_CREATED_BY_SPELL);
        // Native target-triggered summons belong to a raid member, not to the
        // body. Validate that relationship instead of claiming ambient mobs.
        if (entry == 15334 || entry == 15728 || entry == 15725)
        {
            if (spell != (entry == 15334 ? 26768u : entry == 15728 ? 26216u : 26140u)) return 0;
            Unit* source = ai->GetUnit(target->GetSpawnerGuid());
            if (!source || !source->IsPlayer() || !source->IsInWorld() || !bot->IsInMap(source) ||
                static_cast<Player*>(source)->GetGroup() != bot->GetGroup()) return 0;
        }
        else if (entry == 15726)
        {
            if (target->GetSpawnerGuid() != body->GetObjectGuid() || spell < 26144 || spell > 26151) return 0;
        }
        else return 0;
        if (ai->IsTank(bot) && entry == 15728) return 5;
        return entry == 15334 ? 4 : entry == 15726 ? 3 : entry == 15728 ? 2 : 1;
    }
    bool CthunLeaveStomach(Player* bot, Creature* body, bool fleshPresent)
    {
        const SpellAuraHolder* acid = bot->GetSpellAuraHolder(26476);
        return InCthunStomach(bot) && (body->HasAura(26235) || !fleshPresent ||
            (acid && acid->GetStackAmount() >= 5) || bot->GetHealthPercent() < 35);
    }
}
#endif

bool ai::CthunRolePlan(PlayerbotAI* ai, ClassicRaidPlan& plan)
{
#ifdef MANGOSBOT_ZERO
    Creature* body = CthunBody(ai);
    if (!body) return false;
    Player* bot = ai->GetBot();
    const bool stomach = InCthunStomach(bot);
    Unit* selected = nullptr;
    Unit* current = ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("current target")->Get());
    unsigned priority = 0;
    for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets", "100:1")->Get())
    {
        Unit* target = ai->GetUnit(guid);
        const unsigned rank = stomach ? (CthunNativeFlesh(ai, body, target) ? 1 : 0) :
            CthunTentaclePriority(ai, body, target);
        if (rank && (!selected || rank > priority || (rank == priority &&
            (target == current || (selected != current && target->GetObjectGuid() < selected->GetObjectGuid())))))
        { selected = target; priority = rank; }
    }
    plan.boss = body->GetObjectGuid();
    if (stomach && CthunLeaveStomach(bot, body, selected != nullptr))
    {
        plan.holdDamage = true;
        const AreaTriggerEntry* exit = sAreaTriggerStore.LookupEntry(4033);
        if (exit && exit->mapid == 531 && exit->z < 0 && std::fabs(exit->z - bot->GetPositionZ()) < 12)
        {
            EncounterPosition p; p.active = true; p.exclusive = true; p.map = 531;
            p.instance = bot->GetInstanceId(); p.boss = body->GetObjectGuid(); p.spell = 26221;
            p.destination = {exit->x, exit->y, exit->z};
            if (ValidateEncounterDestination(ai, p)) { plan.position = p; plan.emergency = true; }
        }
        return true;
    }
    if (!ai->IsHeal(bot))
    {
        if (selected) plan.target = selected->GetObjectGuid();
        // Only the native weakened window makes the body a sensible damage
        // target. Stomach actors never attack through the floor above them.
        else if (!stomach && body->HasAura(26235)) plan.target = body->GetObjectGuid();
        else plan.holdDamage = true;
    }
    return true; // Retain native tentacle pursuit, not generic body formation.
#else
    return false;
#endif
}

bool ai::CthunPlanCurrent(PlayerbotAI* ai, const ClassicRaidPlan& plan)
{
#ifdef MANGOSBOT_ZERO
    Creature* body = CthunBody(ai);
    return body && InCthunStomach(ai->GetBot()) && plan.boss == body->GetObjectGuid() &&
        plan.position.spell == 26221 && plan.position.map == 531 &&
        plan.position.instance == ai->GetBot()->GetInstanceId();
#else
    return false;
#endif
}

bool ai::CthunFleshTarget(PlayerbotAI* ai, Unit* target)
{
#ifdef MANGOSBOT_ZERO
    return CthunNativeFlesh(ai, CthunBody(ai), target);
#else
    return false;
#endif
}

bool ai::CthunOffenseAllowed(PlayerbotAI* ai, const SpellEntry* spell, Unit* target)
{
#ifdef MANGOSBOT_ZERO
    Creature* body = CthunBody(ai);
    if (body && (!spell || ClassicRaidDamageSpell(spell)))
    {
        if (target == body && !body->HasAura(26235)) return false;
        if (target && std::fabs(target->GetPositionZ() - ai->GetBot()->GetPositionZ()) > 40) return false;
    }
#endif
    return true;
}

bool ai::CthunApproachAllowed(PlayerbotAI* ai, Unit* target)
{
#ifdef MANGOSBOT_ZERO
    if (CthunBody(ai) && target && target->IsInWorld() && ai->GetBot()->IsInMap(target) &&
        std::fabs(target->GetPositionZ() - ai->GetBot()->GetPositionZ()) > 40) return false;
#endif
    return true;
}

bool ai::CthunStomachExit(PlayerbotAI* ai, bool execute)
{
#ifdef MANGOSBOT_ZERO
    ClassicRaidPlan plan;
    if (!CthunRolePlan(ai, plan) || !CthunPlanCurrent(ai, plan)) return false;
    Player* bot = ai->GetBot();
    const AreaTriggerEntry* exit = sAreaTriggerStore.LookupEntry(4033);
    if (!exit || !::IsPointInAreaTriggerZone(exit, bot->GetMapId(), bot->GetPositionX(),
        bot->GetPositionY(), bot->GetPositionZ(), 0.0f)) return false;
    if (execute)
    {
        WorldPacket packet(CMSG_AREATRIGGER); packet << uint32(4033);
        bot->GetSession()->HandleAreaTriggerOpcode(packet);
    }
    return true;
#else
    return false;
#endif
}
