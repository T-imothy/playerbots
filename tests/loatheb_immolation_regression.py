"""Actual live Loatheb lookup and optional splash-aura removal selection."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
source=(Path(__file__).resolve().parents[1]/"playerbot/strategy/actions/ClassicRaidActions.cpp").read_text()
code=r"""
#include <cassert>
#include <iostream>
#include <vector>
#include <list>
#include <set>
#include <map>
using uint32=unsigned;using ObjectGuid=unsigned;
constexpr unsigned SPELL_AURA_DAMAGE_SHIELD=15;
struct Aura{unsigned id=9910;bool positive=true;bool IsPositive()const{return positive;}unsigned GetId()const{return id;}};
struct Unit{bool world=true,alive=true,combat=true;unsigned entry=16011,map=533,instance=1;unsigned GetEntry(){return entry;}};
struct Player:Unit{std::set<unsigned>auras;std::vector<Aura*>shields;unsigned GetMapId(){return map;}bool HasAura(unsigned id){return auras.count(id);}
 bool IsInMap(Unit*u){return u&&map==u->map&&instance==u->instance;}auto&GetAurasByType(unsigned type){assert(type==15);return shields;}};
struct Value{std::list<unsigned>list;auto Get(){return list;}};
struct Context{Value value;template<class T>Value*GetValue(const char*,const char*){return &value;}};
struct PlayerbotAI{Player bot;Context context;bool ready=true;std::map<unsigned,Unit*>units;
 Player*GetBot(){return &bot;}Context*GetAiObjectContext(){return &context;}Unit*GetUnit(unsigned id){return units.count(id)?units[id]:nullptr;}};
bool Ready(PlayerbotAI*a){return a->ready;}bool threat=true;
bool Engaged(Player*p,Unit*u){return threat&&u&&u->world&&u->alive&&u->combat&&p->IsInMap(u);}
namespace classicraid{bool Boss(unsigned map,unsigned entry){return map==533&&entry==16011;}}
__BODY__
int main(){PlayerbotAI ai;Unit boss;ai.units[1]=&boss;ai.context.value.list={1};
 // No instance storage exists in this fixture, matching native Classic Loatheb.
 assert(LoathebImmolationUnsafe(&ai));
 ai.ready=false;assert(!LoathebImmolationUnsafe(&ai));ai.ready=true;
 for(unsigned map:{0u,409u,489u,469u}){ai.bot.map=map;assert(!LoathebImmolationUnsafe(&ai));}ai.bot.map=533;
 ai.context.value.list.clear();assert(!LoathebImmolationUnsafe(&ai));ai.context.value.list={1};
 boss.entry=11583;assert(!LoathebImmolationUnsafe(&ai));boss.entry=16011;
 boss.instance=2;assert(!LoathebImmolationUnsafe(&ai));boss.instance=1;
 boss.world=false;assert(!LoathebImmolationUnsafe(&ai));boss.world=true;
 boss.alive=false;assert(!LoathebImmolationUnsafe(&ai));boss.alive=true;
 boss.combat=false;assert(!LoathebImmolationUnsafe(&ai));boss.combat=true;
 threat=false;assert(!LoathebImmolationUnsafe(&ai));threat=true;
 Aura thorns{9910,true},negative{999,false};ai.bot.shields={&thorns,&negative};ai.bot.auras={11350,12328,13877,10901};
#ifdef MANGOSBOT_ZERO
 assert(LoathebPersistentDamageAuras(&ai)==std::vector<unsigned>({11350,12328,13877,9910}));
 ai.ready=false;assert(LoathebPersistentDamageAuras(&ai).empty());ai.ready=true;
 ai.bot.auras={10901};ai.bot.shields={&negative};assert(LoathebPersistentDamageAuras(&ai).empty());
#else
 assert(LoathebPersistentDamageAuras(&ai).empty());
#endif
 std::cout<<"PASS native Loatheb live lookup without instance registry, positive splash only, lifecycle/scope and era guards\n";
}
""".replace("__BODY__","\n".join(block(source,signature)for signature in (
 "    Unit* FindBoss(PlayerbotAI* ai, uint32 entry)\n",
 "    bool LoathebImmolationUnsafe(", "    std::vector<uint32> LoathebPersistentDamageAuras(")))
for era in ("ZERO","ONE","TWO"):
 with tempfile.TemporaryDirectory(prefix="loatheb-immolation-") as directory:
  p=Path(directory);(p/"test.cpp").write_text(code)
  subprocess.run(["cl","/nologo","/EHsc","/std:c++17","/DMANGOSBOT_"+era,"test.cpp","/Fe:test.exe"],cwd=p,check=True)
  subprocess.run([str(p/"test.exe")],cwd=p,check=True)
