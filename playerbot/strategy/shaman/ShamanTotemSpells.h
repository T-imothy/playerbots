#pragma once

namespace ai
{
    // Wrath merged poison/disease cleansing into spell 8170. Keep the old
    // strategy/command keys, but resolve their actual spell in this expansion.
    inline const char* DiseaseCleansingTotemName()
    {
#ifdef MANGOSBOT_TWO
        return "cleansing totem";
#else
        return "disease cleansing totem";
#endif
    }

    inline const char* PoisonCleansingTotemName()
    {
#ifdef MANGOSBOT_TWO
        return "cleansing totem";
#else
        return "poison cleansing totem";
#endif
    }
}
