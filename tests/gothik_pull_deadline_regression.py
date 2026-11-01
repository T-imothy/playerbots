"""Actual request deadline: Gothik preparation remains bounded; other pulls unchanged."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/generic/PullStrategy.cpp').read_text()
code=r'''
#include <cassert>
#include <iostream>
using uint8=unsigned char;
struct Unit{bool world=true;unsigned map=533,entry=16060;bool IsInWorld(){return world;}unsigned GetEntry(){return entry;}};
struct Player:Unit{unsigned GetMapId(){return map;}bool IsInMap(Unit*u){return map==u->map;}};
struct PlayerbotAI{Player*bot;Player*GetBot(){return bot;}};
struct PullStrategy{PlayerbotAI*ai;Unit*target;bool encounterPreparationAllowed=true;
 Unit*GetTarget()const{return target;}uint8 GetMaxPullTime()const;};
'''+block(source,'uint8 PullStrategy::GetMaxPullTime() const')+r'''
int main(){
 Player bot;Unit boss;PlayerbotAI ai{&bot};PullStrategy pull{&ai,&boss};
#ifdef MANGOSBOT_ZERO
 assert(pull.GetMaxPullTime()==60);
 // The same original request remains alive during role crossing at 20s,
 // expires at 60s, and never receives a moving/renewed deadline.
 for(unsigned elapsed:{0u,15u,20u,59u})assert(elapsed<pull.GetMaxPullTime());
 assert(60>=pull.GetMaxPullTime());assert(pull.GetMaxPullTime()==60);
#else
 assert(pull.GetMaxPullTime()==15);
#endif
 pull.encounterPreparationAllowed=false;assert(pull.GetMaxPullTime()==15);pull.encounterPreparationAllowed=true;
 boss.entry=16061;assert(pull.GetMaxPullTime()==15);boss.entry=16060;
 bot.map=409;assert(pull.GetMaxPullTime()==15);bot.map=533;
 boss.map=469;assert(pull.GetMaxPullTime()==15);boss.map=533;
 boss.world=false;assert(pull.GetMaxPullTime()==15);boss.world=true;
 bot.world=false;assert(pull.GetMaxPullTime()==15);bot.world=true;
 pull.target=nullptr;assert(pull.GetMaxPullTime()==15);pull.target=&boss;
 ai.bot=nullptr;assert(pull.GetMaxPullTime()==15);
 std::cout<<"PASS bounded explicit Classic Gothik preparation, invalid lifecycle and other maps/eras unchanged\n";
}
'''
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='gothik-deadline-') as folder:
  path=Path(folder);(path/'test.cpp').write_text(code)
  result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
  if result.returncode:print(result.stdout,result.stderr)
  result.check_returncode();subprocess.run([str(path/'test.exe')],cwd=path,check=True)
