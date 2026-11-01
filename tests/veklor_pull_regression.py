"""Actual pull spell selection; no boss immunity or ordinary pull bypass."""
from pathlib import Path
from behavior_regression import block
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/generic/PullStrategy.cpp').read_text()
method=block(source,'std::string PullStrategy::GetPullActionName() const')
code=r'''
#include <cassert>
#include <iostream>
#include <set>
#include <string>
enum{CLASS_DRUID=11,CLASS_WARLOCK=9};enum class BotState{BOT_STATE_COMBAT};
struct Unit {unsigned entry=15276,instance=1;bool world=true,alive=true,charm=false;
 unsigned GetEntry(){return entry;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool HasCharmer(){return charm;}};
struct Player:Unit {unsigned map=531,cls=CLASS_WARLOCK;unsigned GetMapId(){return map;}unsigned getClass(){return cls;}
 bool IsInMap(Unit*u){return u&&instance==u->instance;}};
struct PlayerbotAI {Player*bot;std::set<std::string>known;bool feral=false;
 Player*GetBot(){return bot;}bool HasSpell(std::string s){return known.count(s);}bool HasStrategy(std::string,BotState){return feral;}};
struct PullStrategy {PlayerbotAI*ai;bool bodyPull=false;std::string pullActionName="shoot";Unit*target=nullptr;
 Unit*GetTarget()const{return target;}std::string GetPullActionName()const;};
__METHOD__
int main(){Player bot;Unit boss;PlayerbotAI ai{&bot,{"searing pain","shadow bolt"}};PullStrategy s{&ai};s.target=&boss;
#ifdef MANGOSBOT_ZERO
 assert(s.GetPullActionName()=="searing pain");ai.known.erase("searing pain");assert(s.GetPullActionName()=="shadow bolt");
 ai.known.clear();assert(s.GetPullActionName()=="shoot");ai.known={"searing pain","shadow bolt"};
 boss.instance=2;assert(s.GetPullActionName()=="shoot");boss.instance=1;
 boss.world=false;assert(s.GetPullActionName()=="shoot");boss.world=true;
 boss.alive=false;assert(s.GetPullActionName()=="shoot");boss.alive=true;
 boss.charm=true;assert(s.GetPullActionName()=="shoot");boss.charm=false;
#else
 assert(s.GetPullActionName()=="shoot");
#endif
 boss.entry=15275;assert(s.GetPullActionName()=="shoot");boss.entry=15276;
 bot.map=409;assert(s.GetPullActionName()=="shoot");bot.map=531;
 bot.cls=1;assert(s.GetPullActionName()=="shoot");bot.cls=CLASS_WARLOCK;
 s.target=nullptr;assert(s.GetPullActionName()=="shoot");s.target=&boss;
 s.bodyPull=true;assert(s.GetPullActionName()=="melee");s.bodyPull=false;
 s.pullActionName="corruption";assert(s.GetPullActionName()=="corruption");
 bot.cls=CLASS_DRUID;s.pullActionName="faerie fire";ai.known={"faerie fire (feral)"};ai.feral=true;
 assert(s.GetPullActionName()=="faerie fire (feral)");
 std::cout<<"PASS selected Veklor magical pull, learned fallback, identity/lifecycle, explicit action and map/era exclusions\n";
}
'''.replace('__METHOD__',method)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='raid-veklor-pull-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
