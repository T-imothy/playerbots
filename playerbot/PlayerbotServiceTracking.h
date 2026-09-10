#pragma once

class Player;

namespace ai
{
    // Pure post-operation test, also exercised by the native regression test.
    inline bool LivingServiceChanged(unsigned before, unsigned after, bool increase)
    {
        return increase ? after > before : after < before;
    }

    class PlayerbotServiceTracking
    {
    public:
        static void Update();
        static bool Result(Player* bot, const char* service, unsigned target, unsigned item,
            const char* metric, unsigned before, unsigned after, bool increase = true,
            const char* failure = "no_state_change");
        static unsigned Durability(Player* bot);
    };
}
