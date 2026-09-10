#include "botpch.h"
#include "PlayerbotNaturalLanguageCapabilityRegistry.h"

PlayerbotNaturalLanguageCapabilityRegistry& PlayerbotNaturalLanguageCapabilityRegistry::instance()
{
    static PlayerbotNaturalLanguageCapabilityRegistry registry;
    return registry;
}

void PlayerbotNaturalLanguageCapabilityRegistry::Register(const char* key, const char* family,
    const char* risk, const char* authority, const char* confirmation, LivingCapabilityExecutor executor)
{
    LivingCapabilityRegistration value;
    value.operationKey = key;
    value.family = family;
    value.riskTier = risk;
    value.authorityPolicy = authority;
    value.confirmationClass = confirmation;
    value.executor = executor;
    registrations[value.operationKey] = value;
}

PlayerbotNaturalLanguageCapabilityRegistry::PlayerbotNaturalLanguageCapabilityRegistry()
{
    const char* socialRoutine[] = {
        "create_group_and_invite", "invite_to_existing_group", "request_leader_invite",
        "accept_group_invite", "share_quest", "accept_party_quest_plan", "meet_player",
        "vendor_bags", "gather_node", "decline_gather_node", "open_chest", "decline_chest",
        "reserve_gathering_nodes", "release_gathering_nodes", "ask_gathering_nodes",
        "grant_party_free_time", "resume_party_assist", "solicit_petition_signatures"
    };
    for (const char* key : socialRoutine)
        Register(key, key == std::string("solicit_petition_signatures") ? "socialGovernance" : "grouping",
            "routine", "contextual_party_authority", "low_risk", LivingCapabilityExecutor::social);

    const char* socialConsequential[] = {"pass_leadership", "leave_group", "leave_ai_party_for_player"};
    for (const char* key : socialConsequential)
        Register(key, "grouping", "consequential", "party_leader", "explicit_confirmation",
            LivingCapabilityExecutor::social);
    Register("transfer_guild_leadership", "socialGovernance", "consequential", "guild_leader",
        "explicit_confirmation", LivingCapabilityExecutor::social);
    Register("perform_emote", "socialGovernance", "routine", "unrestricted_social_request",
        "low_risk", LivingCapabilityExecutor::social);
    Register("wait_here", "travel", "routine", "contextual_party_authority",
        "low_risk", LivingCapabilityExecutor::social);
    Register("use_hearthstone", "travel", "routine", "contextual_party_authority",
        "low_risk", LivingCapabilityExecutor::social);

    const char* combat[] = {"set_party_role", "clear_party_role", "set_puller", "hold_attacks",
        "resume_assist", "set_tactical_rule", "assign_marker_manager", "clear_tactical_rule"};
    for (const char* key : combat)
        Register(key, "combat", "routine", "party_leader_or_assistant", "low_risk",
            LivingCapabilityExecutor::partyCombat);

    const char* economy[] = {"give_item", "sell_item", "buy_item", "accept_player_gift",
        "conjure_water", "craft_commission"};
    for (const char* key : economy)
        Register(key, "progressionEconomy", "consequential", "self", "low_risk",
            LivingCapabilityExecutor::economy);
}

const LivingCapabilityRegistration* PlayerbotNaturalLanguageCapabilityRegistry::Resolve(
    const std::string& operationKey) const
{
    auto found = registrations.find(operationKey);
    return found == registrations.end() ? nullptr : &found->second;
}
