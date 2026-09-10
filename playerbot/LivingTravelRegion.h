#ifndef LIVING_TRAVEL_REGION_H
#define LIVING_TRAVEL_REGION_H

#include "Server/DBCStores.h"
#include <algorithm>
#include <initializer_list>

// Map 530 combines Outland with distant Azeroth starter continents. Route
// costing runs on map workers: never load VMAP terrain just to classify it.
// Immutable world-map bounds include the coastal ferry approach as well as
// the cities; the six explicit regions do not admit Outland or Quel'Danas.
inline bool LivingIsStarterContinentPosition(uint32 mapId, float x, float y)
{
    if (mapId != 530)
        return false;
    for (uint32 zoneId : {3430u, 3433u, 3487u, 3524u, 3525u, 3557u})
    {
        if (MapCoordinateVsZoneCheck(x, y, mapId, zoneId))
            return true;
    }
    return false;
}

#endif
