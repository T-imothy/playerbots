#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "EncounterItemUse.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

bool VashjCoreAction::GetPlan(PlayerbotAI* ai, VashjCorePlan& plan)
{
#ifndef MANGOSBOT_ZERO
    Player* bot = ai->GetBot();
    if (bot->GetMapId() != 548 || !bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() ||
        !bot->GetGroup() || bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer() ||
        !ai->HasStrategy("dungeon", BotState::BOT_STATE_COMBAT)) return false;
    plan = ai->GetAiObjectContext()->GetValue<VashjCorePlan>("vashj core plan")->Get();
    if (plan.task == VashjCoreTask::None || !plan.position.active || plan.position.map != bot->GetMapId() ||
        plan.position.instance != bot->GetInstanceId()) return false;
    Unit* boss = ai->GetUnit(plan.position.boss);
    if (!boss || !boss->IsInWorld() || !boss->IsAlive() || !boss->IsInCombat() || !bot->IsInMap(boss) ||
        boss->GetEntry() != 21212 || boss->HasCharmer() || !boss->HasAura(38112)) return false;
    if (plan.task == VashjCoreTask::Collect)
        return CanReceiveVashjCore(ai, bot) && CanLootVashjCore(bot, ai->GetCreature(plan.corpse), boss);
    if (!IsVashjGenerator(bot, ai->GetGameObject(plan.generator))) return false;
    if (plan.task == VashjCoreTask::Deliver)
        return plan.carrier == bot->GetObjectGuid() && bot->HasItemCount(31088, 1);
    Unit* carrier = ai->GetUnit(plan.carrier);
    return plan.task == VashjCoreTask::Receive && plan.receiver == bot->GetObjectGuid() &&
        CanReceiveVashjCore(ai, bot) && carrier && carrier->IsPlayer() && carrier->IsInWorld() &&
        carrier->IsAlive() && bot->IsInMap(carrier) && !carrier->HasCharmer() &&
        !static_cast<Player*>(carrier)->IsBeingTeleported() &&
        static_cast<Player*>(carrier)->GetGroup() == bot->GetGroup() &&
        static_cast<Player*>(carrier)->HasItemCount(31088, 1);
#else
    return false;
#endif
}

bool VashjCoreAction::isUseful()
{
#ifndef MANGOSBOT_ZERO
    VashjCorePlan plan;
    if (!GetPlan(ai, plan)) return false;
    if (plan.task == VashjCoreTask::Deliver)
    {
        if (bot->IsNonMeleeSpellCasted(false)) return false;
        GameObject* generator = ai->GetGameObject(plan.generator);
        if (generator->IsAtInteractDistance(bot) && bot->IsWithinLOSInMap(generator)) return true;
        Unit* receiver = ai->GetUnit(plan.receiver);
        return receiver && receiver->IsPlayer() && CanReceiveVashjCore(ai, static_cast<Player*>(receiver)) &&
            CanPassVashjCore(bot, static_cast<Player*>(receiver), generator);
    }
    if (!ai->CanMove()) return false;
    if (plan.task == VashjCoreTask::Collect) return bot->GetLootGuid().IsEmpty();
    const auto& point = plan.position.destination;
    return bot->GetDistance(point.x, point.y, point.z) > 1.0f || bot->IsMoving();
#else
    return false;
#endif
}

bool VashjCoreAction::Execute(Event& event)
{
#ifndef MANGOSBOT_ZERO
    VashjCorePlan plan;
    if (!GetPlan(ai, plan)) return false;
    if (plan.task == VashjCoreTask::Deliver)
    {
        if (bot->IsNonMeleeSpellCasted(false)) return false;
        GameObject* generator = ai->GetGameObject(plan.generator);
        Unit* receiver = ai->GetUnit(plan.receiver);
        const bool open = generator->IsAtInteractDistance(bot) && bot->IsWithinLOSInMap(generator);
        if (!open && (!receiver || !receiver->IsPlayer() || !CanReceiveVashjCore(ai, static_cast<Player*>(receiver)) ||
            !CanPassVashjCore(bot, static_cast<Player*>(receiver), generator))) return false;
        if (!open)
        {
            // Receiving the core roots this player. Recheck the actual landing
            // position immediately before dispatch, including new ground hazards.
            EncounterPosition landing = plan.position;
            landing.destination = {receiver->GetPositionX(), receiver->GetPositionY(), receiver->GetPositionZ()};
            if (!ValidateEncounterDestination(static_cast<Player*>(receiver)->GetPlayerbotAI(), landing)) return false;
        }
        Item* core = bot->GetItemByEntry(31088);
        const ItemPrototype* proto = core ? core->GetProto() : nullptr;
        if (!proto || !bot->IsSpellReady(open ? 3366 : 38134, proto)) return false;
        ai->StopMoving();
        if (!UseNativeEncounterItem(bot, core, open ? nullptr : receiver, open ? generator : nullptr)) return false;
        SetDuration(1000);
        return true;
    }
    if (!ai->CanMove() || !ValidateEncounterDestination(ai, plan.position)) return false;
    auto& point = plan.position.destination;
    if (plan.task == VashjCoreTask::Receive)
    {
        Player* carrier = static_cast<Player*>(ai->GetUnit(plan.carrier));
        const SpellEntry* spell = sSpellTemplate.LookupEntry<SpellEntry>(38134);
        const float range = spell ? GetSpellMaxRange(sSpellRangeStore.LookupEntry(spell->rangeIndex)) : 0;
        if (!std::isfinite(range) || range <= 0 || carrier->GetDistance(point.x, point.y, point.z) > range - 1)
            return false;
        if (bot->GetDistance(point.x, point.y, point.z) > 1)
        {
            if (bot->IsNonMeleeSpellCasted(true)) ai->InterruptSpell();
            return MoveTo(plan.position.map, point.x, point.y, point.z, false, IsReaction(), false, true);
        }
        ai->StopMoving();
        return true;
    }
    Creature* corpse = ai->GetCreature(plan.corpse);
    Unit* boss = ai->GetUnit(plan.position.boss);
    if (!CanLootVashjCore(bot, corpse, boss) || !bot->GetLootGuid().IsEmpty()) return false;
    if (bot->GetDistance(corpse) > INTERACTION_DISTANCE)
    {
        if (bot->IsNonMeleeSpellCasted(true)) ai->InterruptSpell();
        return MoveTo(plan.position.map, point.x, point.y, point.z, false, IsReaction(), false, true);
    }
    if (!bot->IsWithinLOSInMap(corpse)) return false;
    ai->StopMoving();
    if (bot->IsNonMeleeSpellCasted(true)) ai->InterruptSpell();
    WorldPacket packet(CMSG_LOOT);
    packet << corpse->GetObjectGuid();
    bot->GetSession()->HandleLootOpcode(packet);
    // Existing combat packet handling stores permitted loot and releases it.
    // The native item loot hook applies Paralyze only after actual acquisition.
    SetDuration(1000);
    return true;
#else
    return false;
#endif
}
