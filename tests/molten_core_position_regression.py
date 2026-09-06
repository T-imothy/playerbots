"""Exercise actual MC positioning/plan validation, including post-kill Living Bomb."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root = Path(__file__).resolve().parents[1]
value = (root/'playerbot/strategy/values/MoltenCorePositionValue.cpp').read_text()
action = (root/'playerbot/strategy/actions/MoltenCoreDungeonActions.cpp').read_text()
methods = '\n'.join((block(value, 'bool Casting('),
                     block(value, 'EncounterPosition MoltenCorePositionValue::Calculate('),
                     block(action, 'bool MoltenCorePositionAction::GetPlan(')))
code = r'''
#include <cassert>
#include <set>
#include <map>
#include <list>
#include <iostream>
#include "__GEOMETRY__"
using uint32=unsigned;
struct ObjectGuid {unsigned id=0;ObjectGuid(unsigned i=0):id(i){}operator unsigned()const{return id;}
 bool IsEmpty()const{return id==0;}};
enum CurrentSpellTypes {CURRENT_GENERIC_SPELL,CURRENT_CHANNELED_SPELL};
enum {SPELL_STATE_CASTING,SPELL_STATE_FINISHED};
struct SpellEntry {unsigned Id=19695;};
struct Spell {SpellEntry* m_spellInfo=nullptr;int state=SPELL_STATE_CASTING;int getState()const{return state;}};
struct Map {};
struct Unit {unsigned entry=0,phase=1;ObjectGuid guid;bool world=true,alive=true,combat=true;Map* map=nullptr;
 float x=0,y=0,z=0;std::set<unsigned> auras;Unit* victim=nullptr;Spell* cast=nullptr;
 unsigned GetEntry(){return entry;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}
 bool IsInCombat(){return combat;}Map* GetMap(){return map;}ObjectGuid GetObjectGuid(){return guid;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}
 bool HasAura(unsigned id){return auras.count(id);}Unit* GetVictim(){return victim;}
 Spell* GetCurrentSpell(CurrentSpellTypes type){return type==CURRENT_GENERIC_SPELL?cast:nullptr;}
};
struct Group;
struct Player:Unit {bool charmed=false,teleport=false;unsigned mapId=409,instance=1;Group* group=nullptr;
 bool HasCharmer(){return charmed;}bool IsBeingTeleported(){return teleport;}unsigned GetMapId(){return mapId;}
 unsigned GetInstanceId(){return instance;}Group* GetGroup(){return group;}
 bool IsInMap(Unit* other){return world&&other->world&&map==other->map&&phase==other->phase;}
};
struct GroupReference {Player* source=nullptr;GroupReference* following=nullptr;
 Player* getSource(){return source;}GroupReference* next(){return following;}};
struct Group {GroupReference* first=nullptr;GroupReference* GetFirstMember(){return first;}};
namespace ai {
 struct EncounterPosition {bool active=false;unsigned map=0,instance=0,spell=0;ObjectGuid boss,source;encounter::Point destination;};
}
using namespace ai;
struct Cached {EncounterPosition value;EncounterPosition Get(){return value;}};
struct Context {Cached cached;template<class T>Cached* GetValue(const char*){return &cached;}};
struct PlayerbotAI {Player* bot=nullptr;Context context;std::list<ObjectGuid> attackers;std::map<unsigned,Unit*> units;
 bool validPath=true,ranged=false,healer=false;unsigned checked=0;
 Player* GetBot(){return bot;}Context* GetAiObjectContext(){return &context;}
 bool IsRanged(Player*){return ranged;}bool IsHeal(Player*){return healer;}
 Unit* GetUnit(ObjectGuid guid){auto it=units.find(guid);return it==units.end()?nullptr:it->second;}
};
namespace ai {
 std::map<unsigned,float> radii{{20475,10.0f},{19698,10.0f},{20478,20.0f},{19712,10.0f}};
 float NativeEncounterSpellRadius(unsigned id){return radii[id];} // controlled fixture, not replacement data
 bool ValidateEncounterDestination(PlayerbotAI* ai,EncounterPosition&){++ai->checked;return ai->validPath;}
 struct MoltenCorePositionValue {Player* bot;PlayerbotAI* ai;EncounterPosition Calculate();};
 struct MoltenCorePositionAction {static bool GetPlan(PlayerbotAI*,EncounterPosition&);};
}
#define AI_VALUE(type,name) ai->attackers
__METHODS__
int main(){
 Player bot,other;Map map,otherMap;bot.map=other.map=&map;bot.guid=2;other.guid=3;other.x=1;
 Unit boss;boss.entry=12056;boss.guid=1;boss.map=&map;
 PlayerbotAI ai;ai.bot=&bot;ai.attackers={1};ai.units={{1,&boss},{2,&bot},{3,&other}};
 Group group;GroupReference member{&other};group.first=&member;bot.group=&group;
 MoltenCorePositionValue value{&bot,&ai};EncounterPosition resolved;
 auto get=[&](){ai.context.cached.value=value.Calculate();return MoltenCorePositionAction::GetPlan(&ai,resolved);};
 assert(!get()); // no actual danger
 bot.auras={20475};assert(get()&&resolved.spell==20475&&resolved.source==bot.guid);
 assert(encounter::Distance2d(resolved.destination,{other.x,0,0})>=12);
 // Boss death/despawn and combat exit do not erase a still-ticking native bomb.
 boss.alive=false;boss.combat=false;bot.combat=false;ai.attackers.clear();
 assert(get());ai.units.erase(1);assert(get());
 bot.auras.clear();assert(!MoltenCorePositionAction::GetPlan(&ai,resolved));assert(!get());
 // A nearby human/other bot's remaining bomb is also respected out of combat.
 other.auras={20475};assert(get()&&resolved.source==other.guid);
 other.phase=2;assert(!MoltenCorePositionAction::GetPlan(&ai,resolved));assert(!get());other.phase=1;
 other.map=&otherMap;assert(!get());other.map=&map;
 other.alive=false;assert(!get());other.alive=true;
 other.x=60;assert(!get());other.x=1;
 other.z=20;assert(!get());other.z=0;
 ai.validPath=false;ai.checked=0;assert(!get()&&ai.checked<=8);ai.validPath=true;
 bot.teleport=true;assert(!get());bot.teleport=false;
 bot.charmed=true;assert(!get());bot.charmed=false;
 bot.mapId=0;assert(!get());bot.mapId=409;
 assert(get());++bot.instance;assert(!MoltenCorePositionAction::GetPlan(&ai,resolved));--bot.instance;
 other.auras.clear();assert(!get());
 // Existing Inferno uses its native damage spell radius, including cast start.
 ai.units[1]=&boss;ai.attackers={1};boss.alive=boss.combat=bot.combat=true;boss.auras={19695};
 assert(get()&&encounter::Distance2d(resolved.destination,{0,0,0})>=12);
 boss.auras.clear();SpellEntry info;Spell cast;cast.m_spellInfo=&info;boss.cast=&cast;
 assert(get());cast.state=SPELL_STATE_FINISHED;assert(!get());boss.cast=nullptr;
 boss.phase=2;boss.auras={19695};assert(!get());boss.phase=1;boss.auras.clear();
 // Shazzrah stays scoped to ranged/healer roles and excludes his current victim.
 boss.entry=12264;assert(!get());ai.ranged=true;assert(get());boss.victim=&bot;assert(!get());
 std::cout<<"PASS: actual MC bomb lifetime after boss death, friendly carriers, phase/map/role, native radius and bounded paths\n";
}
'''.replace('__GEOMETRY__',(root/'playerbot/strategy/EncounterGeometry.h').as_posix()).replace('__METHODS__',methods)
for expansion in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-mc-position-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{expansion}',
                        'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
strategy=(root/'playerbot/strategy/generic/MoltenCoreDungeonStrategies.cpp').read_text()
assert 'molten core safe position' in block(strategy,'void MoltenCoreDungeonStrategy::InitNonCombatTriggers(')
assert 'PreserveMoltenCorePositionMultiplier' in block(strategy,'void MoltenCoreDungeonStrategy::InitNonCombatMultipliers(')
