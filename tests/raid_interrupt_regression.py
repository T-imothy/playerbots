"""Exercise actual off-target selection and dispatch, without changing a running realm."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
method=block((root/'playerbot/strategy/values/EnemyHealerTargetValue.cpp').read_text(),'ObjectGuid EnemyHealerTargetValue::Calculate(')
action=block((root/'playerbot/strategy/actions/GenericSpellActions.h').read_text(),'class CastSpellOnEnemyHealerAction :')+';'
pet=block((root/'playerbot/strategy/warlock/WarlockActions.h').read_text(),'class CastSpellLockOnEnemyHealerAction :')+';'
code=r'''
#include <cassert>
#include <list>
#include <map>
#include <string>
#include <iostream>
enum{CURRENT_GENERIC_SPELL,CURRENT_CHANNELED_SPELL,SPELL_STATE_FINISHED=9};
struct ObjectGuid{unsigned id=0; ObjectGuid(unsigned n=0):id(n){} bool IsEmpty()const{return !id;} bool operator==(ObjectGuid b)const{return id==b.id;} bool operator<(ObjectGuid b)const{return id<b.id;}};
struct SpellEntry{bool positive=false;};
struct Spell{SpellEntry* m_spellInfo=nullptr;int state=0;int getState()const{return state;}};
bool IsPositiveSpell(const SpellEntry* s){return s->positive;}
struct Map{bool raid=true;bool IsRaid(){return raid;}};
struct Unit{unsigned id=1;bool world=true,alive=true,teleport=false,charmed=false,interruptible=true,castable=true;float distance=5;Map map;Spell* current=nullptr;Spell* channel=nullptr;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsBeingTeleported(){return teleport;}bool HasCharmer(){return charmed;}Map*GetMap(){return &map;}
 Spell* GetCurrentSpell(int slot){return slot==CURRENT_GENERIC_SPELL?current:channel;}ObjectGuid GetObjectGuid(){return id;}};
struct Facade{float GetDistance2d(Unit*,Unit*t){return t->distance;}}sServerFacade;
template<class T>struct Value{T value;T Get(){return value;}};
struct Context{Value<std::list<ObjectGuid>> candidates;Value<ObjectGuid> current;
 template<class T>Value<T>* GetValue(std::string key){if constexpr(std::is_same_v<T,ObjectGuid>)return &current;else return &candidates;}};
struct PlayerbotAI{Context ctx;std::map<ObjectGuid,Unit*> units;bool useful=true;unsigned executed=0;
 Context*GetAiObjectContext(){return &ctx;}Unit*GetUnit(ObjectGuid g){return units[g];}float GetRange(std::string){return 40;}
 bool IsInterruptableSpellCasting(Unit*t,std::string){return t&&t->world&&t->alive&&t->interruptible&&((t->current&&t->current->state!=SPELL_STATE_FINISHED)||(t->channel&&t->channel->state!=SPELL_STATE_FINISHED));}
 bool CanCastSpell(std::string,Unit*t,int){return t->castable;}};
struct EnemyHealerTargetValue{Unit*bot;PlayerbotAI*ai;std::string qualifier="kick";ObjectGuid Calculate();};
struct Event{};
struct CastSpellAction{PlayerbotAI*ai;std::string spell;Unit*target=nullptr;
 CastSpellAction(PlayerbotAI*a,std::string s):ai(a),spell(s){}virtual~CastSpellAction()=default;
 Unit*GetTarget(){return target;}std::string GetSpellName(){return spell;}
 virtual bool isUseful(){return ai->useful;}virtual bool Execute(Event&){++ai->executed;return true;}
 virtual std::string GetReachActionName(){return "";}virtual std::string GetTargetName(){return "";}
 virtual std::string GetTargetQualifier(){return "";}virtual std::string getName(){return "";}};
using CastPetSpellAction=CastSpellAction;
__METHOD__
__ACTION__
__PET__
int main(){
 Unit bot,current,off,healer;current.id=1;off.id=2;healer.id=3;
 SpellEntry harmful,positive{true};Spell damage{&harmful},heal{&positive};current.current=&damage;off.current=&damage;healer.current=&heal;
 PlayerbotAI ai;ai.units={{1,&current},{2,&off},{3,&healer}};ai.ctx.current.value=1;ai.ctx.candidates.value={1,2};
 EnemyHealerTargetValue value{&bot,&ai};assert(value.Calculate()==ObjectGuid(2));
 ai.ctx.candidates.value={1,2,3};assert(value.Calculate()==ObjectGuid(3)); // heals retain precedence
 healer.castable=false;assert(value.Calculate()==ObjectGuid(2));
 off.castable=false;assert(value.Calculate().IsEmpty());off.castable=true;
 off.interruptible=false;assert(value.Calculate().IsEmpty());off.interruptible=true;
 off.distance=50;assert(value.Calculate().IsEmpty());off.distance=5;
 off.current=nullptr;off.channel=&damage;assert(value.Calculate()==ObjectGuid(2));
 damage.state=SPELL_STATE_FINISHED;assert(value.Calculate().IsEmpty());damage.state=0;
 off.alive=false;assert(value.Calculate().IsEmpty());off.alive=true;
 bot.map.raid=false;assert(value.Calculate()==ObjectGuid(3)); // existing non-raid healing policy
 ai.ctx.candidates.value={1,2};assert(value.Calculate().IsEmpty());bot.map.raid=true;
 bot.teleport=true;assert(value.Calculate().IsEmpty());bot.teleport=false;
 bot.charmed=true;assert(value.Calculate().IsEmpty());bot.charmed=false;
 bot.world=false;assert(value.Calculate().IsEmpty());bot.world=true;
 CastSpellOnEnemyHealerAction interrupt(&ai,"kick");CastSpellLockOnEnemyHealerAction pet(&ai);Event event;
 interrupt.target=pet.target=&off;assert(interrupt.isUseful()&&pet.isUseful());
 assert(interrupt.Execute(event)&&pet.Execute(event)&&ai.executed==2);
 off.channel=nullptr;assert(!interrupt.isUseful()&&!pet.isUseful());
 assert(!interrupt.Execute(event)&&!pet.Execute(event)&&ai.executed==2);
 std::cout<<"PASS off-target raid damage/channel interrupts, heal precedence, reachability and stale dispatch\n";
}
'''.replace('__METHOD__',method).replace('__ACTION__',action).replace('__PET__',pet)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='raid-interrupt-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
