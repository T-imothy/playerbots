#pragma once

// Native Classic adapters for the useful BWL/Onyxia/AQ20/Naxx tactics in
// mod-playerbots 79bd428115c8f33b74b13de23b133d49c3f75c60 (GPLv2).
// No Wrath raid IDs, crystal controls, aura grants or teleports are imported.
namespace ai { namespace classicraid
{
    inline bool Map(unsigned map)
    {
        return map == 249 || map == 309 || map == 469 || map == 509 || map == 531 || map == 533;
    }
    inline bool EggZone(float x, float y, float z)
    {
        if (z < -96 || z > -84) return false;
        const float a = (x + 36) * (x + 36) + (y + 164) * (y + 164) + (z + 90) * (z + 90);
        const float b = (x + 34) * (x + 34) + (y + 262) * (y + 262) + (z + 90) * (z + 90);
        return a <= 36 || b <= 36;
    }
    inline bool Boss(unsigned map, unsigned entry)
    {
        switch (map)
        {
            case 249: return entry == 10184;
            case 469:
                return entry == 12435 || entry == 13020 || entry == 12017 || entry == 11983 ||
                    entry == 14601 || entry == 11981 || entry == 14020 || entry == 11583 || entry == 12460 ||
                    entry == 12416 || entry == 12420 || entry == 12422 || entry == 12457 || entry == 12458 ||
                    entry == 12459 || entry == 12461 || entry == 12463 || entry == 12464 || entry == 12465 ||
                    entry == 12467 || entry == 12468 || entry == 12557 || entry == 13996 || entry == 14456 ||
                    (entry >= 14022 && entry <= 14025) || (entry >= 14261 && entry <= 14265) ||
                    entry == 14302 || entry == 14605 || entry == 14668 || entry == 14101;
            case 309:
                return entry == 14517 || entry == 14507 || entry == 14510 || entry == 14509 ||
                    entry == 14515 || entry == 11382 || entry == 15114 || entry == 11380 || entry == 14834 ||
                    entry == 15082 || entry == 15083 || entry == 15084 || entry == 15085;
            case 509:
                return entry == 15348 || entry == 15341 || entry == 15340 || entry == 15370 ||
                    entry == 15369 || entry == 15339;
            case 531:
                return entry == 15263 || entry == 15543 || entry == 15544 || entry == 15511 ||
                    entry == 15516 || entry == 15510 || entry == 15509 || entry == 15275 ||
                    entry == 15276 || entry == 15299 || entry == 15517 || entry == 15589 || entry == 15727;
            case 533:
                return entry == 15956 || entry == 15953 || entry == 15952 || entry == 15954 ||
                    entry == 15936 || entry == 16011 || entry == 16061 || entry == 16060 ||
                    (entry >= 16062 && entry <= 16065) || entry == 16028 || entry == 15931 ||
                    entry == 15932 || entry == 15928 || entry == 15929 || entry == 15930 || entry == 15989 || entry == 15990;
        }
        return false;
    }
    inline unsigned HorsemanMark(unsigned entry)
    {
        switch (entry)
        {
            case 16062: return 28834;
            case 16063: return 28835;
            case 16064: return 28832;
            case 16065: return 28833;
        }
        return 0;
    }
    // Rotate to the next clean, living corner after native relief. Waiting at
    // the same marked boss cannot reset a tank's marks fast enough in Classic.
    inline int ReliefCorner(const unsigned* marks, unsigned count, int previous)
    {
        if (!count || previous < 0 || unsigned(previous) >= count) return -1;
        for (unsigned step = 1; step <= count; ++step)
        {
            const unsigned next = (unsigned(previous) + step) % count;
            if (marks[next] < 3) return int(next);
        }
        return -1;
    }
    inline bool Corner(unsigned entry, float& x, float& y)
    {
        // Four native melee lanes, inside the Classic room/entrance leash.
        // Each is still admitted through native floor/full-path validation.
        switch (entry)
        {
            case 16062: x = 2600; y = -2965; return true;
            case 16063: x = 2505; y = -2899; return true;
            case 16064: x = 2513; y = -3022; return true;
            case 16065: x = 2468; y = -2958; return true;
        }
        return false;
    }
    inline unsigned AddPriority(unsigned boss, unsigned entry, bool frenzied, bool decimated)
    {
        switch (boss)
        {
            case 15956: return entry == 16573 ? 4 : 0; // Crypt Guard
            case 15953: return entry == 16505 ? 3 : 0; // 16506 worshippers are reserved for native Embrace.
            case 15952: return entry == 16486 ? 8 : entry == 17055 ? 2 : 0;
            case 15954: return entry == 16984 || entry == 16983 || entry == 16981 || entry == 16982 ? 3 : 0;
            case 16060: return entry == 16125 || entry == 16126 || entry == 16127 ||
                entry == 16124 || entry == 16148 || entry == 16149 || entry == 16150 ? 3 : 0;
            case 15932: return entry == 16360 && decimated ? 6 : 0;
            case 15990: return entry == 16428 ? 7 : entry == 16429 ? 6 : entry == 16427 ? 5 : 0;
        }
        return 0;
    }
    inline bool Dragon(unsigned entry)
    {
        return entry == 10184 || entry == 13020 || entry == 11983 || entry == 14601 ||
            entry == 11981 || entry == 11583 || entry == 15989;
    }
    inline bool Front(unsigned entry)
    {
        return Dragon(entry) || entry == 12435 || entry == 12017 || entry == 14020 || entry == 12460 ||
            entry == 12416 || entry == 12422 || entry == 12461 || entry == 12467 || entry == 14456 ||
            entry == 15956 || entry == 15952 || entry == 16028 || entry == 15931 || entry == 15932 ||
            entry == 15517 || entry == 15510;
    }
} }
