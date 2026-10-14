
#include "playerbot/playerbot.h"
#include "playerbot/strategy/MoltenCoreTrashPolicy.h"
#include "MoltenCoreDungeonActions.h"
#include "MoltenCoreGarrActions.h"
#include "MoltenCoreLavaTrashActions.h"
#include "playerbot/strategy/values/GeddonControlValue.h"
#include "playerbot/strategy/values/HazardsValue.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"
#include "playerbot/ServerFacade.h"
#include "Movement/MoveSpline.h"
#include "playerbot/strategy/mage/MageCombatPolicy.h"
#include "playerbot/strategy/mage/MageActions.h"
#include "playerbot/strategy/hunter/HunterCombatPolicy.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"
#include "AI/ScriptDevAI/include/sc_instance.h"

using namespace ai;

namespace
{
    void PreserveMoltenCoreTank(PlayerbotAI* ai, Unit* enemy, std::vector<Player*>& tanks)
    {
        if (tanks.empty()) return;
        const std::string key = "mc tank " + std::to_string(enemy->GetInstanceId()) + " " +
            std::to_string(enemy->GetGUIDLow());
        auto* owner = ai->GetAiObjectContext()->GetValue<int32>("manual int", key);
        auto main = std::find_if(tanks.begin(), tanks.end(), [owner](Player* tank) {
            return tank->GetGUIDLow() == uint32(owner->Get());
        });
        if (main == tanks.end())
        {
            main = std::find(tanks.begin(), tanks.end(), enemy->GetVictim());
            if (main == tanks.end()) main = tanks.begin();
            owner->Set(int32((*main)->GetGUIDLow()));
        }
        std::rotate(tanks.begin(), main, main + 1);
    }

    const char* MoltenCoreRangeSpell(PlayerbotAI* ai, Player* member)
    {
        if (ai->IsHeal(member)) return member->getClass()==CLASS_PALADIN?"flash of light":
            member->getClass()==CLASS_SHAMAN?"healing wave":member->getClass()==CLASS_DRUID?"healing touch":"flash heal";
        switch (member->getClass())
        {
            case CLASS_HUNTER:return "auto shot";
            case CLASS_WARLOCK:return "shadow bolt";
            case CLASS_PRIEST:return "mind blast";
            case CLASS_SHAMAN:return "lightning bolt";
            case CLASS_DRUID:return "wrath";
            case CLASS_MAGE:return MagePrimaryDamageSpell(ai);
            default:return "frostbolt";
        }
    }

    std::pair<float,float> FirelordRangedBounds(PlayerbotAI* ai, Unit* target)
    {
        if (ai->GetBot()->getClass()==CLASS_HUNTER) return HunterShotRange(ai,target);
        float range=0;
        if (!ai->GetSpellRange("shadow bolt",&range) || !std::isfinite(range) || range<=0) return {0.0f,0.0f};
        return {0.0f,range+ai->GetBot()->GetCombatReach()+target->GetCombatReach()};
    }

    bool PlanFirelordRanged(PlayerbotAI* ai, EncounterPosition& plan)
    {
        Player* bot=ai->GetBot();
        if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
            bot->GetMapId()!=409 || !bot->GetGroup() || !ai->HasRealPlayerMaster() || ai->IsRealPlayer() ||
            (bot->getClass()!=CLASS_HUNTER && bot->getClass()!=CLASS_WARLOCK) || MoltenCorePackStackRequired(ai)) return false;
        Unit* target=ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("current target")->Get());
        if (!target || !target->IsInWorld() || !target->IsAlive() || !target->IsInCombat() ||
            !bot->IsInMap(target) || target->HasCharmer() || sServerFacade.IsFriendlyTo(bot,target) ||
            (target->GetEntry()!=11668 && target->GetEntry()!=12265) ||
            PossibleAttackTargetsValue::HasBreakableCC(target,bot) || PossibleAttackTargetsValue::HasUnBreakableCC(target,bot)) return false;
        Unit* victim=target->GetVictim();
        if (!victim || !victim->IsPlayer() || !victim->IsInWorld() || !victim->IsAlive() ||
            !bot->IsInMap(victim) || victim->HasCharmer()) return false;
        Player* tank=static_cast<Player*>(victim);
        if (tank->IsBeingTeleported() || tank->GetGroup()!=bot->GetGroup() || !ai->IsTank(tank)) return false;
        const auto bounds=FirelordRangedBounds(ai,target);
        const float minimum=bounds.first+2,maximum=bounds.second-2;
        if (!std::isfinite(minimum) || !std::isfinite(maximum) || maximum<=minimum) return false;
        plan.active=true;plan.map=bot->GetMapId();plan.instance=bot->GetInstanceId();
        plan.boss=target->GetObjectGuid();plan.spell=19630;
        const float radial=std::sqrt(bot->GetDistance(target,true,DIST_CALC_NONE));
        if (radial>=std::max(minimum,maximum-4) && radial<=maximum && bot->IsWithinLOSInMap(target))
        {
            plan.destination={bot->GetPositionX(),bot->GetPositionY(),bot->GetPositionZ()};
            if (ValidateEncounterDestination(ai,plan)) return true;
        }
        // A bounded shooting/casting station is independent of generic flee.
        // Try the current side first; every route retains native path, LOS,
        // terrain, hazard and unpulled-pack admission.
        const float angle=target->GetAngle(bot);
        for (float radius : {maximum,std::max(minimum,maximum-6)})
        for (float offset : {0.0f,0.5f,-0.5f,1.0f,-1.0f})
        {
            plan.destination={target->GetPositionX()+std::cos(angle+offset)*radius,
                target->GetPositionY()+std::sin(angle+offset)*radius,target->GetPositionZ()};
            if (!ValidateEncounterDestination(ai,plan)) continue;
            const float dx=plan.destination.x-target->GetPositionX(),dy=plan.destination.y-target->GetPositionY(),
                dz=plan.destination.z-target->GetPositionZ();
            const float distance=std::sqrt(dx*dx+dy*dy+dz*dz);
            if (distance>=minimum && distance<=maximum+0.01f &&
                target->IsWithinLOS(plan.destination.x,plan.destination.y,plan.destination.z+bot->GetCollisionHeight(),true)) return true;
        }
        plan.active=false;return false;
    }

    bool PlanCoreHoundRanged(PlayerbotAI* ai, Unit* hound, EncounterPosition& plan)
    {
        Player* bot=ai->GetBot();
        Unit* patient=ai->IsHeal(bot)?hound->GetVictim():hound;
        plan.active=false;
        float spellRange=0;
        const float stomp=NativeEncounterSpellRadius(19364);
        if (!patient || !patient->IsInWorld() || !patient->IsAlive() || !bot->IsInMap(patient) ||
            !ai->GetSpellRange(MoltenCoreRangeSpell(ai,bot),&spellRange) ||
            !std::isfinite(spellRange) || spellRange<=5 || !std::isfinite(stomp) || stomp<=0) return false;
        const float legal=spellRange+bot->GetCombatReach()+patient->GetCombatReach()-2;
        if (!std::isfinite(legal) || legal<=5) return false;
        const float safe=stomp+hound->GetObjectBoundingRadius()+bot->GetObjectBoundingRadius()+2;
        bool found=false,outside=false;
        float bestDistance=0;
        encounter::Point best;
        // Rear lanes avoid the native frontal breath. Healers solve their
        // range against the actual holding tank, rather than the hound centre.
        for (float margin : {0.0f,4.0f,8.0f,12.0f})
        for (float offset : {180.0f,140.0f,220.0f,110.0f,250.0f})
        {
            const float angle=hound->GetOrientation()+offset*float(M_PI)/180;
            const float ux=std::cos(angle),uy=std::sin(angle);
            const float vx=patient->GetPositionX()-hound->GetPositionX();
            const float vy=patient->GetPositionY()-hound->GetPositionY();
            const float vz=patient->GetPositionZ()-hound->GetPositionZ();
            const float projection=vx*ux+vy*uy;
            const float discriminant=legal*legal-vx*vx-vy*vy-vz*vz+projection*projection;
            if (discriminant<0) continue;
            const float distance=projection+std::sqrt(discriminant)-margin;
            if (!std::isfinite(distance) || distance<=5) continue;
            plan.destination={hound->GetPositionX()+ux*distance,
                hound->GetPositionY()+uy*distance,hound->GetPositionZ()};
            plan.active=true;plan.spell=19364;
            if (!ValidateEncounterDestination(ai,plan)) continue;
            const auto& p=plan.destination;
            const float dx=p.x-patient->GetPositionX(),dy=p.y-patient->GetPositionY(),dz=p.z-patient->GetPositionZ();
            if (dx*dx+dy*dy+dz*dz>legal*legal+0.01f) continue;
            const float radial=std::hypot(p.x-hound->GetPositionX(),p.y-hound->GetPositionY());
            const bool safeLane=radial>=safe;
            if (found && ((outside&&!safeLane) || (outside==safeLane&&radial<=bestDistance+0.25f))) continue;
            found=true;outside=safeLane;bestDistance=radial;best=p;
        }
        if (!found) { plan.active=false;return false; } // No path, terrain or range bypass.
        const float dx=bot->GetPositionX()-patient->GetPositionX();
        const float dy=bot->GetPositionY()-patient->GetPositionY();
        const float dz=bot->GetPositionZ()-patient->GetPositionZ();
        const float radial=std::hypot(bot->GetPositionX()-hound->GetPositionX(),bot->GetPositionY()-hound->GetPositionY());
        // Retain a legal rear station near maximum range; never hold the old
        // 25-yard station just because it was behind the hound.
        if (std::cos(hound->GetAngle(bot)-hound->GetOrientation())<-0.25f &&
            radial>=bestDistance-1 && dx*dx+dy*dy+dz*dz<=legal*legal &&
            (!outside || radial>=safe)) best={bot->GetPositionX(),bot->GetPositionY(),bot->GetPositionZ()};
        plan.destination=best;plan.spell=19364;plan.active=true;
        if (ValidateEncounterDestination(ai,plan)) return true;
        plan.active=false;return false;
    }

    std::vector<Unit*> MoltenCorePack(PlayerbotAI* ai)
    {
        Player* bot = ai->GetBot();
        std::vector<Unit*> pack;
        Unit* anchor = nullptr;
        for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
        {
            Unit* unit = ai->GetUnit(guid);
            if (!unit || !unit->IsInWorld() || !unit->IsAlive() || !unit->IsInCombat() ||
                !bot->IsInMap(unit) || unit->HasCharmer() || sServerFacade.IsFriendlyTo(bot, unit) ||
                (unit->GetEntry() != 11671 && unit->GetEntry() != 11669) ||
                (!(unit->GetEntry()==11671 && unit->HasAura(19951)) &&
                 (PossibleAttackTargetsValue::HasBreakableCC(unit, bot) ||
                  PossibleAttackTargetsValue::HasUnBreakableCC(unit, bot)))) continue;
            if (!anchor || unit->GetObjectGuid() < anchor->GetObjectGuid()) anchor = unit;
            pack.push_back(unit);
        }
        if (!anchor) return {};
        // A group Attack starts this pack, rather than pinning every tank to
        // one member. Keep collapsed hounds in its identity and allocation.
        Unit* commanded=ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("attack target")->Get());
        if (commanded && std::find(pack.begin(),pack.end(),commanded)!=pack.end()) anchor=commanded;
        const auto* group = static_cast<Creature*>(anchor)->GetCreatureGroup();
        pack.erase(std::remove_if(pack.begin(), pack.end(), [anchor, group](Unit* unit) {
            return unit->GetEntry() != anchor->GetEntry() ||
                (anchor->GetEntry() != 11669 && (group ? static_cast<Creature*>(unit)->GetCreatureGroup() != group : unit->GetDistance(anchor) > 30));
        }), pack.end());
        std::sort(pack.begin(), pack.end(), [](Unit* a, Unit* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        return pack;
    }

    std::vector<Player*> MoltenCorePackTanks(PlayerbotAI* ai, const std::vector<Unit*>& pack)
    {
        std::vector<Player*> tanks;
        if (pack.empty()) return tanks;
        Player* bot = ai->GetBot();
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* tank = ref->getSource();
            if (tank && tank->IsInWorld() && tank->IsAlive() && !tank->IsBeingTeleported() &&
                !tank->HasCharmer() && bot->IsInMap(tank) && ai->IsTank(tank) && tank->GetDistance(pack.front()) <= 50)
                tanks.push_back(tank);
        }
        std::sort(tanks.begin(), tanks.end(), [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        // Keep the first hound's established tank as the common gathering point.
        PreserveMoltenCoreTank(ai, pack.front(), tanks);
        return tanks;
    }
}

bool ai::MoltenCorePackStackRequired(PlayerbotAI* ai)
{
    Player* bot=ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId()!=409 || !bot->GetGroup() || ai->IsRealPlayer()) return false;
    auto pack=MoltenCorePack(ai);
    if (!pack.empty() && pack.front()->GetEntry()==11671 && !MoltenCorePackTanks(ai,pack).empty()) return true;
    for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
    {
        Unit* unit=ai->GetUnit(guid);
        if (!unit || unit->GetEntry()!=12101 || !unit->IsInWorld() || !unit->IsAlive() ||
            !unit->IsInCombat() || !bot->IsInMap(unit) || unit->HasCharmer()) continue;
        Unit* victim=unit->GetVictim();
        if (victim && victim->IsPlayer() && victim->IsInWorld() && victim->IsAlive() && bot->IsInMap(victim) &&
            static_cast<Player*>(victim)->GetGroup()==bot->GetGroup() && ai->IsTank(static_cast<Player*>(victim))) return true;
    }
    return false;
}

bool ai::MoltenCoreRecoverableImp(PlayerbotAI* ai, Unit* enemy)
{
    Player* bot=ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId()!=409 || !bot->GetGroup() || ai->IsRealPlayer() || !enemy ||
        enemy->GetEntry()!=11669 || !enemy->IsInWorld() || !enemy->IsAlive() || !bot->IsInMap(enemy) ||
        !enemy->IsInCombat() || enemy->HasCharmer() || sServerFacade.IsFriendlyTo(bot,enemy) ||
        PossibleAttackTargetsValue::HasBreakableCC(enemy,bot) ||
        PossibleAttackTargetsValue::HasUnBreakableCC(enemy,bot)) return false;
    Unit* victim=enemy->GetVictim();
    if (!victim || !victim->IsInWorld() || !victim->IsAlive() || !bot->IsInMap(victim)) return false;
    Unit* owner=victim->IsPlayer()?victim:victim->GetOwner(nullptr,true);
    Player* carrier=owner && owner->IsPlayer()?static_cast<Player*>(owner):nullptr;
    if (!carrier || !carrier->IsInWorld() || !carrier->IsAlive() || !bot->IsInMap(carrier) ||
        carrier->IsBeingTeleported() || carrier->HasCharmer() || carrier->GetGroup()!=bot->GetGroup()) return false;
    for (GroupReference* ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next())
    {
        Player* tank=ref->getSource();
        if (tank && tank->IsInWorld() && tank->IsAlive() && !tank->IsBeingTeleported() &&
            !tank->HasCharmer() && bot->IsInMap(tank) && ai->IsTank(tank) && tank->CanReactInCombat() &&
            tank->GetDistance(enemy)<=30) return true;
    }
    return false;
}

