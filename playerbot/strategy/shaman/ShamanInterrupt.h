#pragma once

namespace ai
{
    inline const char* ShamanInterruptSpell()
    {
#ifdef MANGOSBOT_TWO
        return "wind shear";
#else
        return "earth shock";
#endif
    }
}
