
#include "playerbot/playerbot.h"
#include "DuelTargetValue.h"

using namespace ai;

ObjectGuid DuelTargetValue::Calculate()
{
    if (!bot->m_duel || bot->m_duel->opponent.IsEmpty()) return ObjectGuid();
    return bot->m_duel->opponent;
}
