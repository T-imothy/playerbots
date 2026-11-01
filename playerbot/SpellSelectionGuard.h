#pragma once

namespace ai
{
    // Native cast checks sometimes need the UI selection to match their target.
    // That temporary selection is not a new combat order, even if the cast fails.
    class ScopedSpellSelection
    {
    public:
        ScopedSpellSelection(Player* player, ObjectGuid target)
            : player(player), previous(player->GetSelectionGuid())
        {
            player->SetSelectionGuid(target);
        }
        ~ScopedSpellSelection() { player->SetSelectionGuid(previous); }
        ScopedSpellSelection(const ScopedSpellSelection&) = delete;
        ScopedSpellSelection& operator=(const ScopedSpellSelection&) = delete;
    private:
        Player* player;
        ObjectGuid previous;
    };
}
