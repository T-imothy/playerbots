"""Production cast preparation blocks and the complete coordinate dispatch.

Tests pre-start ownership and native-start failure semantics, with a controlled
event queue. Does not simulate native spell effects or encounter completion.
"""
from pathlib import Path
import subprocess
import sys
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/PlayerbotAI.cpp').read_text()
before='--before' in sys.argv
if before:
    source=subprocess.check_output(['git','-c','safe.directory='+root.as_posix(),'-C',str(root),'show',
        '8e74916a715228b687b10d35fb1292fa636cb638:playerbot/PlayerbotAI.cpp'],text=True)
functions=[]
for kind,name in (('Unit* target','UnitCast'),('GameObject* goTarget','ObjectCast')):
    method=block(source,'bool PlayerbotAI::CastSpell(uint32 spellId, '+kind)
    begin=method.index('    // SpellStart transfers') if '// SpellStart transfers' in method else method.index('    Spell')
    # Older Unit and GameObject functions already propagate native start failure.
    end=method.index('    PlayAttackEmote(6);')
    section=method[begin:end]
    functions.append('bool PlayerbotAI::'+name+'('+kind+', Item* itemTarget, bool waitForSpell) {\n'
        'const SpellEntry* pSpellInfo=&entry;uint32 spellId=entry.Id;WorldObject* faceTo=nullptr;\n'+section+'return true;\n}')
    # Exercise the real admission prefix before selection/movement is mutated.
    functions.append(method[:method.index('    aiObjectContext->GetValue<LastMovement&>')]+'    return true;\n}')
functions.append(block(source,'bool PlayerbotAI::CastSpell(uint32 spellId, float x'))

