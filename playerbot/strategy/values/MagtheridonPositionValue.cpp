#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;

bool ai::HasMagtheridonChannel(Player* player)
{
#ifndef MANGOSBOT_ZERO
    if (!player || !player->IsInWorld() || !player->IsAlive() || player->GetMapId() != 544 ||
        player->HasCharmer() || player->IsBeingTeleported()) return false;
    const Spell* channel = player->GetCurrentSpell(CURRENT_CHANNELED_SPELL);
    return channel && channel->m_spellInfo && channel->getState() != SPELL_STATE_FINISHED &&
        channel->m_spellInfo->Id == 30410;
#else
    return false;
#endif
}

bool ai::IsMagtheridonNova(Unit* boss)
{
#ifndef MANGOSBOT_ZERO
    if (!boss || !boss->IsInWorld() || !boss->IsAlive() || !boss->IsInCombat() ||
        boss->HasCharmer() || boss->GetMapId() != 544 || boss->GetEntry() != 17257) return false;
    for (const auto type : {CURRENT_GENERIC_SPELL, CURRENT_CHANNELED_SPELL})
    {
        const Spell* spell = boss->GetCurrentSpell(type);
        if (spell && spell->m_spellInfo && spell->getState() != SPELL_STATE_FINISHED &&
            spell->m_spellInfo->Id == 30616) return true;
    }
#endif
    return false;
}

bool ai::IsMagtheridonCubeUser(PlayerbotAI* ai, Player* player, Unit* boss)
{
#ifndef MANGOSBOT_ZERO
    Player* bot = ai->GetBot();
    PlayerbotAI* memberAI = player ? player->GetPlayerbotAI() : nullptr;
    return player && memberAI && !memberAI->IsRealPlayer() && player->IsInWorld() && player->IsAlive() &&
        player->GetSession() && !player->GetSession()->isLogingOut() && !player->IsBeingTeleported() &&
        !player->HasCharmer() && bot->GetMapId() == 544 && bot->GetGroup() &&
        player->GetGroup() == bot->GetGroup() && bot->IsInMap(player) &&
        boss && boss->IsInWorld() && boss->IsAlive() && boss->IsInCombat() && !boss->HasCharmer() &&
        boss->GetEntry() == 17257 && bot->IsInMap(boss) && player->GetDistance(boss) <= 100 &&
        !boss->HasAura(30205) && boss->GetVictim() != player && !ai->IsTank(player) && !ai->IsHeal(player) &&
        !player->HasAura(44032) && !player->HasAura(30410) && !HasMagtheridonChannel(player) &&
        memberAI->HasStrategy("dungeon", BotState::BOT_STATE_COMBAT);
#else
    return false;
#endif
}

bool ai::IsMagtheridonCube(Player* player, GameObject* cube)
{
#ifndef MANGOSBOT_ZERO
    return player && player->IsInWorld() && player->GetMapId() == 544 && cube && cube->IsInWorld() &&
        player->IsInMap(cube) && cube->GetEntry() == 181713 && cube->GetGoType() == GAMEOBJECT_TYPE_GOOBER &&
        cube->IsSpawned() && !cube->HasFlag(GAMEOBJECT_FLAGS, GO_FLAG_NO_INTERACT) &&
        cube->GetLootState() != GO_JUST_DEACTIVATED;
#else
    return false;
#endif
}

Unit* ai::FindMagtheridonCubeTrigger(Player* player, GameObject* cube)
{
#ifndef MANGOSBOT_ZERO
    if (!IsMagtheridonCube(player, cube)) return nullptr;
    std::list<Unit*> nearby;
    MaNGOS::AllCreaturesOfEntryInRangeCheck check(cube, 17376, 8.0f);
    MaNGOS::UnitListSearcher<decltype(check)> searcher(nearby, check);
    Cell::VisitAllObjects(cube, searcher, 8.0f);
    Unit* trigger = nullptr;
    for (Unit* unit : nearby)
        if (unit && unit->IsInWorld() && unit->IsAlive() && player->IsInMap(unit))
        {
            if (trigger) return nullptr; // Ambiguous native spawn data: don't click the wrong beam.
            trigger = unit;
        }
    return trigger;
#else
    return nullptr;
#endif
}

