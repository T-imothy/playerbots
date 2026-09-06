
#include "playerbot/playerbot.h"
#include "NaxxramasDungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

bool NaxxramasPositionAction::GetPlan(PlayerbotAI* ai, EncounterPosition& plan)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->GetMapId() != 533 || !bot->GetGroup()) return false;
    plan = ai->GetAiObjectContext()->GetValue<EncounterPosition>("naxxramas position")->Get();
    if (!plan.active || plan.map != bot->GetMapId() || plan.instance != bot->GetInstanceId() ||
        (plan.spell != 28169 && plan.spell != 27819 && plan.spell != 28059 && plan.spell != 28084)) return false;
    Unit* carrier = plan.source == bot->GetObjectGuid() ? bot : ai->GetUnit(plan.source);
    if (!carrier || !carrier->IsPlayer() || !carrier->IsInWorld() || !carrier->IsAlive() ||
        !bot->IsInMap(carrier) || !carrier->HasAura(plan.spell) || carrier->HasCharmer()) return false;
    Player* player = static_cast<Player*>(carrier);
    if (player->IsBeingTeleported() || player->GetGroup() != bot->GetGroup()) return false;
    if (carrier != bot && (plan.spell == 28059 || plan.spell == 28084) && bot->HasAura(plan.spell)) return false;
    // Revalidate tank ownership before allowing an old safe-position hold to
    // interfere with a newly acquired native boss victim.
    for (const auto& guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("attackers")->Get())
    {
        Unit* enemy = ai->GetUnit(guid);
        if (enemy && enemy->IsInWorld() && bot->IsInMap(enemy) && enemy->IsAlive() &&
            enemy->IsInCombat() && (enemy->GetEntry() == 15931 || enemy->GetEntry() == 15990 ||
                enemy->GetEntry() == 15928) &&
            enemy->GetVictim() == bot) return false;
    }
    return true;
}

bool NaxxramasPositionAction::isUseful()
{
    EncounterPosition plan;
    return GetPlan(ai, plan) && bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.5f;
}

bool NaxxramasPositionAction::Execute(Event& event)
{
    EncounterPosition plan, current;
    std::vector<encounter::Circle> threats;
    if (!GetPlan(ai, plan) || !ai->CanMove() || !NaxxramasBurstThreats(ai, current, threats) ||
        !ValidateEncounterDestination(ai, plan) || !encounter::OutsideCircles(plan.destination, threats)) return false;
    return MoveTo(plan.map, plan.destination.x, plan.destination.y, plan.destination.z, false, IsReaction(), false, true);
}