code=r'''
#include <cassert>
#include <cmath>
#include <memory>
#include <vector>
#include <map>
#include <string>
#include <sstream>
#include <iostream>
using uint32=unsigned;using uint8=unsigned char;
enum {TARGET_FLAG_ITEM=1,TARGET_FLAG_DEST_LOCATION=2,TARGET_FLAG_SOURCE_LOCATION=4,
 SPELL_EFFECT_OPEN_LOCK=10,SPELL_EFFECT_SKINNING=11,SPELL_EFFECT_SUMMON_OBJECT_SLOT1=12,
 SPELL_EFFECT_SUMMON_OBJECT_SLOT2=13,SPELL_EFFECT_SUMMON_OBJECT_SLOT3=14,SPELL_EFFECT_SUMMON_OBJECT_SLOT4=15,
 UNIT_STAT_CHASE=1,UNIT_STAT_FOLLOW=2,UNIT_STAND_STATE_STAND=0,GAMEOBJECT_TYPE_CHEST=1,GO_JUST_DEACTIVATED=1,MAX_EFFECT_INDEX=3};
enum SpellCastResult {SPELL_CAST_OK,SPELL_FAILED_NO_POWER};
enum class BotState {BOT_STATE_NON_COMBAT};
struct ObjectGuid {unsigned id=0;ObjectGuid(unsigned i=0):id(i){}operator bool()const{return id!=0;}
 bool operator!=(ObjectGuid g)const{return id!=g.id;}void Clear(){id=0;}};
struct Item {bool inUse=false;};
struct SpellEntry {unsigned Id=1,Targets=TARGET_FLAG_DEST_LOCATION,Effect[3]{};bool channel=false;unsigned casttime=1000,duration=1000;} entry;
struct WorldObject {bool world=true;unsigned mapId=575,instance=1,phase=1;float GetPositionX(){return 1;}float GetPositionY(){return 2;}float GetPositionZ(){return 3;}
 ObjectGuid GetObjectGuid(){return 1;}unsigned GetMapId(){return mapId;}bool IsInWorld(){return world;}
 bool IsInMap(WorldObject*o){return o&&world&&o->world&&mapId==o->mapId&&instance==o->instance&&phase==o->phase;}};
struct GameObject:WorldObject {unsigned GetGoType(){return 0;}ObjectGuid GetOwnerGuid(){return 1;}void SetOwnerGuid(ObjectGuid){}
 void SetLootState(unsigned){}unsigned GetSpellId(){return 1;}};
struct Map {GameObject* GetGameObject(ObjectGuid){return nullptr;}};
struct Unit:WorldObject {};
struct Pet:Unit {bool HasSpell(unsigned){return false;}};
struct MotionMaster {};
struct TradeData {unsigned saved=0;void SetSpell(unsigned i){saved=i;}};
struct Player:Unit {bool falling=false,stand=true;TradeData* trade=nullptr;MotionMaster mm;Map map;ObjectGuid m_ObjectSlotGuid[4];
 Pet* GetPet(){return nullptr;}MotionMaster* GetMotionMaster(){return &mm;}bool IsFlying(){return false;}bool IsTaxiFlying(){return false;}
 bool IsStandState(){return stand;}void SetStandState(unsigned){stand=true;}void clearUnitState(unsigned){}
 ObjectGuid GetSelectionGuid(){return 1;}void SetSelectionGuid(ObjectGuid){}float GetOrientation(){return 0;}
 float GetAngleAt(float,float,float,float){return 0;}void GetPosition(float&x,float&y,float&z){x=1;y=2;z=3;}
 void UpdateAllowedPositionZ(float&,float&,float&){}bool IsFalling(){return falling;}TradeData* GetTradeData(){return trade;}
 Map* GetMap(){return &map;}void RemoveGameObject(GameObject*,bool,bool){}
};
struct Facade {bool moving=false;const SpellEntry* LookupSpellInfo(unsigned){return &entry;}bool isMoving(Player*){return moving;}
 void SetFacingTo(Player*,float){}bool isSpawned(GameObject*){return true;}}sServerFacade;
struct Config {unsigned globalCoolDown=1500;}sPlayerbotAIConfig;
struct WorldLocation {float coord_x=0,coord_y=0,coord_z=0;};
struct LastMovement {void Set(void*){}};
struct LastSpellCast {unsigned count=0;void Set(unsigned,ObjectGuid,time_t){++count;}};
struct Position {void Reset(){}};
namespace ai {using PositionMap=std::map<std::string,Position>;bool pause=false;
 bool ShouldAvoidEncounterOffense(Player*,Unit*,const SpellEntry*,Unit*){return pause;}}
struct LootObject {ObjectGuid guid;bool IsLootPossible(Player*){return true;}};
struct LootObjectStack {void Add(ObjectGuid){}};
template<class T>struct Value {using Base=typename std::remove_reference<T>::type;Base data{};T Get(){return data;}operator T(){return data;}void Set(Base v){data=v;}};
struct Context {template<class T>Value<T>* GetValue(std::string,unsigned=0){static Value<T> v;return &v;}}context;
#define AI_VALUE(type,name) context->GetValue<type>(name)->Get()
struct SpellCastTargets {Item* item=nullptr;void setItemTarget(Item*i){item=i;}Item* getItemTarget(){return item;}
 void setDestination(float,float,float){}void setUnitTarget(Unit*){}void setGOTarget(GameObject*){}};
struct Spell {static int live,cancels;static SpellCastResult result;static std::vector<Spell*> events;
 Item* item=nullptr;SpellCastTargets m_targets;Spell(Player*,const SpellEntry*,bool){++live;}~Spell(){--live;if(item)item->inUse=false;}
 void SetCastItem(Item*i){item=i;if(item)item->inUse=true;}Item* GetCastItem(){return item;}
 void cancel(){++cancels;}unsigned GetCastTime(){return entry.casttime;}
 SpellCastResult SpellStart(SpellCastTargets*t){m_targets=*t;events.push_back(this);return result;}
};int Spell::live=0,Spell::cancels=0;SpellCastResult Spell::result=SPELL_CAST_OK;std::vector<Spell*>Spell::events;
unsigned GetSpellCastTime(const SpellEntry*s,Player*,Spell*){return s->casttime;}
bool IsChanneledSpell(const SpellEntry*s){return s->channel;}unsigned GetSpellDuration(const SpellEntry*s){return s->duration;}
struct ChatHelper {static std::string formatSpell(const SpellEntry*){return "spell";}};
struct PlayerbotAI {Player* bot;Context* aiObjectContext=&context;bool jumping=false,master=false;unsigned waits=0;
 bool IsJumping(){return jumping;}bool HasActivePlayerMaster(){return master;}void StopMoving(){sServerFacade.moving=false;}
 void SetAIInternalUpdateDelay(unsigned){}void WaitForSpellCast(Spell*){++waits;}unsigned GetSpellCastDuration(Spell*){return 1000;}
 bool HasStrategy(const char*,BotState){return false;}Player* GetMaster(){return nullptr;}void TellPlayerNoFacing(Player*,std::ostringstream&){}
 GameObject* GetGameObject(ObjectGuid){return nullptr;}Unit* GetUnit(ObjectGuid){return nullptr;}Context* GetAiObjectContext(){return aiObjectContext;}
 bool UnitCast(Unit*,Item*,bool);bool ObjectCast(GameObject*,Item*,bool);
 bool CastPetSpell(unsigned,Unit*){return true;}
 bool CastSpell(uint32,Unit*,Item*,bool,uint32*);bool CastSpell(uint32,GameObject*,Item*,bool,uint32*);
 bool CastSpell(uint32,float,float,float,Item*,bool,uint32*);
};
__FUNCTIONS__
int main(){
 Player bot;PlayerbotAI ai{&bot};Unit target;GameObject go;Item item;TradeData trade;
 auto drain=[](){for(Spell*s:Spell::events)delete s;Spell::events.clear();assert(Spell::live==0);};
 auto invoke=[&](int type){return type==0?ai.UnitCast(&target,&item,true):type==1?ai.ObjectCast(&go,&item,true):ai.CastSpell(1,1,2,3,&item,true,nullptr);};
 for(int type=0;type<3;++type){
  for(int failure=0;failure<3;++failure){
   sServerFacade.moving=true;ai.jumping=failure==0;bot.falling=failure==1;ai.master=false;
   assert(!invoke(type));assert(Spell::events.empty());assert(Spell::live==0&&!item.inUse);
  }
  sServerFacade.moving=false;ai.jumping=false;bot.falling=false;
  Spell::result=SPELL_FAILED_NO_POWER;unsigned waits=ai.waits;
  assert(!invoke(type));assert(ai.waits==waits&&Spell::events.size()==1&&Spell::live==1);drain();
  Spell::result=SPELL_CAST_OK;assert(invoke(type));assert(Spell::events.size()==1&&Spell::live==1);drain();
 }
 entry.Targets=0;assert(!ai.CastSpell(1,1,2,3,&item,true,nullptr)&&Spell::live==0);
 entry.Targets=TARGET_FLAG_DEST_LOCATION;entry.Effect[0]=SPELL_EFFECT_OPEN_LOCK;
 assert(!ai.CastSpell(1,1,2,3,&item,true,nullptr)&&Spell::live==0);entry.Effect[0]=0;
 entry.Targets=TARGET_FLAG_ITEM;bot.trade=&trade;
 assert(ai.UnitCast(&target,&item,true)&&Spell::live==0&&!item.inUse&&trade.saved==1);
 assert(ai.CastSpell(1,1,2,3,&item,true,nullptr)&&Spell::live==0&&!item.inUse);
 bot.trade=nullptr;entry.Targets=TARGET_FLAG_DEST_LOCATION;
 auto admits=[&](){return ai.CastSpell(1,&target,nullptr,true,nullptr)&&ai.CastSpell(1,&go,nullptr,true,nullptr);};
 auto rejects=[&](){return !ai.CastSpell(1,&target,nullptr,true,nullptr)&&!ai.CastSpell(1,&go,nullptr,true,nullptr);};
 assert(admits());target.instance=go.instance=2;assert(rejects());target.instance=go.instance=1;
 target.phase=go.phase=2;assert(rejects());target.phase=go.phase=1;
 target.world=go.world=false;assert(rejects());target.world=go.world=true;
 bot.world=false;assert(rejects());bot.world=true;
 ai::pause=true;assert(rejects());ai::pause=false;assert(admits());
 std::cout<<"PASS: actual cast preparation lifetime in all dispatches, native failure ownership and ground-cast result\n";
}
'''.replace('__FUNCTIONS__','\n'.join(functions))
for era,realm in (('ZERO','classic'),('ONE','tbc'),('TWO','wotlk')):
    native=(root.parent/f'mangos-{realm}-behavior/src/game/Spells/Spell.cpp').read_text()
    start=block(native,'SpellCastResult Spell::SpellStart(')
    assert start.index('m_events.AddEvent(')<start.index('PreCastCheck()')
    with tempfile.TemporaryDirectory(prefix='mantech-cast-lifetime-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
