#include "playerbot/playerbot.h"
#include "VashjCoreValue.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;

Unit* ai::FindVashjCorePhase(PlayerbotAI* ai)
{
#ifndef MANGOSBOT_ZERO
    Player* bot = ai->GetBot();
    if (bot->GetMapId() != 548 || !bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() ||
        !bot->GetGroup() || bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer() ||
        !ai->HasStrategy("dungeon", BotState::BOT_STATE_COMBAT)) return nullptr;
    // The shielded boss need not be present in an attackable-target value.
    std::list<Unit*> bosses;
    MaNGOS::AllCreaturesOfEntryInRangeCheck check(bot, 21212, 120.0f);
    MaNGOS::UnitListSearcher<decltype(check)> searcher(bosses, check);
    Cell::VisitAllObjects(bot, searcher, 120.0f);
    Unit* selected = nullptr;
    for (Unit* boss : bosses)
    {
        if (!boss->IsInWorld() || !boss->IsAlive() || !boss->IsInCombat() || !bot->IsInMap(boss) ||
            boss->HasCharmer() || !boss->HasAura(38112)) continue;
        if (selected && selected != boss) return nullptr;
        selected = boss;
    }
    return selected;
#else
    return nullptr;
#endif
}

bool ai::IsVashjGenerator(Player* bot, GameObject* object)
{
    return object && object->IsInWorld() && object->IsSpawned() && bot->IsInMap(object) &&
        object->GetEntry() >= 185051 && object->GetEntry() <= 185054 &&
        object->GetGOInfo()->GetLockId() == 1718 &&
        !object->HasFlag(GAMEOBJECT_FLAGS, GO_FLAG_NO_INTERACT | GO_FLAG_IN_USE);
}

bool ai::CanReceiveVashjCore(PlayerbotAI* ai, Player* member)
{
    Player* bot = ai->GetBot();
    if (!member || !member->IsInWorld() || !member->IsAlive() || !bot->IsInMap(member) ||
        member->GetGroup() != bot->GetGroup() || member->IsBeingTeleported() || member->HasCharmer() ||
        member->HasItemCount(31088, 1) || ai->IsTank(member) || ai->IsHeal(member)) return false;
    // Preserve the actual add victim's job, even when a DPS is kiting rather
    // than using the tank role. A received core would root that player.
    for (Unit* attacker : member->getAttackers())
        if (attacker && attacker->IsInWorld() && attacker->IsAlive() && member->IsInMap(attacker) &&
            attacker->GetVictim() == member && (attacker->GetEntry() == 22056 || attacker->GetEntry() == 22055)) return false;
    PlayerbotAI* memberAI = member->GetPlayerbotAI();
    if (!memberAI || memberAI->IsRealPlayer() || !memberAI->CanMove() ||
        !memberAI->HasStrategy("dungeon", BotState::BOT_STATE_COMBAT) ||
        memberAI->HasStrategy("stay", BotState::BOT_STATE_COMBAT) ||
        memberAI->HasStrategy("guard", BotState::BOT_STATE_COMBAT)) return false;
    auto context = memberAI->GetAiObjectContext();
    if (context->GetValue<std::set<uint32>&>("skip loot list")->Get().count(31088)) return false;
    const ObjectGuid order = context->GetValue<ObjectGuid>("attack target")->Get();
    Unit* commanded = memberAI->GetUnit(order);
    Unit* marked = context->GetValue<Unit*>("rti target")->Get();
    if ((commanded && commanded->IsInWorld() && commanded->IsAlive() && member->IsInMap(commanded)) ||
        (marked && marked->IsInWorld() && marked->IsAlive() && member->IsInMap(marked))) return false;
    ItemPosCountVec destination;
    return member->CanStoreNewItem(NULL_BAG, NULL_SLOT, destination, 31088, 1) == EQUIP_ERR_OK;
}

bool ai::CanLootVashjCore(Player* player, Creature* corpse, Unit* boss)
{
#ifndef MANGOSBOT_ZERO
    if (!corpse || !boss || !corpse->IsInWorld() || corpse->IsAlive() || !player->IsInMap(corpse) ||
        corpse->GetEntry() != 22009 || corpse->GetSpawnerGuid() != boss->GetObjectGuid() ||
        !corpse->HasFlag(UNIT_DYNAMIC_FLAGS, UNIT_DYNFLAG_LOOTABLE)) return false;
    Loot* loot = sLootMgr.GetLoot(player, corpse->GetObjectGuid());
    if (!loot || !loot->CanLoot(player)) return false;
    LootItemList items;
    loot->GetLootItemsListFor(player, items);
    for (LootItem* item : items)
    {
        if (!item || item->itemId != 31088 || item->isBlocked) continue;
        const auto slot = item->GetSlotTypeForSharedLoot(player, loot);
        if (slot == LOOT_SLOT_NORMAL || slot == LOOT_SLOT_OWNER) return true;
    }
#endif
    return false;
}

