#include "playerbot/playerbot.h"
#include "GluthRoleActions.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

namespace
{
    bool GluthMember(Player* bot, Player* member)
    {
        return member && member->IsInWorld() && member->IsAlive() && bot->IsInMap(member) &&
            member->GetGroup() == bot->GetGroup() && !member->IsBeingTeleported() && !member->HasCharmer();
    }
    bool GluthReady(PlayerbotAI* ai, Unit* boss)
    {
        Player* bot = ai->GetBot();
        return bot->IsInWorld() && bot->IsAlive() && bot->GetMapId() == 533 && bot->GetGroup() &&
            !bot->IsBeingTeleported() && !bot->HasCharmer() && !ai->IsRealPlayer() &&
            boss && boss->GetEntry() == 15932 && boss->IsInWorld() && boss->IsAlive() &&
            bot->IsInMap(boss) && !boss->HasCharmer() && boss->IsInCombat();
    }
    unsigned GluthWounds(Player* player)
    {
#ifdef MANGOSBOT_TWO
        const auto* holder = player->GetSpellAuraHolder(54378);
#else
        const auto* holder = player->GetSpellAuraHolder(25646);
#endif
        return holder ? holder->GetStackAmount() : 0;
    }
    bool GluthCanTaunt(PlayerbotAI* brain, Unit* boss, Player* holder)
    {
        // Election and execution both use native readiness. An unavailable
        // low-GUID tank must not exclude another tank whose taunt is ready.
        for (const char* spell : {"taunt", "growl", "hand of reckoning", "dark command"})
            if (brain->CanCastSpell(spell, boss, 0)) return true;
        return brain->CanCastSpell("righteous defense", holder, 0);
    }
}

Player* ai::GluthKiter(PlayerbotAI* ai, Unit* boss)
{
    if (!GluthReady(ai, boss)) return nullptr;
    Player* bot = ai->GetBot();
    std::vector<Player*> tanks;
    std::vector<Player*> members;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!GluthMember(bot, member)) continue;
        members.push_back(member);
        if (ai->IsTank(member)) tanks.push_back(member);
    }
    const auto order = [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); };
    std::sort(tanks.begin(), tanks.end(), order);
    std::sort(members.begin(), members.end(), order);
    // A human actively fighting the native chow that pursues them has already
    // taken this duty. Merely being attacked (e.g. a healer) is not an assignment.
    for (Player* member : members)
    {
        PlayerbotAI* brain = member->GetPlayerbotAI();
        if ((brain && !brain->IsRealPlayer()) || ai->IsHeal(member)) continue;
        Unit* chow = member->GetVictim();
        if (!chow || chow->GetEntry() != 16360 || !chow->IsInWorld() || !chow->IsAlive() ||
            !member->IsInMap(chow) || chow->HasCharmer() || chow->GetVictim() != member ||
            chow->GetUInt32Value(UNIT_CREATED_BY_SPELL) != 28217 || chow->GetHealthPercent() <= 5.1f) continue;
        Unit* source = ai->GetUnit(chow->GetSpawnerGuid());
        if (source && source->GetEntry() == 15384 && source->IsInWorld() && member->IsInMap(source) &&
            source->GetDistance(boss) < 100) return member;
    }
    if (tanks.size() >= 3) return tanks[2]; // Preserve established larger-raid assignments.
#ifdef MANGOSBOT_TWO
    if (!bot->GetMap()->IsRegularDifficulty()) return nullptr;
    // Native10 has only one chow per wave. Reserve both tanks for Mortal Wound
    // relief and use a bot ranged slower when a third tank is not available.
    for (unsigned preferred : {CLASS_HUNTER, CLASS_MAGE})
        for (Player* member : members)
        {
            PlayerbotAI* brain = member->GetPlayerbotAI();
            if (!brain || brain->IsRealPlayer() || member->GetCharm() || ai->IsTank(member) || ai->IsHeal(member) ||
                member->getClass() != preferred || boss->GetVictim() == member ||
                member->hasUnitState(UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL)) continue;
            if (brain->HasSpell(preferred == CLASS_HUNTER ? "concussive shot" : "frostbolt")) return member;
        }
#endif
    return nullptr;
}

bool ai::GluthTankRelief(PlayerbotAI* ai, Unit* boss)
{
    if (!GluthReady(ai, boss)) return false;
    Player* bot = ai->GetBot();
    Unit* victim = boss->GetVictim();
    if (!victim || !victim->IsPlayer()) return false;
    Player* holder = static_cast<Player*>(victim);
    if (!GluthMember(bot, holder) || !ai->IsTank(holder) || GluthWounds(holder) < 4) return false;
    Player* kiter = GluthKiter(ai, boss);
    Player* selected = nullptr;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* tank = ref->getSource();
        if (!GluthMember(bot, tank) || tank == holder || tank == kiter || !ai->IsTank(tank) ||
            tank->GetCharm() || tank->hasUnitState(UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL) || GluthWounds(tank) > 1) continue;
        PlayerbotAI* brain = tank->GetPlayerbotAI();
        if (!brain || brain->IsRealPlayer() || tank->IsNonMeleeSpellCasted(false) || !GluthCanTaunt(brain, boss, holder)) continue;
        if (!selected || GluthWounds(tank) < GluthWounds(selected) ||
            (GluthWounds(tank) == GluthWounds(selected) && tank->GetObjectGuid() < selected->GetObjectGuid())) selected = tank;
    }
    return selected == bot;
}
