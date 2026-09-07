#include "playerbot/playerbot.h"
#include "EncounterSpellPolicy.h"

namespace
{
    struct TankSwapRule
    {
        uint32 auras[4] = {};
        uint32 stacks = 1;
        uint32 bossAura = 0;
    };

    bool EncounterTankRule(Player* bot, Unit* enemy, TankSwapRule& rule)
    {
        if (!enemy) return false;
        switch (bot->GetMapId())
        {
            case 509:
                if (enemy->GetEntry() == 15348) { rule = {{25646}, 3}; return true; }
                break;
            case 531:
                if (enemy->GetEntry() == 15510) { rule = {{25646}, 3}; return true; }
                break;
            case 469:
                if (enemy->GetEntry() == 14601) { rule = {{23340}, 1}; return true; }
                break;
            case 533:
                if (enemy->GetEntry() == 15932)
                {
#ifdef MANGOSBOT_TWO
                    rule = {{54378}, 3};
#else
                    rule = {{25646}, 3};
#endif
                    return true;
                }
                break;
#ifndef MANGOSBOT_ZERO
            case 568:
                // Mangle matters to the incoming bear's bleeds. Do not swap
                // every time troll form reapplies it to the same tank.
                if (enemy->GetEntry() == 23576) { rule = {{42389}, 1, 42377}; return true; }
                break;
#endif
#ifdef MANGOSBOT_TWO
            case 603:
                switch (enemy->GetEntry())
                {
                    case 32865: rule = {{62130}, 1}; return true;
                    case 32871: rule = {{64412}, 4}; return true; // fifth punch phases the tank
                    case 32930:
                        rule = enemy->GetMap()->IsRegularDifficulty() ?
                            TankSwapRule{{63355}, 1} : TankSwapRule{{64002}, 2};
                        return true;
                }
                break;
            case 649:
                if (enemy->GetEntry() == 34796) { rule = {{66331, 67477, 67478, 67479}, 2}; return true; }
                break;
            case 631:
                if (enemy->GetEntry() == 37813) { rule = {{72410}, 1}; return true; }
                // Native Gastric Bloat detonates on the tenth application.
                // Eight leaves one application of headroom for a failed taunt.
                if (enemy->GetEntry() == 36626) { rule = {{72219, 72551, 72552, 72553}, 8}; return true; }
                break;
#endif
        }
        return false;
    }

    Player* EncounterTank(PlayerbotAI* ai, Unit* enemy, TankSwapRule& rule)
    {
        Player* bot = ai->GetBot();
        if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
            ai->IsRealPlayer() || !bot->GetGroup() || !enemy || !enemy->IsInWorld() || !enemy->IsAlive() ||
            !enemy->IsInCombat() || enemy->HasCharmer() || !bot->IsInMap(enemy) ||
            !EncounterTankRule(bot, enemy, rule)) return nullptr;
        Unit* victim = enemy->GetVictim();
        if (!victim || !victim->IsPlayer() || !victim->IsInWorld() || !victim->IsAlive() ||
            victim->HasCharmer() || !bot->IsInMap(victim)) return nullptr;
        Player* tank = static_cast<Player*>(victim);
        return tank->GetGroup() == bot->GetGroup() && !tank->IsBeingTeleported() && ai->IsTank(tank) ? tank : nullptr;
    }

    bool CleanTank(Player* tank, const TankSwapRule& rule)
    {
        for (uint32 aura : rule.auras)
            if (aura && tank->HasAura(aura)) return false;
        return true;
    }

    bool HasReadyTaunt(Player* tank)
    {
        const uint32 taunts[] = {355, 6795,
#ifndef MANGOSBOT_ZERO
            31789,
#endif
#ifdef MANGOSBOT_TWO
            62124, 56222,
#endif
        };
        for (uint32 spell : taunts)
            if (tank->HasSpell(spell) && tank->IsSpellReady(spell)) return true;
        return false;
    }
}

bool ai::ShouldSwapEncounterTank(PlayerbotAI* ai, Unit* enemy)
{
    TankSwapRule rule;
    Player* tank = EncounterTank(ai, enemy, rule);
    Player* bot = ai->GetBot();
    if (!tank || tank == bot || !ai->IsTank(bot) || !CleanTank(bot, rule) ||
        (rule.bossAura && !enemy->HasAura(rule.bossAura))) return false;
    bool needsSwap = false;
    for (uint32 aura : rule.auras)
        if (aura)
            if (const SpellAuraHolder* holder = tank->GetSpellAuraHolder(aura, enemy->GetObjectGuid()))
                needsSwap |= holder->GetStackAmount() >= rule.stacks;
    if (!needsSwap) return false;

    // One eligible bot owns the attempt. No threat edits, assumed hits or
    // timer-based debuff expiry: native learned taunts perform the swap.
    Player* selected = nullptr;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!member || member == tank || !member->IsInWorld() || !member->IsAlive() ||
            !bot->IsInMap(member) || member->GetGroup() != bot->GetGroup() ||
            member->IsBeingTeleported() || member->HasCharmer() || !member->GetPlayerbotAI() ||
            member->GetPlayerbotAI()->IsRealPlayer() || !ai->IsTank(member) ||
            !CleanTank(member, rule) || !HasReadyTaunt(member) || !member->CanReachWithMeleeAttack(enemy)) continue;
        if (!selected || member->GetObjectGuid() < selected->GetObjectGuid()) selected = member;
    }
    return selected == bot;
}

bool ai::ShouldAvoidEncounterTaunt(PlayerbotAI* ai, const SpellEntry* spell, Unit* enemy)
{
    TankSwapRule rule;
    if (!spell || !EncounterTank(ai, enemy, rule)) return false;
    bool taunt = false;
    for (unsigned effect = 0; effect < MAX_EFFECT_INDEX; ++effect)
        taunt |= spell->Effect[effect] == SPELL_EFFECT_ATTACK_ME ||
            (spell->Effect[effect] == SPELL_EFFECT_APPLY_AURA && spell->EffectApplyAuraName[effect] == SPELL_AURA_MOD_TAUNT);
    // Recheck at actual dispatch, after another tank may already have landed
    // its taunt. Do not bounce the boss back to an afflicted/previous tank.
    return taunt && !ShouldSwapEncounterTank(ai, enemy);
}
