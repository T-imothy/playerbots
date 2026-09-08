
#include "playerbot/playerbot.h"
#include "PartyMemberToHeal.h"
#include "playerbot/PlayerbotAIConfig.h"
#include "playerbot/ServerFacade.h"
#include "playerbot/strategy/actions/EncounterSpellPolicy.h"

using namespace ai;

class IsTargetOfHealingSpell : public SpellEntryPredicate
{
public:
    virtual bool Check(SpellEntry const* spell) 
    {
        return PlayerbotAI::IsHealSpell(spell);
    }
};

uint32 getIncomingdamage(Unit const* pTarget)
{
    double damage = 0;
    for (auto const& pAttacker : pTarget->getAttackers())
        if (pAttacker->CanReachWithMeleeAttack(pTarget))
        {
            const double hit = (double(pAttacker->GetFloatValue(UNIT_FIELD_MINDAMAGE)) + pAttacker->GetFloatValue(UNIT_FIELD_MAXDAMAGE)) / 2;
            if (!std::isfinite(hit) || hit <= 0) continue;
            damage += hit;
            if (damage >= pTarget->GetHealth()) return pTarget->GetHealth();
        }

    return uint32(damage);
}

bool compareByHealth(const Unit *u1, const Unit *u2)
{
    return u1->GetHealthPercent() < u2->GetHealthPercent();
}

