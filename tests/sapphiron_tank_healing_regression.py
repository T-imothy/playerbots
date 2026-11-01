"""Compile the actual scoped tank reservation and exercise changing native admission."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
method=block((root/'playerbot/strategy/actions/RaidHealingObjective.cpp').read_text(),'bool ai::NeedsNaxxramasTankHealing(')
code=r'''
#include <algorithm>
#include <cassert>
#include <iostream>
#include <vector>
enum{POWER_MANA};enum class BotState{BOT_STATE_COMBAT};
struct Group;struct PlayerbotAI;
struct Unit{virtual ~Unit()=default;bool world=true,alive=true,combat=true,charm=false,friendly=true,hover=false,reach=true,los=true;unsigned hp=90,maxhp=100,map=533,instance=1,entry=15989,guid=0;float distance=0;Unit*victim=nullptr;std::vector<Unit*> attackers;
virtual bool IsPlayer(){return false;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charm;}unsigned GetEntry(){return entry;}unsigned GetMapId(){return map;}unsigned GetHealth(){return hp;}unsigned GetMaxHealth(){return maxhp;}float GetHealthPercent(){return maxhp?100.f*hp/maxhp:0;}unsigned GetObjectGuid(){return guid;}Unit*GetVictim(){return victim;}bool HasAura(unsigned id){assert(id==18430);return hover;}bool CanReachWithMeleeAttack(Unit*){return reach;}const auto&getAttackers(){return attackers;}
bool IsInMap(Unit*u){return u&&world&&u->world&&map==u->map&&instance==u->instance;}float GetDistance(Unit*u){assert(IsInMap(u));return distance;}bool IsWithinLOSInMap(Unit*u){assert(IsInMap(u));return los;}};
struct Player:Unit{bool teleport=false,duel=false,tank=false,heal=true;unsigned mana=100,maxmana=100;Group*group=nullptr;PlayerbotAI*ai=nullptr;bool IsPlayer()override{return true;}bool IsBeingTeleported(){return teleport;}Group*GetGroup(){return group;}PlayerbotAI*GetPlayerbotAI(){return ai;}unsigned GetPower(unsigned){return mana;}unsigned GetMaxPower(unsigned){return maxmana;}};
struct GroupReference{Player*source;GroupReference*following=nullptr;Player*getSource(){return source;}GroupReference*next(){return following;}};
struct Group{std::vector<GroupReference> refs;GroupReference*GetFirstMember(){return refs.empty()?nullptr:&refs[0];}void Set(std::vector<Player*> roster){refs.clear();for(auto*p:roster){refs.push_back({p});p->group=this;}for(size_t i=0;i+1<refs.size();++i)refs[i].following=&refs[i+1];}};
struct PlayerbotAI{Player*bot=nullptr;bool real=false,focus=false;float range=40;Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool IsTank(Player*p){return p->tank;}bool IsHeal(Player*p){return p->heal;}bool HasStrategy(const char*,BotState){return focus;}float GetRange(const char*){return range;}};
struct{unsigned criticalHealth=20,lowMana=20;}sPlayerbotAIConfig;
struct{bool IsFriendlyTo(Unit*,Unit*u){return u->friendly;}}sServerFacade;
namespace ai{bool NeedsNaxxramasTankHealing(PlayerbotAI*,Unit*);}
__METHOD__
int main(){Group group;Player tank;Unit boss;boss.friendly=false;boss.victim=&tank;tank.tank=true;tank.heal=false;tank.attackers={&boss};Player healers[12];PlayerbotAI brains[12];std::vector<Player*>roster{&tank};
for(unsigned i=0;i<12;++i){healers[i].guid=i+1;brains[i].bot=&healers[i];healers[i].ai=&brains[i];roster.push_back(&healers[i]);}group.Set(roster);
auto need=[&](unsigned i=0){return ai::NeedsNaxxramasTankHealing(&brains[i],&tank);};
#ifdef MANGOSBOT_ZERO
for(unsigned i=0;i<12;++i)assert(need(i)==(i<3));std::reverse(roster.begin(),roster.end());group.Set(roster);for(unsigned i=0;i<12;++i)assert(need(i)==(i<3));
boss.hover=true;assert(!need());boss.hover=false;boss.reach=false;assert(!need());boss.reach=true;boss.victim=&healers[0];assert(!need());boss.victim=&tank;boss.entry=16011;assert(!need());boss.entry=15989;
boss.entry=15953;for(unsigned i=0;i<12;++i)assert(need(i)==(i<3));
boss.hover=true;assert(need());boss.hover=false;boss.entry=16505;assert(!need());boss.entry=15989;
boss.combat=false;assert(!need());boss.combat=true;boss.charm=true;assert(!need());boss.charm=false;boss.instance=2;assert(!need());boss.instance=1;
tank.hp=100;assert(!need());tank.hp=90;tank.tank=false;assert(!need());tank.tank=true;tank.duel=true;assert(!need());tank.duel=false;tank.teleport=true;assert(!need());tank.teleport=false;tank.group=nullptr;assert(!need());tank.group=&group;tank.instance=2;assert(!need());tank.instance=1;
for(bool*flag:{&healers[0].teleport,&healers[0].charm,&healers[0].duel,&brains[0].real,&brains[0].focus}){*flag=true;assert(!need());*flag=false;}
for(bool*flag:{&healers[0].world,&healers[0].alive,&healers[0].combat,&healers[0].heal,&healers[0].los}){*flag=false;assert(!need());*flag=true;}
healers[0].hp=19;assert(!need());healers[0].hp=90;healers[0].mana=20;assert(!need());healers[0].mana=100;healers[0].distance=41;assert(!need());healers[0].distance=40;assert(need());healers[0].distance=0;
healers[0].map=409;assert(!need());healers[0].map=533;assert(!ai::NeedsNaxxramasTankHealing(&brains[0],nullptr));
// Loss of a reserved healer reallocates deterministically without increasing the cap.
healers[0].alive=false;assert(need(3)&&!need(4));healers[0].alive=true;
group.Set({&tank,&healers[0],&healers[1],&healers[2],&healers[3]});assert(need()&&!need(1));
group.Set({&tank,&healers[1]});assert(need(1));healers[1].mana=0;assert(!need(1));
#else
for(unsigned i=0;i<12;++i)assert(!need(i));
#endif
std::cout<<"PASS: Sapphiron native holder/ground phase, bounded healer assignment, resource/range/LOS/ownership and era isolation\n";}
'''.replace('__METHOD__',method)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='sapphiron-healing-') as d:
  p=Path(d);(p/'test.cpp').write_text(code)
  result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
  if result.returncode:raise RuntimeError(result.stdout+result.stderr)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
