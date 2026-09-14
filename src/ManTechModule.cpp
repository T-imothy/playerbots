// Penqle's generated loader owns registration. Data-dependent initialization
// runs in WorldScript::OnStartup after the native caches have been loaded.
#include "Chat/Chat.h"
#include "ScriptObjects.h"

class ManTechCommandAccess : public ChatHandler
{
public:
    static std::vector<ChatCommand> Commands()
    {
        return {
            {"bot", SEC_PLAYER, false, &ManTechCommandAccess::HandlePlayerbotCommand, "", nullptr},
            {"rndbot", SEC_ADMINISTRATOR, true, &ManTechCommandAccess::HandleRandomPlayerbotCommand, "", nullptr},
            {"ahbot", SEC_ADMINISTRATOR, true, &ManTechCommandAccess::HandleAhBotCommand, "", nullptr},
            {"perfmon", SEC_MODERATOR, true, &ManTechCommandAccess::HandlePerfMonCommand, "", nullptr}
        };
    }
};

// Protected inherited handlers retain their actual ChatHandler member-pointer
// type. This adapter never downcasts or fabricates a handler object.
class ManTechBotCommands : public CommandScript
{
public:
    ManTechBotCommands() : CommandScript("mantech_playerbot_commands") {}
    std::vector<ChatCommand> GetCommands() const override
    {
        return ManTechCommandAccess::Commands();
    }
};

void AddSC_playerbot_hooks();
void AddManTechPlayerbotsScripts()
{
    AddSC_playerbot_hooks();
    new ManTechBotCommands();
}
