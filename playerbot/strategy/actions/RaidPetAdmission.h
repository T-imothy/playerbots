#pragma once

class Unit;
struct SpellEntry;
namespace ai
{
    // Native PetAI admission only for the automated owner's actual pet in Naxx.
    // A null spell describes a melee/auto attack; native controlled actors and
    // all other owners/maps continue through their original admission.
    bool RaidPetOffenseAllowed(Unit* pet, const SpellEntry* spell, Unit* target);
    void StopUnsafeRaidPetCasts(Unit* pet);
}
