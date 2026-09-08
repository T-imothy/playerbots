
#include "playerbot/playerbot.h"
#include "RogueActions.h"
#include "playerbot/ServerFacade.h"

using namespace ai;

bool CastPreparationAction::isUseful()
{
    if (!CastBuffSpellAction::isUseful()) return false;
#ifdef MANGOSBOT_ONE
    const uint64 resetMask = 0x0000026000000860;
#elif defined(MANGOSBOT_TWO)
    uint64 resetMask = 0x0000024000000860;
    if (bot->HasAura(56819)) resetMask |= 0x0010080000000010;
#endif
    // Match the native Preparation reset pool, including Wrath's glyph.
    // Reserve the long cooldown for a substantial ability, not a short kick.
    for (const auto& learned : bot->GetSpellMap())
    {
        const SpellEntry* spell = sServerFacade.LookupSpellInfo(learned.first);
        if (!spell || !bot->HasSpell(learned.first) || spell->Id == 14185 ||
            spell->SpellFamilyName != SPELLFAMILY_ROGUE || spell->RecoveryTime < 60000)
            continue;
#ifndef MANGOSBOT_ZERO
        if (!(spell->SpellFamilyFlags & resetMask)) continue;
#endif
        if (!bot->IsSpellReady(spell->Id)) return true;
    }
    return false;
}