bool ai::MoltenCoreImpUnderPressure(PlayerbotAI* ai)
{
    for (ObjectGuid guid:ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
    {
        Unit* enemy=ai->GetUnit(guid);
        if (!MoltenCoreRecoverableImp(ai,enemy)) continue;
        Unit* victim=enemy->GetVictim();
        if (!victim->IsPlayer() || !ai->IsTank(static_cast<Player*>(victim))) return true;
    }
    return false;
}

Unit* ai::MoltenCorePackTankTarget(PlayerbotAI* ai)
{
    auto pack = MoltenCorePack(ai);
    auto tanks = MoltenCorePackTanks(ai, pack);
    auto own = std::find(tanks.begin(), tanks.end(), ai->GetBot());
    if (pack.empty() || (pack.size()<2 && pack.front()->GetEntry()!=11669) || own == tanks.end()) return nullptr;
    const size_t slot = std::distance(tanks.begin(), own);
    Unit* held = nullptr;
    if (pack.front()->GetEntry()==11669)
        for (size_t i=0;i<pack.size();++i)
        {
            Unit* enemy=pack[i];Unit* victim=enemy->GetVictim();
            if (!MoltenCoreRecoverableImp(ai,enemy) ||
                (victim && std::find(tanks.begin(),tanks.end(),victim)!=tanks.end())) continue;
            Player* rescue=tanks[i%tanks.size()];
            if (!rescue->CanReactInCombat()) rescue=nullptr;
            for (Player* candidate:tanks)
                if (candidate->CanReactInCombat() && (!rescue ||
                    candidate->GetDistance(enemy)+8<rescue->GetDistance(enemy))) rescue=candidate;
            if (rescue==ai->GetBot() && PossibleAttackTargetsValue::IsValid(enemy,ai->GetBot(),60,false,true)) return enemy;
        }
    for (size_t i = slot; i < pack.size(); i += tanks.size())
    {
        Unit* enemy = pack[i];
        if (enemy->HasAura(19951)) continue; // Native collapsed hound; retain its slot but never attack it.
        if (!PossibleAttackTargetsValue::IsValid(enemy, ai->GetBot(), 60, false, true)) continue;
        Unit* victim = enemy->GetVictim();
        // Recover a pet/healer-held assigned enemy first. Never steal from
        // another living group tank merely to satisfy the allocation.
        const bool tankHeld = victim && victim->IsPlayer() && victim->IsAlive() &&
            std::find(tanks.begin(), tanks.end(), victim) != tanks.end();
        if (!tankHeld) {if (enemy->GetEntry()==11669) continue;return enemy;}
        if (victim == ai->GetBot()) held = enemy;
    }
    return held;
}

bool ai::PlanMoltenCorePack(PlayerbotAI* ai, EncounterPosition& plan)
{
    auto pack = MoltenCorePack(ai);
    auto tanks = MoltenCorePackTanks(ai, pack);
    if (pack.empty() || tanks.empty()) return false;
    Player* bot = ai->GetBot();
    Player* anchor = tanks.front();
    plan.active = true; plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    plan.boss = pack.front()->GetObjectGuid(); plan.spell = 19771;
    if (!ai->IsTank(bot))
        for (size_t i=0;i<pack.size();++i)
            if (pack[i]->GetVictim()==bot && !pack[i]->HasAura(19951))
            {
                Player* tank=tanks[i%tanks.size()];
                plan.boss=pack[i]->GetObjectGuid();
                plan.spell=pack[i]->GetEntry()==11669?20602:19771;
                plan.source=bot->GetObjectGuid();
                auto recovery=tanks;
                if (pack[i]->GetEntry()==11669)
                    std::sort(recovery.begin(),recovery.end(),[bot](Player* a,Player* b) {
                        const float da=bot->GetDistance(a),db=bot->GetDistance(b);
                        return da!=db ? da<db : a->GetObjectGuid()<b->GetObjectGuid();
                    });
                else recovery={tank};
                for (Player* candidate:recovery)
                {
                    if (!candidate->CanReactInCombat()) continue;
                    plan.destination={candidate->GetPositionX(),candidate->GetPositionY(),candidate->GetPositionZ()};
                    if (ValidateEncounterDestination(ai,plan)) return true;
                }
                plan.active=false;return false;
            }
#ifdef MANGOSBOT_ZERO
    if (bot->getClass()==CLASS_MAGE && !ai->IsTank(bot) && !ai->IsHeal(bot))
        for (ObjectGuid guid:ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
        {
            Unit* ancient=ai->GetUnit(guid);
            if (!ancient || ancient->GetEntry()!=11673 || !ancient->IsInWorld() || !ancient->IsAlive() ||
                !ancient->IsInCombat() || !bot->IsInMap(ancient) || ancient->HasCharmer()) continue;
            Unit* victim=ancient->GetVictim();
            if (!victim || !victim->IsPlayer() || !victim->IsInWorld() || !victim->IsAlive() ||
                !bot->IsInMap(victim) || static_cast<Player*>(victim)->GetGroup()!=bot->GetGroup() ||
                !ai->IsTank(static_cast<Player*>(victim))) continue;
            plan.boss=ancient->GetObjectGuid();
            return PlanCoreHoundRanged(ai,ancient,plan); // Patrol mixed into a pack: preserve ranged safety.
        }
#endif
    if (pack.size()<2 && pack.front()->GetEntry()!=11669) {plan.active=false;return false;}
    if (ai->IsTank(bot))
    {
        // Secure the assigned loose mob before gathering. Otherwise the
        // formation multiplier blocks native reach/taunt while it attacks a
        // healer, ranged member or pet outside the tank cluster.
        Unit* assigned=MoltenCorePackTankTarget(ai);
        if (assigned && assigned->GetVictim()!=bot) {plan.active=false;return false;}
        // Holding tank remains stationary; off-tanks bring their mobs to it.
        if (bot == anchor) { plan.active = false; return false; }
        plan.destination = {anchor->GetPositionX(), anchor->GetPositionY(), anchor->GetPositionZ()};
    }
    else if (pack.front()->GetEntry()==11671)
    {
        // Every role stacks on the holding tank. Hunters switch to native
        // melee instead of opening a charge lane to preserve shooting room.
        plan.destination={anchor->GetPositionX(),anchor->GetPositionY(),anchor->GetPositionZ()};
    }
    else if (ai->IsRanged(bot) || ai->IsHeal(bot))
    {
        float angle = pack.front()->GetAngle(anchor) + float(M_PI);
        float distance = 25.0f;
        float spellRange = 0;
        if (ai->GetSpellRange(ai->IsHeal(bot) ? "flash heal" : "blizzard", &spellRange) && spellRange > 10)
            distance = std::min(30.0f, spellRange - 2);
        if (bot->GetDistance(pack.front()) >= distance - 2 && bot->GetDistance(pack.front()) <= distance + 5)
            plan.destination = {bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
        else plan.destination = {pack.front()->GetPositionX() + std::cos(angle)*distance,
            pack.front()->GetPositionY() + std::sin(angle)*distance, pack.front()->GetPositionZ()};
    }
    else
    {
        // Do not send melee into Flame Imp explosions. Their normal ranged
        // options remain available while the tanks and casters finish the pack.
        if (pack.front()->GetEntry() == 11669)
        {
            const float distance = std::max(10.0f, NativeEncounterSpellRadius(20602) +
                pack.front()->GetCombatReach() + bot->GetCombatReach() + 2);
            float angle = pack.front()->GetAngle(anchor) + float(M_PI);
            plan.destination = {pack.front()->GetPositionX() + std::cos(angle)*distance,
                pack.front()->GetPositionY() + std::sin(angle)*distance, pack.front()->GetPositionZ()};
        }
        else
        {
            const float angle = pack.front()->GetAngle(anchor) + float(M_PI);
            const float distance = std::max(2.0f, pack.front()->GetCombatReach() + bot->GetCombatReach() - 1);
            plan.destination = {pack.front()->GetPositionX() + std::cos(angle)*distance,
                pack.front()->GetPositionY() + std::sin(angle)*distance, pack.front()->GetPositionZ()};
        }
    }
    if (ValidateEncounterDestination(ai, plan)) return true;
    plan.active = false;
    return false;
}

bool ai::MoltenCoreImpTauntAllowed(PlayerbotAI* ai, const std::string& name)
{
    Player* bot=ai->GetBot();
    if (!bot->IsInWorld() || bot->GetMapId()!=409) return true;
    if (!bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        !bot->GetGroup() || !ai->IsTank(bot) || ai->IsRealPlayer()) return false;
    const auto neighbours=ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get();
    Player* selected=nullptr;
    const char* selectedSpell=nullptr;
    for (GroupReference* ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next())
    {
        Player* tank=ref->getSource();
        if (!tank || !tank->IsInWorld() || !tank->IsAlive() || tank->IsBeingTeleported() ||
            tank->HasCharmer() || !bot->IsInMap(tank) || !ai->IsTank(tank) || !tank->GetPlayerbotAI() ||
            tank->GetPlayerbotAI()->IsRealPlayer()) continue;
        const char* ability=tank->getClass()==CLASS_WARRIOR ? "challenging shout" :
            tank->getClass()==CLASS_DRUID ? "challenging roar" : nullptr;
        if (!ability || !tank->GetPlayerbotAI()->CanCastSpell(ability,tank,0)) continue;
        const float radius=NativeEncounterSpellRadius(tank->getClass()==CLASS_WARRIOR?1161:5209);
        if (!std::isfinite(radius) || radius<=0) continue;
        unsigned loose=0;bool safe=true;
        for (ObjectGuid guid:neighbours)
        {
            Unit* enemy=ai->GetUnit(guid);
            if (!enemy || !enemy->IsInWorld() || !enemy->IsAlive() || !bot->IsInMap(enemy) ||
                sServerFacade.IsFriendlyTo(bot,enemy) || tank->GetDistance(enemy)>radius-1) continue;
            if (!enemy->IsInCombat() || enemy->HasCharmer() ||
                PossibleAttackTargetsValue::HasBreakableCC(enemy,bot) ||
                PossibleAttackTargetsValue::HasUnBreakableCC(enemy,bot) ||
                enemy->HasAura(1161) || enemy->HasAura(5209)) {safe=false;break;}
            if (enemy->GetEntry()!=11669) continue;
            Unit* victim=enemy->GetVictim();
            const bool held=victim && victim->IsPlayer() && victim->IsAlive() && victim->IsInWorld() &&
                bot->IsInMap(victim) && static_cast<Player*>(victim)->GetGroup()==bot->GetGroup() &&
                ai->IsTank(static_cast<Player*>(victim));
            if (!held) ++loose;
        }
        // Single-target recovery remains available for one loose imp. Do not
        // spend two long AoE cooldowns on a pack already forced onto a tank.
        if (!safe || loose<2) continue;
        if (!selected || tank->GetObjectGuid()<selected->GetObjectGuid())
        {selected=tank;selectedSpell=ability;}
    }
    return selected==bot && selectedSpell && name==selectedSpell;
}

bool ai::MoltenCoreImpPack(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 409 || !bot->GetGroup() || ai->IsRealPlayer() || ai->IsHeal(bot)) return false;
    Unit* target = ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("current target")->Get());
    if (!target || !target->IsInWorld() || !bot->IsInMap(target) || !target->IsAlive() ||
        !target->IsInCombat() || (target->GetEntry() != 11669 && target->GetEntry()!=12101)) return false;
    unsigned imps = 0,held = 0;
    for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
    {
        Unit* enemy = ai->GetUnit(guid);
        if (!enemy || !enemy->IsInWorld() || !bot->IsInMap(enemy) || !enemy->IsAlive() ||
            sServerFacade.IsFriendlyTo(bot, enemy)) continue;
        if (enemy->GetDistance(target) > 15 && enemy->GetDistance(bot) > 15) continue;
        if (!enemy->IsInCombat() || enemy->HasCharmer() ||
            PossibleAttackTargetsValue::HasBreakableCC(enemy, bot) ||
            PossibleAttackTargetsValue::HasUnBreakableCC(enemy, bot)) return false;
        if (enemy->GetEntry() == 11669 && enemy->GetDistance(target) <= 8)
        {
            Unit* victim = enemy->GetVictim();
            if (victim && victim->IsPlayer() && victim->IsAlive() && bot->IsInMap(victim) &&
                ai->IsTank(static_cast<Player*>(victim)) && static_cast<Player*>(victim)->GetGroup()==bot->GetGroup()) ++held;
            ++imps;
        }
    }
    return imps >= 3 && ((held > 0 && ai->GetCombatStartTime() && time(0) - ai->GetCombatStartTime() >= 10) ||
        MoltenCoreImpUnderPressure(ai));
}

namespace
{
    bool PlanMagmadarTank(PlayerbotAI* ai, Unit* boss, EncounterPosition& plan)
    {
        Player* bot=ai->GetBot();
        if (boss->GetVictim()!=bot || !ai->IsTank(bot)) return false;
        const float melee=std::max(2.0f,boss->GetCombatReach()+bot->GetCombatReach()-1);
        auto* value=ai->GetAiObjectContext()->GetValue<MagmadarControl>("magmadar control");
        auto state=value->Get();
        if (state.boss!=boss->GetObjectGuid() || state.tank!=bot->GetObjectGuid() ||
            state.combatStart!=ai->GetCombatStartTime())
        {
            // Do not replace the native pull approach with a forward station.
            // Once established, retain it through fear and knockback recovery.
            if (bot->GetDistance(boss)>melee+3) {plan.active=false;return false;}
            state.boss=boss->GetObjectGuid();state.tank=bot->GetObjectGuid();
            state.combatStart=ai->GetCombatStartTime();
            state.facing=boss->GetAngle(bot);
            float x=0,y=0;unsigned count=0;
            for (GroupReference* ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next())
            {
                Player* member=ref->getSource();
                if (!member || member==bot || !member->IsInWorld() || !member->IsAlive() ||
                    member->IsBeingTeleported() || !bot->IsInMap(member) || ai->IsTank(member) ||
                    member->GetDistance(boss)>100) continue;
                x+=member->GetPositionX()-boss->GetPositionX();
                y+=member->GetPositionY()-boss->GetPositionY();++count;
            }
            if (count && x*x+y*y>4) state.facing=std::atan2(y,x)+float(M_PI);
            state.tankPosition={boss->GetPositionX()+std::cos(state.facing)*melee,
                boss->GetPositionY()+std::sin(state.facing)*melee,boss->GetPositionZ()};
        }
        std::list<HazardPosition> fire;
        AppendMoltenCoreGroundHazards(ai,fire);
        const auto clearStation=[&](const encounter::Point& p) {
            // Clear the tank, the boss's intended centre and the rear melee
            // station. A safe tank standing beside a burning melee pile is
            // not a safe holding position.
            for (float back : {0.0f,melee,2*melee})
                for (const auto& hazard:fire)
                {
                    const float x=p.x-std::cos(state.facing)*back-hazard.first.getX();
                    const float y=p.y-std::sin(state.facing)*back-hazard.first.getY();
                    if (std::fabs(p.z-hazard.first.getZ())<8 && x*x+y*y<hazard.second*hazard.second) return false;
                }
            return true;
        };
        plan.active=true;plan.spell=19272;plan.boss=boss->GetObjectGuid();
        plan.map=bot->GetMapId();plan.instance=bot->GetInstanceId();
        plan.anchor={boss->GetPositionX(),boss->GetPositionY(),boss->GetPositionZ()};plan.anchored=true;
        plan.destination=state.tankPosition;
        if (clearStation(plan.destination) && ValidateEncounterDestination(ai,plan))
        {value->Set(state);return true;}
        // Relocate only to nearby native-walkable, fire-free stations. Retain
        // the selected point across fear/facing changes instead of chasing a
        // moving raid centroid on every update.
        for (float distance : {8.0f,12.0f,18.0f,24.0f})
            for (float offset : {0.0f,0.7f,-0.7f,1.4f,-1.4f})
            {
                const float angle=state.facing+offset;
                plan.destination={boss->GetPositionX()+std::cos(angle)*(melee+distance),
                    boss->GetPositionY()+std::sin(angle)*(melee+distance),boss->GetPositionZ()};
                if (!clearStation(plan.destination) || !ValidateEncounterDestination(ai,plan)) continue;
                state.tankPosition=plan.destination;value->Set(state);return true;
            }
        plan.active=false;return false;
    }

    bool PlanMagmadarFormation(PlayerbotAI* ai, Unit* boss, EncounterPosition& plan)
    {
        Player* bot=ai->GetBot();
        if (boss->GetVictim()==bot) return PlanMagmadarTank(ai,boss,plan);
        const bool healer=ai->IsHeal(bot);
        const bool ranged=!ai->IsTank(bot) && (ai->IsRanged(bot)||healer||bot->getClass()==CLASS_HUNTER);
        std::vector<Player*> members;
        for (GroupReference* ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next())
        {
            Player* member=ref->getSource();
            if (!member || !member->IsInWorld() || !member->IsAlive() || member->HasCharmer() ||
                member->IsBeingTeleported() || !bot->IsInMap(member) || member==boss->GetVictim() ||
                member->GetDistance(boss)>100 || (!ai->IsTank(member) &&
                (ai->IsRanged(member)||ai->IsHeal(member)||member->getClass()==CLASS_HUNTER))!=ranged) continue;
            members.push_back(member);
        }
        std::sort(members.begin(),members.end(),[](Player* a,Player* b){return a->GetObjectGuid()<b->GetObjectGuid();});
        auto own=std::find(members.begin(),members.end(),bot);
        if (own==members.end()) return false;
        const size_t slot=std::distance(members.begin(),own);
        const float rear=boss->GetOrientation()+float(M_PI);
        float maximum=std::max(2.0f,boss->GetCombatReach()+bot->GetCombatReach()-1);
        Unit* rangeTarget=boss;
        if (ranged)
        {
            if (healer && boss->GetVictim() && boss->GetVictim()->IsPlayer()) rangeTarget=boss->GetVictim();
            float range=0;
            if (!ai->GetSpellRange(MoltenCoreRangeSpell(ai,bot),&range) || !std::isfinite(range) || range<=0)
            {plan.active=false;return false;}
            maximum=range+bot->GetCombatReach()+rangeTarget->GetCombatReach()-2;
        }
        const auto separated=[&](const encounter::Point& p) {
            float distance=100;
            for (Player* member:members)
                if (member!=bot) distance=std::min(distance,std::hypot(p.x-member->GetPositionX(),p.y-member->GetPositionY()));
            return distance;
        };
        const auto outerRange=[&](float angle) {
            if (rangeTarget==boss) return maximum;
            const float x=rangeTarget->GetPositionX()-boss->GetPositionX();
            const float y=rangeTarget->GetPositionY()-boss->GetPositionY();
            const float z=rangeTarget->GetPositionZ()-boss->GetPositionZ();
            const float projection=x*std::cos(angle)+y*std::sin(angle);
            const float remainder=maximum*maximum-(x*x+y*y+z*z-projection*projection);
            return remainder<0 ? 0.0f : projection+std::sqrt(remainder);
        };
        const float ownAngle=boss->GetAngle(bot);
        const float radial=std::hypot(bot->GetPositionX()-boss->GetPositionX(),bot->GetPositionY()-boss->GetPositionY());
        const encounter::Point here{bot->GetPositionX(),bot->GetPositionY(),bot->GetPositionZ()};
        plan.active=true;plan.spell=19272;plan.boss=boss->GetObjectGuid();
        plan.map=bot->GetMapId();plan.instance=bot->GetInstanceId();
        // Keep a valid maximum-range rear station; do not drift inward after
        // finding it, or move just because another bot arrived in its slot.
        plan.anchor={boss->GetPositionX(),boss->GetPositionY(),boss->GetPositionZ()};plan.anchored=true;
        if (std::cos(ownAngle-boss->GetOrientation())<-0.05f && radial>=outerRange(ownAngle)-1.5f &&
            radial<=outerRange(ownAngle)+0.5f && bot->GetDistance(rangeTarget,true,DIST_CALC_NONE)<=maximum*maximum && (!ranged||separated(here)>=5))
        {
            plan.destination=here;
            if (ValidateEncounterDestination(ai,plan)) return true;
        }
        struct Candidate{encounter::Point point;float score;unsigned band;};
        std::vector<Candidate> candidates;
        std::list<HazardPosition> fire;
        AppendMoltenCoreGroundHazards(ai,fire);
        const float preferred=rear+(members.size()>1 ? float(slot)/float(members.size()-1)-0.5f : 0)*float(M_PI)*0.85f;
        // Search the full rear semicircle at usable spell range. A blocked
        // preferred lane must not leave a caster parked close to the boss.
        for (unsigned band=0;band<(ranged?4u:1u);++band)
        for (unsigned lane=0;lane<33;++lane)
        {
            const float angle=rear-float(M_PI)*0.49f+float(lane)/32*float(M_PI)*0.98f;
            const float distance=outerRange(angle)-float(band)*4;
            if (!std::isfinite(distance) || distance<2) continue;
            encounter::Point point{boss->GetPositionX()+std::cos(angle)*distance,
                boss->GetPositionY()+std::sin(angle)*distance,boss->GetPositionZ()};
            if (ranged && !rangeTarget->IsWithinLOS(point.x,point.y,point.z+bot->GetCollisionHeight(),true)) continue;
            if (ranged && bot->getClass()==CLASS_HUNTER)
            {
                const auto bounds=HunterShotRange(ai,boss);
                if (distance<bounds.first+2 || distance>bounds.second-1) continue;
            }
            bool clear=true;
            for (const auto& hazard:fire)
                if (std::fabs(point.z-hazard.first.getZ())<8 &&
                    std::hypot(point.x-hazard.first.getX(),point.y-hazard.first.getY())<hazard.second+1) {clear=false;break;}
            if (!clear) continue;
            const float spacing=separated(point);
            if (ranged && spacing<5) continue;
            const float preference=std::fabs(angle-preferred);
            // Eight yards is the spacing goal; five is the admission minimum.
            candidates.push_back({point,(ranged?std::min(8.0f,spacing):8.0f)*10-preference-float(band)*1000,band});
        }
        std::sort(candidates.begin(),candidates.end(),[](const Candidate& a,const Candidate& b){return a.score>b.score;});
        unsigned checked=0;
        unsigned bandChecks[4]={0,0,0,0};
        for (const auto& candidate:candidates)
        {
            const unsigned budget=candidate.band==0?16:(candidate.band==1?8:4);
            if (ranged && bandChecks[candidate.band]++>=budget) continue;
            if (++checked>32) break;
            plan.destination=candidate.point;
            if (!ValidateEncounterDestination(ai,plan)) continue;
            if (ranged)
            {
                // Native terrain adjustment can change Z. Recheck actual
                // three-dimensional spell reach and LOS at the final point.
                const float dx=plan.destination.x-rangeTarget->GetPositionX(),dy=plan.destination.y-rangeTarget->GetPositionY(),
                    dz=plan.destination.z-rangeTarget->GetPositionZ();
                if (dx*dx+dy*dy+dz*dz>maximum*maximum+0.01f ||
                    !rangeTarget->IsWithinLOS(plan.destination.x,plan.destination.y,plan.destination.z+bot->GetCollisionHeight(),true)) continue;
            }
            return true;
        }
        plan.active=false;return false;
    }
}

bool ai::PlanGeddonFormation(PlayerbotAI* ai, Unit* boss, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    Unit* victim = boss->GetVictim();
    if (!victim || !victim->IsPlayer() || !victim->IsAlive() || !ai->IsTank(static_cast<Player*>(victim)) ||
        static_cast<Player*>(victim)->GetGroup() != bot->GetGroup()) return false;
    auto* value = ai->GetAiObjectContext()->GetValue<GeddonControl>("geddon control");
    GeddonControl state = value->Get();
    if (state.boss != boss->GetObjectGuid() || state.tank != victim->GetObjectGuid())
    {
        state.boss = boss->GetObjectGuid(); state.tank = victim->GetObjectGuid();
        state.tankPosition = {victim->GetPositionX(),victim->GetPositionY(),victim->GetPositionZ()};
        const float angle = boss->GetAngle(victim) + float(M_PI);
        state.rangedPosition = {boss->GetPositionX()+std::cos(angle)*30,
            boss->GetPositionY()+std::sin(angle)*30,boss->GetPositionZ()};
        // The chosen room pads are preferences. Native map/path validation
        // remains authoritative, and remote pulls retain their own anchor.
        if (std::hypot(boss->GetPositionX()-643.981873f,boss->GetPositionY()+761.169434f) < 70)
        {
            EncounterPosition station; station.active = true; station.map = bot->GetMapId(); station.instance = bot->GetInstanceId();
            station.boss = boss->GetObjectGuid(); station.spell = 19771;
            station.destination = {643.981873f,-761.169434f,-208.743454f};
            if (ValidateEncounterDestination(ai,station))
            {
                state.tankPosition = station.destination;
                state.rangedPosition = {685.775574f,-731.014709f,-209.287491f};
            }
        }
        value->Set(state);
    }
    if (bot->HasAura(20475)) return false; // Native Living Bomb escape always wins.
    if (victim == bot)
    {
        if (std::hypot(bot->GetPositionX()-state.tankPosition.x,bot->GetPositionY()-state.tankPosition.y) <= 2) return false;
        plan.destination = state.tankPosition;
    }
    else if (ai->IsRanged(bot) || ai->IsHeal(bot))
    {
        plan.destination = state.rangedPosition;
        // A low-range build may need a nearer point. Native spellbook range,
        // combat reaches and friendly healing reach remain authoritative.
        const char* spell = MoltenCoreRangeSpell(ai,bot);
        float range = 0;
        Unit* target = ai->IsHeal(bot) ? victim : boss;
        if (ai->GetSpellRange(spell,&range) && range > 5)
        {
            const float legal = range + target->GetCombatReach() + bot->GetCombatReach() - 2;
            const float dx=plan.destination.x-target->GetPositionX(),dy=plan.destination.y-target->GetPositionY();
            const float distance=std::hypot(dx,dy);
            if (distance > legal)
            { plan.destination.x=target->GetPositionX()+dx*legal/distance;plan.destination.y=target->GetPositionY()+dy*legal/distance; }
        }
    }
    else return false;
    plan.active=true;plan.map=bot->GetMapId();plan.instance=bot->GetInstanceId();
    plan.boss=boss->GetObjectGuid();plan.spell=19771;
    if (ValidateEncounterDestination(ai,plan)) return true;
    plan.active=false;return false;
}

bool ai::PlanMoltenCoreTrash(PlayerbotAI* ai, EncounterPosition& plan)
{
    plan = EncounterPosition();
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 409 || !bot->GetGroup() || ai->IsRealPlayer()) return false;
    if (PlanGarrPosition(ai, plan)) return true;
    if (PlanRagnarosFormation(ai, plan)) return true;
    if (PlanGolemaggFormation(ai, plan)) return true;
    if (PlanMajordomoFormation(ai, plan)) return true;
    if (PlanMoltenCorePack(ai, plan)) return true;
    if (PlanLavaTrashCarrier(ai, plan)) return true;
    if (PlanLavaTrashBanish(ai, plan)) return true;
    if (PlanMoltenCoreGiants(ai, plan)) return true;
    if (PlanMoltenCoreMageCleave(ai, plan)) return true;
    if (PlanFirelordRanged(ai, plan)) return true;
    Unit* selected = nullptr;
    Unit* chosen=ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("current target")->Get());
    for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
    {
        Unit* boss = ai->GetUnit(guid);
        if (!boss || boss->GetEntry() != 12259 || !boss->IsInWorld() || !boss->IsAlive() ||
            !boss->IsInCombat() || !bot->IsInMap(boss) || boss->HasCharmer()) continue;
        Unit* victim = boss->GetVictim();
        if (!ai->IsTank(bot) || !victim || !victim->IsPlayer() || !ai->IsTank(static_cast<Player*>(victim)) ||
            static_cast<Player*>(victim)->GetGroup() != bot->GetGroup() || victim == bot) break;
        Unit* assigned = MoltenCoreAssignedTankTarget(ai);
        if (!assigned || assigned->GetEntry() != 11661 || assigned->GetVictim() != bot) break;
        plan.active = true; plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
        plan.boss = boss->GetObjectGuid(); plan.spell = 19771;
        plan.destination = {victim->GetPositionX(), victim->GetPositionY(), victim->GetPositionZ()};
        if (ValidateEncounterDestination(ai, plan)) return true;
        plan.active = false;
    }
    for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit || !unit->IsInWorld() || !bot->IsInMap(unit) || !unit->IsAlive() ||
            !unit->IsInCombat() || unit->HasCharmer() || sServerFacade.IsFriendlyTo(bot, unit) ||
            (unit->GetEntry() != 12101 && unit->GetEntry() != 11673 && unit->GetEntry() != 11666 &&
             unit->GetEntry() != 11667 && unit->GetEntry() != 12100 && unit->GetEntry() != 11661 && unit->GetEntry() != 12056 && unit->GetEntry() != 11982)) continue;
        Unit* victim = unit->GetVictim();
        if (!victim || !victim->IsPlayer() || !victim->IsAlive() ||
            static_cast<Player*>(victim)->GetGroup() != bot->GetGroup()) continue;
        // Keep the current victim's tank assignment. Choose one stable nearby
        // source; do not alternate between multiple trash mobs every tick.
        if (!selected || (unit->GetVictim() == bot && selected->GetVictim() != bot) ||
            (unit->GetVictim()!=bot && selected->GetVictim()!=bot && unit==chosen && selected!=chosen) ||
            (unit->GetVictim() != bot && selected->GetVictim() != bot &&
             selected!=chosen && unit->GetObjectGuid() < selected->GetObjectGuid())) selected = unit;
    }
    if (!selected) return false;
    if (!ai->IsTank(bot) && chosen && chosen!=selected && chosen->IsInWorld() && chosen->IsAlive() &&
        chosen->IsInCombat() && bot->IsInMap(chosen) && !sServerFacade.IsFriendlyTo(bot,chosen) &&
        (selected->GetEntry()==11666 || selected->GetEntry()==11667 || selected->GetEntry()==12100 || selected->GetEntry()==11661))
        return false; // A rear station at a different mob cannot veto reach to the actual attack target.
    if (selected->GetEntry() == 11673)
    {
        Unit* current = ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("current target")->Get());
        if (current && current != selected && current->GetEntry() != 11673 && current->IsInWorld() &&
            current->IsAlive() && current->IsInCombat() && bot->IsInMap(current) && !current->HasCharmer() &&
            !sServerFacade.IsFriendlyTo(bot, current) && !ai->IsRanged(bot) && !ai->IsHeal(bot))
        {
            // Other melee follow their chosen mob, rather than being herded
            // back into the hound. Its holding tank separates the two packs.
            if (!ai->IsTank(bot) || current->GetVictim() != bot ||
                (current->GetDistance(selected) >= 20 &&
                 std::cos(selected->GetAngle(current) - selected->GetOrientation()) < -0.25f)) return false;
            // Separate behind the hound: its native 35-yard breath is frontal,
            // so moving 25 yards along its facing would still be unsafe.
            const float angle = selected->GetOrientation() + float(M_PI);
            plan.active = true; plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
            plan.boss = selected->GetObjectGuid(); plan.spell = 19272;
            plan.destination = {selected->GetPositionX()+std::cos(angle)*25,
                selected->GetPositionY()+std::sin(angle)*25, selected->GetPositionZ()};
            if (ValidateEncounterDestination(ai, plan)) return true;
            plan.active = false; return false;
        }
    }
    Unit* victim = selected->GetVictim();
    // A threat reset must not rotate everybody's rear station around a caster
    // who is briefly being chased. Its carrier goes to a tank above; tanks
    // reacquire independently. Other bots keep their usable native cast spot.
    if ((selected->GetEntry() == 11666 || selected->GetEntry() == 11667 || selected->GetEntry() == 12100 || selected->GetEntry() == 11661 || selected->GetEntry() == 11673) &&
        (!victim || !victim->IsPlayer() || !ai->IsTank(static_cast<Player*>(victim)))) return false;
    plan.active = true; plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    plan.boss = selected->GetObjectGuid();
    if (selected->GetEntry() == 12056) return PlanGeddonFormation(ai,selected,plan);
    if (selected->GetEntry() == 11982)
    {
        plan.spell = 19272;
        return PlanMagmadarFormation(ai, selected, plan);
    }
    if (selected->GetEntry() == 12101)
    {
        // Hold the established tank in place; everyone else joins its position.
        // This cannot prevent charges at human players who remain spread out.
        if (victim == bot) { plan.active = false; return false; }
        plan.spell = 19196;
        plan.destination = {victim->GetPositionX(), victim->GetPositionY(), victim->GetPositionZ()};
        if (bot->GetDistance(victim) <= 3)
            plan.destination = {bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
    }
    else
    {
        plan.spell = selected->GetEntry() == 11667 || selected->GetEntry() == 11666 || selected->GetEntry() == 12100 || selected->GetEntry() == 11661 ? 19630 : 19272;
        float angle = selected->GetOrientation() + float(M_PI);
        float distance = std::max(2.0f, selected->GetCombatReach() + bot->GetCombatReach() - 1.0f);
        if (victim == bot && ai->IsTank(bot))
        {
            // The hound faces its victim. Move the tank to the opposite side
            // of the raid, rather than merely turning the player's model.
            float x = 0, y = 0; unsigned count = 0;
            for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
            {
                Player* member = ref->getSource();
                if (!member || member == bot || !member->IsInWorld() || !member->IsAlive() ||
                    !bot->IsInMap(member) || member->IsBeingTeleported() || ai->IsTank(member) ||
                    member->GetDistance(selected) > (selected->GetEntry()==11982?100:40)) continue;
                x += member->GetPositionX(); y += member->GetPositionY(); ++count;
            }
            if (!count) { plan.active = false; return false; }
            x = x / count - selected->GetPositionX(); y = y / count - selected->GetPositionY();
            if (x*x + y*y < 4) { plan.active = false; return false; }
            angle = std::atan2(y, x) + float(M_PI);
            // A wide safe rear sector avoids rotating for tiny centroid shifts.
            if (std::cos(selected->GetAngle(bot) - angle) > 0.86f)
                plan.destination = {bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
            else plan.destination = {selected->GetPositionX() + std::cos(angle)*distance,
                selected->GetPositionY() + std::sin(angle)*distance, selected->GetPositionZ()};
        }
        else
        {
            if (ai->IsTank(bot)) { plan.active = false; return false; }
            if (selected->GetEntry()==11673 && (ai->IsRanged(bot) || ai->IsHeal(bot)))
                return PlanCoreHoundRanged(ai,selected,plan);
            if (ai->IsRanged(bot) || ai->IsHeal(bot))
            {
                distance = 25.0f;
            }
            if (std::cos(selected->GetAngle(bot) - selected->GetOrientation()) < -0.25f &&
                (!(ai->IsRanged(bot) || ai->IsHeal(bot)) || bot->GetDistance(selected) >= 23.0f))
                plan.destination = {bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()};
            else plan.destination = {selected->GetPositionX() + std::cos(angle)*distance,
                selected->GetPositionY() + std::sin(angle)*distance, selected->GetPositionZ()};
        }
    }
    if (ValidateEncounterDestination(ai, plan)) return true;
    plan.active = false;
    return false;
}

namespace
{
    bool RaidMember(Player* bot, Player* member)
    {
        return member && member->IsInWorld() && member->IsAlive() && !member->IsBeingTeleported() &&
            !member->HasCharmer() && bot->IsInMap(member) && member->GetGroup() == bot->GetGroup();
    }

    bool RaidEnemy(Player* bot, Unit* unit)
    {
        return unit && unit->IsInWorld() && unit->IsAlive() && unit->IsInCombat() &&
            !unit->HasCharmer() && bot->IsInMap(unit) && !sServerFacade.IsFriendlyTo(bot, unit);
    }

    bool MoltenCoreBoss(uint32 entry)
    {
        switch (entry)
        {
            case 12118: case 11982: case 12259: case 12057: case 12056:
            case 12264: case 12098: case 11988: case 12018: case 11502: return true;
            default: return false;
        }
    }

    Unit* RaidBoss(PlayerbotAI* ai)
    {
        Unit* result = nullptr;
        Player* bot = ai->GetBot();
        const auto admit = [&](Unit* unit) {
            if (!RaidEnemy(bot, unit) || !MoltenCoreBoss(unit->GetEntry()) || bot->GetDistance(unit) > 100) return true;
            if (result && result != unit) return false;
            result = unit;
            return true;
        };
        for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
        {
            Unit* unit = ai->GetUnit(guid);
            if (!admit(unit)) return nullptr;
        }
        // A ranged bot's local target snapshot can omit the boss while the
        // raid is already fighting it. Native group combat supplies identity;
        // selection, an unpulled nearby boss or a leader's cast is not proof.
        if (bot->GetGroup())
            for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
            {
                Player* member = ref->getSource();
                if (!RaidMember(bot, member) || !member->IsInCombat()) continue;
                for (Unit* attacker : member->getAttackers()) if (!admit(attacker)) return nullptr;
                if (!admit(member->GetVictim())) return nullptr;
            }
        return result;
    }

    Unit* MoltenCoreTrashTankTarget(PlayerbotAI* ai)
    {
        Player* bot = ai->GetBot();
        std::vector<Player*> tanks;
        std::vector<Unit*> enemies = MoltenCoreGroupTrash(ai);
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
            if (RaidMember(bot, ref->getSource()) && ai->IsTank(ref->getSource())) tanks.push_back(ref->getSource());
        std::sort(tanks.begin(), tanks.end(), [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        if (std::find(tanks.begin(), tanks.end(), bot) == tanks.end()) return nullptr;
        enemies.erase(std::remove_if(enemies.begin(), enemies.end(), [&](Unit* enemy) {
            return LavaTrashReservedTarget(ai, enemy) || enemy->HasAura(19951) ||
                PossibleAttackTargetsValue::HasBreakableCC(enemy, bot) ||
                PossibleAttackTargetsValue::HasUnBreakableCC(enemy, bot);
        }), enemies.end());
        std::map<Player*, unsigned> heldCount;
        std::vector<Unit*> loose;
        Unit* held = nullptr;
        for (Unit* enemy : enemies)
        {
            Unit* victim = enemy->GetVictim();
            auto owner = std::find(tanks.begin(), tanks.end(), victim);
            if (owner == tanks.end()) loose.push_back(enemy);
            else
            {
                ++heldCount[*owner];
                if (victim == bot && !held) held = enemy;
            }
        }
        // Allocate actual loose mobs to available tanks, preferring spare
        // tanks before those already holding enemies. A stopped/stunned owner
        // cannot leave a GUID-modulo slot vacant for the other three tanks.
        std::set<Player*> rescuing;
        for (Unit* enemy : loose)
        {
            Player* best = nullptr;
            for (Player* tank : tanks)
            {
                PlayerbotAI* controller = tank->GetPlayerbotAI();
                if (!controller || controller->IsRealPlayer() || !tank->CanReactInCombat() ||
                    tank->IsImmobilizedState() || tank->GetDistance(enemy) > 100 || rescuing.count(tank)) continue;
                if (!best || heldCount[tank] < heldCount[best] ||
                    (heldCount[tank] == heldCount[best] &&
                     (tank->GetDistance(enemy) < best->GetDistance(enemy) ||
                      (tank->GetDistance(enemy) == best->GetDistance(enemy) && tank->GetObjectGuid() < best->GetObjectGuid())))) best = tank;
            }
            if (!best) continue;
            rescuing.insert(best);
            if (best == bot) return enemy;
        }
        return held;
    }

    uint32 RaidAdd(uint32 boss)
    {
        switch (boss)
        {
            case 12118: return 12119;
            case 12259: return 11661;
            case 12057: return 12099;
            case 12098: return 11662;
            case 11988: return 11672;
            case 12018: return 11664;
            case 11502: return 12143;
            default: return 0;
        }
    }

    std::vector<Unit*> RaidAdds(PlayerbotAI* ai, Unit* boss, uint32 entry)
    {
        std::vector<Unit*> result;
        if (!boss || !entry) return result;
        std::list<Unit*> nearby;
        MaNGOS::AllCreaturesOfEntryInRangeCheck check(boss, entry, 100.0f);
        MaNGOS::UnitListSearcher<MaNGOS::AllCreaturesOfEntryInRangeCheck> searcher(nearby, check);
        Cell::VisitAllObjects(boss, searcher, 100.0f);
        for (Unit* unit : nearby)
            if (RaidEnemy(ai->GetBot(), unit)) result.push_back(unit);
        std::sort(result.begin(), result.end(), [](Unit* a, Unit* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        return result;
    }

    Unit* MajordomoFocus(PlayerbotAI* ai, Unit* boss)
    {
        auto elites = RaidAdds(ai, boss, 11664);
        auto healers = RaidAdds(ai, boss, 11663);
        auto& targets = elites.empty() ? healers : elites;
        if (targets.empty()) return nullptr;
        // Every bot uses the same boss-centred GUID order, including CC units.
        // A skull may choose an elite, but cannot release a healer early.
        ObjectGuid skull = ai->GetBot()->GetGroup()->GetTargetIcon(7);
        for (Unit* target : targets)
            if (target->GetObjectGuid() == skull &&
                !PossibleAttackTargetsValue::HasBreakableCC(target, ai->GetBot())) return target;
        for (Unit* target : targets)
            if (!PossibleAttackTargetsValue::HasBreakableCC(target, ai->GetBot()) &&
                !PossibleAttackTargetsValue::HasUnBreakableCC(target, ai->GetBot())) return target;
        return targets.front(); // Release exactly one surviving sheep when tanks are ready.
    }

    ObjectGuid MajordomoSheepOwner(Unit* healer)
    {
        for (Aura* aura : healer->GetAurasByType(SPELL_AURA_MOD_CONFUSE))
            if (aura && aura->GetSpellProto() && aura->GetSpellProto()->Mechanic == MECHANIC_POLYMORPH && aura->GetHolder())
                return aura->GetHolder()->GetCasterGuid();
        return ObjectGuid();
    }

    Unit* MajordomoAssignedHealer(PlayerbotAI* ai, Unit* boss)
    {
        Player* bot=ai->GetBot();
        if (bot->getClass()!=CLASS_MAGE) return nullptr;
        std::vector<Player*> mages;
        for (GroupReference* ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next())
        {
            Player* mage=ref->getSource();
            if (RaidMember(bot,mage) && mage->getClass()==CLASS_MAGE && mage->GetDistance(boss)<=100 &&
                mage->GetPlayerbotAI() && !mage->GetPlayerbotAI()->IsRealPlayer() &&
                mage->GetPlayerbotAI()->HasSpell("polymorph")) mages.push_back(mage);
        }
        std::sort(mages.begin(),mages.end(),[](Player* a,Player* b){return a->GetObjectGuid()<b->GetObjectGuid();});
        auto healers=RaidAdds(ai,boss,11663);
        // Retain native sheep ownership and leave human-owned sheep alone.
        // Rebuilding only from currently attackable targets would cause mages
        // to move onto the next healer and cancel their previous Polymorph.
        std::set<ObjectGuid> occupied;
        for (Unit* healer : healers)
            if (ObjectGuid owner = MajordomoSheepOwner(healer))
            {
                if (owner == bot->GetObjectGuid()) return healer;
                occupied.insert(owner);
            }
        mages.erase(std::remove_if(mages.begin(), mages.end(), [&](Player* mage) {
            return occupied.count(mage->GetObjectGuid()) != 0;
        }), mages.end());
        healers.erase(std::remove_if(healers.begin(), healers.end(), [](Unit* healer) {
            return !MajordomoSheepOwner(healer).IsEmpty();
        }), healers.end());
        auto own=std::find(mages.begin(),mages.end(),bot);
        const size_t slot=std::distance(mages.begin(),own);
        return own!=mages.end() && slot<healers.size()?healers[slot]:nullptr;
    }

    bool MajordomoSupport(PlayerbotAI* ai, Unit* boss, std::string& spell, Unit*& target)
    {
        Player* bot = ai->GetBot();
        const auto ready = [&](const char* name, Unit* unit) {
            // Central native spell admission applies reflection per spell;
            // physical interrupts remain available during Magic Reflection.
            if (!unit || !ai->CanCastSpell(name, unit, 0)) return false;
            spell=name;target=unit;return true;
        };
        auto elites = RaidAdds(ai, boss, 11664);
        auto healers = RaidAdds(ai, boss, 11663);
        Unit* focus = MajordomoFocus(ai, boss);
        if (bot->getClass() == CLASS_MAGE)
        {
            std::vector<Player*> mages;
            for (GroupReference* ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next())
            {
                Player* mage=ref->getSource();
                if (RaidMember(bot,mage) && mage->getClass()==CLASS_MAGE && mage->GetDistance(boss)<=100 &&
                    mage->GetPlayerbotAI() && !mage->GetPlayerbotAI()->IsRealPlayer() &&
                    mage->GetPlayerbotAI()->HasSpell("polymorph")) mages.push_back(mage);
            }
            std::sort(mages.begin(),mages.end(),[](Player* a,Player* b){return a->GetObjectGuid()<b->GetObjectGuid();});
            auto own=std::find(mages.begin(),mages.end(),bot);
            if (own!=mages.end())
            {
                if (Unit* healer=MajordomoAssignedHealer(ai,boss))
                {
                    // Native immunity starts at four add deaths. Never remove
                    // it or keep retrying an impossible Polymorph.
                    if ((!elites.empty() || healer!=focus) && !healer->HasAura(21087) &&
                        !PossibleAttackTargetsValue::HasBreakableCC(healer,bot) &&
                        !PossibleAttackTargetsValue::HasUnBreakableCC(healer,bot) && ready("polymorph",healer)) return true;
                }
                if (elites.empty() && focus && PossibleAttackTargetsValue::HasBreakableCC(focus,bot) && own==mages.begin())
                    for (GroupReference* ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next())
                    {
                        Player* tank=ref->getSource();
                        if (RaidMember(bot,tank) && ai->IsTank(tank) && tank->GetDistance(focus)<=8)
                            for (const char* name : {"frostbolt","fireball"})
                                if (ready(name,focus)) return true; // Real damage breaks only the selected sheep.
                    }
            }
        }
        // Native Flamewaker Healers cast Shadow Bolt, not Rejuvenation.
        // Keep off-target interrupts active when Polymorph immunity starts.
        for (Unit* healer : healers)
        {
            if (PossibleAttackTargetsValue::HasBreakableCC(healer,bot)) continue;
            Spell* cast=healer->GetCurrentSpell(CURRENT_GENERIC_SPELL);
            if (!cast || !cast->m_spellInfo || cast->getState()!=SPELL_STATE_CASTING ||
                cast->m_spellInfo->Id!=21077 || !cast->CanBeInterrupted()) continue;
            for (const char* name : {"pummel","shield bash","kick","counterspell","silence",
#ifdef MANGOSBOT_TWO
                "wind shear","mind freeze"
#else
                "earth shock"
#endif
            }) if (ready(name,healer)) return true;
        }
        return false;
    }

    unsigned MoltenCoreTargetPriority(uint32 boss, uint32 target)
    {
        // These entries and native mechanics match all three CMaNGOS scripts.
        switch (boss)
        {
            case 12118: return target == 12119 ? 1 : 0; // Lucifron's protectors
            case 12259: return target == 11661 ? 1 : 0; // Gehennas's flamewakers
            case 12057: return target == 12099 ? 1 : 0; // Uncontrolled Firesworn; banishes are filtered below.
            case 12098: return target == 11662 ? 1 : 0; // Sulfuron's healing priests
            case 12018: // Majordomo ends on add deaths; the boss has death prevention.
                return target == 11664 ? 2 : (target == 11663 ? 1 : 0);
            case 11988: return target == 11988 ? 1 : 0; // Core Ragers cannot die while Golemagg lives.
            case 11502: return target == 12143 ? 1 : 0; // Ragnaros's native Sons of Flame.
            default: return 0;
        }
    }
}

Unit* MoltenCorePriorityTargetAction::GetTarget()
{
    if (Unit* assigned = MoltenCoreAssignedTankTarget(ai)) return assigned;
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        bot->GetMapId() != 409 || !bot->GetGroup() || ai->IsHeal(bot) || ai->IsTank(bot)) return nullptr;

    Unit* boss = nullptr;
    bool ragSons = false;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "attackers"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit || !unit->IsInWorld() || !bot->IsInMap(unit) || !unit->IsAlive() || !unit->IsInCombat()) continue;
        const uint32 entry = unit->GetEntry();
        if (entry == 12143) ragSons = true;
        if (entry != 12118 && entry != 12259 && entry != 12057 && entry != 12098 && entry != 12018 && entry != 11988 && entry != 11502) continue;
        // Ambiguous multi-boss pulls should retain ordinary player/assist policy.
        if (boss && boss != unit) return nullptr;
        boss = unit;
    }
    if (boss && (boss->GetVictim() == bot || (ragSons && boss->GetEntry() != 11502))) return nullptr;
    // Submerged Ragnaros is correctly absent from attackable-target values.
    // His live, engaged sons identify the add wave without bypassing the
    // native submerged flag, guessing a phase timer or scanning the world.
    const uint32 bossEntry = boss ? boss->GetEntry() : (ragSons ? 11502 : 0);

    auto valid = [this](Unit* unit)
    {
        return unit && unit->IsInWorld() && bot->IsInMap(unit) && unit->IsAlive() && unit->IsInCombat() &&
            PossibleAttackTargetsValue::IsValid(unit, bot, sPlayerbotAIConfig.sightDistance, false, true) &&
            !PossibleAttackTargetsValue::HasBreakableCC(unit, bot) &&
            !PossibleAttackTargetsValue::HasUnBreakableCC(unit, bot);
    };
    // A group attack on the small hound pack starts its native balanced-kill
    // routine. Explicit commands on other mobs remain authoritative.
    Unit* commanded = ai->GetUnit(AI_VALUE(ObjectGuid, "attack target"));
    if (!bossEntry)
        if (Unit* focus = LavaTrashFocusTarget(ai)) return focus;
    if (valid(commanded) && (bossEntry || commanded->GetEntry()!=11671)) return nullptr;
    if (Unit* garr = GarrFocusTarget(ai)) return garr;
    Unit* current = ai->GetUnit(AI_VALUE(ObjectGuid, "current target"));
    Unit* marked = ai->GetUnit(AI_VALUE(ObjectGuid, "rti target"));
    if (!bossEntry)
    {
        // Firelords repeatedly summon; living Lava Spawns split. Clean up the
        // engaged spawns first, then focus a Firelord. A skull on the parent
        // must not pin DPS there while its children multiply. Direct attack
        // commands above remain an explicit override; tanks retain their mob.
        Unit* fireTarget = nullptr;
        unsigned firePriority = 0;
        for (ObjectGuid guid : AI_VALUE(std::list<ObjectGuid>, "possible attack targets"))
        {
            Unit* unit = ai->GetUnit(guid);
            if (!valid(unit)) continue;
            unsigned candidate = unit->GetEntry() == 12265 ? 2 : (unit->GetEntry() == 11668 ? 1 : 0);
            if (!candidate) continue;
            if (!fireTarget || candidate > firePriority || (candidate == firePriority &&
                (unit->GetHealthPercent() < fireTarget->GetHealthPercent() ||
                 (unit->GetHealthPercent() == fireTarget->GetHealthPercent() &&
                  unit->GetObjectGuid() < fireTarget->GetObjectGuid()))))
            {
                fireTarget = unit; firePriority = candidate;
            }
        }
        if (fireTarget)
        {
            if (valid(marked) && marked->GetEntry() == fireTarget->GetEntry()) return marked;
            return fireTarget;
        }
    }
    if (!bossEntry)
        if (Unit* nuke = MoltenCoreNukeTarget(ai)) return nuke;
    if (bossEntry == 12018)
    {
        Unit* focus = MajordomoFocus(ai, boss);
        return valid(focus) ? focus : nullptr;
    }
    if (bossEntry == 11988 && valid(boss)) return boss; // Core Ragers cannot be killed while their master lives.
    if (valid(marked) && (bossEntry || marked->GetEntry() != 11671)) return nullptr;
    if (!bossEntry)
    {
        // Balance the engaged small Core Hounds, not Ancient Core Hounds or
        // Golemagg's Core Ragers. Pack marks initiate the pull and do not pin
        // damage to one hound through its native collapse/reignite cycle.
        std::vector<Unit*> hounds;
        Unit* anchor = valid(current) && current->GetEntry() == 11671 ? current : nullptr;
        for (Unit* unit : MoltenCorePack(ai))
        {
            if (!valid(unit) || unit->GetEntry() != 11671 || unit->HasAura(19951)) continue;
            hounds.push_back(unit);
        }
        if (hounds.empty())
        {
            Unit* patrol = nullptr; Unit* other = nullptr;
            for (ObjectGuid guid : AI_VALUE(std::list<ObjectGuid>, "possible attack targets"))
            {
                Unit* unit = ai->GetUnit(guid);
                if (!valid(unit)) continue;
                Unit*& chosen = unit->GetEntry() == 11673 ? patrol : other;
                if (!chosen || unit == current || (chosen != current && bot->GetDistance(unit) < bot->GetDistance(chosen))) chosen = unit;
            }
            if (patrol && other && other->GetDistance(patrol) <= 40)
                return ai->IsRanged(bot) ? patrol : other;
            return nullptr;
        }
        if (!anchor) anchor = *std::min_element(hounds.begin(), hounds.end(), [this](Unit* a, Unit* b) {
            return bot->GetDistance(a) < bot->GetDistance(b);
        });
        float highest = 0;
        for (Unit* hound : hounds)
            if (hound->GetDistance(anchor) <= 30) highest = std::max(highest, hound->GetHealthPercent());
        // Marks and pull commands cannot pin a hound below twenty percent
        // while another member of its native pack is still healthy. The same
        // highest-health focus is used by assist/area target selection too.
        Unit* focus=nullptr;
        for (Unit* hound : hounds)
        {
            if (hound->GetDistance(anchor)>30 || (highest>20.0f && hound->GetHealthPercent()<=20.0f)) continue;
            if (!focus || hound->GetHealthPercent()>focus->GetHealthPercent() ||
                (hound->GetHealthPercent()==focus->GetHealthPercent() && hound->GetObjectGuid()<focus->GetObjectGuid())) focus=hound;
        }
        // Above the release threshold, tolerate a small health difference to
        // avoid wasting every swing on target churn. Never retain a <=20% dog
        // while a higher-health dog remains.
        if (focus && current && std::find(hounds.begin(),hounds.end(),current)!=hounds.end() &&
            current->GetDistance(anchor)<=30 && current->GetHealthPercent()>20.0f &&
            current->GetHealthPercent()+2.0f>=highest) return current;
        return focus;
    }
    Unit* selected = nullptr;
    unsigned priority = 0;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "possible attack targets"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit) continue;
        const unsigned candidatePriority = MoltenCoreTargetPriority(bossEntry, unit->GetEntry());
        if (!candidatePriority || !valid(unit)) continue;
        if (!selected || candidatePriority > priority || (candidatePriority == priority &&
            (unit == current || (selected != current && bot->GetDistance(unit) < bot->GetDistance(selected)))))
        {
            selected = unit;
            priority = candidatePriority;
        }
    }
    return selected;
}

