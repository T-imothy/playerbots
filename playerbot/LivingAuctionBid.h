#pragma once
#include <algorithm>
#include <cstdint>
#include <limits>

// Match the core's strict bid increase and outbid increment. Zero means that
// no representable bid exists; a zero buyout means the auction has no buyout.
inline uint32_t LivingAuctionMinimumBid(uint32_t start, uint32_t bid, uint32_t increment, uint32_t buyout)
{
    if (buyout && (buyout <= bid || buyout < start)) return 0;
    uint64_t next = std::max<uint64_t>(start, uint64_t(bid) + std::max<uint32_t>(1, increment));
    if (buyout && buyout > bid) next = std::min<uint64_t>(next, buyout);
    return next > std::numeric_limits<uint32_t>::max() ? 0 : uint32_t(next);
}
