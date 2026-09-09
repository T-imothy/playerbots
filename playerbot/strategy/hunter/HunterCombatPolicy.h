#pragma once

#include "playerbot/strategy/MeleeCombatPolicy.h"
#include "Spells/Spell.h"
#include "Spells/SpellMgr.h"
#include <algorithm>
#include <cmath>

namespace ai
{
    inline uint32 HunterSpell(PlayerbotAI* ai, const std::string& name)
    {
        return ai->GetAiObjectContext()->GetValue<uint32>("spell id", name)->Get();
    }

    inline bool HunterAmmoReady(PlayerbotAI* ai)
    {
        Player* bot = ai->GetBot();
        Item* weapon = bot->GetWeaponForAttack(RANGED_ATTACK);
        if (!weapon) return false;
        uint32 kind = weapon->GetProto()->SubClass;
        if (kind != ITEM_SUBCLASS_WEAPON_BOW && kind != ITEM_SUBCLASS_WEAPON_CROSSBOW && kind != ITEM_SUBCLASS_WEAPON_GUN)
            return false;
        if (ai->HasCheat(BotCheatMask::item)) return true;
#ifndef MANGOSBOT_ZERO
        if (bot->HasAura(46699)) return true;
#endif
        uint32 id = bot->GetUInt32Value(PLAYER_AMMO_ID);
        const ItemPrototype* ammo = sObjectMgr.GetItemPrototype(id);
        return ammo && ammo->Class == ITEM_CLASS_PROJECTILE &&
            ammo->SubClass == (kind == ITEM_SUBCLASS_WEAPON_GUN ? ITEM_SUBCLASS_BULLET : ITEM_SUBCLASS_ARROW) &&
            bot->HasItemCount(id, 1) && bot->CanUseAmmo(id) == EQUIP_ERR_OK;
    }

    inline bool HunterAmmoReserve(PlayerbotAI* ai)
    {
        if (!ai->GetBot()->GetWeaponForAttack(RANGED_ATTACK)) return false;
        for (Item* item : ai->GetAiObjectContext()->GetValue<std::list<Item*>>("inventory items", "ammo")->Get())
            if (item && item->GetCount() && ai->GetBot()->CanUseAmmo(item->GetEntry()) == EQUIP_ERR_OK) return true;
        return false;
    }

    // Query the native target-aware range calculation without starting a cast.
    class HunterRangeProbe : public Spell
    {
    public:
        HunterRangeProbe(Player* bot, const SpellEntry* spell, Unit* target) : Spell(bot, spell, false)
        {
            m_targets.setUnitTarget(target);
        }
        std::pair<float, float> Bounds() { return GetMinMaxRange(true); }
    };

    inline std::pair<float, float> HunterShotRange(PlayerbotAI* ai, Unit* target, const std::string& name = "auto shot")
    {
        const SpellEntry* spell = sServerFacade.LookupSpellInfo(HunterSpell(ai, name));
        if (!spell || !target) return {0.0f, 0.0f};
        HunterRangeProbe probe(ai->GetBot(), spell, target);
        return probe.Bounds();
    }

    inline bool HunterInShotRange(PlayerbotAI* ai, Unit* target, float margin = 0.0f)
    {
        if (!MeleeCombatTarget(ai, target) || !HunterAmmoReady(ai)) return false;
        const auto bounds = HunterShotRange(ai, target);
        const float dist2 = ai->GetBot()->GetDistance(target, true, DIST_CALC_NONE);
        return bounds.second > 0.0f && dist2 >= (bounds.first + margin) * (bounds.first + margin) &&
            dist2 <= bounds.second * bounds.second && ai->GetBot()->IsWithinLOSInMap(target);
    }

    inline bool HunterManualAspect(PlayerbotAI* ai)
    {
        for (const char* name : {"aspect hawk", "aspect monkey", "aspect cheetah", "aspect pack", "aspect beast", "aspect wild", "aspect viper", "aspect dragonhawk"})
            if (ai->HasStrategy(name, BotState::BOT_STATE_COMBAT) || ai->HasStrategy(name, BotState::BOT_STATE_NON_COMBAT)) return true;
        return false;
    }

    inline bool HunterWantsViper(PlayerbotAI* ai)
    {
#ifdef MANGOSBOT_ZERO
        return false;
#else
        Player* bot = ai->GetBot();
        if (HunterManualAspect(ai) || !HunterSpell(ai, "aspect of the viper") || !bot->GetMaxPower(POWER_MANA)) return false;
        const float mana = 100.0f * bot->GetPower(POWER_MANA) / bot->GetMaxPower(POWER_MANA);
        // Wrath regenerates through attacks at a damage cost; TBC uses its
        // native passive regeneration. Hysteresis avoids aspect oscillation.
#ifdef MANGOSBOT_TWO
        const float enter = 20.0f, leave = 60.0f;
#else
        const float enter = 30.0f, leave = 70.0f;
#endif
        return mana < (ai->HasAura("aspect of the viper", bot) ? leave : enter);
#endif
    }

    inline bool HunterHasOwnSting(PlayerbotAI* ai, Unit* target)
    {
        return target && (ai->HasMyAura("serpent sting", target) || ai->HasMyAura("viper sting", target) || ai->HasMyAura("scorpid sting", target));
    }

    inline bool HunterWantsViperSting(PlayerbotAI* ai, Unit* target)
    {
        if (!target || !target->GetMaxPower(POWER_MANA)) return false;
        if (ai->HasStrategy("sting serpent", BotState::BOT_STATE_COMBAT) || ai->HasStrategy("sting scorpid", BotState::BOT_STATE_COMBAT)) return false;
        return (ai->HasStrategy("sting viper", BotState::BOT_STATE_COMBAT) || target->IsPlayer()) &&
            100.0f * target->GetPower(POWER_MANA) / target->GetMaxPower(POWER_MANA) >= 10.0f;
    }

    // Inspect the actual planned area, not just a count of engaged targets.
    // Cached nearby lists bound the cost and retain unengaged/marked targets.
    inline bool HunterAreaSafe(PlayerbotAI* ai, float x, float y, float z, float radius)
    {
        auto context = ai->GetAiObjectContext();
        const auto attackers = context->GetValue<std::list<ObjectGuid>>("possible attack targets")->Get();
        MeleeCcCheck cc(ai);
        for (ObjectGuid guid : context->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
        {
            Unit* unit = ai->GetUnit(guid);
            if (!unit || !unit->IsInWorld() || !unit->IsAlive() || !ai->GetBot()->IsInMap(unit)) continue;
            float dx = x - unit->GetPositionX(), dy = y - unit->GetPositionY(), dz = z - unit->GetPositionZ();
            const float reach = radius + unit->GetCombatReach();
            if (dx * dx + dy * dy + dz * dz > reach * reach) continue;
            if (cc.Protected(unit) || std::find(attackers.begin(), attackers.end(), guid) == attackers.end()) return false;
        }
        return true;
    }

    inline bool HunterAreaSafe(PlayerbotAI* ai, Unit* centre, float radius)
    {
        return centre && HunterAreaSafe(ai, centre->GetPositionX(), centre->GetPositionY(), centre->GetPositionZ(), radius);
    }
}
