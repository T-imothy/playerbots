"""Actual subgroup provider election; native casts/totems stay authoritative."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
s=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
code=r'''
#include <cassert>
#include <list>
#include <vector>
#include <set>
#include <string>
using uint32=unsigned;using uint8=unsigned char;using ObjectGuid=unsigned;
enum{CLASS_PALADIN=2,CLASS_SHAMAN=7,POWER_MANA=0,UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL=1,TOTEM_SLOT_WATER=0,UNIT_CREATED_BY_SPELL=1};
struct SpellEntry{};struct PlayerbotAI;
struct Totem{unsigned spell=0;unsigned GetUInt32Value(unsigned){return spell;}};
struct Unit{unsigned entry=13020;unsigned GetEntry(){return entry;}};
struct Group{unsigned GetMemberGroup(unsigned guid){return guid>=10?1:0;}};
struct Player:Unit{unsigned guid=1,cls=CLASS_PALADIN,map=469,mana=100;bool active=false,locked=false;std::set<unsigned> learned;PlayerbotAI*brain=nullptr;Group group;Totem*totem=nullptr;
 unsigned getClass(){return cls;}unsigned GetObjectGuid(){return guid;}unsigned GetMapId(){return map;}
 Group*GetGroup(){return &group;}void*GetSpellAuraHolder(unsigned id,unsigned){return active&&id==19900?this:nullptr;}
 Totem*GetTotem(unsigned){return totem;}bool HasSpell(unsigned id){return learned.count(id);}unsigned GetPower(unsigned){return mana;}
 bool hasUnitState(unsigned){return locked;}PlayerbotAI*GetPlayerbotAI(){return brain;}};
struct Value{std::list<unsigned>ids{1};auto Get(){return ids;}};struct Context{Value value;template<class T>Value*GetValue(const char*,const char*){return &value;}};
struct PlayerbotAI{Player bot;Unit boss;Context context;bool real=false,ready=true,engaged=true;std::vector<Player*>roster;
 PlayerbotAI(){bot.brain=this;bot.learned={19900};roster={&bot};}Player*GetBot(){return &bot;}Context*GetAiObjectContext(){return &context;}
 Unit*GetUnit(unsigned){return &boss;}bool IsRealPlayer(){return real;}};
struct Facade{SpellEntry spell;const SpellEntry*LookupSpellInfo(unsigned){return &spell;}}sServerFacade;
struct Spell{static unsigned CalculatePowerCost(const SpellEntry*,Player*){return 20;}};
bool Ready(PlayerbotAI*a){
#ifdef MANGOSBOT_ZERO
 return a->ready;
#else
 return false;
#endif
}
bool Engaged(Player*,Unit*){return true;}std::vector<Player*>Members(PlayerbotAI*a){return a->roster;}
__BODY__
int main(){PlayerbotAI a,b;auto duty=[&](){const char*d=ResistanceDuty(&a);return d?std::string(d):std::string();};
#ifdef MANGOSBOT_ZERO
 assert(duty()=="fire resistance aura");b.bot.guid=2;a.roster.push_back(&b.bot);b.bot.active=true;assert(duty().empty());
 a.bot.active=true;assert(duty()=="fire resistance aura");a.bot.active=false;b.bot.active=false;
 a.bot.mana=0;assert(duty().empty());a.bot.mana=100;a.bot.locked=true;assert(duty().empty());a.bot.locked=false;
 b.bot.active=true;b.real=true;assert(duty().empty());b.real=false;b.bot.active=false;b.bot.guid=10;a.bot.mana=0;
 b.bot.cls=CLASS_SHAMAN;b.bot.guid=2;b.bot.learned={10538};assert(duty().empty()); // other elected subgroup bot
 a.bot.cls=CLASS_SHAMAN;a.bot.learned={10538};a.bot.mana=100;assert(duty()=="fire resistance totem");
 Totem totem{10538};b.bot.totem=&totem;assert(duty().empty());b.bot.totem=nullptr;
 a.boss.entry=11583;assert(duty().empty());a.boss.entry=13020;a.bot.map=409;assert(duty().empty());
#else
 assert(duty().empty());
#endif
}
'''.replace('__BODY__',block(s,'    const char* ResistanceDuty('))
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='classic-resistance-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
multiplier=block(s,'float PreserveClassicRaidPlan::GetValue(')
execute=block(s,'bool ClassicRaidSupportAction::Execute(')
assert 'delegate->isUseful() && delegate->isPossible() && delegate->Execute(event)' in execute
for spell in ('mana spring totem','healing stream totem','frost resistance totem'):assert spell in multiplier
assert 'name != duty' in multiplier
print('PASS subgroup provider election, active/human precedence, native mana/learned admission and delegate/conflict wiring')
