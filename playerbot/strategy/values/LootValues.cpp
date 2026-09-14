#include "playerbot/playerbot.h"
#include "SharedValueContext.h"
#include "LootValues.h"
#include "playerbot/strategy/actions/LootAction.h"

using namespace ai;

// Penqle's Singleton<> requires an explicit instantiation in a .cpp file.
INSTANTIATE_SINGLETON_1(ai::SharedObjectContext);

// LootAccess methods read from the wrapped Loot* (proper accessor-based
// access; the original layout-cheat reinterpret_cast pattern was removed).

// Empty static fallbacks used when LootAccess wraps a null Loot* (defensive).
static const std::set<ObjectGuid> s_emptyGuidSet;
static const LootItemList s_emptyLootItems;

std::set<ObjectGuid> const& LootAccess::playersLooting() const
{
	if (!loot)
		return s_emptyGuidSet;
	return loot->GetLootingPlayers();
}

LootType LootAccess::lootType() const
{
	return loot ? loot->loot_type : LOOT_CORPSE;
}

uint32 LootAccess::gold() const
{
	return loot ? loot->gold : 0;
}

std::set<ObjectGuid> const& LootAccess::playersOpened() const
{
	// Penqle has no per-player "released the corpse" tracking; return empty set.
	return s_emptyGuidSet;
}

LootItemList const& LootAccess::lootItems() const
{
	if (!loot)
		return s_emptyLootItems;
	return loot->items;
}

std::vector<LootItem*> LootAccess::GetLootContentFor(Player* player) const
{
    std::vector<LootItem*> result;
    if (!loot || !player || !loot->IsAllowedLooter(player->GetObjectGuid(), false))
        return result;

    PermissionTypes permission = OWNER_PERMISSION;
    if (!loot->m_personal)
    {
        Group* group = player->GetGroup();
        if (!group)
            return result;
        switch (group->GetLootMethod())
        {
            case MASTER_LOOT: permission = MASTER_PERMISSION; break;
            case FREE_FOR_ALL: permission = ALL_PERMISSION; break;
            case ROUND_ROBIN: permission = ROUND_ROBIN_PERMISSION; break;
            default: permission = GROUP_PERMISSION; break;
        }
    }

    // The native serializer is read-only despite the historical mutable view.
    // Actual opening/awarding still goes through native session handlers, which
    // recheck target ownership, distance and current group rights.
    Loot* native = const_cast<Loot*>(loot);
    ByteBuffer view;
    view << LootView(*native, player, permission);
    view.read_skip<uint32>(); // money
    uint8 count;
    view >> count;
    for (uint8 i = 0; i < count; ++i)
    {
        uint8 slot, type;
        view >> slot;
        for (uint8 field = 0; field < 5; ++field)
            view.read_skip<uint32>();
        view >> type;
        if (type != LOOT_SLOT_TYPE_ALLOW_LOOT)
            continue;
        if (LootItem* item = native->LootItemInSlot(slot, player->GetGUIDLow()))
            result.push_back(item);
    }
    return result;
}

uint32 LootAccess::GetLootStatusFor(Player const* player) const
{
    if (!loot || !player || !loot->IsAllowedLooter(player->GetObjectGuid(), false))
        return 0;
    uint32 status = loot->gold ? LOOT_STATUS_CONTAIN_GOLD : 0;
    for (LootItem const* item : GetLootContentFor(const_cast<Player*>(player)))
    {
        status |= LOOT_STATUS_NOT_FULLY_LOOTED;
        if (item->freeforall)
            status |= LOOT_STATUS_CONTAIN_FFA;
        if (!loot->roundRobinPlayer && !item->freeforall)
            status |= LOOT_STATUS_CONTAIN_RELEASED_ITEMS;
    }
    return status;
}

bool LootAccess::IsLootedFor(Player const* player) const
{
    return GetLootStatusFor(player) == 0;
}

bool LootAccess::IsLootedForAll() const
{
    // Native count includes remaining per-player quest/FFA/conditional copies.
    return !loot || loot->isLooted();
}

