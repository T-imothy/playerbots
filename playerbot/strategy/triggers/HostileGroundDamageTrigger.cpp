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
            if (area->GetType() != DYNAMIC_OBJECT_AREA_SPELL || !std::isfinite(area->GetRadius()) || area->GetRadius() <= 0 ||
                area->GetRadius() > 25 || area->GetDuration() <= 0 || !area->IsEnemy(bot)) return false;
            const SpellEntry* spell = sServerFacade.LookupSpellInfo(area->GetSpellId());
            if (!spell || area->GetEffIndex() >= MAX_EFFECT_INDEX) return false;
            const auto aura = spell->EffectApplyAuraName[area->GetEffIndex()];
            bool triggeredDamage = false;
            if (aura == SPELL_AURA_PERIODIC_TRIGGER_SPELL &&
                spell->Effect[area->GetEffIndex()] == SPELL_EFFECT_PERSISTENT_AREA_AURA)
            {
                // The aura's affected unit casts self-targeted payloads. Inspect
                // one hop only: Felfire/Doomfire damage is here, while summons,
                // healing and scripted dummy effects (e.g. Flame Wreath) are not.
                const SpellEntry* payload = sServerFacade.LookupSpellInfo(spell->EffectTriggerSpell[area->GetEffIndex()]);
                if (payload && payload->EffectImplicitTargetA[EFFECT_INDEX_0] == TARGET_UNIT_CASTER)
                    for (uint32 i = 0; i < MAX_EFFECT_INDEX; ++i)
                        if (payload->Effect[i] == SPELL_EFFECT_SCHOOL_DAMAGE &&
                            payload->EffectImplicitTargetA[i] == TARGET_UNIT_CASTER && !payload->EffectImplicitTargetB[i])
                        {
                            triggeredDamage = true;
                            break;
                        }
                // Keep the parent spell for native area-target eligibility.
            }
            bool delayedDamage = false;
#ifndef MANGOSBOT_ZERO
            // Native Magtheridon Debris is a warning dummy area. Its script
            // casts 30631 at this area when it ends; waiting for periodic damage
            // misses the only opportunity to leave. Do not classify arbitrary
            // dummy effects as hazards or fabricate a post-despawn lifetime.
            if (bot->GetMapId() == 544 && area->GetSpellId() == 30632 &&
                area->GetEffIndex() == EFFECT_INDEX_0 && aura == SPELL_AURA_DUMMY)
            {
                Unit* owner = area->GetCaster();
                if (!owner || !owner->IsInWorld() || !bot->IsInMap(owner) || owner->HasCharmer() ||
                    owner->GetEntry() != 17257) return false;
                spell = sServerFacade.LookupSpellInfo(30631);
                if (!spell || spell->Effect[EFFECT_INDEX_0] != SPELL_EFFECT_SCHOOL_DAMAGE) return false;
                delayedDamage = true;
            }
#endif
            return (triggeredDamage || delayedDamage || aura == SPELL_AURA_PERIODIC_DAMAGE || aura == SPELL_AURA_PERIODIC_DAMAGE_PERCENT ||
                aura == SPELL_AURA_PERIODIC_LEECH) && area->CanAttackSpell(bot, spell, true);
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
