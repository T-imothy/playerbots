"""Run physical/caster selection and native teleport recovery admission."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
method=block((root/'playerbot/strategy/actions/TwinEmperorTargetAction.cpp').read_text(),'Unit* DungeonAddTargetAction::GetTwinEmperorTarget(')
code=r'''
#include <cassert>
#include <cmath>
#include <list>
#include <map>
#include <string>
#include <iostream>
using uint32=unsigned;using ObjectGuid=unsigned;enum{CLASS_HUNTER=3};
struct Unit{unsigned entry=0,phase=1;bool world=true,alive=true,charmed=false,combat=true,player=false,stun=false,valid=true,cc=false;float x=0;Unit*victim=nullptr;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool HasCharmer(){return charmed;}bool IsInCombat(){return combat;}bool IsPlayer(){return player;}
 unsigned GetEntry(){return entry;}bool HasAura(unsigned id){assert(id==800);return stun;}Unit*GetVictim(){return victim;}
 float GetDistance(Unit*u){return std::abs(x-u->x);}};
struct Group{};
struct Player:Unit{Player(){player=true;}unsigned map=531,cls=8;bool teleport=false;Group*group=nullptr;
 unsigned GetMapId(){return map;}unsigned getClass(){return cls;}Group*GetGroup(){return group;}
 bool IsBeingTeleported(){return teleport;}bool IsInMap(Unit*u){return u&&u->phase==phase;}};
struct PlayerbotAI{std::map<unsigned,Unit*>units;std::list<unsigned>near;bool ranged=true;
 Unit*GetUnit(unsigned id){return units.count(id)?units[id]:nullptr;}bool IsRanged(Player*){return ranged;}
 template<class T>T qualified(std::string name,std::string q){assert(name=="possible targets"&&q=="100:1");return near;}};
struct Config{float sightDistance=60;}sPlayerbotAIConfig;
struct PossibleTargetsValue{static bool IsValid(Unit*u,Player*,bool){return u->valid;}};
struct PossibleAttackTargetsValue{static bool IsPossibleTarget(Unit*u,Player*b,float r,bool ignore){assert(!ignore);return b->GetDistance(u)<=r;}
 static bool HasBreakableCC(Unit*u,Player*){return u->cc;}static bool HasUnBreakableCC(Unit*u,Player*){return u->cc;}};
struct DungeonAddTargetAction{PlayerbotAI*ai;Player*bot;Unit*GetTwinEmperorTarget();};
#define AI_VALUE2(type,name,q) ai->qualified<type>(name,q)
__METHOD__
int main(){Group group,other;Player bot,tank;bot.group=tank.group=&group;Unit physical,magic,duplicate;
 physical.entry=15275;magic.entry=15276;physical.victim=magic.victim=&tank;physical.x=10;magic.x=30;
 PlayerbotAI ai;ai.units={{1,&physical},{2,&magic}};ai.near={1,2};DungeonAddTargetAction action{&ai,&bot};
 assert(action.GetTwinEmperorTarget()==&magic);
 bot.cls=CLASS_HUNTER;assert(action.GetTwinEmperorTarget()==&physical);bot.cls=8;
 ai.ranged=false;assert(action.GetTwinEmperorTarget()==&physical);ai.ranged=true;
 magic.stun=true;assert(!action.GetTwinEmperorTarget());magic.stun=false;
 magic.victim=nullptr;assert(!action.GetTwinEmperorTarget());magic.victim=&bot;assert(!action.GetTwinEmperorTarget());magic.victim=&tank;
 tank.group=&other;assert(!action.GetTwinEmperorTarget());tank.group=&group;
 tank.teleport=true;assert(!action.GetTwinEmperorTarget());tank.teleport=false;
 magic.phase=2;assert(!action.GetTwinEmperorTarget());magic.phase=1;
 magic.cc=true;assert(!action.GetTwinEmperorTarget());magic.cc=false;
 magic.valid=false;assert(!action.GetTwinEmperorTarget());magic.valid=true;
 magic.x=70;assert(!action.GetTwinEmperorTarget());magic.x=30;
 magic.combat=false;assert(!action.GetTwinEmperorTarget());magic.combat=true;
 duplicate=magic;ai.units[3]=&duplicate;ai.near.push_back(3);assert(!action.GetTwinEmperorTarget());ai.near.pop_back();
 bot.teleport=true;assert(!action.GetTwinEmperorTarget());bot.teleport=false;
 bot.map=0;assert(!action.GetTwinEmperorTarget());bot.map=531;assert(action.GetTwinEmperorTarget()==&magic);
 std::cout<<"PASS: Twins caster/physical/hunter choices, no idle pulls, teleport recovery, group/CC/lifecycle\n";
}
'''.replace('__METHOD__',method)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='twin-emperor-target-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
dispatcher=(root/'playerbot/strategy/actions/DungeonAddTargetAction.cpp').read_text()
for gate in ('ai->IsHeal(bot)','ai->IsTank(bot)','commanded(ai->GetUnit'):
    assert dispatcher.index(gate)<dispatcher.index('GetTwinEmperorTarget()')
