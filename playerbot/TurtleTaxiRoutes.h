#pragma once

// Content bindings from Penqle's npc_flying_machine script. The script owns
// eligibility and ActivateTaxiPathTo; bots select its offered gossip option.
// These IDs are Turtle content, not reusable core hooks.
namespace ai
{
    struct TurtleTaxiRoute
    {
        uint32 path;
        uint32 creature;
        uint32 gossipAction;
    };

    inline TurtleTaxiRoute const* GetTurtleTaxiRoute(uint32 path)
    {
        static constexpr TurtleTaxiRoute routes[] = {
            {311, 50597, 1001}, // Blackstone Island -> Sparkwater Port
            {322, 50598, 1002}  // Sparkwater Port -> Blackstone Island
        };
        for (auto const& route : routes)
            if (route.path == path)
                return &route;
        return nullptr;
    }
}