bool MoltenCorePriorityTargetAction::isUseful()
{
    Unit* target = GetTarget();
    return target && target != ai->GetUnit(AI_VALUE(ObjectGuid, "current target"));
}

bool MoltenCorePositionAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 409) return false;
    plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("molten core position")->Get();
    if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId()) return false;
    if (plan.groundOnly)
    {
        EncounterPosition current;std::vector<encounter::Circle> threats;
        if (!MoltenCoreThreats(ai,current,threats)) return false;
        const encounter::Point here{bot->GetPositionX(),bot->GetPositionY(),bot->GetPositionZ()};
        if (current.groundOnly && encounter::OutsideCircles(here,threats))
        {
            ai->GetAiObjectContext()->GetValue<EncounterPosition>("molten core position")->Reset();
            return false;
        }
    }
    if (plan.spell==1449) return PlanMoltenCoreMageCleave(ai,plan);
    if (plan.spell == 18647)
    {
        Unit* assigned = LavaTrashBanishTarget(ai);
        return assigned && assigned->GetObjectGuid() == plan.boss;
    }
    if (plan.spell == 18945) return PlanMoltenCoreGiants(ai, plan);
    if (plan.spell == 21155)
    {
        if (!PlanRagnarosFormation(ai, plan)) return false;
        ai->GetAiObjectContext()->GetValue<EncounterPosition>("molten core position")->Set(plan);
        return true;
    }
    if (plan.spell == 19771)
    {
        Unit* encounter = ai->GetUnit(plan.boss);
        if (encounter && encounter->GetEntry() == 12018)
        {
            if (!PlanMajordomoFormation(ai, plan)) return false;
            ai->GetAiObjectContext()->GetValue<EncounterPosition>("molten core position")->Set(plan);
            return true;
        }
    }
    if (ai->IsTank(bot))
        if (Unit* assigned=MoltenCoreAssignedTankTarget(ai))
            if (assigned->GetVictim()!=bot) return false; // Reacquisition outranks every cached gathering station.
    if (plan.spell == 20475 && !plan.source.IsEmpty())
    {
        Unit* carrier = plan.source == bot->GetObjectGuid() ? bot : ai->GetUnit(plan.source);
        if (!carrier || !carrier->IsPlayer() || !carrier->IsInWorld() || !bot->IsInMap(carrier) ||
            !carrier->IsAlive() || !carrier->HasAura(20475) || carrier->HasCharmer()) return false;
        Player* member = static_cast<Player*>(carrier);
        return !member->IsBeingTeleported() && member->GetGroup() && member->GetGroup() == bot->GetGroup();
    }
    if (plan.spell != 19196 && plan.spell != 19272 && plan.spell != 19364 && plan.spell != 19630 &&
        plan.spell != 19771 && plan.spell != 20602 && plan.spell != 21155)
    {
        EncounterPosition current;
        std::vector<encounter::Circle> threats;
        return MoltenCoreThreats(ai, current, threats);
    }
    Unit* boss = ai->GetUnit(plan.boss);
    if (boss && !ai->IsTank(bot) &&
        (boss->GetEntry() == 11666 || boss->GetEntry() == 11667 || boss->GetEntry() == 12100 || boss->GetEntry() == 11661))
    {
        Unit* target = ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("current target")->Get());
        if (target && target != boss && target->IsInWorld() && target->IsAlive() && target->IsInCombat() &&
            bot->IsInMap(target) && !sServerFacade.IsFriendlyTo(bot, target))
        {
            ai->GetAiObjectContext()->GetValue<EncounterPosition>("molten core position")->Reset();
            if (!PlanMoltenCoreTrash(ai, plan)) return false;
            ai->GetAiObjectContext()->GetValue<EncounterPosition>("molten core position")->Set(plan);
            return true;
        }
    }
    if (boss && (boss->GetEntry()==11668 || boss->GetEntry()==12265) && plan.spell==19630)
    {
        Unit* current=ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("current target")->Get());
        if (current!=boss || MoltenCorePackStackRequired(ai))
        {
            ai->GetAiObjectContext()->GetValue<EncounterPosition>("molten core position")->Reset();
            return false;
        }
        if (!boss->IsInWorld() || !boss->IsAlive() || !boss->IsInCombat() || !bot->IsInMap(boss)) return false;
        Unit* victim=boss->GetVictim();
        if (!victim || !victim->IsPlayer() || !victim->IsInWorld() || !victim->IsAlive() ||
            !bot->IsInMap(victim) || victim->HasCharmer() ||
            static_cast<Player*>(victim)->IsBeingTeleported() || static_cast<Player*>(victim)->GetGroup()!=bot->GetGroup() ||
            !ai->IsTank(static_cast<Player*>(victim)) || PossibleAttackTargetsValue::HasBreakableCC(boss,bot) ||
            PossibleAttackTargetsValue::HasUnBreakableCC(boss,bot)) return false;
        const auto bounds=FirelordRangedBounds(ai,boss);
        const float dx=plan.destination.x-boss->GetPositionX(),dy=plan.destination.y-boss->GetPositionY(),dz=plan.destination.z-boss->GetPositionZ();
        const float distance=std::sqrt(dx*dx+dy*dy+dz*dz);
        if (distance<bounds.first+2 || distance>bounds.second-2 || !bot->IsWithinLOSInMap(boss) ||
            !boss->IsWithinLOS(plan.destination.x,plan.destination.y,plan.destination.z+bot->GetCollisionHeight(),true))
        {
            ai->GetAiObjectContext()->GetValue<EncounterPosition>("molten core position")->Reset();
            if (!PlanFirelordRanged(ai,plan)) return false;
            ai->GetAiObjectContext()->GetValue<EncounterPosition>("molten core position")->Set(plan);
            return true;
        }
    }
    if (boss && plan.spell == 19771 && !plan.source.IsEmpty() && plan.source != bot->GetObjectGuid() &&
        !ai->IsTank(bot) && MoltenCoreRecoveryTrash(boss->GetEntry()))
    {
        // Recovery belongs to this aggro carrier, not to a remembered rear
        // station. Release the hold immediately after native tank pickup.
        if (boss->GetVictim() != bot) return PlanMoltenCoreTrash(ai, plan);
        return PlanLavaTrashCarrier(ai, plan);
    }
    if (boss && boss->IsInWorld() && bot->IsInMap(boss) && boss->IsAlive() && boss->IsInCombat() &&
        boss->GetEntry()==11673 && boss->GetVictim()!=bot &&
        (plan.spell==19272 || plan.spell==19364))
    {
        const float station=std::atan2(plan.destination.y-boss->GetPositionY(),plan.destination.x-boss->GetPositionX());
        if (std::cos(station-boss->GetOrientation())>0.0f)
        {
            ai->GetAiObjectContext()->GetValue<EncounterPosition>("molten core position")->Reset();
            return PlanMoltenCoreTrash(ai,plan);
        }
    }
    if (boss && boss->GetEntry()==11982 && plan.spell==19272 && boss->IsInWorld() &&
        boss->IsAlive() && boss->IsInCombat() && bot->IsInMap(boss))
    {
        // Replan immediately after a fear turns the boss or a relocation
        // leaves the cached station in the frontal half of the room.
        bool displaced=plan.anchored && std::hypot(plan.anchor.x-boss->GetPositionX(),plan.anchor.y-boss->GetPositionY())>1.5f;
        if (boss->GetVictim()!=bot)
        {
            const bool ranged=!ai->IsTank(bot) && (ai->IsRanged(bot)||ai->IsHeal(bot)||bot->getClass()==CLASS_HUNTER);
            Unit* patient=ai->IsHeal(bot)&&boss->GetVictim()&&boss->GetVictim()->IsPlayer()?boss->GetVictim():boss;
            float range=std::max(2.0f,boss->GetCombatReach()+bot->GetCombatReach()-1);
            if (ranged)
            {
                if (!patient->IsInWorld() || !bot->IsInMap(patient) ||
                    !ai->GetSpellRange(MoltenCoreRangeSpell(ai,bot),&range) || !std::isfinite(range) || range<=0) return false;
                range+=bot->GetCombatReach()+patient->GetCombatReach()-2;
            }
            const float dx=plan.destination.x-patient->GetPositionX(),dy=plan.destination.y-patient->GetPositionY(),dz=plan.destination.z-patient->GetPositionZ();
            const float distance=std::sqrt(dx*dx+dy*dy+dz*dz);
            displaced=displaced || distance>range+0.5f ||
                (ranged && !patient->IsWithinLOS(plan.destination.x,plan.destination.y,plan.destination.z+bot->GetCollisionHeight(),true));
        }
        if (boss->GetVictim()==bot || displaced || std::cos(std::atan2(plan.destination.y-boss->GetPositionY(),
            plan.destination.x-boss->GetPositionX())-boss->GetOrientation())>0)
        {
            if (!PlanMagmadarFormation(ai,boss,plan)) return false;
            ai->GetAiObjectContext()->GetValue<EncounterPosition>("molten core position")->Set(plan);
            return true;
        }
    }
    if (plan.spell==19771 && ai->IsTank(bot) && boss &&
        (boss->GetEntry()==11671 || boss->GetEntry()==11669))
    {
        Unit* loose=MoltenCorePackTankTarget(ai);
        if (loose && loose->GetVictim()!=bot) return false; // Invalidate an old gathering hold immediately.
    }
    return boss && boss->IsInWorld() && bot->IsInMap(boss) && boss->IsAlive() && boss->IsInCombat() &&
        ((plan.spell!=20602 && !(plan.spell==19771 && plan.source==bot->GetObjectGuid())) ||
         ((boss->GetEntry()==11669 || boss->GetEntry()==11671) && !boss->HasAura(19951) &&
          boss->GetVictim()==bot && !ai->IsTank(bot)));
}

