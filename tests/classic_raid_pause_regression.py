"""Actual raid damage-pause action: preserve useful casts and settle cleanly."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
src=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
parts='\n'.join(block(src, marker) for marker in (
    '    bool RaidDamageSpell(', 'bool ClassicRaidPauseAction::isUseful(',
    'bool ClassicRaidPauseAction::Execute('))
code=r'''
#include <algorithm>
#include <cassert>
#include <iostream>
#include <map>
#include <vector>
using uint32=unsigned;using SpellEffectIndex=unsigned;
constexpr unsigned MAX_EFFECT_INDEX=3,CURRENT_GENERIC_SPELL=0,CURRENT_CHANNELED_SPELL=1,CURRENT_AUTOREPEAT_SPELL=2;
constexpr unsigned SPELL_STATE_FINISHED=2,CMSG_PET_ACTION=1,ACT_COMMAND=7,COMMAND_FOLLOW=1;
struct ObjectGuid{unsigned id=0;};
struct SpellEntry{unsigned Id=0;bool damage=false,positive=false;unsigned EffectTriggerSpell[3]={};};
bool IsSpellEffectDamage(const SpellEntry&s,unsigned){return s.damage;}
bool IsSpellEffectTriggerSpell(const SpellEntry*s,unsigned i){return s->EffectTriggerSpell[i]!=0;}
bool IsSpellEffectTriggerSpellByAura(const SpellEntry*,unsigned){return false;}
struct Unit{Unit*victim=nullptr;ObjectGuid guid{4};Unit*GetVictim(){return victim;}ObjectGuid GetObjectGuid(){return guid;}};
bool IsPositiveSpell(const SpellEntry*s,Unit*,Unit*){return s->positive;}
struct Pet:Unit{};
struct Targets{Unit*target=nullptr;Unit*getUnitTarget(){return target;}};
struct Spell{const SpellEntry*m_spellInfo=nullptr;Targets m_targets;unsigned state=0;unsigned getState(){return state;}};
struct WorldPacket{unsigned kind;std::vector<unsigned>data;WorldPacket(unsigned k):kind(k){}
 WorldPacket&operator<<(ObjectGuid g){data.push_back(g.id);return *this;}WorldPacket&operator<<(unsigned v){data.push_back(v);return *this;}};
struct Session{Pet*pet=nullptr;unsigned follows=0;void HandlePetAction(WorldPacket&p){assert(p.data[1]==((ACT_COMMAND<<24)|COMMAND_FOLLOW));
 ++follows;if(pet)pet->victim=nullptr;}};
struct Player:Unit{Pet*pet=nullptr;Session session;Spell*casts[3]={};unsigned stops=0;std::vector<unsigned>interrupts;
 Pet*GetPet(){session.pet=pet;return pet;}Session*GetSession(){return &session;}
 Spell*GetCurrentSpell(unsigned slot){return casts[slot];}void AttackStop(){++stops;victim=nullptr;}
 void InterruptSpell(unsigned slot){interrupts.push_back(slot);casts[slot]=nullptr;}};
struct ClassicRaidPlan{bool holdDamage=false;};
struct PlayerbotAI{Player bot;ClassicRaidPlan plan;bool ready=true,offense=true;Player*GetBot(){return &bot;}};
bool Ready(PlayerbotAI*a){return a->ready;}
bool ClassicRaidOffenseAllowed(PlayerbotAI*a,const SpellEntry*,Unit*){return a->offense;}
struct Facade{std::map<unsigned,const SpellEntry*>spells;const SpellEntry*LookupSpellInfo(unsigned id){return spells.count(id)?spells[id]:nullptr;}}sServerFacade;
struct Event{};
struct ClassicRaidPauseAction{PlayerbotAI*ai;Player*bot;bool isUseful();bool Execute(Event&);};
#define AI_VALUE(T,N) (ai->plan)
__PARTS__
int main(){PlayerbotAI brain;ClassicRaidPauseAction pause{&brain,&brain.bot};Event event;Unit boss;
 SpellEntry bolt{1,true,false},heal{2,false,true},taunt{3,false,false},cc{4,false,false},defense{5,false,true};
 SpellEntry ticks{6,true,false},channel{7,false,false},friendlyTicks{8,true,true},loop{9,false,false};
 channel.EffectTriggerSpell[0]=6;loop.EffectTriggerSpell[0]=9;sServerFacade.spells={{6,&ticks},{9,&loop}};
 assert(RaidDamageSpell(&bolt)&&RaidDamageSpell(&channel)&&!RaidDamageSpell(&loop)&&!RaidDamageSpell(nullptr));
 brain.plan.holdDamage=true;
 for(const auto*info:{&heal,&taunt,&cc,&defense,&friendlyTicks,&loop}){
  Spell cast{info,{&boss}};brain.bot.casts[0]=&cast;assert(!pause.isUseful()&&!pause.Execute(event)&&brain.bot.interrupts.empty());
 }
 brain.bot.casts[0]=nullptr;assert(!pause.isUseful()&&!pause.Execute(event));
 Spell normal{&bolt,{&boss}},channeled{&channel,{&boss}},wand{&bolt,{&boss}};
 brain.bot.casts[0]=&normal;brain.bot.casts[1]=&channeled;brain.bot.casts[2]=&wand;
 assert(pause.isUseful()&&pause.Execute(event)&&brain.bot.interrupts==std::vector<unsigned>({0,1,2}));
 assert(!pause.isUseful()&&!pause.Execute(event)); // Settled hold does not consume more actions.
 brain.bot.interrupts.clear();brain.bot.victim=&boss;assert(pause.Execute(event)&&!brain.bot.victim);
 Pet pet;pet.victim=&boss;brain.bot.pet=&pet;assert(!brain.bot.victim&&pause.isUseful());
 const auto follows=brain.bot.session.follows;assert(pause.Execute(event)&&brain.bot.session.follows==follows+1&&!pet.victim);
 assert(!pause.isUseful()&&!pause.Execute(event)); // Pet-only recall also settles.
 Spell malformed{nullptr,{&boss}};brain.bot.casts[0]=&malformed;assert(!pause.isUseful());
 normal.state=SPELL_STATE_FINISHED;brain.bot.casts[0]=&normal;assert(!pause.isUseful());
 normal.state=0;brain.bot.casts[0]=&normal;brain.ready=false;assert(!pause.isUseful()&&!pause.Execute(event));brain.ready=true;
 brain.plan.holdDamage=false;assert(!pause.isUseful());
 brain.offense=false;assert(pause.isUseful()&&pause.Execute(event)&&brain.bot.interrupts==std::vector<unsigned>({0}));
 pet.victim=&boss;const auto reservedFollow=brain.bot.session.follows;
 assert(!brain.bot.victim&&pause.isUseful()&&pause.Execute(event));
 assert(!pet.victim&&brain.bot.session.follows==reservedFollow+1); // A reserved target is protected without a raid-wide hold.
 assert(!pause.isUseful());
 brain.offense=true;assert(!pause.isUseful());
 std::cout<<"PASS actual raid pause: damage-only generic/channel/auto cancellation, CC/heal/defense preservation, pet recall, settled/finished/native refusal\n";
}
'''.replace('__PARTS__',parts)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='classic-raid-pause-') as folder:
        p=Path(folder);(p/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
        subprocess.run([str(p/'test.exe')],cwd=p,check=True)
