#include "playerbot/playerbot.h"
#include "UldamanAltarAction.h"
#include "RitualSummonAction.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/ServerFacade.h"

using namespace ai;

namespace
{
    bool IsUldamanAltar(GameObject* altar)
    {
        if (!altar || !altar->IsInWorld() || !sServerFacade.isSpawned(altar) ||
            altar->GetLootState() == GO_JUST_DEACTIVATED || altar->GetOwnerGuid() ||
            altar->GetGoType() != GAMEOBJECT_TYPE_SUMMONING_RITUAL || !altar->GetGOInfo()) return false;
        const auto& ritual = altar->GetGOInfo()->summoningRitual;
        // Respect native expansion data: Wrath normally needs only one user.
        return ritual.reqParticipants > 1 && ritual.animSpell == 11206 &&
            ((altar->GetEntry() == 130511 && ritual.spellId == 11568) ||
             (altar->GetEntry() == 133234 && ritual.spellId == 10340));
    }
}

bool AssistUldamanAltarAction::Start(PlayerbotAI* ai, Player* requester, ObjectGuid altarGuid)
{
    Player* bot = ai->GetBot();
    if (!CanParticipateInRitual(bot) || !CanParticipateInRitual(requester) ||
        bot == requester || bot->GetMapId() != 70 || !bot->GetGroup() ||
        requester->GetGroup() != bot->GetGroup() || requester->GetMap() != bot->GetMap()) return false;
    GameObject* altar = ai->GetGameObject(altarGuid);
    if (!IsUldamanAltar(altar) || !bot->IsInMap(altar) ||
        requester->GetDistance(altar) > altar->GetInteractionDistance() ||
        bot->GetDistance(altar) > sPlayerbotAIConfig.reactDistance) return false;
    // This bounded request originates only from the master's actual object click.
    // Store identities, never pointers, across movement and map updates.
    ai->GetAiObjectContext()->GetValue<UldamanAltarRequest>("uldaman altar request")->Set(
        {altarGuid, requester->GetObjectGuid(), bot->GetInstanceId(), time(nullptr) + 30});
    return true;
}

GameObject* AssistUldamanAltarAction::GetAltar()
{
    if (!bot->IsInWorld() || bot->IsBeingTeleported() || bot->GetMapId() != 70) return nullptr;
    auto* value = ai->GetAiObjectContext()->GetValue<UldamanAltarRequest>("uldaman altar request");
    auto request = value->Get();
    if (!request.expires && CanParticipateInRitual(bot) && bot->GetGroup() &&
        !bot->IsNonMeleeSpellCasted(true))
    {
        // A queued master-click event is not a reliable invitation: another
        // real party member can start the ritual, or the event can be lost
        // during an AI state reset. Recover only an already active ritual.
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* player = ref->getSource();
            if (!CanParticipateInRitual(player) || !player->isRealPlayer() ||
                player == bot || player->GetMap() != bot->GetMap()) continue;
            const Spell* channel = player->GetCurrentSpell(CURRENT_CHANNELED_SPELL);
            if (!channel || !channel->m_spellInfo || channel->getState() == SPELL_STATE_FINISHED ||
                channel->m_spellInfo->Id != 11206) continue;
            // Search only after finding a live party channel, using the existing
            // bounded nearby-object value rather than scanning on every AI tick.
            for (const auto& guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("nearest game objects no los")->Get())
            {
                GameObject* altar = ai->GetGameObject(guid);
                if (!IsUldamanAltar(altar) || !altar->GetUniqueUseCount() ||
                    altar->GetUniqueUseCount() >= altar->GetGOInfo()->summoningRitual.reqParticipants) continue;
                if (Start(ai, player, guid)) break;
            }
            request = value->Get();
            if (request.expires) break;
        }
    }
    if (!request.expires) return nullptr;
    if (request.expires <= time(nullptr) || request.instance != bot->GetInstanceId() ||
        !CanParticipateInRitual(bot) || !bot->GetGroup())
    {
        value->Set({});
        return nullptr;
    }
    if (bot->IsNonMeleeSpellCasted(true)) return nullptr;
    Player* requester = nullptr;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        if (ref->getSource() && ref->getSource()->GetObjectGuid() == request.requester)
            requester = ref->getSource();
    if (!CanParticipateInRitual(requester) || requester->GetGroup() != bot->GetGroup() ||
        requester->GetMap() != bot->GetMap())
    {
        value->Set({});
        return nullptr;
    }
    GameObject* altar = ai->GetGameObject(request.altar);
    if (!IsUldamanAltar(altar) || !bot->IsInMap(altar) ||
        bot->GetDistance(altar) > sPlayerbotAIConfig.reactDistance ||
        requester->GetDistance(altar) > altar->GetInteractionDistance()) return nullptr;
    const Spell* channel = requester->GetCurrentSpell(CURRENT_CHANNELED_SPELL);
    if (!channel || !channel->m_spellInfo || channel->getState() == SPELL_STATE_FINISHED ||
        channel->m_spellInfo->Id != altar->GetGOInfo()->summoningRitual.animSpell ||
        !altar->GetUniqueUseCount() ||
        altar->GetUniqueUseCount() >= altar->GetGOInfo()->summoningRitual.reqParticipants) return nullptr;
    return altar;
}

bool AssistUldamanAltarAction::isPossible()
{
    GameObject* altar = GetAltar();
    return altar && (bot->GetDistance(altar) <= altar->GetInteractionDistance() || ai->CanMove());
}

bool AssistUldamanAltarAction::Execute(Event&)
{
    GameObject* altar = GetAltar();
    if (!altar) return false;
    if (bot->GetDistance(altar) > altar->GetInteractionDistance())
        return ai->CanMove() && MoveNear(altar, std::min(2.0f, altar->GetInteractionDistance() * 0.5f));
    if (!bot->IsWithinLOSInMap(altar)) return false;
    ai->StopMoving();
    WorldPacket packet(CMSG_GAMEOBJ_USE);
    packet << altar->GetObjectGuid();
    bot->GetSession()->HandleGameObjectUseOpcode(packet);
    // The native handler owns counting, channel completion and encounter start.
    SetDuration(sPlayerbotAIConfig.globalCoolDown);
    return true;
}
