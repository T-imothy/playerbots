"""Exercise the production Infusion selector against native-interface fixtures."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block
r=Path(__file__).resolve().parents[1]
body=block((r/'playerbot/strategy/priest/PowerInfusionTarget.h').read_text(encoding='utf-8'),'inline Unit* SelectPowerInfusionTarget(')
code=r'''
#include <cassert>
#include <list>
#include <map>
#include <set>
#include <string>
#include <iostream>
using uint8=unsigned char;using uint64=unsigned long long;using ObjectGuid=unsigned;
enum{POWER_MANA,CLASS_WARRIOR=1,CLASS_HUNTER=3,CLASS_PRIEST=5,CLASS_SHAMAN=7,CLASS_MAGE=8,CLASS_WARLOCK=9,CLASS_DRUID=11};
struct Group;struct Map{bool raid=true;bool IsRaid(){return raid;}};
struct Unit{virtual ~Unit()=default;bool world=true,alive=true,combat=true,teleport=false,safe=true,friendly=true,legal=true;unsigned instance=1,guid=0;std::set<std::string>auras;Group*group=nullptr;
bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool IsBeingTeleported(){return teleport;}bool IsInMap(Unit*u){return u&&world&&u->world&&instance==u->instance;}
bool IsInGroup(Unit*u){return u==this||(group&&group==u->group);}unsigned GetObjectGuid(){return guid;}};
struct Player:Unit{bool healer=false,tank=false,ranged=true;unsigned cls=CLASS_PRIEST,mana=100,maxMana=100;Map map;
Group*GetGroup(){return group;}Map*GetMap(){return &map;}unsigned getClass(){return cls;}unsigned GetPower(int){return mana;}unsigned GetMaxPower(int){return maxMana;}};
struct GroupReference{Player*player;GroupReference*following=nullptr;Player*getSource(){return player;}GroupReference*next(){return following;}};
struct Group{bool raid=true;std::list<GroupReference>refs;bool IsRaidGroup(){return raid;}GroupReference*GetFirstMember(){return refs.empty()?nullptr:&refs.front();}
void Add(Player*p){p->group=this;if(!refs.empty()){auto&old=refs.back();refs.push_back({p});old.following=&refs.back();}else refs.push_back({p});}};
template<class T>struct Cached{T value;T Get(){return value;}};struct Context{Cached<std::list<ObjectGuid>>assigned;template<class T>Cached<T>*GetValue(const char*){return &assigned;}};
struct{unsigned lowHealth=40;}sPlayerbotAIConfig;
struct{bool IsFriendlyTo(Player*,Unit*u){return u->friendly;}}sServerFacade;
struct PlayerbotAI{Player*bot;Context context;bool learned=true,ready=true,pressure=false;std::map<unsigned,Unit*>units;
Player*GetBot(){return bot;}bool HasSpell(const char*){return learned;}Context*GetAiObjectContext(){return &context;}Unit*GetUnit(unsigned g){return units.count(g)?units[g]:nullptr;}
bool HasAura(const char*n,Unit*u){return u->auras.count(n);}bool CanCastSpell(const char*,Unit*u,int){return ready&&u->legal&&!u->teleport;}bool IsSafe(Unit*u){return u->safe;}
bool IsHeal(Player*p){return p->healer;}bool IsTank(Player*p){return p->tank;}bool IsRanged(Player*p){return p->ranged;}};
namespace ai{bool HasHealingPressure(PlayerbotAI*a,unsigned){return a->pressure;}
__BODY__
}
int main(){using ai::SelectPowerInfusionTarget;Player bot;bot.guid=1;bot.healer=true;PlayerbotAI a{&bot};Group group;group.Add(&bot);
Player mage,lock,balance,hunter;mage.cls=CLASS_MAGE;mage.guid=10;lock.cls=CLASS_WARLOCK;lock.guid=20;balance.cls=CLASS_DRUID;balance.guid=2;hunter.cls=CLASS_HUNTER;hunter.guid=3;
for(Player*p:{&hunter,&balance,&lock,&mage}){group.Add(p);a.units[p->guid]=p;}a.units[bot.guid]=&bot;
assert(SelectPowerInfusionTarget(&a)==&mage);mage.auras.insert("power infusion");assert(SelectPowerInfusionTarget(&a)==&lock);
lock.legal=false;assert(SelectPowerInfusionTarget(&a)==&balance);balance.healer=true;assert(!SelectPowerInfusionTarget(&a));balance.healer=false;lock.legal=true;mage.auras.clear();
mage.mana=0;assert(SelectPowerInfusionTarget(&a)==&lock);mage.mana=100;mage.instance=2;assert(SelectPowerInfusionTarget(&a)==&lock);mage.instance=1;
mage.teleport=true;assert(SelectPowerInfusionTarget(&a)==&lock);mage.teleport=false;mage.combat=false;assert(SelectPowerInfusionTarget(&a)==&lock);mage.combat=true;
mage.auras.insert("bloodlust");
#ifdef MANGOSBOT_ZERO
assert(SelectPowerInfusionTarget(&a)==&mage);
#else
assert(SelectPowerInfusionTarget(&a)==&lock);
#endif
mage.auras.clear();a.pressure=true;assert(!SelectPowerInfusionTarget(&a));a.pressure=false;a.ready=false;assert(!SelectPowerInfusionTarget(&a));a.ready=true;
a.context.assigned.value={20};assert(SelectPowerInfusionTarget(&a)==&lock);lock.alive=false;assert(!SelectPowerInfusionTarget(&a));lock.alive=true;
a.context.assigned.value={1};assert(SelectPowerInfusionTarget(&a)==&bot);a.context.assigned.value.clear();
group.raid=false;bot.map.raid=false;assert(SelectPowerInfusionTarget(&a)==&bot);group.raid=true;bot.map.raid=true;
bot.teleport=true;assert(!SelectPowerInfusionTarget(&a));bot.teleport=false;a.learned=false;assert(!SelectPowerInfusionTarget(&a));
std::cout<<"PASS: caster DPS selection, legal-target/cooldown admission, healing priority, assignment and expansion rules\n";}
'''.replace('__BODY__',body)
for file,cls in [('PriestActions.h','CastPowerInfusionAction'),('PriestTriggers.h','PowerInfusionTrigger')]:
    text=(r/'playerbot/strategy/priest'/file).read_text(encoding='utf-8')
    start=text.index('    class '+cls);end=text.index('\n    class ',start+1)
    assert 'SelectPowerInfusionTarget(ai)' in text[start:end]
    if file=='PriestTriggers.h':assert 'IsSpellReady() && GetTarget()' in text[start:end]
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='priest-infusion-') as folder:
        d=Path(folder);(d/'test.cpp').write_text(code,encoding='utf-8')
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=d,check=True)
        subprocess.run([str(d/'test.exe')],cwd=d,check=True)
