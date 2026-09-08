"""Compile actual healer support decisions with controlled native interfaces."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]/'playerbot'
header=(root/'strategy/actions/HealerSupportActions.h').read_text()
implementation=(root/'strategy/actions/HealerSupportActions.cpp').read_text()
code=r"""
#include <cassert>
#include <cstdint>
#include <string>
#include <set>
#include <vector>
#include <algorithm>
using uint32=uint32_t;using uint64=uint64_t;
enum {POWER_MANA=0,CLASS_DRUID=11,CURRENT_CHANNELED_SPELL=1};
struct Group;
struct SpellEntry {uint32 Id=64901;};
struct Spell {SpellEntry* m_spellInfo;};
struct Unit {virtual ~Unit()=default;bool world=true,alive=true;uint32 maximum=100;float health=100;int map=1;bool wound=false;uint32 absorb=0;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}uint32 GetMaxHealth(){return maximum;}float GetHealthPercent(){return health;}};
struct Player:Unit {bool safe=true,teleport=false,friendly=true,tank=false,moving=false;void* duel=nullptr;float distance=0;uint32 phase=1,mana=10,maxMana=100,cls=7;int duration=99,interrupts=0;Group* group=nullptr;Spell* channel=nullptr;std::set<int> attackers;std::set<std::string> mine,auras;
 bool IsBeingTeleported(){return teleport;}bool IsInMap(Unit*u){return u&&map==u->map;}bool IsInGroup(Player*p);uint32 GetPhaseMask(){return phase;}Group* GetGroup(){return group;}
 const std::set<int>& getAttackers(){return attackers;}uint32 getClass(){return cls;}uint32 GetMaxPower(int){return maxMana;}uint32 GetPower(int){return mana;}
 Spell* GetCurrentSpell(int){return channel;}void InterruptSpell(int){channel=nullptr;++interrupts;}};
struct GroupReference {Player* player=nullptr;GroupReference* following=nullptr;Player* getSource(){return player;}GroupReference* next(){return following;}};
struct Group {GroupReference refs[4];GroupReference* GetFirstMember(){return &refs[0];}void set(Player*a,Player*b,Player*c=nullptr,Player*d=nullptr){Player*v[]={a,b,c,d};for(int i=0;i<4;++i){refs[i].player=v[i];refs[i].following=i<3?&refs[i+1]:nullptr;if(v[i])v[i]->group=this;}}};
bool Player::IsInGroup(Player*p){return p&&group&&group==p->group;}
struct Config {uint32 lowHealth=50,criticalHealth=25,mediumHealth=70,lowMana=25;}sPlayerbotAIConfig;
struct PlayerbotAI {Player* bot;Player* master=nullptr;Unit* patient=nullptr;bool baseUseful=true,nsReady=true;int casts=0;std::set<std::string> learned;
 Player* GetBot(){return bot;}Player* GetMaster(){return master;}bool IsSafe(Player*p){return p&&p->safe;}bool HasSpell(std::string s){return learned.count(s);}
 bool HasMyAura(std::string s,Player*p){return p->mine.count(s);}bool HasAura(std::string s,Unit*u){auto p=dynamic_cast<Player*>(u);return p&&(p->mine.count(s)||p->auras.count(s));}
 bool IsTank(Player*p){return p->tank;}bool CanCastSpell(std::string s,Player*,unsigned){return HasSpell(s)&&nsReady;}
 struct TargetValue{Unit* value;Unit* Get(){return value;}} cached;
 PlayerbotAI* GetAiObjectContext(){return this;}template<class T>TargetValue* GetValue(std::string){cached.value=patient;return &cached;}};
