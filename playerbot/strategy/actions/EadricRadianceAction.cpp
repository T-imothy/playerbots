#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

Unit* EadricRadianceAction::GetBoss(PlayerbotAI* ai)
{
#ifdef MANGOSBOT_TWO
    Player* bot = ai->GetBot();
    if (bot->GetMapId() != 650 || !bot->GetGroup() || !bot->IsInWorld() || !bot->IsAlive() ||
        !bot->IsInCombat() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        !ai->HasStrategy("dungeon", BotState::BOT_STATE_COMBAT)) return nullptr;
    for (const auto& guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets", "100:1")->Get())
    {
        Unit* boss = ai->GetUnit(guid);
        if (!boss || boss->GetEntry() != 35119 || !boss->IsInWorld() || !boss->IsAlive() ||
            !boss->IsInCombat() || boss->HasCharmer() || !bot->IsInMap(boss) || bot->GetDistance(boss) > 40) continue;
        const Spell* cast = boss->GetCurrentSpell(CURRENT_GENERIC_SPELL);
        if (cast && cast->m_spellInfo && cast->m_spellInfo->Id == 66935 &&
            cast->getState() != SPELL_STATE_FINISHED && cast->getState() != SPELL_STATE_DELAYED)
            return boss;
    }
#endif
    return nullptr;
}

bool EadricRadianceAction::isUseful()
{
    Unit* boss = GetBoss(ai);
    return boss && (bot->HasInArc(boss, 2.5f) || !bot->IsStopped() ||
        bot->GetMotionMaster()->GetCurrentMovementGeneratorType() != IDLE_MOTION_TYPE);
}

bool EadricRadianceAction::ShouldReactionInterruptCast() const
{
    Unit* boss = GetBoss(ai);
    return boss && bot->HasInArc(boss, 2.5f);
}

bool EadricRadianceAction::Execute(Event&)
{
    Unit* boss = GetBoss(ai);
    if (!boss || !ai->CanMove()) return false;
    const bool turn = bot->HasInArc(boss, 2.5f);
    ai->StopMoving();
    if (turn)
    {
        ai->InterruptSpell();
        sServerFacade.SetFacingTo(bot, bot->GetAngle(boss) + M_PI_F, true);
    }
    SetDuration(100);
    return true;
}
