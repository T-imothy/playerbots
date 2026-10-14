"""Compile the real buff-family/provider policy and final mutation guard in all eras."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block
R=Path(__file__).resolve().parents[1]
s=(R/'playerbot/strategy/actions/GroupBuffPolicy.cpp').read_text()
methods=block(s,'const std::pair<const char*, const char*>* BuffFamily(')+'\n'+block(s,'bool ai::HasEquivalentGroupBuff(')+'\n'+block(s,'bool ai::AutomaticGroupBuffAllowed(')
generic=(R/'playerbot/strategy/actions/GenericSpellActions.cpp').read_text()
methods+='\n'+block(generic,'bool CastBuffSpellAction::isUseful(')+'\n'+block(generic,'bool CastBuffSpellAction::Execute(')
code=r'''
#include <algorithm>
#include <cassert>
#include <cctype>
#include <iostream>
#include <map>
#include <set>
#include <string>
#include <vector>
using uint32=unsigned;using int32=int;
enum{CURRENT_GENERIC_SPELL,SPELL_STATE_FINISHED=7,EFFECT_INDEX_0=0,POWER_MANA=0};
enum class BotState{BOT_STATE_NON_COMBAT,BOT_STATE_COMBAT};
struct SpellEntry{std::string SpellName[1];bool passive=false;int strength=50;};
struct Unit{virtual ~Unit()=default;unsigned guid=0,map=1,instance=1,phase=1;bool world=true,alive=true,charm=false,friendly=true;std::set<std::string>auras;
virtual bool IsPlayer(){return false;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool HasCharmer(){return charm;}
bool IsInMap(Unit*u){return u&&world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}};
struct Spell{SpellEntry*m_spellInfo=nullptr;unsigned state=0;struct Targets{Unit*target=nullptr;Unit*getUnitTarget(){return target;}}m_targets;unsigned getState(){return state;}};
struct Group;struct PlayerbotAI;
struct Player:Unit{bool teleport=false,duel=false,ready=true;unsigned subgroup=0,power=0;Group*group=nullptr;PlayerbotAI*ai=nullptr;Spell*pending=nullptr;std::set<unsigned>known;
bool IsPlayer()override{return true;}bool IsBeingTeleported(){return teleport;}Group*GetGroup(){return group;}unsigned GetSubGroup(){return subgroup;}unsigned GetObjectGuid(){return guid;}unsigned GetPowerType(){return power;}
PlayerbotAI*GetPlayerbotAI(){return ai;}Spell*GetCurrentSpell(unsigned){return pending;}bool HasSpell(unsigned id){return known.count(id);}
int CalculateSpellEffectValue(Unit*,const SpellEntry*s,unsigned,void*,bool max,bool final){assert(max&&!final);return s->strength;}};
struct GroupReference{Player*p;GroupReference*n=nullptr;Player*getSource(){return p;}GroupReference*next(){return n;}};
struct Group{std::vector<GroupReference>refs;void Set(std::vector<Player*>players){refs.clear();for(auto*p:players){p->group=this;refs.push_back({p});}for(unsigned i=1;i<refs.size();++i)refs[i-1].n=&refs[i];}GroupReference*GetFirstMember(){return refs.empty()?nullptr:&refs[0];}};
template<class T>struct Value{T id=0;T Get(){return id;}};
struct Context{std::map<std::string,Value<unsigned>>ids;template<class T>Value<T>*GetValue(const char*,std::string n){return &ids[n];}};
struct PlayerbotAI{Player*bot;bool real=false,buff=true;Context context;PlayerbotAI(Player*p):bot(p){p->ai=this;}Player*GetBot(){return bot;}Context*GetAiObjectContext(){return &context;}bool IsRealPlayer(){return real;}bool HasStrategy(const char*,BotState){return buff;}
bool HasAura(std::string n,Unit*u){return u&&u->auras.count(n);}bool CanCastSpell(unsigned id,Unit*u,unsigned){return bot->ready&&bot->known.count(id)&&bot->IsInMap(u);}
bool CanCastSpell(std::string n,Unit*u,unsigned e){return CanCastSpell(context.ids[n].id,u,e);}};
struct Facade{std::map<unsigned,SpellEntry>spells;const SpellEntry*LookupSpellInfo(unsigned id){auto i=spells.find(id);return i==spells.end()?nullptr:&i->second;}bool IsFriendlyTo(Unit*,Unit*u){return u->friendly;}}sServerFacade;
bool IsPassiveSpell(const SpellEntry*s){return s->passive;}void strToLower(std::string&s){for(char&c:s)c=char(std::tolower(static_cast<unsigned char>(c)));}
namespace ai{bool HasEquivalentGroupBuff(PlayerbotAI*,const std::string&,Unit*);bool AutomaticGroupBuffAllowed(PlayerbotAI*,const std::string&,Unit*);}
using namespace ai;
struct Event{};
struct CastSpellAction{unsigned casts=0;bool Execute(Event&){++casts;return true;}};
struct CastAuraSpellAction:CastSpellAction{bool useful=true;bool isUseful(){return useful;}};
struct CastBuffSpellAction:CastAuraSpellAction{PlayerbotAI*ai;Unit*target;std::string name;std::string GetSpellName(){return name;}Unit*GetTarget(){return target;}bool isUseful();bool Execute(Event&);};
__METHODS__
int main(){
 Player priests[4],patients[8];PlayerbotAI a(&priests[0]),b(&priests[1]),c(&priests[2]),d(&priests[3]);std::vector<Player*>roster;
 for(unsigned i=0;i<4;++i){priests[i].guid=i+1;priests[i].known={1,2};priests[i].auras={"power word: fortitude"};priests[i].ai->context.ids["power word: fortitude"].id=1;priests[i].ai->context.ids["prayer of fortitude"].id=2;roster.push_back(&priests[i]);}
 sServerFacade.spells[1]={{"Power Word: Fortitude"},false,50};sServerFacade.spells[2]={{"Prayer of Fortitude"},false,50};
 for(unsigned i=0;i<8;++i){patients[i].guid=10+i;patients[i].subgroup=i;roster.push_back(&patients[i]);}Group group;group.Set(roster);
 for(unsigned i=0;i<8;++i){unsigned count=0;for(auto&p:priests)if(AutomaticGroupBuffAllowed(p.ai,"power word: fortitude",&patients[i])){++count;assert(p.guid==1+i%4);}assert(count==1);}
 // Missing one player uses the inexpensive single variant; complete group is not rebuffed.
 for(auto&p:patients)p.auras={"power word: fortitude"};patients[0].auras.clear();
 assert(!AutomaticGroupBuffAllowed(&a,"prayer of fortitude",&patients[0]));for(auto&p:patients)p.auras.clear();
 patients[0].auras={"prayer of fortitude"};assert(!AutomaticGroupBuffAllowed(&a,"power word: fortitude",&patients[0]));patients[0].auras={"power word: fortitude"};assert(!AutomaticGroupBuffAllowed(&a,"prayer of fortitude",&patients[0]));patients[0].auras.clear();
 // Final guard prevents a cached target from consuming mana after another caster succeeds.
 CastBuffSpellAction action;action.ai=&a;action.target=&patients[0];action.name="power word: fortitude";Event event;assert(action.isUseful());patients[0].auras={"power word: fortitude"};assert(!action.Execute(event)&&action.casts==0);patients[0].auras.clear();assert(action.Execute(event)&&action.casts==1);
 // Native capability loss releases the assignment immediately.
 for(unsigned mode=0;mode<8;++mode){switch(mode){case 0:priests[0].alive=false;break;case 1:priests[0].teleport=true;break;case 2:priests[0].instance=2;break;case 3:priests[0].world=false;break;case 4:priests[0].charm=true;break;case 5:a.buff=false;break;case 6:priests[0].ready=false;break;case 7:priests[0].known.clear();break;}
 assert(AutomaticGroupBuffAllowed(&b,"power word: fortitude",&patients[0]));priests[0].alive=priests[0].world=priests[0].ready=true;priests[0].teleport=priests[0].charm=false;priests[0].instance=1;a.buff=true;priests[0].known={1,2};}
 // A human's pending cast is authoritative; finished/unrelated casts do not block.
 Spell pending{&sServerFacade.spells[1],0,{&patients[0]}};priests[1].pending=&pending;b.real=true;assert(!AutomaticGroupBuffAllowed(&a,"power word: fortitude",&patients[0]));pending.state=SPELL_STATE_FINISHED;assert(AutomaticGroupBuffAllowed(&a,"power word: fortitude",&patients[0]));priests[1].pending=nullptr;b.real=false;
 // Stronger native rank/talent provider wins over equal-rank distribution.
 sServerFacade.spells[3]={{"Power Word: Fortitude"},false,75};priests[2].known.insert(3);c.context.ids["power word: fortitude"].id=3;
 assert(!AutomaticGroupBuffAllowed(&a,"power word: fortitude",&patients[0])&&AutomaticGroupBuffAllowed(&c,"power word: fortitude",&patients[0]));c.context.ids["power word: fortitude"].id=1;
 // Group-variant threshold follows the actual expansion scope.
 for(auto&p:patients)p.auras={"power word: fortitude"};patients[0].auras.clear();patients[1].auras.clear();patients[2].auras.clear();
#ifdef MANGOSBOT_TWO
 assert(AutomaticGroupBuffAllowed(&a,"prayer of fortitude",&patients[0]));
#else
 assert(!AutomaticGroupBuffAllowed(&a,"prayer of fortitude",&patients[0]));patients[1].subgroup=patients[2].subgroup=0;assert(AutomaticGroupBuffAllowed(&a,"prayer of fortitude",&patients[0]));
#endif
 // Every common family shares the same final equivalent-aura guard.
 for(auto f:{std::pair{"divine spirit","prayer of spirit"},std::pair{"arcane intellect","arcane brilliance"},std::pair{"mark of the wild","gift of the wild"},std::pair{"shadow protection","prayer of shadow protection"}}){patients[0].auras={f.second};assert(HasEquivalentGroupBuff(&a,f.first,&patients[0]));assert(!AutomaticGroupBuffAllowed(&a,f.first,&patients[0]));}
 assert(AutomaticGroupBuffAllowed(&a,"power word: shield",&patients[0]));assert(AutomaticGroupBuffAllowed(&a,"blessing of wisdom",&patients[0]));
 patients[0].auras.clear();patients[0].phase=2;assert(!AutomaticGroupBuffAllowed(&a,"power word: fortitude",&patients[0]));patients[0].phase=1;patients[0].alive=false;assert(!AutomaticGroupBuffAllowed(&a,"power word: fortitude",&patients[0]));
 std::cout<<"PASS: four-caster subgroup coordination, native strength/fallback, group cost threshold, pending casts and zero-mutation stale targets\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='group-buff-') as d:
  p=Path(d);(p/'test.cpp').write_text(code)
  r=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
  if r.returncode:raise RuntimeError(r.stdout+r.stderr)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)

assert "HasEquivalentGroupBuff(ai, *i, unit)" in (R/"playerbot/strategy/values/PartyMemberWithoutAuraValue.cpp").read_text()
