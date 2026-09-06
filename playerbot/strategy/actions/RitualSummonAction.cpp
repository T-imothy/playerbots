#include "playerbot/playerbot.h"
#include "RitualSummonAction.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/ServerFacade.h"
#include "Spells/SpellMgr.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;

bool ai::IsNativeSummoningRitual(uint32 spell)
{
    if (spell == 698 || spell == 23598) return true;
#ifndef MANGOSBOT_ZERO
    if (spell == 46546) return true; // TBC's native 698 replacement, retained in Wrath data
#endif
#ifdef MANGOSBOT_TWO
    if (spell == 59782 || spell == 61994) return true;
#endif
    return false; // Never auto-assist Ritual of Doom or unrelated ritual objects.
}

bool ai::CanParticipateInRitual(Player* player)
{
    return player && player->IsInWorld() && player->IsAlive() && player->GetSession() &&
        !player->GetSession()->isLogingOut() && !player->HasCharmer() && !player->IsInCombat() &&
        !player->IsBeingTeleported() && !player->IsTaxiFlying() && !player->GetTransport();
}

bool ai::HasActiveSummoningRitual(Player* player)
{
    if (!CanParticipateInRitual(player)) return false;
    for (const auto type : {CURRENT_GENERIC_SPELL, CURRENT_CHANNELED_SPELL})
    {
        const Spell* spell = player->GetCurrentSpell(type);
        if (spell && spell->m_spellInfo && spell->getState() != SPELL_STATE_FINISHED &&
            IsNativeSummoningRitual(spell->m_spellInfo->Id)) return true;
    }
    return false;
}

GameObject* ai::FindOwnedSummoningPortal(Player* player)
{
#ifdef MANGOSBOT_TWO
    if (!CanParticipateInRitual(player)) return nullptr;
    // Native EffectTransmitted does not add a type-23 portal to Unit::m_gameObj.
    // Find the live, owned, native portal through the core grid visitor instead.
    struct OwnedPortalCheck
    {
        Player* player;
        Player const& GetFocusObject() const { return *player; }
        bool operator()(GameObject* object) const
        {
            return object && object->IsInWorld() && object->GetMap() == player->GetMap() &&
                object->GetEntry() == 194097 && object->GetSpellId() == 61993 &&
                object->GetOwnerGuid() == player->GetObjectGuid() &&
                sServerFacade.isSpawned(object) && object->GetLootState() != GO_JUST_DEACTIVATED &&
                player->GetDistance(object) <= sPlayerbotAIConfig.reactDistance;
        }
    } ownedPortal{player};
    GameObject* portal = nullptr;
    MaNGOS::GameObjectSearcher<decltype(ownedPortal)> search(portal, ownedPortal);
    Cell::VisitGridObjects(player, search, sPlayerbotAIConfig.reactDistance);
    return portal;
#else
    return nullptr;
#endif
}

GameObject* AssistSummoningRitualAction::GetRitual()
{
    if (!CanParticipateInRitual(bot) || !bot->GetGroup() || bot->IsNonMeleeSpellCasted(true)) return nullptr;
    GameObject* nearest = nullptr;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* owner = ref->getSource();
        if (owner == bot || !CanParticipateInRitual(owner) || owner->GetMap() != bot->GetMap() ||
            owner->GetSelectionGuid() == bot->GetObjectGuid()) continue;
        const Spell* channel = owner->GetCurrentSpell(CURRENT_CHANNELED_SPELL);
        if (!channel || !channel->m_spellInfo || channel->getState() == SPELL_STATE_FINISHED ||
            !IsNativeSummoningRitual(channel->m_spellInfo->Id)) continue;
        GameObject* ritual = owner->GetGameObject(channel->m_spellInfo->Id);
        if (!ritual || !ritual->IsInWorld() || !bot->IsInMap(ritual) ||
            ritual->GetOwnerGuid() != owner->GetObjectGuid() || !sServerFacade.isSpawned(ritual) ||
            ritual->GetLootState() == GO_JUST_DEACTIVATED || !ritual->GetGOInfo() ||
            ritual->GetGoType() != GAMEOBJECT_TYPE_SUMMONING_RITUAL ||
            ritual->GetUniqueUseCount() >= ritual->GetGOInfo()->summoningRitual.reqParticipants ||
            bot->GetDistance(ritual) > sPlayerbotAIConfig.reactDistance) continue;
        if (!nearest || bot->GetDistance(ritual) < bot->GetDistance(nearest)) nearest = ritual;
    }
    return nearest;
}

bool AssistSummoningRitualAction::isUseful()
{
    return GetRitual() != nullptr;
}

bool AssistSummoningRitualAction::isPossible()
{
    GameObject* ritual = GetRitual();
    return ritual && (bot->GetDistance(ritual) <= ritual->GetInteractionDistance() || ai->CanMove());
}

bool AssistSummoningRitualAction::UseRitual(GameObject* ritual)
{
    // Resolve again from a live group caster instead of trusting a stale event
    // pointer. Never mark participants or finish someone else's channel ourselves.
    if (!ritual || GetRitual() != ritual) return false;
    if (bot->GetDistance(ritual) > ritual->GetInteractionDistance())
    {
        if (!ai->CanMove()) return false;
        return MoveNear(ritual, std::min(2.0f, ritual->GetInteractionDistance() * 0.5f));
    }
    if (!bot->IsWithinLOSInMap(ritual)) return false;
    ai->StopMoving();
    WorldPacket packet(CMSG_GAMEOBJ_USE);
    packet << ritual->GetObjectGuid();
    bot->GetSession()->HandleGameObjectUseOpcode(packet);
    SetDuration(sPlayerbotAIConfig.globalCoolDown);
    return true; // Submitted a normal click; native ritual completion is separate.
}

