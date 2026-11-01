#pragma once
#ifdef MANTECH_RAID_LAB
#include "World/RaidLab.h"
#endif
namespace ai {
inline bool RaidLabMovementResult(Player* bot, const char* operation, uint32 line, bool result)
{
#ifdef MANTECH_RAID_LAB
    if (bot && bot->IsInWorld() && RaidLab::AllowedMap(bot->GetMapId()))
        RaidLab::Count(bot,operation,line,result?1:0);
#endif
    return result;
}
}
