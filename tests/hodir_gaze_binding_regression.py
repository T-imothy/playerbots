"""Execute native lethal-hit rescue and area-aura charge propagation."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[2]/'mangos-wotlk-behavior'
s=(root/'src/game/AI/ScriptDevAI/scripts/northrend/ulduar/ulduar/boss_yogg_saron.cpp').read_text();handler=block(s,'struct HodirsProtectiveGaze')
auras=(root/'src/game/Spells/SpellAuras.cpp').read_text();drop=block(auras,'bool SpellAuraHolder::DropAuraCharge(')
instance=(root/'src/game/AI/ScriptDevAI/scripts/northrend/ulduar/ulduar/ulduar.cpp').read_text();timer=block(instance[instance.index('creature->AI()->AddCustomAction(TIMER_HODIRS_PROTECTIVE_GAZE'):],'[&]()');timer=timer[timer.index('{'):]
code=r"""
#include <cassert>
#include <chrono>
#include <iostream>
using namespace std::chrono_literals;
using int32=int;using uint32=unsigned;using DamageEffectType=unsigned;
enum{NPC_HODIR_HELPER=1,TYPE_YOGGSARON=2,IN_PROGRESS=3,TIMER_HODIRS_PROTECTIVE_GAZE=4,TRIGGERED_OLD_TRIGGERED=5,TRIGGERED_NONE=0};
struct Aura;struct Instance{virtual ~Instance()=default;};struct Map{Instance*instance;Instance*GetInstanceData(){return instance;}};
struct Unit{virtual ~Unit()=default;unsigned guid=1;bool active=true,alive=true;unsigned GetObjectGuid(){return guid;}bool IsAlive(){return alive;}void RemoveAuraCharge(unsigned id){assert(id==64174);active=false;}};
struct AI{unsigned resets=0;void ResetTimer(unsigned id,std::chrono::seconds delay){assert(id==TIMER_HODIRS_PROTECTIVE_GAZE&&delay==25s);++resets;}};
struct Creature:Unit{::AI*ai;unsigned casts=0;::AI*AI(){return ai;}bool HasAura(unsigned id){assert(id==64174);return active;}void CastSpell(Unit*,unsigned id,unsigned){assert(id==64174);active=true;++casts;}};
struct Player:Unit{unsigned hp=100,calls=0;Map*map;unsigned GetHealth(){return hp;}Map*GetMap(){return map;}void CastSpell(Player*,unsigned id,unsigned,void*,Aura*,unsigned owner){assert(id==64175&&owner==1);++calls;}};
struct instance_ulduar:Instance{Creature*hodir=nullptr;unsigned state=IN_PROGRESS;Creature*GetSingleCreatureFromStorage(unsigned){return hodir;}unsigned GetData(unsigned){return state;}void TimerTick()__TIMER__};
struct Aura{Unit*target,*caster;Unit*GetTarget(){return target;}Unit*GetCaster(){return caster;}};struct AuraScript{};
struct Proto{unsigned Id=64174;};struct SpellAuraHolder{unsigned m_procCharges=1;Unit*m_target,*caster;Proto proto;Proto*m_spellProto=&proto;void SendAuraUpdate(bool){}unsigned GetCasterGuid(){return caster->guid;}bool IsAreaAura(){return true;}Unit*GetCaster(){return caster;}bool DropAuraCharge();};
__DROP__
__HANDLER__;
int main(){
 AI ai;Creature hodir;hodir.ai=&ai;instance_ulduar instance;instance.hodir=&hodir;Map map{&instance};Player first,second;first.guid=2;second.guid=3;first.map=second.map=&map;
 Aura aura{&first,&hodir};HodirsProtectiveGaze handler;int32 absorb=100,damage=99,reflect=0;unsigned reflectSpell=0;bool prevented=false,charge=true;
 auto hit=[&](int d){absorb=100;damage=d;prevented=false;charge=true;handler.OnAbsorb(&aura,absorb,damage,reflectSpell,reflect,prevented,charge,0);};
 hit(99);assert(absorb==0&&damage==99&&!prevented&&!charge&&first.calls==0);
 hit(100);assert(absorb==0&&damage==0&&prevented&&charge&&first.calls==1&&ai.resets==1);
 SpellAuraHolder holder;holder.m_target=&first;holder.caster=&hodir;assert(holder.DropAuraCharge()&&!hodir.active);
 aura.target=&second;hit(200);assert(damage==200&&!prevented&&!charge&&second.calls==0&&ai.resets==1); // stale second area aura cannot save another player
 instance.TimerTick();assert(hodir.active&&hodir.casts==1);hit(200);assert(prevented&&charge&&second.calls==1&&ai.resets==2);
 instance.state=0;hit(200);assert(!prevented&&damage==200);hodir.active=false;instance.TimerTick();assert(!hodir.active&&hodir.casts==1);instance.state=IN_PROGRESS;
 hodir.active=true;hodir.alive=false;hit(200);assert(!prevented);hodir.alive=true;
 Unit wrong; aura.caster=&wrong;hit(200);assert(!prevented);aura.caster=&hodir;hodir.ai=nullptr;hit(200);assert(!prevented);hodir.ai=&ai;
 aura.target=&hodir;hit(200);assert(!prevented); // keeper's own source aura does not absorb ordinary damage
 std::cout<<"PASS: native lethal-hit rescue, propagated shared charge, stale-area-aura rejection, keeper cooldown callback and encounter/source gates\n";
}
""".replace('__TIMER__',timer).replace('__DROP__',drop).replace('__HANDLER__',handler.replace(' override',''))
with tempfile.TemporaryDirectory(prefix='hodir-gaze-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,check=True,timeout=60)
 subprocess.run([str(path/'test.exe')],cwd=path,check=True,timeout=20)
