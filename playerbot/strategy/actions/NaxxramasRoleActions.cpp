#include "playerbot/playerbot.h"
#include "NaxxramasRoleActions.h"
#include "ClassicRaidActions.h"
#include "GenericSpellActions.h"
#include "playerbot/ServerFacade.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"
#include "playerbot/strategy/NaxxramasNativePolicy.h"
#include "AI/ScriptDevAI/include/sc_instance.h"
#include "Combat/ThreatManager.h"

using namespace ai;

namespace
{
    bool Ready(PlayerbotAI* ai)
    {
        Player* bot = ai->GetBot();
        return bot->GetMapId() == 533 && bot->IsInWorld() && bot->IsAlive() &&
            bot->IsInCombat() && !bot->HasCharmer() && !bot->IsBeingTeleported() &&
            bot->GetGroup() && !ai->IsRealPlayer() && ai->HasStrategy("dungeon", BotState::BOT_STATE_COMBAT);
    }
    std::vector<Player*> Members(PlayerbotAI* ai, bool tanks = false)
    {
        Player* bot = ai->GetBot();
        std::vector<Player*> members;
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (member && member->IsInWorld() && member->IsAlive() && !member->HasCharmer() &&
                !member->IsBeingTeleported() && bot->IsInMap(member) && member->GetGroup() == bot->GetGroup() &&
                (!tanks || ai->IsTank(member))) members.push_back(member);
        }
        std::sort(members.begin(), members.end(), [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        return members;
    }
    std::vector<Unit*> Enemies(PlayerbotAI* ai)
    {
        std::vector<Unit*> enemies;
        for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets", "100:1")->Get())
            if (Unit* unit = ai->GetUnit(guid))
                if (NaxxramasEncounterEngaged(ai->GetBot(), unit)) enemies.push_back(unit);
        std::sort(enemies.begin(), enemies.end(), [](Unit* a, Unit* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        return enemies;
    }
    Unit* Find(const std::vector<Unit*>& enemies, uint32 entry)
    {
        for (Unit* unit : enemies) if (unit->GetEntry() == entry) return unit;
        return nullptr;
    }
    bool Attackable(PlayerbotAI* ai, Unit* enemy)
    {
        return enemy && PossibleAttackTargetsValue::IsValid(enemy, ai->GetBot(), sPlayerbotAIConfig.sightDistance, false, true) &&
            !PossibleAttackTargetsValue::HasBreakableCC(enemy, ai->GetBot()) &&
            !PossibleAttackTargetsValue::HasUnBreakableCC(enemy, ai->GetBot());
    }
    bool Regular(PlayerbotAI* ai)
    {
#ifdef MANGOSBOT_TWO
        return ai->GetBot()->GetMap()->IsRegularDifficulty();
#else
        return true;
#endif
    }
    unsigned HatefulSlots(PlayerbotAI* ai)
    {
#ifdef MANGOSBOT_TWO
        return Regular(ai) ? 2u : 3u;
#else
        return 4u;
#endif
    }
    // The native primer considers only these first threat slots and then picks
    // the highest current health in melee. Merely standing nearby is insufficient.
    bool HatefulReady(PlayerbotAI* ai, Unit* boss, const std::vector<Player*>& tanks)
    {
        const unsigned required = HatefulSlots(ai);
        if (tanks.size() < required || !boss->GetVictim()) return false;
        unsigned checked = 0;
        for (auto* reference : boss->getThreatManager().getThreatList())
        {
            Unit* target = reference->getTarget();
            if (checked >= required) break;
            if (!target || !target->IsPlayer() || !ai->IsTank(static_cast<Player*>(target)) ||
                std::find(tanks.begin(), tanks.end(), target) == tanks.end() ||
                boss->getThreatManager().getThreat(target) <= 0.0f || !boss->CanReachWithMeleeAttack(target)) return false;
            ++checked;
        }
        return checked == required;
    }
    void Anchor(PlayerbotAI* ai, Unit* boss, ClassicRaidPlan& plan, uint32 mechanic)
    {
        plan.boss = boss->GetObjectGuid();
        plan.position.map = ai->GetBot()->GetMapId();
        plan.position.instance = ai->GetBot()->GetInstanceId();
        plan.position.boss = boss->GetObjectGuid();
        plan.position.source = boss->GetObjectGuid();
        plan.position.spell = mechanic;
    }
    bool MeleePosition(PlayerbotAI* ai, Unit* boss, ClassicRaidPlan& plan, unsigned slot)
    {
        Player* bot = ai->GetBot();
        if (boss->CanReachWithMeleeAttack(bot)) return true;
        const float distance = std::max(2.0f, boss->GetCombatReach() + bot->GetCombatReach() - 1.0f);
        for (unsigned attempt = 0; attempt < 8; ++attempt)
        {
            const float angle = boss->GetOrientation() + M_PI_F + (float(slot % 3) - 1.0f) * 0.45f +
                (attempt % 2 ? 1.0f : -1.0f) * float(attempt / 2) * 0.3f;
            plan.position.destination = {boss->GetPositionX() + distance * std::cos(angle),
                boss->GetPositionY() + distance * std::sin(angle), boss->GetPositionZ()};
            if (ValidateEncounterDestination(ai, plan.position))
            { plan.position.active = true; return true; }
        }
        return false;
    }
    const char* LargeHeal(Player* healer)
    {
        switch (healer->getClass())
        {
            case CLASS_PRIEST: return "greater heal";
            case CLASS_DRUID: return "healing touch";
            case CLASS_PALADIN: return "holy light";
            case CLASS_SHAMAN: return "healing wave";
        }
        return nullptr;
    }
    Player* HealingTarget(PlayerbotAI* ai)
    {
        Player* selected = nullptr;
        const auto members = Members(ai);
        for (Player* member : members)
        {
            if (member->GetHealthPercent() > 85.0f ||
                (selected && member->GetHealthPercent() >= selected->GetHealthPercent())) continue;
            // A stranded injured player must not reserve every healer's turn
            // while a reachable tank needs the available heal.
            for (Player* healer : members)
            {
                PlayerbotAI* brain = healer->GetPlayerbotAI();
                const char* name = LargeHeal(healer);
                if (ai->IsHeal(healer) && brain && !brain->IsRealPlayer() && name &&
                    !healer->hasUnitState(UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL) &&
                    brain->CanCastSpell(name, member, 0))
                { selected = member; break; }
            }
        }
        return selected;
    }
    // Native Classic/TBC Corrupted Mind adds the healing cooldown. Elect only
    // ready healers; an actual in-flight heal owns its turn until it completes.
    Player* LoathebHealer(PlayerbotAI* ai, Player* target)
    {
        Player* selected = nullptr;
        for (Player* healer : Members(ai))
        {
            if (!ai->IsHeal(healer)) continue;
            for (CurrentSpellTypes type : {CURRENT_GENERIC_SPELL, CURRENT_CHANNELED_SPELL})
                if (const Spell* cast = healer->GetCurrentSpell(type))
                    if (cast->m_spellInfo && cast->getState() != SPELL_STATE_FINISHED &&
                        PlayerbotAI::IsHealSpell(cast->m_spellInfo))
                        if (Unit* receiving = cast->m_targets.getUnitTarget())
                            if (receiving->IsPlayer() && receiving->IsInWorld() && receiving->IsAlive() &&
                                healer->IsInMap(receiving) && static_cast<Player*>(receiving)->GetGroup() == healer->GetGroup()) return healer;
            PlayerbotAI* healerAi = healer->GetPlayerbotAI();
            if (!healerAi || healerAi->IsRealPlayer()) continue;
            const char* name = LargeHeal(healer);
            if (!name || !target || healer->hasUnitState(UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL)) continue;
            const uint32 id = healerAi->GetAiObjectContext()->GetValue<uint32>("spell id", name)->Get();
            const SpellEntry* info = sServerFacade.LookupSpellInfo(id);
            if (!info || !healer->HasSpell(id) || !healer->IsSpellReady(*info) ||
                healer->GetPower(POWER_MANA) < Spell::CalculatePowerCost(info, healer) ||
                !healerAi->CanCastSpell(name, target, 0)) continue;
            if (!selected) selected = healer;
        }
        return selected;
    }
    Unit* KelthuzadControlledAlly(PlayerbotAI* ai, Unit* boss)
    {
        if (!boss || ai->GetBot()->getClass() != CLASS_MAGE) return nullptr;
        Player* bot = ai->GetBot();
        const auto members = Members(ai);
        std::vector<Player*> controlled, used;
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (member && member->IsInWorld() && member->IsAlive() && !member->IsBeingTeleported() &&
                bot->IsInMap(member) && member->GetGroup() == bot->GetGroup() &&
                member->HasCharmer(boss->GetObjectGuid()) && member->HasAura(28410) &&
                !PossibleAttackTargetsValue::HasBreakableCC(member, bot)) controlled.push_back(member);
        }
        std::sort(controlled.begin(), controlled.end(), [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        for (Player* victim : controlled)
        {
            bool reserved = false;
            for (Player* caster : members)
                if (const Spell* cast = caster->GetCurrentSpell(CURRENT_GENERIC_SPELL))
                    if (cast->m_spellInfo && cast->getState() != SPELL_STATE_FINISHED && cast->m_targets.getUnitTarget() == victim)
                    {
                        bool polymorph = cast->m_spellInfo->Mechanic == MECHANIC_POLYMORPH;
                        for (unsigned effect = 0; effect < MAX_EFFECT_INDEX; ++effect)
                            polymorph |= cast->m_spellInfo->EffectMechanic[effect] == MECHANIC_POLYMORPH;
                        if (polymorph) { used.push_back(caster); reserved = true; break; }
                    }
            if (reserved) continue;
            for (Player* caster : members)
            {
                PlayerbotAI* brain = caster->GetPlayerbotAI();
                if (caster->getClass() != CLASS_MAGE || !brain || brain->IsRealPlayer() ||
                    caster->hasUnitState(UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL) ||
                    std::find(used.begin(), used.end(), caster) != used.end() ||
                    !brain->CanCastSpell("polymorph", victim, 0)) continue;
                used.push_back(caster);
                if (caster == bot) return victim;
                break;
            }
        }
        return nullptr;
    }
}

bool ai::NaxxramasRolePlan(PlayerbotAI* ai, ClassicRaidPlan& plan)
{
    if (!Ready(ai)) return false;
    Player* bot = ai->GetBot();
    const auto enemies = Enemies(ai);
    if (Unit* boss = Find(enemies, 16060))
    {
        auto* instance = dynamic_cast<ScriptedInstance*>(bot->GetMap()->GetInstanceData());
        GameObject* gate = instance ? instance->GetSingleGameObjectFromStorage(181170) : nullptr;
        if (gate && gate->IsInWorld() && bot->IsInMap(gate) && gate->GetGoState() == GO_STATE_READY)
        {
            Anchor(ai, boss, plan, 16060);
            const bool right = bot->GetPositionY() <= gate->GetPositionY();
            Unit* target = nullptr;
            for (Unit* enemy : enemies)
            {
                const bool encounterAdd = classicraid::AddPriority(16060, enemy->GetEntry(), false, false) != 0;
                if ((enemy != boss && !encounterAdd) || !Attackable(ai, enemy) ||
                    (enemy->GetPositionY() <= gate->GetPositionY()) != right) continue;
                if (!target || enemy->GetHealthPercent() < target->GetHealthPercent()) target = enemy;
            }
            if (target) plan.target = target->GetObjectGuid();
            else
            {
                plan.holdDamage = !ai->IsHeal(bot);
                plan.position.active = true;
                plan.position.destination = {bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
            }
            return true;
        }
    }
    if (Unit* boss = Find(enemies, 16028))
    {
        Anchor(ai, boss, plan, 28307);
        const auto tanks = Members(ai, true);
        plan.target = boss->GetObjectGuid();
        if (ai->IsTank(bot))
        {
            if (boss->GetVictim() != bot)
            {
                const auto it = std::find(tanks.begin(), tanks.end(), bot);
                MeleePosition(ai, boss, plan, unsigned(it - tanks.begin()));
            }
            return true;
        }
        if (!ai->IsHeal(bot) && !HatefulReady(ai, boss, tanks))
        { plan.target.Clear(); plan.holdDamage = true; return true; }
        plan = ClassicRaidPlan();
        return false; // retain the ordinary healer/ranged formation once ready.
    }
    // Reserved worshippers and late KT guardians need an actual tank owner,
    // while the damage group retains the boss/sacrifice policy.
    for (uint32 bossEntry : {15953u, 15990u})
        if (Unit* boss = Find(enemies, bossEntry))
        {
            if (!ai->IsTank(bot) || boss->GetVictim() == bot) break;
            auto tanks = Members(ai, true);
            tanks.erase(std::remove(tanks.begin(), tanks.end(), boss->GetVictim()), tanks.end());
            auto me = std::find(tanks.begin(), tanks.end(), bot);
            if (me == tanks.end()) break;
            std::vector<Unit*> adds;
            for (Unit* enemy : enemies)
                if (enemy->GetEntry() == (bossEntry == 15953 ? 16506u : 16441u) && Attackable(ai, enemy)) adds.push_back(enemy);
            if (adds.empty()) break;
            Unit* add = adds[unsigned(me - tanks.begin()) % adds.size()];
            Anchor(ai, boss, plan, bossEntry);
            plan.target = add->GetObjectGuid();
            // Keep the Faerlina sacrifice in native Embrace range. A tank with
            // no aggro first approaches/attacks normally, never drags an add by fiat.
            if (bossEntry == 15953 && add->GetVictim() == bot)
            {
                const float radius = NativeEncounterSpellRadius(naxxnative::FaerlinaEmbrace(Regular(ai)));
                if (radius > 3 && radius < 30 && add->GetDistance(boss) > radius - 2)
                    MeleePosition(ai, boss, plan, unsigned(me - tanks.begin()));
            }
            return true;
        }
    if (!ai->IsTank(bot) && !ai->IsHeal(bot))
    {
        Unit* selected = nullptr;
        for (Unit* enemy : enemies)
            if (enemy->GetEntry() == 16168 && enemy->GetHealthPercent() < 30.0f && Attackable(ai, enemy) &&
                (!selected || enemy->GetHealthPercent() < selected->GetHealthPercent())) selected = enemy;
        if (selected)
        { Anchor(ai, selected, plan, 28995); plan.target = selected->GetObjectGuid(); return true; }
    }
    return false;
}

bool ai::NaxxramasRoleSupport(PlayerbotAI* ai, std::string& spell, Unit*& target)
{
    if (!Ready(ai)) return false;
    const auto enemies = Enemies(ai);
    if (Unit* victim = KelthuzadControlledAlly(ai, Find(enemies, 15990)))
    { spell = "polymorph"; target = victim; return true; }
#ifndef MANGOSBOT_TWO
    if (!ai->IsHeal(ai->GetBot()) || !Find(enemies, 16011)) return false;
    Player* injured = HealingTarget(ai);
    if (!injured || LoathebHealer(ai, injured) != ai->GetBot()) return false;
    const char* name = LargeHeal(ai->GetBot());
    if (!name || !ai->CanCastSpell(name, injured, 0)) return false;
    spell = name; target = injured; return true;
#else
    return false;
#endif
}

float ai::NaxxramasRoleMultiplier(PlayerbotAI* ai, Action* action)
{
#ifndef MANGOSBOT_TWO
    if (!action || !Ready(ai) || !ai->IsHeal(ai->GetBot())) return 1.0f;
    auto* cast = dynamic_cast<CastSpellAction*>(action);
    if (!cast) return 1.0f;
    const SpellEntry* info = sServerFacade.LookupSpellInfo(cast->GetDecisionSpellId());
    if (!info || !PlayerbotAI::IsHealSpell(info) || !Find(Enemies(ai), 16011)) return 1.0f;
    Player* injured = HealingTarget(ai);
    return injured && LoathebHealer(ai, injured) == ai->GetBot() ? 1.0f : 0.0f;
#else
    return 1.0f;
#endif
}
