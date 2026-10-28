#include "playerbot/playerbot.h"
#include "RazuviousPullActions.h"
#include "BotCommandAccess.h"
#include "GenericActions.h"
#include "playerbot/ServerFacade.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/generic/PullStrategy.h"

using namespace ai;

namespace
{
#ifdef MANGOSBOT_TWO
    bool RazuviousMember(Player* bot, Player* member)
    {
        return member && member->IsInWorld() && member->IsAlive() && bot->IsInMap(member) &&
            member->GetGroup() == bot->GetGroup() && !member->IsBeingTeleported() && !member->HasCharmer();
    }
    Unit* OwnedUnderstudy(Player* owner)
    {
        Unit* student = owner->GetCharm();
        return student && student->GetEntry() == 16803 && student->IsInWorld() && student->IsAlive() &&
            owner->IsInMap(student) && student->HasCharmer(owner->GetObjectGuid()) &&
            student->HasSpell(29061) && student->HasSpell(29060) ? student : nullptr;
    }
    struct RazuviousPreparation
    {
        PullStrategy* request = nullptr;
        Player* puller = nullptr;
        Unit* boss = nullptr;
        Unit* crystal = nullptr;
        Player* starter = nullptr;
        unsigned controlled = 0;
        bool assigned = false;
    };
    RazuviousPreparation RazuviousRequest(PlayerbotAI* ai)
    {
        RazuviousPreparation plan;
        Player* bot = ai->GetBot();
        if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
            ai->IsRealPlayer() || bot->GetMapId() != 533 || !bot->GetMap()->IsRegularDifficulty() || !bot->GetGroup()) return plan;
        std::vector<Player*> members;
        const time_t now = time(nullptr);
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (!RazuviousMember(bot, member)) continue;
            members.push_back(member);
            PlayerbotAI* brain = member->GetPlayerbotAI();
            PullStrategy* request = PullStrategy::Get(brain);
            if (!brain || brain->IsRealPlayer() || !request || !request->IsEncounterPreparationAllowed() ||
                !request->HasPullStarted() || request->HasPullActionIssued() ||
                now < request->GetPullStartTime() || now - request->GetPullStartTime() >= request->GetMaxPullTime()) continue;
            Unit* boss = request->GetTarget();
            if (!IsRazuviousCrystalPull(brain, boss) || boss->IsInCombat()) continue;
            Unit* requesterUnit = ai->GetUnit(request->GetRequester());
            if (!requesterUnit || !requesterUnit->IsPlayer()) continue;
            Player* requester = static_cast<Player*>(requesterUnit);
            if (!RazuviousMember(bot, requester) || !CanManageBotCommands(brain, requester) ||
                (requester->GetPlayerbotAI() && !requester->GetPlayerbotAI()->IsRealPlayer())) continue;
            if (!plan.request || request->GetPullStartTime() < plan.request->GetPullStartTime() ||
                (request->GetPullStartTime() == plan.request->GetPullStartTime() && member->GetObjectGuid() < plan.puller->GetObjectGuid()))
            { plan.request = request; plan.puller = member; plan.boss = boss; }
        }
        if (!plan.request) return plan;
        std::sort(members.begin(), members.end(), [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        std::vector<Player*> eligible;
        for (Player* member : members)
        {
            Unit* student = OwnedUnderstudy(member);
            if (student && student->GetDistance(plan.boss) < 80)
            {
                ++plan.controlled;
                if (!plan.starter && member->GetPlayerbotAI() && !member->GetPlayerbotAI()->IsRealPlayer()) plan.starter = member;
                continue;
            }
            if (!member->GetCharm() && !member->hasUnitState(UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL) &&
                member->GetPlayerbotAI() && !member->GetPlayerbotAI()->IsRealPlayer() && ai->IsTank(member)) eligible.push_back(member);
        }
        if (plan.controlled >= 2) return plan;
        const auto self = std::find(eligible.begin(), eligible.end(), bot);
        if (self == eligible.end()) return plan;
        const size_t slot = size_t(self - eligible.begin());
        if (slot >= 2 - plan.controlled) return plan;
        plan.assigned = true;
        std::vector<Unit*> crystals;
        for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets", "100:1")->Get())
        {
            Unit* crystal = ai->GetUnit(guid);
            if (crystal && crystal->GetEntry() == 29912 && crystal->IsInWorld() && crystal->IsAlive() &&
                bot->IsInMap(crystal) && !crystal->HasCharmer() && !crystal->IsInCombat() &&
                !crystal->IsNonMeleeSpellCasted(true) && crystal->GetDistance(plan.boss) < 80) crystals.push_back(crystal);
        }
        std::sort(crystals.begin(), crystals.end(), [](Unit* a, Unit* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        if (slot < crystals.size()) plan.crystal = crystals[slot];
        return plan;
    }
#endif
}

bool ai::IsRazuviousCrystalPull(PlayerbotAI* ai, Unit* target)
{
#ifdef MANGOSBOT_TWO
    Player* bot = ai->GetBot();
    return bot->IsInWorld() && bot->IsAlive() && !bot->IsBeingTeleported() && !bot->HasCharmer() &&
        !ai->IsRealPlayer() && bot->GetMapId() == 533 && bot->GetMap()->IsRegularDifficulty() &&
        target && target->GetEntry() == 16061 && target->IsInWorld() && target->IsAlive() &&
        bot->IsInMap(target) && !target->HasCharmer();
#else
    return false;
#endif
}

bool ai::RazuviousCrystalPullReady(PlayerbotAI* ai)
{
#ifdef MANGOSBOT_TWO
    PullStrategy* request = PullStrategy::Get(ai);
    if (!request || !request->IsEncounterPreparationAllowed() || !IsRazuviousCrystalPull(ai, request->GetTarget())) return true;
    if (request->GetTarget()->IsInCombat()) return true; // Existing native combat controller takes ownership.
    const auto plan = RazuviousRequest(ai);
    Unit* student = plan.starter ? OwnedUnderstudy(plan.starter) : nullptr;
    return plan.request == request && plan.controlled >= 2 && student && student->HasAura(29061);
#else
    return true;
#endif
}

bool RazuviousPreparationAction::isUseful()
{
#ifdef MANGOSBOT_TWO
    const auto plan = RazuviousRequest(ai);
    if (!plan.request) return false;
    if (plan.assigned) return plan.crystal != nullptr;
    Unit* student = OwnedUnderstudy(bot);
    return plan.starter == bot && plan.controlled >= 2 && student &&
        (!student->HasAura(29061) || !plan.request->IsPullPendingToStart());
#else
    return false;
#endif
}

bool RazuviousPreparationAction::Execute(Event& event)
{
#ifdef MANGOSBOT_TWO
    const auto plan = RazuviousRequest(ai);
    if (!plan.request) return false;
    if (plan.assigned && plan.crystal)
    {
        if (bot->IsNonMeleeSpellCasted(false)) return false;
        if (!bot->IsWithinDistInMap(plan.crystal, INTERACTION_DISTANCE) || !bot->IsWithinLOSInMap(plan.crystal))
            return ai->CanMove() && MoveNear(plan.crystal, INTERACTION_DISTANCE - 1);
        const uint32 now = WorldTimer::getMSTime();
        if (static_cast<int32>(nextAttempt - now) > 0) return false;
        nextAttempt = now + 1000;
        WorldPacket click(CMSG_SPELLCLICK);
        click << plan.crystal->GetObjectGuid();
        bot->GetSession()->HandleSpellClick(click);
        SetDuration(300);
        Unit* student = OwnedUnderstudy(bot);
        if (!student) return false; // Native script may refuse; never invent control.
        // Charm creation enables autocasts before the next native PetAI update.
        // Reserve Barrier and Taunt immediately, while waiting for the second
        // controller, so preparation cannot consume the opening cooldowns.
        for (uint32 id : {29061u, 29060u})
            if (student->HasSpell(id) && IsAutocastable(id))
            {
                WorldPacket packet(CMSG_PET_SPELL_AUTOCAST);
                packet << student->GetObjectGuid() << id << uint8(0);
                bot->GetSession()->HandlePetSpellAutocastOpcode(packet);
            }
        return true;
    }
    Unit* student = OwnedUnderstudy(bot);
    if (plan.starter != bot || plan.controlled < 2 || !student || student->IsNonMeleeSpellCasted(false)) return false;
    const uint32 now = WorldTimer::getMSTime();
    if (static_cast<int32>(nextAttempt - now) > 0) return false;
    nextAttempt = now + 300;
    if (!student->HasAura(29061))
    {
        const SpellEntry* wall = sServerFacade.LookupSpellInfo(29061);
        if (!wall || !student->IsSpellReady(*wall)) return false;
        SpellCastTargets targets;
        targets.setUnitTarget(student);
        WorldPacket cast(CMSG_PET_CAST_SPELL);
        cast << student->GetObjectGuid() << uint8(0) << uint32(29061) << uint8(0) << targets;
        bot->GetSession()->HandlePetCastSpellOpcode(cast);
        SetDuration(300);
        return student->HasAura(29061); // Opening attack requires the actual native barrier.
    }
    if (plan.request->IsPullPendingToStart()) return false;
    WorldPacket attack(CMSG_PET_ACTION);
    attack << student->GetObjectGuid() << uint32((ACT_COMMAND << 24) | COMMAND_ATTACK) << plan.boss->GetObjectGuid();
    bot->GetSession()->HandlePetAction(attack);
    if (student->GetVictim() != plan.boss) return false;
    plan.request->OnPullActionIssued();
    SetDuration(300);
    return true;
#else
    return false;
#endif
}

bool ai::ExecuteRazuviousCrystalPull(PlayerbotAI* ai)
{
#ifdef MANGOSBOT_TWO
    // A different bot may own the nominated student. Its own preparation
    // action sends the packet; never impersonate another player's session.
    Action* action = ai->GetAiObjectContext()->GetAction("razuvious preparation");
    if (action && action->isUseful())
    {
        Event event("razuvious preparation");
        return action->Execute(event);
    }
#endif
    return false;
}

float ai::RazuviousPreparationMultiplier(PlayerbotAI* ai, Action* action)
{
#ifdef MANGOSBOT_TWO
    if (!action) return 1.0f;
    const auto plan = RazuviousRequest(ai);
    if (!plan.request || action->getName() == "razuvious preparation" || dynamic_cast<ChatCommandAction*>(action)) return 1.0f;
    // Preserve cancellation/explicit orders and the pending pull lifecycle.
    if (action->getName() == "pull start" || action->getName() == "pull action" || action->getName() == "pull end") return 1.0f;
    if (plan.assigned || OwnedUnderstudy(ai->GetBot())) return 0.0f;
#endif
    return 1.0f;
}
