"""Production Fade/threat policy and per-expansion action routing regressions."""
from pathlib import Path
import subprocess,tempfile,re
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
priest=root/'playerbot/strategy/priest'
fade=block((priest/'PriestActions.cpp').read_text(),'bool CastFadeAction::isUseful(')
threat=block((root/'playerbot/strategy/generic/ThreatStrategy.cpp').read_text(),'float ThreatMultiplier::GetValue(')
code=r'''
#include <cassert>
using uint8=unsigned char;
#include <cstddef>
#include <string>
struct Unit{float health=100;float GetHealthPercent(){return health;}};
struct Session{void SendPlaySpellVisual(unsigned,unsigned){}};
struct Player:Unit{bool grouped=true,combat=true;Session session;bool GetGroup(){return grouped;}bool IsInCombat(){return combat;}Session* GetSession(){return &session;}unsigned GetObjectGuid(){return 1;}};
enum class BotState{BOT_STATE_COMBAT};
struct PlayerbotAI{Player* bot;bool group=true;bool HasStrategy(const char*,BotState){return false;}Player* GetMaster(){return bot;}Player* GetBot(){return bot;}};
enum class ActionThreatType{ACTION_THREAT_NONE,ACTION_THREAT_LOW,ACTION_THREAT_SINGLE,ACTION_THREAT_AOE};
struct Action{Unit* target=nullptr;ActionThreatType kind=ActionThreatType::ACTION_THREAT_AOE;virtual ~Action()=default;virtual ActionThreatType getThreatType(){return kind;}virtual Unit* GetTarget(){return target;}};
struct CastHealingSpellAction:Action{};
struct CastBuffSpellAction:Action{bool allowed=true;virtual bool isUseful(){return allowed;}};
struct CastFadeAction:CastBuffSpellAction{Player* bot;PlayerbotAI* ai;bool isUseful()override;};
struct ThreatMultiplier{PlayerbotAI* ai;float GetValue(Action*);};
struct {float lowHealth=50;}sPlayerbotAIConfig;
Unit enemy;float ownThreat=0;
struct ThreatValue{static float GetThreat(Player*,Unit*){return ownThreat;}};
template<class T>T value(const char*){if constexpr(sizeof(T)==sizeof(Unit*))return &enemy;else return true;}
#define AI_VALUE(T,N) value<T>(N)
#define AI_VALUE2(T,N,Q) T(100)
'''+fade+'\n'+threat+r'''
int main(){Player bot;PlayerbotAI ai{&bot};CastFadeAction fade;fade.bot=&bot;fade.ai=&ai;
 assert(!fade.isUseful());ownThreat=10;assert(fade.isUseful());fade.allowed=false;assert(!fade.isUseful());fade.allowed=true;
 bot.combat=false;assert(!fade.isUseful());bot.combat=true;bot.grouped=false;assert(!fade.isUseful());bot.grouped=true;
 ThreatMultiplier multiplier{&ai};CastHealingSpellAction heal;Unit patient;heal.target=&patient;
 patient.health=20;assert(multiplier.GetValue(&heal)==1);patient.health=75;assert(multiplier.GetValue(&heal)==0);
 Action damage;damage.target=&patient;assert(multiplier.GetValue(&damage)==0);damage.kind=ActionThreatType::ACTION_THREAT_LOW;assert(multiplier.GetValue(&damage)==1);
 assert(multiplier.GetValue(nullptr)==1);
}
'''
with tempfile.TemporaryDirectory(prefix='priest-combat-') as tmp:
 p=Path(tmp);(p/'test.cpp').write_text(code)
 result=subprocess.run(['cl','/nologo','/std:c++17','/EHsc','test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
 if result.returncode:raise RuntimeError(result.stdout+result.stderr)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
actions=(priest/'PriestActions.h').read_text();triggers=(priest/'PriestTriggers.h').read_text()
assert 'SPELL_ACTION(CastShadowfiendAction, "shadowfiend")' in actions
assert 'RANGED_DEBUFF_ENEMY_ACTION(CastVampiricTouchActionOnAttacker, "vampiric touch")' in actions
assert 'BUFF_ACTION(CastShadowfiendAction' not in actions
for text,clazz,wrath,older in [(actions,'CastVampiricEmbraceAction','BUFF_ACTION','RANGED_DEBUFF_ACTION'),(triggers,'VampiricEmbraceTrigger','BUFF_TRIGGER','DEBUFF_TRIGGER'),(actions,'CastPrayerOfHealingAction','AOE_HEAL_ACTION','HEAL_ACTION')]:
 assert re.search(r'#ifdef MANGOSBOT_TWO\s+'+wrath+r'\('+clazz+r',.*?#else\s+'+older+r'\('+clazz+r',',text,re.S)
for clazz in ['CastManaBurnAction','CastStarshardsAction']:
 assert re.search(clazz+r', [^\n]*CastSpellAction::isUseful\(\)',actions)
factory=(priest/'PriestStrategy.cpp').read_text()
for name in ['prayer_of_healing','binding_heal','prayer_of_mending','divine_hymn']:
 assert re.search(r'ACTION_NODE_P\('+name+r', "[^"]+", "remove shadowform"\)',factory)
print('PASS: zero-threat Fade, native/base eligibility, urgent healing under low-threat behavior, priest spell identities and expansion-specific targeting')
