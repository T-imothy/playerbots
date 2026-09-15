#include "playerbot/playerbot.h"
#include "TacticalCommands.h"
#include <limits>
#include <vector>

using namespace ai;
TacticalResult TacticalCommands::Execute(Player* owner,Unit* target,TacticalCommand const& command,
    std::function<bool(Player*)> const& authorized)
{
    TacticalResult result;
    Group* group=owner->GetGroup();
    if(!group) {result.reason="no_party";return result;}
    if(!owner->IsAlive() || !owner->IsInWorld() || owner->IsBeingTeleported()) {
        result.reason="requester_unavailable";return result;
    }
    if(!target || !target->IsInWorld() || !target->IsAlive() || !owner->IsValidAttackTarget(target)) {
        result.reason="invalid_target";return result;
    }
    if(command.intent=="interrupt" && !target->IsNonMeleeSpellCasted(true)) {
        result.reason="not_casting";return result;
    }
    std::vector<char const*> spells = command.intent=="interrupt" ?
        std::vector<char const*>{"kick","pummel","shield bash","counterspell","earth shock","silence","feral charge"} :
        std::vector<char const*>{"polymorph","shackle undead","banish","hibernate","sap","repentance","entangling roots"};
    PlayerbotAI* selected=nullptr;std::string chosen;float best=std::numeric_limits<float>::max();
    std::vector<PlayerbotAI*> party;
    unsigned examined=0;
    for(GroupReference* ref=group->GetFirstMember();ref && examined++<40;ref=ref->next()) {
        Player* candidate=ref->getSource();
        PlayerbotAI* ai=candidate ? GetBotAI(candidate) : nullptr;
        if(!ai || IsRealPlayer(candidate) || !authorized(candidate) || !candidate->IsAlive() ||
            !candidate->IsInWorld() || candidate->IsBeingTeleported() || candidate->IsTaxiFlying() ||
            candidate->HasCharmer() || candidate->GetTransport() || candidate->GetMap()!=owner->GetMap()) continue;
        party.push_back(ai);
        if(candidate->IsNonMeleeSpellCasted(true) || !candidate->IsValidAttackTarget(target)) continue;
        for(auto spell:spells) {
            if(!ai->CanCastSpell(spell,target)) continue;
            float distance=candidate->GetDistance(target);
            if(distance<best || (distance==best && selected && candidate->GetGUIDLow()<selected->GetBot()->GetGUIDLow())) {
                best=distance;selected=ai;chosen=spell;
            }
            break;
        }
    }
    if(!selected) {result.reason="no_ready_bot";return result;}
    // Native admission is checked again by CastSpell, including rank, resources,
    // range, LOS, stance and immunities. Exactly one selected bot attempts a cast.
    result.executor=selected->GetBot()->GetGUIDLow();
    result.spell=selected->GetAiObjectContext()->GetValue<uint32>("spell id",chosen)->Get();
    result.started=selected->CastSpell(chosen,target);
    result.reason=result.started ? "cast_started" : "cast_rejected";
    if(result.started && command.intent=="cc") {
        for(auto* ai:party) {
            ai->GetAiObjectContext()->GetValue<std::string>("rti cc")->Set(command.mark);
            ai->GetAiObjectContext()->GetValue<Unit*>("rti cc target")->Reset();
        }
    }
    return result;
}
