#include "PartyCatchupMath.h"
#include <cassert>
#include <limits>
int main()
{
    using namespace ai;
    assert(PartyCatchupMultiplier(0, 5, 3600, 5) == 1);
    assert(PartyCatchupMultiplier(50000, 0, 3600, 5) == 1);
    assert(PartyCatchupMultiplier(50000, 5, 3600, 5) > PartyCatchupMultiplier(15000, 5, 3600, 5));
    assert(PartyCatchupMultiplier(50000000, 1, 600, 5) == 5);
    assert(PartyCatchupBonus(100, 10000, 3) == 200);
    assert(PartyCatchupBonus(100, 150, 5) == 50);
    assert(PartyCatchupBonus(100, 100, 5) == 0);
    assert(PartyCatchupBonus(100, 50, 5) == 0);
    assert(PartyCatchupBonus(0, 10000, 5) == 0);
    assert(PartyCatchupBonus(100, 10000, 1) == 0);
    assert(PartyCatchupBonus(100, 10000, std::numeric_limits<double>::quiet_NaN()) == 0);
    for (uint64_t gap = 1; gap < 10000; gap += 19)
        for (uint64_t base = 1; base < 1000; base += 13)
        {
            auto extra = PartyCatchupBonus(base, gap, 5);
            assert(extra <= 4*base);
            assert(extra == 0 || base + extra <= gap);
        }
    // A sequence of earned awards closes the gap without awarding XP while idle.
    uint64_t gap=6000, normal=100;
    for (int i=0;i<100 && gap>normal;++i)
    {
        double rate=PartyCatchupMultiplier(gap, 1, 600, 5);
        auto award=normal+PartyCatchupBonus(normal,gap,rate);
        assert(award<=gap);
        gap-=award;
    }
    assert(gap<=normal);
}
