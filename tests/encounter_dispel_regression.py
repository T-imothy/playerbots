"""Actual dispel policy/selector/trigger bodies and native dispel-mask helpers."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
policy=(root/'playerbot/strategy/actions/EncounterDispelPolicy.cpp').read_text()
policy='\n'.join(line for line in policy.splitlines() if not line.startswith('#include'))
selector=(root/'playerbot/strategy/values/PartyMemberToDispel.cpp').read_text()
trigger=(root/'playerbot/strategy/triggers/CureTriggers.cpp').read_text()
methods='\n'.join((block(selector,'class PartyMemberToDispelPredicate')+';',
                   block(selector,'Unit* PartyMemberToDispel::Calculate('),
                   block(trigger,'bool NeedCureTrigger::IsActive('),
                   block(trigger,'Value<Unit*>* PartyMemberNeedCureTrigger::GetTargetValue(')))
generic=(root/'playerbot/strategy/actions/GenericSpellActions.cpp').read_text()
assert 'ShouldAvoidEncounterDispel' in block(generic,'bool CastSpellAction::isUseful(')
execute=block(generic,'bool CastSpellAction::Execute(')
assert execute.index('ShouldAvoidEncounterDispel') < execute.index('executed = ai->CastSpell(spellName')
assert 'std::to_string(dispelType) + "," + GetSpellName()' in (root/'playerbot/strategy/actions/GenericSpellActions.h').read_text()
code=r'''
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <list>
#include <map>
#include <set>
#include <string>
#include <type_traits>
#include <vector>
using uint32=unsigned;using ObjectGuid=unsigned;
enum DispelType{DISPEL_NONE=0,DISPEL_MAGIC=1,DISPEL_CURSE=2,DISPEL_DISEASE=3,DISPEL_POISON=4,DISPEL_ALL=7,DISPEL_ZG_TICKET=10};
constexpr unsigned DISPEL_ALL_MASK=0x1e,MAX_EFFECT_INDEX=3,SPELL_EFFECT_DISPEL=38,SPELL_EFFECT_APPLY_AURA=6,
 SPELL_AURA_PERIODIC_TRIGGER_SPELL=23,MINI_PET=1,SUMMON_PET=2;
__NATIVE_MASK__
struct SpellEntry{unsigned Id=0,Effect[3]{},EffectApplyAuraName[3]{},EffectTriggerSpell[3]{};int EffectMiscValue[3]{};};
struct Unit{virtual ~Unit()=default;unsigned map=533,phase=1,entry=0;bool world=true,alive=true,charmed=false,combat=true,friendly=true;
 float distance=0;std::set<unsigned> auras,cures;bool IsInWorld(){return world;}bool IsAlive(){return alive;}
 bool HasCharmer(){return charmed;}bool IsInCombat(){return combat;}bool HasAura(unsigned id){return auras.count(id);}
 unsigned GetMapId(){return map;}unsigned GetEntry(){return entry;}};
struct Group;
struct Player:Unit{bool teleport=false;Group* group=nullptr;bool IsBeingTeleported(){return teleport;}
 bool IsInMap(Unit* unit){return unit&&world&&unit->world&&map==unit->map&&phase==unit->phase;}Group* GetGroup(){return group;}};
struct Pet:Unit{unsigned type=0;unsigned getPetType(){return type;}};
struct GroupReference{Player* source;GroupReference* following=nullptr;Player* getSource(){return source;}GroupReference* next(){return following;}};
struct Group{GroupReference* first;GroupReference* GetFirstMember(){return first;}};
template<class T>struct Value{T value{};T Get(){return value;}};
struct Context{Value<std::list<ObjectGuid>> attackers;Value<Unit*> party;std::string lastQualifier;
 template<class T>Value<T>* GetValue(const char*,std::string q=""){
  if constexpr(std::is_same_v<T,std::list<ObjectGuid>>)return &attackers;else{lastQualifier=q;return &party;}}};
struct PlayerbotAI{Player* bot;Context context;std::map<ObjectGuid,Unit*> units;std::map<std::string,unsigned> spellIds;
 Player* GetBot(){return bot;}Context* GetAiObjectContext(){return &context;}float GetRange(const char*){return 30;}
 Unit* GetUnit(ObjectGuid guid){auto i=units.find(guid);return i==units.end()?nullptr:i->second;}
 bool HasAuraToDispel(Unit*,unsigned);};
struct Facade{std::map<unsigned,SpellEntry> spells;bool IsFriendlyTo(Unit*,Unit* target){return target->friendly;}
 bool IsAlive(Unit* u){return u&&u->alive;}float GetDistance2d(Unit*,Unit* u){return u?u->distance:999;}
 const SpellEntry* LookupSpellInfo(unsigned id){auto i=spells.find(id);return i==spells.end()?nullptr:&i->second;}}sServerFacade;
namespace ai{bool IsProtectedEncounterDispel(Unit*,uint32);bool ShouldAvoidEncounterDispel(PlayerbotAI*,const SpellEntry*,Unit*);}
__POLICY__
using namespace ai;
bool PlayerbotAI::HasAuraToDispel(Unit* u,unsigned type){return u&&u->world&&bot->IsInMap(u)&&u->cures.count(type)&&!IsProtectedEncounterDispel(u,type);}
struct FindPlayerPredicate{virtual bool Check(Unit*)=0;};struct PlayerbotAIAware{PlayerbotAI* ai;PlayerbotAIAware(PlayerbotAI* a):ai(a){}};
struct PartyMemberToDispel{PlayerbotAI* ai;std::string qualifier;std::vector<Unit*> members;Unit* Calculate();
 Unit* FindPartyMember(FindPlayerPredicate& predicate){for(Unit* member:members)if(predicate.Check(member))return member;return nullptr;}};
struct NeedCureTrigger{PlayerbotAI* ai;Unit* target;std::string spell;unsigned dispelType=DISPEL_MAGIC;
 Unit* GetTarget(){return target;}bool IsActive();};
struct PartyMemberNeedCureTrigger:NeedCureTrigger{Context* context;Value<Unit*>* GetTargetValue();};
#define AI_VALUE2(type,key,value) ai->spellIds[value]
__METHODS__
int main(){
 Player bot,infected,healthy;PlayerbotAI ai{&bot};Unit boss;boss.entry=15931;boss.friendly=false;ai.units[1]=&boss;
 GroupReference ref{&infected};Group group{&ref};bot.group=infected.group=healthy.group=&group;
 SpellEntry cure;cure.Id=528;cure.Effect[0]=SPELL_EFFECT_DISPEL;cure.EffectMiscValue[0]=DISPEL_DISEASE;
 SpellEntry cleanse=cure;cleanse.Id=4987;cleanse.Effect[1]=cleanse.Effect[2]=SPELL_EFFECT_DISPEL;
 cleanse.EffectMiscValue[0]=DISPEL_POISON;cleanse.EffectMiscValue[1]=DISPEL_DISEASE;cleanse.EffectMiscValue[2]=DISPEL_MAGIC;
 SpellEntry magic=cure;magic.Id=527;magic.EffectMiscValue[0]=DISPEL_MAGIC;
 SpellEntry abolish=cure;abolish.Id=552;abolish.Effect[1]=SPELL_EFFECT_APPLY_AURA;
 abolish.EffectApplyAuraName[1]=SPELL_AURA_PERIODIC_TRIGGER_SPELL;abolish.EffectTriggerSpell[1]=10872;
 SpellEntry totem;totem.Id=8170;SpellEntry other;other.Id=5394;
 sServerFacade.spells={{528,cure},{4987,cleanse},{527,magic},{552,abolish},{10872,cure},{8170,totem}};
 ai.spellIds={{"cleanse",4987},{"dispel magic",527},{"cure disease",528},{"abolish disease",552}};
 infected.auras={28169};infected.cures=healthy.cures={DISPEL_MAGIC,DISPEL_DISEASE,DISPEL_POISON};
 assert(IsProtectedEncounterDispel(&infected,DISPEL_DISEASE)&&IsProtectedEncounterDispel(&infected,DISPEL_ALL));
 assert(!IsProtectedEncounterDispel(&infected,DISPEL_MAGIC)&&!IsProtectedEncounterDispel(&infected,32));
 assert(ShouldAvoidEncounterDispel(&ai,&cure,&infected)&&ShouldAvoidEncounterDispel(&ai,&cleanse,&infected));
 assert(!ShouldAvoidEncounterDispel(&ai,&magic,&infected)&&!ShouldAvoidEncounterDispel(&ai,&cure,&healthy));
 assert(!ShouldAvoidEncounterDispel(&ai,&other,&infected));
 PartyMemberToDispel selector{&ai,"1,cleanse",{&infected,&healthy}};
 assert(selector.Calculate()==&healthy); // Do not loop on the first unsafe Cleanse recipient.
 selector.qualifier="1,dispel magic";assert(selector.Calculate()==&infected); // Magic-only cure remains allowed.
 selector.qualifier="1";assert(selector.Calculate()==&infected); // Legacy type-only value callers remain compatible.
 selector.qualifier="3";assert(selector.Calculate()==&healthy);
 NeedCureTrigger trigger{&ai,&infected,"cleanse",DISPEL_MAGIC};assert(!trigger.IsActive());
 trigger.spell="dispel magic";assert(trigger.IsActive());
 PartyMemberNeedCureTrigger party;party.ai=&ai;party.context=&ai.context;party.spell="cleanse";party.dispelType=DISPEL_MAGIC;
 party.GetTargetValue();assert(ai.context.lastQualifier=="1,cleanse");
 assert(ShouldAvoidEncounterDispel(&ai,&totem,&bot)); // Live injection remains after boss dies.
 infected.auras.clear();assert(!ShouldAvoidEncounterDispel(&ai,&totem,&bot));
 ai.context.attackers.value={1};assert(ShouldAvoidEncounterDispel(&ai,&totem,&bot)&&ShouldAvoidEncounterDispel(&ai,&abolish,&healthy));
 assert(!ShouldAvoidEncounterDispel(&ai,&cure,&healthy)); // Ordinary direct cures remain available before injection.
 boss.combat=false;assert(!ShouldAvoidEncounterDispel(&ai,&totem,&bot));boss.combat=true;
 boss.phase=2;assert(!ShouldAvoidEncounterDispel(&ai,&totem,&bot));boss.phase=1;boss.world=false;
 assert(!ShouldAvoidEncounterDispel(&ai,&totem,&bot));boss.world=true;ai.context.attackers.value.clear();
 infected.auras={28169};infected.phase=2;assert(!ShouldAvoidEncounterDispel(&ai,&totem,&bot));infected.phase=1;
 infected.teleport=true;assert(!ShouldAvoidEncounterDispel(&ai,&totem,&bot));infected.teleport=false;
 infected.charmed=true;assert(!ShouldAvoidEncounterDispel(&ai,&totem,&bot));infected.charmed=false;
 bot.map=0;assert(!ShouldAvoidEncounterDispel(&ai,&cure,&infected));bot.map=533;
 bot.teleport=true;assert(!ShouldAvoidEncounterDispel(&ai,&totem,&bot));bot.teleport=false;
 assert(!ShouldAvoidEncounterDispel(&ai,nullptr,&infected));
 SpellEntry malformed=cure;malformed.EffectMiscValue[0]=32;assert(!ShouldAvoidEncounterDispel(&ai,&malformed,&infected));
 malformed.EffectMiscValue[0]=31;assert(!ShouldAvoidEncounterDispel(&ai,&malformed,&infected));
 malformed.EffectMiscValue[0]=-1;assert(!ShouldAvoidEncounterDispel(&ai,&malformed,&infected));
 std::cout<<"PASS: actual native-mask dispel guard, multi-effect Cleanse, periodic/totem prevention and spell-aware party selection\n";
}
'''.replace('__POLICY__',policy).replace('__METHODS__',methods)
for era,realm in (('ZERO','classic'),('ONE','tbc'),('TWO','wotlk')):
    native=(root.parent/f'mangos-{realm}-behavior/src/game/Spells/SpellMgr.h').read_text()
    fixture=code.replace('__NATIVE_MASK__',block(native,'inline uint32 GetDispellMask('))
    with tempfile.TemporaryDirectory(prefix='mantech-encounter-dispel-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(fixture)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