bool ai::CanPassVashjCore(Player* carrier, Player* receiver, GameObject* generator)
{
#ifndef MANGOSBOT_ZERO
    if (!carrier || !receiver || carrier == receiver || !generator ||
        !carrier->HasItemCount(31088, 1) || receiver->HasItemCount(31088, 1) ||
        !receiver->IsInWorld() || !receiver->IsAlive() || receiver->IsBeingTeleported() || receiver->HasCharmer() ||
        !carrier->IsInMap(receiver) || !carrier->GetGroup() || carrier->GetGroup() != receiver->GetGroup() ||
        !IsVashjGenerator(carrier, generator)) return false;
    const SpellEntry* spell = sSpellTemplate.LookupEntry<SpellEntry>(38134);
    const float range = spell ? GetSpellMaxRange(sSpellRangeStore.LookupEntry(spell->rangeIndex)) : 0;
    if (!std::isfinite(range) || range <= 0 || carrier->GetDistance(receiver) > range ||
        !carrier->IsWithinLOSInMap(receiver)) return false;
    // Every throw must make measurable progress, or arrive at the generator.
    // This prevents nearby bots from continually throwing the same core back.
    return (generator->IsAtInteractDistance(receiver) && receiver->IsWithinLOSInMap(generator)) ||
        receiver->GetDistance(generator) + 3.0f < carrier->GetDistance(generator);
#else
    return false;
#endif
}

