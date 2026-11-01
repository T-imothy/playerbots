#include "playerbot/playerbot.h"
#include "EncounterSpellPolicy.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/ServerFacade.h"
#include "playerbot/PlayerbotAIConfig.h"

bool ai::NeedsMoltenCoreBurstHealing(PlayerbotAI* ai, Unit* target)
{
    Player* bot = ai->GetBot();
    if (!bot || !target || !bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 409 || !bot->GetGroup() || ai->IsRealPlayer() ||
        !target->IsPlayer() || !target->IsInWorld() || !target->IsAlive() || target->HasCharmer() ||
        !bot->IsInMap(target) || !target->GetMaxHealth() || target->GetHealth() >= target->GetMaxHealth() ||
        !sServerFacade.IsFriendlyTo(bot, target)) return false;
    Player* tank = static_cast<Player*>(target);
    if (tank->IsBeingTeleported() || tank->duel || tank->GetGroup() != bot->GetGroup() || !ai->IsTank(tank)) return false;
    // Native victim changes, not a remembered controller/marker, identify the
    // threatened tank. Existing party admission and native casts retain range,
    // LOS, resources, immunity and GCD checks.
    for (Unit* attacker : tank->getAttackers())
        if (attacker && attacker->IsInWorld() && attacker->IsAlive() && attacker->IsInCombat() &&
            !attacker->HasCharmer() && attacker->GetEntry() == 11666 && bot->IsInMap(attacker) &&
            attacker->GetVictim() == tank && !sServerFacade.IsFriendlyTo(bot, attacker)) return true;
    return false;
}

bool ai::NeedsSapphironSelfHealing(PlayerbotAI* ai)
{
#ifdef MANGOSBOT_ZERO
    Player* bot=ai?ai->GetBot():nullptr;
    if (!bot || bot->GetMapId()!=533 || !bot->IsInWorld() || !bot->IsAlive() ||
        !bot->IsInCombat() || bot->IsBeingTeleported() || bot->HasCharmer() || bot->duel ||
        !bot->GetGroup() || ai->IsRealPlayer() || !ai->IsHeal(bot) ||
        ai->HasStrategy("focus heal targets",BotState::BOT_STATE_COMBAT) ||
        !bot->GetMaxHealth() || bot->GetHealthPercent()>=sPlayerbotAIConfig.criticalHealth ||
        !bot->GetPower(POWER_MANA) || bot->GetMaxNegativeAuraModifier(SPELL_AURA_MOD_HEALING_PCT)<=-100) return false;
    // Sustained native Frost Aura made party-critical heals/shields win over
    // equally urgent self healing until a priest died with mana remaining.
    // Select self for the existing learned party heal actions, without changing
    // their priorities, native spell admission, or interrupting an active cast.
    const SpellAuraHolder* aura=bot->GetSpellAuraHolder(28531);
    Unit* boss=aura?aura->GetCaster():nullptr;
    return boss && boss->IsInWorld() && boss->IsAlive() && bot->IsInMap(boss) &&
        boss->GetEntry()==15989 && boss->IsInCombat() && !boss->HasCharmer() &&
        !sServerFacade.IsFriendlyTo(bot,boss);
#else
    return false;
#endif
}

