
#include "playerbot/playerbot.h"
#include "playerbot/ServerFacade.h"
#include "HazardsValue.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "MotionGenerators/PathFinder.h"
#include "Entities/GameObject.h"
#include "Entities/DynamicObject.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;

void ai::AppendBlackwingGroundHazards(PlayerbotAI* ai, std::list<HazardPosition>& hazards)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->GetMapId() != 469 ||
        bot->IsBeingTeleported() || bot->HasCharmer()) return;
    struct FireCheck
    {
        Player* bot;
        WorldObject const& GetFocusObject() const { return *bot; }
        bool operator()(WorldObject* object) const
        {
            if (!object || object->GetTypeId() != TYPEID_DYNAMICOBJECT || !object->IsInWorld() ||
                !bot->IsInMap(object) || std::fabs(object->GetPositionZ() - bot->GetPositionZ()) > 8) return false;
            DynamicObject* fire = static_cast<DynamicObject*>(object);
            Unit* caster = fire->GetCaster();
            const uint32 spell = fire->GetSpellId();
            if (spell != 19717 && spell != 22275) return false;
            return fire->GetType() == DYNAMIC_OBJECT_AREA_SPELL && fire->GetDuration() > 0 &&
                std::isfinite(fire->GetRadius()) && fire->GetRadius() > 0 && fire->GetRadius() <= 25 &&
                caster && !caster->HasCharmer() && bot->IsInMap(caster) && fire->IsEnemy(bot) &&
                fire->CanAttackSpell(bot, sServerFacade.LookupSpellInfo(spell), true);
        }
    } check{bot};
    WorldObjectList objects;
    MaNGOS::WorldObjectListSearcher<FireCheck> searcher(objects, check);
    Cell::VisitAllObjects(bot, searcher, 60.0f);
    for (WorldObject* object : objects)
        hazards.emplace_back(WorldPosition(object), static_cast<DynamicObject*>(object)->GetRadius() + 1.0f);
}

Hazard::Hazard()
: position(WorldPosition())
, expirationTime(0)
, guid(ObjectGuid())
, radius(0.0f)
, hazardNavmeshArea(0)
, previousNavmeshArea(0)
{

}

Hazard::Hazard(const WorldPosition& inPosition, uint64 inExpiration, float inRadius)
: position(inPosition)
, expirationTime(time(0) + inExpiration)
, guid(ObjectGuid())
, radius(inRadius)
, hazardNavmeshArea(14)
, previousNavmeshArea(11)
{

}

Hazard::Hazard(const ObjectGuid& inGuid, uint64 inExpiration, float inRadius)
: position(WorldPosition())
, expirationTime(time(0) + inExpiration)
, guid(inGuid)
, radius(inRadius)
, hazardNavmeshArea(14)
, previousNavmeshArea(11)
{

}

bool Hazard::operator==(const Hazard& other) const
{
    if (!guid.IsEmpty())
    {
        return (guid == other.guid);
    }
    else if (position)
    {
        return position == other.position;
    }

    return false;
}

bool Hazard::operator<(const Hazard& other) const
{
    return radius < other.radius;
}

bool Hazard::GetPosition(PlayerbotAI* ai, WorldPosition& outPosition)
{
    const WorldObject* object = GetObject(ai);
    if (object)
    {
        outPosition = position = WorldPosition(object);
        return true;
    }
    else if (guid.IsEmpty() && position)
    {
        outPosition = position;
        return true;
    }

    return false;
}

bool Hazard::IsExpired() const
{
    return time(0) > expirationTime;
}

bool Hazard::IsValid(PlayerbotAI* ai) const
{
    if (IsExpired()) return false;
    if (guid.IsEmpty()) return bool(position);
    const WorldObject* object = GetObject(ai);
    // Object hazards end with the object. Its remembered coordinates must not
    // turn a despawned void zone into a permanent invisible obstacle. Native
    // map membership also excludes another phase in cores supporting phases.
    if (!object || !ai->GetBot()->IsInMap(object)) return false;
    if (object->GetTypeId() == TYPEID_GAMEOBJECT)
        return static_cast<const GameObject*>(object)->IsSpawned();
    if (object->IsUnit()) return static_cast<const Unit*>(object)->IsAlive();
    return true;
}

const WorldObject* Hazard::GetObject(PlayerbotAI* ai) const
{
    if (!guid.IsEmpty())
    {
        if (guid.IsUnit())
        {
            return ai->GetUnit(guid);
        }
        else if (guid.IsGameObject())
        {
            return ai->GetGameObject(guid);
        }
        else if (guid.IsDynamicObject())
        {
            Player* bot = ai->GetBot();
            return bot->IsInWorld() ? bot->GetMap()->GetDynamicObject(guid) : nullptr;
        }
    }

    return nullptr;
}

void AddHazardValue::Set(Hazard hazard)
{
    AiObjectContext* context = ai->GetAiObjectContext();
    std::list<Hazard> storedHazards = AI_VALUE(std::list<Hazard>, "stored hazards");

    // Check if the hazard already exists
    auto it = std::find(storedHazards.begin(), storedHazards.end(), hazard);
    if (it == storedHazards.end())
    {
        storedHazards.emplace_back(std::move(hazard));
        SET_AI_VALUE(std::list<Hazard>, "stored hazards", storedHazards);
    }
}

std::list<HazardPosition> HazardsValue::Calculate()
{
    AiObjectContext* context = ai->GetAiObjectContext();
    std::list<Hazard> storedHazards = AI_VALUE(std::list<Hazard>, "stored hazards");

    // Create an updated hazard positions list
    bool hazardsUpdated = false;
    std::list<HazardPosition> hazards;
    for (auto it = storedHazards.begin(); it != storedHazards.end();)
    {
        // Check if the hazard is valid
        bool validHazard = false;
        Hazard& hazard = (*it);
        if (hazard.IsValid(ai))
        {
            // Try to retrieve the hazard position
            WorldPosition hazardPosition;
            if (hazard.GetPosition(ai, hazardPosition))
            {
                hazards.emplace_back(std::make_pair(hazardPosition, hazard.GetRadius()));
                validHazard = true;
            }
        }

        // Remove the invalid hazards
        if (!validHazard)
        {
            it = storedHazards.erase(it);
            hazardsUpdated = true;
        }
        else
        {
            ++it;
        }
    }

    if (hazardsUpdated)
    {
        SET_AI_VALUE(std::list<Hazard>, "stored hazards", storedHazards);
    }

    AppendMoltenCoreGroundHazards(ai, hazards);
    AppendBlackwingGroundHazards(ai, hazards);
    AppendVashjStriderHazards(ai, hazards);
    AppendNativeEncounterActorHazards(ai, hazards);
    return hazards;
}