LootTemplate const* DropMapValue::GetLootTemplate(ObjectGuid guid, LootType type)
{
	LootTemplate const* lTemplate = nullptr;

	if (guid.IsCreature())
	{
		CreatureInfo const* info = sObjectMgr.GetCreatureTemplate(guid.GetEntry());

		if (info)
		{
			if (type == LOOT_CORPSE)
				lTemplate = LootTemplates_Creature.GetLootFor(info->LootId);
			else if (type == LOOT_PICKPOCKETING && info->PickpocketLootId)
				lTemplate = LootTemplates_Pickpocketing.GetLootFor(info->PickpocketLootId);
			else if (type == LOOT_SKINNING && info->SkinningLootId)
				lTemplate = LootTemplates_Skinning.GetLootFor(info->SkinningLootId);
		}
	}
	else if (guid.IsGameObject())
	{
		GameObjectInfo const* info = sObjectMgr.GetGameObjectInfo(guid.GetEntry());

		if (info && info->GetLootId() != 0)
		{
			if (type == LOOT_CORPSE)
				lTemplate = LootTemplates_Gameobject.GetLootFor(info->GetLootId());
			else if (type == LOOT_FISHINGHOLE)
				lTemplate = LootTemplates_Fishing.GetLootFor(info->GetLootId());
		}
	}
	else if (guid.IsItem())
	{
		ItemPrototype const* proto = sObjectMgr.GetItemPrototype(guid.GetEntry());
		
		if (proto)
		{
			if (type == LOOT_CORPSE)
				lTemplate = LootTemplates_Item.GetLootFor(proto->ItemId);
			else if (type == LOOT_DISENCHANTING && proto->DisenchantID)
				lTemplate = LootTemplates_Disenchant.GetLootFor(proto->DisenchantID);
#ifdef MANGOSBOT_TWO
			if (type == LOOT_MILLING)
				lTemplate = LootTemplates_Milling.GetLootFor(proto->ItemId);
			if (type == LOOT_PROSPECTING)
				lTemplate = LootTemplates_Prospecting.GetLootFor(proto->ItemId);
#endif
		}
	}

	return lTemplate;
}

DropMap* ItemDropMapValue::Calculate()
{
	DropMap* dropMap = new DropMap;

	for (auto const& [itemId, nativeTemplate] : sObjectMgr.GetItemPrototypeMap())
	{
		ItemPrototype const* proto = sItemStorage.LookupEntry<ItemPrototype>(itemId);

		if (!proto)
			continue;

		if (!(proto->Flags & ITEM_FLAG_HAS_LOOT))
			continue;

		LootTemplate const* lTemplateA = DropMapValue::GetLootTemplate(ObjectGuid(HIGHGUID_ITEM, itemId, uint32(1)), LOOT_CORPSE);

		if (lTemplateA)
		{
			for (LootStoreItem const& lItem : lTemplateA->GetEntries())
				dropMap->insert(std::make_pair(lItem.itemid, itemId));

			lTemplateA->VisitGroups([&](LootEntryView explicitEntries, LootEntryView equalEntries)
			{
				for (LootStoreItem const& lItem : explicitEntries)
					dropMap->insert(std::make_pair(lItem.itemid, itemId));

				for (LootStoreItem const& lItem : equalEntries)
					dropMap->insert(std::make_pair(lItem.itemid, itemId));
			});
		}
	}

	return dropMap;
}

DropMap* DropMapValue::Calculate()
{
	DropMap* dropMap = new DropMap;

	int32 sEntry;

	for (auto const& [entry, nativeTemplate] : sObjectMgr.GetCreatureInfoMap())
	{
		sEntry = entry;

		LootTemplate const* lTemplateA = GetLootTemplate(ObjectGuid(HIGHGUID_UNIT, entry, uint32(1)), LOOT_CORPSE);

		if (lTemplateA)
		{
			for (LootStoreItem const& lItem : lTemplateA->GetEntries())
				dropMap->insert(std::make_pair(lItem.itemid, sEntry));

			lTemplateA->VisitGroups([&](LootEntryView explicitEntries, LootEntryView equalEntries)
			{
				for (LootStoreItem const& lItem : explicitEntries)
					dropMap->insert(std::make_pair(lItem.itemid, sEntry));

				for (LootStoreItem const& lItem : equalEntries)
					dropMap->insert(std::make_pair(lItem.itemid, sEntry));
			});
		}
	}

	for (auto const& [entry, nativeTemplate] : sObjectMgr.GetGameObjectInfoMap())
	{
		sEntry = entry;

		LootTemplate const* lTemplateA = GetLootTemplate(ObjectGuid(HIGHGUID_GAMEOBJECT, entry, uint32(1)), LOOT_CORPSE);

		if (lTemplateA)
		{
			for (LootStoreItem const& lItem : lTemplateA->GetEntries())
				dropMap->insert(std::make_pair(lItem.itemid, -sEntry));

			lTemplateA->VisitGroups([&](LootEntryView explicitEntries, LootEntryView equalEntries)
			{
				for (LootStoreItem const& lItem : explicitEntries)
					dropMap->insert(std::make_pair(lItem.itemid, -sEntry));

				for (LootStoreItem const& lItem : equalEntries)
					dropMap->insert(std::make_pair(lItem.itemid, -sEntry));
			});
		}
	}

	DropMap* itemDropMap = GAI_VALUE(DropMap*, "item drop map");
	if (!itemDropMap)
		return dropMap;

	//Add items that drop from items.
	// Stage the new pairs first: inserting into dropMap while iterating a range from the same
	// unordered_multimap can trigger a rehash, which invalidates the range iterators (itr /
	// range.second) and crashes on the next ++itr. Build the additions, then apply them once.
	std::vector<std::pair<uint32, int32>> itemSourcedDrops;
	for (auto& [lootItemId, sourceItemId] : *itemDropMap)
	{
		auto range = dropMap->equal_range(sourceItemId);
		for (auto itr = range.first; itr != range.second; ++itr)
			itemSourcedDrops.emplace_back(lootItemId, itr->second);
	}

	for (auto& drop : itemSourcedDrops)
		dropMap->insert(drop);

	return dropMap;
}

