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
        std::string quoteId;
    };

    struct EconomicQuote
    {
        std::string quoteId, state, direction, capabilityRef, delivery, freeGiftDisposition;
        uint32_t botGuid = 0;
        uint32_t targetGuid = 0;
        uint32_t itemId = 0;
        uint32_t quantity = 0;
        uint32_t openingPriceCopper = 0;
        uint32_t currentPriceCopper = 0;
        uint32_t limitPriceCopper = 0;
        uint32_t roundsUsed = 0;
        uint32_t maximumRounds = 0;
        uint32_t expiresInSeconds = 300;
    };

    struct Envelope
    {
        std::vector<Reply> replies;
        std::vector<Proposal> proposals;
        std::vector<EconomicQuote> economicOffers;
        std::vector<EconomicQuote> economicQuoteUpdates;
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
                    proposal.quoteId = node.get<std::string>("quote_id", "");
                    if (proposal.proposalId.empty() || proposal.proposalId.size() > 64 || !proposal.botGuid ||
                        !proposal.targetGuid || proposal.type.empty() || proposal.type.size() > 32 ||
                        proposal.capabilityRef.empty() || proposal.capabilityRef.size() > 120 || !proposal.quantity ||
                        proposal.delivery.empty() || proposal.delivery.size() > 24 || proposal.intent.size() > 240)
                        throw std::runtime_error("invalid proposal fields");
                    envelope.proposals.push_back(std::move(proposal));
                }
            }
            auto parseQuotes = [](const boost::property_tree::ptree& values, std::vector<EconomicQuote>& output)
            {
                for (const auto& entry : values)
                {
                    const auto& node = entry.second;
                    EconomicQuote quote;
                    quote.quoteId = node.get<std::string>("quote_id");
                    quote.state = node.get<std::string>("state", "offered");
                    quote.botGuid = node.get<uint32_t>("bot_guid");
                    quote.targetGuid = node.get<uint32_t>("target_guid");
                    quote.direction = node.get<std::string>("direction");
                    quote.itemId = node.get<uint32_t>("item_id");
                    quote.quantity = node.get<uint32_t>("quantity");
                    quote.capabilityRef = node.get<std::string>("capability_ref");
                    quote.openingPriceCopper = node.get<uint32_t>("opening_price_copper");
                    quote.currentPriceCopper = node.get<uint32_t>("current_price_copper");
                    quote.limitPriceCopper = node.get<uint32_t>("limit_price_copper");
                    quote.roundsUsed = node.get<uint32_t>("rounds_used", 0);
                    quote.maximumRounds = node.get<uint32_t>("maximum_rounds", 0);
                    quote.delivery = node.get<std::string>("delivery", "meeting");
                    quote.freeGiftDisposition = node.get<std::string>("free_gift_disposition", "insist_pay");
                    quote.expiresInSeconds = node.get<uint32_t>("expires_in_seconds", 300);
                    if (quote.quoteId.empty() || quote.quoteId.size() > 64 || !quote.botGuid || !quote.targetGuid ||
                        !quote.itemId || !quote.quantity || quote.capabilityRef.empty() || quote.capabilityRef.size() > 120)
                        throw std::runtime_error("invalid economic quote fields");
                    output.push_back(std::move(quote));
                }
            };
            if (auto values = root.get_child_optional("economic_offers")) parseQuotes(*values, envelope.economicOffers);
            if (auto values = root.get_child_optional("economic_quote_updates")) parseQuotes(*values, envelope.economicQuoteUpdates);
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
