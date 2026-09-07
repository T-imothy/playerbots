#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

Player* ai::NajentusSpineVictim(PlayerbotAI* ai, GameObject* spine)
{
#ifndef MANGOSBOT_ZERO
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || bot->GetMapId() != 564 || !bot->GetGroup() || !spine ||
        !spine->IsInWorld() || !bot->IsInMap(spine) || !spine->IsSpawned() || spine->GetEntry() != 185584 ||
        spine->GetSpellId() != 39929 || spine->GetLootState() != GO_READY ||
        spine->HasFlag(GAMEOBJECT_FLAGS, GO_FLAG_NO_INTERACT | GO_FLAG_IN_USE)) return nullptr;
    Unit* source = ai->GetUnit(spine->GetSpawnerGuid());
    if (!source || !source->IsPlayer() || !source->IsInWorld() || !source->IsAlive() ||
        !bot->IsInMap(source) || source->HasCharmer()) return nullptr;
    Player* victim = static_cast<Player*>(source);
    if (victim->GetGroup() != bot->GetGroup() || victim->IsBeingTeleported()) return nullptr;
    const SpellAuraHolder* aura = victim->GetSpellAuraHolder(39837);
    Unit* boss = aura ? aura->GetCaster() : nullptr;
    return boss && boss->IsInWorld() && boss->IsAlive() && boss->IsInCombat() &&
        !boss->HasCharmer() && bot->IsInMap(boss) && boss->GetEntry() == 22887 ? victim : nullptr;
#else
    return nullptr;
#endif
}

Player* ai::NajentusSpineUser(PlayerbotAI* ai, GameObject* spine)
{
#ifndef MANGOSBOT_ZERO
    Player* victim = NajentusSpineVictim(ai, spine);
    if (!victim) return nullptr;
    Player* bot = ai->GetBot();
    Unit* boss = victim->GetSpellAuraHolder(39837)->GetCaster();
    Player* selected = nullptr;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!member || !member->IsInWorld() || !member->IsAlive() || !bot->IsInMap(member) ||
            member->GetGroup() != bot->GetGroup() || member->IsBeingTeleported() || member->HasCharmer() ||
            member == boss->GetVictim() || ai->IsTank(member) || member->HasAura(39837) ||
            member->GetDistance(spine) > 50 || !member->GetPlayerbotAI() ||
            member->GetPlayerbotAI()->IsRealPlayer() || !member->GetPlayerbotAI()->CanMove() ||
            !member->GetPlayerbotAI()->HasStrategy("dungeon", BotState::BOT_STATE_COMBAT)) continue;
        ItemPosCountVec destination;
        if (member->CanStoreNewItem(NULL_BAG, NULL_SLOT, destination, 32408, 1) != EQUIP_ERR_OK) continue;
        // Prefer a DPS so the rescue does not occupy the raid's healers.
        if (!selected || (ai->IsHeal(selected) && !ai->IsHeal(member)) ||
            (ai->IsHeal(selected) == ai->IsHeal(member) &&
                (member->GetDistance(spine) < selected->GetDistance(spine) ||
                    (member->GetDistance(spine) == selected->GetDistance(spine) && member->GetObjectGuid() < selected->GetObjectGuid()))))
            selected = member;
    }
    return selected;
#else
    return nullptr;
#endif
}

EncounterPosition NajentusPositionValue::Calculate()
{
    EncounterPosition plan;
#ifndef MANGOSBOT_ZERO
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || bot->GetMapId() != 564 ||
        !bot->GetGroup() || bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer() || !ai->CanMove()) return plan;
    GameObject* selected = nullptr;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "nearest game objects no los"))
    {
        GameObject* spine = ai->GetGameObject(guid);
        if (!NajentusSpineVictim(ai, spine) || NajentusSpineUser(ai, spine) != bot) continue;
        if (!selected || bot->GetDistance(spine) < bot->GetDistance(selected) ||
            (bot->GetDistance(spine) == bot->GetDistance(selected) && spine->GetObjectGuid() < selected->GetObjectGuid())) selected = spine;
    }
    if (!selected) return plan;
    Player* victim = NajentusSpineVictim(ai, selected);
    if (!victim) return plan;
    plan.active = true; plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    plan.boss = victim->GetSpellAuraHolder(39837)->GetCaster()->GetObjectGuid();
    plan.source = selected->GetObjectGuid(); plan.spell = 39929;
    plan.destination = {selected->GetPositionX(), selected->GetPositionY(), selected->GetPositionZ()};
    plan.active = ValidateEncounterDestination(ai, plan);
#endif
    return plan;
}