bool MoltenCorePositionAction::isUseful()
{
    EncounterPosition plan;
    if (!GetPlan(ai,plan)) return false;
    // Formation adjustments wait for a real cast/channel to finish. Otherwise
    // a one-yard formation correction can cancel Frostbolt (or any class's
    // damage/heal) repeatedly without ever completing useful work.
    if (bot->IsNonMeleeSpellCasted(false,false,true) && !ShouldReactionInterruptCast()) return false;
    return EncounterMovementRequired(bot, plan.destination);
}

bool MoltenCorePositionAction::ShouldReactionInterruptCast() const
{
    EncounterPosition plan;
    if (!ai->CanMove() || !GetPlan(ai,plan) ||
        bot->GetDistance(plan.destination.x,plan.destination.y,plan.destination.z)<=1.5f) return false;
    // Carrying a bomb/loose mob and escaping a real hazard outrank casts.
    if (!plan.source.IsEmpty() && plan.source==bot->GetObjectGuid()) return true;
    const bool formation=plan.spell==1449 || plan.spell==18945 || plan.spell==19196 || plan.spell==19272 ||
        plan.spell==19364 || plan.spell==19630 || plan.spell==19771 || plan.spell==20602 || plan.spell==21155;
    if (!formation) return true;
    std::list<HazardPosition> fire;
    AppendMoltenCoreGroundHazards(ai,fire);
    const WorldPosition here(bot);
    for (const auto& hazard:fire)
        if (here.distance(hazard.first)<hazard.second) return true;
    Unit* boss=ai->GetUnit(plan.boss);
    // Fear can leave a melee/caster directly in Magmadar's breath. That is a
    // real emergency; ordinary maximum-range/spacing adjustments are not.
    return boss && boss->GetEntry()==11982 && boss->IsInWorld() && boss->IsAlive() &&
        bot->IsInMap(boss) && boss->GetVictim()!=bot &&
        std::cos(boss->GetAngle(bot)-boss->GetOrientation())>0;
}

