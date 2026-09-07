"""Run personal-demon ownership and healer native-cast admission."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/InnerDemonAction.cpp').read_text()
code=r'''
#include <cassert>
#include <cmath>
#include <list>
#include <map>
#include <string>
#include <type_traits>
#include <iostream>
using ObjectGuid=unsigned;enum{UNIT_CREATED_BY_SPELL,CLASS_PRIEST=5,CLASS_DRUID=11,CLASS_SHAMAN=7,CLASS_PALADIN=2};
struct Unit{unsigned entry=0,guid=0,phase=1,spawner=0,created=0;bool alive=true,world=true,combat=true,charmed=false,friendly=false,valid=true,cc=false;float x=0;Unit*victim=nullptr;
 unsigned GetEntry(){return entry;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 unsigned GetSpawnerGuid(){return spawner;}unsigned GetObjectGuid(){return guid;}Unit*GetVictim(){return victim;}
 unsigned GetUInt32Value(int field){assert(field==UNIT_CREATED_BY_SPELL);return created;}float GetDistance(Unit*u){return std::abs(x-u->x);}};
struct SpellAuraHolder{Unit*caster;Unit*GetCaster(){return caster;}};struct Group{};
struct Player:Unit{unsigned map=548,cls=CLASS_PRIEST;bool teleport=false;Group group;SpellAuraHolder*aura=nullptr;
 unsigned GetMapId(){return map;}unsigned getClass(){return cls;}Group*GetGroup(){return &group;}bool IsBeingTeleported(){return teleport;}
 bool IsInMap(Unit*u){return u&&u->phase==phase;}SpellAuraHolder*GetSpellAuraHolder(unsigned id){assert(id==37676);return aura;}};
template<class T>struct Value{T data{};T Get(){return data;}};
struct Context{Value<ObjectGuid>attack;Value<Unit*>rti;Value<std::list<ObjectGuid>>near;
 template<class T>Value<T>*GetValue(std::string name,std::string q=""){
 if constexpr(std::is_same_v<T,ObjectGuid>){assert(name=="attack target");return &attack;}
 else if constexpr(std::is_same_v<T,Unit*>){assert(name=="rti target");return &rti;}
 else {assert(name=="possible targets"&&q=="100:1");return &near;}}};
struct PlayerbotAI{Player*bot;Context context;std::map<unsigned,Unit*>units;bool real=false,heal=false,nativeReady=true;unsigned casts=0;
 Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool IsHeal(Player*){return heal;}
 Context*GetAiObjectContext(){return &context;}Unit*GetUnit(unsigned id){return units.count(id)?units[id]:nullptr;}};
struct Config{float sightDistance=60;}sPlayerbotAIConfig;
struct Facade{bool IsFriendlyTo(Unit*u,Player*){return u->friendly;}}sServerFacade;
struct PossibleTargetsValue{static bool IsValid(Unit*u,Player*,bool){return u->valid;}};
struct PossibleAttackTargetsValue{static bool IsPossibleTarget(Unit*u,Player*b,float range,bool ignore){assert(!ignore);return u->GetDistance(b)<=range;}
 static bool HasBreakableCC(Unit*u,Player*){return u->cc;}static bool HasUnBreakableCC(Unit*u,Player*){return u->cc;}};
struct Event{};
struct CastSpellAction{PlayerbotAI*ai;Player*bot;std::string name;CastSpellAction(PlayerbotAI*a,std::string n):ai(a),bot(a->bot),name(n){}
 std::string GetSpellName(){return name;}bool isUseful(){return ai->nativeReady;}bool Execute(Event&){if(!ai->nativeReady)return false;++ai->casts;return true;}};
struct InnerDemonAction:CastSpellAction{InnerDemonAction(PlayerbotAI*);static Unit*GetDemon(PlayerbotAI*);Unit*GetTarget();bool isUseful();bool Execute(Event&);};
__METHODS__
int main(){Player bot;bot.guid=1;Unit boss,demon,other;boss.entry=21215;SpellAuraHolder whisper{&boss};bot.aura=&whisper;
 demon.entry=21857;demon.guid=2;demon.spawner=1;demon.created=37735;demon.victim=&bot;demon.x=10;
 other=demon;other.guid=3;other.spawner=4;other.x=1;PlayerbotAI ai;ai.bot=&bot;ai.units={{1,&bot},{2,&demon},{3,&other}};ai.context.near.data={3,2};
 InnerDemonAction action(&ai);Event event;
#ifdef MANGOSBOT_ZERO
 assert(!action.GetDemon(&ai)&&!action.isUseful()&&!action.Execute(event));return 0;
#else
 assert(action.GetDemon(&ai)==&demon);assert(!action.isUseful());ai.heal=true;assert(action.isUseful()&&action.Execute(event)&&ai.casts==1);
 ai.nativeReady=false;assert(!action.Execute(event)&&ai.casts==1);ai.nativeReady=true;
 for(auto row:{std::pair<unsigned,std::string>{CLASS_PRIEST,"smite"},{CLASS_DRUID,"wrath"},{CLASS_SHAMAN,"lightning bolt"},{CLASS_PALADIN,"exorcism"}}){bot.cls=row.first;InnerDemonAction spell(&ai);assert(spell.name==row.second);}
 bot.cls=1;InnerDemonAction melee(&ai);assert(!melee.isUseful());bot.cls=CLASS_PRIEST;
 demon.created=37736;assert(!action.GetDemon(&ai));demon.created=37735;
 demon.spawner=4;assert(!action.GetDemon(&ai));demon.spawner=1;
 demon.victim=&other;assert(!action.GetDemon(&ai));demon.victim=&bot;
 demon.cc=true;assert(!action.GetDemon(&ai));demon.cc=false;
 demon.x=61;assert(!action.GetDemon(&ai));demon.x=10;
 demon.phase=2;assert(!action.GetDemon(&ai));demon.phase=1;
 bot.aura=nullptr;assert(!action.Execute(event));bot.aura=&whisper;
 boss.alive=false;assert(!action.GetDemon(&ai));boss.alive=true;
 boss.entry=21875;assert(!action.GetDemon(&ai));boss.entry=21215;
 ai.context.attack.data=3;assert(!action.GetDemon(&ai));ai.context.attack.data=0;
 ai.context.rti.data=&other;assert(!action.GetDemon(&ai));ai.context.rti.data=nullptr;
 bot.teleport=true;assert(!action.GetDemon(&ai));bot.teleport=false;ai.real=true;assert(!action.GetDemon(&ai));ai.real=false;
 other=demon;assert(!action.GetDemon(&ai));other.spawner=4;assert(action.GetDemon(&ai)==&demon);
 std::cout<<"PASS: own demon only, exact boss aura/summon, healer cast admission, orders and lifecycle\n";
#endif
}
'''
methods='\n'.join(block(source,name) for name in ('Unit* InnerDemonAction::GetDemon(', 'InnerDemonAction::InnerDemonAction(', 'Unit* InnerDemonAction::GetTarget(', 'bool InnerDemonAction::isUseful(', 'bool InnerDemonAction::Execute('))
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='inner-demon-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code.replace('__METHODS__',methods))
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
dispatcher=(root/'playerbot/strategy/actions/DungeonAddTargetAction.cpp').read_text()
assert dispatcher.index('InnerDemonAction::GetDemon(ai)')<dispatcher.index('ai->IsHeal(bot)')<dispatcher.index('GetSummonObjectiveTarget()')
for era in ('tbc','wotlk'):
    native=(root.parent/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/outland/coilfang_reservoir/serpent_shrine/boss_leotheras_the_blind.cpp').read_text()
    assert 'target->CastSpell(target, 37735' in native
    assert 'killer->GetObjectGuid() == m_creature->GetSpawnerGuid()' in native
