"""Compile actual party healing selection and incoming-cast lookup in each era."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/values/PartyMemberToHeal.cpp').read_text()
shared=(root/'playerbot/strategy/values/PartyMemberValue.cpp').read_text()
methods='\n'.join([block(source,'class IsTargetOfHealingSpell')+';',
    block(source,'uint32 getIncomingdamage('),block(shared,'bool PartyMemberValue::IsTargetOfSpellCast(')] +
    [block(source,key) for key in ('Unit* PartyMemberToHeal::Calculate(', 'bool PartyMemberToHeal::CanHealPet(',
     'bool PartyMemberToHeal::Check(', 'std::vector<Player*> PartyMemberToHeal::GetPartyMembers(')])
code=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <limits>
#include <list>
#include <map>
#include <string>
#include <type_traits>
#include <vector>
using uint32=unsigned;using uint64=unsigned long long;using uint8=unsigned char;using ObjectGuid=unsigned;
enum{UNIT_FIELD_MINDAMAGE=0,UNIT_FIELD_MAXDAMAGE=1,SPELL_AURA_MOD_HEALING_PCT=118,MINI_PET=1,POWER_MANA=0};
enum CurrentSpellTypes{CURRENT_GENERIC_SPELL=0,CURRENT_CHANNELED_SPELL=1,CURRENT_MAX_SPELL=2};
enum class BotState{BOT_STATE_COMBAT};
struct SpellEntry{bool healing=true;};
struct Targets{unsigned unit=0,corpse=0;unsigned getUnitTargetGuid(){return unit;}unsigned getCorpseTargetGuid(){return corpse;}};
constexpr uint32 SPELL_STATE_FINISHED=7;
struct Spell{SpellEntry* m_spellInfo=nullptr;Targets m_targets;bool finished=false;uint32 getState(){return finished ? SPELL_STATE_FINISHED : 0;}};
struct Unit{virtual ~Unit()=default;unsigned guid=0,hp=100,maxhp=100,map=533,instance=1,phase=1,absorb=0;
 bool alive=true,world=true,friendly=true,reach=true,fullHealWound=false;float distance=0,damage=0;int healing=0;
 mutable unsigned attackerReads=0;std::vector<Unit*> attackers;
 virtual bool IsPlayer(){return false;}unsigned GetHealth()const{return hp;}unsigned GetMaxHealth()const{return maxhp;}
 float GetHealthPercent()const{return maxhp?100.f*hp/maxhp:0;}ObjectGuid GetObjectGuid(){return guid;}
 bool IsAlive(){return alive;}bool IsInWorld(){return world;}unsigned GetMapId(){return map;}
 bool IsInMap(Unit* u){return u&&world&&u->world&&map==u->map&&instance==u->instance&&phase==u->phase;}
 int GetMaxNegativeAuraModifier(unsigned){return healing;}
 const std::vector<Unit*>& getAttackers()const{++attackerReads;return attackers;}
 bool CanReachWithMeleeAttack(const Unit*){return reach;}float GetFloatValue(unsigned){return damage;}
};
struct Pet:Unit{unsigned petType=0;unsigned getPetType(){return petType;}};
struct Player;
// Encounter timing is compiled separately in healing_window_regression.py.
unsigned UpcomingEncounterHealingWindow(Player*,Unit*){return 0;}
bool NeedsFullHealingToRemoveAura(Unit* u){return u && u->fullHealWound && u->hp < u->maxhp;}
unsigned RemainingHealingAbsorb(Unit* u){return u?u->absorb:0;}
struct Corpse{unsigned guid=500;unsigned GetObjectGuid(){return guid;}};
struct Duel{Unit* opponent=nullptr;};struct Group;
struct Player:Unit{bool teleport=false,bg=false,tank=false,healer=false,safe=true,hasAI=true;
 unsigned selection=0,mana=100,maxmana=100;Pet* pet=nullptr;Duel* duel=nullptr;Corpse* corpse=nullptr;
 Group* group=nullptr;Spell* casts[2]{};
 bool IsPlayer()override{return true;}bool IsBeingTeleported(){return teleport;}bool InBattleGround(){return bg;}
 unsigned GetSelectionGuid(){return selection;}unsigned GetInstanceId(){return instance;}
 Pet* GetPet(){return pet;}bool IsInGroup(Player* p){return group&&group==p->group;}Group* GetGroup(){return group;}
 void* GetPlayerbotAI(){return hasAI?this:nullptr;}unsigned GetPower(unsigned){return mana;}unsigned GetMaxPower(unsigned){return maxmana;}
 Corpse* GetCorpse(){return corpse;}bool IsNonMeleeSpellCasted(bool){return casts[0]||casts[1];}
 Spell* GetCurrentSpell(CurrentSpellTypes type){return casts[type];}
};
struct GroupReference{Player* source=nullptr;GroupReference* following=nullptr;Player* getSource(){return source;}GroupReference* next(){return following;}};
struct Group{std::vector<GroupReference> refs;GroupReference* GetFirstMember(){return refs.empty()?nullptr:&refs[0];}
 void Set(std::initializer_list<Player*> players){refs.clear();for(auto p:players){refs.push_back({p});p->group=this;}
 for(size_t i=0;i+1<refs.size();++i)refs[i].following=&refs[i+1];}};
struct GuidPosition{Unit* unit=nullptr;operator bool()const{return unit;}Unit* GetCreature(unsigned){return unit;}};
struct PlayerbotAI{Player* bot;std::map<unsigned,Unit*> units;bool preheal=false,focus=false;
 std::list<ObjectGuid> nearest,focused;GuidPosition rpg;
 static bool IsHealSpell(const SpellEntry* s){return s&&s->healing;}
 bool HasStrategy(std::string name,BotState){return name=="preheal"?preheal:focus;}
 Unit* GetUnit(unsigned id){auto it=units.find(id);return it==units.end()?nullptr:it->second;}
 bool IsTank(Player* p){return p->tank;}bool IsHeal(Player* p){return p->healer;}bool IsSafe(Player* p){return p&&p->safe;}
 float GetRange(const char*){return 40;}
 template<class T>T value(std::string key){if constexpr(std::is_same_v<T,GuidPosition>)return rpg;
 else return key=="focus heal targets"?focused:nearest;}
};
struct Facade{bool IsFriendlyTo(Unit*,Unit* u){return u&&u->friendly;}bool IsAlive(Unit* u){return u&&u->alive;}
 float GetDistance2d(Unit*,Unit* u){return u->distance;}}sServerFacade;
struct Config{unsigned almostFullHealth=95,lowMana=20,criticalHealth=20,lowHealth=50;}sPlayerbotAIConfig;
struct SpellEntryPredicate{virtual bool Check(const SpellEntry*)=0;};
struct PartyMemberValue{PlayerbotAI* ai;Player* bot;bool IsTargetOfSpellCast(Unit*,SpellEntryPredicate&);};
struct PartyMemberToHeal:PartyMemberValue{Unit* Calculate();bool CanHealPet(Pet*);bool Check(Unit*);std::vector<Player*> GetPartyMembers();};
#define AI_VALUE(type,key) ai->value<type>(key)
__METHODS__
int main(){
 Player bot,owner,healer,a,b;bot.guid=1;owner.guid=2;healer.guid=3;a.guid=4;b.guid=5;
 Pet pet;pet.guid=6;owner.pet=&pet;PlayerbotAI ai{&bot};Group group;group.Set({&bot,&owner});
 ai.units={{1,&bot},{2,&owner},{3,&healer},{4,&a},{5,&b},{6,&pet}};
 PartyMemberToHeal selector;selector.ai=&ai;selector.bot=&bot;
 assert(selector.Calculate()==nullptr); // full-health pet no longer fabricates work
 owner.hp=98;assert(selector.Calculate()==nullptr);owner.fullHealWound=true;
 assert(selector.Calculate()==&owner);owner.fullHealWound=false;owner.hp=100;
 owner.absorb=60000;assert(selector.Calculate()==&owner);owner.absorb=0;
 pet.hp=40;assert(selector.Calculate()==&pet);
 SpellEntry heal;Spell healing{&heal,{pet.guid,0}};healer.casts[0]=&healing;ai.nearest={healer.guid};
 assert(selector.Calculate()==nullptr); // the pet, not its owner, is already being healed
 healing.m_targets.unit=owner.guid;assert(selector.Calculate()==&pet);
 healing.m_targets.unit=pet.guid;healing.finished=true;assert(selector.Calculate()==&pet);healing.finished=false;
 healer.phase=2;assert(selector.Calculate()==&pet);healer.phase=1;healer.teleport=true;assert(selector.Calculate()==&pet);healer.teleport=false;
 ai.nearest.clear();pet.alive=false;assert(selector.Calculate()==nullptr);pet.alive=true;
 pet.instance=2;assert(selector.Calculate()==nullptr);pet.instance=1;pet.healing=-100;assert(selector.Calculate()==nullptr);pet.healing=0;
 pet.petType=MINI_PET;assert(selector.Calculate()==nullptr);pet.petType=0;pet.hp=100;
 owner.hp=20;Unit enemy;enemy.damage=50;owner.attackers={&enemy};ai.preheal=true;
 assert(getIncomingdamage(&owner)==20);owner.attackerReads=0;
 assert(selector.Calculate()==&owner&&owner.attackerReads==1); // saturate, never wrap into healthy range
 enemy.damage=std::numeric_limits<float>::max();assert(getIncomingdamage(&owner)==20);
 enemy.damage=-5;assert(getIncomingdamage(&owner)==0);enemy.damage=std::numeric_limits<float>::quiet_NaN();assert(getIncomingdamage(&owner)==0);
 enemy.damage=50;ai.preheal=false;owner.attackerReads=0;assert(selector.Calculate()==&owner&&owner.attackerReads==0);
 owner.phase=2;assert(selector.Calculate()==nullptr);owner.phase=1;owner.teleport=true;assert(selector.Calculate()==nullptr);owner.teleport=false;
 owner.friendly=false;assert(selector.Calculate()==nullptr);owner.friendly=true;owner.maxhp=0;assert(selector.Calculate()==nullptr);owner.maxhp=100;
 bot.bg=true;owner.distance=25;assert(selector.Calculate()==nullptr);bot.bg=false;assert(selector.Calculate()==&owner);owner.distance=0;
 owner.hp=100;ai.rpg.unit=&pet;pet.hp=40;pet.instance=2;assert(selector.Calculate()==nullptr);pet.instance=1;assert(selector.Calculate()==&pet);ai.rpg.unit=nullptr;
 // De-duplicate selected+group candidates before distributing two healers.
 owner.pet=nullptr;a.hp=10;b.hp=20;healer.healer=true;group.Set({&healer,&bot,&a,&b});bot.selection=a.guid;
 assert(selector.Calculate()==&a);healer.maxmana=0;assert(selector.Calculate()==&a);healer.maxmana=100;
 // Low-health cloth wearer outranks a much healthier tank with more missing HP.
 bot.selection=0;a.hp=30;b.maxhp=10000;b.hp=9000;b.tank=true;
 assert(selector.Calculate()==&a); // healer index must stay within the urgent band
 // An incoming cast is not a guarantee that a critically injured player is safe.
 a.hp=10;healing.m_targets.unit=a.guid;healer.casts[0]=&healing;ai.nearest={healer.guid};
 assert(selector.Calculate()==&a);ai.nearest.clear();b.tank=false;b.maxhp=100;
 // Absorb amount competes with ordinary missing health; actual critical health wins.
 healer.maxmana=0;ai.preheal=false;a.hp=100;a.absorb=60000;b.hp=50;
 assert(selector.Calculate()==&a);b.hp=10;assert(selector.Calculate()==&b);
 a.absorb=0;a.hp=10;b.hp=20;healer.maxmana=100;
 bot.selection=0;ai.preheal=true;ai.nearest.clear();a.attackers={&enemy};b.attackers={&enemy};
 a.attackerReads=b.attackerReads=0;selector.Calculate();assert(a.attackerReads==1&&b.attackerReads==1);
 // Focus list must not downcast a pet/creature to Player.
 ai.focus=true;ai.focused={pet.guid,a.guid};assert(selector.GetPartyMembers().size()==1&&selector.GetPartyMembers()[0]==&a);ai.focus=false;
 // Existing resurrection corpse matching and soulstone/player targeting remain.
 Corpse corpse;a.corpse=&corpse;a.alive=false;healing.m_targets={0,corpse.guid};ai.nearest={healer.guid};
 IsTargetOfHealingSpell predicate;assert(selector.IsTargetOfSpellCast(&a,predicate));
 healing.m_targets={b.guid,0};assert(selector.IsTargetOfSpellCast(&b,predicate)&&!selector.IsTargetOfSpellCast(&pet,predicate));
 healing.m_spellInfo=nullptr;assert(!selector.IsTargetOfSpellCast(&b,predicate));
 std::cout<<"PASS: actual healer selection, saturated forecasts, one scan/candidate, pet cast recipients, deduplication and lifecycle\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-heal-selection-') as directory:
        tmp=Path(directory);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