EncounterPosition MagtheridonPositionValue::Calculate()
{
    EncounterPosition plan;
#ifndef MANGOSBOT_ZERO
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 544 || !bot->GetGroup() || !bot->IsInCombat()) return plan;
    std::list<Unit*> bosses;
    MaNGOS::AllCreaturesOfEntryInRangeCheck bossCheck(bot, 17257, 100.0f);
    MaNGOS::UnitListSearcher<decltype(bossCheck)> bossSearch(bosses, bossCheck);
    Cell::VisitAllObjects(bot, bossSearch, 100.0f);
    Unit* boss = nullptr;
    for (Unit* unit : bosses)
        if (unit && unit->IsInWorld() && unit->IsAlive() && unit->IsInCombat() && !unit->HasCharmer() &&
            bot->IsInMap(unit) && !unit->HasAura(30205))
        { if (boss) return plan; boss = unit; }
    if (!boss) return plan;
    plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    plan.boss = boss->GetObjectGuid(); plan.spell = 30410;
    if (HasMagtheridonChannel(bot)) { plan.active = true; return plan; }
    if (!IsMagtheridonCubeUser(ai, bot, boss) || !ai->CanMove()) return plan;

    struct CubeCheck
    {
        Player* player;
        Player const& GetFocusObject() const { return *player; }
        bool operator()(GameObject* cube) const { return IsMagtheridonCube(player, cube); }
    } cubeCheck{bot};
    GameObjectList nearby;
    MaNGOS::GameObjectListSearcher<decltype(cubeCheck)> cubeSearch(nearby, cubeCheck);
    Cell::VisitGridObjects(boss, cubeSearch, 100.0f);
    std::vector<GameObject*> cubes;
    for (GameObject* cube : nearby)
    {
        Unit* trigger = FindMagtheridonCubeTrigger(bot, cube);
        // A real player's beam also owns a cube. Its GO auto-close is much
        // shorter than its channel, so GO_FLAG_IN_USE alone is insufficient.
        if (trigger && !trigger->HasAura(30410) && !cube->HasFlag(GAMEOBJECT_FLAGS, GO_FLAG_IN_USE))
            cubes.push_back(cube);
    }
    if (cubes.empty() || cubes.size() > 5) return plan;
    std::sort(cubes.begin(), cubes.end(), [](GameObject* left, GameObject* right)
        { return left->GetObjectGuid() < right->GetObjectGuid(); });
    std::vector<Player*> members;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        if (IsMagtheridonCubeUser(ai, ref->getSource(), boss)) members.push_back(ref->getSource());
    // Stable role/GUID ordering, not a nearest-player race that changes every
    // time a participant takes a step. Never assign humans, tanks or healers.
    std::sort(members.begin(), members.end(), [this](Player* left, Player* right)
    {
        if (ai->IsRanged(left) != ai->IsRanged(right)) return ai->IsRanged(left);
        return left->GetObjectGuid() < right->GetObjectGuid();
    });
    for (size_t index = 0; index < cubes.size() && index < members.size(); ++index)
    {
        if (members[index] != bot) continue;
        // Ranged volunteers can attack from their cube between Novas. Melee
        // relief only leaves melee during a real Nova; no guessed boss timer.
        if (!ai->IsRanged(bot) && !IsMagtheridonNova(boss)) return plan;
        GameObject* cube = cubes[index];
        const float reach = cube->GetInteractionDistance();
        if (!std::isfinite(reach) || reach < 1 || reach > 10) return plan;
        const float angle = cube->GetAngle(boss);
        plan.destination = {cube->GetPositionX() + std::cos(angle) * reach * 0.5f,
            cube->GetPositionY() + std::sin(angle) * reach * 0.5f, cube->GetPositionZ()};
        plan.source = cube->GetObjectGuid(); plan.active = true;
        plan.active = ValidateEncounterDestination(ai, plan) &&
            cube->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) < reach;
        return plan;
    }
#endif
    return plan;
}
