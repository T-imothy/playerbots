#pragma once
#include <cstdint>
#include <vector>

namespace ai
{
    struct HumanPosition
    {
        uint32_t map, instance;
        float x, y, z;
        bool camera = false;
    };
    struct HumanPresence
    {
        bool visible = false;
        std::vector<HumanPosition> positions;
    };
    inline unsigned CountHumansNear(std::vector<HumanPresence> const& humans,
        uint32_t map, uint32_t instance, float x, float y, float z,
        float range, bool cameras, bool threeDimensions)
    {
        if (range <= 0) return 0;
        unsigned count = 0;
        for (auto const& human : humans)
        {
            if (!human.visible) continue;
            for (auto const& pos : human.positions)
            {
                if (pos.map != map || pos.instance != instance || (pos.camera && !cameras)) continue;
                float dx = pos.x-x, dy = pos.y-y, dz = threeDimensions ? pos.z-z : 0;
                if (dx*dx+dy*dy+dz*dz < range*range) { ++count; break; }
            }
        }
        return count;
    }
}
