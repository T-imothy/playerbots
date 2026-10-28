"""Actual Gluth duty and Mortal Wound relief selection in all three eras."""
from pathlib import Path
import subprocess
import tempfile

root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/GluthRoleActions.cpp').read_text()
source='\n'.join(line for line in source.splitlines() if not line.startswith('#include'))
code=r'''
#include <algorithm>
#include <cassert>
#include <iostream>
#include <map>
#include <set>
#include <string>
#include <vector>
constexpr unsigned CLASS_HUNTER=3,CLASS_MAGE=8,UNIT_CREATED_BY_SPELL=1,UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL=1;
using uint32=unsigned;
struct ObjectGuid{unsigned id=0;bool operator<(ObjectGuid o)const{return id<o.id;}};
struct Unit;struct Player;struct PlayerbotAI;struct Group;
struct AuraHolder{unsigned stacks=0;unsigned GetStackAmount()const{return stacks;}};
struct Unit{ObjectGuid guid{};unsigned entry=0,created=0,spawner=0;bool world=true,alive=true,sameMap=true,combat=true,charmed=false,player=false;
 float hp=100,distance=10;Unit*victim=nullptr;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 bool IsPlayer(){return player;}unsigned GetEntry(){return entry;}ObjectGuid GetObjectGuid(){return guid;}Unit*GetVictim(){return victim;}
 float GetHealthPercent(){return hp;}float GetDistance(Unit*){return distance;}unsigned GetUInt32Value(unsigned){return created;}
 ObjectGuid GetSpawnerGuid(){return {spawner};}};
struct Map{bool regular=true;bool IsRegularDifficulty(){return regular;}};
struct Player:Unit{PlayerbotAI*brain=nullptr;Group*group=nullptr;Map map;Unit*charm=nullptr;unsigned mapId=533,cls=1;
 bool tank=false,heal=false,transfer=false,locked=false,casting=false;std::map<unsigned,AuraHolder>auras;
 Player(){player=true;}bool IsBeingTeleported(){return transfer;}bool IsInMap(Unit*u){return u&&u->sameMap;}
 Group*GetGroup(){return group;}Map*GetMap(){return &map;}unsigned GetMapId(){return mapId;}unsigned getClass(){return cls;}
 PlayerbotAI*GetPlayerbotAI(){return brain;}Unit*GetCharm(){return charm;}bool hasUnitState(unsigned){return locked;}
 bool IsNonMeleeSpellCasted(bool){return casting;}const AuraHolder*GetSpellAuraHolder(unsigned id){auto i=auras.find(id);return i==auras.end()?nullptr:&i->second;}};
struct GroupReference{Player*source;GroupReference*following=nullptr;Player*getSource(){return source;}GroupReference*next(){return following;}};
struct Group{std::vector<GroupReference>refs;void set(std::initializer_list<Player*>members){refs.clear();for(auto*p:members){refs.push_back({p});p->group=this;}
 for(size_t i=1;i<refs.size();++i)refs[i-1].following=&refs[i];}GroupReference*GetFirstMember(){return refs.empty()?nullptr:&refs[0];}};
struct PlayerbotAI{Player bot;bool real=false;std::set<std::string>known,ready;std::map<unsigned,Unit*>units;
 PlayerbotAI(){bot.brain=this;}Player*GetBot(){return &bot;}bool IsRealPlayer(){return real;}bool IsTank(Player*p){return p->tank;}
 bool IsHeal(Player*p){return p->heal;}bool HasSpell(std::string s){return known.count(s);}
 bool CanCastSpell(std::string s,Unit*,unsigned){return known.count(s)&&ready.count(s);}
 Unit*GetUnit(ObjectGuid g){auto i=units.find(g.id);return i==units.end()?nullptr:i->second;}};
namespace ai{Player*GluthKiter(PlayerbotAI*,Unit*);bool GluthTankRelief(PlayerbotAI*,Unit*);}
__SOURCE__
int main(){using namespace ai;PlayerbotAI main,relief,third,hunter,mage;Player human;Group group;
 main.bot.guid={1};relief.bot.guid={2};third.bot.guid={3};hunter.bot.guid={4};mage.bot.guid={5};human.guid={6};
 main.bot.tank=relief.bot.tank=third.bot.tank=true;hunter.bot.cls=CLASS_HUNTER;mage.bot.cls=CLASS_MAGE;
 hunter.known={"concussive shot"};mage.known={"frostbolt"};
 Unit boss,chow,trigger;boss.entry=15932;boss.victim=&main.bot;chow.entry=16360;chow.created=28217;chow.spawner=20;trigger.entry=15384;
 for(auto*a:{&main,&relief,&third,&hunter,&mage})a->units[20]=&trigger;
 group.set({&main.bot,&relief.bot,&third.bot,&hunter.bot,&mage.bot,&human});
 assert(GluthKiter(&main,&boss)==&third.bot); // Established third-tank assignment preserved in every era.
 human.victim=&chow;chow.victim=&human;assert(GluthKiter(&main,&boss)==&human); // Actual human-owned duty not stolen.
 human.heal=true;assert(GluthKiter(&main,&boss)==&third.bot);human.heal=false;
 chow.created=0;assert(GluthKiter(&main,&boss)==&third.bot);chow.created=28217;
 trigger.entry=1;assert(GluthKiter(&main,&boss)==&third.bot);trigger.entry=15384;
 chow.hp=5;assert(GluthKiter(&main,&boss)==&third.bot);chow.hp=100;human.victim=nullptr;chow.victim=nullptr;
 group.set({&main.bot,&relief.bot,&hunter.bot,&mage.bot,&human});
#ifdef MANGOSBOT_TWO
 assert(GluthKiter(&main,&boss)==&hunter.bot);hunter.known.clear();assert(GluthKiter(&main,&boss)==&mage.bot);
 hunter.known={"concussive shot"};hunter.bot.heal=true;assert(GluthKiter(&main,&boss)==&mage.bot);hunter.bot.heal=false;
 hunter.real=true;assert(GluthKiter(&main,&boss)==&mage.bot);hunter.real=false;
 hunter.bot.transfer=true;assert(GluthKiter(&main,&boss)==&mage.bot);hunter.bot.transfer=false;
 hunter.bot.locked=true;assert(GluthKiter(&main,&boss)==&mage.bot);hunter.bot.locked=false;
 main.bot.map.regular=false;assert(!GluthKiter(&main,&boss));main.bot.map.regular=true;
 constexpr unsigned wound=54378,wrongWound=25646;
#else
 assert(!GluthKiter(&main,&boss));constexpr unsigned wound=25646,wrongWound=54378;
#endif
 main.bot.auras[wrongWound]={4};assert(!GluthTankRelief(&relief,&boss));main.bot.auras.clear();
 main.bot.auras[wound]={3};assert(!GluthTankRelief(&relief,&boss));
 main.bot.auras[wound]={4};relief.known=relief.ready={"taunt"};assert(GluthTankRelief(&relief,&boss));
 assert(!GluthTankRelief(&main,&boss));
 relief.ready.clear();assert(!GluthTankRelief(&relief,&boss));relief.ready={"taunt"};
 relief.bot.auras[wound]={2};assert(!GluthTankRelief(&relief,&boss));relief.bot.auras[wound]={1};assert(GluthTankRelief(&relief,&boss));
 relief.bot.auras.clear();relief.bot.casting=true;assert(!GluthTankRelief(&relief,&boss));relief.bot.casting=false;
 relief.bot.transfer=true;assert(!GluthTankRelief(&relief,&boss));relief.bot.transfer=false;
 relief.bot.alive=false;assert(!GluthTankRelief(&relief,&boss));relief.bot.alive=true;
 relief.real=true;assert(!GluthTankRelief(&relief,&boss));relief.real=false;
 relief.bot.charm=&chow;assert(!GluthTankRelief(&relief,&boss));relief.bot.charm=nullptr;
 relief.known=relief.ready={"righteous defense"};assert(GluthTankRelief(&relief,&boss));
 boss.victim=&relief.bot;assert(!GluthTankRelief(&main,&boss));boss.victim=&main.bot;
 group.set({&main.bot,&relief.bot,&third.bot,&hunter.bot,&mage.bot,&human});
 third.known=third.ready={"taunt"};relief.ready.clear();assert(!GluthTankRelief(&third,&boss)); // Never steal assigned kiter.
 boss.combat=false;assert(!GluthKiter(&main,&boss)&&!GluthTankRelief(&relief,&boss));boss.combat=true;
 main.bot.mapId=409;assert(!GluthKiter(&main,&boss));main.bot.mapId=533;
 boss.sameMap=false;assert(!GluthKiter(&main,&boss)&&!GluthTankRelief(&relief,&boss));boss.sameMap=true;
 std::cout<<"PASS Gluth native era kiter election, human duty, actual Mortal Wound relief and native taunt readiness\n";
}
'''.replace('__SOURCE__',source)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='gluth-roles-') as folder:
        p=Path(folder);(p/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
        subprocess.run([str(p/'test.exe')],cwd=p,check=True)
