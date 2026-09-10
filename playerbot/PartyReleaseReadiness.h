#ifndef LIVING_WOW_PARTY_RELEASE_READINESS_H
#define LIVING_WOW_PARTY_RELEASE_READINESS_H
namespace living_party_release {
enum class Blocker { ready, combat, transport, taxi, transfer };
inline Blocker Classify(bool combat, bool transport, bool taxi, bool transfer) {
    return transfer ? Blocker::transfer : taxi ? Blocker::taxi :
        transport ? Blocker::transport : combat ? Blocker::combat : Blocker::ready;
}
inline const char* Code(Blocker b) {
    switch (b) {
    case Blocker::combat: return "waiting_for_combat";
    case Blocker::transport: return "waiting_for_transport";
    case Blocker::taxi: return "waiting_for_flight";
    case Blocker::transfer: return "waiting_for_map_transfer";
    default: return "ready";
    }
}
inline const char* Waiting(Blocker b) {
    switch (b) {
    case Blocker::combat: return "I'm in a fight. I'll leave this group when it's safe, then let you know.";
    case Blocker::transport: return "I'm aboard a boat or zeppelin. I'll leave this group once I'm safely off, then let you know.";
    case Blocker::taxi: return "I'm on a flight. I'll leave this group after I land, then let you know.";
    case Blocker::transfer: return "I'm changing zones. I'll leave this group once that's finished, then let you know.";
    default: return "I'm still arranging to leave this group. I'll let you know when I'm free.";
    }
}
inline const char* Expired(Blocker b) {
    switch (b) {
    case Blocker::combat: return "I couldn't get clear of combat, so I'm still grouped. Please ask me again when it's safe.";
    case Blocker::transport: return "I couldn't safely get off the transport, so I'm still grouped. Please ask me again once I'm off.";
    case Blocker::taxi: return "I'm still on a flight and couldn't switch groups yet. Please ask me again after I land.";
    default: return "I couldn't safely leave before the request expired. I'm still grouped; please ask me again.";
    }
}
}
#endif