//What items does this entry have in its loot list?
std::list<int32> ItemDropListValue::Calculate()
{
	uint32 itemId = stoi(getQualifier());

	DropMap* dropMap = GAI_VALUE(DropMap*, "drop map");
	if (!dropMap)
		return {};

	std::list<int32> entries;

	auto range = dropMap->equal_range(itemId);

	for (auto itr = range.first; itr != range.second; ++itr)
		entries.push_back(itr->second);

	return entries;
}

//What items does this entry have in its loot list?
std::list<uint32> EntryLootListValue::Calculate()
{
	int32 entry = stoi(getQualifier());

	std::list<uint32> items;

	DropMap* dropMap = GAI_VALUE(DropMap*, "drop map");
	if (!dropMap)
		return {};
	for (auto it = dropMap->begin(); it != dropMap->end(); ++it)
	{
		if (it->second == entry)
		{
			items.push_back(it->first);
		}
	}

	return items;
}

//What is the item's loot chance?
float LootChanceValue::Calculate()
{
	int32 entry = getMultiQualifierInt(getQualifier(), 0, " ");
	uint32 itemId = getMultiQualifierInt(getQualifier(), 1, " ");

	LootTemplate const* lTemplateA;

	if (entry > 0)
		lTemplateA = DropMapValue::GetLootTemplate(ObjectGuid(HIGHGUID_UNIT, entry, uint32(1)), LOOT_CORPSE);
	else
		lTemplateA = DropMapValue::GetLootTemplate(ObjectGuid(HIGHGUID_GAMEOBJECT, -entry, uint32(1)), LOOT_CORPSE);

	if (lTemplateA)
	{
		for (auto& item : lTemplateA->GetEntries())
			if (item.itemid == itemId)
				return item.chance;

		float chance = 0.0f;
		bool found = false;
		lTemplateA->VisitGroups([&](LootEntryView explicitEntries, LootEntryView equalEntries)
		{
			if (found) return;
			for (LootStoreItem const& item : explicitEntries)
				if (item.itemid == itemId)
				{ chance = item.chance; found = true; return; }

			float equalChance = equalEntries.empty() ? 0.0f : 100.0f / float(equalEntries.size());

			for (LootStoreItem const& item : equalEntries)
				if (item.itemid == itemId)
				{ chance = item.chance ? item.chance : equalChance; found = true; return; }
		});
		return chance;
	}

	return 0.0f;
}

itemUsageMap EntryLootUsageValue::Calculate()
{
	itemUsageMap items;

	for (auto itemId : GAI_VALUE2(std::list<uint32>, "entry loot list", getQualifier()))
	{
		items[AI_VALUE2(ItemUsage, "item usage", itemId)].push_back(itemId);
	}

	return items;
}

bool HasUpgradeValue::Calculate()
{
	for (auto itemId : GAI_VALUE2(std::list<uint32>, "entry loot list", getQualifier()))
	{
		ForceItemUsage forceUsage = AI_VALUE2_EXISTS(ForceItemUsage, "force item usage", itemId, ForceItemUsage::FORCE_USAGE_NONE);

		if (forceUsage == ForceItemUsage::FORCE_USAGE_NEED)
			return true;

		ItemQualifier qualifier(itemId);

		ItemUsage equip = ItemUsageValue::QueryItemUsageForEquip(qualifier, bot);
		if (equip == ItemUsage::ITEM_USAGE_EQUIP)
			return true;
	}
	return false;
}

//How many (stack) items can be looted while still having free space.
uint32 StackSpaceForItem::Calculate()
{
	uint32 maxValue = 999;

	uint32 itemId = stoi(getQualifier());

	ItemPrototype const* proto = sItemStorage.LookupEntry<ItemPrototype>(itemId);

	if (!proto) 
		return maxValue;

	if (proto->MaxCount > 0)
		return proto->MaxCount - AI_VALUE2(uint32, "item count", proto->Name1);

	if (ai->HasActivePlayerMaster())
		return maxValue;
	
	if (AI_VALUE(uint8, "bag space") <= 80)
		return maxValue;

	uint32 maxStack = proto->GetMaxStackSize();
	if (maxStack == 1)
		return 0;

	std::list<Item*> found = AI_VALUE2(std::list < Item*>, "inventory items", chat->formatItem(proto));

	maxValue = 0;

	for (auto stack : found)
		if (maxStack - stack->GetCount() > maxValue)
			maxValue = maxStack - stack->GetCount();

	return maxValue;
}