bool ai::NeedsNaxxramasTankHealing(PlayerbotAI* ai, Unit* target)
{
#ifdef MANGOSBOT_ZERO
    Player* bot=ai->GetBot();
    if (!bot || bot->GetMapId()!=533 || !bot->IsInWorld() || !bot->IsAlive() ||
        !bot->IsInCombat() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        !bot->GetGroup() || ai->IsRealPlayer() || !ai->IsHeal(bot) ||
        ai->HasStrategy("focus heal targets",BotState::BOT_STATE_COMBAT) ||
        !target || !target->IsPlayer() || !target->IsInWorld() || !target->IsAlive() ||
        !bot->IsInMap(target) || target->HasCharmer() || !target->GetMaxHealth() ||
        target->GetHealth()>=target->GetMaxHealth() || !sServerFacade.IsFriendlyTo(bot,target)) return false;
    Player* tank=static_cast<Player*>(target);
    if (!ai->IsTank(tank) || tank->GetGroup()!=bot->GetGroup() || tank->IsBeingTeleported() || tank->duel) return false;
    bool held=false;
    for (Unit* enemy:tank->getAttackers())
        if (enemy && (enemy->GetEntry()==15989 || enemy->GetEntry()==15953) && enemy->IsInWorld() && enemy->IsAlive() &&
            bot->IsInMap(enemy) && enemy->IsInCombat() && !enemy->HasCharmer() &&
            enemy->GetVictim()==tank && (enemy->GetEntry()!=15989 || !enemy->HasAura(18430)) && enemy->CanReachWithMeleeAttack(tank) &&
            !sServerFacade.IsFriendlyTo(bot,enemy)) {held=true;break;}
    if (!held) return false;
    // Native traces: Sapphiron's Frost Aura and Faerlina's raid damage sent healers away from the
    // current tank after a synchronized overheal. Reserve a bounded minority
    // on the actual holder. Other healers retain ordinary raid triage; a
    // healer's own critical health, explicit focus orders and native spell
    // admission still take precedence.
    std::vector<Player*> healers;
    for (GroupReference* ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next())
    {
        Player* healer=ref->getSource();
        if (!healer || !healer->IsInWorld() || !healer->IsAlive() || !bot->IsInMap(healer) ||
            healer->HasCharmer() || healer->IsBeingTeleported() || healer->duel ||
            healer->GetGroup()!=bot->GetGroup() || !ai->IsHeal(healer) ||
            !healer->GetPlayerbotAI() || healer->GetPlayerbotAI()->IsRealPlayer() ||
            healer->GetPlayerbotAI()->HasStrategy("focus heal targets",BotState::BOT_STATE_COMBAT) ||
            healer->GetHealthPercent()<sPlayerbotAIConfig.criticalHealth || !healer->GetMaxPower(POWER_MANA) ||
            float(healer->GetPower(POWER_MANA))*100/healer->GetMaxPower(POWER_MANA)<=sPlayerbotAIConfig.lowMana ||
            healer->GetDistance(tank)>healer->GetPlayerbotAI()->GetRange("heal") || !healer->IsWithinLOSInMap(tank)) continue;
        healers.push_back(healer);
    }
    std::sort(healers.begin(),healers.end(),[](Player* a,Player* b){return a->GetObjectGuid()<b->GetObjectGuid();});
    const size_t reserved=std::min(size_t(3),(healers.size()+3)/4);
    return std::find(healers.begin(),healers.begin()+reserved,bot)!=healers.begin()+reserved;
#else
    return false;
#endif
}

bool ai::NeedsRaidObjectiveHealing(Unit* target)
{
#ifdef MANGOSBOT_TWO
    return target && target->IsInWorld() && target->IsAlive() && target->IsInCombat() &&
        !target->HasCharmer() && target->GetMapId() == 631 && target->GetEntry() == 36789 &&
        target->GetMaxHealth() && target->GetHealth() < target->GetMaxHealth();
#else
    return false;
#endif
}

Unit* ai::FindRaidHealingObjective(PlayerbotAI* ai)
{
#ifdef MANGOSBOT_TWO
    Player* bot = ai->GetBot();
    if (!bot || bot->GetMapId() != 631 || !bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() ||
        bot->HasCharmer() || bot->IsBeingTeleported() || !bot->GetGroup() || ai->IsRealPlayer() ||
        !ai->IsHeal(bot) || ai->HasStrategy("focus heal targets", BotState::BOT_STATE_COMBAT)) return nullptr;
    Unit* objective = nullptr;
    for (const auto& guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets", "100:1")->Get())
    {
        Unit* unit = ai->GetUnit(guid);
        if (!NeedsRaidObjectiveHealing(unit) || !bot->IsInMap(unit) ||
            !sServerFacade.IsFriendlyTo(bot, unit) || bot->GetDistance(unit) > ai->GetRange("heal")) continue;
        if (objective && objective != unit) return nullptr;
        objective = unit;
    }
    if (!objective) return nullptr;

    // Keep one available bot healer on the raid when there are several. Prefer
    // the least-buffed healer for that role, so native Dream stacks contribute
    // to the objective. Read native player state, not another bot's AI values.
    Player* raidHealer = nullptr;
    uint32 leastStacks = 0;
    unsigned count = 0;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* healer = ref->getSource();
        if (!healer || !healer->IsInWorld() || !healer->IsAlive() || !bot->IsInMap(healer) ||
            healer->HasCharmer() || healer->IsBeingTeleported() || healer->GetGroup() != bot->GetGroup() ||
            !healer->GetPlayerbotAI() || healer->GetPlayerbotAI()->IsRealPlayer() || !ai->IsHeal(healer) ||
            !healer->GetPower(POWER_MANA) || healer->GetDistance(objective) > ai->GetRange("heal")) continue;
        uint32 stacks = 0;
        for (uint32 id : {70873u, 71941u})
            if (const SpellAuraHolder* aura = healer->GetSpellAuraHolder(id)) stacks += aura->GetStackAmount();
        ++count;
        if (!raidHealer || stacks < leastStacks ||
            (stacks == leastStacks && healer->GetObjectGuid() < raidHealer->GetObjectGuid()))
        {
            raidHealer = healer;
            leastStacks = stacks;
        }
    }
    if (!count || !bot->GetPower(POWER_MANA) || (count > 1 && raidHealer == bot)) return nullptr;
    return objective;
#else
    return nullptr;
#endif
}
