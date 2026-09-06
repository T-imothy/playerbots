#include "playerbot/playerbot.h"
#include "playerbot/ServerFacade.h"
#include "DungeonTriggers.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/HazardsValue.h"
#include "Entities/DynamicObject.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;

namespace
{
    struct HostileDamageAreaCheck
    {
        Player* bot;
        WorldObject const& GetFocusObject() const { return *bot; }
        bool operator()(WorldObject* object) const
        {
            if (!object || object->GetTypeId() != TYPEID_DYNAMICOBJECT || !object->IsInWorld() ||
                object->GetMap() != bot->GetMap()) return false;
            DynamicObject* area = static_cast<DynamicObject*>(object);
            // Do not mistake farsight, friendly ground heals, or raid-wide damage
            // for a local avoidable hazard. Native attack rules decide hostility.
            if (area->GetType() != DYNAMIC_OBJECT_AREA_SPELL || area->GetRadius() <= 0 ||
                area->GetRadius() > 25 || area->GetDuration() <= 0 || !area->IsEnemy(bot)) return false;
            const SpellEntry* spell = sServerFacade.LookupSpellInfo(area->GetSpellId());
            if (!spell || area->GetEffIndex() >= MAX_EFFECT_INDEX || !area->CanAttackSpell(bot, spell, true)) return false;
            const auto aura = spell->EffectApplyAuraName[area->GetEffIndex()];
            return aura == SPELL_AURA_PERIODIC_DAMAGE || aura == SPELL_AURA_PERIODIC_DAMAGE_PERCENT || aura == SPELL_AURA_PERIODIC_LEECH;
        }
    };
}

bool HostileGroundDamageTrigger::IsActive()
{
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || !bot->IsInCombat() ||
        !bot->GetMap()->IsDungeon()) return false;
    WorldObjectList areas;
    HostileDamageAreaCheck check{bot};
    MaNGOS::WorldObjectListSearcher<HostileDamageAreaCheck> searcher(areas, check);
    Cell::VisitAllObjects(bot, searcher, 30.0f);
    bool inside = false;
    for (WorldObject* object : areas)
    {
        DynamicObject* area = static_cast<DynamicObject*>(object);
        const float radius = area->GetRadius() + 1.0f;
        SET_AI_VALUE(Hazard, "add hazard", Hazard(area->GetObjectGuid(), (area->GetDuration() + 999) / 1000, radius));
        if (bot->GetDistance(area->GetPositionX(), area->GetPositionY(), area->GetPositionZ()) <= radius) inside = true;
    }
    return inside;
}
