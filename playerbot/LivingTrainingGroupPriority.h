#pragma once

// Optional autonomous grouping must not repeatedly turn a pending class lesson
// into a follower wait. Existing parties and all human-directed invitations
// retain their original behavior. The normal trainer predicates own eligibility.
inline bool LivingWowDeferBotPartyForTraining(Player* candidate, Player* inviter, Group* invitedGroup = nullptr)
{
    if (!candidate || !inviter || candidate->isRealPlayer() || inviter->isRealPlayer() ||
        candidate->GetGroup()) return false;
    PlayerbotAI* candidateAI = candidate->GetPlayerbotAI();
    PlayerbotAI* inviterAI = inviter->GetPlayerbotAI();
    if (!candidateAI || !inviterAI || candidateAI->HasRealPlayerMaster() ||
        inviterAI->HasRealPlayerMaster()) return false;
    Group* group = invitedGroup ? invitedGroup : inviter->GetGroup();
    if (group)
        for (GroupReference* ref = group->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            // An unloaded member may be a human. Do not restrict that group.
            if (!member || member->isRealPlayer() || !member->GetPlayerbotAI() ||
                member->GetPlayerbotAI()->HasRealPlayerMaster()) return false;
        }
    auto* context = candidateAI->GetAiObjectContext();
    return context && context->GetValue<bool>("should travel named", "trainer class")->Get() &&
        !context->GetValue<std::vector<int32>>("available trainers", "0")->Get().empty();
}
