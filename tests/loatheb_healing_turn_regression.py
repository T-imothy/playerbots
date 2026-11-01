"""Execute actual Loatheb action admission, including native Holy Shock wrapper."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
source=(Path(__file__).resolve().parents[1]/'playerbot/strategy/actions/NaxxramasRoleActions.cpp').read_text()
code=r'''
#include <cassert>
#include <map>
#include <vector>
#include <iostream>
constexpr unsigned SPELLFAMILY_PALADIN=10,SPELL_EFFECT_DISPEL=38;
using uint32=unsigned;
struct SpellEntry{unsigned Id=1,SpellFamilyName=6,SpellIconID=0,effect=10;bool heal=true;};
bool IsSpellHaveEffect(const SpellEntry*s,unsigned effect){return s->effect==effect;}
struct Unit{bool friendly=true;};struct Player:Unit{};
struct Value{unsigned value=1;unsigned Get(){return value;}};
struct Context{Value id;template<class T>Value*GetValue(const char*,const char*){return &id;}};
struct PlayerbotAI{Player bot;Context context;bool ready=true,healer=true,boss=true;
 Player*GetBot(){return &bot;}bool IsHeal(Player*){return healer;}Context*GetAiObjectContext(){return &context;}
 static bool IsHealSpell(const SpellEntry*s){return s->heal;}};
struct Action{virtual ~Action()=default;Unit*target=nullptr;virtual Unit*GetTarget(){return target;}};
struct CastSpellAction:Action{unsigned id=1;unsigned GetDecisionSpellId(){return id;}protected:Unit*GetTarget()override{return target;}};
struct Facade{std::map<unsigned,SpellEntry> spells;const SpellEntry*LookupSpellInfo(unsigned id){return spells.count(id)?&spells[id]:nullptr;}
 bool IsFriendlyTo(Player*,Unit*u){return u&&u->friendly;}}sServerFacade;
bool Ready(PlayerbotAI*a){return a->ready;}std::vector<Unit*>Enemies(PlayerbotAI*a){return a->boss?std::vector<Unit*>{&a->bot}:std::vector<Unit*>{};}
Unit*Find(const std::vector<Unit*>&v,unsigned){return v.empty()?nullptr:v.front();}
Player injured,other;Player*selectedTarget=&injured;Player*elected=nullptr;
Player*HealingTarget(PlayerbotAI*){return selectedTarget;}
Player*LoathebHealer(PlayerbotAI*,Player*){return elected;}
const char*LargeHeal(Player*){return "holy light";}
namespace ai{float NaxxramasRoleMultiplier(PlayerbotAI*,Action*);}
__BODY__
int main(){PlayerbotAI ai;elected=&ai.bot;CastSpellAction cast;cast.target=&injured;
 sServerFacade.spells={{1,{1,10,70,77,true}},{2,{2,10,156,3,false}},
 {3,{3,6,0,10,true}},{4,{4,6,0,38,false}},{5,{5,6,0,6,false}}};
 assert(ai::NaxxramasRoleMultiplier(&ai,&cast)==1);
 cast.id=2;
#ifdef MANGOSBOT_ZERO
 assert(ai::NaxxramasRoleMultiplier(&ai,&cast)==0); // friendly Holy Shock spends the turn
 cast.target=&other;assert(ai::NaxxramasRoleMultiplier(&ai,&cast)==0);
 other.friendly=false;assert(ai::NaxxramasRoleMultiplier(&ai,&cast)==1);other.friendly=true;
 cast.target=&injured;cast.id=4;assert(ai::NaxxramasRoleMultiplier(&ai,&cast)==0); // dispel
 cast.id=3;assert(ai::NaxxramasRoleMultiplier(&ai,&cast)==0); // small heal, not elected large spell
#else
 assert(ai::NaxxramasRoleMultiplier(&ai,&cast)==1);
#endif
 cast.id=5;assert(ai::NaxxramasRoleMultiplier(&ai,&cast)==1); // absorb, no healing cooldown
 cast.id=1;elected=&other;
#ifndef MANGOSBOT_TWO
 assert(ai::NaxxramasRoleMultiplier(&ai,&cast)==0);
#else
 assert(ai::NaxxramasRoleMultiplier(&ai,&cast)==1);
#endif
 elected=&ai.bot;selectedTarget=nullptr;
#ifndef MANGOSBOT_TWO
 assert(ai::NaxxramasRoleMultiplier(&ai,&cast)==0);
#endif
 selectedTarget=&injured;cast.id=2;
 ai.ready=false;assert(ai::NaxxramasRoleMultiplier(&ai,&cast)==1);ai.ready=true;
 ai.boss=false;assert(ai::NaxxramasRoleMultiplier(&ai,&cast)==1);ai.boss=true;
 ai.healer=false;assert(ai::NaxxramasRoleMultiplier(&ai,&cast)==1);ai.healer=true;
 cast.id=999;assert(ai::NaxxramasRoleMultiplier(&ai,&cast)==1);
 Action ordinary;assert(ai::NaxxramasRoleMultiplier(&ai,&ordinary)==1);
 assert(ai::NaxxramasRoleMultiplier(&ai,nullptr)==1);
 std::cout<<"PASS actual Loatheb turn admission: Holy Shock friendly/hostile, dispels, large heal, absorb, election and era guards\n";
}
'''.replace('__BODY__',block(source,'float ai::NaxxramasRoleMultiplier('))
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='loatheb-heal-turn-') as directory:
  p=Path(directory);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
