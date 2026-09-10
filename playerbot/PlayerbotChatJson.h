#ifndef _PLAYERBOT_CHAT_JSON_H
#define _PLAYERBOT_CHAT_JSON_H

#include <boost/property_tree/json_parser.hpp>
#include <boost/property_tree/ptree.hpp>

#include <cstdint>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace LivingWowChatJson
{
    struct Reply
    {
        uint32_t botGuid = 0;
        std::string text;
        uint32_t delayMs = 0;
        std::string requiresActionId;
        std::string replyChannel;
    };

    struct Proposal
    {
        std::string proposalId;
        uint32_t botGuid = 0;
        uint32_t targetGuid = 0;
        std::string type;
        std::string capabilityRef;
        uint32_t quantity = 0;
        uint32_t priceCopper = 0;
        std::string delivery;
        std::string intent;
    };

    struct Envelope
    {
        std::vector<Reply> replies;
        std::vector<Proposal> proposals;
    };

    inline bool ParseEnvelope(const std::string& value, Envelope& envelope, std::string& error)
    {
        envelope = Envelope();
        error.clear();
        try
        {
            boost::property_tree::ptree root;
            std::istringstream input(value);
            boost::property_tree::read_json(input, root);

            if (auto responses = root.get_child_optional("responses"))
            {
                for (const auto& entry : *responses)
                {
                    const auto& node = entry.second;
                    Reply reply;
                    reply.botGuid = node.get<uint32_t>("bot_guid");
                    reply.text = node.get<std::string>("text");
                    reply.delayMs = node.get<uint32_t>("delay_ms");
                    reply.requiresActionId = node.get<std::string>("requires_action_id", "");
                    reply.replyChannel = node.get<std::string>("reply_channel", "");
                    if (!reply.botGuid || reply.text.size() > 500 || reply.requiresActionId.size() > 64 ||
                        reply.replyChannel.size() > 16)
                        throw std::runtime_error("invalid reply fields");
                    envelope.replies.push_back(std::move(reply));
                }
            }

            if (auto proposals = root.get_child_optional("action_proposals"))
            {
                for (const auto& entry : *proposals)
                {
                    const auto& node = entry.second;
                    Proposal proposal;
                    proposal.proposalId = node.get<std::string>("proposal_id");
                    proposal.botGuid = node.get<uint32_t>("bot_guid");
                    proposal.targetGuid = node.get<uint32_t>("target_guid");
                    proposal.type = node.get<std::string>("type");
                    proposal.capabilityRef = node.get<std::string>("capability_ref");
                    proposal.quantity = node.get<uint32_t>("quantity");
                    proposal.priceCopper = node.get<uint32_t>("price_copper", 0);
                    proposal.delivery = node.get<std::string>("delivery");
                    proposal.intent = node.get<std::string>("intent", "");
                    if (proposal.proposalId.empty() || proposal.proposalId.size() > 64 || !proposal.botGuid ||
                        !proposal.targetGuid || proposal.type.empty() || proposal.type.size() > 32 ||
                        proposal.capabilityRef.empty() || proposal.capabilityRef.size() > 120 || !proposal.quantity ||
                        proposal.delivery.empty() || proposal.delivery.size() > 24 || proposal.intent.size() > 240)
                        throw std::runtime_error("invalid proposal fields");
                    envelope.proposals.push_back(std::move(proposal));
                }
            }
            return true;
        }
        catch (const std::exception& exception)
        {
            envelope = Envelope();
            error = exception.what();
            return false;
        }
    }
}

#endif
