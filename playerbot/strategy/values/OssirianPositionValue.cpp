#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;

bool ai::IsOssirianCrystal(Player* bot, GameObject* crystal)
{
    return crystal && crystal->IsInWorld() && bot->IsInMap(crystal) && crystal->IsSpawned() &&
        crystal->GetEntry() == 180619 && crystal->GetLootState() != GO_JUST_DEACTIVATED &&
        !crystal->HasFlag(GAMEOBJECT_FLAGS, GO_FLAG_NO_INTERACT | GO_FLAG_IN_USE);
}

bool ai::OssirianNeedsCrystal(Unit* boss)
{
    if (!boss || !boss->IsInWorld() || !boss->IsAlive() || !boss->IsInCombat() ||
        boss->HasCharmer() || boss->GetMapId() != 509 || boss->GetEntry() != 15339) return false;
    if (boss->HasAura(25176)) return true;
    for (uint32 spell : {25177u, 25178u, 25180u, 25181u, 25183u})
        if (const SpellAuraHolder* aura = boss->GetSpellAuraHolder(spell))
            if (aura->GetAuraDuration() < 0 || aura->GetAuraDuration() > 5000) return false;
    return true;
}

Unit* ai::FindOssirianCrystalTrigger(Player* bot, GameObject* crystal)
{
    if (!IsOssirianCrystal(bot, crystal)) return nullptr;
    std::list<Unit*> nearby;
    MaNGOS::AllCreaturesOfEntryInRangeCheck check(crystal, 15590, 10.0f);
    MaNGOS::UnitListSearcher<decltype(check)> searcher(nearby, check);
    Cell::VisitAllObjects(crystal, searcher, 10.0f);
    Unit* selected = nullptr;
    for (Unit* unit : nearby)
        if (unit && unit->IsInWorld() && unit->IsAlive() && bot->IsInMap(unit) && unit->GetEntry() == 15590 &&
            (!selected || crystal->GetDistance(unit) < crystal->GetDistance(selected))) selected = unit;
    return selected;
}

Player* ai::OssirianCrystalUser(PlayerbotAI* ai, Unit* boss, GameObject* crystal)
{
    Player* bot = ai->GetBot();
    if (!bot->GetGroup() || !boss || !IsOssirianCrystal(bot, crystal)) return nullptr;
    Player* selected = nullptr;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!member || !member->IsInWorld() || !member->IsAlive() || !bot->IsInMap(member) ||
            member->GetGroup() != bot->GetGroup() || member->IsBeingTeleported() || member->HasCharmer() ||
            member == boss->GetVictim() || ai->IsTank(member) || ai->IsHeal(member) ||
            member->GetDistance(crystal) > 60 || !member->GetPlayerbotAI() ||
            member->GetPlayerbotAI()->IsRealPlayer() || !member->GetPlayerbotAI()->CanMove() ||
            !member->GetPlayerbotAI()->HasStrategy("dungeon", BotState::BOT_STATE_COMBAT)) continue;
        if (!selected || member->GetDistance(crystal) < selected->GetDistance(crystal) ||
            (member->GetDistance(crystal) == selected->GetDistance(crystal) && member->GetObjectGuid() < selected->GetObjectGuid()))
            selected = member;
    }
    return selected;
}

EncounterPosition OssirianPositionValue::Calculate()
{
    EncounterPosition plan;
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || bot->GetMapId() != 509 ||
        !bot->GetGroup() || bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer() || !ai->CanMove())
    { anchorCrystal.Clear(); return plan; }
    Unit* boss = nullptr;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "attackers"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit || !unit->IsInWorld() || !unit->IsAlive() || !unit->IsInCombat() ||
            unit->HasCharmer() || !bot->IsInMap(unit) || unit->GetEntry() != 15339) continue;
        if (boss && boss != unit) return plan;
        boss = unit;
    }
    if (!boss) { anchorCrystal.Clear(); return plan; }
    struct CrystalCheck
    {
        Player* bot;
        Player const& GetFocusObject() const { return *bot; }
        bool operator()(GameObject* object) const { return IsOssirianCrystal(bot, object); }
    } check{bot};
    std::list<GameObject*> objects;
    MaNGOS::GameObjectListSearcher<CrystalCheck> searcher(objects, check);
    Cell::VisitAllObjects(boss, searcher, 80.0f);
    GameObject* crystal = nullptr;
    for (GameObject* object : objects)
        if (IsOssirianCrystal(bot, object) && std::fabs(object->GetPositionZ() - boss->GetPositionZ()) <= 8 &&
            (!crystal || boss->GetDistance(object) < boss->GetDistance(crystal) ||
                (boss->GetDistance(object) == boss->GetDistance(crystal) && object->GetObjectGuid() < crystal->GetObjectGuid())))
            crystal = object;
    if (!crystal) { anchorCrystal.Clear(); return plan; }
    const bool tank = boss->GetVictim() == bot && ai->IsTank(bot);
    if (!tank && OssirianCrystalUser(ai, boss, crystal) != bot) return plan;
    plan.active = true; plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    plan.boss = boss->GetObjectGuid(); plan.source = crystal->GetObjectGuid(); plan.spell = 25192;
    float dx = crystal->GetPositionX() - boss->GetPositionX(), dy = crystal->GetPositionY() - boss->GetPositionY();
    const float length = std::hypot(dx, dy);
    if (length < 1) { dx = 1; dy = 0; } else { dx /= length; dy /= length; }
    const float offset = tank ? 8.0f : 1.0f;
    plan.destination = {crystal->GetPositionX() + dx * offset, crystal->GetPositionY() + dy * offset, crystal->GetPositionZ()};
    if (tank)
    {
        // Keep the pull direction stable when the boss crosses the crystal.
        // Recomputing from its new side would make the tank run back and forth.
        if (anchorCrystal != crystal->GetObjectGuid())
        { anchorCrystal = crystal->GetObjectGuid(); tankAnchor = plan.destination; }
        plan.destination = tankAnchor;
    }
    else anchorCrystal.Clear();
    plan.active = ValidateEncounterDestination(ai, plan);
    return plan;
}