bool MoltenCorePositionAction::Execute(Event& event)
{
    EncounterPosition plan, current;
    std::vector<encounter::Circle> threats;
    if (!GetPlan(ai, plan) || !ai->CanMove()) return false;
    if (bot->IsNonMeleeSpellCasted(false,false,true) && !ShouldReactionInterruptCast()) return false;
    if (plan.spell == 21155)
    {
        if (!PlanRagnarosFormation(ai, current)) return false;
        plan = current;
        if (!ValidateEncounterDestination(ai, plan, false)) return false;
        if (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 3 &&
            !ai->IsRanged(bot) && !ai->IsHeal(bot))
        {
            JumpAction jump(ai); jump.Qualify("ragnaros");
            if (jump.Execute(event)) return true;
        }
    }
    else if (plan.spell == 18945 || plan.spell == 19196 || plan.spell == 19272 || plan.spell == 19364 || plan.spell == 19630 ||
        plan.spell == 19771 || plan.spell == 20602 || plan.spell == 1449)
    {
        // GetPlan admitted this exact station. Replacing it with a different
        // fresh formation here could stop/reverse the route on every reaction.
        if (MoltenCoreThreats(ai, current, threats))
        {
            // A safe formation must remain executable in the ground-fire
            // approach band. Destination and full native route are checked
            // below; bombs and other live mechanics retain their own escape.
            if (!current.groundOnly || current.spell || !current.source.IsEmpty() ||
                !encounter::OutsideCircles(plan.destination,threats)) return false;
        }
    }
    else if (!MoltenCoreThreats(ai, current, threats)) return false;
    if (
        !ValidateEncounterDestination(ai, plan) || !encounter::OutsideCircles(plan.destination, threats)) return false;
    if (bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) <= 1.5f)
    {
        ai->StopMoving();
        SetDuration(100);
        return true;
    }
    if (bot->movespline && !bot->movespline->Finalized())
    {
        const auto end=bot->movespline->FinalDestination();
        if (std::hypot(end.x-plan.destination.x,end.y-plan.destination.y)<=1.5f &&
            std::fabs(end.z-plan.destination.z)<=1.5f)
        { SetDuration(100);return true; } // Let the admitted native route finish.
    }
    return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
}

