#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleTargetsValue.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"
#include "Spells/SpellAuras.h"

using namespace ai;

Unit* InnerDemonAction::GetDemon(PlayerbotAI* ai)
{
#ifndef MANGOSBOT_ZERO
    Player* bot = ai->GetBot();
    if (bot->GetMapId() != 548 || !bot->GetGroup() || !bot->IsInWorld() || !bot->IsAlive() ||
        !bot->IsInCombat() || bot->HasCharmer() || bot->IsBeingTeleported() || ai->IsRealPlayer()) return nullptr;
    SpellAuraHolder* whisper = bot->GetSpellAuraHolder(37676);
    Unit* boss = whisper ? whisper->GetCaster() : nullptr;
    if (!boss || boss->GetEntry() != 21215 || !boss->IsInWorld() || !boss->IsAlive() ||
        !boss->IsInCombat() || boss->HasCharmer() || !bot->IsInMap(boss)) return nullptr;
    // Explicit attack orders still take precedence over autonomous mechanics.
    auto commanded = [bot](Unit* unit) {
        return unit && unit->IsInWorld() && unit->IsAlive() && bot->IsInMap(unit) && !unit->HasCharmer() &&
            !sServerFacade.IsFriendlyTo(unit, bot) && bot->GetDistance(unit) <= sPlayerbotAIConfig.sightDistance;
    };
    if (commanded(ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("attack target")->Get())) ||
        commanded(ai->GetAiObjectContext()->GetValue<Unit*>("rti target")->Get())) return nullptr;

    Unit* selected = nullptr;
    for (const auto& guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets", "100:1")->Get())
    {
        Unit* demon = ai->GetUnit(guid);
        if (!demon || demon->GetEntry() != 21857 || !demon->IsInWorld() || !demon->IsAlive() ||
            !bot->IsInMap(demon) || demon->HasCharmer() || demon->GetSpawnerGuid() != bot->GetObjectGuid() ||
            demon->GetUInt32Value(UNIT_CREATED_BY_SPELL) != 37735 || demon->GetVictim() != bot ||
            !PossibleTargetsValue::IsValid(demon, bot, false) ||
            !PossibleAttackTargetsValue::IsPossibleTarget(demon, bot, sPlayerbotAIConfig.sightDistance, false) ||
            PossibleAttackTargetsValue::HasBreakableCC(demon, bot) ||
            PossibleAttackTargetsValue::HasUnBreakableCC(demon, bot)) continue;
        if (selected && selected != demon) return nullptr;
        selected = demon;
    }
    return selected;
#else
    return nullptr;
#endif
}

InnerDemonAction::InnerDemonAction(PlayerbotAI* ai) : CastSpellAction(ai,
    ai->GetBot()->getClass() == CLASS_PRIEST ? "smite" :
    ai->GetBot()->getClass() == CLASS_DRUID ? "wrath" :
    ai->GetBot()->getClass() == CLASS_SHAMAN ? "lightning bolt" :
    ai->GetBot()->getClass() == CLASS_PALADIN ? "exorcism" : "")
{
}

Unit* InnerDemonAction::GetTarget()
{
    return GetDemon(ai);
}

bool InnerDemonAction::isUseful()
{
    return !GetSpellName().empty() && ai->IsHeal(bot) && GetDemon(ai) && CastSpellAction::isUseful();
}

bool InnerDemonAction::Execute(Event& event)
{
    // Keep native learned-rank, mana, form, range and cooldown checks. Never
    // grant an offensive spell or fake the player's required killing blow.
    return isUseful() && CastSpellAction::Execute(event);
}