bool ShouldLootObject::Calculate()
{
	GuidPosition guid(stoull(getQualifier()), WorldPosition(bot));

	if (!guid)
		return false;

	WorldObject* object = guid.GetWorldObject(bot->GetInstanceId());

	if (!object)
		return false;

	// Penqle has m_loot only on Creature/GameObject; check via cast.
	Loot* objLoot = nullptr;
	if (object->IsCreature()) objLoot = ((Creature*)object)->m_loot;
	else if (object->IsGameObject()) objLoot = ((GameObject*)object)->m_loot;
	if (!objLoot)
    {
		if (!object->IsGameObject())
			return true;

		GameObject* go = static_cast<GameObject*>(object);

		if (go->GetGoType() != GAMEOBJECT_TYPE_GOOBER)
			return true;

		uint32 spellId = go->GetSpellId();

		if (!spellId)
            return true;

		SpellEntry const* lootSpell = GetSpellStore()->LookupEntry<SpellEntry>(spellId);

		if (!lootSpell || lootSpell->Effect[0] != SPELL_EFFECT_CREATE_ITEM)
            return true;

		uint32 itemId = lootSpell->EffectItemType[0];

		if (!AI_VALUE2(uint32, "stack space for item", itemId))
            return false;

        ItemQualifier ltemQualifier(itemId);

        if (!StoreLootAction::IsLootAllowed(ltemQualifier, ai))
            return false;

		return true;				
    }

	// Dispatch via cast to access m_loot (lives on Creature/GameObject only).
	Loot* objLoot2 = nullptr;
	if (object->IsCreature()) objLoot2 = ((Creature*)object)->m_loot;
	else if (object->IsGameObject()) objLoot2 = ((GameObject*)object)->m_loot;
	if (objLoot2 && objLoot2->GetGoldAmount() > 0)
		return true;

	// LootAccess wraps a Loot* now.
	if (!objLoot2)
		return false;

	LootAccess lootAccess(objLoot2);

	if (lootAccess.lootMethod() != NOT_GROUP_TYPE_LOOT && !lootAccess.isChecked()) //Open loot once to start rolls.
		return true;

	for (auto& lItem : lootAccess.GetLootContentFor(bot))
	{
		if (!lItem->itemId)
			continue;

		uint32 canLootAmount = AI_VALUE2(uint32, "stack space for item", lItem->itemId);

		if (canLootAmount < lItem->count)
			continue;

		ItemQualifier ltemQualifier(lItem);

		if (lootAccess.lootType() != LOOT_SKINNING && !StoreLootAction::IsLootAllowed(ltemQualifier, ai))
			continue;

		return true;
	}

	return false;
}

void ActiveRolls::CleanUp(Player* bot, LootRollMap& rollMap, ObjectGuid guid, uint32 slot)
{
	for (auto roll = rollMap.begin(); roll != rollMap.end();)
	{
		if (guid && roll->first != guid)
		{
			++roll;
			continue;
		}

		if (slot && roll->second != slot)
		{
			++roll;
			continue;
		}

		// Ask the group, not the loot object: this core keeps rolls in
		// Group::RollId and Loot::GetRollForSlot is a stub returning nullptr,
		// which used to wipe every entry the moment it was added.
		Group* group = bot->GetGroup();
		if (!group || !group->GetActiveRoll(roll->first, roll->second))
		{
			roll = rollMap.erase(roll);
			continue;
		}

		if(guid)
		{
			roll = rollMap.erase(roll);
			continue;
		}

		++roll;
	}
}

std::string ActiveRolls::Format()
{
	std::ostringstream out;

	for (auto& roll : value)
	{
		WorldObject* wo = ai->GetWorldObject(roll.first);

		if (wo)
			out << wo->GetName();
		else
			out << roll.first;

		std::string itemLink;

		Loot* loot = sLootMgr.GetLoot(bot, roll.first);
		if (loot)
		{
			LootItem* item = loot->GetLootItemInSlot(roll.second);

			if (item)
			{
				const ItemPrototype* proto = sItemStorage.LookupEntry<ItemPrototype>(item->itemId);

				if (proto)
				{
					itemLink = ChatHelper::formatItem(proto);
				}
			}
		}

		if (itemLink.empty())
			out << roll.second;
		else
			out << itemLink;

		out << ",";
	}

	return out.str();
}
