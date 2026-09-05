#include "playerbot/playerbot.h"
#include "CheckMailAction.h"
#include "Mails/Mail.h"
#include "playerbot/PlayerbotAIConfig.h"

using namespace ai;

bool CheckMailAction::Execute(Event& event)
{
    WorldPacket packet;
    bot->GetSession()->HandleQueryNextMailTime(packet);

    // Returning mail can change in-memory mail lists; iterate stable IDs.
    std::vector<uint32> ids;
    for (auto it = bot->GetMailBegin(); it != bot->GetMailEnd(); ++it)
        if (*it)
            ids.push_back((*it)->messageID);
    for (uint32 id : ids)
        if (Mail* mail = bot->GetMail(id))
            ProcessMail(mail);
    // A completed scan with nothing eligible is not a failed action.
    return true;
}

bool CheckMailAction::isUseful()
{
    return !ai->GetMaster() && bot->GetMailSize() && !bot->InBattleGround() && !bot->IsInCombat();
}

bool CheckMailAction::ProcessMail(Mail* mail)
{
    if (!mail || mail->state == MAIL_STATE_DELETED || mail->deliver_time > time(nullptr) ||
        mail->messageType != MAIL_NORMAL || !mail->sender || mail->mailTemplateId ||
        (mail->checked & MAIL_CHECK_MASK_RETURNED) ||
        mail->subject.find("Item(s) you asked for") != std::string::npos ||
        mail->subject.find("Item(s) you've sent me") != std::string::npos)
        return false;

    const ObjectGuid senderGuid(HIGHGUID_PLAYER, mail->sender);
    const uint32 senderAccount = sObjectMgr.GetPlayerAccountIdByGUID(senderGuid);
    if (!senderAccount || senderGuid == bot->GetObjectGuid() || sPlayerbotAIConfig.IsInRandomAccountList(senderAccount))
        return false;

    // Leave text-only mail alone. Validate every attachment before taking any.
    if (mail->items.empty() && !mail->money)
        return false;
    for (const MailItemInfo& entry : mail->items)
        if (!bot->GetMItem(entry.item_guid))
            return false;

    MailDraft draft;
#ifdef MANGOSBOT_TWO
    draft.SetSubjectAndBody(mail->subject, mail->body);
#else
    draft.SetSubjectAndBodyId(mail->subject, mail->itemTextId);
#endif
    for (const MailItemInfo& entry : mail->items)
        draft.AddItem(bot->GetMItem(entry.item_guid));

    const uint32 id = mail->messageID;
    draft.SetMoney(mail->money).SetReturnSourceMailId(id);
    draft.SendReturnToSender(bot->GetSession()->GetAccountId(), bot->GetObjectGuid(), senderGuid);

    for (const MailItemInfo& entry : mail->items)
        bot->RemoveMItem(entry.item_guid);
    bot->RemoveMail(id);
    delete mail;
    bot->SendMailResult(id, MAIL_RETURNED_TO_SENDER, MAIL_OK);
    return true;
}
