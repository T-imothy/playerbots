#pragma once
class PlayerbotAI;
class Unit;
namespace ai
{
    struct EncounterPosition;
    bool RazuviousControlCover(PlayerbotAI* ai, Unit* boss, Unit* student, EncounterPosition& plan);
    bool NaxxramasControlAllowed(PlayerbotAI* ai);
    void ProcessNaxxramasControlCommands(PlayerbotAI* ai, bool commandsPending);
}
