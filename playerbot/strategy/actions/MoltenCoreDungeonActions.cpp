
#include "playerbot/playerbot.h"
#include "playerbot/strategy/MoltenCoreTrashPolicy.h"
#include "MoltenCoreDungeonActions.h"
#include "MoltenCoreGarrActions.h"
#include "playerbot/strategy/values/GeddonControlValue.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"
#include "playerbot/ServerFacade.h"
#include "Movement/MoveSpline.h"
#include "playerbot/strategy/mage/MageCombatPolicy.h"
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
                (group ? static_cast<Creature*>(unit)->GetCreatureGroup() != group : unit->GetDistance(anchor) > 30);
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
    return !pack.empty() && pack.front()->GetEntry()==11671 && !MoltenCorePackTanks(ai,pack).empty();
}

Unit* ai::MoltenCorePackTankTarget(PlayerbotAI* ai)
{
    auto pack = MoltenCorePack(ai);
    auto tanks = MoltenCorePackTanks(ai, pack);
    auto own = std::find(tanks.begin(), tanks.end(), ai->GetBot());
    if (pack.empty() || (pack.size()<2 && pack.front()->GetEntry()!=11669) || own == tanks.end()) return nullptr;
    const size_t slot = std::distance(tanks.begin(), own);
    Unit* held = nullptr;
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
        if (!tankHeld) return enemy;
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
                plan.destination={tank->GetPositionX(),tank->GetPositionY(),tank->GetPositionZ()};
                if (ValidateEncounterDestination(ai,plan)) return true;
                plan.active=false;return false;
            }
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
        // Five-pack hounds have Serrated Bite, not the patrol's stomp/breath.
        // The entire group stacks at the holding tank so melee AoE and equal
        // health targeting work on the same controlled cluster.
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
            const float distance = std::max(10.0f, NativeEncounterSpellRadius(20602) + 2);
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

bool ai::MoltenCoreImpPack(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 409 || !bot->IsInCombat() || !bot->GetGroup() || ai->IsRealPlayer() || ai->IsHeal(bot)) return false;
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
    return imps >= 3 && held > 0 && ai->GetCombatStartTime() && time(0) - ai->GetCombatStartTime() >= 10;
}

