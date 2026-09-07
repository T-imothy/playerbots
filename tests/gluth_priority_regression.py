"""Execute Gluth targeting against native summon and Decimate contracts."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
method=block((root/'playerbot/strategy/actions/GluthTargetAction.cpp').read_text(),'Unit* DungeonAddTargetAction::GetGluthTarget(')
code=r'''
#include <cassert>
#include <cmath>
#include <list>
#include <map>
#include <string>
#include <iostream>
using ObjectGuid=unsigned;
enum{UNIT_CREATED_BY_SPELL};
struct Unit{unsigned entry=0,guid=0,hp=100,maxhp=100,phase=1,created=28217,spawner=0;
 bool world=true,alive=true,charmed=false,combat=true,player=false,valid=true,breakCC=false,assignedCC=false;float x=0;Unit* victim=nullptr;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool HasCharmer(){return charmed;}bool IsInCombat(){return combat;}bool IsPlayer(){return player;}
 unsigned GetEntry(){return entry;}unsigned GetObjectGuid(){return guid;}unsigned GetMaxHealth(){return maxhp;}unsigned GetHealth(){return hp;}
 unsigned GetUInt32Value(unsigned field){assert(field==UNIT_CREATED_BY_SPELL);return created;}unsigned GetSpawnerGuid(){return spawner;}
 float GetDistance(Unit*u){return std::abs(x-u->x);}Unit* GetVictim(){return victim;}};
struct Group{};
struct Player:Unit{Player(){player=true;}unsigned map=533;bool teleport=false;Group* group=nullptr;
 unsigned GetMapId(){return map;}Group* GetGroup(){return group;}bool IsBeingTeleported(){return teleport;}bool IsInMap(Unit*u){return u&&u->phase==phase;}};
struct PlayerbotAI{Player* bot;Unit* current=nullptr;std::map<unsigned,Unit*> units;std::list<unsigned> near;
 Unit* GetUnit(unsigned id){return units.count(id)?units[id]:nullptr;}
 template<class T>T value(std::string name){assert(name=="current target");return current;}
 template<class T>T qualified(std::string name,std::string qualifier){assert(name=="possible targets"&&qualifier=="100:1");return near;}};
struct Config{float sightDistance=60;}sPlayerbotAIConfig;
struct PossibleTargetsValue{static bool IsValid(Unit*u,Player*,bool){return u->valid;}};
struct PossibleAttackTargetsValue{static bool IsPossibleTarget(Unit*u,Player*b,float range,bool ignore){assert(ignore);return !u->assignedCC&&b->GetDistance(u)<=range;}
 static bool HasBreakableCC(Unit*u,Player*){return u->breakCC;}};
struct DungeonAddTargetAction{PlayerbotAI* ai;Player* bot;Unit* GetGluthTarget();};
#define AI_VALUE(type,key) ai->value<type>(key)
#define AI_VALUE2(type,key,q) ai->qualified<type>(key,q)
__METHOD__
int main(){Group group,other;Player bot,tank;bot.group=tank.group=&group;PlayerbotAI ai{&bot};DungeonAddTargetAction a{&ai,&bot};
 Unit boss,trigger,chow,nearer,duplicate;boss.entry=15932;boss.guid=1;boss.victim=&tank;
 trigger.entry=15384;trigger.guid=2;trigger.combat=false;trigger.x=50;
 chow.entry=16360;chow.guid=3;chow.spawner=2;chow.x=40;chow.maxhp=10000;chow.hp=10000;chow.combat=false;
 ai.units={{1,&boss},{2,&trigger},{3,&chow}};ai.near={1,3}; // Nonattackable trigger resolved by actual spawner GUID.
 assert(!a.GetGluthTarget());chow.hp=501;assert(a.GetGluthTarget()==&chow);chow.hp=502;assert(!a.GetGluthTarget());chow.hp=500;
 nearer=chow;nearer.guid=4;nearer.x=20;ai.units[4]=&nearer;ai.near.push_back(4);ai.current=&chow;
 assert(a.GetGluthTarget()==&nearer);chow.x=23;assert(a.GetGluthTarget()==&chow);chow.x=24;assert(a.GetGluthTarget()==&nearer);
 nearer.breakCC=true;assert(a.GetGluthTarget()==&chow);nearer.breakCC=false;
 ai.near.pop_back();chow.assignedCC=true;assert(!a.GetGluthTarget());chow.assignedCC=false;
 chow.breakCC=true;assert(!a.GetGluthTarget());chow.breakCC=false;chow.valid=false;assert(!a.GetGluthTarget());chow.valid=true;
 chow.created=1;assert(!a.GetGluthTarget());chow.created=28217;chow.spawner=1;assert(!a.GetGluthTarget());chow.spawner=2;
 trigger.world=false;assert(!a.GetGluthTarget());trigger.world=true;trigger.phase=2;assert(!a.GetGluthTarget());trigger.phase=1;
 trigger.x=101;assert(!a.GetGluthTarget());trigger.x=50;chow.x=61;assert(!a.GetGluthTarget());chow.x=24;
 boss.combat=false;assert(!a.GetGluthTarget());boss.combat=true;boss.victim=&bot;assert(!a.GetGluthTarget());boss.victim=&tank;
 tank.group=&other;assert(!a.GetGluthTarget());tank.group=&group;tank.teleport=true;assert(!a.GetGluthTarget());tank.teleport=false;
 duplicate=boss;duplicate.guid=5;ai.units[5]=&duplicate;ai.near.push_back(5);assert(!a.GetGluthTarget());ai.near.pop_back();
 bot.map=0;assert(!a.GetGluthTarget());bot.map=533;bot.teleport=true;assert(!a.GetGluthTarget());bot.teleport=false;
 chow.hp=0;chow.alive=false;assert(!a.GetGluthTarget());chow.alive=true;chow.hp=500;assert(a.GetGluthTarget()==&chow);
 std::cout<<"PASS: weakened zombie rescue, actual trigger ownership, passive adds, threat order, CC and lifecycle\n";
}
'''.replace('__METHOD__',method)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-gluth-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
dispatcher=(root/'playerbot/strategy/actions/DungeonAddTargetAction.cpp').read_text()
assert dispatcher.index('ai->IsHeal(bot)')<dispatcher.index('GetGluthTarget()')
assert dispatcher.index('commanded(ai->GetUnit')<dispatcher.index('GetGluthTarget()')
for era in ('classic','tbc','wotlk'):
    core=root.parent/f'mangos-{era}-behavior/src/game'
    native=next((core/'AI/ScriptDevAI/scripts').rglob('boss_gluth.cpp')).read_text()
    assert 'GetMaxHealth() * 0.05f' in native and '28217' in native
    assert 'SetUInt32Value(UNIT_CREATED_BY_SPELL, m_spellInfo->Id)' in (core/'Spells/SpellEffects.cpp').read_text()
    if era=='wotlk': assert 'unitTarget->AttackStop(true, true)' in native
print('PASS: all-era native Decimate/summon evidence and role/manual-target dispatcher gates')
