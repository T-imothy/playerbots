"""Actual subgroup provider election; native casts/totems stay authoritative."""
from pathlib import Path
import subprocess,tempfile,sys
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
s=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
if '--before-sapphiron' in sys.argv:
 old=(root.parent.parent/'work/classic-raid-lab-20261030/candidates/ddb4a02dee234a7b318ebbe329e79deb83e6d099f71afef55021f43f4cfc1f7e/playerbots/playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
 s=s.replace(block(s,'    const char* ResistanceDuty('),block(old,'    const char* ResistanceDuty('))
code=r'''
#include <cassert>
#include <list>
#include <vector>
#include <set>
#include <string>
using uint32=unsigned;using uint8=unsigned char;using ObjectGuid=unsigned;
enum{CLASS_PALADIN=2,CLASS_SHAMAN=7,POWER_MANA=0,UNIT_STAT_CAN_NOT_REACT_OR_LOST_CONTROL=1,TOTEM_SLOT_WATER=0,TOTEM_SLOT_FIRE=1,UNIT_CREATED_BY_SPELL=1};
struct SpellEntry{};struct PlayerbotAI;
struct Totem{unsigned spell=0;unsigned GetUInt32Value(unsigned){return spell;}};
struct Unit{unsigned entry=13020;unsigned GetEntry(){return entry;}};
struct Group{unsigned GetMemberGroup(unsigned guid){return guid>=10?1:0;}};
struct Player:Unit{unsigned guid=1,cls=CLASS_PALADIN,map=469,mana=100,totemSlot=TOTEM_SLOT_WATER;bool active=false,locked=false;std::set<unsigned> learned;PlayerbotAI*brain=nullptr;Group group;Totem*totem=nullptr;
 unsigned getClass(){return cls;}unsigned GetObjectGuid(){return guid;}unsigned GetMapId(){return map;}
 Group*GetGroup(){return &group;}void*GetSpellAuraHolder(unsigned id,unsigned){return active&&learned.count(id)?this:nullptr;}
 Totem*GetTotem(unsigned slot){return slot==totemSlot?totem:nullptr;}bool HasSpell(unsigned id){return learned.count(id);}unsigned GetPower(unsigned){return mana;}
 bool hasUnitState(unsigned){return locked;}PlayerbotAI*GetPlayerbotAI(){return brain;}};
struct Value{std::list<unsigned>ids{1};auto Get(){return ids;}};struct Context{Value value;template<class T>Value*GetValue(const char*,const char*){return &value;}};
struct PlayerbotAI{Player bot;Unit boss;Context context;bool real=false,ready=true,engaged=true;std::vector<Player*>roster;
 PlayerbotAI(){bot.brain=this;bot.learned={19900};roster={&bot};}Player*GetBot(){return &bot;}Context*GetAiObjectContext(){return &context;}
 Unit*GetUnit(unsigned){return &boss;}bool IsRealPlayer(){return real;}};
struct Facade{SpellEntry spell;const SpellEntry*LookupSpellInfo(unsigned){return &spell;}}sServerFacade;
struct Spell{static unsigned CalculatePowerCost(const SpellEntry*,Player*){return 20;}};
bool Ready(PlayerbotAI*a){
 return a->ready;
}
bool Engaged(Player*,Unit*){return true;}std::vector<Player*>Members(PlayerbotAI*a){return a->roster;}
__BODY__
int main(){PlayerbotAI a,b;auto duty=[&](){const char*d=ResistanceDuty(&a);return d?std::string(d):std::string();};
 assert(duty()=="fire resistance aura");b.bot.guid=2;a.roster.push_back(&b.bot);b.bot.active=true;assert(duty().empty());
 a.bot.active=true;assert(duty()=="fire resistance aura");a.bot.active=false;b.bot.active=false;
 a.bot.mana=0;assert(duty().empty());a.bot.mana=100;a.bot.locked=true;assert(duty().empty());a.bot.locked=false;
 b.bot.active=true;b.real=true;assert(duty().empty());b.real=false;b.bot.active=false;b.bot.guid=10;a.bot.mana=0;
 b.bot.cls=CLASS_SHAMAN;b.bot.guid=2;b.bot.learned={10538};assert(duty().empty()); // other elected subgroup bot
 a.bot.cls=CLASS_SHAMAN;a.bot.learned={10538};a.bot.mana=100;assert(duty()=="fire resistance totem");
 Totem totem{10538};b.bot.totem=&totem;assert(duty().empty());b.bot.totem=nullptr;
 a.boss.entry=11583;assert(duty().empty());a.boss.entry=13020;a.bot.map=409;assert(duty().empty());
 PlayerbotAI frost;frost.bot.map=533;frost.boss.entry=15989;frost.bot.learned={19898};
#ifdef MANGOSBOT_ZERO
 assert(std::string(ResistanceDuty(&frost)?ResistanceDuty(&frost):"")=="frost resistance aura");
 frost.bot.cls=CLASS_SHAMAN;frost.bot.learned={10479};
 assert(std::string(ResistanceDuty(&frost)?ResistanceDuty(&frost):"")=="frost resistance totem");
 PlayerbotAI second;second.bot.cls=CLASS_SHAMAN;second.bot.map=533;second.bot.guid=2;second.bot.learned={10479};
 Totem frostTotem{10479};second.bot.totem=&frostTotem;second.bot.totemSlot=TOTEM_SLOT_FIRE;
 frost.roster.push_back(&second.bot);assert(!ResistanceDuty(&frost)); // actual fire-slot owner wins
 second.bot.totemSlot=TOTEM_SLOT_WATER;assert(ResistanceDuty(&frost)); // wrong slot is not protection
 second.bot.totemSlot=TOTEM_SLOT_FIRE;second.real=true;assert(!ResistanceDuty(&frost));
 frost.boss.entry=15990;assert(!ResistanceDuty(&frost));frost.boss.entry=15989;frost.bot.map=469;assert(!ResistanceDuty(&frost));
#else
 assert(!ResistanceDuty(&frost));
#endif
 for(const char* name:{"searing totem","magma totem","fire nova totem","flametongue totem"})assert(ResistanceTotemReplacement("frost resistance totem",name));
 for(const char* name:{"frost resistance totem","mana spring totem","healing stream totem","strength of earth totem"})assert(!ResistanceTotemReplacement("frost resistance totem",name));
}
'''.replace('__BODY__',block(s,'    const char* ResistanceDuty(')+'\n'+block(s,'    bool ResistanceTotemReplacement('))
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='classic-resistance-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
multiplier=block(s,'float PreserveClassicRaidPlan::GetValue(')
execute=block(s,'bool ClassicRaidSupportAction::Execute(')
assert 'delegate->isUseful() && delegate->isPossible() && delegate->Execute(event)' in execute
assert 'ResistanceTotemReplacement(duty, name)' in multiplier
for spell in ('frost resistance aura','frost resistance totem'):assert spell in execute
assert 'name != duty' in multiplier
print('PASS subgroup provider election, active/human precedence, native mana/learned admission and delegate/conflict wiring')
