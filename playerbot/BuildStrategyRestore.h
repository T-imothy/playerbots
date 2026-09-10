#pragma once

#include <string>
#include <vector>

namespace ai
{
    // Only build-owned strategy names are replaced after restoring a saved AI
    // preset. Follow/stay, loot, custom strategies and saved context are not builds.
    inline bool IsBuildOwnedStrategy(const std::string& name, unsigned int classId)
    {
        if (name.compare(0, 8, "custom::") == 0)
            return false;

        for (const char* owned : {"ranged", "close", "behind", "flee", "tank assist",
            "dps assist", "pull", "pull back", "living party combat", "living party healer offdps"})
            if (name == owned)
                return true;

        std::vector<std::string> roots = {"offheal", "offdps"};
        // Native class IDs; this helper deliberately has no world dependencies.
        switch (classId)
        {
            case 1: roots.insert(roots.end(), {"arms", "fury", "protection"}); break;
            case 2: roots.insert(roots.end(), {"holy", "protection", "retribution"}); break;
            case 3: roots.insert(roots.end(), {"beast mastery", "marksmanship", "survival"}); break;
            case 4: roots.insert(roots.end(), {"assassination", "combat", "subtlety"}); break;
            case 5: roots.insert(roots.end(), {"discipline", "holy", "shadow"}); break;
            case 6: roots.insert(roots.end(), {"blood", "frost", "unholy"}); break;
            case 7: roots.insert(roots.end(), {"elemental", "enhancement", "restoration"}); break;
            case 8: roots.insert(roots.end(), {"arcane", "fire", "frost"}); break;
            case 9: roots.insert(roots.end(), {"affliction", "demonology", "destruction"}); break;
            case 11: roots.insert(roots.end(), {"balance", "restoration", "tank feral", "dps feral"}); break;
        }

        // Include dependent variants (e.g. "totems enhancement pve"), not just
        // their root. Leaving those behind retains the previous spell rotation.
        const std::string words = " " + name + " ";
        for (const std::string& root : roots)
            if (words.find(" " + root + " ") != std::string::npos)
                return true;
        return false;
    }
}
