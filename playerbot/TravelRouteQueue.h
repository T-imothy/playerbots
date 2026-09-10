#pragma once

#include <algorithm>
#include <vector>

namespace ai
{
    // Route costs can decrease while a node is open. A heap of pointers whose
    // keys mutate is invalid unless rebuilt; scan once instead of sorting every
    // expansion. Removing exactly the selected node preserves open membership.
    template<class Node>
    Node* PopLowestRouteCost(std::vector<Node*>& open)
    {
        if (open.empty())
            return nullptr;
        auto selected = std::min_element(open.begin(), open.end(),
            [](Node* a, Node* b) { return a->m_f < b->m_f; });
        Node* result = *selected;
        *selected = open.back();
        open.pop_back();
        return result;
    }
}
