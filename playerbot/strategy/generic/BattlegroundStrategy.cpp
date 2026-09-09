
#include "playerbot/playerbot.h"
#include "playerbot/ServerFacade.h"
#include "BattlegroundStrategy.h"
#include "playerbot/strategy/Multiplier.h"
#include "playerbot/strategy/actions/MovementActions.h"
#include "playerbot/strategy/values/PvpValues.h"
#include "playerbot/strategy/actions/GenericSpellActions.h"
#include "playerbot/strategy/actions/AttackAction.h"

using namespace ai;

void BGStrategy::InitNonCombatTriggers(std::list<TriggerNode*> &triggers)
{
    triggers.push_back(new TriggerNode(
        "random",
        NextAction::array(0, new NextAction("bg join", relevance), NULL)));

    triggers.push_back(new TriggerNode(
        "bg invite active",
        NextAction::array(0, new NextAction("bg status check", relevance), NULL)));
}

void BattlegroundStrategy::InitNonCombatTriggers(std::list<TriggerNode*> &triggers)
{
    triggers.push_back(new TriggerNode(
        "bg waiting",
        NextAction::array(0, new NextAction("bg move to start", 1.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "player has flag",
        NextAction::array(0, new NextAction("jump::position bg objective", 3.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "bg active",
        NextAction::array(0, new NextAction("check mount state", 2.0f), new NextAction("bg move to objective", 1.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "very often",
        NextAction::array(0, new NextAction("bg check objective", 10.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "bg active",
        NextAction::array(0, new NextAction("bg check flag", ACTION_HIGH), NULL)));

    triggers.push_back(new TriggerNode(
        "bg ended",
        NextAction::array(0, new NextAction("bg leave", ACTION_HIGH), NULL)));

    /*triggers.push_back(new TriggerNode(
        "enemy flagcarrier near",
        NextAction::array(0, new NextAction("attack enemy flag carrier", 80.0f), NULL)));*/

    /*triggers.push_back(new TriggerNode(
        "team flagcarrier near",
        NextAction::array(0, new NextAction("bg protect fc", 40.0f), NULL)));*/

    /*triggers.push_back(new TriggerNode(
        "player has flag",
        NextAction::array(0, new NextAction("bg move to objective", 90.0f), NULL)));*/
}

void WarsongStrategy::InitNonCombatTriggers(std::list<TriggerNode*> &triggers)
{
    triggers.push_back(new TriggerNode("bg active",
        NextAction::array(0, new NextAction("bg move to objective", ACTION_MOVE + 5), NULL)));

    triggers.push_back(new TriggerNode(
        "bg active",
        NextAction::array(0, new NextAction("bg check flag", 70.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "often",
        NextAction::array(0, new NextAction("bg use buff", 30.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "low health",
        NextAction::array(0, new NextAction("bg use buff", 30.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "low mana",
        NextAction::array(0, new NextAction("bg use buff", 30.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "enemy flagcarrier near",
        NextAction::array(0, new NextAction("attack enemy flag carrier", 80.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "player has flag",
        NextAction::array(0,
            new NextAction("jump::position bg objective", ACTION_MOVE + 5.5f),
            new NextAction("bg move to objective", ACTION_MOVE + 5),
            NULL)));

    triggers.push_back(new TriggerNode(
        "player has flag",
        NextAction::array(0, new NextAction("rocket boots", ACTION_INTERRUPT + 5), NULL)));

    triggers.push_back(new TriggerNode(
        "very often",
        NextAction::array(0, new NextAction("bg banner", 10.0f), NULL)));
}

void WarsongStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    InitNonCombatTriggers(triggers);
}

void AlteracStrategy::InitNonCombatTriggers(std::list<TriggerNode*> &triggers)
{
}

void AlteracStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode(
        "very often",
        NextAction::array(0, new NextAction("bg banner", ACTION_NORMAL), NULL)));
}

void ArathiStrategy::InitNonCombatTriggers(std::list<TriggerNode*> &triggers)
{
    triggers.push_back(new TriggerNode(
        "bg active",
        NextAction::array(0, new NextAction("bg check flag", 70.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "often",
        NextAction::array(0, new NextAction("bg use buff", 30.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "low health",
        NextAction::array(0, new NextAction("bg use buff", 30.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "low mana",
        NextAction::array(0, new NextAction("bg use buff", 30.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "very often",
        NextAction::array(0, new NextAction("bg banner", 10.0f), NULL)));
}

void ArathiStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    InitNonCombatTriggers(triggers);
}

void EyeStrategy::InitNonCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode(
        "bg active",
        NextAction::array(0, new NextAction("bg check flag", 70.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "often",
        NextAction::array(0, new NextAction("bg use buff", 30.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "low health",
        NextAction::array(0, new NextAction("bg use buff", 30.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "low mana",
        NextAction::array(0, new NextAction("bg use buff", 30.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "enemy flagcarrier near",
        NextAction::array(0, new NextAction("attack enemy flag carrier", 80.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "player has flag",
        NextAction::array(0, new NextAction("bg move to objective", 80.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "player has flag",
        NextAction::array(0, new NextAction("rocket boots", 81.0f), NULL)));
}

void EyeStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    InitNonCombatTriggers(triggers);
}

void IsleStrategy::InitNonCombatTriggers(std::list<TriggerNode*>& triggers)
{
    triggers.push_back(new TriggerNode(
        "bg active",
        NextAction::array(0, new NextAction("bg check flag", 70.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "timer",
        NextAction::array(0, new NextAction("enter vehicle", 85.0f), NULL)));

    /*triggers.push_back(new TriggerNode(
        "random",
        NextAction::array(0, new NextAction("leave vehicle", 80.0f), NULL)));*/

    triggers.push_back(new TriggerNode(
        "in vehicle",
        NextAction::array(0, new NextAction("hurl boulder", 70.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "in vehicle",
        NextAction::array(0, new NextAction("fire cannon", 70.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "in vehicle",
        NextAction::array(0, new NextAction("napalm", 70.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "enemy is close",
        NextAction::array(0, new NextAction("steam blast", 80.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "in vehicle",
        NextAction::array(0, new NextAction("ram", 70.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "enemy is close",
        NextAction::array(0, new NextAction("ram", 79.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "enemy out of melee",
        NextAction::array(0, new NextAction("steam rush", 81.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "in vehicle",
        NextAction::array(0, new NextAction("incendiary rocket", 70.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "in vehicle",
        NextAction::array(0, new NextAction("rocket blast", 70.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "in vehicle",
        NextAction::array(0, new NextAction("blade salvo", 71.0f), NULL)));

    triggers.push_back(new TriggerNode(
        "in vehicle",
        NextAction::array(0, new NextAction("glaive throw", 70.0f), NULL)));
}

void IsleStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    InitNonCombatTriggers(triggers);
}

void ArenaStrategy::InitNonCombatTriggers(std::list<TriggerNode*> &triggers)
{
    triggers.push_back(new TriggerNode(
        "no possible targets",
        NextAction::array(0, new NextAction("arena tactics", 1.0f), NULL)));
}

void ArenaStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    InitNonCombatTriggers(triggers);
}

namespace
{
    class WarsongObjectiveMultiplier : public Multiplier
    {
    public:
        WarsongObjectiveMultiplier(PlayerbotAI* ai) : Multiplier(ai, "warsong objective") {}
        float GetValue(Action* action) override
        {
            if (!action || ActualBattlegroundType(bot) != BATTLEGROUND_WS) return 1.0f;
            if (ai->HasRealPlayerMaster()) return 1.0f;
            const bool advance = ShouldAdvanceWarsongObjective(ai);
            if (JumpAction* jump = dynamic_cast<JumpAction*>(action))
                if (jump->getQualifier() == "position bg objective" && !advance) return 0.0f;
            const std::string& name = action->getName();
            const WarsongObjective objective = AI_VALUE(WarsongObjective, "warsong objective");
            Unit* preferred = AI_VALUE(Unit*, "enemy player target");
            // Assist strategies must not undo the same automatic target choice
            // used by normal PvP and flag-carrier attacks.
            if ((name == "dps assist" || name == "tank assist") && preferred && action->GetTarget() != preferred)
                return 0.0f;
            if (!advance) return 1.0f;
            if (objective.carrying)
            {
                // Keep existing hostile selections from reopening pursuit after
                // pickup. Friendly healing approaches and native escape checks
                // are preserved. Generic fleeing must not replace the home route.
                if (dynamic_cast<AttackAction*>(action) || name == "reach melee" || name == "reach spell" ||
                    name == "set behind" || name == "flee") return 0.0f;
                if (JumpAction* jump = dynamic_cast<JumpAction*>(action))
                    if (jump->getQualifier() == "chase") return 0.0f;
                if (CastSpellAction* cast = dynamic_cast<CastSpellAction*>(action))
                {
                    const SpellEntry* spell = sServerFacade.LookupSpellInfo(cast->GetDecisionSpellId());
                    if (spell && !IsPositiveSpell(spell, bot, action->GetTarget()))
                    {
                        // Instant control can help escape; damage casts and
                        // charges toward enemies cannot override carrying home.
                        bool control = IsSpellHaveEffect(spell, SPELL_EFFECT_INTERRUPT_CAST);
                        for (unsigned i = 0; i < MAX_EFFECT_INDEX; ++i)
                            control = control || spell->EffectApplyAuraName[i] == SPELL_AURA_MOD_DECREASE_SPEED ||
                                spell->EffectApplyAuraName[i] == SPELL_AURA_MOD_ROOT ||
                                spell->EffectApplyAuraName[i] == SPELL_AURA_MOD_STUN ||
                                spell->EffectApplyAuraName[i] == SPELL_AURA_MOD_FEAR ||
                                spell->EffectApplyAuraName[i] == SPELL_AURA_MOD_CONFUSE ||
                                spell->EffectApplyAuraName[i] == SPELL_AURA_MOD_SILENCE;
                        Unit* target = action->GetTarget();
                        const bool pressure = target == bot ? objective.pressured : IsWarsongLocalThreat(ai, target, bot);
                        if (!control || !pressure || GetSpellCastTime(spell, bot) || IsChanneledSpell(spell) ||
                            cast->HasMovementEffect()) return 0.0f;
                        const float relevance = action->getRelevance();
                        return relevance > 0 && relevance < ACTION_INTERRUPT ? ACTION_INTERRUPT / relevance : 1.0f;
                    }
                }
            }
            // Let native-legal mobility/support precede travel without outranking
            // urgent heals. Never promote Cheetah into incoming pressure.
            if (name == "sprint" || name == "dash" || name == "travel form" || name == "ghost wolf" ||
                (name == "aspect of the cheetah" && !objective.pressured))
            {
                const float relevance = action->getRelevance();
                return relevance > 0 && relevance < ACTION_INTERRUPT ? ACTION_INTERRUPT / relevance : 1.0f;
            }
            if (name == "attack enemy player" || name == "attack enemy flag carrier" ||
                name == "dps assist" || name == "tank assist")
            {
                Unit* target = action->GetTarget();
                if (target && target->GetObjectGuid() == objective.target && objective.goal == WarsongGoal::Intercept)
                    return 1.0f;
                return 0.0f;
            }
            // Healing, dispels, interrupts, consumables and self-defense retain
            // their normal checks; movement priority beats ordinary damage.
            return 1.0f;
        }
    };
}

void WarsongStrategy::InitCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new WarsongObjectiveMultiplier(ai));
}

void WarsongStrategy::InitNonCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new WarsongObjectiveMultiplier(ai));
}
