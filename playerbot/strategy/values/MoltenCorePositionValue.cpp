#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/ServerFacade.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "Spells/SpellMgr.h"
#include "HazardsValue.h"
#include "Entities/DynamicObject.h"
#include "Entities/GameObject.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;

namespace
{
    bool Casting(Unit* unit, uint32 id)
    {
        for (CurrentSpellTypes type : {CURRENT_GENERIC_SPELL, CURRENT_CHANNELED_SPELL})
        {
            const Spell* spell = unit->GetCurrentSpell(type);
            if (spell && spell->m_spellInfo && spell->m_spellInfo->Id == id && spell->getState() != SPELL_STATE_FINISHED) return true;
        }
        return false;
    }
}

// Read live native objects, not a remembered target position or guessed timer.
// This is also appended to general movement hazards so chasing cannot re-enter fire.
void ai::AppendMoltenCoreGroundHazards(PlayerbotAI* ai, std::list<HazardPosition>& hazards)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->GetMapId() != 409 ||
        bot->IsBeingTeleported() || bot->HasCharmer()) return;
    struct FireCheck
    {
        Player* bot;
        WorldObject const& GetFocusObject() const { return *bot; }
        bool operator()(WorldObject* object) const
        {
            if (!object || !object->IsInWorld() || !bot->IsInMap(object) ||
                std::fabs(object->GetPositionZ() - bot->GetPositionZ()) > 8) return false;
            if (object->GetTypeId() == TYPEID_DYNAMICOBJECT)
            {
                DynamicObject* fire = static_cast<DynamicObject*>(object);
                Unit* caster = fire->GetCaster();
                return fire->GetSpellId() == 19717 && fire->GetType() == DYNAMIC_OBJECT_AREA_SPELL &&
                    fire->GetDuration() > 0 && std::isfinite(fire->GetRadius()) &&
                    fire->GetRadius() > 0 && fire->GetRadius() <= 25 && caster &&
                    caster->GetEntry() == 12259 && !caster->HasCharmer() && bot->IsInMap(caster) &&
                    fire->IsEnemy(bot) && fire->CanAttackSpell(bot, sServerFacade.LookupSpellInfo(19717), true);
            }
            if (object->GetTypeId() == TYPEID_GAMEOBJECT)
            {
                GameObject* bomb = static_cast<GameObject*>(object);
                return bomb->GetEntry() == 177704 && bomb->IsSpawned() &&
                    bomb->GetGoType() == GAMEOBJECT_TYPE_TRAP && bomb->GetGOInfo()->trap.spellId == 19428;
            }
            return false;
        }
    } check{bot};
    WorldObjectList objects;
    MaNGOS::WorldObjectListSearcher<FireCheck> searcher(objects, check);
    Cell::VisitAllObjects(bot, searcher, 60.0f);
    for (WorldObject* object : objects)
    {
        float radius = 0;
        if (object->GetTypeId() == TYPEID_DYNAMICOBJECT)
            radius = static_cast<DynamicObject*>(object)->GetRadius();
        else
        {
            GameObject* bomb = static_cast<GameObject*>(object);
            radius = std::max(float(bomb->GetGOInfo()->trap.diameter) * 0.5f, NativeEncounterSpellRadius(19428));
        }
        if (std::isfinite(radius) && radius > 0 && radius <= 25)
            hazards.emplace_back(WorldPosition(object), radius + 1.0f);
    }
}

