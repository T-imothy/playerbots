#pragma once
#include "playerbot/strategy/Value.h"

namespace ai
{
    class AttackerWithoutAuraTargetValue : public UnitCalculatedValue, public Qualified
	{
	public:
        AttackerWithoutAuraTargetValue(PlayerbotAI* ai, bool owned = false) : UnitCalculatedValue(ai, owned ? "attacker without my aura" : "attacker without aura"), Qualified(), owned(owned) {}

    protected:
        virtual Unit* Calculate() override;
        bool owned;
	};
}
