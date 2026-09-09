#pragma once

#include "playerbot/strategy/MeleeCombatPolicy.h"
#include "playerbot/ServerFacade.h"
#include "Spells/SpellMgr.h"
#include <algorithm>
#include <vector>

namespace ai
{
    inline uint32 CasterSpell(PlayerbotAI* ai, const std::string& name)
    {
        return ai->GetAiObjectContext()->GetValue<uint32>("spell id", name)->Get();
    }

    // Personal periodic effects may coexist with another caster's copy.
    // Shared debuffs, curses and earlier expansion debuff limits stay separate.
    inline bool CasterPersonalDot(const std::string& name)
    {
        for (const char* dot : {"corruption", "immolate", "unstable affliction", "siphon life",
            "shadow word: pain", "vampiric touch", "devouring plague", "moonfire", "insect swarm", "living bomb"})
            if (name == dot) return true;
        return false;
    }

    enum class CasterArea { None, Ground, Self, Target, Chain };
    inline CasterArea CasterSpellArea(const std::string& name)
    {
        for (const char* spell : {"blizzard", "flamestrike", "rain of fire", "hurricane", "shadowfury", "force of nature"})
            if (name == spell) return CasterArea::Ground;
        for (const char* spell : {"starfall", "arcane explosion", "frost nova", "cone of cold", "dragon's breath",
            "blast wave", "howl of terror", "hellfire", "immolation aura", "shadow cleave", "shadowflame", "typhoon", "thunderstorm"})
            if (name == spell) return CasterArea::Self;
        if (name == "living bomb" || name == "seed of corruption" || name == "mind sear") return CasterArea::Target;
        if (name == "chain lightning") return CasterArea::Chain;
        return CasterArea::None;
    }

    inline bool CasterAreaSafe(PlayerbotAI* ai, float x, float y, float z, float radius)
    {
        auto context = ai->GetAiObjectContext();
        const auto attackers = context->GetValue<std::list<ObjectGuid>>("possible attack targets")->Get();
        MeleeCcCheck cc(ai);
        for (ObjectGuid guid : context->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
        {
            Unit* unit = ai->GetUnit(guid);
            if (!unit || !unit->IsInWorld() || !unit->IsAlive() || !ai->GetBot()->IsInMap(unit)) continue;
            float dx = x - unit->GetPositionX(), dy = y - unit->GetPositionY(), dz = z - unit->GetPositionZ();
            float reach = radius + unit->GetCombatReach();
            if (dx * dx + dy * dy + dz * dz > reach * reach) continue;
            if (cc.Protected(unit) || std::find(attackers.begin(), attackers.end(), guid) == attackers.end()) return false;
        }
        return true;
    }

    inline bool CasterAreaSafe(PlayerbotAI* ai, Unit* centre, float radius)
    {
        return centre && CasterAreaSafe(ai, centre->GetPositionX(), centre->GetPositionY(), centre->GetPositionZ(), radius);
    }

    inline bool CasterSpellAreaSafe(PlayerbotAI* ai, const std::string& name, Unit* target)
    {
        CasterArea area = CasterSpellArea(name);
        if (area == CasterArea::None) return true;
        if (!target) return false;
        const SpellEntry* spell = sServerFacade.LookupSpellInfo(CasterSpell(ai, name));
        if (!spell) return false;
        float radius = 10.0f; // Conservative minimum also covers triggered damage effects.
        if (name == "starfall" || name == "typhoon") radius = 30.0f;
        if (name == "seed of corruption") radius = 15.0f;
        for (unsigned i = 0; i < MAX_EFFECT_INDEX; ++i)
            radius = std::max(radius, GetSpellRadius(sSpellRadiusStore.LookupEntry(spell->EffectRadiusIndex[i])));
        if (area == CasterArea::Chain)
        {
            // Check every reachable bounce origin, including enemies omitted by
            // the eligible-target list because of CC. Bound traversal by jump count.
            std::vector<Unit*> frontier{target};
            std::vector<ObjectGuid> visited{target->GetObjectGuid()};
            unsigned jumps = 1;
            for (unsigned i = 0; i < MAX_EFFECT_INDEX; ++i) jumps = std::max(jumps, spell->EffectChainTarget[i]);
            jumps = std::min(8u, jumps + 1); // Include a possible extra glyph target.
            auto nearby = ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get();
            for (unsigned depth = 0; depth < jumps && !frontier.empty(); ++depth)
            {
                std::vector<Unit*> next;
                for (Unit* origin : frontier)
                {
                    if (!CasterAreaSafe(ai, origin, 15.0f)) return false;
                    for (ObjectGuid guid : nearby)
                    {
                        if (std::find(visited.begin(), visited.end(), guid) != visited.end()) continue;
                        Unit* unit = ai->GetUnit(guid);
                        if (unit && unit->IsInWorld() && unit->IsAlive() && origin->IsInMap(unit) && origin->IsWithinDistInMap(unit, 15.0f))
                        { visited.push_back(guid); next.push_back(unit); }
                    }
                }
                frontier.swap(next);
                if (visited.size() > 64) return false; // Bound crowded-pack planning work.
            }
            return true;
        }
        if (area == CasterArea::Self) return CasterAreaSafe(ai, ai->GetBot(), radius);
        if (area == CasterArea::Ground)
        {
            // Match PlayerbotAI::CastSpell's actual destination selection.
            WorldLocation location = ai->GetAiObjectContext()->GetValue<WorldLocation>("aoe position")->Get();
            if (location.coord_x != 0) return CasterAreaSafe(ai, location.coord_x, location.coord_y, location.coord_z, radius);
        }
        return CasterAreaSafe(ai, target, radius);
    }

    inline bool CasterCarryingFlag(Player* bot)
    {
        return bot->HasAura(23333) || bot->HasAura(23335) || bot->HasAura(34976);
    }

    inline bool CasterDamageSpell(const SpellEntry* spell)
    {
        if (!spell) return false;
        for (unsigned i = 0; i < MAX_EFFECT_INDEX; ++i)
            if (spell->Effect[i] == SPELL_EFFECT_SCHOOL_DAMAGE || spell->Effect[i] == SPELL_EFFECT_HEALTH_LEECH ||
                spell->EffectApplyAuraName[i] == SPELL_AURA_PERIODIC_DAMAGE || spell->EffectApplyAuraName[i] == SPELL_AURA_PERIODIC_LEECH)
                return true;
        return false;
    }

    inline bool CasterControlAvailable(PlayerbotAI* ai, const std::string& name, Unit* target)
    {
        const SpellEntry* spell = sServerFacade.LookupSpellInfo(CasterSpell(ai, name));
        if (!spell || !target) return false;
        DiminishingGroup group = GetDiminishingReturnsGroupForSpell(spell, false);
        return group == DIMINISHING_NONE || target->GetDiminishing(group) < DIMINISHING_LEVEL_IMMUNE;
    }

    inline bool CasterUnderAttack(PlayerbotAI* ai)
    {
        for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("attackers")->Get())
            if (Unit* unit = ai->GetUnit(guid))
                if (unit->IsAlive() && unit->GetVictim() == ai->GetBot()) return true;
        return false;
    }

    inline bool CasterHealthCostSafe(PlayerbotAI* ai, const std::string& name)
    {
        Player* bot = ai->GetBot();
        if (name == "shadow word: death") return bot->GetHealthPercent() > 50.0f;
        if (name == "health funnel") return bot->GetHealthPercent() > 70.0f && !CasterUnderAttack(ai);
        if (name == "hellfire") return bot->GetHealthPercent() > 80.0f && !CasterUnderAttack(ai);
        return true;
    }
}
