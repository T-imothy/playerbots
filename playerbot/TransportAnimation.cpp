#include "playerbot/playerbot.h"
#include "TransportAnimation.h"
#include "Database/DBCStore.h"
#include <cmath>

namespace {
struct AnimationEntry {
    uint32 id, entry, time;
    float x, y, z;
};
struct AnimationIndex {
    // Node-owning maps are never modified after construction. Published pointers
    // remain valid through shutdown and all joined bot/navigation jobs.
    std::map<uint32, std::map<uint32, TransportAnimationNode>> nodes;
    std::map<uint32, TransportAnimation> animations;
    AnimationIndex()
    {
        DBCStorage<AnimationEntry> storage("niifffx");
        std::string path = sWorld.GetDataPath() + "dbc/TransportAnimation.dbc";
        if (!storage.Load(path.c_str())) {
            sLog.outError("ManTech: optional TransportAnimation.dbc unavailable; animated transport route generation disabled");
            return;
        }
        for (uint32 id = 0; id < storage.GetNumRows(); ++id)
            if (auto const* row = storage.LookupEntry(id))
                if (row->entry && std::isfinite(row->x) && std::isfinite(row->y) && std::isfinite(row->z))
                    nodes[row->entry].emplace(row->time,
                        TransportAnimationNode{row->id, row->time, row->x, row->y, row->z});
        for (auto& entry : nodes) {
            auto& animation = animations[entry.first];
            for (auto& node : entry.second) animation.Path.emplace(node.first, &node.second);
            animation.TotalTime = entry.second.rbegin()->first;
        }
        sLog.outString("ManTech: loaded %zu transport animation paths", animations.size());
    }
};
}
TransportAnimation const* GetPlayerbotTransportAnimation(unsigned int entry)
{
    static AnimationIndex const index;
    auto found = index.animations.find(entry);
    return found == index.animations.end() ? nullptr : &found->second;
}