VashjCorePlan VashjCoreValue::Calculate()
{
    VashjCorePlan result;
#ifndef MANGOSBOT_ZERO
    Unit* boss = FindVashjCorePhase(ai);
    if (!boss) return result;
    struct GeneratorCheck
    {
        Player* bot;
        Player const& GetFocusObject() const { return *bot; }
        bool operator()(GameObject* object) const { return IsVashjGenerator(bot, object); }
    } check{bot};
    std::list<GameObject*> generators;
    MaNGOS::GameObjectListSearcher<GeneratorCheck> searcher(generators, check);
    Cell::VisitAllObjects(boss, searcher, 100.0f);
    if (generators.empty()) return result;

    std::vector<Player*> carriers, available;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!member || !member->IsInWorld() || !member->IsAlive() || !bot->IsInMap(member) ||
            member->GetGroup() != bot->GetGroup() || member->IsBeingTeleported() || member->HasCharmer() ||
            boss->GetDistance(member) > 120) continue;
        if (member->HasItemCount(31088, 1)) carriers.push_back(member);
        else if (CanReceiveVashjCore(ai, member)) available.push_back(member);
    }
    auto byGuid = [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); };
    std::sort(carriers.begin(), carriers.end(), byGuid);
    std::sort(available.begin(), available.end(), byGuid);
    auto fill = [&](VashjCoreTask task, GameObject* generator, Player* carrier, Player* receiver) {
        result.task = task;
        result.generator = generator ? generator->GetObjectGuid() : ObjectGuid();
        result.carrier = carrier ? carrier->GetObjectGuid() : ObjectGuid();
        result.receiver = receiver ? receiver->GetObjectGuid() : ObjectGuid();
        result.position.active = true;
        result.position.map = bot->GetMapId(); result.position.instance = bot->GetInstanceId();
        result.position.boss = boss->GetObjectGuid(); result.position.spell = 38134;
    };
    const SpellEntry* pass = sSpellTemplate.LookupEntry<SpellEntry>(38134);
    const float range = pass ? GetSpellMaxRange(sSpellRangeStore.LookupEntry(pass->rangeIndex)) : 0;
    if (!std::isfinite(range) || range <= 6) return result;
    for (Player* carrier : carriers)
    {
        GameObject* generator = nullptr;
        for (GameObject* candidate : generators)
            if (!generator || carrier->GetDistance(candidate) < carrier->GetDistance(generator) ||
                (carrier->GetDistance(candidate) == carrier->GetDistance(generator) &&
                    candidate->GetObjectGuid() < generator->GetObjectGuid())) generator = candidate;
        if (generator->IsAtInteractDistance(carrier) && carrier->IsWithinLOSInMap(generator))
        {
            if (carrier == bot) { fill(VashjCoreTask::Deliver, generator, carrier, nullptr); return result; }
            continue;
        }
        const float dx = generator->GetPositionX() - carrier->GetPositionX();
        const float dy = generator->GetPositionY() - carrier->GetPositionY();
        const float dz = generator->GetPositionZ() - carrier->GetPositionZ();
        const float distance = std::sqrt(dx * dx + dy * dy + dz * dz);
        if (!std::isfinite(distance) || distance <= 0) continue;
        const float fraction = std::min(1.0f, (range - 4.0f) / distance);
        encounter::Point waypoint{carrier->GetPositionX() + dx * fraction,
            carrier->GetPositionY() + dy * fraction, carrier->GetPositionZ() + dz * fraction};
        Player* receiver = nullptr;
        bool ready = false;
        float best = 0;
        for (Player* candidate : available)
        {
            bool canPass = CanPassVashjCore(carrier, candidate, generator);
            float score = canPass ? candidate->GetDistance(generator) :
                candidate->GetDistance(waypoint.x, waypoint.y, waypoint.z);
            if (!canPass && score > 55) continue;
            if (!receiver || (canPass && !ready) || (canPass == ready && score < best))
            { receiver = candidate; ready = canPass; best = score; }
        }
        if (receiver) available.erase(std::find(available.begin(), available.end(), receiver));
        if (carrier == bot)
        {
            fill(VashjCoreTask::Deliver, generator, carrier, receiver);
            return result;
        }
        if (receiver == bot)
        {
            fill(VashjCoreTask::Receive, generator, carrier, receiver);
            // Try a bounded fan toward the generator when a direct stair/edge
            // endpoint is obstructed. Every route still uses native path and
            // hazard validation; a failed path never becomes a shortcut.
            const float angle = std::atan2(dy, dx);
            for (unsigned sample = 0; sample < (ready ? 1u : 8u); ++sample)
            {
                static const float offsets[] = {0, 0.4f, -0.4f, 0.8f, -0.8f, 0, 0.4f, -0.4f};
                const float scale = sample >= 5 ? 0.6f : 1.0f;
                const float horizontal = std::hypot(dx, dy) * fraction * scale;
                result.position.destination = ready ? encounter::Point{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()} :
                    encounter::Point{carrier->GetPositionX() + horizontal * std::cos(angle + offsets[sample]),
                        carrier->GetPositionY() + horizontal * std::sin(angle + offsets[sample]),
                        carrier->GetPositionZ() + dz * fraction * scale};
                if (!ValidateEncounterDestination(ai, result.position)) continue;
                const auto& point = result.position.destination;
                if (carrier->GetDistance(point.x, point.y, point.z) > range - 1 ||
                    !carrier->IsWithinLOS(point.x, point.y, point.z + bot->GetCollisionHeight(), true)) continue;
                const float remaining = generator->GetDistance(point.x, point.y, point.z);
                if (remaining > 2 && remaining + 3 >= carrier->GetDistance(generator)) continue;
                return result;
            }
            return VashjCorePlan();
        }
    }
    if (std::find(available.begin(), available.end(), bot) == available.end()) return result;
    std::list<Unit*> elementals;
    MaNGOS::AllCreaturesOfEntryInRangeCheck corpseCheck(boss, 22009, 120.0f);
    MaNGOS::UnitListSearcher<decltype(corpseCheck)> corpseSearch(elementals, corpseCheck);
    Cell::VisitAllObjects(boss, corpseSearch, 120.0f);
    Creature* selected = nullptr;
    for (Unit* unit : elementals)
    {
        Creature* corpse = static_cast<Creature*>(unit);
        Player* collector = nullptr;
        for (Player* member : available)
            if (member->GetDistance(corpse) <= 55 && CanLootVashjCore(member, corpse, boss) &&
                (!collector || member->GetDistance(corpse) < collector->GetDistance(corpse))) collector = member;
        if (collector != bot) continue;
        if (!selected || bot->GetDistance(corpse) < bot->GetDistance(selected) ||
            (bot->GetDistance(corpse) == bot->GetDistance(selected) && corpse->GetObjectGuid() < selected->GetObjectGuid())) selected = corpse;
    }
    if (selected)
    {
        fill(VashjCoreTask::Collect, nullptr, nullptr, bot);
        result.corpse = selected->GetObjectGuid();
        result.position.destination = {selected->GetPositionX(), selected->GetPositionY(), selected->GetPositionZ()};
        if (!ValidateEncounterDestination(ai, result.position)) return VashjCorePlan();
    }
#endif
    return result;
}
