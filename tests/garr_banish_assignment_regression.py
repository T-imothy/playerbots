"""Execute native-state Garr assignment: no shared mutable bot context or threat edits."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/values/CcTargetValue.cpp').read_text()
method=block(source,'bool GarrBanishAssignment(')
code=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <list>
#include <map>
#include <set>
#include <string>
#include <vector>
using ObjectGuid=unsigned;constexpr unsigned CLASS_WARLOCK=9;
struct Unit{unsigned guid=0,entry=0,map=409,instance=1,phase=1;float x=0;
 bool world=true,alive=true,combat=true,charmed=false,friendly=false,castable=true;
 std::map<unsigned,unsigned>auras;
 unsigned GetEntry(){return entry;}ObjectGuid GetObjectGuid(){return guid;}
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 bool HasAura(unsigned id){return auras.count(id);}
 bool GetSpellAuraHolder(unsigned id,ObjectGuid caster){auto it=auras.find(id);return it!=auras.end()&&it->second==caster;}
 float GetDistance(Unit*u){return std::fabs(x-u->x);}
};
struct Player;struct PlayerbotAI;struct GroupReference{Player*member=nullptr;GroupReference*following=nullptr;
 Player*getSource(){return member;}GroupReference*next(){return following;}};
struct Group{GroupReference*first=nullptr;ObjectGuid skull=0;GroupReference*GetFirstMember(){return first;}ObjectGuid GetTargetIcon(unsigned i){assert(i==7);return skull;}};
struct Player:Unit{Group*group=nullptr;PlayerbotAI*ai=nullptr;bool teleport=false;unsigned cls=9;std::set<unsigned>spells{710};
 Group*GetGroup(){return group;}unsigned GetMapId(){return map;}bool IsBeingTeleported(){return teleport;}
 bool IsInMap(Unit*u){return u&&world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}
 unsigned getClass(){return cls;}bool HasSpell(unsigned id){return spells.count(id);}PlayerbotAI*GetPlayerbotAI(){return ai;}
};
struct AiObjectContext{Unit*mark=nullptr;std::list<ObjectGuid>possible;
 template<class T>T Read(const char*){if constexpr(std::is_same_v<T,Unit*>)return mark;else return possible;}
};
enum class BotState{BOT_STATE_COMBAT};
struct PlayerbotAI{Player*bot;AiObjectContext context;bool real=false,cc=true;std::map<ObjectGuid,Unit*>units;
 bool HasStrategy(const char*,BotState){return cc;}
 Player*GetBot(){return bot;}AiObjectContext*GetAiObjectContext(){return &context;}bool IsRealPlayer(){return real;}
 Unit*GetUnit(ObjectGuid id){auto i=units.find(id);return i==units.end()?nullptr:i->second;}
 bool CanCastSpell(std::string,Unit*u,unsigned,void*,bool,bool){return u->castable;}
};
struct{float sightDistance=60;}sPlayerbotAIConfig;
struct{bool IsFriendlyTo(Player*,Unit*u){return u->friendly;}}sServerFacade;
static std::list<Unit*>nativeAdds;
namespace MaNGOS{
 struct AllCreaturesOfEntryInRangeCheck{AllCreaturesOfEntryInRangeCheck(Unit*boss,unsigned entry,float range){assert(boss->entry==12057&&entry==12099&&range==100);}};
 template<class T>struct UnitListSearcher{std::list<Unit*>&result;UnitListSearcher(std::list<Unit*>&r,T&):result(r){}};
}
namespace Cell{template<class T>void VisitAllObjects(Unit*,T&s,float){s.result=nativeAdds;}}
#define AI_VALUE(type,key) context->Read<type>(key)
__METHOD__
int main(){
 Group group;Player first,second;first.guid=10;second.guid=20;first.group=second.group=&group;
 PlayerbotAI a{&first},b{&second};first.ai=&a;second.ai=&b;GroupReference r2{&second},r1{&first,&r2};group.first=&r1;
 Unit boss,one,two;boss.guid=1;boss.entry=12057;one.guid=2;two.guid=3;one.entry=two.entry=12099;
 nativeAdds={&two,&one};
 a.units=b.units={{1,&boss},{2,&one},{3,&two}};a.context.possible={3,1,2};b.context.possible={2,3,1};
 auto select=[](PlayerbotAI&ai){Unit*out=nullptr;assert(GarrBanishAssignment(&ai,"banish",out));return out;};
 assert(select(a)==&one&&select(b)==&two); // independent of local target iteration order
 a.context.possible={1,2};b.context.possible={1,3};assert(select(a)==&one&&select(b)==&two); // unequal local sight subsets
 one.auras={{710,10}};assert(!select(a)&&select(b)==&two); // successful cast keeps other's assignment
 two.auras={{18647,20}};assert(!select(a)&&!select(b));one.auras.clear();two.auras.clear();
 one.auras={{710,99}};assert(select(a)==&two&&!select(b));one.auras.clear(); // human-owned CC reserved
 group.skull=2;assert(select(a)==&two&&!select(b));group.skull=0;
 second.spells.clear();assert(select(a)==&one&&!select(b));second.spells={18647};assert(select(b)==&two);
 first.alive=false;assert(select(b)==&one);first.alive=true;
 first.phase=2;assert(select(b)==&one);first.phase=1;
 first.teleport=true;assert(select(b)==&one);first.teleport=false;
 first.charmed=true;assert(select(b)==&one);first.charmed=false;
 a.real=true;assert(select(b)==&one);a.real=false;
 a.cc=false;assert(select(b)==&one&&!select(a));a.cc=true;
 one.castable=false;assert(!select(a)&&select(b)==&two);one.castable=true;
 one.alive=false;assert(select(a)==&two&&!select(b));one.alive=true;
 a.context.mark=&one;Unit*out=nullptr;assert(!GarrBanishAssignment(&a,"banish",out));a.context.mark=nullptr;
 boss.combat=false;assert(!GarrBanishAssignment(&a,"banish",out));boss.combat=true;
 assert(!GarrBanishAssignment(&a,"polymorph",out));first.map=0;assert(!GarrBanishAssignment(&a,"banish",out));
 std::cout<<"PASS: separate/stable Garr banishes, human marks, native rank, lifecycle and reset gates\n";
}
'''.replace('__METHOD__',method)
for era in ('classic','tbc','wotlk'):
 native=root.parent/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/eastern_kingdoms/molten_core/boss_garr.cpp'
 text=native.read_text();assert 'SPELL_SEPARATION_ANXIETY    = 23487' in text and 'DoCastSpellIfCan(nullptr, SPELL_ERUPTION)' in text
 with tempfile.TemporaryDirectory(prefix='mantech-garr-cc-') as directory:
  tmp=Path(directory);(tmp/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
  subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
