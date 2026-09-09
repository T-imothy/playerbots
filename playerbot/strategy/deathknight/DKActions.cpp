#include "playerbot/strategy/MeleeCombatPolicy.h"

#include "playerbot/playerbot.h"
#include "DKActions.h"


using namespace ai;

bool CastPestilenceAction::isUseful()
{
#ifdef MANGOSBOT_TWO
    if (!CastSpellAction::isUseful()) return false;
    Unit* source = GetTarget();
    if (!MeleeCombatTarget(ai, source) || SafeMeleeTargetCount(ai, 10.0f, source) == 0) return false;
    Aura* plague = ai->GetAura(55078, source, true);
    Aura* fever = ai->GetAura(55095, source, true);
    if (!plague && !fever) return false;
    if (bot->HasAura(63334) && ((plague && plague->GetHolder()->GetAuraDuration() < 3000) ||
        (fever && fever->GetHolder()->GetAuraDuration() < 3000))) return true;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "possible attack targets"))
    {
        Unit* target = ai->GetUnit(guid);
        if (!target || target == source || !target->IsInWorld() || target->GetMap() != bot->GetMap() ||
            !target->IsAlive() || source->GetDistance(target) > 10.0f) continue;
        if ((plague && !ai->GetAura(55078, target, true)) || (fever && !ai->GetAura(55095, target, true))) return true;
    }
#endif
    return false;
}

bool CastRaiseDeadAction::isPossible()
{
	if (!CastBuffSpellAction::isPossible())
		return false;
	if (AI_VALUE2(uint32, "item count", "corpse dust") > 0)
		return true;
		
	for (auto guid : AI_VALUE(std::list<ObjectGuid>, "nearest corpses"))
	{
		Creature* creature = ai->GetCreature(guid);

		if (!creature)
			continue;

		if (creature->GetCreatureType() != CREATURE_TYPE_HUMANOID)
			continue;

		if (!bot->isHonorOrXPTarget(creature))
			continue;

		return true;
	}

	for (auto guid : AI_VALUE(std::list<ObjectGuid>, "nearest friendly players"))
	{
		Player* player = dynamic_cast<Player*>(ai->GetUnit(guid));

		if (!player)
			continue;

		if (!player->IsDead())
			continue;

		return true;
	}

	for (auto guid : AI_VALUE(std::list<ObjectGuid>, "enemy player targets"))
	{
		Player* player = dynamic_cast<Player*>(ai->GetUnit(guid));

		if (!player)
			continue;

		if (!player->IsDead())
			continue;

		return true;
	}

	return false;
}

bool RuneforgeAction::Execute(Event& event)
{
    Player* requester = event.getOwner() ? event.getOwner() : GetMaster();
    std::string text = event.getParam();

    uint32 runeforgeSpellId;

    if (text == "?")
    {
        for (auto& runeforgeSpell : AI_VALUE(std::vector<uint32>, "runeforge spells"))
        {
            ai->TellPlayerNoFacing(requester, ChatHelper::formatSpell(runeforgeSpell), PlayerbotSecurityLevel::PLAYERBOT_SECURITY_ALLOW_ALL, false);
        }

        return true;
    }
    else if (!text.empty())
    {
        runeforgeSpellId = chat->parseSpell(text);

        if(!runeforgeSpellId)
        {
            ai->TellPlayerNoFacing(requester, text + " is not a [spelllink].", PlayerbotSecurityLevel::PLAYERBOT_SECURITY_ALLOW_ALL, false);
            return false;
        }

        std::vector<uint32> available = AI_VALUE(std::vector<uint32>, "runeforge spells");

        if(std::find(available.begin(), available.end(), runeforgeSpellId) == available.end())
        {
            ai->TellPlayerNoFacing(requester, text + " is not a known runeforgespell.", PlayerbotSecurityLevel::PLAYERBOT_SECURITY_ALLOW_ALL, false);
            return false;
        }
    }
    else
        runeforgeSpellId = AI_VALUE(uint32, "best runeforge spell");

    if (!runeforgeSpellId || !sServerFacade.LookupSpellInfo(runeforgeSpellId) || !bot->HasSpell(runeforgeSpellId))
        return false;

    WorldPosition botLocation(bot);
    GameObject* runeforge = nullptr;
    float closestDistance = FLT_MAX;

    std::list<ObjectGuid> possibleObjects = bot->GetMap()->IsDungeon() ? AI_VALUE(std::list<ObjectGuid>, "nearest game objects") : AI_VALUE(std::list<ObjectGuid>, "nearest game objects no los");

    for (auto& guid : possibleObjects)
    {
        if (std::find(RUNEFORGES.begin(), RUNEFORGES.end(), guid.GetEntry()) == RUNEFORGES.end())
            continue;

        GuidPosition guidP(guid, bot->GetMapId(), bot->GetInstanceId());

        float dist = botLocation.distance(guidP);
        if (dist < closestDistance)
        {
            closestDistance = dist;
            runeforge = ai->GetGameObject(guid);
        }
    }

    if (runeforge && closestDistance <= INTERACTION_DISTANCE)
    {
        Item* weapon = bot->GetItemByPos(INVENTORY_SLOT_BAG_0, EQUIPMENT_SLOT_MAINHAND);
        if (!weapon)
            return false;
        

        uint32 spellDuration = sPlayerbotAIConfig.globalCoolDown;

        if (ai->CastSpell(runeforgeSpellId, bot, weapon, true, &spellDuration))
        {
            SetDuration(spellDuration);
            ai->TellPlayerNoFacing(requester, "Applying "+ ChatHelper::formatSpell(runeforgeSpellId) +" to weapon.", PlayerbotSecurityLevel::PLAYERBOT_SECURITY_ALLOW_ALL, false);
            return true;
        }

        return false;
    }
    else if (runeforge)
    {
        float angle = runeforge->GetAngle(bot); //Current approuch angle.
        float distance = frand(0.5, 1);

        WorldPosition runeForgePos(runeforge);

        runeForgePos += WorldPosition(0, cos(angle) * INTERACTION_DISTANCE * distance, sin(angle) * INTERACTION_DISTANCE * distance);

        if (MoveTo(runeForgePos, false, false))
        {
            SetDuration(GetDuration() + 1);
            return true;
        }

        return false;
    }

    SET_AI_VALUE2(time_t, "manual time", "next runeforge check", time(0) + 30);

    return false;
}

bool RuneforgeAction::isUseful()
{
    Item* weapon = bot->GetItemByPos(INVENTORY_SLOT_BAG_0, EQUIPMENT_SLOT_MAINHAND);
    if (!weapon)
        return false;

    return true;
}
