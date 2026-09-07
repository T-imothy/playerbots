"""Compile actual trio balancing and fake-death transition targeting."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
method=block((root/'playerbot/strategy/actions/ThekalTargetAction.cpp').read_text(),'Unit* DungeonAddTargetAction::GetThekalTarget(')
code=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <list>
#include <map>
#include <string>
#include <vector>
#include <iostream>
using ObjectGuid=unsigned;
struct Unit{unsigned entry=0,guid=0,hp=100,maxhp=100,phase=1;bool world=true,alive=true,charmed=false,combat=true,player=false,tiger=false,valid=true,cc=false;float distance=0;Unit* victim=nullptr;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool HasCharmer(){return charmed;}bool IsInCombat(){return combat;}bool IsPlayer(){return player;}
 unsigned GetEntry(){return entry;}unsigned GetObjectGuid(){return guid;}unsigned GetMaxHealth(){return maxhp;}float GetHealthPercent(){return maxhp?100.f*hp/maxhp:0;}
 float GetDistance(Unit*u){return std::abs(distance-u->distance);}Unit* GetVictim(){return victim;}bool HasAura(unsigned id){return id==24169&&tiger;}};
struct Group{};
struct Player:Unit{Player(){player=true;}unsigned map=309;bool teleport=false;Group* group=nullptr;
 unsigned GetMapId(){return map;}Group* GetGroup(){return group;}bool IsBeingTeleported(){return teleport;}bool IsInMap(Unit*u){return u&&u->phase==phase;}};
struct PlayerbotAI{Player* bot;Unit* current=nullptr;std::map<unsigned,Unit*> units;std::list<unsigned> near;
 Unit* GetUnit(unsigned id){return units.count(id)?units[id]:nullptr;}
 template<class T>T value(std::string){return current;}
 template<class T>T qualified(std::string name,std::string qualifier){assert(name=="possible targets"&&qualifier=="100:1");return near;}};
struct Config{float sightDistance=60;}sPlayerbotAIConfig;
struct PossibleTargetsValue{static bool IsValid(Unit*u,Player*,bool){return u->valid;}};
struct PossibleAttackTargetsValue{static bool IsPossibleTarget(Unit*u,Player*b,float range,bool ignore){assert(!ignore);return !u->cc&&b->GetDistance(u)<=range;}
 static bool HasBreakableCC(Unit*u,Player*){return u->cc;}static bool HasUnBreakableCC(Unit*u,Player*){return u->cc;}};
struct DungeonAddTargetAction{PlayerbotAI* ai;Player* bot;Unit* GetThekalTarget();};
#define AI_VALUE(type,key) ai->value<type>(key)
#define AI_VALUE2(type,key,q) ai->qualified<type>(key,q)
__METHOD__
int main(){Group group,other;Player bot,tank;bot.group=tank.group=&group;PlayerbotAI ai{&bot};DungeonAddTargetAction a{&ai,&bot};
 Unit thekal,lorkhan,zath,duplicate;thekal.entry=14509;thekal.guid=1;lorkhan.entry=11347;lorkhan.guid=2;zath.entry=11348;zath.guid=3;
 for(Unit*u:{&thekal,&lorkhan,&zath}){u->victim=&tank;ai.units[u->guid]=u;ai.near.push_back(u->guid);}
 assert(a.GetThekalTarget()==&thekal);thekal.hp=70;assert(a.GetThekalTarget()==&lorkhan);
 ai.current=&zath;zath.hp=96;assert(a.GetThekalTarget()==&zath);zath.hp=94;assert(a.GetThekalTarget()==&lorkhan);
 thekal.hp=9;lorkhan.hp=4;zath.hp=10;assert(a.GetThekalTarget()==&lorkhan);
 lorkhan.hp=1;lorkhan.valid=false;lorkhan.victim=nullptr;assert(a.GetThekalTarget()==&zath); // Native fake-death actor stays identifiable.
 zath.hp=1;zath.valid=false;zath.victim=nullptr;assert(a.GetThekalTarget()==&thekal);
 thekal.tiger=true;assert(!a.GetThekalTarget());thekal.tiger=false;
 thekal.cc=true;assert(!a.GetThekalTarget());thekal.cc=false;
 tank.group=&other;assert(!a.GetThekalTarget());tank.group=&group;tank.teleport=true;assert(!a.GetThekalTarget());tank.teleport=false;
 tank.alive=false;assert(!a.GetThekalTarget());tank.alive=true;
 ai.units.erase(2);assert(!a.GetThekalTarget());ai.units[2]=&lorkhan;
 duplicate=thekal;duplicate.guid=4;ai.units[4]=&duplicate;ai.near.push_back(4);assert(!a.GetThekalTarget());ai.near.pop_back();
 thekal.phase=2;assert(!a.GetThekalTarget());thekal.phase=1;thekal.distance=70;assert(!a.GetThekalTarget());thekal.distance=0;
 bot.map=0;assert(!a.GetThekalTarget());bot.map=309;bot.teleport=true;assert(!a.GetThekalTarget());bot.teleport=false;
 assert(a.GetThekalTarget()==&thekal);
 std::cout<<"PASS: trio health balance/hysteresis, low-health finish, fake deaths, tiger phase and lifecycle\n";
}
'''.replace('__METHOD__',method)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-thekal-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
dispatcher=(root/'playerbot/strategy/actions/DungeonAddTargetAction.cpp').read_text()
assert dispatcher.index('ai->IsHeal(bot)')<dispatcher.index('GetThekalTarget()')
assert dispatcher.index('commanded(ai->GetUnit')<dispatcher.index('GetThekalTarget()')
for era in ('classic','tbc','wotlk'):
    native=(root.parent/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/zulgurub/boss_thekal.cpp').read_text()
    assert 'SetStandState(UNIT_STAND_STATE_DEAD)' in native and 'SetDeathPrevention(true)' in native
    assert 'SPELL_TIGER_FORM        = 24169' in native
print('PASS: dispatcher preserves manual/healer/tank controls and all native fake-death scripts')
