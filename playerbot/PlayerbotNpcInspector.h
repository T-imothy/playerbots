#pragma once
#include <string>
class Player;

class PlayerbotNpcInspector
{
public:
    static bool Handle(Player* viewer, const std::string& message);
    static void Update();
};
