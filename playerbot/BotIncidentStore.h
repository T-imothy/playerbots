#pragma once
#include "BotProgress.h"
#include <deque>
#include <map>

namespace ai {
struct BotIncident {
    uint64_t id=0, target=0, updated=0;
    uint32_t bot=0, map=0, zone=0, duration=0;
    BotIncidentKind kind=BotIncidentKind::Stuck;
    std::string action, reason;
    bool open=false;
};
// Protected by the diagnostic service mutex. History and active storage are bounded.
class BotIncidentStore {
    std::map<std::pair<uint32_t, BotIncidentKind>, BotIncident> active;
    std::deque<BotIncident> resolved;
    uint64_t nextId=0, overflow=0;
    size_t capacity, history;
    void Archive(BotIncident value, char const* reason) {
        value.open=false; value.reason=reason;
        resolved.push_back(std::move(value));
        while (resolved.size()>history) resolved.pop_front();
    }
public:
    explicit BotIncidentStore(size_t limit=1024, size_t retained=200):capacity(limit),history(retained) {}
    void Record(BotIncident value) {
        auto key=std::make_pair(value.bot,value.kind);
        auto it=active.find(key);
        if (!value.open) {
            if (it==active.end()) return;
            value.id=it->second.id;
            if (value.action.empty()) value.action=it->second.action;
            Archive(std::move(value),"condition_cleared"); active.erase(it); return;
        }
        if (it!=active.end()) { value.id=it->second.id; it->second=std::move(value); return; }
        if (active.size()>=capacity) { ++overflow; return; }
        value.id=++nextId; active.emplace(key,std::move(value));
    }
    void Expire(uint64_t now) {
        for(auto it=active.begin();it!=active.end();) {
            if (now>=it->second.updated && now-it->second.updated>90000) {
                Archive(it->second,"telemetry_expired"); it=active.erase(it);
            } else ++it;
        }
    }
    void CloseBot(uint32_t bot) {
        for(auto it=active.begin();it!=active.end();) {
            if(it->first.first==bot) { Archive(it->second,"observation_reset");it=active.erase(it); }
            else ++it;
        }
    }
    std::vector<BotIncident> Snapshot() const {
        std::vector<BotIncident> rows; rows.reserve(active.size()+resolved.size());
        for(auto const& kv:active) rows.push_back(kv.second);
        rows.insert(rows.end(),resolved.begin(),resolved.end()); return rows;
    }
    size_t Active()const{return active.size();}
    uint64_t Overflow()const{return overflow;}
};
}
