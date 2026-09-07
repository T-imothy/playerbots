#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;

bool ai::IsHakkarPoisonSource(Player* bot, Unit* son)
{
    if (!son || !son->IsInWorld() || !son->IsAlive() || !son->IsInCombat() || !bot->IsInMap(son) ||
        son->HasCharmer() || son->GetEntry() != 11357 || !bot->GetGroup()) return false;
    Unit* victim = son->GetVictim();
    return victim && victim->IsPlayer() && victim->IsInWorld() && victim->IsAlive() &&
        bot->IsInMap(victim) && !victim->HasCharmer() &&
        static_cast<Player*>(victim)->GetGroup() == bot->GetGroup() &&
        !static_cast<Player*>(victim)->IsBeingTeleported();
}

EncounterPosition HakkarPositionValue::Calculate()
{
    EncounterPosition plan;
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || bot->GetMapId() != 309 ||
        !bot->GetGroup() || bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer() || !ai->CanMove())
    { preparationSon = ObjectGuid(); return plan; }
    bool needsPoison = !bot->HasAura(24321);
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref && !needsPoison; ref = ref->next())
    {
        Player* member = ref->getSource();
        needsPoison = member && member->IsInWorld() && member->IsAlive() && bot->IsInMap(member) &&
            member->GetGroup() == bot->GetGroup() && !member->IsBeingTeleported() && !member->HasCharmer() && !member->HasAura(24321);
    }
    if (!needsPoison) { preparationSon = ObjectGuid(); return plan; }
    Unit* boss = nullptr;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "attackers"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit || !unit->IsInWorld() || !unit->IsAlive() || !unit->IsInCombat() ||
            unit->HasCharmer() || !bot->IsInMap(unit) || unit->GetEntry() != 14834) continue;
        if (boss && boss != unit) return plan;
        boss = unit;
    }
    if (!boss) { preparationSon = ObjectGuid(); return plan; }
    const float radius = NativeEncounterSpellRadius(24320);
    if (!std::isfinite(radius) || radius <= 2 || radius > 20) return plan;
    std::list<Unit*> sons;
    MaNGOS::AllCreaturesOfEntryInRangeCheck check(boss, 11357, 60.0f);
    MaNGOS::UnitListSearcher<decltype(check)> searcher(sons, check);
    Cell::VisitAllObjects(boss, searcher, 60.0f);
    Unit* son = nullptr;
    for (Unit* candidate : sons)
        if (IsHakkarPoisonSource(bot, candidate) && std::fabs(candidate->GetPositionZ() - boss->GetPositionZ()) <= 8 &&
            (!son || boss->GetDistance(candidate) < boss->GetDistance(son) ||
                (boss->GetDistance(candidate) == boss->GetDistance(son) && candidate->GetObjectGuid() < son->GetObjectGuid()))) son = candidate;
    if (!son) { preparationSon = ObjectGuid(); return plan; }
    if (preparationSon != son->GetObjectGuid())
    {
        preparationSon = son->GetObjectGuid();
        preparationStarted = 0;
    }
    if (son->GetHealthPercent() <= 40 && !preparationStarted) preparationStarted = time(0);
    // Poisonous Cloud casts only ON SPAWN in native EventAI. Position before
    // the Son dies; walking into the lingering visual cannot apply poison.
    const bool inside = bot->GetDistance(son) <= radius - 2;
    if (boss->GetVictim() == bot && !inside) return plan;
    plan.active = true; plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
    plan.boss = boss->GetObjectGuid(); plan.source = son->GetObjectGuid(); plan.spell = 24321;
    const time_t now = time(0);
    plan.exclusive = preparationStarted && now >= preparationStarted && now - preparationStarted < 10;
    plan.destination = inside || bot->HasAura(24321) ? encounter::Point{bot->GetPositionX(), bot->GetPositionY(), bot->GetPositionZ()} :
        encounter::Point{son->GetPositionX(), son->GetPositionY(), son->GetPositionZ()};
    plan.active = ValidateEncounterDestination(ai, plan);
    return plan;
}

bool ai::HasHakkarPoisonPreparation(Player* bot)
{
    if (!bot || !bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || bot->GetMapId() != 309 ||
        !bot->GetGroup() || bot->HasCharmer() || bot->IsBeingTeleported() || !bot->GetPlayerbotAI() ||
        bot->GetPlayerbotAI()->IsRealPlayer()) return false;
    PlayerbotAI* ai = bot->GetPlayerbotAI();
    const EncounterPosition plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("hakkar poison position")->Get();
    if (!plan.active || !plan.exclusive || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId()) return false;
    Unit* son = ai->GetUnit(plan.source);
    Unit* boss = ai->GetUnit(plan.boss);
    if (!IsHakkarPoisonSource(bot, son) || son->GetHealthPercent() > 40 || !boss || !boss->IsInWorld() ||
        !boss->IsAlive() || !boss->IsInCombat() || !bot->IsInMap(boss) || boss->GetEntry() != 14834 || boss->GetVictim() == bot) return false;
    const float radius = NativeEncounterSpellRadius(24320);
    if (!std::isfinite(radius) || radius <= 2 || radius > 20) return false;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (member && member != boss->GetVictim() && member->IsInWorld() && member->IsAlive() && bot->IsInMap(member) &&
            member->GetGroup() == bot->GetGroup() && !member->IsBeingTeleported() && !member->HasCharmer() &&
            !member->HasAura(24321) && member->GetDistance(son) > radius - 1 && member->GetDistance(son) <= 40 &&
            member->GetPlayerbotAI() && !member->GetPlayerbotAI()->IsRealPlayer() && member->GetPlayerbotAI()->CanMove() &&
            member->GetPlayerbotAI()->HasStrategy("dungeon", BotState::BOT_STATE_COMBAT)) return true;
    }
    return false;
}