std::vector<Unit*> ai::MoltenCoreGroupTrash(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    std::vector<Unit*> enemies;
    if (!bot->GetGroup() || !bot->IsInWorld() || bot->GetMapId() != 409) return enemies;
    const auto add = [&](Unit* enemy) {
        if (MoltenCoreRecoveryTrash(enemy ? enemy->GetEntry() : 0) && MoltenCoreGroupEnemy(ai, enemy) &&
            std::find(enemies.begin(), enemies.end(), enemy) == enemies.end()) enemies.push_back(enemy);
    };
    // Share native attacker identities across the raid. Per-bot 50-yard
    // snapshots produced different allocations and missed fleeing mobs.
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!member || !member->IsInWorld() || !bot->IsInMap(member) || member->IsBeingTeleported() || member->HasCharmer()) continue;
        for (Unit* enemy : member->getAttackers()) add(enemy);
        if (PlayerbotAI* controller = member->GetPlayerbotAI())
            add(ai->GetUnit(controller->GetAiObjectContext()->GetValue<ObjectGuid>("current target")->Get()));
    }
    for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get()) add(ai->GetUnit(guid));
    std::sort(enemies.begin(), enemies.end(), [](Unit* a, Unit* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
    return enemies;
}

bool ai::PlanMoltenCoreGiants(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    if (!ai->IsTank(bot) || !bot->GetGroup() || !bot->IsInWorld() || bot->GetMapId() != 409) return false;
    std::vector<Unit*> giants;
    for (Unit* enemy : MoltenCoreGroupTrash(ai))
        if ((enemy->GetEntry() == 11658 || enemy->GetEntry() == 11659) && enemy->GetVictim() && enemy->GetVictim()->IsPlayer() &&
            RaidMember(bot, static_cast<Player*>(enemy->GetVictim())) && ai->IsTank(static_cast<Player*>(enemy->GetVictim()))) giants.push_back(enemy);
    if (giants.size() < 2) return false;
    Unit* assigned = MoltenCoreAssignedTankTarget(ai);
    if (!assigned || assigned->GetVictim() != bot || assigned == giants.front() ||
        std::find(giants.begin(), giants.end(), assigned) == giants.end() || assigned->GetDistance(giants.front()) <= 5) return false;
    Unit* anchor = giants.front();
    Unit* tank = anchor->GetVictim();
    const float angle = anchor->GetAngle(tank);
    const float distance = std::max(anchor->GetDistance(tank), assigned->GetCombatReach() + bot->GetCombatReach() + 1.0f);
    plan.active = true; plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    plan.boss = assigned->GetObjectGuid(); plan.source = tank->GetObjectGuid(); plan.spell = 18945;
    plan.destination = {anchor->GetPositionX() + std::cos(angle)*distance,
        anchor->GetPositionY() + std::sin(angle)*distance, anchor->GetPositionZ()};
    if (ValidateEncounterDestination(ai, plan)) return true;
    plan.active = false; return false;
}

Unit* ai::MoltenCoreAssignedTankTarget(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 409 || !bot->GetGroup() || !ai->IsTank(bot) || ai->IsRealPlayer()) return nullptr;
    Unit* boss = RaidBoss(ai);
    // A raid Attack order chooses the DPS focus, not ownership of every trash
    // mob. Native pickup and an established held mob outrank that focus.
    if (!boss)
    {
        if (Unit* assigned = MoltenCorePackTankTarget(ai)) return assigned;
        return MoltenCoreTrashTankTarget(ai);
    }
    // Dedicated boss tactics retain explicit human orders.
    Unit* commanded=ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("attack target")->Get());
    if (RaidEnemy(bot,commanded) && commanded->GetEntry()!=11671 && commanded->GetEntry()!=11669) return nullptr;
    if (Unit* assigned = GarrTankTarget(ai)) return assigned;
    if (Unit* assigned = MoltenCorePackTankTarget(ai)) return assigned;
    std::vector<Player*> tanks;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (RaidMember(bot, member) && ai->IsTank(member) && member->GetDistance(boss) <= 100) tanks.push_back(member);
    }
    std::sort(tanks.begin(), tanks.end(), [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
    // Preserve the established main tank (including a human), rather than
    // changing ownership every time an off-tank acquires an add.
    PreserveMoltenCoreTank(ai, boss, tanks);
    auto own = std::find(tanks.begin(), tanks.end(), bot);
    if (own == tanks.end()) return nullptr;
    const size_t slot = std::distance(tanks.begin(), own);
    auto valid = [bot](Unit* unit) {
        return RaidEnemy(bot, unit) &&
            PossibleAttackTargetsValue::IsValid(unit, bot, 100.0f, false, true) &&
            !PossibleAttackTargetsValue::HasBreakableCC(unit, bot) &&
            !PossibleAttackTargetsValue::HasUnBreakableCC(unit, bot);
    };
    if (slot == 0) return valid(boss) ? boss : nullptr;
    std::vector<Unit*> adds = RaidAdds(ai, boss, RaidAdd(boss->GetEntry()));
    if (boss->GetEntry() == 12018)
    {
        auto healers = RaidAdds(ai, boss, 11663);
        adds.insert(adds.end(), healers.begin(), healers.end());
    }
    // Keep CC targets in the allocation so banish/sheep does not reshuffle
    // every other tank. A tank's assigned CC target is never attacked.
    const size_t offTanks = tanks.size() - 1;
    Unit* selected = nullptr;
    for (size_t i = slot - 1; i < adds.size(); i += offTanks)
    {
        Unit* add = adds[i];
        if (!valid(add)) continue;
        if (!selected || (selected->GetVictim() == bot && add->GetVictim() != bot)) selected = add;
    }
    return selected; // No add assignment means ordinary tank behavior can resume.
}

bool MoltenCoreSupportAction::Select(std::string& spell, Unit*& target)
{
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 409 || !bot->IsInCombat() || !bot->GetGroup() || ai->IsRealPlayer()) return false;
    Unit* boss = RaidBoss(ai);
    const auto ready = [&](const char* name, Unit* unit) {
        if (!unit || !ai->CanCastSpell(name, unit, 0)) return false;
        spell = name; target = unit; return true;
    };
    // Soul Burn silences damage dealers, allowing spawns to multiply. This
    // trash dispel must not depend on a raid boss being in the target list.
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!RaidMember(bot, member) || !member->HasAura(19393)) continue;
        for (const char* name : {"dispel magic", "cleanse"})
            if (ready(name, member)) return true;
    }
    if (ai->IsTank(bot))
    {
        for (const char* name : {"challenging shout","challenging roar"})
            if (MoltenCoreImpTauntAllowed(ai,name) && ready(name,bot)) return true;
        // Native survival cooldowns supplement tank threat; Fire Nova remains
        // an unavoidable risk for the tanks, so do not wait until near death.
        const auto pack=MoltenCorePack(ai);
        if (!pack.empty() && pack.front()->GetEntry()==11669 && bot->GetHealthPercent()<60)
            for (const char* name : {"shield wall","last stand","frenzied regeneration","barkskin",
#ifndef MANGOSBOT_ZERO
                "divine protection",
#endif
#ifdef MANGOSBOT_TWO
                "icebound fortitude","anti-magic shell",
#endif
            }) if (ready(name,bot)) return true;
    }
    if (ai->IsTank(bot))
    {
        Unit* assigned = MoltenCoreAssignedTankTarget(ai);
        Unit* victim = assigned ? assigned->GetVictim() : nullptr;
        const bool otherTank = victim && victim->IsPlayer() && victim->IsAlive() &&
            bot->IsInMap(victim) && static_cast<Player*>(victim)->GetGroup() == bot->GetGroup() &&
            ai->IsTank(static_cast<Player*>(victim));
        if (assigned && victim != bot && (!otherTank || GarrTankHandoff(ai, assigned)))
        {
            for (const char* name : {"taunt", "growl", "hand of reckoning", "righteous defense", "dark command"})
                if (ready(name, assigned)) return true;
            // Taunt-immune or cooldown-blocked enemies still receive ordinary
            // learned threat attacks. No immunity/stance/resource shortcuts.
            for (const char* name : {"shield slam", "revenge", "mangle (bear)", "maul", "judgement", "sunder armor"})
                if (ready(name, assigned)) return true;
        }
    }
    if (Unit* add = GarrBanishTarget(ai))
        if (ready("banish", add)) return true;
    if (!boss)
        if (Unit* add = LavaTrashBanishTarget(ai))
            if (ready("banish", add)) return true;
    if (!boss) return false;
    // Establish/restore sheep before optional curses and resistance support.
    // An unavailable native cast still allows the other useful support below.
    if (boss->GetEntry() == 12018 && MajordomoSupport(ai, boss, spell, target)) return true;
    if (boss->GetEntry() == 11502 && boss->GetVictim() == bot && ai->IsTank(bot) && bot->GetHealthPercent() < 50)
        for (const char* name : {"shield wall", "last stand", "frenzied regeneration", "barkskin",
#ifndef MANGOSBOT_ZERO
            "divine protection",
#endif
#ifdef MANGOSBOT_TWO
            "icebound fortitude", "vampiric blood", "anti-magic shell",
#endif
        }) if (ready(name,bot)) return true;
    if (boss->GetEntry() == 11502 && !boss->HasAura(21859) && !boss->HasAura(21107) &&
        ai->IsHeal(bot) && boss->GetVictim() && boss->GetVictim()->IsPlayer() &&
        boss->GetVictim()->GetHealthPercent() < 80)
        for (const char* name : {"flash heal", "flash of light", "healing wave", "healing touch", "penance"})
            if (ready(name,boss->GetVictim())) return true;
    if (boss->GetEntry() == 12056 && boss->HasAura(19695) && ai->IsHeal(bot) && boss->GetVictim() &&
        boss->GetVictim()->IsPlayer() && boss->GetVictim()->GetHealthPercent() < 80)
        for (const char* name : {"flash heal", "flash of light", "healing wave", "healing touch", "penance"})
            if (ready(name,boss->GetVictim())) return true;
    if (boss->GetEntry() == 11988)
    {
        auto dogs = RaidAdds(ai, boss, 11672);
        const bool holding = boss->GetVictim() == bot || std::any_of(dogs.begin(), dogs.end(),
            [bot = bot](Unit* dog) { return dog->GetVictim() == bot; });
        Aura* splash = ai->GetAura(13880, bot);
        if (ai->IsTank(bot) && holding && (bot->GetHealthPercent() < 50 ||
            (boss->GetVictim() == bot && splash && splash->GetStackAmount() >= 5)))
            for (const char* name : {"shield wall", "last stand", "frenzied regeneration", "barkskin",
#ifndef MANGOSBOT_ZERO
                "divine protection",
#endif
#ifdef MANGOSBOT_TWO
                "icebound fortitude", "vampiric blood", "anti-magic shell",
#endif
                })
                if (ready(name, bot)) return true;
        if (ai->IsHeal(bot))
        {
            std::vector<Player*> patients;
            const auto addPatient = [&](Unit* unit) {
                if (!unit || !unit->IsPlayer()) return;
                Player* tank = static_cast<Player*>(unit);
                if (RaidMember(bot, tank) && ai->IsTank(tank) && tank->GetHealthPercent() < 80 &&
                    std::find(patients.begin(), patients.end(), tank) == patients.end()) patients.push_back(tank);
            };
            addPatient(boss->GetVictim());
            for (Unit* dog : dogs) addPatient(dog->GetVictim());
            std::sort(patients.begin(), patients.end(), [](Player* a, Player* b) {
                return a->GetHealthPercent() != b->GetHealthPercent() ? a->GetHealthPercent() < b->GetHealthPercent() :
                    a->GetObjectGuid() < b->GetObjectGuid();
            });
            for (Player* patient : patients)
                for (const char* name : {"penance", "flash heal", "flash of light", "healing wave", "healing touch"})
                    if (ready(name, patient)) return true;
        }
    }
    // Dominate Mind makes the raid member hostile: ordinary friendly-party
    // dispel selection deliberately excludes that player. Offensive Dispel
    // Magic can remove the verified aura; native eligibility still decides.
    if (boss->GetEntry() == 12118)
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (member && member->IsInWorld() && member->IsAlive() && bot->IsInMap(member) &&
                !member->IsBeingTeleported() && member->GetGroup() == bot->GetGroup() &&
                member->HasAura(20604) && ready("dispel magic", member)) return true;
        }
    // Magmadar's actual Frenzy aura; do not shoot merely because the boss exists.
    if (boss->GetEntry() == 11982 && boss->HasAura(19451) && ready("tranquilizing shot", boss)) return true;
    // Pre-emptive protection for the current Magmadar tank when actually learned.
    if (boss->GetEntry() == 11982 && boss->GetVictim() && boss->GetVictim()->IsPlayer())
    {
        Player* tank = static_cast<Player*>(boss->GetVictim());
        if (RaidMember(bot, tank) && !ai->HasAura("fear ward", tank) && ready("fear ward", tank)) return true;
    }
    if (boss->GetEntry()==11982)
    {
        Spell* panic=boss->GetCurrentSpell(CURRENT_GENERIC_SPELL);
        const bool fearCast=panic && panic->m_spellInfo && panic->m_spellInfo->Id==19408 &&
            panic->getState()!=SPELL_STATE_FINISHED;
        if (bot->HasAura(19408) || (ai->IsTank(bot) && fearCast && !bot->HasAura(6346)))
        {
            if (ready("berserker rage",bot)) return true;
            // Dance only in response to an actual cast and a ready learned
            // Rage. Native stance/fear restrictions can still reject the cast.
            if (fearCast && bot->getClass()==CLASS_WARRIOR && ai->IsTank(bot) &&
                ai->HasSpell("berserker rage") && bot->IsSpellReady(18499) &&
                !bot->HasAura(18499) && ready("berserker stance",bot)) return true;
        }
        if (ai->IsTank(bot) && bot->HasAura(18499) && bot->HasAura(2458) && ready("defensive stance",bot)) return true;
        // Panic is magic-dispellable; Conflagration is not. Keep the tank first
        // in the dispel order without guessing the boss's random fear timer.
        Unit* victim=boss->GetVictim();
        if (victim && victim->IsPlayer() && RaidMember(bot,static_cast<Player*>(victim)) &&
            victim->HasAura(19408))
            for (const char* name : {"dispel magic","cleanse"}) if (ready(name,victim)) return true;
        for (GroupReference* ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next())
        {
            Player* member=ref->getSource();
            if (!RaidMember(bot,member) || !member->HasAura(19408)) continue;
            for (const char* name : {"dispel magic","cleanse"}) if (ready(name,member)) return true;
        }
    }
    // Counter an active priest heal, including a priest other than our DPS target.
    if (boss->GetEntry() == 12098)
        for (Unit* priest : RaidAdds(ai, boss, 11662))
        {
            Spell* cast = priest->GetCurrentSpell(CURRENT_GENERIC_SPELL);
            if (!cast || !cast->m_spellInfo || cast->getState() != SPELL_STATE_CASTING || cast->m_spellInfo->Id != 19775 ||
                !cast->CanBeInterrupted()) continue;
            for (const char* name : {"pummel", "shield bash", "kick", "counterspell", "silence",
#ifdef MANGOSBOT_TWO
                "wind shear", "mind freeze"
#else
                "earth shock"
#endif
            })
                if (ready(name, priest)) return true;
        }
    // Dispel priority is tied to actual live auras, not guesses about boss timers.
    // No blanket dispels of beneficial/other encounter effects.
    for (uint32 aura : {19702u, 19716u, 19659u, 19703u, 19713u, 20294u, 19776u})
    {
        std::vector<Player*> afflicted;
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (RaidMember(bot, member) && member->HasAura(aura)) afflicted.push_back(member);
        }
        std::sort(afflicted.begin(), afflicted.end(), [this](Player* a, Player* b) {
            if (ai->IsTank(a) != ai->IsTank(b)) return ai->IsTank(a);
            if (a->GetHealthPercent() != b->GetHealthPercent()) return a->GetHealthPercent() < b->GetHealthPercent();
            return a->GetObjectGuid() < b->GetObjectGuid();
        });
        for (Player* member : afflicted)
        {
            if (aura == 19702 || aura == 19659 || aura == 20294 || aura == 19776)
            {
                for (const char* name : {"dispel magic", "cleanse"}) if (ready(name, member)) return true;
            }
            else
                for (const char* name : {"remove lesser curse", "remove curse", "cleanse spirit"}) if (ready(name, member)) return true;
        }
    }
    if (boss->GetEntry() == 12264 && boss->HasAura(19714))
        for (const char* name : {"purge", "dispel magic", "spellsteal"}) if (ready(name, boss)) return true;

    return false;
}

