#pragma once
#ifdef MANTECH_RAID_LAB
#include <string>
namespace ai {
struct RaidLabCorridorRoute {
    const char* name;
    unsigned map, boss, size;
    float x,y,z;
};
// Native local spawn coordinates. These are first-boss/segment destinations,
// not a claim of full-raid traversal. Only suppression starts mid-instance.
inline constexpr RaidLabCorridorRoute RaidLabCorridorRoutes[] = {
    {"molten-entrance",409,12118,40,1000.2026f,-955.4069f,-179.5825f},
    {"suppression",469,12017,40,-7573.89f,-1035.25f,449.248f},
    {"onyxia-entrance",249,10184,40,-4.868896f,-217.1708f,-86.71037f},
    {"zulgurub-entrance",309,14507,20,-12029.8f,-1707.93f,39.413f},
    {"naxxramas-entrance",533,15956,40,3316.47f,-3476.23f,287.26f},
    {"ruins-entrance",509,15348,20,-8824.54f,1629.52f,20.446f},
    {"temple-entrance",531,15263,40,-8346.05f,2080.98f,125.732f}
};
inline const RaidLabCorridorRoute* FindRaidLabCorridor(const std::string& name) {
    for(const auto& route:RaidLabCorridorRoutes)if(name==route.name)return &route;
    return nullptr;
}
}
#endif
