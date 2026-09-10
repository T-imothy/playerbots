#pragma once

namespace ai
{
    // Match the core's item restrictions before pricing, routing, or submitting
    // an auction. CanBeTraded covers binding, loot, equipped/nonempty bags, etc.
    // Keep the template usable by the native fixture and the real Item API.
    template<class ItemType>
    bool LivingWowAuctionItemEligible(const ItemType* item)
    {
        return item && item->GetProto() && item->CanBeTraded() &&
            !(item->GetProto()->Flags & ITEM_FLAG_CONJURED) &&
            !item->GetUInt32Value(ITEM_FIELD_DURATION);
    }
}
