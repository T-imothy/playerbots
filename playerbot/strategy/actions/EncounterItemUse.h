#pragma once

namespace ai
{
    bool IsNativeEncounterItem(uint32 itemId);
    // Returns whether a native use attempt was dispatched, not whether its
    // effects completed. Inventory and spell state remain owned by the core.
    bool UseNativeEncounterItem(Player* bot, Item* item, Unit* unit, GameObject* object);
}
