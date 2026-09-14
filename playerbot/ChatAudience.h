#pragma once

// Called only after map jobs and the native channel broadcaster have joined.
// Publishes values, never Channel or Player pointers, for map-owner readers.
void RefreshPlayerbotChatAudience(uint32 diff);
