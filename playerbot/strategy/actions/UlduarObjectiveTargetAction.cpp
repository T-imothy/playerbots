#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleTargetsValue.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"
#ifdef MANGOSBOT_TWO
#include "Maps/TransportSystem.h"
#endif

using namespace ai;

Unit* DungeonAddTargetAction::GetUlduarObjectiveTarget()
{
#ifdef MANGOSBOT_TWO
    if (bot->GetMapId() != 603 || !bot->GetGroup() || !bot->IsInWorld() || !bot->IsAlive() ||
        !bot->IsInCombat() || bot->HasCharmer() || bot->IsBeingTeleported()) return nullptr;
    auto live = [this](Unit* unit) {
        return unit && unit->IsInWorld() && unit->IsAlive() && bot->IsInMap(unit) && !unit->HasCharmer();
    };
    auto member = [this, &live](Unit* unit) {
        return live(unit) && unit->IsPlayer() && !static_cast<Player*>(unit)->IsBeingTeleported() &&
            static_cast<Player*>(unit)->GetGroup() == bot->GetGroup();
    };
    const auto nearby = AI_VALUE2(std::list<ObjectGuid>, "possible targets", "100:1");
    Unit* current = ai->GetUnit(AI_VALUE(ObjectGuid, "current target"));
    Unit* selected = nullptr;
    Unit* owner = nullptr;
    unsigned selectedRank = 0;
    for (const auto& guid : nearby)
    {
        Unit* add = ai->GetUnit(guid);
        if (!live(add)) continue;
        const uint32 entry = add->GetEntry();
        uint32 bossEntry = 0;
        unsigned rank = 0;
        switch (entry)
        {
            case 32934: bossEntry = 32930; break; // Kologarn's right arm, while actually holding a player.
            case 32926: case 32938: bossEntry = 32845; break; // Hodir's player/NPC-owned Flash Freeze.
            case 33228: bossEntry = 32906; break; // Freya's passive healing tree.
            default: continue;
        }
        Unit* boss = nullptr;
        for (const auto& bossGuid : nearby)
        {
            Unit* candidate = ai->GetUnit(bossGuid);
            if (!live(candidate) || candidate->GetEntry() != bossEntry || !candidate->IsInCombat() ||
                candidate->GetVictim() == bot || !member(candidate->GetVictim()) ||
                bot->GetDistance(candidate) > 100 || add->GetDistance(candidate) > 100) continue;
            if (boss && boss != candidate) return nullptr;
            boss = candidate;
        }
        if (!boss) continue;
        if (entry == 32926 || entry == 32938)
        {
            Unit* prisoner = ai->GetUnit(add->GetSpawnerGuid());
            // The ice block casts its stun onto its summoner. Require that
            // exact live relationship, not an unrelated Freeze/root aura.
            if (!live(prisoner) || !sServerFacade.IsFriendlyTo(prisoner, bot) ||
                prisoner->GetDistance(add) > 20 ||
                !prisoner->GetSpellAuraHolder(entry == 32938 ? 61990 : 61969, add->GetObjectGuid())) continue;
            if (prisoner->IsPlayer())
            {
                if (entry == 32938 || !member(prisoner)) continue;
            }
            else rank = 1; // Free living raid members before the friendly NPC helpers.
        }
        else
        {
            if (ai->GetUnit(add->GetSpawnerGuid()) != boss) continue;
            if (entry == 32934)
            {
                bool carryingMember = false;
                for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
                {
                    Player* player = ref->getSource();
                    if (member(player) && player->IsBoarded() && player->GetTransportInfo() &&
                        player->GetTransportInfo()->GetTransport() == add)
                    {
                        carryingMember = true;
                        break;
                    }
                }
                if (!carryingMember) continue;
            }
        }
        // Neither a stationary tree nor an ice block needs a threat victim.
        // Normal attackability, immunity, range and player CC still apply.
        if (!PossibleTargetsValue::IsValid(add, bot, false) ||
            !PossibleAttackTargetsValue::IsPossibleTarget(add, bot, sPlayerbotAIConfig.sightDistance, false) ||
            PossibleAttackTargetsValue::HasBreakableCC(add, bot) ||
            PossibleAttackTargetsValue::HasUnBreakableCC(add, bot)) continue;
        if (owner && owner != boss) return nullptr;
        owner = boss;
        if (!selected || rank < selectedRank || (rank == selectedRank &&
            (add == current || (selected != current && bot->GetDistance(add) < bot->GetDistance(selected)))))
        {
            selected = add;
            selectedRank = rank;
        }
    }
    return selected;
#else
    return nullptr;
#endif
}
