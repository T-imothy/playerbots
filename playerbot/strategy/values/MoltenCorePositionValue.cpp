#include "playerbot/playerbot.h"
#include "playerbot/strategy/actions/MoltenCoreDungeonActions.h"
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
#include "Movement/MoveSpline.h"
#include "playerbot/strategy/actions/MovementPathSafety.h"

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
            // The trap's visual and trigger diameter are smaller than the
            // native five-yard damage footprint. Leave room for the actor's
            // body and for the next movement update, not merely its centre.
            hazards.emplace_back(WorldPosition(object), radius +
                (object->GetTypeId() == TYPEID_GAMEOBJECT ? 3.0f + bot->GetObjectBoundingRadius() : 1.0f));
    }
}

bool ai::StopMoltenCoreUnsafeTravel(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->GetMapId() != 409 || bot->IsBeingTeleported() ||
        bot->HasCharmer() || ai->IsRealPlayer() || bot->GetTransport() || bot->IsFreeFlying() ||
        !bot->movespline || !ai->CanMove()) return false;
    std::list<HazardPosition> fire;
    AppendMoltenCoreGroundHazards(ai, fire);
    if (fire.empty()) return false;
    const WorldPosition here(bot);
    for (const auto& hazard : fire)
        if (here.distance(hazard.first)<hazard.second)
        {
            if (!bot->movespline->Finalized())
            {
                const auto next=bot->movespline->CurrentDestination();
                const WorldPosition destination(bot->GetMapId(),next.x,next.y,next.z);
                if (!IsHazardSafeSegment(here,destination,fire)) ai->StopMoving();
            }
            ai->PrepareForUrgentHazard();
            ai->GetAiObjectContext()->GetValue<std::list<HazardPosition>>("hazards")->Reset();
            ai->GetAiObjectContext()->GetValue<EncounterPosition>("molten core position")->Reset();
            return true;
        }
    if (bot->movespline->Finalized()) return false;
    // Fire can spawn after a native chase/path was admitted. Validate the
    // current native spline segment again, rather than waiting to reach the trap.
    const auto next = bot->movespline->CurrentDestination();
    const WorldPosition destination(bot->GetMapId(), next.x, next.y, next.z);
    if (IsHazardSafeSegment(WorldPosition(bot), destination, fire)) return false;
    ai->StopMoving();
    ai->GetAiObjectContext()->GetValue<std::list<HazardPosition>>("hazards")->Reset();
    ai->GetAiObjectContext()->GetValue<EncounterPosition>("molten core position")->Reset();
    return true;
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
    plan.groundOnly=!ground.empty();
    for (const auto& hazard : ground)
        threats.push_back({{hazard.first.getX(), hazard.first.getY(), hazard.first.getZ()}, hazard.second + 1.0f});
    const auto add = [&](Unit* center, float radius) {
        if (radius > 0 && radius <= 45 && std::fabs(center->GetPositionZ() - here.z) < 8)
        {
            threats.push_back({{center->GetPositionX(), center->GetPositionY(), center->GetPositionZ()}, radius + 2});
            plan.groundOnly=false; // A bomb, pulse or boss burst retains its separate hold.
        }
    };
    if (boss && boss->GetEntry() == 12056)
    {
        // Inferno's damage is a native script-triggered spell (19698), not the
        // radius-zero channel. Living Bomb's explosion comes from its DBC trigger.
        // Holding tank keeps the encounter anchored; healers sustain it while
        // everyone else avoids native Inferno damage. Bombs still override this.
        if (!(ai->IsTank(bot) && boss->GetVictim() == bot) && (boss->HasAura(19695) || Casting(boss, 19695))) add(boss, NativeEncounterSpellRadius(19698));
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
                member->GetGroup() != bot->GetGroup() || ai->IsTank(member) ||
                (!ai->IsRanged(member) && !ai->IsHeal(member))) continue;
            // Separate triples using Intense Heat's actual explosion radius,
            // rather than Might's one-yard creature-summon radius.
            if (!RagnarosSameCluster(ai, member)) add(member, NativeEncounterSpellRadius(21155));
        }

    // Native death eruptions remain dangerous after Garr has died.
    for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
        {
            Unit* firesworn = ai->GetUnit(guid);
            if (!firesworn || firesworn->GetEntry() != 12099 || !firesworn->IsInWorld() ||
                !firesworn->IsAlive() || !firesworn->IsInCombat() || !bot->IsInMap(firesworn) ||
                firesworn->HasCharmer() ||
                firesworn->HasAura(710) || firesworn->HasAura(18647)) continue;
            if (Casting(firesworn, 20483)) add(firesworn, NativeEncounterSpellRadius(20483));
            // Normal Eruption is cast on native death. Its holding tank must
            // anchor the isolated add; retreating from a living threat circle
            // only drags that same circle farther across the room.
            else if ((Casting(firesworn, 19497) || firesworn->GetHealthPercent() <= 25.0f) &&
                !(firesworn->GetVictim()==bot && ai->IsTank(bot)))
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
    // Ragnaros knockback/spacing escape ends at real clearance. Keeping a
    // stationary escape in the approach band can strand a landed ranged bot
    // outside casting range instead of handing it back to its formation.
    // Live Wrath casts, bombs and every other encounter retain their hold.
    const float approach = boss && boss->GetEntry()==11502 && !Casting(boss,20566) &&
        !carryingBomb && !plan.spell && plan.source.IsEmpty() ? 0.0f : 8.0f;
    // Do not freeze an unrelated bot on the other side of the room.
    bool relevant = carryingBomb;
    for (const auto& circle : threats)
        relevant = relevant || encounter::Distance2d(here, circle.center) < circle.radius + approach;
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
    if (plan.groundOnly && !plan.spell && plan.source.IsEmpty())
    {
        // Nearby ground fire must not turn a safe actor's current spot into
        // an exclusive hold that prevents recovering its useful formation.
        // A complete safe route can also take an actor directly out of fire
        // to its useful station; otherwise retain the native escape search.
        EncounterPosition formation;
        if (PlanMoltenCoreTrash(ai,formation) && encounter::OutsideCircles(formation.destination,threats)) return formation;
    }
    if (plan.groundOnly && encounter::OutsideCircles(here,threats))
    {
        // Live ground hazards already guard every native movement route.
        // Do not strand melee outside attack range in an eight-yard approach
        // band after they have escaped the actual fire.
        plan.active=false;return plan;
    }
    if (bot->HasAura(20475) && std::hypot(here.x-690.709167f,here.y+766.988770f) < 100)
    {
        plan.active = true; plan.destination = {690.709167f,-766.988770f,-209.290512f};
        if (ValidateEncounterDestination(ai,plan) && encounter::OutsideCircles(plan.destination,threats)) return plan;
    }
    const auto candidates = encounter::EscapeCircles(here, threats);
    unsigned checked = 0;
    for (const auto& point : candidates)
    {
        if (++checked > 32) break; // Cover complete near rings; retain a bounded native path search.
        plan.active = true; plan.destination = point;
        if (ValidateEncounterDestination(ai, plan) && encounter::OutsideCircles(plan.destination, threats)) return plan;
    }
    plan.active = false;
    return plan;
}