bool MoltenCoreSupportAction::isUseful()
{
    std::string spell; Unit* target = nullptr;
    return Select(spell, target);
}

bool MoltenCoreSupportAction::Execute(Event& event)
{
    std::string spell; Unit* target = nullptr;
    if (!Select(spell, target)) return false; // Recheck on execution; never retain raw unit pointers.
    uint32 duration = sPlayerbotAIConfig.globalCoolDown;
    if (!ai->CastSpell(spell, target, nullptr, false, &duration)) return false;
    SetDuration(duration);
    return true;
}

bool ai::MoltenCoreDouseItemAvailable(PlayerbotAI* ai, uint32 itemId)
{
#ifdef MANGOSBOT_TWO
    // Native Wrath extinguishes runes on boss death; no player dousing.
    return false;
#else
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 409 || bot->IsInCombat() || !bot->GetGroup() || ai->IsRealPlayer() ||
        bot->IsNonMeleeSpellCasted(false, false, true)) return false;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (member && member->IsInWorld() && bot->IsInMap(member) && member->IsInCombat()) return false;
    }
    for (uint32 item : {22754u, 17333u})
    {
        // Real inventory is required even when generic bot item cheats are on.
        if ((itemId && itemId != item) || !bot->HasItemCount(item, 1)) continue;
        UseItemIdAction use(ai);
        use.Qualify(int32(item));
        if (use.isPossible() && use.isUseful()) return true;
    }
    return false;
#endif
}

GameObject* ai::MoltenCoreRuneTarget(PlayerbotAI* ai, bool close)
{
    if (!MoltenCoreDouseItemAvailable(ai)) return nullptr;
    Player* bot = ai->GetBot();
    InstanceData* instance = bot->GetMap()->GetInstanceData();
    if (!instance) return nullptr;
    GameObject* selected = nullptr;
    for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("nearest game objects")->Get())
    {
        GameObject* rune = ai->GetGameObject(guid);
        if (!rune || !rune->IsInWorld() || !bot->IsInMap(rune) || !sServerFacade.isSpawned(rune) ||
            rune->HasFlag(GAMEOBJECT_FLAGS, GO_FLAG_IN_USE) || rune->GetGoState() != GO_STATE_READY ||
            rune->GetLootState() != GO_READY) continue;
        GameObject* flames = rune->GetLinkedTrap();
        if (flames && sServerFacade.isSpawned(flames) && flames->GetLootState() == GO_READY) continue;
        uint32 encounter;
        // Same rune-to-encounter mapping as native Classic/TBC molten_core.h.
        switch (rune->GetEntry())
        {
            case 176956: encounter = 1; break;
            case 176957: encounter = 2; break;
            case 176955: encounter = 3; break;
            case 176953: encounter = 4; break;
            case 176952: encounter = 5; break;
            case 176954: encounter = 6; break;
            case 176951: encounter = 7; break;
            default: continue;
        }
        if (instance->GetData(encounter) != DONE || bot->GetDistance(rune) > sPlayerbotAIConfig.sightDistance ||
            (close && bot->GetDistance(rune) > INTERACTION_DISTANCE)) continue;
        if (!selected || bot->GetDistance(rune) < bot->GetDistance(selected) ||
            (bot->GetDistance(rune) == bot->GetDistance(selected) && rune->GetObjectGuid() < selected->GetObjectGuid())) selected = rune;
    }
    return selected;
}

bool MoveToMCRuneAction::isUseful()
{
    GameObject* rune = MoltenCoreRuneTarget(ai, false);
    return rune && ai->CanMove() && bot->GetDistance(rune) > INTERACTION_DISTANCE;
}

bool MoveToMCRuneAction::Execute(Event& event)
{
    GameObject* rune = MoltenCoreRuneTarget(ai, false);
    if (!rune || !ai->CanMove() || bot->GetDistance(rune) <= INTERACTION_DISTANCE) return false;
    return MoveTo(bot->GetMapId(), rune->GetPositionX(), rune->GetPositionY(), rune->GetPositionZ());
}

bool DouseMCRuneAction::isPossible()
{
    return MoltenCoreDouseItemAvailable(ai, GetItemId()) && UseItemIdAction::isPossible();
}

bool DouseMCRuneAction::isUseful()
{
    return isPossible() && MoltenCoreRuneTarget(ai, true) && UseItemIdAction::isUseful();
}

bool DouseMCRuneAction::Execute(Event& event)
{
    // Re-resolve the object and recheck possession/cooldown at execution time.
    // The native item spell handles the rune, consumption and cooldown.
    if (!isPossible() || !UseItemIdAction::isUseful()) return false;
    GameObject* rune = MoltenCoreRuneTarget(ai, true);
    return rune && UseItem(event.getOwner(), GetItemId(), rune);
}

bool ai::PlanGolemaggFormation(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 409 || !bot->IsInCombat() || !bot->GetGroup() || ai->IsRealPlayer()) return false;
    Unit* boss = RaidBoss(ai);
    if (!boss || boss->GetEntry() != 11988) return false;
    const float facing = boss->GetVictim() && boss->GetVictim()->IsInWorld() ? boss->GetAngle(boss->GetVictim()) : boss->GetOrientation();
    float angle = facing + float(M_PI);
    float distance = 0;
    Unit* centre = boss;
    if (ai->IsTank(bot))
    {
        Unit* assigned = MoltenCoreAssignedTankTarget(ai);
        if (!assigned || assigned->GetEntry() != 11672 || assigned->GetVictim() != bot) return false;
        // Move the holding tank beyond the native boss->dog buff radius,
        // including both reaches and the dog's melee approach to its tank.
        const float trust = NativeEncounterSpellRadius(20556);
        if (trust <= 0) return false;
        distance = trust + boss->GetCombatReach() + assigned->GetCombatReach() +
            assigned->GetCombatReach() + bot->GetCombatReach() + 5;
        if (distance > 85) return false; // Retain the native encounter's 100-yard range.
        auto dogs = RaidAdds(ai, boss, 11672);
        auto own = std::find(dogs.begin(), dogs.end(), assigned);
        if (own == dogs.end()) return false;
        // Distinct side stations keep both dogs away from the ranged rear lane.
        angle = facing + (std::distance(dogs.begin(), own) % 2 ? -1.0f : 1.0f) * float(M_PI)/2;
    }
    else if (ai->IsRanged(bot) || ai->IsHeal(bot))
    {
        const bool healer = ai->IsHeal(bot);
        const char* spell = healer ?
            (bot->getClass()==CLASS_PALADIN?"flash of light":bot->getClass()==CLASS_SHAMAN?"healing wave":
             bot->getClass()==CLASS_DRUID?"healing touch":"flash heal") :
            (bot->getClass()==CLASS_HUNTER?"auto shot":bot->getClass()==CLASS_WARLOCK?"shadow bolt":
             bot->getClass()==CLASS_PRIEST?"mind blast":bot->getClass()==CLASS_SHAMAN?"lightning bolt":
             bot->getClass()==CLASS_DRUID?"wrath":"frostbolt");
        if (!healer && bot->getClass()==CLASS_MAGE)
        {
            spell=MagePrimaryDamageSpell(ai);
        }
        if (healer)
        {
            Unit* patient = ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("party member to heal")->Get());
            if (patient && patient->IsPlayer() && RaidMember(bot, static_cast<Player*>(patient))) centre = patient;
            else if (boss->GetVictim() && boss->GetVictim()->IsPlayer() && RaidMember(bot, static_cast<Player*>(boss->GetVictim()))) centre = boss->GetVictim();
            // Healers may move to support either isolated dog tank; use the
            // actual patient's legal healing range, rather than boss distance.
            angle = centre->GetAngle(bot);
        }
        float range = 0;
        if (!ai->GetSpellRange(spell, &range) || range <= 5) return false;
        distance = range + centre->GetCombatReach() + bot->GetCombatReach() - 2;
        if (!healer) angle += (float(bot->GetGUIDLow() % 5)-2)*0.08f;
    }
    else return false; // Existing native Magma Splash withdrawal handles melee DPS.
    plan.active=true;plan.map=bot->GetMapId();plan.instance=bot->GetInstanceId();
    plan.boss=boss->GetObjectGuid();plan.spell=19771;
    for (float offset : {0.0f, 0.10f, -0.10f, 0.20f, -0.20f, 0.60f, -0.60f, 1.0f, -1.0f})
    {
        plan.destination={centre->GetPositionX()+std::cos(angle+offset)*distance,
            centre->GetPositionY()+std::sin(angle+offset)*distance,centre->GetPositionZ()};
        if (ai->IsHeal(bot) && std::hypot(plan.destination.x-boss->GetPositionX(), plan.destination.y-boss->GetPositionY()) <
            NativeEncounterSpellRadius(19798)+boss->GetCombatReach()+bot->GetCombatReach()+2) continue;
        if (ValidateEncounterDestination(ai,plan)) return true;
    }
    plan.active=false;return false;
}

