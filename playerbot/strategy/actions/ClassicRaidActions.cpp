#include "playerbot/playerbot.h"
#include "ClassicRaidActions.h"
#include "WrathHorsemenActions.h"
#include "NaxxramasRoleActions.h"
#include "NaxxramasControlCommands.h"
#include "GluthRoleActions.h"
#include "BlackwingMovementSafety.h"
#include "BroodlordFormation.h"
#include "BotCommandAccess.h"
#include "playerbot/strategy/generic/PullStrategy.h"
#include "playerbot/strategy/generic/CombatStrategy.h"
#include "EncounterSpellPolicy.h"
#include "ReachTargetActions.h"
#include "GenericSpellActions.h"
#include "MovementPathSafety.h"
#include "playerbot/strategy/NaxxramasNativePolicy.h"
#include "playerbot/ServerFacade.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"
#include "playerbot/strategy/values/PositionValue.h"
#include "MotionGenerators/PathFinder.h"
#include "Movement/MoveSpline.h"
#include "AI/ScriptDevAI/include/sc_instance.h"
#include "Entities/Totem.h"

using namespace ai;

namespace
{
    bool Ready(PlayerbotAI* ai)
    {
        Player* bot = ai->GetBot();
#if defined(MANGOSBOT_ONE)
        // These raids retain their Classic encounter contracts in TBC.
        if (bot->GetMapId() != 249 && bot->GetMapId() != 309 &&
            bot->GetMapId() != 469 && bot->GetMapId() != 533) return false;
#elif defined(MANGOSBOT_TWO)
        // Naxx uses explicit native difficulty/control/Horsemen variants below.
        // Wrath Onyxia retains its separate level-80 encounter planner.
        if (bot->GetMapId() != 309 && bot->GetMapId() != 469 && bot->GetMapId() != 533) return false;
#endif
        return bot->IsInWorld() && bot->IsAlive() && bot->IsInCombat() && !bot->IsBeingTeleported() &&
            !bot->HasCharmer() && !ai->IsRealPlayer() && bot->GetGroup() && classicraid::Map(bot->GetMapId());
    }
    bool Live(Player* bot, Unit* unit)
    {
        return unit && unit->IsInWorld() && unit->IsAlive() && bot->IsInMap(unit) && !unit->HasCharmer();
    }
    bool Member(Player* bot, Player* player)
    {
        return Live(bot, player) && player->GetGroup() == bot->GetGroup() && !player->IsBeingTeleported();
    }
    bool Engaged(Player* bot, Unit* unit)
    {
        if (!Live(bot, unit) || !unit->IsInCombat() || sServerFacade.IsFriendlyTo(bot, unit)) return false;
        Unit* victim = unit->GetVictim();
        if (victim && victim->IsInWorld() && bot->IsInMap(victim))
        {
            if (victim->IsPlayer() && Member(bot, static_cast<Player*>(victim))) return true;
            Unit* owner = victim->GetMaster();
            if (owner && owner->IsPlayer() && Member(bot, static_cast<Player*>(owner))) return true;
        }
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* player = ref->getSource();
            if (!Member(bot, player)) continue;
            if (player->GetVictim() == unit || unit->getAttackers().count(player)) return true;
        }
        return false;
    }
    std::vector<Player*> Members(PlayerbotAI* ai, bool tanks = false)
    {
        std::vector<Player*> members;
        Player* bot = ai->GetBot();
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
            if (Member(bot, ref->getSource()) && (!tanks || ai->IsTank(ref->getSource()))) members.push_back(ref->getSource());
        std::sort(members.begin(), members.end(), [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        return members;
    }
    Unit* FindBoss(PlayerbotAI* ai, uint32 entry)
    {
        if (!Ready(ai) || !classicraid::Boss(ai->GetBot()->GetMapId(), entry)) return nullptr;
        for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets", "100:1")->Get())
        {
            Unit* unit = ai->GetUnit(guid);
            if (unit && unit->GetEntry() == entry && Engaged(ai->GetBot(), unit)) return unit;
        }
        return nullptr;
    }
    bool NaxxRegular(PlayerbotAI* ai)
    {
#ifdef MANGOSBOT_TWO
        return ai->GetBot()->GetMap()->IsRegularDifficulty();
#else
        return true;
#endif
    }
    bool RaidDamageSpell(const SpellEntry* spell)
    {
        if (!spell) return false;
        // Channels can deal their damage through a native tick spell. Inspect
        // a bounded graph so a damage pause still admits non-damaging CC/taunts.
        std::vector<const SpellEntry*> pending{spell};
        std::vector<uint32> visited;
        for (size_t next = 0; next < pending.size() && next < 16; ++next)
        {
            const SpellEntry* current = pending[next];
            if (!current || std::find(visited.begin(), visited.end(), current->Id) != visited.end()) continue;
            visited.push_back(current->Id);
            for (unsigned i = 0; i < MAX_EFFECT_INDEX; ++i)
            {
                const auto effect = SpellEffectIndex(i);
                if (IsSpellEffectDamage(*current, effect)) return true;
                if ((IsSpellEffectTriggerSpell(current, effect) || IsSpellEffectTriggerSpellByAura(current, effect)) &&
                    current->EffectTriggerSpell[i] && pending.size() < 16)
                    pending.push_back(sServerFacade.LookupSpellInfo(current->EffectTriggerSpell[i]));
            }
        }
        return false;
    }
    Unit* FaerlinaSacrifice(PlayerbotAI* ai, Unit* boss)
    {
        if (!boss || !naxxnative::WorshipperDeathEmbrace(NaxxRegular(ai)) ||
            !boss->HasAura(naxxnative::FaerlinaFrenzy(NaxxRegular(ai)))) return nullptr;
        const float radius = NativeEncounterSpellRadius(naxxnative::FaerlinaEmbrace(NaxxRegular(ai)));
        if (!std::isfinite(radius) || radius <= 1 || radius > 30) return nullptr;
        Unit* selected = nullptr;
        for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets", "100:1")->Get())
        {
            Unit* add = ai->GetUnit(guid);
            if (!Live(ai->GetBot(), add) || add->GetEntry() != 16506 || !Engaged(ai->GetBot(), add) ||
                add->GetDistance(boss) >= radius - 1 || PossibleAttackTargetsValue::HasBreakableCC(add, ai->GetBot())) continue;
            if (!selected || add->GetObjectGuid() < selected->GetObjectGuid()) selected = add;
        }
        return selected;
    }
    bool Attackable(PlayerbotAI* ai, Unit* unit)
    {
        Player* bot = ai->GetBot();
        return Engaged(bot, unit) && PossibleAttackTargetsValue::IsValid(unit, bot,
            sPlayerbotAIConfig.sightDistance, false, true) && !PossibleAttackTargetsValue::HasBreakableCC(unit, bot) &&
            !PossibleAttackTargetsValue::HasUnBreakableCC(unit, bot);
    }
    bool Spore(PlayerbotAI* ai, Unit* unit)
    {
        Player* bot = ai->GetBot();
        if (!Live(bot, unit) || bot->GetMapId() != 533 || unit->GetEntry() != 16286 ||
            unit->GetUInt32Value(UNIT_CREATED_BY_SPELL) != 29234 || ai->IsTank(bot) || ai->IsHeal(bot)) return false;
        Unit* owner = ai->GetUnit(unit->GetSpawnerGuid());
        return owner && owner->GetEntry() == 16011 && Engaged(bot, owner) &&
            PossibleAttackTargetsValue::IsPossibleTarget(unit, bot, sPlayerbotAIConfig.sightDistance, false) &&
            !PossibleAttackTargetsValue::HasBreakableCC(unit, bot);
    }
    std::vector<Player*> SporeRecipients(PlayerbotAI* ai, Unit* spore, bool& assembled)
    {
        std::vector<Player*> recipients;
        const float radius = NativeEncounterSpellRadius(29232);
        assembled = radius > 1 && radius <= 30;
        for (Player* member : Members(ai))
        {
            // Humans choose their own spores; never wait for them to obey a bot plan.
            if (ai->IsTank(member) || ai->IsHeal(member))
            { if (member->GetDistance(spore) < radius) assembled = false; continue; }
            if (member->HasAura(29232) || !member->GetPlayerbotAI() || member->GetPlayerbotAI()->IsRealPlayer()) continue;
            if (recipients.size() < 5) recipients.push_back(member);
        }
        if (recipients.empty()) assembled = false;
        for (Player* member : recipients) if (member->GetDistance(spore) >= radius - 1) assembled = false;
        return recipients;
    }
    unsigned Stacks(Player* player, Unit* boss)
    {
        const uint32 mark = classicraid::HorsemanMark(boss->GetEntry());
        const SpellAuraHolder* holder = mark ? player->GetSpellAuraHolder(mark) : nullptr;
        return holder ? holder->GetStackAmount() : 0;
    }
    // Existing native mechanic handlers outrank an ordinary formation. Never
    // countermand cover, polarity/injection, dance, a beam, crystal or poison.
    bool SpecialPosition(PlayerbotAI* ai)
    {
        const uint32 map = ai->GetBot()->GetMapId();
        if (map == 249) return ai->GetAiObjectContext()->GetValue<EncounterPosition>("onyxia position")->Get().active;
        if (map == 469 && ai->GetAiObjectContext()->GetValue<EncounterPosition>("blackwing lair position")->Get().active) return true;
        if (map == 533 && (ai->GetAiObjectContext()->GetValue<EncounterPosition>("naxxramas position")->Get().active ||
            ai->GetAiObjectContext()->GetValue<EncounterPosition>("heigan dance position")->Get().active)) return true;
        if ((map == 469 || map == 533) && ai->GetAiObjectContext()->GetValue<EncounterPosition>("boss cover position")->Get().active) return true;
        if (IsBossEscapeMap(map) && ai->GetAiObjectContext()->GetValue<EncounterPosition>("boss cast position")->Get().active) return true;
        if (map == 531 && ai->GetAiObjectContext()->GetValue<EncounterPosition>("rotating beam position")->Get().active) return true;
        if (map == 509 && ai->GetAiObjectContext()->GetValue<EncounterPosition>("ossirian crystal position")->Get().active) return true;
        return map == 309 && ai->GetAiObjectContext()->GetValue<EncounterPosition>("hakkar poison position")->Get().active;
    }
    float Range(PlayerbotAI* ai, Unit* enemy)
    {
        Player* bot = ai->GetBot();
        const char* spell = ai->IsHeal(bot) ? "flash heal" : nullptr;
        if (!spell)
            switch (bot->getClass())
            {
                case CLASS_MAGE: spell = "frostbolt"; break;
                case CLASS_WARLOCK: spell = "shadow bolt"; break;
                case CLASS_HUNTER: spell = "auto shot"; break;
                case CLASS_PRIEST: spell = "mind blast"; break;
                case CLASS_DRUID: spell = ai->IsHeal(bot) ? "healing touch" : "wrath"; break;
                case CLASS_SHAMAN: spell = ai->IsHeal(bot) ? "healing wave" : "lightning bolt"; break;
                case CLASS_PALADIN: spell = "flash of light"; break;
            }
        if (ai->IsHeal(bot))
            switch (bot->getClass())
            {
                case CLASS_DRUID: spell = "healing touch"; break;
                case CLASS_SHAMAN: spell = "healing wave"; break;
                case CLASS_PALADIN: spell = "flash of light"; break;
            }
        float range = ai->GetRange("spell");
        if (spell) ai->GetSpellRange(spell, &range);
        return std::isfinite(range) ? std::max(8.0f, std::min(45.0f, range) - 2.0f) : 28.0f;
    }
    bool PositionLegal(PlayerbotAI* ai, Unit* anchor, EncounterPosition& position, float range)
    {
        if (!ValidateEncounterDestination(ai, position)) return false;
        const auto& p = position.destination;
        return anchor->GetDistance(p.x, p.y, p.z) <= range &&
            anchor->IsWithinLOS(p.x, p.y, p.z + ai->GetBot()->GetCollisionHeight(), true);
    }
    bool SuppressionTrash(Unit* unit)
    {
        if (!unit) return false;
        const uint32 entry = unit->GetEntry();
        return entry == 12458 || entry == 12468 || (entry >= 14022 && entry <= 14025);
    }
    bool SuppressionStationActive(PlayerbotAI* ai)
    {
        if (!BlackwingSuppressionMovementActive(ai)) return false;
        if (InstanceData* instance = ai->GetBot()->GetMap()->GetInstanceData())
            if (instance->GetData(2) == IN_PROGRESS || instance->GetData(2) == DONE) return false;
        return true;
    }
    Player* SuppressionLeader(PlayerbotAI* ai)
    {
        Player* bot = ai->GetBot();
        if (!bot->GetGroup()) return nullptr;
        for (Player* member : Members(ai))
            if (member->GetObjectGuid() == bot->GetGroup()->GetLeaderGuid() && member->isRealPlayer()) return member;
        return nullptr;
    }
    std::vector<encounter::Circle> SuppressionFlames(PlayerbotAI* ai)
    {
        std::vector<encounter::Circle> flames;
        const float radius = NativeEncounterSpellRadius(22442);
        if (!std::isfinite(radius) || radius <= 0 || radius >= 40) return flames;
        for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets", "100:1")->Get())
        {
            Unit* hatcher = ai->GetUnit(guid);
            if (hatcher && hatcher->GetEntry() == 12468 && Engaged(ai->GetBot(), hatcher))
                flames.push_back({{hatcher->GetPositionX(), hatcher->GetPositionY(), hatcher->GetPositionZ()}, radius + 2.0f});
        }
        return flames;
    }
    bool LocalCircleRoute(PlayerbotAI* ai, const EncounterPosition& p, const std::vector<encounter::Circle>& circles);
    bool SuppressionCombatStation(PlayerbotAI* ai, Unit* boss, Unit* target, ClassicRaidPlan& plan)
    {
        if (!SuppressionTrash(boss) || !SuppressionTrash(target) || !SuppressionStationActive(ai) ||
            classicraid::Front(target->GetEntry())) return false;
        Player* leader = SuppressionLeader(ai);
        Player* bot = ai->GetBot();
        const bool tank = ai->IsTank(bot);
        const bool ranged = !tank && (ai->IsRanged(bot) || ai->IsHeal(bot));
        const auto flames = SuppressionFlames(ai);
        if (!leader)
        {
            // A dead/loading leader is not a request to resume generic outward
            // spacing. Preserve class actions while the shared anchor recovers.
            EncounterPosition hold; hold.active = true; hold.exclusive = false;
            hold.map = bot->GetMapId(); hold.instance = bot->GetInstanceId();
            hold.boss = boss->GetObjectGuid(); hold.spell = 179784;
            hold.destination = {bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
            if (ranged && !encounter::OutsideCircles(hold.destination, flames))
            {
                const auto here = hold.destination;
                unsigned checks = 0;
                for (const auto point : encounter::EscapeCircles(here, flames))
                {
                    if (encounter::Distance2d(here, point) > 24.0f) continue;
                    hold.destination = point;
                    if (!ValidateEncounterDestination(ai, hold, false)) continue;
                    if (++checks > 20) break;
                    if (!ValidateEncounterDestination(ai, hold) || !LocalCircleRoute(ai, hold, flames)) continue;
                    plan.position = hold; plan.emergency = true;
                    return true;
                }
                hold.destination = here;
            }
            if (ValidateEncounterDestination(ai, hold)) plan.position = hold;
            return true;
        }
        const bool holder = boss->GetVictim() == bot;
        // Hatcher pulse requires a separate melee/tank work area. Otherwise
        // packs are brought into the compact area around the human leader.
        const float workRadius = flames.empty() ? 6.0f : 20.0f;
        const float meleeReach = std::max(2.0f, target->GetCombatReach() + bot->GetCombatReach() - 1.0f);
        if (tank && !holder) return true; // Actual tank pickup retains native chase/taunt admission.
        const bool hatcherHolder = tank && boss->GetEntry() == 12468;
        const bool hatcherAtLeader = hatcherHolder &&
            boss->GetDistance(leader) < NativeEncounterSpellRadius(22442) + 2.0f;
        // The mob stops within native melee reach of its tank. Position the
        // tank beyond that reach, otherwise a safe-looking tank ring can leave
        // the actual Hatcher pulse on the leader.
        float tankRadius = hatcherHolder ? std::max(workRadius, NativeEncounterSpellRadius(22442) +
            4.0f + boss->GetCombatReach() + bot->GetCombatReach()) : workRadius;
        if (hatcherAtLeader)
            tankRadius = std::max(tankRadius, std::min(tankRadius + 4.0f, bot->GetDistance(leader) + 2.0f));

        Unit* castAnchor = target;
        if (ai->IsHeal(bot))
        {
            Unit* victim = boss->GetVictim();
            if (Live(bot, victim) && (victim->IsPlayer() || victim->GetCharmer())) castAnchor = victim;
        }
        float maximum = ranged ? Range(ai, castAnchor) + 2.0f : meleeReach;
        float minimum = 0;
        if (ranged && bot->getClass() == CLASS_HUNTER &&
            (!ai->GetSpellRange("auto shot", &maximum, &minimum) || !std::isfinite(minimum) || minimum < 0)) return true;
        if (!std::isfinite(maximum) || maximum <= minimum + 1) return true;
        const bool localTarget = target->GetDistance(leader) <= workRadius + meleeReach;
        // A distant mob must come to the raid. Failure to reach it from the
        // leader area is not permission for every DPS to chase the tank ahead.
        const bool requireCastRange = ranged && (ai->IsHeal(bot) || castAnchor->GetDistance(leader) <= maximum + 3.0f);
        const bool meleeContact = !ranged && !tank && localTarget;
        const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
        const encounter::Point lead{leader->GetPositionX(), leader->GetPositionY(), leader->GetPositionZ()};
        EncounterPosition p; p.active = true; p.exclusive = false; p.map = bot->GetMapId();
        p.instance = bot->GetInstanceId(); p.boss = boss->GetObjectGuid(); p.source = leader->GetObjectGuid();
        p.spell = 179784; // Native suppression context; never submitted as a spell.
        p.destination = here;
        auto legal = [&](EncounterPosition& candidate) {
            const auto& point = candidate.destination;
            const float limit = ranged ? 24.0f : tank ? tankRadius + 2.0f : workRadius + meleeReach + 2;
            const float fromLeader = encounter::Distance2d(point, lead);
            if (fromLeader > limit && fromLeader >= encounter::Distance2d(here, lead) - 1) return false;
            if (ranged && (!encounter::OutsideCircles(point, flames) ||
                castAnchor->GetDistance(point.x, point.y, point.z) < minimum)) return false;
            if (requireCastRange && (castAnchor->GetDistance(point.x, point.y, point.z) > maximum ||
                !castAnchor->IsWithinLOS(point.x, point.y, point.z + bot->GetCollisionHeight(), true))) return false;
            if (meleeContact && !PositionLegal(ai, target, candidate, meleeReach)) return false;
            if (!meleeContact && !ValidateEncounterDestination(ai, candidate)) return false;
            return !ranged || flames.empty() || bot->GetDistance(point.x, point.y, point.z) <= 1.0f ||
                LocalCircleRoute(ai, candidate, flames);
        };
        const bool assembled = tank ? !hatcherAtLeader && bot->GetDistance(leader) <= tankRadius + 1 :
            meleeContact ? bot->CanReachWithMeleeAttack(target) : bot->GetDistance(leader) <= 3.0f;
        if (assembled && legal(p))
        {
            plan.position = p; // Suppress competing generic chase even while holding still.
            return true;
        }
        std::vector<encounter::Point> candidates;
        if (tank)
        {
            const float angle = leader->GetAngle(bot);
            // A bounded walking leg brings the owned mob back. Never drag a
            // currently nearby mob away just to achieve a decorative radius.
            for (float radius : {tankRadius, hatcherHolder ? tankRadius : std::max(2.0f, tankRadius - 2.0f)})
                for (float offset : {0.0f, 0.2f, -0.2f, 0.4f, -0.4f})
                    candidates.push_back({lead.x + radius * std::cos(angle + offset),
                        lead.y + radius * std::sin(angle + offset), here.z});
        }
        else if (meleeContact)
        {
            const float angle = target->GetAngle(bot);
            for (unsigned i = 0; i < 16; ++i)
            {
                const float offset = i == 0 ? 0 : ((i + 1) / 2) * 0.18f * (i % 2 ? 1 : -1);
                candidates.push_back({target->GetPositionX() + meleeReach * std::cos(angle + offset),
                    target->GetPositionY() + meleeReach * std::sin(angle + offset), here.z});
            }
        }
        else
        {
            candidates.push_back(lead);
            const float start = leader->GetAngle(bot);
            for (float radius : {1.5f, 3.0f, 6.0f, 10.0f, 18.0f, 22.0f})
                for (unsigned i = 0; i < 16; ++i)
                {
                    const float angle = start + i * M_PI_F / 8;
                    candidates.push_back({lead.x + radius * std::cos(angle), lead.y + radius * std::sin(angle), here.z});
                }
            if (ranged)
                for (const auto& flame : flames)
                {
                    const float angle = std::atan2(lead.y - flame.center.y, lead.x - flame.center.x);
                    candidates.push_back({flame.center.x + (flame.radius + 0.25f) * std::cos(angle),
                        flame.center.y + (flame.radius + 0.25f) * std::sin(angle), here.z});
                }
        }
        std::stable_sort(candidates.begin(), candidates.end(), [&](const encounter::Point& a, const encounter::Point& b) {
            const auto center = (tank || meleeContact) ? here : lead;
            const float da = encounter::Distance2d(center, a), db = encounter::Distance2d(center, b);
            return da != db ? da < db : encounter::Distance2d(here, a) < encounter::Distance2d(here, b);
        });
        unsigned checks = 0;
        for (auto point : candidates)
        {
            if (ranged && (!encounter::OutsideCircles(point, flames) ||
                castAnchor->GetDistance(point.x, point.y, point.z) < minimum)) continue;
            if (requireCastRange && castAnchor->GetDistance(point.x, point.y, point.z) > maximum) continue;
            // Long return/pullback uses validated, bounded walking legs.
            const float distance = encounter::Distance2d(here, point);
            if (distance > 50) { point.x = here.x + (point.x - here.x) * 50 / distance; point.y = here.y + (point.y - here.y) * 50 / distance; }
            p.destination = point;
            // Reject native ground/height hazards before spending a bounded
            // pathfinding attempt, so a fire patch at the leader cannot use
            // the entire route budget on overlapping close candidates.
            if (!ValidateEncounterDestination(ai, p, false)) continue;
            if (++checks > 20) break;
            if (!legal(p)) continue;
            plan.position = p;
            plan.emergency = ranged && !encounter::OutsideCircles(here, flames);
            return true;
        }
        // A blocked route must not become permission to resume an unsafe chase.
        // Holding still does not pause attacks, heals, taunts or native defenses.
        p.destination = here;
        if (ValidateEncounterDestination(ai, p)) plan.position = p;
        return true;
    }
    bool LocalCircleRoute(PlayerbotAI* ai, const EncounterPosition& p, const std::vector<encounter::Circle>& circles)
    {
        Player* bot = ai->GetBot();
        PathFinder path(bot);
        if (!path.calculate(p.destination.x, p.destination.y, p.destination.z, false) ||
            path.getPathType() != PATHFIND_NORMAL || path.getPath().size() < 2 || path.getPath().size() > 256) return false;
        std::list<HazardPosition> avoid;
        for (const auto& circle : circles)
            avoid.emplace_back(WorldPosition(bot->GetMapId(), circle.center.x, circle.center.y, circle.center.z), circle.radius);
        WorldPosition previous(bot);
        for (const auto& step : path.getPath())
        {
            WorldPosition point(bot->GetMapId(), step.x, step.y, step.z);
            if (!IsHazardSafeSegment(previous, point, avoid)) return false;
            previous = point;
        }
        return true;
    }
    bool KeepFormationRoute(PlayerbotAI* ai, Unit* target, Unit* anchor, EncounterPosition& p,
        float radius, bool ranged, bool front, const std::vector<encounter::Point>& neighbors, float spacing)
    {
        Player* bot = ai->GetBot();
        if (!bot->movespline || bot->movespline->Finalized()) return false;
        const auto end = bot->movespline->FinalDestination();
        const float angle = std::atan2(end.y - target->GetPositionY(), end.x - target->GetPositionX()) - target->GetOrientation();
        if (front && (classicraid::Dragon(target->GetEntry()) ? std::fabs(std::cos(angle)) > 0.70710678f : std::cos(angle) > 0)) return false;
        const encounter::Point point{end.x, end.y, end.z};
        for (auto q : neighbors)
            if (encounter::Distance2d(point, q) < spacing && std::fabs(point.z - q.z) < 8) return false;
        const float distance = anchor->GetDistance(end.x, end.y, end.z);
        if (ranged && distance < radius - 8) return false;
        p.destination = point;
        return PositionLegal(ai, anchor, p, radius + (ranged ? 2 : 3));
    }
    bool SubmitControlledSpell(Player* bot, Unit* charm, uint32 id, Unit* target)
    {
        const SpellEntry* spell = sServerFacade.LookupSpellInfo(id);
        if (!spell || !charm->HasSpell(id) || !charm->IsSpellReady(*spell) || charm->IsNonMeleeSpellCasted(false)) return false;
        SpellCastTargets targets;
        if (IsSpellRequireTarget(spell)) targets.setUnitTarget(target);
        WorldPacket packet(CMSG_PET_CAST_SPELL);
        packet << charm->GetObjectGuid();
#ifdef MANGOSBOT_TWO
        packet << uint8(0) << id << uint8(0);
#else
        packet << id;
#endif
        packet << targets;
        bot->GetSession()->HandlePetCastSpellOpcode(packet);
        return true; // Submission only. Native ownership/CheckCast/cooldown decide the result.
    }
    bool ControlledInRadius(PlayerbotAI* ai, Unit* charm, Unit* boss, float radius)
    {
        if (!std::isfinite(radius) || radius <= 1 || radius > 40) return false;
        if (charm->IsWithinDistInMap(boss, radius - 1) && charm->IsWithinLOSInMap(boss)) return true;
        if (charm->movespline && !charm->movespline->Finalized()) return false;
        const float angle = boss->GetAngle(charm);
        float x = boss->GetPositionX() + radius * 0.5f * std::cos(angle);
        float y = boss->GetPositionY() + radius * 0.5f * std::sin(angle);
        float z = boss->GetPositionZ();
        charm->UpdateAllowedPositionZ(x, y, z);
        if (!std::isfinite(z) || std::fabs(z - boss->GetPositionZ()) > 8) return false;
        PathFinder path(charm);
        if (!path.calculate(x, y, z, false) || path.getPathType() != PATHFIND_NORMAL ||
            path.getPath().size() < 2 || path.getPath().size() > 256) return false;
        const auto hazards = ai->GetAiObjectContext()->GetValue<std::list<HazardPosition>>("hazards")->Get();
        WorldPosition previous(charm);
        for (const auto& step : path.getPath())
        {
            WorldPosition point(charm->GetMapId(), step.x, step.y, step.z);
            if (!IsHazardSafeSegment(previous, point, hazards)) return false;
            previous = point;
        }
        charm->GetMotionMaster()->MovePoint(28732, x, y, z, FORCED_MOVEMENT_RUN, true);
        return false; // Wait for actual native arrival before spending the worshipper.
    }
    Unit* ControlledRelief(PlayerbotAI* ai, Unit* boss)
    {
        const SpellEntry* wall = sServerFacade.LookupSpellInfo(29061);
        const SpellEntry* taunt = sServerFacade.LookupSpellInfo(29060);
        if (!wall || !taunt || !boss) return nullptr;
        Unit* selected = nullptr;
        for (Player* owner : Members(ai))
        {
            if (!owner->GetPlayerbotAI() || owner->GetPlayerbotAI()->IsRealPlayer()) continue;
            Unit* student = owner->GetCharm();
            if (!student || student->GetEntry() != 16803 || !student->IsInWorld() || !student->IsAlive() ||
                !owner->IsInMap(student) || !student->HasCharmer(owner->GetObjectGuid()) ||
                !student->HasSpell(29061) || student->IsNonMeleeSpellCasted(false) ||
                !student->CanReachWithMeleeAttack(boss) || !student->IsWithinLOSInMap(boss) ||
                (boss->GetVictim() != student && (!student->HasSpell(29060) || !student->IsSpellReady(*taunt))) ||
                (!student->HasAura(29061) && !student->IsSpellReady(*wall))) continue;
            if (!selected || student->GetObjectGuid() < selected->GetObjectGuid()) selected = student;
        }
        return selected;
    }
    bool RingPosition(PlayerbotAI* ai, Unit* boss, float x, float y, float radius, uint32 tag, EncounterPosition& p)
    {
        Player* bot = ai->GetBot();
        if (std::hypot(bot->GetPositionX() - x, bot->GetPositionY() - y) > 80) return false;
        p.active = true; p.map = bot->GetMapId(); p.instance = bot->GetInstanceId();
        p.boss = boss->GetObjectGuid(); p.spell = tag;
        auto valid = [&]() {
            if (tag == 28217 && boss->GetDistance(p.destination.x, p.destination.y, p.destination.z) < 15) return false;
            if (!ValidateEncounterDestination(ai, p)) return false;
            return tag != 28217 || LocalCircleRoute(ai, p,
                {{{boss->GetPositionX(), boss->GetPositionY(), boss->GetPositionZ()}, 15}});
        };
        if (bot->movespline && !bot->movespline->Finalized())
        {
            const auto end = bot->movespline->FinalDestination();
            if (std::fabs(std::hypot(end.x - x, end.y - y) - radius) < 2)
            {
                p.destination = {end.x, end.y, end.z};
                if (valid()) return true; // keep a valid in-flight leg rather than changing it every tick.
            }
        }
        const float a = std::atan2(bot->GetPositionY() - y, bot->GetPositionX() - x);
        const int nearest = int(std::round(a / (M_PI_F / 4)));
        for (unsigned step = 1; step <= 8; ++step)
        {
            const float next = (nearest + int(step)) * (M_PI_F / 4);
            p.destination = {x + radius * std::cos(next), y + radius * std::sin(next), bot->GetPositionZ()};
            if (valid()) return true;
        }
        p.active = false; return false;
    }
    const char* ResistanceDuty(PlayerbotAI* ai)
    {
        if (!Ready(ai) || ai->GetBot()->GetMapId() != 469) return nullptr;
        bool fire = false;
        for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets", "100:1")->Get())
        {
            Unit* enemy = ai->GetUnit(guid);
            if (!Engaged(ai->GetBot(), enemy)) continue;
            const uint32 entry = enemy->GetEntry();
            fire |= entry == 12435 || entry == 13020 || entry == 12017 || entry == 11983 || entry == 11981;
        }
        if (!fire) return nullptr;
        Player* bot = ai->GetBot();
        const uint8 subgroup = bot->GetGroup()->GetMemberGroup(bot->GetObjectGuid());
        for (uint8 cls : {uint8(CLASS_PALADIN), uint8(CLASS_SHAMAN)})
        {
            Player* provider = nullptr;
            bool providerActive = false;
            const uint32 paladin[] = {19891, 19899, 19900};
            const uint32 shaman[] = {8184, 10537, 10538};
            const uint32* ranks = cls == CLASS_PALADIN ? paladin : shaman;
            for (Player* member : Members(ai))
            {
                if (member->getClass() != cls || member->GetGroup()->GetMemberGroup(member->GetObjectGuid()) != subgroup) continue;
                bool active = false;
                for (unsigned i = 0; i < 3; ++i)
                    active |= member->GetSpellAuraHolder(ranks[i], member->GetObjectGuid()) != nullptr;
                if (cls == CLASS_SHAMAN)
                    if (Totem* totem = member->GetTotem(TOTEM_SLOT_WATER))
                        for (unsigned i = 0; i < 3; ++i) active |= totem->GetUInt32Value(UNIT_CREATED_BY_SPELL) == ranks[i];
                // Observe human providers but never make them cast or switch.
                if (active && (!member->GetPlayerbotAI() || member->GetPlayerbotAI()->IsRealPlayer())) return nullptr;
                if (!member->GetPlayerbotAI() || member->GetPlayerbotAI()->IsRealPlayer()) continue;
                const SpellEntry* learned = nullptr;
                for (unsigned i = 0; i < 3; ++i)
                    if (member->HasSpell(ranks[i])) learned = sServerFacade.LookupSpellInfo(ranks[i]);
                if (!learned || (!active && member->GetPower(POWER_MANA) < Spell::CalculatePowerCost(learned, member))) continue;
                if (!active && member->hasUnitState(UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL)) continue;
                if (!provider || (active && !providerActive) || (active == providerActive && member->GetObjectGuid() < provider->GetObjectGuid()))
                { provider = member; providerActive = active; }
            }
            if (provider) return provider == bot ? (cls == CLASS_PALADIN ? "fire resistance aura" : "fire resistance totem") : nullptr;
        }
        return nullptr;
    }
}

bool ai::BlackwingSuppressionChaseAllowed(PlayerbotAI* ai, Unit* target)
{
    if (!SuppressionTrash(target) || !SuppressionStationActive(ai)) return true;
    Player* leader = SuppressionLeader(ai);
    Player* bot = ai->GetBot();
    if (PullStrategy* pull = PullStrategy::Get(ai))
        if (pull->IsEncounterPreparationAllowed() && pull->HasPullStarted() && pull->GetTarget() == target)
        {
            const time_t elapsed = time(nullptr) - pull->GetPullStartTime();
            Unit* owner = ai->GetUnit(pull->GetRequester());
            Player* requester = owner && owner->IsPlayer() ? static_cast<Player*>(owner) : nullptr;
            if (elapsed >= 0 && elapsed < pull->GetMaxPullTime() && requester && requester->isRealPlayer() &&
                Member(bot, requester) && CanManageBotCommands(ai, requester)) return true;
        }
    if (ai->IsTank(bot))
    {
        if (Engaged(bot, target)) return true;
        WaitForAttackStrategy* wait = WaitForAttackStrategy::Get(ai);
        return wait && wait->GetExplicitAttackTarget(ai) == target;
    }
    if (!leader || !Engaged(bot, target) || ai->IsRanged(bot) || ai->IsHeal(bot)) return false;
    const float workRadius = SuppressionFlames(ai).empty() ? 6.0f : 20.0f;
    const float reach = std::max(2.0f, target->GetCombatReach() + bot->GetCombatReach() - 1.0f);
    return target->GetDistance(leader) <= workRadius + reach && bot->GetDistance(leader) <= workRadius + reach + 2;
}

ClassicRaidPlan ClassicRaidPlanValue::Calculate()
{
    ClassicRaidPlan plan;
    if (!Ready(ai)) return plan;
    if (NaxxramasRolePlan(ai, plan)) return plan;
    auto nearby = AI_VALUE2(std::list<ObjectGuid>, "possible targets", "100:1");
    if (bot->GetMapId() == 533)
        if (auto* instance = dynamic_cast<ScriptedInstance*>(bot->GetMap()->GetInstanceData()))
            if (instance->GetData(8) == IN_PROGRESS)
                for (uint32 entry : {
#ifdef MANGOSBOT_TWO
                    30549u,
#else
                    16062u,
#endif
                    16063u, 16064u, 16065u})
                    if (Unit* horseman = instance->GetSingleCreatureFromStorage(entry, true))
                        if (Engaged(bot, horseman) && std::find(nearby.begin(), nearby.end(), horseman->GetObjectGuid()) == nearby.end())
                            nearby.push_back(horseman->GetObjectGuid());
    Unit* boss = nullptr;
    Unit* current = ai->GetUnit(AI_VALUE(ObjectGuid, "current target"));
    std::vector<Unit*> horsemen;
    for (ObjectGuid guid : nearby)
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit || !classicraid::Boss(bot->GetMapId(), unit->GetEntry()) || !Engaged(bot, unit)) continue;
        if (bot->GetMapId() == 469 && !Attackable(ai, unit)) continue;
        if (classicraid::HorsemanMark(unit->GetEntry())) horsemen.push_back(unit);
        if (!boss || unit == current || (boss != current && unit->GetObjectGuid() < boss->GetObjectGuid())) boss = unit;
    }
    if (!boss) return plan;
    if (horsemen.size() > 4) return plan;
    if (bot->GetMapId() == 533)
    {
        Unit* feugen = FindBoss(ai, 15930);
        Unit* stalagg = FindBoss(ai, 15929);
        if (!Attackable(ai, feugen)) feugen = nullptr;
        if (!Attackable(ai, stalagg)) stalagg = nullptr;
        if (feugen || stalagg)
        {
            const auto members = Members(ai, ai->IsTank(bot));
            const auto self = std::find(members.begin(), members.end(), bot);
            const size_t slot = self == members.end() ? 0 : size_t(self - members.begin());
            boss = slot % 2 ? stalagg : feugen;
            if (!boss) boss = feugen ? feugen : stalagg;
            if (feugen && stalagg && !ai->IsTank(bot) && !ai->IsHeal(bot) &&
                std::fabs(feugen->GetHealthPercent() - stalagg->GetHealthPercent()) > 15)
                boss = feugen->GetHealthPercent() > stalagg->GetHealthPercent() ? feugen : stalagg;
            if (!ai->IsHeal(bot) && Attackable(ai, boss)) plan.target = boss->GetObjectGuid();
        }
    }
    // Wrath's stationary rear casters and Rivendare need different assignments.
#ifdef MANGOSBOT_TWO
    if (!horsemen.empty())
    {
        BuildWrathHorsemenPlan(ai, horsemen, previousHorseman, plan);
        return plan;
    }
#endif
    // Classic has four melee Horsemen, including Mograine. Their actual marks
    // select relief; no Wrath back-corner ranged tank or invented immunity.
    if (!horsemen.empty())
    {
        std::sort(horsemen.begin(), horsemen.end(), [](Unit* a, Unit* b) { return a->GetEntry() < b->GetEntry(); });
        const auto members = Members(ai, ai->IsTank(bot));
        const auto self = std::find(members.begin(), members.end(), bot);
        const size_t slot = self == members.end() ? 0 : size_t(self - members.begin());
        Unit* assigned = horsemen[slot % horsemen.size()];
        if (ai->IsTank(bot))
        {
            Unit* held = nullptr;
            for (Unit* horseman : horsemen)
                if (horseman->GetVictim() == bot) { held = horseman; previousHorseman = horseman->GetObjectGuid(); }
            if (held) assigned = held; // Never abandon before a real replacement taunt lands.
            else if (!previousHorseman.IsEmpty())
            {
                unsigned marks[4] = {}; int previous = -1;
                for (unsigned i = 0; i < horsemen.size(); ++i)
                { marks[i] = Stacks(bot, horsemen[i]); if (horsemen[i]->GetObjectGuid() == previousHorseman) previous = int(i); }
                const int next = classicraid::ReliefCorner(marks, unsigned(horsemen.size()), previous);
                if (next >= 0) assigned = horsemen[next];
            }
            Unit* victim = assigned->GetVictim();
            const bool hasTank = victim && victim->IsPlayer() && Member(bot, static_cast<Player*>(victim)) && ai->IsTank(static_cast<Player*>(victim));
            unsigned heldCount = 0;
            if (hasTank) for (Unit* horseman : horsemen) heldCount += horseman->GetVictim() == victim ? 1 : 0;
            const bool waiting = !held && (Stacks(bot, assigned) >= 3 ||
                (hasTank && heldCount <= 1 && Stacks(static_cast<Player*>(victim), assigned) < 3));
            if (waiting)
            {
                // Keep relief outside this corner's native mark until needed.
                // Already-safe waiting consumes no action or cast updates.
                const float nativeRadius = NativeEncounterSpellRadius(classicraid::HorsemanMark(assigned->GetEntry()));
                if (nativeRadius > 0 && nativeRadius <= 60)
                {
                    EncounterPosition p; p.active = true; p.map = 533; p.instance = bot->GetInstanceId();
                    p.boss = assigned->GetObjectGuid(); p.spell = classicraid::HorsemanMark(assigned->GetEntry());
                    plan.boss = p.boss; plan.holdDamage = true;
                    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
                    const std::vector<encounter::Circle> marks{{{assigned->GetPositionX(), assigned->GetPositionY(), assigned->GetPositionZ()}, nativeRadius + 2}};
                    if (encounter::OutsideCircles(here, marks)) p.destination = here;
                    else
                    {
                        unsigned checks = 0;
                        for (auto point : encounter::EscapeCircles(here, marks))
                        {
                            if (++checks > 8) break;
                            p.destination = point;
                            if (ValidateEncounterDestination(ai, p)) break;
                        }
                    }
                    if (encounter::OutsideCircles(p.destination, marks) && ValidateEncounterDestination(ai, p)) plan.position = p;
                    return plan;
                }
            }
        }
        else
        {
            if (ai->IsHeal(bot))
            {
                std::vector<Player*> healers;
                for (Player* member : Members(ai)) if (ai->IsHeal(member)) healers.push_back(member);
                const auto selfHealer = std::find(healers.begin(), healers.end(), bot);
                const unsigned home = selfHealer == healers.end() ? 0 : unsigned(selfHealer - healers.begin()) % unsigned(horsemen.size());
                assigned = horsemen[home];
                if (Stacks(bot, assigned) >= 3)
                {
                    unsigned marks[4] = {};
                    for (unsigned i = 0; i < horsemen.size(); ++i) marks[i] = Stacks(bot, horsemen[i]);
                    const int next = classicraid::ReliefCorner(marks, unsigned(horsemen.size()), int(home));
                    if (next >= 0) { assigned = horsemen[next]; goto chosen; }
                }
                else goto chosen;
            }
            // Focus Korth'azz, then Mograine, before the two chain/void bosses.
            for (uint32 entry : {16064u, 16062u, 16065u, 16063u})
                for (Unit* horseman : horsemen)
                    if (horseman->GetEntry() == entry && Stacks(bot, horseman) < 3) { assigned = horseman; goto chosen; }
            // All available marks are high: leave all live mark radii to reset.
            {
                EncounterPosition p; p.active = true; p.map = 533; p.instance = bot->GetInstanceId();
                std::vector<encounter::Circle> marks;
                for (Unit* horseman : horsemen)
                    marks.push_back({{horseman->GetPositionX(), horseman->GetPositionY(), horseman->GetPositionZ()},
                        std::max(45.0f, NativeEncounterSpellRadius(classicraid::HorsemanMark(horseman->GetEntry()))) + 2});
                const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
                unsigned checks = 0;
                for (auto point : encounter::EscapeCircles(here, marks))
                {
                    if (++checks > 8) break;
                    p.destination = point;
                    if (encounter::OutsideCircles(point, marks) && ValidateEncounterDestination(ai, p))
                    { plan.position = p; plan.emergency = true; plan.holdDamage = true; return plan; }
                }
            }
        }
chosen:
        boss = assigned;
        if (!ai->IsHeal(bot)) plan.target = boss->GetObjectGuid();
        if (ai->IsTank(bot) && boss->GetVictim() == bot)
        {
            EncounterPosition p; p.active = true; p.map = 533; p.instance = bot->GetInstanceId();
            p.boss = boss->GetObjectGuid(); p.spell = classicraid::HorsemanMark(boss->GetEntry());
            p.destination.z = bot->GetPositionZ();
            if (classicraid::Corner(boss->GetEntry(), p.destination.x, p.destination.y))
            {
                const float dx = p.destination.x - bot->GetPositionX(), dy = p.destination.y - bot->GetPositionY();
                const float distance = std::hypot(dx, dy);
                if (distance > 55) { p.destination.x = bot->GetPositionX() + dx * 55 / distance; p.destination.y = bot->GetPositionY() + dy * 55 / distance; }
                if (ValidateEncounterDestination(ai, p)) plan.position = p;
            }
            plan.boss = boss->GetObjectGuid();
            return plan;
        }
        if (bot->GetDistance(boss) > 45)
        {
            EncounterPosition p; p.active = true; p.map = 533; p.instance = bot->GetInstanceId();
            p.boss = boss->GetObjectGuid(); p.spell = classicraid::HorsemanMark(boss->GetEntry());
            const float dx = boss->GetPositionX() - bot->GetPositionX(), dy = boss->GetPositionY() - bot->GetPositionY();
            const float distance = std::hypot(dx, dy);
            const float leg = std::min(55.0f, std::max(0.0f, distance - 25));
            if (distance > 1)
            {
                p.destination = {bot->GetPositionX() + dx * leg / distance, bot->GetPositionY() + dy * leg / distance, bot->GetPositionZ()};
                if (ValidateEncounterDestination(ai, p)) plan.position = p;
            }
            plan.boss = boss->GetObjectGuid();
            return plan;
        }
    }
    plan.boss = boss->GetObjectGuid();
    const uint32 entry = boss->GetEntry();
    if (entry == 15931 && boss->GetVictim() == bot && !SpecialPosition(ai))
    {
        EncounterPosition p;
        if (RingPosition(ai, boss, 3281.23f, -3310.38f, 35.0f, 28137, p)) plan.position = p;
        return plan;
    }
    if (entry == 15932)
    {
        if (boss->GetVictim() == bot && !SpecialPosition(ai))
        {
            // The 40-player layout separates the boss from the chow circuit.
            // Long approaches use bounded native walking legs, never teleport.
            EncounterPosition p; p.active = true; p.map = 533; p.instance = bot->GetInstanceId();
            p.boss = boss->GetObjectGuid(); p.spell = 28235;
            p.destination = {3331.48f, -3109.06f, bot->GetPositionZ()};
            const float dx = p.destination.x - bot->GetPositionX(), dy = p.destination.y - bot->GetPositionY();
            const float d = std::hypot(dx, dy);
            if (d > 55) { p.destination.x = bot->GetPositionX() + dx * 55 / d; p.destination.y = bot->GetPositionY() + dy * 55 / d; }
            if (ValidateEncounterDestination(ai, p)) plan.position = p;
            return plan;
        }
        if (GluthKiter(ai, boss) == bot)
        {
            Unit* chow = nullptr;
            bool pursued = false;
            for (ObjectGuid guid : nearby)
            {
                Unit* unit = ai->GetUnit(guid);
                if (!Attackable(ai, unit) || unit->GetEntry() != 16360 || unit->GetHealthPercent() <= 5.1f ||
                    unit->GetUInt32Value(UNIT_CREATED_BY_SPELL) != 28217) continue;
                Unit* source = ai->GetUnit(unit->GetSpawnerGuid());
                if (!Live(bot, source) || source->GetEntry() != 15384 || source->GetDistance(boss) > 100) continue;
                pursued |= unit->GetVictim() == bot;
                if (!chow || (unit->GetVictim() != bot && chow->GetVictim() == bot) ||
                    (unit->GetVictim() != bot && unit->GetObjectGuid() < chow->GetObjectGuid())) chow = unit;
            }
            if (chow)
            {
                plan.target = chow->GetObjectGuid();
                if (pursued)
                {
                    EncounterPosition p;
                    if (RingPosition(ai, boss, 3293.61f, -3149.01f, 12.0f, 28217, p)) plan.position = p;
                }
                return plan;
            }
        }
    }
    if (entry == 12460 && boss->GetVictim() == bot && ai->IsTank(bot) && !SpecialPosition(ai))
    {
        std::vector<encounter::Circle> others;
        for (ObjectGuid guid : nearby)
        {
            Unit* other = ai->GetUnit(guid);
            if (!Engaged(bot, other) || other == boss || other->GetEntry() != 12460 ||
                !(other->GetObjectGuid() < boss->GetObjectGuid())) continue;
            Unit* victim = other->GetVictim();
            if (!victim || !victim->IsPlayer() || !Member(bot, static_cast<Player*>(victim)) ||
                !ai->IsTank(static_cast<Player*>(victim)) || other->GetDistance(bot) >= 18) continue;
            others.push_back({{other->GetPositionX(), other->GetPositionY(), other->GetPositionZ()}, 18});
        }
        if (!others.empty())
        {
            // Stable GUID precedence: one holder moves, the older lane stays
            // anchored. Both tanks must not repeatedly flee from each other.
            EncounterPosition p; p.active = true; p.map = 469; p.instance = bot->GetInstanceId();
            p.boss = boss->GetObjectGuid(); p.spell = 12460;
            unsigned checks = 0;
            const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
            for (auto point : encounter::EscapeCircles(here, others))
            {
                if (++checks > 8) break;
                p.destination = point;
                if (encounter::OutsideCircles(point, others) && ValidateEncounterDestination(ai, p) && LocalCircleRoute(ai, p, others))
                { plan.position = p; return plan; }
            }
        }
    }
    // Native rescue/phase add selectors already handle Maexxna, Gluth,
    // Ayamiss, Thekal, Twins, Hakkar, Jin'do and other ZG/AQ adds.
    if (bot->GetMapId() == 533 && !ai->IsHeal(bot) && boss->GetVictim() != bot && horsemen.empty())
    {
        Unit* selected = nullptr; unsigned priority = 0;
        for (ObjectGuid guid : nearby)
        {
            Unit* add = ai->GetUnit(guid);
            if (!Attackable(ai, add) || add->GetDistance(boss) > 100) continue;
            const unsigned rank = classicraid::AddPriority(entry, add->GetEntry(), boss->HasAura(28798), add->GetHealthPercent() <= 5.1f);
            if (!rank) continue;
            // Controlled human/bot worshippers/understudies are never attackable.
            if (!selected || rank > priority || (rank == priority && (add == current ||
                (selected != current && add->GetObjectGuid() < selected->GetObjectGuid()))))
            { selected = add; priority = rank; }
        }
        if (selected) plan.target = selected->GetObjectGuid();
    }
    if (entry == 15953 && !ai->IsHeal(bot) && boss->GetVictim() != bot)
        if (Unit* sacrifice = FaerlinaSacrifice(ai, boss)) plan.target = sacrifice->GetObjectGuid();
    if ((entry == 15953 || entry == 16061) && !ai->IsTank(bot) && !ai->IsHeal(bot) &&
        plan.target.IsEmpty() && Attackable(ai, boss)) plan.target = boss->GetObjectGuid();
    Unit* target = ai->GetUnit(plan.target);
    if (!target) target = current && Attackable(ai, current) ? current : boss;
    if (SpecialPosition(ai) || !ai->CanMove() || bot->GetCharm()) return plan;
    if (entry == 15928 && !bot->HasAura(28059) && !bot->HasAura(28084) &&
        !bot->CanReachWithMeleeAttack(boss) && std::fabs(bot->GetPositionZ() - boss->GetPositionZ()) > 3)
    {
        // Transition from the native add ledges. Submit an ordinary validated
        // jump through the existing trajectory/landing machinery, never teleport.
        const float r = std::max(3.0f, boss->GetCombatReach() + bot->GetCombatReach() - 1);
        const float a = boss->GetAngle(bot);
        EncounterPosition p; p.active = true; p.map = 533; p.instance = bot->GetInstanceId();
        p.boss = boss->GetObjectGuid(); p.spell = 15928;
        p.destination = {boss->GetPositionX() + r * std::cos(a), boss->GetPositionY() + r * std::sin(a), boss->GetPositionZ()};
        if (ValidateEncounterDestination(ai, p, false)) plan.position = p;
        return plan;
    }
    if (entry == 16011 && !ai->IsTank(bot) && !ai->IsHeal(bot) && !bot->HasAura(29232))
    {
        Unit* spore = nullptr;
        for (ObjectGuid guid : nearby)
        {
            Unit* candidate = ai->GetUnit(guid);
            if (Spore(ai, candidate) && (!spore || candidate->GetObjectGuid() < spore->GetObjectGuid())) spore = candidate;
        }
        if (spore)
        {
            const float radius = NativeEncounterSpellRadius(29232);
            if (radius > 0 && radius <= 30)
            {
                bool assembled = false;
                const auto dps = SporeRecipients(ai, spore, assembled);
                if (std::find(dps.begin(), dps.end(), bot) != dps.end())
                {
                    plan.target = assembled ? spore->GetObjectGuid() : boss->GetObjectGuid();
                    EncounterPosition p; p.active = true; p.map = 533; p.instance = bot->GetInstanceId();
                    p.boss = boss->GetObjectGuid(); p.source = spore->GetObjectGuid();
                    p.destination = {spore->GetPositionX(), spore->GetPositionY(), bot->GetPositionZ()};
                    if (ValidateEncounterDestination(ai, p)) plan.position = p;
                    return plan;
                }
            }
        }
    }
    if (entry == 16061 && !naxxnative::ObedienceCrystal(NaxxRegular(ai)) &&
        bot->getClass() == CLASS_PRIEST) return plan; // Priest controller must hold its native channel.
    if (entry == 15989 && boss->HasAura(18430)) return plan;
    if (entry == 15928 || entry == 16060) return plan; // Phase-specific platforms/gate retain native travel.
    if (BroodlordFormationPlan(ai, boss, target, plan)) return plan;
    if (SuppressionCombatStation(ai, boss, target, plan)) return plan;
    const bool ranged = ai->IsRanged(bot) || ai->IsHeal(bot);
    Unit* anchor = target;
    if (ai->IsHeal(bot))
    {
        Unit* victim = boss->GetVictim();
        if (Live(bot, victim) && (victim->IsPlayer() || victim->GetCharmer())) anchor = victim;
    }
    const float radius = ranged ? Range(ai, anchor) : std::max(2.0f, target->GetCombatReach() + bot->GetCombatReach() - 1.0f);
    const encounter::Point here{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    const bool front = classicraid::Front(target->GetEntry()) && target->GetVictim() != bot;
    const float angle = target->GetAngle(bot) - target->GetOrientation();
    const bool unsafe = front && (classicraid::Dragon(target->GetEntry()) ? std::fabs(std::cos(angle)) > 0.70710678f : std::cos(angle) > 0);
    float spacing = entry == 15990 ? 10.0f : entry == 16063 ? 8.0f : ranged ? 5.0f : 0.0f;
    // Korth'azz's meteor is shared. Melee and its tank stack, never generic spread.
    if (entry == 16064 && !ranged) spacing = 0;
    std::vector<encounter::Point> neighbors;
    for (Player* member : Members(ai))
        if (member != bot) neighbors.push_back({member->GetPositionX(), member->GetPositionY(), member->GetPositionZ()});
    auto separated = [&](const encounter::Point& p) {
        for (auto q : neighbors) if (encounter::Distance2d(p, q) < spacing && std::fabs(p.z - q.z) < 8) return false;
        return true;
    };
    EncounterPosition p; p.active = true; p.exclusive = false; p.map = bot->GetMapId();
    p.instance = bot->GetInstanceId(); p.boss = boss->GetObjectGuid(); p.source = anchor->GetObjectGuid(); p.destination = here;
    // Holding the boss keeps native tank orientation; spare tanks participate
    // from a legal melee flank instead of standing at a ranged formation.
    if (boss->GetVictim() == bot) return plan;
    if (KeepFormationRoute(ai, target, anchor, p, radius, ranged, front, neighbors, spacing))
    { plan.position = p; plan.emergency = unsafe; return plan; }
    if (!unsafe && separated(here) && (ranged ? (anchor->GetDistance(bot) >= radius - 8 &&
        PositionLegal(ai, anchor, p, radius + 2)) : bot->CanReachWithMeleeAttack(target))) return plan;
    const float side = std::sin(angle) >= 0 ? 1.0f : -1.0f;
    const float base = front ? target->GetOrientation() + side * float(M_PI) * (classicraid::Dragon(target->GetEntry()) ? 2.0f / 3.0f : 0.85f) : target->GetAngle(bot);
    for (unsigned i = 0; i < 16; ++i)
    {
        const float offset = i == 0 ? 0 : ((i + 1) / 2) * 0.18f * (i % 2 ? 1 : -1);
        const float a = base + offset;
        if (front && (classicraid::Dragon(target->GetEntry()) ? std::fabs(std::cos(a - target->GetOrientation())) > 0.70710678f : std::cos(a - target->GetOrientation()) > 0)) continue;
        p.destination = {target->GetPositionX() + radius * std::cos(a), target->GetPositionY() + radius * std::sin(a), here.z};
        if (separated(p.destination) && PositionLegal(ai, anchor, p, ranged ? radius + 2 : radius + 3))
        { plan.position = p; plan.emergency = unsafe; return plan; }
    }
    return plan;
}

bool ClassicRaidPositionAction::GetPlan(PlayerbotAI* ai, ClassicRaidPlan& plan)
{
    if (!Ready(ai) || SpecialPosition(ai) || ai->GetBot()->GetCharm()) return false;
    plan = ai->GetAiObjectContext()->GetValue<ClassicRaidPlan>("classic raid plan")->Get();
    if (!plan.position.active || plan.position.map != ai->GetBot()->GetMapId() ||
        plan.position.instance != ai->GetBot()->GetInstanceId()) return false;
    Unit* boss = ai->GetUnit(plan.boss);
    if (!boss) return plan.boss.IsEmpty() && plan.emergency && ai->GetBot()->GetMapId() == 533 &&
        (ai->GetBot()->HasAura(28832) || ai->GetBot()->HasAura(28833) || ai->GetBot()->HasAura(28834) || ai->GetBot()->HasAura(28835));
    // Recalculate after a fear/knockback, target change, boss turn or relocation.
    if (!Engaged(ai->GetBot(), boss)) return false;
    if (plan.position.spell == 179784)
    {
        Player* leader = SuppressionLeader(ai);
        return SuppressionTrash(boss) && SuppressionStationActive(ai) &&
            (leader ? plan.position.source == leader->GetObjectGuid() : plan.position.source.IsEmpty());
    }
    if (boss->GetVictim() == ai->GetBot())
        return (plan.position.spell == 12017 && boss->GetEntry() == 12017) ||
            (plan.position.spell == 12460 && boss->GetEntry() == 12460) ||
            (plan.position.spell == 28137 && boss->GetEntry() == 15931) ||
            (plan.position.spell == 28235 && boss->GetEntry() == 15932) ||
            (classicraid::HorsemanMark(boss->GetEntry()) && plan.position.spell == classicraid::HorsemanMark(boss->GetEntry()));
    return true;
}

bool ai::ClassicRaidDamageSpell(const SpellEntry* spell) { return RaidDamageSpell(spell); }

bool ai::ClassicRaidOffenseAllowed(PlayerbotAI* ai, const SpellEntry* spell, Unit* target)
{
    if (!Ready(ai) || ai->GetBot()->GetMapId() != 533) return true;
    Player* bot = ai->GetBot();
    const bool damage = !spell || RaidDamageSpell(spell); // nullptr is native melee/pet attack admission.
    const bool cleaveBuff = spell && (spell->Id == 13877 || spell->Id == 12328);
    if (!damage && !cleaveBuff) return true; // heals, CC and native taunts remain admitted normally.
    const bool area = spell && (IsAreaOfEffectSpell(spell) || spell->MaxAffectedTargets > 1 || cleaveBuff);
    for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets", "100:1")->Get())
    {
        Unit* reserved = ai->GetUnit(guid);
        if (Live(bot, reserved) && reserved->GetEntry() == 16286 &&
            reserved->GetUInt32Value(UNIT_CREATED_BY_SPELL) == 29234)
        {
            Unit* source = ai->GetUnit(reserved->GetSpawnerGuid());
            if (source && source->GetEntry() == 16011 && Engaged(bot, source))
            {
                if (area) return false; // do not pop another group's spore with splash.
                if (target == reserved)
                {
                    bool assembled = false;
                    const auto recipients = SporeRecipients(ai, reserved, assembled);
                    if (!assembled || std::find(recipients.begin(), recipients.end(), bot) == recipients.end()) return false;
                }
            }
        }
        if (!Live(bot, reserved) || (reserved->GetEntry() != 16506 && reserved->GetEntry() != 16803)) continue;
        Unit* boss = FindBoss(ai, reserved->GetEntry() == 16506 ? 15953 : 16061);
        if (!boss || reserved->GetDistance(boss) > 80) continue;
        if (target == reserved && reserved->GetEntry() == 16506 &&
            FaerlinaSacrifice(ai, boss) == reserved && !area) continue;
        if (target == reserved && (!ai->IsTank(bot) || reserved->GetHealthPercent() <= 50)) return false;
        // All classes' damaging AoE/proc-cleave admission reserves the actual
        // Classic control actors. No disease/curse removal or taunt is blocked.
        if (area) return false;
    }
    return true;
}
bool ClassicRaidPositionAction::isUseful()
{
    ClassicRaidPlan plan;
    return GetPlan(ai, plan) && EncounterMovementRequired(bot, plan.position.destination);
}
bool ClassicRaidPositionAction::ShouldReactionInterruptCast() const
{
    ClassicRaidPlan plan;
    return GetPlan(ai, plan) && plan.emergency && EncounterMovementRequired(bot, plan.position.destination);
}
bool ClassicRaidPositionAction::Execute(Event& event)
{
    ClassicRaidPlan plan;
    if (!GetPlan(ai, plan) || !ai->CanMove() || (!plan.emergency && bot->IsNonMeleeSpellCasted(false)) ||
        !ValidateEncounterDestination(ai, plan.position, plan.position.spell != 15928)) return false;
    if (plan.holdDamage)
    {
        bot->AttackStop();
        if (Pet* pet = bot->GetPet())
        {
            WorldPacket follow(CMSG_PET_ACTION);
            follow << pet->GetObjectGuid() << uint32((ACT_COMMAND << 24) | COMMAND_FOLLOW) << ObjectGuid();
            bot->GetSession()->HandlePetAction(follow);
        }
    }
    if (!EncounterMovementRequired(bot, plan.position.destination)) return false;
    const auto& p = plan.position.destination;
    if (plan.position.spell == 179784 && plan.position.map == 469 && bot->GetDistance(p.x, p.y, p.z) <= 1.5f)
    {
        ai->StopMoving(); // Cancel only the obsolete suppression formation leg.
        return true;
    }
    if (plan.position.spell == 15928)
    {
        AI_VALUE(PositionMap&, "position")["classic thaddius"].Set(p.x, p.y, p.z, plan.position.map);
        return ai->DoSpecificAction("jump::position classic thaddius", Event(), true);
    }
    return MoveTo(plan.position.map, p.x, p.y, p.z, false, IsReaction(), false, true);
}
Unit* ClassicRaidTargetAction::GetTarget()
{
    if (!Ready(ai) || ai->IsHeal(bot)) return nullptr;
    Unit* target = ai->GetUnit(AI_VALUE(ClassicRaidPlan, "classic raid plan").target);
    return Attackable(ai, target) || Spore(ai, target) ? target : nullptr;
}
bool ClassicRaidTargetAction::isUseful()
{
    Unit* target = GetTarget();
    return target && target != ai->GetUnit(AI_VALUE(ObjectGuid, "current target"));
}

bool ClassicRaidSupportAction::Select(std::string& spell, Unit*& target)
{
    if (!Ready(ai) || bot->GetCharm()) return false;
    if (NaxxramasRoleSupport(ai, spell, target)) return true;
    auto cast = [&](const char* name, Unit* unit) {
        if (!unit || !ai->CanCastSpell(name, unit, 0)) return false;
        spell = name; target = unit; return true;
    };
    if (ai->IsHeal(bot) && bot->GetMapId() == 533)
    {
        const ClassicRaidPlan plan = AI_VALUE(ClassicRaidPlan, "classic raid plan");
        Unit* horseman = ai->GetUnit(plan.boss);
        Unit* patient = horseman && classicraid::HorsemanMark(horseman->GetEntry()) ? horseman->GetVictim() : nullptr;
        if (patient && patient->IsPlayer() && Member(bot, static_cast<Player*>(patient)) && patient->GetHealthPercent() < 90)
            for (const char* name : {"greater heal", "healing wave", "healing touch", "holy light", "flash heal", "flash of light"})
                if (cast(name, patient)) return true;
        if (FindBoss(ai, 16061))
            for (Player* owner : Members(ai))
            {
                Unit* student = owner->GetCharm();
                if (!student || student->GetEntry() != 16803 || !student->IsInWorld() || !student->IsAlive() ||
                    !owner->IsInMap(student) || !student->HasCharmer(owner->GetObjectGuid()) || student->GetHealthPercent() >= 80) continue;
                for (const char* name : {"greater heal", "healing wave", "healing touch", "holy light", "flash heal", "flash of light"})
                    if (cast(name, student)) return true;
            }
    }
    if (bot->GetMapId() == 469 && bot->getClass() == CLASS_MAGE && bot->HasAura(23410) &&
        FindBoss(ai, 11583) && cast("ice block", bot)) return true;
    if (Unit* gluth = FindBoss(ai, 15932))
    {
        if (GluthTankRelief(ai, gluth))
        {
            for (const char* name : {"taunt", "growl", "dark command", "hand of reckoning"})
                if (cast(name, gluth)) return true;
            if (Unit* victim = gluth->GetVictim()) if (cast("righteous defense", victim)) return true;
        }
        if ((gluth->HasAura(28371) || gluth->HasAura(54427)) && cast("tranquilizing shot", gluth)) return true;
        for (ObjectGuid guid : AI_VALUE2(std::list<ObjectGuid>, "possible targets", "100:1"))
        {
            Unit* chow = ai->GetUnit(guid);
            if (!Attackable(ai, chow) || chow->GetEntry() != 16360 || chow->GetHealthPercent() <= 5.1f ||
                chow->GetUInt32Value(UNIT_CREATED_BY_SPELL) != 28217 || chow->GetDistance(gluth) > 100 ||
                chow->GetTotalAuraModifier(SPELL_AURA_MOD_DECREASE_SPEED) < 0) continue;
            for (const char* name : {"concussive shot", "frostbolt"}) if (cast(name, chow)) return true;
        }
        // Classic traps cannot be placed in combat. Keep native admission,
        // rather than importing Wrath's unconditional combat Frost Trap cast.
    }
    if (Unit* onyxia = FindBoss(ai, 10184))
        if (Unit* tank = onyxia->GetVictim())
            if (Member(bot, tank->IsPlayer() ? static_cast<Player*>(tank) : nullptr) && !ai->HasAura("fear ward", tank) && cast("fear ward", tank)) return true;
    if (Unit* boss = FindBoss(ai, 15990))
        for (auto slot : {CURRENT_GENERIC_SPELL, CURRENT_CHANNELED_SPELL})
        {
            const Spell* active = boss->GetCurrentSpell(slot);
            if (!active || !active->m_spellInfo || active->getState() == SPELL_STATE_FINISHED ||
                (active->m_spellInfo->Id != 28478 && active->m_spellInfo->Id != 28479 &&
                    active->m_spellInfo->Id != 55802)) continue;
            for (const char* name : {"kick", "pummel", "shield bash", "counterspell", "wind shear", "mind freeze", "earth shock"})
                if (cast(name, boss)) return true;
        }
    auto members = Members(ai);
    std::sort(members.begin(), members.end(), [](Player* a, Player* b) { return a->GetHealthPercent() < b->GetHealthPercent(); });
    // Actual native dispel types; injection, polarity, Hakkar poison and other
    // deliberate encounter auras remain governed by existing dispel policy.
    for (Player* member : members)
        for (uint32 id : {29213u, 28776u, 54121u, 28542u, 28167u})
        {
            const SpellEntry* aura = member->HasAura(id) ? sServerFacade.LookupSpellInfo(id) : nullptr;
            if (!aura) continue;
            const char* spells[4] = {};
            if (aura->Dispel == DISPEL_CURSE) { spells[0] = "remove lesser curse"; spells[1] = "remove curse"; }
            if (aura->Dispel == DISPEL_POISON) { spells[0] = "abolish poison"; spells[1] = "cleanse"; spells[2] = "purify"; }
            if (aura->Dispel == DISPEL_DISEASE) { spells[0] = "abolish disease"; spells[1] = "cleanse"; spells[2] = "purify"; }
            if (aura->Dispel == DISPEL_MAGIC) { spells[0] = "dispel magic"; spells[1] = "cleanse"; }
            for (const char* name : spells) if (name && cast(name, member)) return true;
        }
#ifdef MANGOSBOT_TWO
    if (Unit* relief = WrathHorsemanReliefTarget(ai))
        for (const char* name : {"taunt", "growl", "dark command", "hand of reckoning"})
            if (cast(name, relief)) return true;
#endif
    for (ObjectGuid guid : AI_VALUE2(std::list<ObjectGuid>, "possible targets", "100:1"))
    {
        Unit* boss = ai->GetUnit(guid);
#ifdef MANGOSBOT_TWO
        if (bot->GetMapId() == 533) continue; // Wrath's native front-pair relief is handled above.
#endif
        if (!Engaged(bot, boss) || !classicraid::HorsemanMark(boss->GetEntry()) || !ai->IsTank(bot)) continue;
        Unit* victim = boss->GetVictim();
        if (!victim || !victim->IsPlayer() || !Member(bot, static_cast<Player*>(victim)) || victim == bot || Stacks(bot, boss) != 0) continue;
        unsigned heldCount = 0;
        for (ObjectGuid otherGuid : AI_VALUE2(std::list<ObjectGuid>, "possible targets", "100:1"))
        {
            Unit* other = ai->GetUnit(otherGuid);
            if (Engaged(bot, other) && classicraid::HorsemanMark(other->GetEntry()) && other->GetVictim() == victim) ++heldCount;
        }
        if (heldCount <= 1 && Stacks(static_cast<Player*>(victim), boss) < 3) continue;
        // Elect only the closest clean bot tank; native taunt can still miss.
        Player* selected = nullptr;
        for (Player* tank : Members(ai, true))
            if (tank != victim && tank->GetPlayerbotAI() && !tank->GetPlayerbotAI()->IsRealPlayer() &&
                tank->GetVictim() == boss && !Stacks(tank, boss) && tank->CanReachWithMeleeAttack(boss) &&
                (!selected || tank->GetObjectGuid() < selected->GetObjectGuid())) selected = tank;
        if (selected == bot)
            for (const char* name : {"taunt", "growl"}) if (cast(name, boss)) return true;
    }
    if (const char* duty = ResistanceDuty(ai))
        if (Action* delegate = ai->GetAiObjectContext()->GetAction(duty))
            if (delegate->isUseful() && delegate->isPossible()) { spell = duty; target = bot; return true; }
    return false;
}
bool ClassicRaidSupportAction::isUseful() { std::string spell; Unit* target = nullptr; return Select(spell, target); }
bool ClassicRaidSupportAction::Execute(Event& event)
{
    std::string spell; Unit* target = nullptr;
    if (!Select(spell, target) || bot->IsNonMeleeSpellCasted(false)) return false;
    if (spell == "fire resistance aura" || spell == "fire resistance totem")
    {
        Action* delegate = ai->GetAiObjectContext()->GetAction(spell);
        return delegate && delegate->isUseful() && delegate->isPossible() && delegate->Execute(event);
    }
    uint32 duration = sPlayerbotAIConfig.globalCoolDown;
    if (!ai->CastSpell(spell, target, nullptr, false, &duration)) return false;
    SetDuration(duration); return true;
}

Unit* ClassicRaidControlAction::SelectUnderstudy()
{
    if (!Ready(ai) || bot->GetMapId() != 533 || bot->GetCharm()) return nullptr;
    if (!NaxxramasControlAllowed(ai)) return nullptr;
    Unit* boss = FindBoss(ai, 16061);
    if (!boss) boss = FindBoss(ai, 15953);
    if (!boss) return nullptr;
    const bool faerlina = boss->GetEntry() == 15953;
    const bool crystal = !faerlina && naxxnative::ObedienceCrystal(NaxxRegular(ai));
    if (faerlina && (naxxnative::WorshipperDeathEmbrace(NaxxRegular(ai)) ||
        !boss->HasAura(naxxnative::FaerlinaFrenzy(NaxxRegular(ai))))) return nullptr;
    if (!crystal && (bot->getClass() != CLASS_PRIEST || !bot->HasSpell(naxxnative::MindControl()))) return nullptr;
    std::vector<Unit*> students;
    for (ObjectGuid guid : AI_VALUE2(std::list<ObjectGuid>, "possible targets", "100:1"))
    {
        Unit* student = ai->GetUnit(guid);
        if (Live(bot, student) && student->GetEntry() == (faerlina ? 16506 : 16803) && student->GetDistance(boss) < 80 &&
            !PossibleAttackTargetsValue::HasBreakableCC(student, bot)) students.push_back(student);
    }
    std::sort(students.begin(), students.end(), [](Unit* a, Unit* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
    std::vector<Player*> priests;
    unsigned controlled = 0;
    const SpellEntry* mindControl = sServerFacade.LookupSpellInfo(naxxnative::MindControl());
    for (Player* member : Members(ai))
    {
        Unit* charm = member->GetCharm();
        if (charm && charm->GetEntry() == (faerlina ? 16506 : 16803) && charm->IsInWorld() &&
            charm->IsAlive() && member->IsInMap(charm) &&
            charm->HasCharmer(member->GetObjectGuid())) { ++controlled; continue; }
        if (member->GetCharm() || member->hasUnitState(UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL)) continue;
        // Count a real in-flight control cast as a reservation, so later bot
        // updates do not nominate additional priests for the same free actor.
        bool claiming = false;
        for (auto slot : {CURRENT_GENERIC_SPELL, CURRENT_CHANNELED_SPELL})
            if (const Spell* cast = member->GetCurrentSpell(slot))
                if (cast->m_spellInfo && cast->m_spellInfo->Id == naxxnative::MindControl() &&
                    cast->getState() != SPELL_STATE_FINISHED)
                    if (Unit* target = cast->m_targets.getUnitTarget())
                        if (target->GetEntry() == (faerlina ? 16506 : 16803) && Live(bot, target))
                        {
                            ++controlled; claiming = true;
                            students.erase(std::remove(students.begin(), students.end(), target), students.end());
                        }
        if (claiming || member->IsNonMeleeSpellCasted(false) ||
            !member->GetPlayerbotAI() || member->GetPlayerbotAI()->IsRealPlayer()) continue;
        if (crystal ? ai->IsTank(member) : (mindControl && member->getClass() == CLASS_PRIEST &&
            member->HasSpell(naxxnative::MindControl()) && member->IsSpellReady(*mindControl) &&
            member->GetPower(POWER_MANA) >= Spell::CalculatePowerCost(mindControl, member))) priests.push_back(member);
    }
    const unsigned required = faerlina ? 1 : 2;
    if (controlled >= required || priests.empty()) return nullptr;
    const auto self = std::find(priests.begin(), priests.end(), bot);
    const size_t slot = self == priests.end() ? priests.size() : size_t(self - priests.begin());
    if (slot >= required - controlled || slot >= students.size()) return nullptr;
    if (crystal)
    {
        std::vector<Unit*> crystals;
        for (ObjectGuid guid : AI_VALUE2(std::list<ObjectGuid>, "possible targets", "100:1"))
        {
            Unit* unit = ai->GetUnit(guid);
            if (Live(bot, unit) && unit->GetEntry() == 29912 && !unit->IsInCombat() &&
                !unit->IsNonMeleeSpellCasted(true) && unit->GetDistance(boss) < 80) crystals.push_back(unit);
        }
        std::sort(crystals.begin(), crystals.end(), [](Unit* a, Unit* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        return slot < crystals.size() ? crystals[slot] : nullptr;
    }
    return students[slot];
}
bool ClassicRaidControlAction::isUseful() { return SelectUnderstudy() != nullptr; }
bool ClassicRaidControlAction::Execute(Event& event)
{
    Unit* student = SelectUnderstudy();
    if (!student || bot->IsNonMeleeSpellCasted(false)) return false;
#ifdef MANGOSBOT_TWO
    if (student->GetEntry() == 29912)
    {
        if (!bot->IsWithinDistInMap(student, INTERACTION_DISTANCE) || !bot->IsWithinLOSInMap(student))
            return MoveNear(student, INTERACTION_DISTANCE - 1);
        const uint32 now = WorldTimer::getMSTime();
        if (static_cast<int32>(nextControl - now) > 0) return false;
        nextControl = now + 1000;
        WorldPacket packet(CMSG_SPELLCLICK);
        packet << student->GetObjectGuid();
        bot->GetSession()->HandleSpellClick(packet);
        SetDuration(300);
        // Native spellclick may reject or find no free student; do not report
        // ownership or suppress the class rotation until the charm is real.
        return bot->GetCharm() && bot->GetCharm()->GetEntry() == 16803 &&
            bot->GetCharm()->HasCharmer(bot->GetObjectGuid());
    }
#endif
    if (ai->CanCastSpell("mind control", student, 0))
    {
        uint32 duration = sPlayerbotAIConfig.globalCoolDown;
        if (!ai->CastSpell("mind control", student, nullptr, false, &duration)) return false;
        SetDuration(duration); return true;
    }
    return MoveNear(student, 18.0f);
}
bool ClassicRaidControlAction::UpdateControl()
{
    Unit* charm = bot->GetCharm();
    if (!charm || !charm->IsInWorld() || !charm->IsAlive() || !bot->IsInMap(charm) ||
        !charm->HasCharmer(bot->GetObjectGuid()))
    {
        configuredCharm.Clear(); nextControl = 0;
        return false;
    }
    if (!Ready(ai) || bot->GetMapId() != 533 ||
        (bot->getClass() != CLASS_PRIEST && !naxxnative::ObedienceCrystal(NaxxRegular(ai)))) return false;
    if (charm->GetEntry() != 16803 && charm->GetEntry() != 16506) return false;
    Unit* boss = FindBoss(ai, charm->GetEntry() == 16803 ? 16061 : 15953);
    if (!boss) return false; // Native channel/cleanup completes normally after death/reset.
    if (configuredCharm != charm->GetObjectGuid())
    {
        configuredCharm = charm->GetObjectGuid(); nextControl = 0;
        // Native charm initialization enables autocastable spells. Disable
        // only our managed abilities through the ordinary ownership-checked
        // packet, so PetAI cannot race the explicit raid timing/controller.
        for (uint32 id : {29061u, 29060u, naxxnative::FaerlinaEmbrace(NaxxRegular(ai))})
            if (charm->HasSpell(id) && IsAutocastable(id))
            {
                WorldPacket packet(CMSG_PET_SPELL_AUTOCAST);
                packet << charm->GetObjectGuid() << id << uint8(0);
                bot->GetSession()->HandlePetSpellAutocastOpcode(packet);
            }
    }
    const uint32 now = WorldTimer::getMSTime();
    if (static_cast<int32>(nextControl - now) > 0) return true;
    nextControl = now + 300;
    if (charm->GetEntry() == 16506)
    {
        // Classic/TBC and Wrath25 use the actual possessed worshipper ability.
        // Wrath10 instead reserves one nearby worshipper for death sacrifice.
        const uint32 embrace = naxxnative::FaerlinaEmbrace(NaxxRegular(ai));
        if (!naxxnative::WorshipperDeathEmbrace(NaxxRegular(ai)) &&
            boss->HasAura(naxxnative::FaerlinaFrenzy(NaxxRegular(ai))) &&
            ControlledInRadius(ai, charm, boss, NativeEncounterSpellRadius(embrace)))
            SubmitControlledSpell(bot, charm, embrace, nullptr);
        return true;
    }
    // Two native controlled students alternate on real Shield Wall expiry.
    // Elect one activation so both do not spend the wall on the same frame.
    // Never renew/strip MC or alter the boss threat table.
    Unit* victim = boss->GetVictim();
    const bool relief = !victim || victim->GetEntry() != 16803 || !victim->HasAura(29061);
    if (charm->GetVictim() != boss)
    {
        WorldPacket attack(CMSG_PET_ACTION);
        attack << charm->GetObjectGuid() << uint32((ACT_COMMAND << 24) | COMMAND_ATTACK) << boss->GetObjectGuid();
        bot->GetSession()->HandlePetAction(attack);
    }
    const bool elected = relief && ControlledRelief(ai, boss) == charm;
    if (elected && (!charm->CanReachWithMeleeAttack(boss) || !charm->IsWithinLOSInMap(boss))) return true;
    if (elected && !charm->HasAura(29061) && SubmitControlledSpell(bot, charm, 29061, charm)) return true;
    if (elected && victim != charm && charm->HasAura(29061) && SubmitControlledSpell(bot, charm, 29060, boss)) return true;
    return true;
}

bool ClassicRaidCloakAction::isUseful()
{
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsInCombat() || bot->IsBeingTeleported() ||
        bot->HasCharmer() || bot->GetMapId() != 469 || ai->IsRealPlayer()) return false;
    Item* worn = bot->GetItemByPos(INVENTORY_SLOT_BAG_0, EQUIPMENT_SLOT_BACK);
    Item* cloak = bot->GetItemByEntry(15138);
    uint16 dest;
    return (!worn || worn->GetEntry() != 15138) && cloak &&
        bot->CanEquipItem(EQUIPMENT_SLOT_BACK, dest, cloak, true) == EQUIP_ERR_OK;
}
bool ClassicRaidCloakAction::Execute(Event& event)
{
    if (!isUseful() || bot->IsNonMeleeSpellCasted(false)) return false;
    Item* cloak = bot->GetItemByEntry(15138);
    if (!cloak) return false;
    // Equip only a real owned cloak. Native inventory admission grants its
    // protective aura; no aura, item, old-cloak deletion or GM bypass is added.
    WorldPacket packet(CMSG_AUTOEQUIP_ITEM);
    packet << cloak->GetBagSlot() << cloak->GetSlot();
    bot->GetSession()->HandleAutoEquipItemOpcode(packet);
    Item* worn = bot->GetItemByPos(INVENTORY_SLOT_BAG_0, EQUIPMENT_SLOT_BACK);
    return worn && worn->GetEntry() == 15138;
}

bool ClassicRaidPauseAction::isUseful()
{
    if (!Ready(ai)) return false;
    const bool hold = AI_VALUE(ClassicRaidPlan, "classic raid plan").holdDamage;
    if (hold && bot->GetVictim()) return true;
    if (Pet* pet = bot->GetPet())
        if (pet->GetVictim() && (hold || !ClassicRaidOffenseAllowed(ai, nullptr, pet->GetVictim()))) return true;
    if (bot->GetVictim() && !ClassicRaidOffenseAllowed(ai, nullptr, bot->GetVictim())) return true;
    for (auto slot : {CURRENT_GENERIC_SPELL, CURRENT_CHANNELED_SPELL, CURRENT_AUTOREPEAT_SPELL})
        if (Spell* cast = bot->GetCurrentSpell(slot))
            if (cast->getState() != SPELL_STATE_FINISHED && cast->m_spellInfo && ((!ClassicRaidOffenseAllowed(ai, cast->m_spellInfo, cast->m_targets.getUnitTarget())) ||
                (hold && RaidDamageSpell(cast->m_spellInfo) &&
                    !IsPositiveSpell(cast->m_spellInfo, bot, cast->m_targets.getUnitTarget())))) return true;
    return false;
}
bool ClassicRaidPauseAction::Execute(Event& event)
{
    if (!isUseful()) return false;
    const bool hold = AI_VALUE(ClassicRaidPlan, "classic raid plan").holdDamage;
    if (hold || (bot->GetVictim() && !ClassicRaidOffenseAllowed(ai, nullptr, bot->GetVictim()))) bot->AttackStop();
    for (auto slot : {CURRENT_GENERIC_SPELL, CURRENT_CHANNELED_SPELL, CURRENT_AUTOREPEAT_SPELL})
        if (Spell* cast = bot->GetCurrentSpell(slot))
            if (cast->getState() != SPELL_STATE_FINISHED && cast->m_spellInfo && ((!ClassicRaidOffenseAllowed(ai, cast->m_spellInfo, cast->m_targets.getUnitTarget())) ||
                (hold && RaidDamageSpell(cast->m_spellInfo) &&
                    !IsPositiveSpell(cast->m_spellInfo, bot, cast->m_targets.getUnitTarget()))))
                bot->InterruptSpell(slot);
    Pet* pet = bot->GetPet();
    if (pet && (hold || (pet->GetVictim() && !ClassicRaidOffenseAllowed(ai, nullptr, pet->GetVictim()))))
    {
        WorldPacket packet(CMSG_PET_ACTION);
        packet << pet->GetObjectGuid() << uint32((ACT_COMMAND << 24) | COMMAND_FOLLOW) << ObjectGuid();
        bot->GetSession()->HandlePetAction(packet);
    }
    return true;
}

bool ClassicRaidTrigger::IsActive()
{
#ifndef MANGOSBOT_ZERO
    // The BWL strategy previously registered only these common helpers in
    // later eras. Keep that behavior when registering them centrally.
    if (bot->GetMapId() == 469 && getName() != "classic raid position" &&
        getName() != "classic raid support" && getName() != "classic raid emergency" &&
        getName() != "classic raid cloak") return false;
#endif
    if (getName() == "classic raid cloak") { ClassicRaidCloakAction action(ai); return action.isUseful(); }
    if (!Ready(ai)) return false;
    if (getName() == "classic raid egg hazard")
        return ai->GetBot()->GetMapId() == 249 && classicraid::EggZone(
            bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ());
    if (getName() == "classic raid pause") { ClassicRaidPauseAction action(ai); return action.isUseful(); }
    if (getName() == "classic raid emergency")
    { ClassicRaidPlan plan; return ClassicRaidPositionAction::GetPlan(ai, plan) && plan.emergency && EncounterMovementRequired(bot, plan.position.destination); }
    if (getName() == "classic raid position") { ClassicRaidPositionAction action(ai); return action.isUseful(); }
    if (getName() == "classic raid target") { ClassicRaidTargetAction action(ai); return action.isUseful(); }
    if (getName() == "classic raid support") { ClassicRaidSupportAction action(ai); return action.isUseful(); }
    if (getName() == "classic raid control") { ClassicRaidControlAction action(ai); return action.isUseful(); }
    return false;
}
float PreserveClassicRaidPlan::GetValue(Action* action)
{
    if (!action || !Ready(ai) || dynamic_cast<ClassicRaidPositionAction*>(action) ||
        dynamic_cast<ClassicRaidControlAction*>(action) || dynamic_cast<MoveAwayFromHazard*>(action)) return 1.0f;
    if (NaxxramasRoleMultiplier(ai, action) == 0.0f) return 0.0f;
    const std::string& name = action->getName();
    if (const char* duty = ResistanceDuty(ai))
    {
        if (ai->GetBot()->getClass() == CLASS_PALADIN && name.find("aura") != std::string::npos && name != duty) return 0.0f;
        if (ai->GetBot()->getClass() == CLASS_SHAMAN &&
            (name == "mana spring totem" || name == "healing stream totem" || name == "frost resistance totem")) return 0.0f;
    }
    if (CastSpellAction* cast = dynamic_cast<CastSpellAction*>(action))
        if (!ClassicRaidOffenseAllowed(ai, sServerFacade.LookupSpellInfo(cast->GetDecisionSpellId()), action->GetTarget())) return 0.0f;
    if (dynamic_cast<AttackAction*>(action) && !ClassicRaidOffenseAllowed(ai, nullptr, action->GetTarget())) return 0.0f;
    const ClassicRaidPlan assigned = ai->GetAiObjectContext()->GetValue<ClassicRaidPlan>("classic raid plan")->Get();
    if (assigned.holdDamage)
    {
        if (dynamic_cast<AttackAction*>(action)) return 0.0f;
        if (CastSpellAction* cast = dynamic_cast<CastSpellAction*>(action))
            if (const SpellEntry* spell = sServerFacade.LookupSpellInfo(cast->GetDecisionSpellId()))
                if (RaidDamageSpell(spell) && !IsPositiveSpell(spell, ai->GetBot(), action->GetTarget())) return 0.0f;
    }
    if (!assigned.target.IsEmpty() && (name == "dps assist" || name == "tank assist") &&
        action->GetTarget() && action->GetTarget()->GetObjectGuid() != assigned.target) return 0.0f;
    // Block only ordinary formation/pursuit drift. Other raid mechanics and
    // friendly healing approaches retain their existing native priorities.
    if (name != "follow" && name != "set behind" && name != "reach melee" && name != "reach spell") return 1.0f;
    if (ReachTargetAction* reach = dynamic_cast<ReachTargetAction*>(action))
        if (Unit* target = reach->GetTarget()) if (sServerFacade.IsFriendlyTo(ai->GetBot(), target)) return 1.0f;
    ClassicRaidPlan plan;
    return ClassicRaidPositionAction::GetPlan(ai, plan) ? 0.0f : 1.0f;
}
