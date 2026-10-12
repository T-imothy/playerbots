#pragma once
#include "Trigger.h"
#include "triggers/WorldPacketTrigger.h"
#include "playerbot/ChatHelper.h"

namespace ai
{
    class ExternalEventHelper 
    {
    public:
        ExternalEventHelper(AiObjectContext* aiObjectContext) : aiObjectContext(aiObjectContext) {}

        bool ParseChatCommand(std::string command, Player* owner = NULL)
        {
            std::string linkCommand = ChatHelper::parseValue("command", command);
            bool forceCommand = false;

            if (!linkCommand.empty())
            {
                command = linkCommand;
                forceCommand = true;
            }

            if (HandleCommand(command, "", owner, forceCommand))
                return true;

            size_t i = std::string::npos;
            while (true)
            {
                size_t found = command.rfind(" ", i);
                if (found == std::string::npos || !found)
                    break;

                std::string name = command.substr(0, found);
                std::string param = command.substr(found + 1);

                i = found - 1;

                if (HandleCommand(name, param, owner, forceCommand))
                    return true;
            }

            if (!ChatHelper::parseable(command))
                return false;

            if (command.find("Hvalue:help") != std::string::npos || command.find("[h:") != std::string::npos)
            {
                HandleCommand("help", command, owner);
                return true;
            }

            if (owner->isRealPlayer())
            {
                HandleCommand("c", command, owner);
                HandleCommand("t", command, owner);
            }
            return true;
        }

        bool HandlePacket(std::map<uint16, std::string> &handlers, const WorldPacket &packet, Player* owner = NULL)
        {
            uint16 opcode = packet.GetOpcode();
            std::string name = handlers[opcode];
            // BuyResult values are payload fields, not packet opcodes. All
            // three native SendBuyError layouts finish with the result byte.
            if (opcode == SMSG_BUY_FAILED && name == "buy failed")
            {
                if (packet.size() != 13 && packet.size() != 17)
                    return true;
                WorldPacket resultPacket(packet);
                resultPacket.rpos(packet.size() - 1);
                uint8 result;
                resultPacket >> result;
#ifdef MANGOSBOT_TWO
                if (result == uint8(BuyResult::NOT_ENOUGHT_MONEY))
                    name = "not enough money";
                else if (result == uint8(BuyResult::REPUTATION_REQUIRE))
#else
                if (result == uint8(BUY_ERR_NOT_ENOUGHT_MONEY))
                    name = "not enough money";
                else if (result == uint8(BUY_ERR_REPUTATION_REQUIRE))
#endif
                    name = "not enough reputation";
                else
                    return true;
            }
            if (name.empty())
                return true;

            Trigger* trigger = aiObjectContext->GetTrigger(name);
            if (!trigger)
                return true;

            Event event = trigger->Check();            
            if (!event.getSource().empty())
                return false;
                        
            WorldPacket p(packet);
            trigger->ExternalEvent(p, owner);

            return true;
        }

        bool HandleCommand(std::string name, std::string param, Player* owner = NULL, bool forceCommand = false)
        {
            Trigger* trigger = aiObjectContext->GetTrigger(name);
            if (!trigger)
                return false;

            if(!forceCommand)
                trigger->ExternalEvent(param, owner);
            else
                trigger->ExternalEventForce(param, owner);
            return true;
        }

    private:
        AiObjectContext* aiObjectContext;
    };
}
