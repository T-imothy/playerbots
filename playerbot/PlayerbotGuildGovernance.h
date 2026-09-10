#ifndef LIVING_PLAYERBOT_GUILD_GOVERNANCE_H
#define LIVING_PLAYERBOT_GUILD_GOVERNANCE_H
#include "GuildGovernancePolicy.h"
#include <map>
#include <string>
#include <vector>
#include <set>
class Player;
class Guild;
class PlayerbotGuildGovernance {
public:
    static PlayerbotGuildGovernance& instance();
    bool IsAvailable() { return Ready(); }
    bool Handle(Player* actor,const std::string& message);
    bool HandleLegacy(Player* actor,const std::string& message);
    void RememberLegacySnapshot(Player* actor,uint32_t token);
    void Update(bool active);
    void ConfigureServer(bool global,const std::set<uint32_t>& canaries,bool recruitment,bool events,bool supplies);
    bool Allows(Guild* guild,const std::string& duty,Player* actor=nullptr);
    uint32_t Permissions(Player* actor,Guild* guild) const;
    livingguild::Policy ReadPolicy(Guild* guild);
    void Record(uint32_t guild,uint32_t kind,uint32_t actor,uint32_t target,uint32_t value);
private:
    bool Ready();
    livingguild::Policy* Load(Guild* guild);
    void Send(Player* actor,const std::string& text);
    void Snapshot(Player* actor,Guild* guild,livingguild::Policy& policy,const std::string& operation,
        const std::string& section,uint32_t offset,uint32_t starts=0,uint32_t ends=0,bool history=false);
    bool active_=false,ready_=false;
    uint32_t readyCheck_=0,nextFlush_=0;
    std::map<uint32_t,livingguild::Policy> policies_;
    std::map<uint32_t,uint32_t> requests_;
    bool global_=false,recruitment_=false,events_=false,supplies_=false;
    std::set<uint32_t> canaries_;
    struct Duties { uint32_t refreshed=0;std::map<std::string,uint32_t> actors; };
    std::map<uint32_t,Duties> officers_;
    struct Fact { uint32_t guild,kind,actor,target,value,time; };
    std::vector<Fact> facts_;
    struct LegacySnapshot { uint32_t guild,token,revision,expires; };
    std::map<uint32_t,LegacySnapshot> legacySnapshots_;
    uint32_t legacyActor_=0;
    bool legacySucceeded_=false;
};
#define sGuildGovernance PlayerbotGuildGovernance::instance()
#endif