bool AssistSummoningRitualAction::Execute(Event& event)
{
    return UseRitual(GetRitual());
}

uint32 ContinueRitualSummonAction::RequiredHelpers(Player* bot)
{
#ifdef MANGOSBOT_TWO
    const uint32 entry = FindOwnedSummoningPortal(bot) ? 179944 : 194108;
#else
    const uint32 entry = 36727;
#endif
    const GameObjectInfo* info = sObjectMgr.GetGameObjectInfo(entry);
    // The native data count includes the summoner, who is not a helper.
    if (!info || info->type != GAMEOBJECT_TYPE_SUMMONING_RITUAL ||
        info->summoningRitual.reqParticipants < 2 || info->summoningRitual.reqParticipants > 40) return 0;
    return info->summoningRitual.reqParticipants - 1;
}

bool ContinueRitualSummonAction::Start(PlayerbotAI* ai, Player* requester, Player* target)
{
    Player* bot = ai->GetBot();
    if (!CanParticipateInRitual(bot) || !CanParticipateInRitual(target) || !requester ||
        !bot->GetGroup() || requester->GetGroup() != bot->GetGroup() || target->GetGroup() != bot->GetGroup() ||
        target == bot || bot->getClass() != CLASS_WARLOCK || !bot->HasSpell(698) || bot->IsNonMeleeSpellCasted(true)) return false;
    const SpellEntry* ritualSpell = sServerFacade.LookupSpellInfo(698);
    if (!ritualSpell) return false;
#ifdef MANGOSBOT_TWO
    auto* pending = ai->GetAiObjectContext()->GetValue<RitualSummonRequest>("ritual summon request");
    if (pending->Get().expires > time(nullptr)) return false;
    // Reuse only this warlock's native portal, not an unrelated nearby object.
    GameObject* portal = FindOwnedSummoningPortal(bot);
    if (portal)
    {
        pending->Set({target->GetObjectGuid(), requester->GetObjectGuid(), bot->GetMapId(), bot->GetInstanceId(), time(nullptr) + 30});
        return true;
    }
#endif
    ai->StopMoving();
    // Native EffectTransmitted captures the selection for the final summon.
    // Cast via the core, not the generic AI wrapper which selects its unit target.
    const ObjectGuid previousSelection = bot->GetSelectionGuid();
    bot->SetSelectionGuid(target->GetObjectGuid());
    const SpellCastResult result = bot->CastSpell(bot, 698, TRIGGERED_NONE);
    if (result != SPELL_CAST_OK)
    {
        bot->SetSelectionGuid(previousSelection);
        ai->TellPlayerNoFacing(requester, "The server refused Ritual of Summoning; check shards, mana, cooldown and casting conditions.");
        return false;
    }
#ifdef MANGOSBOT_TWO
    const time_t seconds = std::min(180, std::max(30, int(GetSpellDuration(ritualSpell) / 1000) + 15));
    pending->Set({target->GetObjectGuid(), requester->GetObjectGuid(), bot->GetMapId(), bot->GetInstanceId(), time(nullptr) + seconds});
#endif
    return true; // Started the native ritual, not proof the recipient accepted it.
}

bool ContinueRitualSummonAction::isUseful()
{
#ifdef MANGOSBOT_TWO
    if (bot->getClass() != CLASS_WARLOCK) return false;
    auto* value = ai->GetAiObjectContext()->GetValue<RitualSummonRequest>("ritual summon request");
    const RitualSummonRequest request = value->Get();
    if (!request.expires) return false;
    if (request.expires <= time(nullptr) || !CanParticipateInRitual(bot) ||
        request.map != bot->GetMapId() || request.instance != bot->GetInstanceId())
    {
        value->Set({});
        return false;
    }
    // Let the core keep all actual casts/channels running to completion.
    return !bot->IsNonMeleeSpellCasted(true);
#else
    return false;
#endif
}

bool ContinueRitualSummonAction::Execute(Event& event)
{
#ifdef MANGOSBOT_TWO
    if (!isUseful()) return false;
    auto* value = ai->GetAiObjectContext()->GetValue<RitualSummonRequest>("ritual summon request");
    const RitualSummonRequest request = value->Get();
    Player* target = sObjectMgr.GetPlayer(request.target);
    Player* requester = sObjectMgr.GetPlayer(request.requester);
    if (!CanParticipateInRitual(target) || !requester || !bot->GetGroup() ||
        target->GetGroup() != bot->GetGroup() || requester->GetGroup() != bot->GetGroup())
    {
        value->Set({});
        return false;
    }
    GameObject* portal = FindOwnedSummoningPortal(bot);
    if (!portal)
    {
        // The initial cast was interrupted/failed before creating its portal.
        value->Set({});
        ai->TellPlayerNoFacing(requester, "The summoning ritual ended without a portal; request it again when ready.");
        return false;
    }
    if (bot->GetDistance(portal) > portal->GetInteractionDistance())
        return ai->CanMove() && MoveNear(portal, 2.0f);
    if (!bot->IsWithinLOSInMap(portal)) return false;
    // Clear before submitting: a rejection must not spam native ritual requests.
    value->Set({});
    ai->StopMoving();
    bot->SetSelectionGuid(target->GetObjectGuid());
    WorldPacket packet(CMSG_GAMEOBJ_USE);
    packet << portal->GetObjectGuid();
    bot->GetSession()->HandleGameObjectUseOpcode(packet);
    SetDuration(sPlayerbotAIConfig.globalCoolDown);
    return true;
#else
    return false;
#endif
}
