"""Execute production consumable gating and validate per-era warrior routing."""
from pathlib import Path
import subprocess,tempfile,re
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
s=(root/'playerbot/strategy/actions/UseConsumableAction.cpp').read_text(encoding='utf-8')
method=block(s,'bool UseConsumableAction::isUseful(')
code=r'''
#include <cassert>
struct Player;
struct GroupReference{Player* member;GroupReference* following=nullptr;Player* getSource(){return member;}GroupReference* next(){return following;}};
struct Group{GroupReference* first=nullptr;GroupReference* GetFirstMember(){return first;}};
struct Player{bool combat=false,world=true,sameMap=true,taxi=false,bg=false;float distance=10;int level=40;Group* group=nullptr;
 bool IsInCombat(){return combat;}bool IsInWorld(){return world;}bool IsInMap(Player*){return sameMap;}float GetDistance(Player*){return distance;}
 Group* GetGroup(){return group;}bool IsTaxiFlying(){return taxi;}bool InBattleGround(){return bg;}int GetLevel(){return level;}};
namespace BotState{enum{BOT_STATE_COMBAT};}namespace BotCheatMask{enum{item};}
struct PlayerbotAI{bool combat=false,cheat=false;bool IsStateActive(int){return combat;}bool HasCheat(int){return cheat;}};
struct PullStrategy{bool target=false;static PullStrategy* active;static PullStrategy* Get(PlayerbotAI*){return active;}bool HasTarget()const{return target;}};PullStrategy* PullStrategy::active=nullptr;
struct {float reactDistance=60;}sPlayerbotAIConfig;
struct UseConsumableAction{Player* bot;PlayerbotAI* ai;bool isUseful();};
'''+method+r'''
int main(){Player tank,friendPlayer;PlayerbotAI ai;UseConsumableAction use{&tank,&ai};PullStrategy pull;PullStrategy::active=&pull;
 assert(use.isUseful());pull.target=true;assert(!use.isUseful());pull.target=false;
 ai.combat=true;assert(!use.isUseful());ai.combat=false;tank.combat=true;assert(!use.isUseful());tank.combat=false;
 GroupReference ref{&friendPlayer};Group group{&ref};tank.group=&group;friendPlayer.combat=true;
 assert(!use.isUseful());tank.sameMap=false;assert(use.isUseful());tank.sameMap=true;
 tank.distance=100;assert(use.isUseful());tank.distance=10;friendPlayer.world=false;assert(use.isUseful());friendPlayer.world=true;
 friendPlayer.combat=false;assert(use.isUseful());tank.taxi=true;assert(!use.isUseful());tank.taxi=false;
 ai.cheat=true;assert(!use.isUseful());ai.cheat=false;tank.level=4;assert(!use.isUseful());
}
'''
with tempfile.TemporaryDirectory(prefix='warrior-combat-guards-') as tmp:
 p=Path(tmp);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=p,check=True,capture_output=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
execute=block(s,'bool UseConsumableAction::Execute(')
assert execute.index('!isUseful() || !isPossible()') < execute.index('IsNonMeleeSpellCasted')
warrior=root/'playerbot/strategy/warrior'
arms=(warrior/'ArmsWarriorStrategy.cpp').read_text(encoding='utf-8')
fury=(warrior/'FuryWarriorStrategy.cpp').read_text(encoding='utf-8')
protection=(warrior/'ProtectionWarriorStrategy.cpp').read_text(encoding='utf-8')
for era in ['MANGOSBOT_ZERO','MANGOSBOT_ONE','MANGOSBOT_TWO']:
 a=arms.split('#ifdef '+era,1)[1].split('#endif',1)[0]
 cc=block(a,'void ArmsWarriorCcStrategy::InitCombatTriggers(')
 assert all('"'+n+'"' in cc for n in ['pummel','pummel on enemy healer','shield bash'])
w=fury.split('#ifdef MANGOSBOT_TWO',1)[1].split('#endif',1)[0]
assert all('"'+n+'"' in block(w,'void FuryWarriorAoeStrategy::InitCombatTriggers(') for n in ['whirlwind','bloodthirst'])
assert 'new TriggerNode' not in block(w,'void FuryWarriorAoeStrategy::InitNonCombatTriggers(')
w=protection.split('#ifdef MANGOSBOT_TWO',1)[1].split('#endif',1)[0]
assert re.search(r'"lose aggro",\s*NextAction::array\(0, new NextAction\("taunt"',w)
assert 'DEBUFF_TRIGGER(MortalStrike' not in (warrior/'WarriorTriggers.h').read_text(encoding='utf-8')
assert 'CAN_CAST_TRIGGER(MortalStrike' in (warrior/'WarriorTriggers.h').read_text(encoding='utf-8')
assert 'enemy is out of melee' not in (warrior/'WarriorAiObjectContext.cpp').read_text(encoding='utf-8')
assert 'WarriorSweepingStrikesPveMultiplier' not in arms
print('PASS: production consumable guards; per-era interrupts, Mortal Strike, Fury combat scheduling, Wrath taunt and registry wiring')