Unit* PartyMemberToHeal::Calculate()
{
    std::vector<Unit*> needHeals;
    std::vector<Unit*> tankTargets;
    const bool preHealing = ai->HasStrategy("preheal", BotState::BOT_STATE_COMBAT);
    // Freeze each candidate's forecast once for this selection. Rewalking its
    // attackers in the sort comparator wastes work and can change comparisons.
    std::map<Unit*, uint32> predictedHealth;
    const auto forecast = [&](Unit* target) -> uint32 {
        auto found = predictedHealth.find(target);
        if (found != predictedHealth.end()) return found->second;
        const uint32 health = target->GetHealth();
        const uint32 damage = preHealing ? std::min(health, getIncomingdamage(target)) : 0;
        return predictedHealth.emplace(target, health - damage).first->second;
    };
    const auto addCandidate = [&](Unit* target) {
        if (std::find(needHeals.begin(), needHeals.end(), target) == needHeals.end())
            needHeals.push_back(target);
    };
    if (bot->GetSelectionGuid())
    {
        Unit* target = ai->GetUnit(bot->GetSelectionGuid());
        if (target &&
            target->GetObjectGuid() != bot->GetObjectGuid() && 
            sServerFacade.IsFriendlyTo(bot, target) &&
            target->GetHealthPercent() < 100 && 
            Check(target))
        {
            addCandidate(target);
        }
    }

    if (GuidPosition rpgTarget = AI_VALUE(GuidPosition, "rpg target"))
    {
        Unit* target = rpgTarget.GetCreature(bot->GetInstanceId());
        if (Check(target) && target->GetHealthPercent() < 100)
        {
            addCandidate(target);
        }
    }

    const std::vector<Player*> partyMembers = GetPartyMembers();
    if (partyMembers.empty() && needHeals.empty())
    {
        return nullptr;
    }

    if (!partyMembers.empty() || !needHeals.empty())
    {
        IsTargetOfHealingSpell predicate;
        for (Player* player : partyMembers)
        {
            if (!Check(player) || !sServerFacade.IsAlive(player))
            {
                continue;
            }

            bool isTank = ai->IsTank(player);

            // do not heal dueling members
            if (player->duel && player->duel->opponent)
            {
                continue;
            }

            uint8 health = uint8((double(forecast(player)) * 100.0) / player->GetMaxHealth());
            if (isTank || ((health < sPlayerbotAIConfig.almostFullHealth || NeedsFullHealingToRemoveAura(player) || RemainingHealingAbsorb(player)) &&
                (health < sPlayerbotAIConfig.criticalHealth || !IsTargetOfSpellCast(player, predicate))))
            { 
                addCandidate(player);
            }

            Pet* pet = player->GetPet();
            if (pet && CanHealPet(pet) && Check(pet))
            {
                health = pet->GetHealthPercent();
                if ((health < sPlayerbotAIConfig.almostFullHealth || NeedsFullHealingToRemoveAura(pet) || RemainingHealingAbsorb(pet)) &&
                    !IsTargetOfSpellCast(pet, predicate))
                {
                    addCandidate(pet);
                }
            }

            if (isTank && bot->IsInGroup(player))
            {
                tankTargets.push_back(player);
            }
        }
    }

    if (needHeals.empty() && tankTargets.empty())
    {
        return nullptr;
    }

    if (needHeals.empty() && !tankTargets.empty())
    {
        needHeals = tankTargets;
    }

    // Distribute healers within the most urgent health band. A second healer
    // must not be sent to a healthy tank while the only injured player waits.
    const auto urgency = [&](Unit* target) {
        if (target->GetHealthPercent() < sPlayerbotAIConfig.criticalHealth) return 0;
        if (double(forecast(target)) * 100.0 / target->GetMaxHealth() < sPlayerbotAIConfig.lowHealth) return 1;
        return 2;
    };
    std::map<Unit*, uint64> healingNeed;
    for (Unit* target : needHeals)
        healingNeed[target] = uint64(target->GetMaxHealth() - forecast(target)) + RemainingHealingAbsorb(target);
    std::stable_sort(needHeals.begin(), needHeals.end(), [&](Unit* u1, Unit* u2) {
        const int urgency1 = urgency(u1), urgency2 = urgency(u2);
        if (urgency1 != urgency2) return urgency1 < urgency2;
        return healingNeed.at(u1) > healingNeed.at(u2);
    });

    int healerIndex = 0;
    if (!partyMembers.empty())
    {
        for (Player* player : partyMembers)
        {
            if (!ai->IsSafe(player))
            {
                continue;
            }
            else if (player == bot)
            {
                break;
            }
            else if (player->IsAlive() && bot->IsInMap(player) && ai->IsHeal(player) && player->GetPlayerbotAI() && player->GetMaxPower(POWER_MANA))
            {
                float percent = (float)player->GetPower(POWER_MANA) / (float)player->GetMaxPower(POWER_MANA) * 100.0;
                if (percent > sPlayerbotAIConfig.lowMana)
                {
                    healerIndex++;
                }
            }
        }
    }
    else
    {
        healerIndex = 1;
    }

    const int mostUrgent = urgency(needHeals.front());
    const size_t sameUrgency = std::count_if(needHeals.begin(), needHeals.end(),
        [&](Unit* target) { return urgency(target) == mostUrgent; });
    healerIndex = healerIndex % sameUrgency;
    return needHeals[healerIndex];
}

bool PartyMemberToHeal::CanHealPet(Pet* pet)
{
    return MINI_PET != pet->getPetType();
}

bool PartyMemberToHeal::Check(Unit* player)
{
    const float maxDist = ai->GetRange("heal");

    if (!player || !bot->IsInWorld() || !player->IsInWorld() || !player->IsAlive() ||
        !player->GetMaxHealth() || !bot->IsInMap(player) || !sServerFacade.IsFriendlyTo(bot, player))
        return false;

    if (player->GetObjectGuid() == bot->GetObjectGuid())
        return false;

    if (player->IsPlayer() && static_cast<Player*>(player)->IsBeingTeleported())
        return false;

    if (player->GetMaxNegativeAuraModifier(SPELL_AURA_MOD_HEALING_PCT) <= -100 &&
        !UpcomingEncounterHealingWindow(bot, player))
        return false;
                                                     
    if (sServerFacade.GetDistance2d(bot, player) > maxDist)
        return false;

    return true;
}

