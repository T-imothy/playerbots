"""Actual Classic royalty assignment: holders, relief, commands, consumed actors."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/ClassicRaidActions.cpp').read_text()
methods='\n'.join(block(source,marker) for marker in ('Unit* BugTrioRoleTarget(', 'bool BugTrioHealActive('))
code=r'''
#include <algorithm>
#include <cassert>
#include <iostream>
#include <map>
#include <string>
#include <vector>
using uint32=unsigned;using ObjectGuid=unsigned;
constexpr unsigned UNIT_STAND_STATE_DEAD=7,CURRENT_GENERIC_SPELL=0,SPELL_STATE_FINISHED=4;
struct SpellEntry{unsigned Id=25807;};
struct Spell{SpellEntry info;SpellEntry*m_spellInfo=&info;unsigned state=1;unsigned getState()const{return state;}};
struct Unit{unsigned entry=0,guid=0,map=531,instance=1,stand=0;bool player=false,alive=true,world=true,combat=true,charm=false,friendly=false,attackable=true,consumed=false,tank=false,heal=false;Unit* victim=nullptr;Spell*spell=nullptr;
 unsigned GetMapId(){return map;}unsigned GetEntry(){return entry;}unsigned getStandState(){return stand;}bool HasAura(unsigned id){assert(id==25770);return consumed;}Unit*GetVictim(){return victim;}bool IsPlayer(){return player;}Spell*GetCurrentSpell(unsigned){return spell;}
};using Player=Unit;
struct Value{unsigned id=0;unsigned Get(){return id;}};
struct Context{std::map<std::string,Value> values;template<class T>Value*GetValue(const char*s){return &values[s];}};
struct PlayerbotAI{Player*bot=nullptr;bool ready=true;Context ctx;std::vector<Player*> members;std::map<unsigned,Unit*> units;
 Player*GetBot(){return bot;}bool IsTank(Player*p){return p->tank;}bool IsHeal(Player*p){return p->heal;}Context*GetAiObjectContext(){return &ctx;}Unit*GetUnit(unsigned id){return units.count(id)?units[id]:nullptr;}
};
bool Ready(PlayerbotAI*a){return a->ready&&a->bot->world&&a->bot->alive;}
bool Engaged(Player*p,Unit*u){return u&&u->world&&u->alive&&u->combat&&!u->charm&&!u->friendly&&p->map==u->map&&p->instance==u->instance;}
bool Attackable(PlayerbotAI*a,Unit*u){return Engaged(a->bot,u)&&u->attackable;}
Unit*FindBoss(PlayerbotAI*a,unsigned entry){for(auto pair:a->units)if(pair.second->entry==entry&&Engaged(a->bot,pair.second))return pair.second;return nullptr;}
std::vector<Player*>Members(PlayerbotAI*a,bool tanks=false){std::vector<Player*> out;for(auto p:a->members)if(p->alive&&p->world&&!p->charm&&p->map==a->bot->map&&p->instance==a->bot->instance&&(!tanks||p->tank))out.push_back(p);std::sort(out.begin(),out.end(),[](Player*a,Player*b){return a->guid<b->guid;});return out;}
__METHODS__
int main(){
 Unit kri,yauj,vem,trash;Player t1,t2,t3,t4,dps,h1,h2,h3,h4;unsigned guid=10;
 PlayerbotAI ai;
 for(Player*p:{&t1,&t2,&t3,&t4,&dps,&h1,&h2,&h3,&h4}){p->guid=guid++;p->player=true;ai.members.push_back(p);}
 for(Player*p:{&t1,&t2,&t3,&t4})p->tank=true;
 for(Player*p:{&h1,&h2,&h3,&h4})p->heal=true;
 kri.entry=15511;kri.guid=1;yauj.entry=15543;yauj.guid=2;vem.entry=15544;vem.guid=3;trash.entry=15247;trash.guid=4;
 ai.units={{1,&kri},{2,&yauj},{3,&vem},{4,&trash}};
 auto choose=[&](Player*p,Unit*expected){ai.bot=p;assert(BugTrioRoleTarget(&ai)==expected);};
 choose(&t1,&kri);choose(&t2,&yauj);choose(&t3,&vem);choose(&t4,&kri);choose(&dps,&kri);
 bool holder=true;ai.bot=&t4;assert(BugTrioRoleTarget(&ai,&holder)==&kri&&!holder);
 ai.bot=&t2;assert(BugTrioRoleTarget(&ai,&holder)==&yauj&&holder);
 choose(&h1,&kri);choose(&h2,&yauj);choose(&h3,&vem);choose(&h4,&kri);
 // Existing holders win over GUID slots. Free tanks rescue untanked bosses.
 kri.victim=&t3;yauj.victim=&dps;vem.victim=&t1;
 choose(&t3,&kri);choose(&t1,&vem);choose(&t2,&yauj);
 // One tank holding all three releases two to distinct free tanks.
 kri.victim=yauj.victim=vem.victim=&t3;
 choose(&t3,&kri);choose(&t1,&yauj);choose(&t2,&vem);
 t3.alive=false;choose(&t1,&kri);choose(&t2,&yauj);choose(&t4,&vem);t3.alive=true;
 // Marks change DPS kill order, not each holder's job. An unrelated explicit
 // combat target remains under player control.
 ai.ctx.values["rti target"].id=3;choose(&dps,&vem);choose(&t3,&kri);
 ai.ctx.values["attack target"].id=2;choose(&dps,&yauj);
 ai.ctx.values["attack target"].id=4;choose(&dps,nullptr);choose(&t1,nullptr);
 ai.ctx.values.clear();
 kri.stand=UNIT_STAND_STATE_DEAD;choose(&dps,&yauj);kri.stand=0;kri.consumed=true;choose(&dps,&yauj);
 yauj.consumed=true;choose(&dps,&vem);vem.alive=false;choose(&dps,nullptr);vem.alive=true;
 kri.consumed=yauj.consumed=false;ai.ready=false;choose(&dps,nullptr);ai.ready=true;
 dps.map=409;choose(&dps,nullptr);dps.map=531;
 kri.instance=2;choose(&dps,&yauj);kri.instance=1;kri.charm=true;choose(&dps,&yauj);kri.charm=false;
 kri.attackable=false;choose(&dps,&yauj);kri.attackable=true;
 // Only the real in-progress native heal is an interrupt objective.
 Spell heal;ai.bot=&dps;assert(!BugTrioHealActive(&ai,&yauj));yauj.spell=&heal;
 assert(BugTrioHealActive(&ai,&yauj));heal.state=SPELL_STATE_FINISHED;assert(!BugTrioHealActive(&ai,&yauj));heal.state=1;
 heal.info.Id=26580;assert(!BugTrioHealActive(&ai,&yauj));heal.info.Id=25807;
 yauj.consumed=true;assert(!BugTrioHealActive(&ai,&yauj));yauj.consumed=false;yauj.instance=2;assert(!BugTrioHealActive(&ai,&yauj));yauj.instance=1;
 dps.map=409;assert(!BugTrioHealActive(&ai,&yauj));
 std::cout<<"PASS native Bug Trio role holders, distinct rescue, spare tanks, healer anchors, commands, death/consume, map/instance and heal cast state\n";
}
'''.replace('__METHODS__',methods)
with tempfile.TemporaryDirectory(prefix='bug-trio-roles-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 r=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
 if r.returncode:print(r.stdout,r.stderr)
 r.check_returncode();subprocess.run([str(p/'test.exe')],cwd=p,check=True)
# Check admission at the real callers, rather than allowing a dead helper test.
assert '#ifdef MANGOSBOT_ZERO' in source[source.index('bool Attackable('):source.index('Unit* BugTrioRoleTarget(')]
plan=block(source,'ClassicRaidPlan ClassicRaidPlanValue::Calculate(')
assert 'if(Unit* royalty=BugTrioRoleTarget(ai))' in plan
support=block(source,'bool ClassicRaidSupportAction::Select(')
assert 'BugTrioHealActive(ai,yauj)' in support and 'royalty->GetVictim()!=bot' in support
print('PASS Classic-only plan/support integration')
