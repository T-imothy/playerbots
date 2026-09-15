#pragma once
#include "Common.h"
#include "TacticalCommandPolicy.h"
#include <functional>
class Player;
class Unit;
namespace ai {
struct TacticalResult { bool started=false; uint32 executor=0,spell=0; std::string reason; };
class TacticalCommands {
public:
    // Called only by the existing world-owned recruitment dispatcher.
    static TacticalResult Execute(Player* owner,Unit* target,TacticalCommand const& command,
        std::function<bool(Player*)> const& authorized);
};
}
