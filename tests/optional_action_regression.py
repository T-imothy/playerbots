"""Exercise production optional-action bodies with controlled bot interfaces."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1] / 'playerbot/strategy/actions'
res = (root / 'ReleaseSpiritAction.h').read_text()
loot = (root / 'AddLootAction.cpp').read_text()
code = r'''
#include <cassert>
#include <list>
#include <string>
using ObjectGuid = unsigned;
enum class BotState { BOT_STATE_DEAD };
enum { PLAYER_SELF_RES_SPELL, CMSG_SELF_RES };
struct WorldPacket { WorldPacket(int) {} };
struct Event {};
struct Session { int calls=0; void HandleSelfResOpcode(WorldPacket&) { ++calls; } };
struct Player { unsigned spell=0; Session session;
 unsigned GetUInt32Value(int) { return spell; } Session* GetSession() { return &session; } };
struct PlayerbotAI { Player* bot; bool dead=false;
 bool IsStateActive(BotState) { return dead; } };
struct ChatCommandAction { PlayerbotAI* ai; Player* bot;
 ChatCommandAction(PlayerbotAI* a, std::string):ai(a),bot(a->bot) {}
 virtual bool isUseful() { return true; } virtual bool isPossible() { return true; }
 virtual bool Execute(Event&) { return false; } };
struct Value { std::list<ObjectGuid> data; auto& Get() { return data; } };
struct Context { Value objects, corpses;
 template<class T> Value* GetValue(std::string name) {
  return name=="nearest corpses" ? &corpses : &objects;
 } };
struct AddAllLootAction {
 Context* context; int scans=0; bool added=false;
 virtual bool isUseful() { return true; }
 virtual bool Execute(Event&) { ++scans; return added; }
};
struct AddGatheringLootAction : AddAllLootAction {
 bool isUseful() override; bool Execute(Event&) override;
};
'''
code += block(res, 'class SelfResurrectAction') + ';\n'
code += block(loot, 'bool AddGatheringLootAction::isUseful()') + '\n'
code += block(loot, 'bool AddGatheringLootAction::Execute(Event& event)') + '\n'
code += r'''
int main() {
 Player bot; PlayerbotAI ai{&bot}; Event event; SelfResurrectAction res(&ai);
 // Alive or dead without a resurrection source must not dispatch the opcode.
 for (bool dead : {false,true}) for (unsigned spell : {0u,123u}) {
  ai.dead=dead; bot.spell=spell;
  assert(res.isUseful()==(dead && spell!=0));
  assert(res.isPossible()==(dead && spell!=0));
  if (res.isUseful() && res.isPossible()) assert(res.Execute(event));
 }
 assert(bot.session.calls==1);
 Context context; AddGatheringLootAction gather; gather.context=&context;
 assert(!gather.isUseful());
 // Corpses alone must still permit skinning discovery.
 context.corpses.data.push_back(1); assert(gather.isUseful());
 assert(gather.Execute(event)); assert(gather.scans==1);
 context.corpses.data.clear(); context.objects.data.push_back(2);
 assert(gather.isUseful());
 // An empty/filtered scan succeeds; a scan adding loot still succeeds.
 gather.added=false; assert(gather.Execute(event));
 gather.added=true; assert(gather.Execute(event)); assert(gather.scans==3);
 context.objects.data.clear(); assert(!gather.isUseful());
}
'''
with tempfile.TemporaryDirectory(prefix='optional-actions-') as tmp:
    p = Path(tmp)
    (p / 'test.cpp').write_text(code)
    result = subprocess.run(['cl', '/nologo', '/EHsc', '/std:c++17',
        str(p / 'test.cpp'), '/Fe:' + str(p / 'test.exe'),
        '/Fo:' + str(p / 'test.obj')], capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(result.stdout + result.stderr)
    subprocess.run([str(p / 'test.exe')], check=True)
print('PASS: resurrection eligibility, empty discovery, corpse discovery and scan outcomes')
