#pragma once
#include "playerbot/strategy/Value.h"

namespace ai
{
    struct UldamanAltarRequest
    {
        ObjectGuid altar, requester;
        uint32 instance = 0;
        time_t expires = 0;
    };

    class UldamanAltarRequestValue : public ManualSetValue<UldamanAltarRequest>
    {
    public:
        UldamanAltarRequestValue(PlayerbotAI* ai) : ManualSetValue(ai, UldamanAltarRequest{}, "uldaman altar request") {}
        void Reset() override { Set(UldamanAltarRequest{}); }
    };
}
