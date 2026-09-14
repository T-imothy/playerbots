#include "playerbot/playerbot.h"
#include "TurtleClassStrategy.h"
using namespace ai;
void TurtleClassStrategy::InitCombatTriggers(std::list<TriggerNode*>& triggers)
{
    if (!ai || !ai->GetBot()) return;
    switch (ai->GetBot()->getClass())
    {
    case 1:
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("master strike", ACTION_NORMAL + 3), NULL)));
        break;
    case 2:
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("bulwark of the righteous", ACTION_HIGH + 3), NULL)));
        break;
    case 3:
        triggers.push_back(new TriggerNode("melee medium aoe", NextAction::array(0, new NextAction("carve", ACTION_NORMAL + 4), NULL)));
        break;
    case 4:
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("detection", ACTION_NORMAL + 3), NULL)));
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("surprise attack", ACTION_NORMAL + 4), NULL)));
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("noxious assault", ACTION_NORMAL + 3), NULL)));
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("mark for death", ACTION_NORMAL + 5), NULL)));
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("shadow of death", ACTION_HIGH + 3), NULL)));
        triggers.push_back(new TriggerNode("panic", NextAction::array(0, new NextAction("smoke bomb", ACTION_EMERGENCY + 10), NULL)));
        break;
    case 5:
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("pain spike", ACTION_NORMAL + 3), NULL)));
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("searing shot", ACTION_NORMAL + 3), NULL)));
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("light of an'she", ACTION_NORMAL + 3), NULL)));
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("enlighten", ACTION_HIGH + 2), NULL)));
        triggers.push_back(new TriggerNode("party member critical health", NextAction::array(0, new NextAction("ascendance", ACTION_CRITICAL_HEAL + 1), NULL)));
        triggers.push_back(new TriggerNode("critical health", NextAction::array(0, new NextAction("ascendance", ACTION_CRITICAL_HEAL + 1), NULL)));
        break;
    case 7:
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("earthshaker slam", ACTION_HIGH + 2), NULL)));
        triggers.push_back(new TriggerNode("ranged medium aoe", NextAction::array(0, new NextAction("earthquake", ACTION_NORMAL + 4), NULL)));
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("lightning strike", ACTION_NORMAL + 3), NULL)));
        triggers.push_back(new TriggerNode("party member critical health", NextAction::array(0, new NextAction("ancestral swiftness", ACTION_CRITICAL_HEAL + 1), NULL)));
        triggers.push_back(new TriggerNode("critical health", NextAction::array(0, new NextAction("ancestral swiftness", ACTION_CRITICAL_HEAL + 1), NULL)));
        triggers.push_back(new TriggerNode("party member low health", NextAction::array(0, new NextAction("spirit link", ACTION_MEDIUM_HEAL + 1), NULL)));
        break;
    case 8:
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("arcane surge", ACTION_NORMAL + 3), NULL)));
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("arcane rupture", ACTION_NORMAL + 3), NULL)));
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("icicles", ACTION_NORMAL + 2), NULL)));
        break;
    case CLASS_DRUID:
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("savage bite", ACTION_NORMAL + 3), NULL)));
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("barkskin (feral)", ACTION_HIGH + 3), NULL)));
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("reshift", ACTION_HIGH + 3), NULL)));
        break;
    case 9:
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("use felstone", ACTION_HIGH + 2), NULL)));
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("use voidstone", ACTION_HIGH + 2), NULL)));
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("use wrathstone", ACTION_HIGH + 2), NULL)));
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("dark harvest", ACTION_NORMAL + 2), NULL)));
        triggers.push_back(new TriggerNode("timer", NextAction::array(0, new NextAction("power overwhelming", ACTION_HIGH + 2), NULL)));
        break;
    }
}
void TurtleClassStrategy::InitNonCombatTriggers(std::list<TriggerNode*>& triggers)
{
    if (!ai || !ai->GetBot()) return;
    if (ai->GetBot()->getClass() == CLASS_WARLOCK)
    {
        triggers.push_back(new TriggerNode("very often", NextAction::array(0, new NextAction("create felstone", ACTION_NORMAL), NULL)));
        triggers.push_back(new TriggerNode("very often", NextAction::array(0, new NextAction("create voidstone", ACTION_NORMAL), NULL)));
        triggers.push_back(new TriggerNode("very often", NextAction::array(0, new NextAction("create wrathstone", ACTION_NORMAL), NULL)));
    }
    if (ai->GetBot()->getClass() == CLASS_ROGUE)
        triggers.push_back(new TriggerNode("very often", NextAction::array(0, new NextAction("detection", ACTION_NORMAL), NULL)));
    if (ai && ai->GetBot() && ai->GetBot()->getClass() == CLASS_DRUID)
        triggers.push_back(new TriggerNode("very often", NextAction::array(0, new NextAction("tree of life form", ACTION_NORMAL + 1), NULL)));
}
