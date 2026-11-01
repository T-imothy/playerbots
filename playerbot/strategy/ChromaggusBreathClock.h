#pragma once
#include <ctime>

namespace ai
{
    // Observations, not access to the boss AI's private timers. Native Classic
    // starts the two breaths at 30/60 seconds and repeats each every 60 seconds.
    struct ChromaggusBreathClock
    {
        time_t due[2] = {}, last = 0;
        unsigned spells[2] = {}, active = 0;
        bool initialized = false;

        void Reset() { *this = ChromaggusBreathClock{}; }
        static bool IsBreath(unsigned id)
        {
            switch (id)
            {
                case 23187: case 23189: case 23308: case 23309: case 23310:
                case 23312: case 23313: case 23314: case 23315: case 23316: return true;
                default: return false;
            }
        }
        bool Observe(time_t now, unsigned cast)
        {
            if (initialized && (now < last || now - last > 10)) Reset();
            if (!initialized) { due[0] = now + 30; due[1] = now + 60; initialized = true; }
            last = now;
            if (!IsBreath(cast)) cast = 0;
            if (cast && cast != active)
            {
                unsigned slot = spells[1] == cast ? 1 : 0;
                if (spells[0] && spells[0] != cast && spells[1] != cast) slot = 1;
                spells[slot] = cast;
                due[slot] = now + 60;
                // A late first observation must not predict the other breath
                // immediately; the native initial cycles are 30 seconds apart.
                if (!spells[1 - slot]) due[1 - slot] = now + 30;
            }
            active = cast;
            if (cast) return true;
            for (time_t& deadline : due)
            {
                // No observed cast: expire this warning instead of remaining
                // hidden forever. A later actual cast re-synchronizes it.
                while (now > deadline + 5) deadline += 60;
                if (now >= deadline - 8 && now <= deadline + 5) return true;
            }
            return false;
        }
    };
}
