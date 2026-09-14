#pragma once

#include "ObjectGuid.h"
#include "WorldPacket.h"

class Player;

namespace ai
{
    // Queued work may outlive the player who submitted it. Resolve by GUID
    // before use, and do not deliver old commands to a replacement login.
    class EventOwner
    {
    public:
        EventOwner(Player* player = nullptr);
        Player* Get() const;
        bool HasOwner() const { return original != nullptr; }
        bool IsAvailable() const { return !HasOwner() || Get() != nullptr; }
    private:
        ObjectGuid guid;
        Player* original;
    };

    class Event
	{
	public:
        // Penqle's WorldPacket has a deleted copy operator= (it has a user-defined
        // move ctor, which implicitly deletes copy=). Use the member init list for
        // the copy ctor (WorldPacket's copy CTOR IS available) and an explicit
        // operator= that copy-constructs + move-assigns.
        Event(Event const& other)
            : source(other.source)
            , param(other.param)
            , packet(other.packet)
            , owner(other.owner)
        {}
        Event& operator=(Event const& other)
        {
            if (this == &other) return *this;
            source = other.source;
            param = other.param;
            packet = WorldPacket(other.packet);  // copy-construct + move-assign
            owner = other.owner;
            return *this;
        }
        Event() {}
        Event(std::string source) : source(source) {}
        Event(std::string source, std::string param, EventOwner owner = {}) : source(source), param(param), owner(owner) {}
        Event(std::string source, WorldPacket &packet, EventOwner owner = {}) : source(source), packet(packet), owner(owner) {}
        Event(std::string source, ObjectGuid object, EventOwner owner = {}) : source(source), owner(owner) { packet << object; }
        virtual ~Event() {}

	public:
        std::string getSource() const { return source; }
        std::string getParam() { return param; }
        WorldPacket& getPacket() { return packet; }
        ObjectGuid getObject();
        Player* getOwner() const { return owner.Get(); }
        bool IsOwnerAvailable() const { return owner.IsAvailable(); }
        bool operator! () const { return source.empty() || !IsOwnerAvailable(); }

    protected:
        std::string source;
        std::string param;
        WorldPacket packet;
        EventOwner owner;
	};
}
