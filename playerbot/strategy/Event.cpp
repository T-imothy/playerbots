
#include "playerbot/playerbot.h"
#include "Objects/Player.h"
#include "ObjectAccessor.h"
#include "Event.h"


using namespace ai;

EventOwner::EventOwner(Player* player) : guid(player ? player->GetObjectGuid() : ObjectGuid()), original(player) {}

Player* EventOwner::Get() const
{
    if (!original)
        return nullptr;

    Player* player = sObjectMgr.GetPlayer(guid, false);
    // Compare the old address only; never dereference a saved player pointer.
    if (player != original || !player->GetSession() || player->GetSession()->GetPlayer() != player)
        return nullptr;

    return player;
}

ObjectGuid Event::getObject()
{
    if (packet.empty())
        return ObjectGuid();

    WorldPacket p(packet);
    p.rpos(0);
    
    ObjectGuid guid;
    p >> guid;

    return guid;
}