bool ai::MoltenCoreThreats(PlayerbotAI* ai, EncounterPosition& plan,
    std::vector<encounter::Circle>& threats)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 409) return false;
    Unit* boss = nullptr;
    for (const auto& guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
    {
        Unit* unit = ai->GetUnit(guid);
        if (unit && unit->IsInWorld() && bot->IsInMap(unit) && unit->IsAlive() && unit->IsInCombat() &&
            (unit->GetEntry() == 12056 || unit->GetEntry() == 12264 || unit->GetEntry() == 12057 ||
             unit->GetEntry() == 11988 || unit->GetEntry() == 11502))
        {
            if (boss && boss != unit) { boss = nullptr; break; } // Fire remains real on ambiguous pulls.
            boss = unit;
        }
    }
    plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    if (boss) plan.boss = boss->GetObjectGuid();
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    std::list<HazardPosition> ground;
    AppendMoltenCoreGroundHazards(ai, ground);
    for (const auto& hazard : ground)
        threats.push_back({{hazard.first.getX(), hazard.first.getY(), hazard.first.getZ()}, hazard.second + 1.0f});
    const auto add = [&](Unit* center, float radius) {
        if (radius > 0 && radius <= 45 && std::fabs(center->GetPositionZ() - here.z) < 8)
            threats.push_back({{center->GetPositionX(), center->GetPositionY(), center->GetPositionZ()}, radius + 2});
    };
    if (boss && boss->GetEntry() == 12056)
    {
        // Inferno's damage is a native script-triggered spell (19698), not the
        // radius-zero channel. Living Bomb's explosion comes from its DBC trigger.
        if (boss->HasAura(19695) || Casting(boss, 19695)) add(boss, NativeEncounterSpellRadius(19698));
        if (boss->HasAura(20478) || Casting(boss, 20478)) add(boss, NativeEncounterSpellRadius(20478));
    }
    else if (boss && boss->GetEntry() == 12264 && (ai->IsRanged(bot) || ai->IsHeal(bot)) && boss->GetVictim() != bot)
        add(boss, NativeEncounterSpellRadius(19712)); // Ranged/healers stay outside Shazzrah's native explosion.

    if (boss && boss->GetEntry() == 11988 && !ai->IsTank(bot) && !ai->IsRanged(bot))
    {
        Aura* splash = ai->GetAura(13880, bot);
        // Melee DPS shed accumulated Magma Splash while tanks retain control.
        // Once outside melee, keep holding until the native aura expires.
        if (splash && (splash->GetStackAmount() >= 5 || bot->GetDistance(boss) > 8.0f))
            add(boss, boss->GetCombatReach() + bot->GetCombatReach() + 5.0f);
    }
    if (boss && boss->GetEntry() == 11502 && !boss->HasAura(21107) && !boss->HasAura(21859) && boss->GetVictim() != bot &&
        (ai->IsRanged(bot) || ai->IsHeal(bot) || Casting(boss, 20566)))
        add(boss, NativeEncounterSpellRadius(20566)); // Preserve the tank in melee; avoid Wrath knockback.
    if (boss && boss->GetEntry() == 11502 && !boss->HasAura(21107) && !boss->HasAura(21859) && boss->GetVictim() != bot && bot->GetGroup() && (ai->IsRanged(bot) || ai->IsHeal(bot)))
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (!member || member == bot || !member->IsInWorld() || !member->IsAlive() ||
                !bot->IsInMap(member) || member->IsBeingTeleported() || member->HasCharmer() ||
                member->GetGroup() != bot->GetGroup()) continue;
            // Deterministic yielding avoids two bots perpetually mirroring one
            // another. Human players have right of way regardless of GUID.
            if (!member->GetPlayerbotAI() || member->GetPlayerbotAI()->IsRealPlayer() ||
                member->GetObjectGuid() < bot->GetObjectGuid()) add(member, NativeEncounterSpellRadius(21154));
        }

    if (boss && boss->GetEntry() == 12057)
        for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
        {
            Unit* firesworn = ai->GetUnit(guid);
            if (!firesworn || firesworn->GetEntry() != 12099 || !firesworn->IsInWorld() ||
                !firesworn->IsAlive() || !firesworn->IsInCombat() || !bot->IsInMap(firesworn) ||
                firesworn->HasCharmer() ||
                firesworn->HasAura(710) || firesworn->HasAura(18647)) continue;
            if (Casting(firesworn, 20483)) add(firesworn, NativeEncounterSpellRadius(20483));
            else if (Casting(firesworn, 19497) || firesworn->GetHealthPercent() <= 10.0f)
                add(firesworn, NativeEncounterSpellRadius(19497));
        }

    // Living Bomb can outlive Geddon and combat itself. Its native aura, not
    // boss life or a guessed encounter timer, controls separation and cleanup.
    const bool carryingBomb = bot->HasAura(20475);
    const float bombRadius = NativeEncounterSpellRadius(20475);
    if (carryingBomb && bot->GetGroup()) { plan.spell = 20475; plan.source = bot->GetObjectGuid(); }
    if (bot->GetGroup())
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (!member || member == bot || !member->IsInWorld() || !bot->IsInMap(member) || !member->IsAlive() ||
                member->IsBeingTeleported() || member->HasCharmer() || member->GetGroup() != bot->GetGroup()) continue;
            const bool memberBomb = member->HasAura(20475);
            if (carryingBomb || memberBomb) add(member, bombRadius);
            if (!carryingBomb && memberBomb && (plan.source.IsEmpty() || member->GetObjectGuid() < plan.source))
            { plan.spell = 20475; plan.source = member->GetObjectGuid(); }
        }
    if (threats.empty()) return false;
    // Do not freeze an unrelated bot on the other side of the room. Within the
    // danger/approach band, hold the safe position so ordinary chasing cannot undo it.
    bool relevant = carryingBomb;
    for (const auto& circle : threats)
        relevant = relevant || encounter::Distance2d(here, circle.center) < circle.radius + 8;
    return relevant;
}

EncounterPosition MoltenCorePositionValue::Calculate()
{
    EncounterPosition plan;
    std::vector<encounter::Circle> threats;
    if (!MoltenCoreThreats(ai, plan, threats))
    {
        PlanMoltenCoreTrash(ai, plan);
        return plan;
    }
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    const auto candidates = encounter::EscapeCircles(here, threats);
    unsigned checked = 0;
    for (const auto& point : candidates)
    {
        if (++checked > 8) break; // Bound native path queries per cached decision.
        plan.active = true; plan.destination = point;
        if (ValidateEncounterDestination(ai, plan) && encounter::OutsideCircles(plan.destination, threats)) return plan;
    }
    plan.active = false;
    return plan;
}
