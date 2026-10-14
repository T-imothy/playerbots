"""Compile the native-victim Firewalker healing predicate across all three cores."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
R=Path(__file__).resolve().parents[1]
method=block((R/'playerbot/strategy/actions/RaidHealingObjective.cpp').read_text(),'bool ai::NeedsMoltenCoreBurstHealing(')
code=r'''
#include <cassert>
#include <iostream>
#include <vector>
struct Group{};struct Player;
struct Unit{virtual ~Unit()=default;bool world=true,alive=true,charm=false,combat=true,friendly=true;unsigned hp=99,maxhp=100,map=409,instance=1,phase=1,entry=11666;Unit*victim=nullptr;std::vector<Unit*>attackers;
 virtual bool IsPlayer(){return false;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool HasCharmer(){return charm;}bool IsInCombat(){return combat;}
 unsigned GetHealth(){return hp;}unsigned GetMaxHealth(){return maxhp;}unsigned GetEntry(){return entry;}const auto&getAttackers(){return attackers;}Unit*GetVictim(){return victim;}};
struct Player:Unit{bool teleport=false,duel=false,tank=false;Group*group=nullptr;bool IsPlayer()override{return true;}unsigned GetMapId(){return map;}bool IsBeingTeleported(){return teleport;}Group*GetGroup(){return group;}
 bool IsInMap(Unit*u){return u&&world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}};
struct PlayerbotAI{Player*bot;bool real=false;Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool IsTank(Player*p){return p->tank;}};
struct Facade{bool IsFriendlyTo(Unit*,Unit*u){return u->friendly;}}sServerFacade;
namespace ai{bool NeedsMoltenCoreBurstHealing(PlayerbotAI*,Unit*);}
__METHOD__
int main(){Player healer,tank;Group group;healer.group=tank.group=&group;tank.tank=true;Unit fire;fire.friendly=false;fire.victim=&tank;tank.attackers={&fire};PlayerbotAI brain{&healer};
 auto need=[&]{return ai::NeedsMoltenCoreBurstHealing(&brain,&tank);};assert(need());tank.hp=100;assert(!need());tank.hp=99;
 fire.victim=&healer;assert(!need());fire.victim=&tank;fire.entry=11667;assert(!need());fire.entry=11666;
 fire.combat=false;assert(!need());fire.combat=true;fire.alive=false;assert(!need());fire.alive=true;fire.world=false;assert(!need());fire.world=true;
 fire.friendly=true;assert(!need());fire.friendly=false;fire.charm=true;assert(!need());fire.charm=false;
 tank.teleport=true;assert(!need());tank.teleport=false;tank.instance=2;assert(!need());tank.instance=1;tank.phase=2;assert(!need());tank.phase=1;
 tank.tank=false;assert(!need());tank.tank=true;tank.duel=true;assert(!need());tank.duel=false;tank.group=nullptr;assert(!need());tank.group=&group;
 healer.map=1;assert(!need());healer.map=409;brain.real=true;assert(!need());brain.real=false;healer.teleport=true;assert(!need());healer.teleport=false;
 assert(need());tank.attackers.clear();assert(!need());assert(!ai::NeedsMoltenCoreBurstHealing(&brain,nullptr));
 std::cout<<"PASS: Firewalker actual victim, injured tank priority and world/instance/phase/control/group safety\n";
}
'''.replace('__METHOD__',method)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='firewalker-heal-') as d:
  p=Path(d);(p/'test.cpp').write_text(code)
  r=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
  if r.returncode:raise RuntimeError(r.stdout+r.stderr)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
