#include "playerbot/playerbot.h"
#include "Database/DBCStore.h"
#include <tuple>

namespace {
    DBCStorage<EmotesTextSoundEntry> emoteSounds("niiii");
    std::map<std::tuple<uint32,uint32,uint32>, EmotesTextSoundEntry const*> soundIndex;
}
void LoadPlayerbotEmoteSounds()
{
    // Startup only; the immutable index and native storage outlive all AI jobs.
    std::string path = sWorld.GetDataPath() + "dbc/EmotesTextSound.dbc";
    if (!emoteSounds.Load(path.c_str()))
    {
        sLog.outError("ManTech: optional EmotesTextSound.dbc unavailable; voice emotes disabled");
        return;
    }
    for (uint32 id = 0; id < emoteSounds.GetNumRows(); ++id)
        if (auto* entry = emoteSounds.LookupEntry(id))
            if (entry->SoundId)
                soundIndex.emplace(std::make_tuple(entry->EmotesTextId, entry->RaceId, entry->SexId), entry);
    sLog.outString("ManTech: loaded %zu race/sex voice emotes", soundIndex.size());
}
EmotesTextSoundEntry const* FindTextSoundEmoteFor(uint32 textEmoteId, uint32 race, uint32 gender)
{
    auto entry = soundIndex.find(std::make_tuple(textEmoteId, race, gender));
    return entry == soundIndex.end() ? nullptr : entry->second;
}
