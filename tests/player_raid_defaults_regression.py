"""Execute actual raid/default selector and config application boundary."""
from pathlib import Path
import re,subprocess,tempfile
from behavior_regression import block
source=(Path(__file__).resolve().parents[1]/'playerbot/AiFactory.cpp').read_text()
selector=block(source,'bool UsePlayerRaidCombatDefaults(')
autonomous=block(source,'bool UseAutonomousNonCombatDefaults(')
application=re.search(r'combatEngine->ChangeStrategy\(UsePlayerRaidCombatDefaults.*?;',source,re.S).group()
nc_start=source.index('if (UseAutonomousNonCombatDefaults(player, facade))')
nc_application=source[nc_start:source.index('// Battleground switch',nc_start)]
code=r'''
#include <cassert>
#include <string>
#include <iostream>
#include <set>
struct Player {bool group=true,bg=false,ai=true;unsigned map=409;bool GetGroup(){return group;}bool InBattleGround(){return bg;}unsigned GetMapId(){return map;}bool GetPlayerbotAI(){return ai;}};
struct PlayerbotAI {bool active=true,real=false,leader=false;Player master;bool HasActivePlayerMaster(){return active;}bool HasRealPlayerMaster(){return active;}bool IsRealPlayer(){return real;}bool IsGroupLeader(){return leader;}Player*GetMaster(){return &master;}};
struct Config {std::string combatStrategies="+custom::say",randomBotCombatStrategies="+dps,+dps assist,-threat",nonCombatStrategies="+buff",randomBotNonCombatStrategies="+rpg";bool randomBotJoinLfg=true,autoDoQuests=true,randomBotJoinBG=true,autonomousTravel=true;}sPlayerbotAIConfig;
struct {bool free=true;bool IsFreeBot(Player*){return free;}}sRandomPlayerbotMgr;
unsigned urand(unsigned,unsigned){return 1;}
struct Engine {std::string last;std::set<std::string>strategies;void ChangeStrategy(const std::string&s){last=s;}void addStrategy(const char*s){strategies.insert(s);}};
'''+selector+'\n'+autonomous+'\nvoid Apply(Player* player,PlayerbotAI* facade,Engine* combatEngine){'+application+'}\nvoid ApplyNonCombat(Player* player,PlayerbotAI* facade,Engine* nonCombatEngine){'+nc_application+'}\n'+r'''
int main(){Player p;PlayerbotAI ai;Engine e;
 assert(!UsePlayerRaidCombatDefaults(nullptr,&ai));assert(!UsePlayerRaidCombatDefaults(&p,nullptr));
 for(unsigned map:{409u,249u,469u,533u,309u,509u,531u}){
  p.map=map;Apply(&p,&ai,&e);assert(e.last==sPlayerbotAIConfig.combatStrategies);
  e=Engine();ApplyNonCombat(&p,&ai,&e);
#ifdef MANGOSBOT_ZERO
  assert(e.last==sPlayerbotAIConfig.nonCombatStrategies&&e.strategies.count("grind")==0&&e.strategies.count("travel")==0);
#else
  assert(e.last==sPlayerbotAIConfig.randomBotNonCombatStrategies&&e.strategies.count("grind")==1);
#endif
  ai.active=false;e=Engine();ApplyNonCombat(&p,&ai,&e);assert(e.strategies.count("grind")==1);ai.active=true;
  p.group=false;Apply(&p,&ai,&e);assert(e.last==sPlayerbotAIConfig.randomBotCombatStrategies);p.group=true;
  ai.active=false;Apply(&p,&ai,&e);assert(e.last==sPlayerbotAIConfig.randomBotCombatStrategies);ai.active=true;
  p.bg=true;Apply(&p,&ai,&e);assert(e.last==sPlayerbotAIConfig.randomBotCombatStrategies);p.bg=false;
 }
 for(unsigned map:{0u,1u,30u,489u,529u,429u,230u,209u,530u,571u}){
  p.map=map;Apply(&p,&ai,&e);assert(e.last==sPlayerbotAIConfig.randomBotCombatStrategies);
  e=Engine();ApplyNonCombat(&p,&ai,&e);assert(e.strategies.count("grind")==1);
 }
 p.bg=true;e=Engine();ApplyNonCombat(&p,&ai,&e);assert(e.strategies.count("grind")==0);p.bg=false;
 p.map=409;p.group=false;e=Engine();ApplyNonCombat(&p,&ai,&e);assert(e.strategies.count("grind")==1);p.group=true;
 sPlayerbotAIConfig.combatStrategies="+heal,+custom::say";p.map=409;
 Apply(&p,&ai,&e);assert(e.last=="+heal,+custom::say");
 std::cout<<"PASS actual combat/noncombat defaults: player-led raids do not grind, solo/bot-led/dungeons/BG and other-era noncombat unchanged\n";
}
'''
with tempfile.TemporaryDirectory(prefix='raid-defaults-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 for era in ('ZERO','ONE','TWO'):
  result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
  if result.returncode:print(result.stdout,result.stderr)
  result.check_returncode();subprocess.run([str(path/'test.exe')],cwd=path,check=True)
