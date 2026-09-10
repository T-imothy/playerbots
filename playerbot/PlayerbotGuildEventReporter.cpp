#include "playerbot/playerbot.h"
#include "PlayerbotGuildEventReporter.h"
#include "PlayerbotLLMInterface.h"
#include "GuildGovernancePolicy.h"
#include <boost/property_tree/ptree.hpp>
#include <boost/property_tree/json_parser.hpp>
#include <openssl/sha.h>
#include <future>
#include <iomanip>
#include <sstream>

namespace {
std::string Quoted(const std::string& value) {return "\""+PlayerbotLLMInterface::SanitizeForJson(value)+"\"";}
std::string Digest(const std::string& body) {
    unsigned char bytes[SHA256_DIGEST_LENGTH];
    SHA256(reinterpret_cast<const unsigned char*>(body.data()),body.size(),bytes);
    std::ostringstream out;for(auto b:bytes)out<<std::hex<<std::setw(2)<<std::setfill('0')<<unsigned(b);return out.str();
}
}
void UpdateGuildEventReporting() {
    static std::future<std::string> request;
    static std::string cursor,nextCursor,pending;
    static uint32 next=0;
    const uint32 now=uint32(time(nullptr));
    if(request.valid()) {
        if(request.wait_for(std::chrono::seconds(0))!=std::future_status::ready) return;
        bool recorded=false;
        try {
            std::istringstream response(request.get());boost::property_tree::ptree root;
            boost::property_tree::read_json(response,root);recorded=root.get<std::string>("status","")=="recorded";
        } catch(...) {}
        if(recorded) {cursor=nextCursor;pending.clear();}
        next=now+(recorded?10:30);
    }
    if(now<next) return;
    next=now+10;
    if(pending.empty()) {
        // Reuse the native tables as the durable source. Keyset pages revisit
        // recent history and live schedules after restarts or gateway outages.
        // One 24-event page and at most 24 bounded roster reads per cadence.
        auto rows=CharacterDatabase.PQuery("SELECT event_id,guild_id,event_type,state,title,target_id,organizer_guid,scheduled_at,COALESCE(ends_at,0),minimum_members,maximum_members,tank_slots,healer_slots,damage_slots,failure_reason,created_at,revision,finished_at FROM guild_society_event WHERE event_id>'%s' AND (state IN ('draft','announced','forming','traveling','active') OR updated_at>=%u) ORDER BY event_id LIMIT 24",cursor.c_str(),now>604800?now-604800:0);
        if(!rows) {cursor.clear();return;}
        std::ostringstream batch;batch<<"{\"events\":[";uint32 count=0;
        do {
            Field* f=rows->Fetch();const std::string id=f[0].GetString();
            if(!livingguild::Id(id)) continue;
            nextCursor=id;
            std::ostringstream item;
            item<<"\"type\":\"guild_event\",\"guild_event_id\":"<<Quoted(id)<<",\"guild_id\":"<<f[1].GetUInt32()
                <<",\"event_type\":"<<Quoted(f[2].GetString())<<",\"state\":"<<Quoted(f[3].GetString())
                <<",\"title\":"<<Quoted(f[4].GetString())<<",\"target_id\":"<<f[5].GetUInt32()
                <<",\"organizer_guid\":"<<f[6].GetUInt32()<<",\"scheduled_at\":"<<f[7].GetUInt32()
                <<",\"ends_at\":"<<f[8].GetUInt32()<<",\"minimum_members\":"<<f[9].GetUInt32()
                <<",\"maximum_members\":"<<f[10].GetUInt32()<<",\"tank_slots\":"<<f[11].GetUInt32()
                <<",\"healer_slots\":"<<f[12].GetUInt32()<<",\"damage_slots\":"<<f[13].GetUInt32()
                <<",\"failure_reason\":"<<Quoted(f[14].GetString())<<",\"created_at\":"<<f[15].GetUInt32()
                <<",\"revision\":"<<f[16].GetUInt32()<<",\"finished_at\":"<<f[17].GetUInt32()<<",\"roster\":[";
            auto roster=CharacterDatabase.PQuery("SELECT r.character_guid,r.response,r.role,r.human,r.accepted_revision,COALESCE(c.name,'') FROM guild_society_rsvp r LEFT JOIN characters c ON c.guid=r.character_guid WHERE r.event_id='%s' ORDER BY r.character_guid LIMIT 64",id.c_str());
            uint32 people=0;
            if(roster) do {
                Field* r=roster->Fetch();const std::string name=r[5].GetString();
                if(people++) item<<',';
                item<<"{\"character_guid\":"<<r[0].GetUInt32()<<",\"character_name\":"<<Quoted(name)
                    <<",\"response\":"<<Quoted(r[1].GetString())<<",\"role\":"<<Quoted(r[2].GetString())
                    <<",\"human\":"<<(r[3].GetUInt32()?"true":"false")<<",\"accepted_revision\":"<<r[4].GetUInt32()<<'}';
            } while(roster->NextRow());
            // Empty/error roster queries are deliberately non-destructive;
            // cancelled/declined native rows still update individual records.
            item<<"],\"roster_complete\":"<<(roster&&people<64?"true":"false");
            const std::string content=item.str();
            if(count++)batch<<',';
            batch<<"{\"event_id\":\"realm-event:"<<Digest(content)<<"\",\"snapshot_at\":"<<now<<','<<content<<'}';
        } while(rows->NextRow());
        batch<<"]}";
        if(!count){cursor.clear();return;}
        pending=batch.str();
    }
    const std::string body=pending;
    try { request=std::async(std::launch::async,[body] {
        std::vector<std::string> debug;
        // Existing authenticated telemetry endpoint, not an LLM/model request.
        return PlayerbotLLMInterface::Generate(body,9,1000000,debug,true,"/v2/guilds/events");
    }); } catch(...) { next=now+30; } // Keep the same page when a worker cannot start.
}