namespace
{
    bool PlanMagmadarFormation(PlayerbotAI* ai, Unit* boss, EncounterPosition& plan)
    {
        Player* bot = ai->GetBot();
        if (boss->GetVictim() == bot) return false;
        const bool healer = ai->IsHeal(bot);
        const bool ranged = ai->IsRanged(bot) || healer;
        std::vector<Player*> members;
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (!member || !member->IsInWorld() || !member->IsAlive() || member->HasCharmer() ||
                member->IsBeingTeleported() || !bot->IsInMap(member) || member==boss->GetVictim() ||
                member->GetDistance(boss) > 100 || (ai->IsRanged(member) || ai->IsHeal(member)) != ranged ||
                (ranged && ai->IsHeal(member) != healer)) continue;
            members.push_back(member);
        }
        std::sort(members.begin(), members.end(), [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        auto own = std::find(members.begin(), members.end(), bot);
        if (own == members.end()) return false;
        const size_t slot = std::distance(members.begin(), own);
        float distance = std::max(2.0f, boss->GetCombatReach() + bot->GetCombatReach() - 1.0f);
        float angle = boss->GetOrientation() + float(M_PI);
        Unit* healingTarget = nullptr;
        Unit* wardTarget = nullptr;
        float healingRange = 0, wardRange = 0;
        if (ranged)
        {
            const char* spell = "frostbolt";
            if (healer)
            {
                switch (bot->getClass())
                {
                    case CLASS_PRIEST: spell = "flash heal"; break;
                    case CLASS_PALADIN: spell = "flash of light"; break;
                    case CLASS_SHAMAN: spell = "healing wave"; break;
                    case CLASS_DRUID: spell = "healing touch"; break;
                    default: break;
                }
            }
            else switch (bot->getClass())
            {
                case CLASS_HUNTER: spell = "auto shot"; break;
                case CLASS_WARLOCK: spell = "shadow bolt"; break;
                case CLASS_PRIEST: spell = "mind blast"; break;
                case CLASS_DRUID: spell = "wrath"; break;
                case CLASS_SHAMAN: spell = "lightning bolt"; break;
                case CLASS_MAGE:
                    spell = MagePrimaryDamageSpell(ai);
                    break;
                default: break;
            }
            Unit* victim = boss->GetVictim();
            if (healer && victim && victim->IsPlayer()) healingTarget = victim;
            float spellRange = ai->GetRange("spell"); ai->GetSpellRange(spell, &spellRange);
            Unit* rangeTarget = healingTarget ? healingTarget : boss;
            // Match native ranged admission, including learned-rank/talent
            // range and both combat reaches; retain two yards of margin.
            distance = std::max(10.0f, spellRange + bot->GetCombatReach() + rangeTarget->GetCombatReach() - 2);
            if (healingTarget) healingRange = distance;
            if (victim && victim->IsPlayer() && !ai->HasAura("fear ward", victim) &&
                ai->CanCastSpell("fear ward", victim, 0, nullptr, true) && ai->GetSpellRange("fear ward", &wardRange))
            {
                wardTarget = victim;
                wardRange += bot->GetCombatReach() + victim->GetCombatReach() - 2;
            }
            if (healingTarget)
            {
                // Distinct side slots retain range to the actual tank. They
                // do not crowd all healers onto one of two identical points.
                const size_t lanes = (members.size()+1)/2;
                const float step = lanes > 1 ? std::min(float(M_PI)/9, float(M_PI)/3/float(lanes-1)) : 0;
                angle = boss->GetAngle(healingTarget) + (slot % 2 ? 1.0f : -1.0f) *
                    (float(M_PI)*5/12 + float(slot/2)*step);
            }
            else angle += (members.size()>1 ? float(slot)/float(members.size()-1)-0.5f : 0) * float(M_PI)*2/3;
        }
        else angle += (float(slot % 3)-1)*float(M_PI)/3; // rear-left, rear, rear-right
        for (float offset : {0.0f,0.12f,-0.12f,0.24f,-0.24f,0.36f,-0.36f})
        {
            const float candidateAngle = angle+offset;
            if (std::cos(candidateAngle-boss->GetOrientation()) > 0.0f) continue;
            float candidateDistance = distance;
            const auto withinFriendlyRange = [&](Unit* target, float maximum) {
                if (!target) return true;
                const float x=target->GetPositionX()-boss->GetPositionX();
                const float y=target->GetPositionY()-boss->GetPositionY();
                const float projection=x*std::cos(candidateAngle)+y*std::sin(candidateAngle);
                const float remainder=maximum*maximum-(x*x+y*y-projection*projection);
                if (remainder<0) return false;
                const float outer=projection+std::sqrt(remainder);
                if (outer<10) return false;
                candidateDistance=std::min(candidateDistance,outer);
                return true;
            };
            if (!withinFriendlyRange(healingTarget,healingRange) || !withinFriendlyRange(wardTarget,wardRange)) continue;
            plan.destination={boss->GetPositionX()+std::cos(candidateAngle)*candidateDistance,
                boss->GetPositionY()+std::sin(candidateAngle)*candidateDistance,boss->GetPositionZ()};
            if (ValidateEncounterDestination(ai,plan)) return true;
        }
        plan.active=false;
        return false;
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
        const char* spell = ai->IsHeal(bot) ?
            (bot->getClass()==CLASS_PALADIN?"flash of light":bot->getClass()==CLASS_SHAMAN?"healing wave":
             bot->getClass()==CLASS_DRUID?"healing touch":"flash heal") :
            (bot->getClass()==CLASS_HUNTER?"arcane shot":bot->getClass()==CLASS_WARLOCK?"shadow bolt":
             bot->getClass()==CLASS_PRIEST?"mind blast":bot->getClass()==CLASS_SHAMAN?"lightning bolt":
             bot->getClass()==CLASS_DRUID?"wrath":"fireball");
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
        bot->GetMapId() != 409 || !bot->IsInCombat() || !bot->GetGroup() || ai->IsRealPlayer()) return false;
    if (PlanGarrPosition(ai, plan)) return true;
    if (PlanRagnarosFormation(ai, plan)) return true;
    if (PlanGolemaggFormation(ai, plan)) return true;
    if (PlanMajordomoFormation(ai, plan)) return true;
    if (PlanMoltenCorePack(ai, plan)) return true;
    Unit* selected = nullptr;
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
             unit->GetEntry() != 11667 && unit->GetEntry() != 11661 && unit->GetEntry() != 12056 && unit->GetEntry() != 11982)) continue;
        Unit* victim = unit->GetVictim();
        if (!victim || !victim->IsPlayer() || !victim->IsAlive() ||
            static_cast<Player*>(victim)->GetGroup() != bot->GetGroup()) continue;
        // Keep the current victim's tank assignment. Choose one stable nearby
        // source; do not alternate between multiple trash mobs every tick.
        if (!selected || (unit->GetVictim() == bot && selected->GetVictim() != bot) ||
            (unit->GetVictim() != bot && selected->GetVictim() != bot &&
             unit->GetObjectGuid() < selected->GetObjectGuid())) selected = unit;
    }
    if (!selected) return false;
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
    plan.active = true; plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    plan.boss = selected->GetObjectGuid();
    if (selected->GetEntry() == 12056) return PlanGeddonFormation(ai,selected,plan);
    if (selected->GetEntry() == 11982 && victim != bot)
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
        plan.spell = selected->GetEntry() == 11667 || selected->GetEntry() == 11666 || selected->GetEntry() == 11661 ? 19630 : 19272;
        float angle = selected->GetOrientation() + float(M_PI);
        float distance = std::max(2.0f, selected->GetCombatReach() + bot->GetCombatReach() - 1.0f);
        if (victim == bot)
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
        for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
        {
            Unit* unit = ai->GetUnit(guid);
            if (!RaidEnemy(ai->GetBot(), unit) || !MoltenCoreBoss(unit->GetEntry())) continue;
            if (result && result != unit) return nullptr; // Do not invent assignments on multi-boss pulls.
            result = unit;
        }
        return result;
    }

    Unit* MoltenCoreTrashTankTarget(PlayerbotAI* ai)
    {
        Player* bot = ai->GetBot();
        std::vector<Player*> tanks;
        std::vector<Unit*> enemies;
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
            if (RaidMember(bot, ref->getSource()) && ai->IsTank(ref->getSource())) tanks.push_back(ref->getSource());
        std::sort(tanks.begin(), tanks.end(), [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        auto own = std::find(tanks.begin(), tanks.end(), bot);
        if (own == tanks.end()) return nullptr;
        for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
        {
            Unit* enemy = ai->GetUnit(guid);
            if (RaidEnemy(bot, enemy) && !MoltenCoreBoss(enemy->GetEntry()) && enemy->GetDistance(bot) <= 50 &&
                !PossibleAttackTargetsValue::HasBreakableCC(enemy, bot) &&
                !PossibleAttackTargetsValue::HasUnBreakableCC(enemy, bot) && !enemy->HasAura(19951)) enemies.push_back(enemy);
        }
        std::sort(enemies.begin(), enemies.end(), [](Unit* a, Unit* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        Unit* held = nullptr;
        for (size_t i = std::distance(tanks.begin(), own); i < enemies.size(); i += tanks.size())
        {
            Unit* victim = enemies[i]->GetVictim();
            // Raid marks select DPS targets, never ownership of all trash.
            // Recover assigned unheld/pet-held mobs without stealing a tank's mob.
            if (!victim || !victim->IsAlive() || !victim->IsPlayer() ||
                std::find(tanks.begin(), tanks.end(), victim) == tanks.end()) return enemies[i];
            if (victim == bot) held = enemies[i];
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
        auto own=std::find(mages.begin(),mages.end(),bot);
        auto healers=RaidAdds(ai,boss,11663);
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
                const size_t slot=std::distance(mages.begin(),own);
                if (slot<healers.size())
                {
                    Unit* healer=healers[slot];
                    // Native immunity starts at four add deaths. Never remove
                    // it or keep retrying an impossible Polymorph.
                    if ((!elites.empty() || healer!=focus) && healer==MajordomoAssignedHealer(ai,boss) && !healer->HasAura(21087) &&
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
        bot->GetMapId() != 409 || !bot->IsInCombat() || !bot->GetGroup() || ai->IsHeal(bot) || ai->IsTank(bot)) return nullptr;

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
        // Five percentage points of tolerance avoids switching on every hit.
        // Keep damage distributed amongst the highest-health band instead of
        // sending the entire raid onto the same nearly-dead marked hound.
        std::vector<Unit*> band;
        for (Unit* hound : hounds)
            if (hound->GetDistance(anchor) <= 30 && hound->GetHealthPercent() + 5.0f >= highest &&
                (highest<=20.0f || hound->GetHealthPercent()>20.0f)) band.push_back(hound);
        if (band.empty()) return nullptr;
        if (std::find(band.begin(), band.end(), current) != band.end()) return current;
        std::sort(band.begin(), band.end(), [](Unit* a, Unit* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        return band[bot->GetGUIDLow() % band.size()];
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
    if (boss && boss->IsInWorld() && bot->IsInMap(boss) && boss->IsAlive() && boss->IsInCombat() &&
        (boss->GetEntry()==11982 || boss->GetEntry()==11673) && boss->GetVictim()!=bot &&
        (plan.spell==19272 || plan.spell==19364))
    {
        const float station=std::atan2(plan.destination.y-boss->GetPositionY(),plan.destination.x-boss->GetPositionX());
        if (std::cos(station-boss->GetOrientation())>0.0f)
        {
            ai->GetAiObjectContext()->GetValue<EncounterPosition>("molten core position")->Reset();
            return PlanMoltenCoreTrash(ai,plan);
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
    if (bot->GetDistance(plan.destination.x,plan.destination.y,plan.destination.z)>1.5f) return true;
    if (!bot->movespline || bot->movespline->Finalized()) return false;
    // Only stop an actual spline continuing beyond the station. A retained
    // generator or movement flag must not monopolize every reaction frame.
    const auto end=bot->movespline->FinalDestination();
    return std::hypot(end.x-plan.destination.x,end.y-plan.destination.y)>1.5f ||
        std::fabs(end.z-plan.destination.z)>1.5f;
}

bool MoltenCorePositionAction::ShouldReactionInterruptCast() const
{
    EncounterPosition plan;
    return ai->CanMove() && GetPlan(ai, plan) && bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.5f;
}

bool MoltenCorePositionAction::Execute(Event& event)
{
    EncounterPosition plan, current;
    std::vector<encounter::Circle> threats;
    if (!GetPlan(ai, plan) || !ai->CanMove()) return false;
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
    else if (plan.spell == 19196 || plan.spell == 19272 || plan.spell == 19364 || plan.spell == 19630 ||
        plan.spell == 19771 || plan.spell == 20602)
    {
        if (MoltenCoreThreats(ai, current, threats) || !PlanMoltenCoreTrash(ai, current)) return false;
        plan = current;
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
    return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
}

Unit* ai::MoltenCoreAssignedTankTarget(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 409 || !bot->IsInCombat() || !bot->GetGroup() || !ai->IsTank(bot) || ai->IsRealPlayer()) return nullptr;
    // Direct commands remain available for a human-led alternative tactic.
    Unit* commanded=ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("attack target")->Get());
    if (RaidEnemy(bot,commanded) && commanded->GetEntry()!=11671 && commanded->GetEntry()!=11669) return nullptr;
    if (Unit* assigned = GarrTankTarget(ai)) return assigned;
    if (Unit* assigned = MoltenCorePackTankTarget(ai)) return assigned;
    Unit* boss = RaidBoss(ai);
    if (!boss) return MoltenCoreTrashTankTarget(ai);
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
    if (!boss) return false;
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
    if (boss->GetEntry() == 12018 && MajordomoSupport(ai, boss, spell, target)) return true;

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
        if (ai->IsTank(bot) && boss->GetVictim()!=bot && boss->GetVictim() &&
            boss->GetVictim()->IsPlayer() && ai->IsTank(static_cast<Player*>(boss->GetVictim())))
        {
            // Only the holding tank is inside Wrath. Backups remain available
            // outside its native radius instead of being knocked away together.
            distance=std::max(distance,NativeEncounterSpellRadius(20566)+5);
            angle+=(float(bot->GetGUIDLow()%3)-1)*0.15f;
        }
        if (!ai->IsTank(bot)) angle+=float(M_PI); // rear melee station, tank stays anchored
        plan.destination={boss->GetPositionX()+std::cos(angle)*distance,boss->GetPositionY()+std::sin(angle)*distance,boss->GetPositionZ()};
    }
    plan.active=true;plan.map=bot->GetMapId();plan.instance=bot->GetInstanceId();plan.boss=boss->GetObjectGuid();plan.spell=21155;
    const auto proposed=plan.destination;
    EncounterPosition landing; bool hasLanding=false;
    for (float offset : {0.0f,0.025f,-0.025f,0.05f,-0.05f})
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
