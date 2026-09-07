#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

bool NajentusSpineAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan)
{
#ifndef MANGOSBOT_ZERO
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || bot->GetMapId() != 564 ||
        !bot->GetGroup() || bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer() || !ai->CanMove()) return false;
    plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("najentus spine position")->Get();
    if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId() || plan.spell != 39929) return false;
    GameObject* spine = ai->GetGameObject(plan.source);
    Player* victim = NajentusSpineVictim(ai, spine);
    return victim && victim->GetSpellAuraHolder(39837)->GetCaster()->GetObjectGuid() == plan.boss &&
        NajentusSpineUser(ai, spine) == bot;
#else
    return false;
#endif
}

bool NajentusSpineAction::isUseful()
{
    EncounterPosition plan;
    return GetPlan(ai, plan);
}

bool NajentusSpineAction::Execute(Event& event)
{
#ifndef MANGOSBOT_ZERO
    EncounterPosition plan;
    if (!GetPlan(ai, plan) || !ValidateEncounterDestination(ai, plan)) return false;
    GameObject* spine = ai->GetGameObject(plan.source);
    if (!NajentusSpineVictim(ai, spine) || NajentusSpineUser(ai, spine) != bot) return false;
    if (!spine->IsAtInteractDistance(bot))
        return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
    if (!bot->IsWithinLOSInMap(spine)) return false;
    ai->StopMoving();
    if (bot->IsNonMeleeSpellCasted(true)) ai->InterruptSpell();
    WorldPacket packet(CMSG_GAMEOBJ_USE);
    packet << spine->GetObjectGuid();
    bot->GetSession()->HandleGameObjectUseOpcode(packet);
    SetDuration(1000); // Native goober creates the item and activates the rescue trap.
    return true;
#else
    return false;
#endif
}

Unit* NajentusShieldAction::GetTarget()
{
#ifndef MANGOSBOT_ZERO
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || bot->GetMapId() != 564 ||
        !bot->GetGroup() || bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer() ||
        !bot->HasItemCount(32408, 1)) return nullptr;
    Unit* boss = nullptr;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "attackers"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit || !unit->IsInWorld() || !unit->IsAlive() || !unit->IsInCombat() ||
            !bot->IsInMap(unit) || unit->HasCharmer() || unit->GetEntry() != 22887 || !unit->HasAura(39872)) continue;
        if (boss && boss != unit) return nullptr;
        boss = unit;
    }
    if (!boss) return nullptr;
    const SpellEntry* burst = sSpellTemplate.LookupEntry<SpellEntry>(39878);
    const SpellEntry* hurl = sSpellTemplate.LookupEntry<SpellEntry>(39948);
    const ItemPrototype* item = sObjectMgr.GetItemPrototype(32408);
    if (!burst || !hurl || !item) return nullptr;
    const float radius = NativeEncounterSpellRadius(39878);
    const float range = GetSpellMaxRange(sSpellRangeStore.LookupEntry(hurl->rangeIndex));
    const int32 damage = burst->EffectBasePoints[EFFECT_INDEX_0] + std::max(1, burst->EffectDieSides[EFFECT_INDEX_0]);
    if (!std::isfinite(radius) || radius <= 0 || !std::isfinite(range) || range <= 0 || damage <= 0) return nullptr;
    Player* selected = nullptr;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!member || !member->IsInWorld() || !member->IsAlive() || !bot->IsInMap(member) ||
            member->GetGroup() != bot->GetGroup() || member->IsBeingTeleported() || member->HasCharmer()) continue;
        // Do not deliberately trigger the known raw burst while an exposed
        // group member is below it. Native mitigation/absorbs still decide damage.
        if (boss->GetDistance(member) <= radius && member->GetHealth() <= uint32(damage)) return nullptr;
        if (!member->HasItemCount(32408, 1) || !member->IsSpellReady(39948, item) ||
            member->HasAura(39837) || boss->GetDistance(member) > range || !member->IsWithinLOSInMap(boss) ||
            !member->GetPlayerbotAI() || member->GetPlayerbotAI()->IsRealPlayer() ||
            !member->GetPlayerbotAI()->HasStrategy("dungeon", BotState::BOT_STATE_COMBAT)) continue;
        if (!selected || member->GetObjectGuid() < selected->GetObjectGuid()) selected = member;
    }
    return selected == bot ? boss : nullptr;
#else
    return nullptr;
#endif
}

bool NajentusShieldAction::isUseful()
{
    return GetTarget() && UseItemIdAction::isUseful();
}

bool NajentusShieldAction::Execute(Event& event)
{
    return isUseful() && UseItemIdAction::Execute(event);
}
