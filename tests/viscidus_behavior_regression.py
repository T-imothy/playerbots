"""Execute actual frost admission, cast rechecks and native-freeze CC policy."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/ViscidusFrostAction.cpp').read_text()
methods='\n'.join(block(source,name) for name in ('bool ai::IsViscidusShatterTarget(', 'uint32 ViscidusFrostAction::GetFrostSpell(', 'bool ViscidusFrostAction::isUseful(', 'bool ViscidusFrostAction::Execute('))
code=r'''
#include <cassert>
#include <map>
#include <set>
#include <string>
#include <iostream>
using uint32=unsigned;
enum{CLASS_MAGE=8,CLASS_SHAMAN=7,CLASS_DEATH_KNIGHT=6,SPELL_SCHOOL_MASK_FROST=16};
struct SpellEntry{unsigned id,school=16;};unsigned GetSpellSchoolMask(const SpellEntry*s){return s->school;}
struct Unit{unsigned entry=15299,guid=1,phase=1;bool world=true,alive=true,combat=true,charm=false,valid=true,cc=false;std::set<std::pair<unsigned,unsigned>>auras;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charm;}
 unsigned GetEntry(){return entry;}unsigned GetObjectGuid(){return guid;}
 bool HasAura(unsigned id){for(auto a:auras)if(a.first==id)return true;return false;}
 bool GetSpellAuraHolder(unsigned id,unsigned caster){return auras.count({id,caster});}};
struct Group{};
struct Player:Unit{unsigned map=531,cls=CLASS_MAGE;bool teleport=false;Group*group=nullptr;std::set<unsigned>known;
 unsigned GetMapId(){return map;}unsigned getClass(){return cls;}bool HasSpell(unsigned id){return known.count(id);}bool IsBeingTeleported(){return teleport;}
 bool IsInMap(Unit*u){return u&&phase==u->phase;}Group*GetGroup(){return group;}};
struct PlayerbotAI{Player*bot;Unit*target=nullptr;bool real=false,heal=false,tank=false,canCast=true,castResult=true,allowed=true;unsigned last=0;
 bool IsRealPlayer(){return real;}bool IsHeal(Player*){return heal;}bool IsTank(Player*){return tank;}
 bool CanCastSpell(unsigned,Unit*u,unsigned mask,bool learned){assert(mask==0&&learned&&u==target);return canCast;}
 bool CastSpell(unsigned id,Unit*u,void*,bool wait,unsigned*duration){assert(!wait&&u==target);last=id;*duration=1500;return castResult;}
 template<class T>T value(std::string key){assert(key=="current target");return target;}
 template<class T>T qualified(std::string key,std::string name){assert(key=="spell cast useful"&&(name=="frostbolt"||name=="frost shock"||name=="icy touch"));return allowed;}};
struct Facade{std::map<unsigned,SpellEntry>spells;const SpellEntry*LookupSpellInfo(unsigned id){return spells.count(id)?&spells[id]:nullptr;}}sServerFacade;
struct Config{float sightDistance=60;}sPlayerbotAIConfig;
struct PossibleTargetsValue{static bool IsValid(Unit*u,Player*,bool){return u->valid;}};
struct PossibleAttackTargetsValue{static bool IsPossibleTarget(Unit*u,Player*,float,bool ignore){assert(!ignore);return !u->cc;}};
struct Event{};
struct ViscidusFrostAction{PlayerbotAI*ai;Player*bot;unsigned duration=0;void SetDuration(unsigned d){duration=d;}unsigned GetFrostSpell();bool isUseful();bool Execute(Event&);};
namespace ai{bool IsViscidusShatterTarget(Unit*,Player*);}
#define AI_VALUE(type,key) ai->value<type>(key)
#define AI_VALUE2(type,key,q) ai->qualified<type>(key,q)
__METHODS__
int main(){Group group;Player bot;bot.group=&group;Unit boss;boss.auras={{25926,1}};PlayerbotAI brain{&bot,&boss};ViscidusFrostAction a{&brain,&bot};Event event;
 sServerFacade.spells={{116,{116}},{8056,{8056}},{45477,{45477}}};bot.known={116,8056,45477};
 assert(a.GetFrostSpell()==116&&a.isUseful());assert(a.Execute(event)&&brain.last==116&&a.duration==1500);
 bot.cls=CLASS_SHAMAN;assert(a.GetFrostSpell()==8056);bot.cls=CLASS_DEATH_KNIGHT;
#ifdef MANGOSBOT_TWO
 assert(a.GetFrostSpell()==45477);
#else
 assert(!a.GetFrostSpell());
#endif
 bot.cls=CLASS_MAGE;bot.known.erase(116);assert(!a.isUseful());bot.known.insert(116);
 brain.canCast=false;assert(!a.isUseful()&&!a.Execute(event));brain.canCast=true;
 brain.allowed=false;assert(!a.isUseful()&&!a.Execute(event));brain.allowed=true; // Explicit skipped spell.
 brain.castResult=false;assert(!a.Execute(event));brain.castResult=true;
 sServerFacade.spells[116].school=20;assert(!a.isUseful());sServerFacade.spells[116].school=16; // Native requires pure frost.
 boss.auras={{25926,99}};assert(!a.isUseful());boss.auras={{25926,1},{25937,1}};assert(!a.isUseful()&&ai::IsViscidusShatterTarget(&boss,&bot));
 boss.auras={{25937,99}};assert(!ai::IsViscidusShatterTarget(&boss,&bot));boss.auras={{25926,1}};
 brain.heal=true;assert(!a.isUseful());brain.heal=false;brain.tank=true;assert(!a.isUseful());brain.tank=false;
 brain.real=true;assert(!a.isUseful());brain.real=false;boss.cc=true;assert(!a.isUseful());boss.cc=false;
 bot.teleport=true;assert(!a.isUseful());bot.teleport=false;boss.phase=2;assert(!a.isUseful());boss.phase=1;
 boss.combat=false;assert(!a.isUseful());boss.combat=true;boss.entry=1;assert(!a.isUseful());boss.entry=15299;
 bot.map=0;assert(!a.isUseful());bot.map=531;assert(a.isUseful());
 std::cout<<"PASS: pure-frost learned ranks, native phase ownership, roles, cast rechecks and shatter CC exception\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-viscidus-bot-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
cc=(root/'playerbot/strategy/values/PossibleAttackTargetsValue.cpp').read_text()
for signature in ('bool PossibleAttackTargetsValue::HasBreakableCC(', 'bool PossibleAttackTargetsValue::HasUnBreakableCC('):
    assert block(cc,signature).split('{',1)[1].strip().startswith('if (IsViscidusShatterTarget(target, player)) return false;')
assert 'IsCcTarget(target, player)' in block(cc,'bool PossibleAttackTargetsValue::IsPossibleTarget(')
for era in ('classic','tbc','wotlk'):
    native=(root.parent/f'mangos-{era}-behavior/src/game/AI/ScriptDevAI/scripts/kalimdor/temple_of_ahnqiraj/boss_viscidus.cpp').read_text()
    assert 'procData.spell->GetSchoolMask() == SPELL_SCHOOL_MASK_FROST' in native
    assert 'procData.attType == BASE_ATTACK || procData.attType == OFF_ATTACK' in native
print('PASS: actual native hit counters and explicit CC assignments remain intact')
