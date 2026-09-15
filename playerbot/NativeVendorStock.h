#pragma once
#include "ObjectMgr.h"

namespace ai
{
    // Native gossip exposes a merchant only when either offer list has items.
    // Keep quest/gossip purposes independent of an erroneously set vendor flag.
    inline bool HasNativeVendorStock(uint32 entry)
    {
        CreatureInfo const* creature = sObjectMgr.GetCreatureTemplate(entry);
        if (!creature) return false;
        VendorItemData const* direct = sObjectMgr.GetNpcVendorItemList(entry);
        if (direct && !direct->m_items.empty()) return true;
        VendorItemData const* shared = creature->VendorTemplateId ?
            sObjectMgr.GetNpcVendorTemplateItemList(creature->VendorTemplateId) : nullptr;
        return shared && !shared->m_items.empty();
    }
}
