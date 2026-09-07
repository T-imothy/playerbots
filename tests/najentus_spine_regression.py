"""Actual native spine ownership, rescue assignment, interaction and shield use."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
value=(root/'playerbot/strategy/values/NajentusPositionValue.cpp').read_text()
action=(root/'playerbot/strategy/actions/NajentusActions.cpp').read_text()
methods='\n'.join(block(value,s) for s in ('Player* ai::NajentusSpineVictim(', 'Player* ai::NajentusSpineUser(', 'EncounterPosition NajentusPositionValue::Calculate('))
methods+='\n'+'\n'.join(block(action,'bool NajentusSpineAction::'+s+'(') for s in ('GetPlan','isUseful','Execute'))
methods+='\n'+block(action,'Unit* NajentusShieldAction::GetTarget(')
methods+='\n'+'\n'.join(block(action,'bool NajentusShieldAction::'+s+'(') for s in ('isUseful','Execute'))
code=r'''
#include <cassert>
#include <cmath>
#include <iostream>
#include <list>
#include <map>
#include <set>
#include <vector>
using uint32=unsigned;using int32=int;using ObjectGuid=unsigned;using ItemPosCountVec=std::vector<int>;
enum{GO_READY=0,GO_ACTIVATED=1,GAMEOBJECT_FLAGS=0,GO_FLAG_NO_INTERACT=1,GO_FLAG_IN_USE=2,NULL_BAG=0,NULL_SLOT=0,EQUIP_ERR_OK=0,CMSG_GAMEOBJ_USE=1,EFFECT_INDEX_0=0};
enum class BotState{BOT_STATE_COMBAT};
struct Unit{unsigned guid=1,entry=22887,map=564,instance=1,phase=1;float x=0,y=0,z=0;bool world=true,alive=true,combat=true,charmed=false,player=false;Unit*victim=nullptr;std::set<unsigned>auras;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}bool IsPlayer(){return player;}
 unsigned GetObjectGuid(){return guid;}unsigned GetEntry(){return entry;}unsigned GetMapId(){return map;}Unit*GetVictim(){return victim;}bool HasAura(unsigned id){return auras.count(id);}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}float GetDistance(Unit*u){return std::hypot(x-u->x,y-u->y);}
};
struct GameObject:Unit{unsigned spawner=12,spell=39929,loot=GO_READY,flags=0;bool spawned=true;
 unsigned GetSpellId(){return spell;}unsigned GetSpawnerGuid(){return spawner;}unsigned GetLootState(){return loot;}bool IsSpawned(){return spawned;}
 bool HasFlag(unsigned,unsigned mask){return flags&mask;}bool IsAtInteractDistance(Unit*u){return GetDistance(u)<=5;}};
struct SpellAuraHolder{Unit*caster;Unit*GetCaster()const{return caster;}};
struct WorldPacket{unsigned guid=0;WorldPacket(unsigned){}WorldPacket&operator<<(unsigned id){guid=id;return *this;}};
struct Session{GameObject*spine;unsigned clicks=0;void HandleGameObjectUseOpcode(WorldPacket&p){assert(p.guid==spine->guid);++clicks;spine->loot=GO_ACTIVATED;}};
struct Player;struct PlayerbotAI;
struct GroupReference{Player*member;GroupReference*following=nullptr;Player*getSource(){return member;}GroupReference*next(){return following;}};
struct Group{GroupReference*first=nullptr;GroupReference*GetFirstMember(){return first;}};
struct ItemPrototype{};
struct Player:Unit{Player(){player=true;}bool teleport=false,space=true,healer=false,tank=false,item=false,ready=true,los=true,casting=false;unsigned health=12000;Group*group=nullptr;PlayerbotAI*ai=nullptr;Session*session=nullptr;SpellAuraHolder*impale=nullptr;
 bool IsBeingTeleported(){return teleport;}bool IsInMap(Unit*u){return u&&world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}
 unsigned GetInstanceId(){return instance;}Group*GetGroup(){return group;}PlayerbotAI*GetPlayerbotAI(){return ai;}const SpellAuraHolder*GetSpellAuraHolder(unsigned id){return id==39837?impale:nullptr;}
 unsigned CanStoreNewItem(unsigned,unsigned,ItemPosCountVec&,unsigned id,unsigned count){assert(id==32408&&count==1);return space?0:1;}
 bool HasItemCount(unsigned id,unsigned){assert(id==32408);return item;}bool IsSpellReady(unsigned,const ItemPrototype*){return ready;}
 unsigned GetHealth(){return health;}bool IsWithinLOSInMap(Unit*){return los;}bool IsNonMeleeSpellCasted(bool){return casting;}Session*GetSession(){return session;}
};
namespace encounter{struct Point{float x=0,y=0,z=0;};}
struct EncounterPosition{bool active=false;unsigned map=0,instance=0,spell=0,boss=0,source=0;encounter::Point destination;};
template<class T>struct Cached{T data;T Get(){return data;}};struct Context{Cached<EncounterPosition>position;template<class T>Cached<T>*GetValue(const char*){return &position;}};
struct PlayerbotAI{Player*bot;Context context;bool real=false,canMove=true,path=true,strategy=true;unsigned moves=0,stops=0,interrupts=0,uses=0;std::list<ObjectGuid>guids;std::map<unsigned,Unit*>units;GameObject*spine=nullptr;
 Player*GetBot(){return bot;}bool IsRealPlayer(){return real;}bool CanMove(){return canMove;}bool HasStrategy(const char*,BotState){return strategy;}
 bool IsTank(Player*p){return p->tank;}bool IsHeal(Player*p){return p->healer;}Context*GetAiObjectContext(){return &context;}
 Unit*GetUnit(unsigned id){auto i=units.find(id);return i==units.end()?nullptr:i->second;}GameObject*GetGameObject(unsigned id){return spine&&spine->guid==id?spine:nullptr;}
 void StopMoving(){++stops;}void InterruptSpell(){++interrupts;bot->casting=false;}
};
bool ValidateEncounterDestination(PlayerbotAI*ai,EncounterPosition&){return ai->path;}
struct SpellEntry{unsigned rangeIndex=34;int EffectBasePoints[1]={8499},EffectDieSides[1]={1};};
struct SpellStore{SpellEntry entry;template<class T>const T*LookupEntry(unsigned){return &entry;}}sSpellTemplate;
struct ObjectMgr{ItemPrototype item;const ItemPrototype*GetItemPrototype(unsigned){return &item;}}sObjectMgr;
struct RangeStore{int range=40;const int*LookupEntry(unsigned){return &range;}}sSpellRangeStore;
float GetSpellMaxRange(const int*r){return float(*r);}float NativeEncounterSpellRadius(unsigned id){assert(id==39878);return 100;}
struct Event{};
namespace ai{
 Player*NajentusSpineVictim(PlayerbotAI*,GameObject*);Player*NajentusSpineUser(PlayerbotAI*,GameObject*);
 struct NajentusPositionValue{PlayerbotAI*ai;Player*bot;EncounterPosition Calculate();};
 struct NajentusSpineAction{PlayerbotAI*ai;Player*bot;static bool GetPlan(PlayerbotAI*,EncounterPosition&);bool isUseful();bool Execute(Event&);
 bool IsReaction(){return false;}void SetDuration(unsigned){}bool MoveTo(unsigned,float,float,float,bool,bool,bool,bool){++ai->moves;return true;}};
 struct UseItemIdAction{PlayerbotAI*ai;Player*bot;bool isUseful(){return true;}bool Execute(Event&){if(!bot->ready)return false;++ai->uses;return true;}};
 struct NajentusShieldAction:UseItemIdAction{Unit*GetTarget();bool isUseful();bool Execute(Event&);};
}
using namespace ai;
#define AI_VALUE(type,key) ai->guids
__METHODS__
int main(){
 Player bot,other,victim;bot.guid=10;other.guid=11;victim.guid=12;other.x=2;victim.x=15;
 Group group;GroupReference vr{&victim},orr{&other,&vr},br{&bot,&orr};group.first=&br;bot.group=other.group=victim.group=&group;
 Unit boss;GameObject spine;spine.guid=3;spine.entry=185584;spine.x=15;SpellAuraHolder impale{&boss};victim.impale=&impale;victim.auras.insert(39837);
 Session session{&spine};bot.session=&session;PlayerbotAI ai{&bot},otherAi{&other};bot.ai=&ai;other.ai=&otherAi;ai.spine=&spine;ai.guids={3};ai.units={{1,&boss},{12,&victim}};
 NajentusPositionValue planner{&ai,&bot};NajentusSpineAction rescue{&ai,&bot};NajentusShieldAction shield;shield.ai=&ai;shield.bot=&bot;Event event;
 auto calculate=[&](){ai.context.position.data=planner.Calculate();return ai.context.position.data;};
#ifndef MANGOSBOT_ZERO
 assert(NajentusSpineVictim(&ai,&spine)==&victim);assert(NajentusSpineUser(&ai,&spine)==&other&&!calculate().active);
 other.healer=true;assert(NajentusSpineUser(&ai,&spine)==&bot);auto p=calculate();assert(p.active&&rescue.Execute(event)&&ai.moves==1);
 bot.space=false;assert(!rescue.Execute(event)&&NajentusSpineUser(&ai,&spine)==&other);bot.space=true;
 bot.x=15;bot.casting=true;assert(rescue.Execute(event)&&session.clicks==1&&ai.interrupts==1);assert(!rescue.Execute(event));
 spine.loot=GO_READY;spine.spawner=11;assert(!calculate().active);spine.spawner=12;
 boss.entry=22947;assert(!calculate().active);boss.entry=22887;
 boss.combat=false;assert(!calculate().active);boss.combat=true;
 victim.impale=nullptr;assert(!calculate().active);victim.impale=&impale;
 victim.phase=2;assert(!calculate().active);victim.phase=1;
 spine.flags=GO_FLAG_NO_INTERACT;assert(!calculate().active);spine.flags=0;
 ai.path=false;assert(!calculate().active);ai.path=true;
 boss.victim=&bot;assert(!calculate().active);boss.victim=nullptr;
 // Shield breaks use an owned item and exactly one ready eligible bot.
 ai.guids={1};boss.auras.insert(39872);bot.item=other.item=true;assert(shield.GetTarget()==&boss&&shield.Execute(event)&&ai.uses==1);
 other.guid=9;assert(!shield.isUseful());other.ready=false;assert(shield.isUseful());other.ready=true;other.guid=11;
 victim.health=8500;assert(!shield.isUseful());victim.health=8501;assert(shield.isUseful());victim.health=12000;
 other.health=1000;other.x=101;assert(shield.isUseful());other.x=2;other.health=12000;
 bot.item=false;assert(!shield.Execute(event));bot.item=true;
 bot.ready=false;assert(!shield.isUseful());bot.ready=true;
 bot.los=false;assert(!shield.isUseful());bot.los=true;
 boss.auras.clear();assert(!shield.isUseful());boss.auras.insert(39872);
 bot.teleport=true;assert(!shield.isUseful()&&!rescue.isUseful());bot.teleport=false;
 ai.real=true;assert(!shield.isUseful());
#else
 assert(!calculate().active&&!rescue.Execute(event)&&!shield.Execute(event));
#endif
 std::cout<<"PASS: native spine provenance, rescue assignment/capacity, stale GO, one thrower and raw burst health gate\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-spine-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
for era in ('tbc','wotlk'):
    core=root.parent/f'mangos-{era}-behavior'
    native=(core/'src/game/Spells/SpellEffects.cpp').read_text()
    summon=block(native,'void Spell::EffectSummonObjectWild(')
    assert 'SetSpawnerGuid(m_trueCaster->GetObjectGuid())' in summon
    assert 'case 39977:' in native and 'RemoveAurasDueToSpell(39837)' in native
