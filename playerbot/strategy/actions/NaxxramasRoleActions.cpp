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
#include "MotionGenerators/PathFinder.h"

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
    Unit* GothikTankTarget(PlayerbotAI* ai, GameObject* gate, const std::vector<Unit*>& adds)
    {
        Player* bot = ai->GetBot();
        const bool side = bot->GetPositionY() <= gate->GetPositionY();
        auto tanks = Members(ai, true);
        tanks.erase(std::remove_if(tanks.begin(), tanks.end(), [&](Player* tank)
        {
            PlayerbotAI* brain = tank->GetPlayerbotAI();
            return !brain || brain->IsRealPlayer() ||
                tank->hasUnitState(UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL) ||
                (tank->GetPositionY() <= gate->GetPositionY()) != side;
        }), tanks.end());
        if (std::find(tanks.begin(), tanks.end(), bot) == tanks.end()) return nullptr;
        Unit* selected = nullptr;
        unsigned selectedRank = 0;
        for (Unit* add : adds)
        {
            Unit* victim = add->GetVictim();
            const bool held = victim && victim->IsPlayer() && victim->IsAlive() &&
                static_cast<Player*>(victim)->GetGroup() == bot->GetGroup() &&
                ai->IsTank(static_cast<Player*>(victim));
            Player* owner = held ? static_cast<Player*>(victim) : nullptr;
            if (!held)
            {
                // A temporary stun can nominate a relief tank. Keep that
                // active pickup when the original tank recovers, until an
                // actual tank holds the add. Otherwise the changing eligible
                // roster revokes the rescue while the add is killing a caster.
                for (Player* tank : tanks)
                    if (tank->GetVictim() == add &&
                        (!owner || tank->GetObjectGuid() < owner->GetObjectGuid())) owner = tank;
                if (!owner) owner = tanks[add->GetObjectGuid().GetRawValue() % tanks.size()];
            }
            if (owner != bot) continue;
            // Stable ownership for exposed adds. Never pull a safely held add
            // off another tank just because every damage dealer focuses it.
            const unsigned rank = (held ? 0u : 100u) + classicraid::AddPriority(16060, add->GetEntry(), false, false);
            if (!selected || rank > selectedRank || (rank == selectedRank && add->GetHealthPercent() < selected->GetHealthPercent()))
            { selected = add; selectedRank = rank; }
        }
        return selected;
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
#ifdef MANGOSBOT_ZERO
            plan.position.active = true;
#endif
            if (ValidateEncounterDestination(ai, plan.position))
            { plan.position.active = true; return true; }
#ifdef MANGOSBOT_ZERO
            plan.position.active = false;
#endif
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
#ifdef MANGOSBOT_ZERO
        Unit* boss = Find(Enemies(ai), 16011);
        Unit* holder = boss ? boss->GetVictim() : nullptr;
        int selectedPriority = -1;
#endif
        for (Player* member : members)
        {
#ifdef MANGOSBOT_ZERO
            // One heal per minute: preserve turns for the native melee victim.
            // Other players need an emergency, not a small poison wound.
            const bool holding = member == holder;
            if (member->GetHealthPercent() > (holding ? 85.0f : 35.0f)) continue;
            const int priority = holding ? 1 : 0;
            if (selected && (priority < selectedPriority ||
                (priority == selectedPriority && member->GetHealthPercent() >= selected->GetHealthPercent()))) continue;
#else
            if (member->GetHealthPercent() > 85.0f ||
                (selected && member->GetHealthPercent() >= selected->GetHealthPercent())) continue;
#endif
            // A stranded injured player must not reserve every healer's turn
            // while a reachable tank needs the available heal.
            for (Player* healer : members)
            {
#ifdef MANGOSBOT_ZERO
                if (healer->HasOverrideScript(4327)) continue;
#endif
                PlayerbotAI* brain = healer->GetPlayerbotAI();
                const char* name = LargeHeal(healer);
                if (ai->IsHeal(healer) && brain && !brain->IsRealPlayer() && name &&
                    !healer->hasUnitState(UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL) &&
                    brain->CanCastSpell(name, member, 0))
                {
                    selected = member;
#ifdef MANGOSBOT_ZERO
                    selectedPriority = priority;
#endif
                    break;
                }
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
#ifdef MANGOSBOT_ZERO
            // Holy Light is a script wrapper around native heal 19968.
            // Its outer spell can look ready while Corrupted Mind rejects
            // the payload. Do not let that caster monopolize the election.
            if (healer->HasOverrideScript(4327)) continue;
#endif
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

namespace
{
    bool ThaddiusWalkPosition(PlayerbotAI* ai, ClassicRaidPlan& plan, encounter::Point destination)
    {
        Player* bot=ai->GetBot();
        if (!ai->CanMove()) return false;
        if (bot->GetDistance(destination.x,destination.y,destination.z)>50)
        {
            // The other platform starts outside ordinary target perception.
            // Walk a bounded leg of the complete native path, never a straight
            // interpolation across the gap or a teleport to the other side.
            PathFinder finder(bot);
            if (!finder.calculate(destination.x,destination.y,destination.z,false) ||
                finder.getPathType()!=PATHFIND_NORMAL || finder.getPath().size()<2 || finder.getPath().size()>256) return false;
            const auto& end=finder.getPath().back();
            if (!std::isfinite(end.x) || !std::isfinite(end.y) || !std::isfinite(end.z) ||
                std::sqrt((end.x-destination.x)*(end.x-destination.x)+(end.y-destination.y)*(end.y-destination.y)+
                    (end.z-destination.z)*(end.z-destination.z))>2) return false;
            encounter::Point previous{bot->GetPositionX(),bot->GetPositionY(),bot->GetPositionZ()};
            float total=0;
            for (const auto& node:finder.getPath())
            {
                const float segment=std::sqrt((node.x-previous.x)*(node.x-previous.x)+
                    (node.y-previous.y)*(node.y-previous.y)+(node.z-previous.z)*(node.z-previous.z));
                total+=segment;
                if (!std::isfinite(total) || total>240) return false;
                previous={node.x,node.y,node.z};
            }
            previous={bot->GetPositionX(),bot->GetPositionY(),bot->GetPositionZ()};
            float remaining=30;
            for (const auto& node:finder.getPath())
            {
                const encounter::Point next{node.x,node.y,node.z};
                const float distance=std::sqrt((next.x-previous.x)*(next.x-previous.x)+
                    (next.y-previous.y)*(next.y-previous.y)+(next.z-previous.z)*(next.z-previous.z));
                if (!std::isfinite(distance)) return false;
                if (distance>=remaining && distance>0)
                {
                    const float scale=remaining/distance;
                    destination={previous.x+(next.x-previous.x)*scale,previous.y+(next.y-previous.y)*scale,
                        previous.z+(next.z-previous.z)*scale};
                    break;
                }
                remaining-=distance;previous=next;
            }
        }
        plan.position.destination=destination;
        // The native validator rejects inactive requests before checking the
        // route. Admit this candidate, then retain only a validated result.
        plan.position.active=true;
        plan.position.active=ValidateEncounterDestination(ai,plan.position);
        return plan.position.active;
    }

    bool ThaddiusAddRolePlan(PlayerbotAI* ai, ClassicRaidPlan& plan)
    {
#ifdef MANGOSBOT_ZERO
        Player* bot=ai->GetBot();
        auto* instance=dynamic_cast<ScriptedInstance*>(bot->GetMap()->GetInstanceData());
        if (!instance || instance->GetData(12)!=IN_PROGRESS) return false;
        Creature* adds[2]={instance->GetSingleCreatureFromStorage(15930,true),instance->GetSingleCreatureFromStorage(15929,true)};
        for (unsigned i=0;i<2;++i)
            if (!NaxxramasEncounterEngaged(bot,adds[i]) || adds[i]->GetEntry()!=(i?15929u:15930u) ||
                adds[i]->IsImmuneToPlayer() || bot->GetDistance(adds[i])>180) adds[i]=nullptr;
        if (!adds[0] && !adds[1]) return false;
        const bool tank=ai->IsTank(bot),healer=ai->IsHeal(bot);
        auto peers=Members(ai);
        peers.erase(std::remove_if(peers.begin(),peers.end(),[&](Player* member) {
            return ai->IsTank(member)!=tank || (!tank && ai->IsHeal(member)!=healer);
        }),peers.end());
        auto self=std::find(peers.begin(),peers.end(),bot);
        if (self==peers.end()) return false;
        unsigned side=unsigned(self-peers.begin())%2;
        if (tank && adds[0] && adds[1])
        {
            // Keep a real holder; after Magnetic Pull, take the nearby add
            // rather than running back across the room and breaking its chain.
            const unsigned nearest=bot->GetDistance(adds[1])<bot->GetDistance(adds[0])?1:0;
            // An authorized pull may have assigned this tank to the opposite
            // parity. Keep its actually reached platform, without turning an
            // unprepared raid's idle spare tanks away from the remote add.
            if (ai->GetAiObjectContext()->GetValue<ObjectGuid>("thaddius prepared target")->Get()==adds[nearest]->GetObjectGuid() &&
                bot->GetDistance(adds[nearest])<40 && bot->GetDistance(adds[1-nearest])>60) side=nearest;
            if (adds[0]->GetVictim()==bot || adds[1]->GetVictim()==bot)
                side=(adds[nearest]->GetVictim()==bot || (bot->GetDistance(adds[nearest])<20 &&
                    bot->GetDistance(adds[1-nearest])>40))?nearest:1-nearest;
        }
        Creature* boss=adds[side]?adds[side]:adds[1-side];
        Anchor(ai,boss,plan,boss->GetEntry());
        if (!healer && Attackable(ai,boss)) plan.target=boss->GetObjectGuid();
        if (adds[0] && adds[1] && boss->GetHealthPercent()<25 &&
            boss->GetHealthPercent()+3<adds[boss==adds[0]?1:0]->GetHealthPercent()) plan.holdDamage=!healer;
        float x,y,z;boss->GetRespawnCoord(x,y,z);
        if (!std::isfinite(x) || !std::isfinite(y) || !std::isfinite(z) ||
            boss->GetDistance(x,y,z)>100) return true;
        if (tank && boss->GetVictim()==bot)
        {
            // Native Tesla effects require the add within 60yd of its coil.
            // Hold its home platform, and bring it back after a displacement.
            if (boss->GetDistance(x,y,z)<8 && boss->CanReachWithMeleeAttack(bot))
            {
                ThaddiusWalkPosition(ai,plan,{bot->GetPositionX(),bot->GetPositionY(),bot->GetPositionZ()});return true;
            }
            ThaddiusWalkPosition(ai,plan,{x,y,z});return true;
        }
        const bool ranged=!tank && (healer || ai->IsRanged(bot));
        const float radius=ranged?20.0f:std::max(2.0f,boss->GetCombatReach()+bot->GetCombatReach()-1);
        const float start=std::atan2(bot->GetPositionY()-(ranged?y:boss->GetPositionY()),bot->GetPositionX()-(ranged?x:boss->GetPositionX()));
        for (unsigned i=0;i<8;++i)
        {
            const float angle=start+float(i)*M_PI_F/4;
            encounter::Point station{(ranged?x:boss->GetPositionX())+radius*std::cos(angle),
                (ranged?y:boss->GetPositionY())+radius*std::sin(angle),ranged?z:boss->GetPositionZ()};
            if (ThaddiusWalkPosition(ai,plan,station)) break;
        }
        return true;
#else
        return false;
#endif
    }
}

bool ai::NaxxramasRolePlan(PlayerbotAI* ai, ClassicRaidPlan& plan)
{
    if (!Ready(ai)) return false;
    if (ThaddiusAddRolePlan(ai,plan)) return true;
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
            unsigned selectedRank = 0;
            std::vector<Unit*> sideAdds;
            for (Unit* enemy : enemies)
            {
                unsigned rank = classicraid::AddPriority(16060, enemy->GetEntry(), false, false);
                const bool encounterAdd = rank != 0;
#ifndef MANGOSBOT_ZERO
                rank = 0; // Retain the other native eras' existing lowest-health policy.
#endif
                if ((enemy != boss && !encounterAdd) || !Attackable(ai, enemy) ||
                    (enemy->GetPositionY() <= gate->GetPositionY()) != right) continue;
                if (encounterAdd) sideAdds.push_back(enemy);
                if (!target || rank > selectedRank || (rank == selectedRank && enemy->GetHealthPercent() < target->GetHealthPercent()))
                { target = enemy; selectedRank = rank; }
            }
#ifdef MANGOSBOT_ZERO
            if (ai->IsTank(bot)) target = GothikTankTarget(ai, gate, sideAdds);
#endif
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
                if ((enemy->GetEntry() == (bossEntry == 15953 ? 16506u : 16441u)
#ifdef MANGOSBOT_ZERO
                     || (bossEntry == 15953 && enemy->GetEntry() == 16505)
#endif
                    ) && Attackable(ai, enemy)) adds.push_back(enemy);
            if (adds.empty()) break;
            Unit* add = adds[unsigned(me - tanks.begin()) % adds.size()];
#ifdef MANGOSBOT_ZERO
            if (bossEntry == 15953)
            {
                // Distribute ALL six native adds over the off-tanks. Assigning
                // one worshipper per tank left both followers chasing healers.
                std::sort(adds.begin(),adds.end(),[](Unit* a,Unit* b) {
                    if (a->GetEntry()!=b->GetEntry()) return a->GetEntry()<b->GetEntry();
                    return a->GetObjectGuid()<b->GetObjectGuid();
                });
                add=nullptr;bool selectedLoose=false;
                for (size_t index=unsigned(me-tanks.begin());index<adds.size();index+=tanks.size())
                {
                    Unit* candidate=adds[index];Unit* victim=candidate->GetVictim();
                    const bool tankHeld=victim && victim->IsPlayer() && victim->IsAlive() &&
                        ai->IsTank(static_cast<Player*>(victim));
                    if (tankHeld && victim!=bot) continue; // Do not steal a secured add.
                    const bool loose=!tankHeld;
                    if (!add || (loose && !selectedLoose)) {add=candidate;selectedLoose=loose;}
                }
                if (!add) break;
            }
#endif
            Anchor(ai, boss, plan, bossEntry);
            plan.target = add->GetObjectGuid();
            // Keep the Faerlina sacrifice in native Embrace range. A tank with
            // no aggro first approaches/attacks normally, never drags an add by fiat.
            if (bossEntry == 15953 && add->GetEntry() == 16506 && add->GetVictim() == bot)
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
    if (!info || !Find(Enemies(ai), 16011)) return 1.0f;
    bool healingTurn=PlayerbotAI::IsHealSpell(info);
#ifdef MANGOSBOT_ZERO
    // Holy Shock's outer spell is DUMMY, while its friendly payload consumes
    // Corrupted Mind. Native trace had three healers spend turns on full tanks.
    // Dispels consume the same turn. Keep hostile Holy Shock available.
    if (Unit* target=action->GetTarget())
        if (sServerFacade.IsFriendlyTo(ai->GetBot(),target))
            healingTurn |= (info->SpellFamilyName==SPELLFAMILY_PALADIN && info->SpellIconID==156) ||
                IsSpellHaveEffect(info,SPELL_EFFECT_DISPEL);
#endif
    if (!healingTurn) return 1.0f;
    Player* injured = HealingTarget(ai);
#ifdef MANGOSBOT_ZERO
    // The support action issues the elected large heal directly. A generic
    // Renew/Flash Heal/pet heal must not spend the same caster's turn on a
    // different target before that action runs.
    const char* large = LargeHeal(ai->GetBot());
    if (!large || action->GetTarget() != injured || cast->GetDecisionSpellId() !=
        ai->GetAiObjectContext()->GetValue<uint32>("spell id", large)->Get()) return 0.0f;
#endif
    return injured && LoathebHealer(ai, injured) == ai->GetBot() ? 1.0f : 0.0f;
#else
    return 1.0f;
#endif
}