bool ai::PlanMajordomoFormation(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot=ai->GetBot();
    if (!bot || !bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId()!=409 || !bot->IsInCombat() || !bot->GetGroup() || ai->IsRealPlayer()) return false;
    Unit* boss=RaidBoss(ai);
    if (!boss || boss->GetEntry()!=12018) return false;
    if (Unit* healer=MajordomoAssignedHealer(ai,boss))
    {
        if (healer->HasAura(21087) || healer->GetReflectChance(SPELL_SCHOOL_MASK_ALL)>=50 ||
            PossibleAttackTargetsValue::HasBreakableCC(healer,bot) || PossibleAttackTargetsValue::HasUnBreakableCC(healer,bot) ||
            (RaidAdds(ai,boss,11664).empty() && healer==MajordomoFocus(ai,boss))) return false;
        float range=0;
        if (!ai->GetSpellRange("polymorph",&range) || range<=5) return false;
        const float distance=range+healer->GetCombatReach()+bot->GetCombatReach()-3;
        const float angle=healer->GetAngle(bot);
        plan.active=true;plan.map=bot->GetMapId();plan.instance=bot->GetInstanceId();plan.boss=boss->GetObjectGuid();plan.spell=19771;
        if (bot->GetDistance(healer) <= distance + 1 && bot->IsWithinLOSInMap(healer))
        {
            plan.destination={bot->GetPositionX(),bot->GetPositionY(),bot->GetPositionZ()};
            if (ValidateEncounterDestination(ai,plan,false)) return true;
        }
        for (float offset : {0.0f,0.2f,-0.2f,0.4f,-0.4f})
        {
            plan.destination={healer->GetPositionX()+std::cos(angle+offset)*distance,
                healer->GetPositionY()+std::sin(angle+offset)*distance,healer->GetPositionZ()};
            if (ValidateEncounterDestination(ai,plan)) return true;
        }
        plan.active=false;return false;
    }
    if (!ai->IsTank(bot)) return false;
    Unit* assigned=MoltenCoreAssignedTankTarget(ai);
    if (!assigned && RaidAdds(ai,boss,11664).empty())
    {
        Unit* focus=MajordomoFocus(ai,boss);
        Player* pickup=nullptr;
        for (GroupReference* ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next())
        {
            Player* tank=ref->getSource();
            if (RaidMember(bot,tank) && ai->IsTank(tank) && tank!=boss->GetVictim() &&
                (!pickup || tank->GetObjectGuid()<pickup->GetObjectGuid())) pickup=tank;
        }
        if (pickup!=bot || !focus || !PossibleAttackTargetsValue::HasBreakableCC(focus,bot)) return false;
        const float angle=focus->GetAngle(bot);
        plan.active=true;plan.map=bot->GetMapId();plan.instance=bot->GetInstanceId();plan.boss=boss->GetObjectGuid();plan.spell=19771;
        plan.destination={focus->GetPositionX()+std::cos(angle)*4,focus->GetPositionY()+std::sin(angle)*4,focus->GetPositionZ()};
        if (ValidateEncounterDestination(ai,plan)) return true;
        plan.active=false;return false;
    }
    if (!assigned || assigned==boss || assigned->GetVictim()!=bot) return false;
    auto healers=RaidAdds(ai,boss,11663);
    if (healers.empty()) return false;
    const float base=boss->GetVictim()?boss->GetAngle(boss->GetVictim()):boss->GetOrientation();
    // Park controlled adds away from the sheep. Native terrain/path/hazard
    // admission chooses a legal station; keep the entire fight inside 100yd.
    plan.active=true;plan.map=bot->GetMapId();plan.instance=bot->GetInstanceId();plan.boss=boss->GetObjectGuid();plan.spell=19771;
    for (float distance : {24.0f,32.0f,40.0f})
        for (float offset : {0.0f,0.6f,-0.6f,1.2f,-1.2f,1.8f,-1.8f,2.4f,-2.4f,3.14f})
        {
            plan.destination={boss->GetPositionX()+std::cos(base+offset)*distance,
                boss->GetPositionY()+std::sin(base+offset)*distance,boss->GetPositionZ()};
            bool safe=true;
            for (Unit* healer : healers)
                if (healer!=assigned && !healer->HasAura(21087) &&
                    std::hypot(plan.destination.x-healer->GetPositionX(),plan.destination.y-healer->GetPositionY())<
                    15+assigned->GetCombatReach()+healer->GetCombatReach()+bot->GetCombatReach()) {safe=false;break;}
            if (safe && ValidateEncounterDestination(ai,plan)) return true;
        }
    plan.active=false;return false;
}

Unit* ai::MoltenCoreRagnaros(PlayerbotAI* ai)
{
    Player* bot=ai->GetBot();
    if (!bot || !bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId()!=409 || !bot->IsInCombat() || !bot->GetGroup() || ai->IsRealPlayer()) return nullptr;
    // Attackable target values omit submerged Ragnaros. Native grid lookup
    // preserves phase awareness without targeting an immune creature.
    std::list<Unit*> nearby;
    MaNGOS::AllCreaturesOfEntryInRangeCheck check(bot,11502,120.0f);
    MaNGOS::UnitListSearcher<MaNGOS::AllCreaturesOfEntryInRangeCheck> searcher(nearby,check);
    Cell::VisitAllObjects(bot,searcher,120.0f);
    for (Unit* boss : nearby) if (RaidEnemy(bot,boss)) return boss;
    return nullptr;
}

namespace
{
    std::vector<Player*> RagnarosRanged(PlayerbotAI* ai)
    {
        Player* bot=ai->GetBot(); std::vector<Player*> result;
        if (!bot->GetGroup()) return result;
        for (GroupReference* ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next())
        {
            Player* member=ref->getSource();
            if (RaidMember(bot,member) && !ai->IsTank(member) && (ai->IsRanged(member)||ai->IsHeal(member))) result.push_back(member);
        }
        std::sort(result.begin(),result.end(),[ai](Player* a,Player* b){
            if (ai->IsHeal(a)!=ai->IsHeal(b)) return ai->IsHeal(a);
            return a->GetObjectGuid()<b->GetObjectGuid();
        });
        return result;
    }

    const char* RagnarosRangeSpell(PlayerbotAI* ai, Player* member)
    {
        if (ai->IsHeal(member)) return member->getClass()==CLASS_PALADIN?"flash of light":
            member->getClass()==CLASS_SHAMAN?"healing wave":member->getClass()==CLASS_DRUID?"healing touch":"flash heal";
        switch (member->getClass())
        {
            case CLASS_HUNTER:return "auto shot";
            case CLASS_WARLOCK:return "shadow bolt";
            case CLASS_PRIEST:return "mind blast";
            case CLASS_SHAMAN:return "lightning bolt";
            case CLASS_DRUID:return "wrath";
            default:return "frostbolt"; // Fire-immune boss; use the learned frost option.
        }
    }
}

bool ai::RagnarosSameCluster(PlayerbotAI* ai, Player* member)
{
    auto members=RagnarosRanged(ai);
    auto own=std::find(members.begin(),members.end(),ai->GetBot()),other=std::find(members.begin(),members.end(),member);
    return own!=members.end() && other!=members.end() && std::distance(members.begin(),own)/3==std::distance(members.begin(),other)/3;
}

bool ai::PlanRagnarosFormation(PlayerbotAI* ai, EncounterPosition& plan)
{
    Unit* boss=MoltenCoreRagnaros(ai); if (!boss) return false;
    Player* bot=ai->GetBot(); std::vector<Player*> tanks;
    for (GroupReference* ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next())
    {
        Player* member=ref->getSource();
        if (RaidMember(bot,member) && ai->IsTank(member) && member->GetDistance(boss)<=120) tanks.push_back(member);
    }
    if (tanks.empty()) return false;
    std::sort(tanks.begin(),tanks.end(),[](Player*a,Player*b){return a->GetObjectGuid()<b->GetObjectGuid();});
    PreserveMoltenCoreTank(ai,boss,tanks);
    Player* tank=tanks.front();
    auto* saved=ai->GetAiObjectContext()->GetValue<GeddonControl>("ragnaros control");
    auto state=saved->Get();
    if (state.boss!=boss->GetObjectGuid() || state.tank!=tank->GetObjectGuid())
    {
        state.boss=boss->GetObjectGuid();state.tank=tank->GetObjectGuid();
        const float angle=boss->GetAngle(tank);
        const float reach=std::max(2.0f,boss->GetCombatReach()+tank->GetCombatReach()-1);
        state.tankPosition={boss->GetPositionX()+std::cos(angle)*reach,boss->GetPositionY()+std::sin(angle)*reach,boss->GetPositionZ()};
        saved->Set(state);
    }
    const float base=std::atan2(state.tankPosition.y-boss->GetPositionY(),state.tankPosition.x-boss->GetPositionX());
    const bool submerged=boss->HasAura(21107)||boss->HasAura(21859)||boss->HasAura(20567);
    float angle=base,distance=std::max(2.0f,boss->GetCombatReach()+bot->GetCombatReach()-1);
    auto ranged=RagnarosRanged(ai);
    auto own=std::find(ranged.begin(),ranged.end(),bot);
    size_t slot=own==ranged.end()?0:std::distance(ranged.begin(),own);
    if (submerged)
    {
        angle=base+float(M_PI);
        // Tanks gather Sons at the established tank station. Mana users stay
        // behind them rather than stacking inside the Sons' mana-burn aura.
        distance=(own!=ranged.end()?15.0f:3.0f);
        if (ai->IsTank(bot) && bot==tank) {plan.destination=state.tankPosition;}
        else {plan.destination={state.tankPosition.x+std::cos(angle)*distance,state.tankPosition.y+std::sin(angle)*distance,state.tankPosition.z};}
    }
    else if (own!=ranged.end())
    {
        float range=0;
        if (!ai->GetSpellRange(RagnarosRangeSpell(ai,bot),&range) || range<=5) return false;
        distance=range+boss->GetCombatReach()+bot->GetCombatReach()-3;
        // All members of a triple use its shortest learned cast/heal range.
        // Healing needs reach to the actual tank, not merely to the boss.
        for (size_t i=slot/3*3;i<std::min(ranged.size(),slot/3*3+3);++i)
        {
            Player* member=ranged[i];PlayerbotAI* brain=member->GetPlayerbotAI();float memberRange=0;
            if (brain && !brain->IsRealPlayer() && brain->GetSpellRange(RagnarosRangeSpell(ai,member),&memberRange) && memberRange>5)
                distance=std::min(distance,memberRange+boss->GetCombatReach()+member->GetCombatReach()-3);
        }
        const size_t groups=(ranged.size()+2)/3;
        const size_t station=slot/3;
        const float lane=station==0?0.0f:(station%2?1.0f:-1.0f)*float((station+1)/2);
        angle=base+lane/float(groups)*2*float(M_PI); // healer triples nearest the tank
        for (size_t i=slot/3*3;i<std::min(ranged.size(),slot/3*3+3);++i)
        {
            Player* member=ranged[i];PlayerbotAI* brain=member->GetPlayerbotAI();float healRange=0;
            if (!brain || !ai->IsHeal(member) || !brain->GetSpellRange(RagnarosRangeSpell(ai,member),&healRange)) continue;
            const float dx=tank->GetPositionX()-boss->GetPositionX(),dy=tank->GetPositionY()-boss->GetPositionY();
            const float projection=dx*std::cos(angle)+dy*std::sin(angle);
            const float legal=healRange+tank->GetCombatReach()+member->GetCombatReach()-3;
            const float remainder=legal*legal-(dx*dx+dy*dy-projection*projection);
            if (remainder<0) return false;
            distance=std::min(distance,projection+std::sqrt(remainder));
        }
        if (distance<NativeEncounterSpellRadius(20566)+3) return false;
        const float spread=NativeEncounterSpellRadius(21155)+4;
        if (groups>1 && 2*distance*std::sin(float(M_PI)/float(groups))<spread) return false;
        const float offset=(float(slot%3)-1)*0.8f;
        plan.destination={boss->GetPositionX()+std::cos(angle)*distance-std::sin(angle)*offset,
            boss->GetPositionY()+std::sin(angle)*distance+std::cos(angle)*offset,boss->GetPositionZ()};
        for (size_t i=slot/3*3;i<std::min(ranged.size(),slot/3*3+3);++i)
        {
            Player* member=ranged[i];PlayerbotAI* brain=member->GetPlayerbotAI();float healRange=0;
            if (brain && ai->IsHeal(member) && brain->GetSpellRange(RagnarosRangeSpell(ai,member),&healRange))
                if (std::hypot(plan.destination.x-tank->GetPositionX(),plan.destination.y-tank->GetPositionY())>
                    healRange+tank->GetCombatReach()+member->GetCombatReach()-2) return false;
        }
        for (Player* member : ranged)
            if (!RagnarosSameCluster(ai,member) && std::hypot(plan.destination.x-member->GetPositionX(),plan.destination.y-member->GetPositionY())<spread-2) return false;
    }
    else
    {
        // A spare tank can still attack. Only the actual boss holder uses the
        // tank lane; every other melee bot returns to the rear attack station.
        // The live Wrath cast escape above temporarily overrides this station.
        if (boss->GetVictim()!=bot) angle+=float(M_PI);
        plan.destination={boss->GetPositionX()+std::cos(angle)*distance,boss->GetPositionY()+std::sin(angle)*distance,boss->GetPositionZ()};
    }
    plan.active=true;plan.map=bot->GetMapId();plan.instance=bot->GetInstanceId();plan.boss=boss->GetObjectGuid();plan.spell=21155;
    const auto proposed=plan.destination;
    EncounterPosition landing; bool hasLanding=false;
    const bool meleeRecovery = !submerged && own == ranged.end() && boss->GetVictim() != bot;
    const std::vector<float> offsets = meleeRecovery ?
        std::vector<float>{0.0f,0.15f,-0.15f,0.30f,-0.30f,0.60f,-0.60f,0.90f,-0.90f} :
        std::vector<float>{0.0f,0.025f,-0.025f,0.05f,-0.05f};
    for (float offset : offsets)
    {
        plan.destination=proposed;
        if (offset)
        {
            const float dx=proposed.x-boss->GetPositionX(),dy=proposed.y-boss->GetPositionY();
            plan.destination.x=boss->GetPositionX()+dx*std::cos(offset)-dy*std::sin(offset);
            plan.destination.y=boss->GetPositionY()+dx*std::sin(offset)+dy*std::cos(offset);
        }
        const auto unadjusted=plan.destination;
        if (ValidateEncounterDestination(ai,plan)) return true;
        // Validation projects to the native floor. Restore the unadjusted
        // candidate before retrying, so a failed height check cannot admit it.
        plan.destination=unadjusted;
        if (!hasLanding && !submerged && own==ranged.end() && ValidateEncounterDestination(ai,plan,false))
        {landing=plan;hasLanding=true;}
    }
    // Only the separate trajectory solver can use an endpoint without a walk.
    if (hasLanding) {plan=landing;return true;}
    plan.active=false;return false;
}
