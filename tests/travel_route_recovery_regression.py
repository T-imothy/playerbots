"""Compile actual route selection and getFullPath; no realm or database needed."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

source = (Path(__file__).resolve().parents[1] / 'playerbot/TravelNode.cpp').read_text()
route = block(source, 'TravelNodeRoute TravelNodeMap::getRoute(TravelNode* start,')
assert not any(name in route for name in ('push_heap', 'make_heap', 'pop_heap'))
start = route.index('        auto selected =')
end = route.index('        currentNode->open = false;', start)
selection = route[start:end]
full_path = block(source, 'TravelPath TravelNodeMap::getFullPath(')

code = r'''
#include <algorithm>
#include <cassert>
#include <future>
#include <iostream>
#include <shared_mutex>
#include <stdexcept>
#include <vector>
struct TravelNodeStub { float m_f; int id; };
TravelNodeStub* pop(std::vector<TravelNodeStub*>& open) {
    TravelNodeStub* currentNode;
    __SELECTION__
    return currentNode;
}
struct Unit {};
struct WorldPosition {
    bool direct = false;
    std::vector<WorldPosition> getPathFromPath(std::vector<WorldPosition> path, Unit*, int) { return path; }
    bool isPathTo(const std::vector<WorldPosition>&, float) { return direct; }
};
struct TravelPath {
    int size = 0;
    TravelPath() = default;
    TravelPath(const std::vector<WorldPosition>& path) : size(int(path.size())) {}
};
struct { float spellDistance = 30; } sPlayerbotAIConfig;
int mode = 0, cleanups = 0, lookups = 0;
struct TravelNodeRoute {
    bool isEmpty() { return mode == 1; }
    void cleanTempNodes() { ++cleanups; }
    TravelPath buildPath(const std::vector<WorldPosition>&, const std::vector<WorldPosition>&) {
        if (mode == 3) throw std::runtime_error("path failure");
        TravelPath path; path.size = 2; return path;
    }
};
struct TravelNodeMap {
    std::shared_timed_mutex m_nMapMtx;
    TravelNodeRoute getRoute(WorldPosition, WorldPosition, std::vector<WorldPosition>&,
                            std::vector<WorldPosition>&, Unit*) {
        ++lookups;
        if (mode == 2) throw std::runtime_error("lookup failure");
        return {};
    }
    TravelPath getFullPath(WorldPosition, WorldPosition, Unit*);
} sTravelNodeMap;
__FULL_PATH__
bool writerCanAcquire() {
    // Another thread probes the lock; never recursively acquire on the reader.
    return std::async(std::launch::async, [] {
        if (!sTravelNodeMap.m_nMapMtx.try_lock()) return false;
        sTravelNodeMap.m_nMapMtx.unlock(); return true;
    }).get();
}
int main() {
    TravelNodeStub a{10,1}, b{2,2}, c{5,3}, d{5,4};
    std::vector<TravelNodeStub*> open{&a,&b,&c,&d};
    assert(pop(open) == &b);
    assert(open.size() == 3 && std::find(open.begin(),open.end(),&b) == open.end());
    a.m_f = 1; // An already-open route becomes cheaper after relaxing a link.
    assert(pop(open) == &a);
    auto first = pop(open); auto second = pop(open);
    assert(first != second && first->m_f == 5 && second->m_f == 5 && open.empty());
    open = {&a}; assert(pop(open) == &a && open.empty());
    // Reopen an expanded node after discovering a better path.
    a.m_f = 0.5f; open = {&c,&a}; assert(pop(open) == &a && pop(open) == &c);
    mode = 1;
    assert(sTravelNodeMap.getFullPath({}, {}, nullptr).size == 0);
    assert(cleanups == 1 && writerCanAcquire());
    for (mode = 2; mode <= 3; ++mode) {
        bool caught = false;
        try { sTravelNodeMap.getFullPath({}, {}, nullptr); }
        catch (const std::runtime_error&) { caught = true; }
        assert(caught && writerCanAcquire());
    }
    mode = 0;
    assert(sTravelNodeMap.getFullPath({}, {}, nullptr).size == 2 && writerCanAcquire());
    const int before = lookups;
    assert(sTravelNodeMap.getFullPath({}, {true}, nullptr).size == 1);
    assert(lookups == before && writerCanAcquire());
    std::cout << "PASS: mutable route costs, ties, exact removal, reopen; lock release on empty, success and exceptions\n";
}
'''.replace('__SELECTION__', selection).replace('__FULL_PATH__', full_path)

with tempfile.TemporaryDirectory(prefix='mantech-route-recovery-') as folder:
    tmp = Path(folder)
    (tmp / 'test.cpp').write_text(code)
    for expansion in ('ZERO', 'ONE', 'TWO'):
        subprocess.run(['cl', '/nologo', '/std:c++17', '/EHsc', '/D' + 'MANGOSBOT_' + expansion,
                        'test.cpp', '/Fe:test.exe'], cwd=tmp, check=True)
        subprocess.run([str(tmp / 'test.exe')], cwd=tmp, check=True)