struct Facade {bool IsFriendlyTo(Player*,Player*p){return p->friendly;}float GetDistance2d(Player*,Player*p){return p->distance;}bool isMoving(Player*p){return p->moving;}}sServerFacade;
#define AI_VALUE(type,key) (ai->patient)
struct Event {};
struct NextAction {std::string name;NextAction(std::string s):name(s){}static NextAction** array(int,NextAction*a,NextAction*){auto p=new NextAction*[2]{a,nullptr};return p;}static NextAction** merge(NextAction**a,NextAction**b){std::vector<NextAction*> v;for(auto p:{a,b})if(p)for(int i=0;p[i];++i)v.push_back(p[i]);auto r=new NextAction*[v.size()+1]{};std::copy(v.begin(),v.end(),r);return r;}};
struct Action {PlayerbotAI*ai;Player*bot;int duration=1000;std::string name;Action(PlayerbotAI*a,std::string n):ai(a),bot(a->bot),name(n){}virtual~Action()=default;virtual bool isUseful(){return true;}virtual bool Execute(Event&){return true;}virtual std::string getName(){return name;}void SetDuration(int n){duration=n;}};
struct CastBuffSpellAction:Action {float range=40;CastBuffSpellAction(PlayerbotAI*a,std::string n):Action(a,n){}std::string GetSpellName(){return name;}virtual std::string GetTargetName(){return "self target";}virtual Unit*GetTarget(){return GetTargetName()=="self target"?bot:ai->patient;}bool isUseful()override{return ai->baseUseful&&ai->HasSpell(name)&&GetTarget()&&!ai->HasAura(name,GetTarget());}bool Execute(Event&)override{++ai->casts;return true;}virtual NextAction**getPrerequisites(){return nullptr;}};
using CastHealingSpellAction=CastBuffSpellAction;
namespace ai {bool NeedsFullHealingToRemoveAura(Unit*u){return u->wound;}uint32 RemainingHealingAbsorb(Unit*u){return u->absorb;}}
"""
code+='\n'.join(l for l in header.splitlines() if not l.startswith(('#include','#pragma')))+'\n'
code+='\n'.join(l for l in implementation.splitlines() if not l.startswith('#include'))+'\n'
code+=r"""
int main(){
 Player bot,master,tank,other;Group group;group.set(&bot,&master,&tank,&other);PlayerbotAI ai{&bot};ai.master=&master;ai.patient=&master;
 ai.learned={"earth shield","prayer of mending","beacon of light","sacred shield","nature's swiftness","regrowth","healing wave","tidal force","hymn of hope"};
 for(std::string spell:{"earth shield","prayer of mending","beacon of light","sacred shield"}){
  tank.tank=true;assert(ai::SelectHealerSupportTarget(&ai,spell,40)==&tank);
  master.mine.insert(spell);master.distance=100;assert(!ai::SelectHealerSupportTarget(&ai,spell,40));master.mine.clear();master.distance=0;
  other.auras.insert(spell);assert(ai::SelectHealerSupportTarget(&ai,spell,40)==&tank);other.auras.clear();
  tank.auras.insert(spell);assert(ai::SelectHealerSupportTarget(&ai,spell,40)==&master);tank.auras.clear();
  ai.learned.erase(spell);assert(!ai::SelectHealerSupportTarget(&ai,spell,40));ai.learned.insert(spell);
 }
 tank.tank=false;other.attackers.insert(1);assert(ai::SelectHealerSupportTarget(&ai,"earth shield",40)==&other);other.attackers.clear();
 assert(ai::SelectHealerSupportTarget(&ai,"earth shield",40)==&master);
 tank.tank=true;
 for(int failure=0;failure<8;++failure){
  switch(failure){case 0:tank.alive=false;break;case 1:tank.world=false;break;case 2:tank.teleport=true;break;case 3:tank.map=2;break;case 4:tank.friendly=false;break;case 5:tank.duel=&other;break;case 6:tank.distance=41;break;case 7:tank.safe=false;break;}
  assert(ai::SelectHealerSupportTarget(&ai,"earth shield",40)==&master);
  tank.alive=tank.world=tank.friendly=tank.safe=true;tank.teleport=false;tank.map=1;tank.duel=nullptr;tank.distance=0;
 }
#ifdef MANGOSBOT_TWO
 tank.phase=2;assert(ai::SelectHealerSupportTarget(&ai,"earth shield",40)==&master);tank.phase=1;
#endif
 group.set(&bot,nullptr);assert(!ai::SelectHealerSupportTarget(&ai,"earth shield",40));group.set(&bot,&master,&tank,&other);
 master.health=20;assert(ai::HasHealingPressure(&ai,25));master.health=100;assert(!ai::HasHealingPressure(&ai,25));
 master.absorb=100;assert(ai::HasHealingPressure(&ai,25));master.absorb=0;master.wound=true;assert(ai::HasHealingPressure(&ai,25));master.wound=false;
 ai::CastUrgentHealingBuffAction ns(&ai,"nature's swiftness");assert(!ns.isUseful());master.health=20;assert(ns.isUseful());ai.baseUseful=false;assert(!ns.isUseful());ai.baseUseful=true;
 ai::CastNaturesSwiftnessHealAction heal(&ai,"healing wave",true);assert(heal.isUseful());ai.nsReady=false;assert(!heal.isUseful());bot.mine.insert("nature's swiftness");assert(heal.isUseful());bot.mine.clear();ai.nsReady=true;
 ai.learned.erase("nature's swiftness");assert(!heal.isUseful());ai.learned.insert("nature's swiftness");master.health=50;assert(!heal.isUseful());master.health=20;
 auto p=heal.getPrerequisites();assert(p[0]->name=="nature's swiftness"&&!p[1]);bot.cls=CLASS_DRUID;p=heal.getPrerequisites();assert(p[0]->name=="restoration caster form"&&p[1]->name=="nature's swiftness"&&!p[2]);
 ai::CastSelfAndPartyHealingAction binding(&ai,"binding heal");ai.learned.insert("binding heal");assert(!binding.isUseful());bot.health=40;assert(binding.isUseful());ai.patient=&bot;assert(!binding.isUseful());ai.patient=nullptr;assert(!binding.isUseful());ai.patient=&master;ai.baseUseful=false;assert(!binding.isUseful());ai.baseUseful=true;bot.health=100;
 ai::CastUrgentHealingBuffAction tidal(&ai,"tidal force");assert(!tidal.isUseful());master.health=40;assert(tidal.isUseful());master.health=100;assert(!tidal.isUseful());
#ifdef MANGOSBOT_TWO
 ai::CastHymnOfHopeAction hymn(&ai);Event event;assert(hymn.isUseful());bot.moving=true;assert(!hymn.isUseful());bot.moving=false;bot.attackers.insert(1);assert(!hymn.isUseful());bot.attackers.clear();
 master.health=60;assert(!hymn.isUseful());assert(!hymn.Execute(event));assert(ai.casts==0);master.health=100;
 bot.mana=80;assert(!hymn.isUseful());bot.mana=10;assert(hymn.Execute(event));assert(ai.casts==1);
 SpellEntry entry{64901};Spell channel{&entry};bot.channel=&channel;ai::StopHymnOfHopeAction stop(&ai);assert(!stop.isUseful());master.health=20;assert(stop.isUseful());assert(stop.Execute(event));assert(bot.interrupts==1&&!bot.channel&&stop.duration==0);
 entry.Id=64843;bot.channel=&channel;assert(!stop.isUseful());assert(!stop.Execute(event));assert(bot.interrupts==1);bot.channel=nullptr;
#endif
}
"""
for mode in ('MANGOSBOT_ZERO','MANGOSBOT_ONE','MANGOSBOT_TWO'):
 with tempfile.TemporaryDirectory(prefix='healer-support-') as tmp:
  p=Path(tmp);(p/'test.cpp').write_text(code)
  result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/D'+mode,str(p/'test.cpp'),'/Fe:'+str(p/'test.exe'),'/Fo:'+str(p/'test.obj')],capture_output=True,text=True)
  if result.returncode:raise SystemExit(result.stdout+result.stderr)
  subprocess.run([str(p/'test.exe')],check=True)
 print('PASS '+mode+': maintained assignments, talent/cooldown gates, invalid targets, urgent heal prerequisites and mana-channel safety')
