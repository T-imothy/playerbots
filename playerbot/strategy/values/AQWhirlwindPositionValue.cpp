#include "playerbot/playerbot.h"
#include "EncounterPositionValue.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

bool ai::AQWhirlwindThreats(PlayerbotAI* ai, EncounterPosition& plan, std::vector<encounter::Circle>& threats)
{
    Player* bot = ai->GetBot();
    plan = EncounterPosition();
    threats.clear();
    if (bot->GetMapId() != 531 || !bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() ||
        bot->HasCharmer() || bot->IsBeingTeleported()) return false;
    for (const auto& guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("attackers")->Get())
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit || !unit->IsInWorld() || !unit->IsAlive() || !unit->IsInCombat() || unit->HasCharmer() ||
            !bot->IsInMap(unit) || bot->GetDistance(unit) > 100 ||
            std::fabs(unit->GetPositionZ() - bot->GetPositionZ()) > 8) continue;
        uint32 aura = CurrentBossEscapeSpell(bot, unit);
        uint32 damage = NativeBossEscapeSpell(531, unit->GetEntry(), aura);
        if (!damage) continue;
        const float radius = NativeEncounterSpellRadius(damage);
        if (!std::isfinite(radius) || radius <= 0 || radius > 35) continue;
        threats.push_back({{unit->GetPositionX(), unit->GetPositionY(), unit->GetPositionZ()}, radius + 2});
        if (!plan.active || unit->GetObjectGuid() < plan.boss)
        {
            plan.active = true;
            plan.map = bot->GetMapId(); plan.instance = bot->GetInstanceId();
            plan.boss = unit->GetObjectGuid(); plan.spell = aura;
        }
    }
    return plan.active;
}