std::vector<Player*> PartyMemberToHeal::GetPartyMembers()
{
    std::vector<Player*> partyMembers;
    if (ai->HasStrategy("focus heal targets", BotState::BOT_STATE_COMBAT))
    {
        const std::list<ObjectGuid> focusHealTargets = AI_VALUE(std::list<ObjectGuid>, "focus heal targets");
        for(const ObjectGuid& focusHealTarget : focusHealTargets)
        {
            Player* player = dynamic_cast<Player*>(ai->GetUnit(focusHealTarget));
            if (player && player->IsInGroup(bot) && ai->IsSafe(player))
            {
                partyMembers.push_back(player);
            }
        }
    }
    else
    {
        Group* group = bot->GetGroup();
        if (group)
        {
            for (GroupReference* gref = group->GetFirstMember(); gref; gref = gref->next())
            {
                Player* player = gref->getSource();
                if (player && ai->IsSafe(player))
                {
                    partyMembers.push_back(player);
                }
            }
        }
    }

    return partyMembers;
}

Unit* PartyMemberToProtect::Calculate()
{
    Group* group = bot->GetGroup();
    if (!group)
        return NULL;

    std::vector<Unit*> needProtect;

    std::list<ObjectGuid> attackers = ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible attack targets")->Get();
    for (std::list<ObjectGuid>::iterator i = attackers.begin(); i != attackers.end(); ++i)
    {
        Unit* unit = ai->GetUnit(*i);
        if (!unit)
            continue;

        bool isRanged = false;
        if (unit->AI())
        {
            if (unit->AI()->IsRangedUnit())
                isRanged = true;
        }

        Unit* pVictim = unit->GetVictim();
        if (!pVictim || !pVictim->IsPlayer())
            continue;

        Player* player = static_cast<Player*>(pVictim);
        if (pVictim == bot || !ai->IsSafe(player) || !player->IsInWorld() || !player->IsAlive() ||
            player->IsBeingTeleported() || !bot->IsInMap(player) || !bot->IsInGroup(player) ||
            !sServerFacade.IsFriendlyTo(bot, player) || player->duel)
            continue;

#ifdef MANGOSBOT_TWO
        if (!(bot->GetPhaseMask() & player->GetPhaseMask()))
            continue;
#endif

        if (sServerFacade.GetDistance2d(pVictim, bot) > 30.0f)
            continue;

        float attackDistance = isRanged ? 30.0f : 10.0f;
        if (sServerFacade.GetDistance2d(pVictim, unit) > attackDistance)
            continue;

        if (ai->IsTank((Player*)pVictim) && pVictim->GetHealthPercent() > 25)
            continue;
        else if ((ai->IsMelee((Player*)pVictim) || pVictim->getClass() != CLASS_HUNTER) && pVictim->GetHealthPercent() > 50)
            continue;

        if (find(needProtect.begin(), needProtect.end(), pVictim) == needProtect.end())
            needProtect.push_back(pVictim);
    }

    if (needProtect.empty())
        return NULL;

    sort(needProtect.begin(), needProtect.end(), compareByHealth);

    return needProtect[0];
}

Unit* PartyMemberToRemoveRoots::Calculate()
{
    Unit* target = nullptr;
    Group* group = bot->GetGroup();
    if(group)
    {
        for (GroupReference* gref = group->GetFirstMember(); gref; gref = gref->next())
        {
            Player* player = gref->getSource();
            if (sServerFacade.IsAlive(player))
            {
                if (player->duel && player->duel->opponent)
                    continue;

                if (player->HasAuraType(SPELL_AURA_MOD_ROOT) || player->HasAuraType(SPELL_AURA_MOD_DECREASE_SPEED))
                {
                    if (!ai->HasAura("stealth", player) && !ai->HasAura("prowl", player) && !ai->HasAura("tree of life", player))
                    {
                        target = player;
                        break;
                    }
                }
            }
        }
    }

    return target;
}
