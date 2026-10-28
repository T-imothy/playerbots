#pragma once

namespace ai { namespace naxxnative
{
    inline unsigned MindControl()
    {
#ifdef MANGOSBOT_TWO
        return 605; // Wrath removed the additional Mind Control ranks.
#else
        return 10912;
#endif
    }
    inline bool ObedienceCrystal(bool regular)
    {
#ifdef MANGOSBOT_TWO
        return regular;
#else
        return false;
#endif
    }
    inline unsigned FaerlinaFrenzy(bool regular)
    {
#ifdef MANGOSBOT_TWO
        return regular ? 28798 : 54100;
#else
        return 28798;
#endif
    }
    inline unsigned FaerlinaEmbrace(bool regular)
    {
#ifdef MANGOSBOT_TWO
        return regular ? 28732 : 54097;
#else
        return 28732;
#endif
    }
    inline bool WorshipperDeathEmbrace(bool regular)
    {
#ifdef MANGOSBOT_TWO
        return regular;
#else
        return false;
#endif
    }
} }
