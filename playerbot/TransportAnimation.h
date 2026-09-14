#pragma once
struct TransportAnimation;
// Immutable module view of the installed client data, loaded on first use.
TransportAnimation const* GetPlayerbotTransportAnimation(unsigned int entry);
