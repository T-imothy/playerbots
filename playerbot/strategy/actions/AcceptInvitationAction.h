#pragma once

#include "playerbot/strategy/Action.h"
#include "playerbot/LivingTrainingGroupPriority.h"
#include "playerbot/PlayerbotChatDirector.h"
#include "playerbot/PlayerbotRendezvousManager.h"
#include "playerbot/PlayerbotSocialActionBroker.h"

namespace ai
{
    class AcceptInvitationAction : public Action 
    {
    public:
        AcceptInvitationAction(PlayerbotAI* ai) : Action(ai, "accept invitation") {}

        static uint32 RememberPartyMember(Player* observer, Player* member)
        {
            if (!observer || !member || !observer->GetPlayerbotAI() || observer == member)
                return 0;

            std::ostringstream key;
            key << "partyWith:" << member->GetGUIDLow();
            uint32 previous = sRandomPlayerbotMgr.GetValue(observer->GetGUIDLow(), key.str());
            const int32 persistentSeconds = 10 * 365 * 24 * 60 * 60;
            sRandomPlayerbotMgr.SetValue(observer->GetGUIDLow(), key.str(),
                std::min<uint32>(1000000, previous + 1), "", persistentSeconds);
            return previous;
        }

        virtual bool Execute(Event& event) override
        {
            Group* grp = bot->GetGroupInvite();
            if (!grp)
                return false;

            Player* inviter = sObjectMgr.GetPlayer(grp->GetLeaderGuid());
            if (!inviter)
                return false;

            uint32 reservedFor = sPlayerbotSocialActionBroker.ReservedForPlayer(bot->GetGUIDLow());
            if (reservedFor && inviter->GetGUIDLow() != reservedFor)
            {
                bot->UninviteFromGroup();
                return false;
            }

			if (!ai->GetSecurity()->CheckLevelFor(PlayerbotSecurityLevel::PLAYERBOT_SECURITY_INVITE, false, inviter))
            {
                WorldPacket data(SMSG_GROUP_DECLINE, 10);
                data << bot->GetName();
                sServerFacade.SendPacket(inviter, data);
                bot->UninviteFromGroup();
                return false;
            }
            
            if (LivingWowDeferBotPartyForTraining(bot, inviter, grp))
            {
                bot->UninviteFromGroup();
                return false;
            }

            if (bot->isAFK())
                bot->ToggleAFK();

            WorldPacket p;
            uint32 roles_mask = 0;
            p << roles_mask;
            bot->GetSession()->HandleGroupAcceptOpcode(p);

            if (!bot->GetGroup() || !bot->GetGroup()->IsMember(inviter->GetObjectGuid()))
                return false;

            sPlayerbotSocialActionBroker.CompleteGroupReservation(
                bot->GetGUIDLow(), inviter->GetGUIDLow());

            // Capture the bot's pre-assist position and activity immediately
            // after a real player's invitation succeeds. Movement itself is
            // deferred to the rendezvous manager's world update.
            if (inviter->isRealPlayer())
                sPlayerbotRendezvousManager.RegisterPartyAssist(bot, inviter);

            if (sRandomPlayerbotMgr.IsFreeBot(bot))
            {
                ai->SetMaster(inviter);

                std::string defaultMovementStrategy = ai->GetDefaultMovementStrategy();
                ai->ChangeStrategy("+" + defaultMovementStrategy, BotState::BOT_STATE_NON_COMBAT);
            }

            // ResetStrategies destroys this AcceptInvitationAction. Queue the
            // rebuild for the next AI tick so this Execute call can finish
            // without continuing through freed engine/action memory.
            ai->RequestStrategyReset(true, "-lfg,-bg");

            ai->Reset();

            sPlayerbotAIConfig.logEvent(ai, "AcceptInvitationAction", grp->GetLeaderName(), std::to_string(grp->GetMembersCount()));

            Player* master = inviter;
            if (Group* acceptedGroup = bot->GetGroup())
            {
                for (GroupReference* reference = acceptedGroup->GetFirstMember(); reference; reference = reference->next())
                {
                    Player* member = reference->getSource();
                    if (!member || member == bot)
                        continue;
                    RememberPartyMember(bot, member);
                    if (member->GetPlayerbotAI())
                        RememberPartyMember(member, bot);
                }
            }

            if (master->GetPlayerbotAI()) //Copy formation from bot master.
            {
                if (sPlayerbotAIConfig.inviteChat && (sRandomPlayerbotMgr.IsFreeBot(bot) || !ai->HasActivePlayerMaster()))
                {
                    std::map<std::string, std::string> placeholders;
                    placeholders["%name"] = master->GetName();
                    std::string reply;
                    if (urand(0, 3))
                        reply = BOT_TEXT2("Send me an invite %name!", placeholders);
                    else
                        reply = BOT_TEXT2("Sure I will join you.", placeholders);

                    Guild* guild = sGuildMgr.GetGuildById(bot->GetGuildId());

                    if (guild && master->IsInGuild(bot))
                        ai->SayToGuild(reply);
                    else if (sServerFacade.GetDistance2d(bot, master) < sPlayerbotAIConfig.spellDistance * 1.5)
                        ai->Say(reply);
                }

                Formation* masterFormation = MAI_VALUE(Formation*, "formation");
                FormationValue* value = (FormationValue*)context->GetValue<Formation*>("formation");
                value->Load(masterFormation->getName());
            }

            // The stock "hello" pool contains first-meeting claims.  Keep a
            // durable pair history and let Chat v2 use its existing relationship
            // and memory state to distinguish a new acquaintance from a regular.
            if (inviter->isRealPlayer())
                sPlayerbotChatDirector.ObservePartyJoin(bot, inviter);

            ai->DoSpecificAction("reset raids", event, true);
            ai->DoSpecificAction("update gear", event, true);

            return true;
        }

        virtual bool isUsefulWhenStunned() override { return true; }

#ifdef GenerateBotHelp
        virtual std::string GetHelpName() { return "accept invitation"; }
        virtual std::string GetHelpDescription()
        {
            return "This action makes the bot accept group invitations.\n"
                   "It will automatically handle AFK status and update strategies.\n"
                   "For free bots, the inviter becomes the bot's master.";
        }
        virtual std::vector<std::string> GetUsedActions() { return {"reset raids", "update gear"}; }
        virtual std::vector<std::string> GetUsedValues() { return {"formation"}; }
#endif 
    };

}
