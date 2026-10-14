"""Run real trash allocation and native-facing decisions across every era."""
from pathlib import Path
import ast,re,subprocess,tempfile
R=Path(__file__).resolve().parents[1]
tree=ast.parse((R/'tests/molten_core_support_regression.py').read_text())
node=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
while isinstance(node,ast.Call):node=node.func.value
code=ast.literal_eval(node);code=code[:code.index('__METHODS__')]
code=code.replace('struct ObjectGuid{unsigned id=0;','struct ObjectGuid{unsigned GetCounter()const{return id;}unsigned id=0;')
code=code.replace('struct SpellEntry{unsigned Id=19775,Mechanic=MECHANIC_POLYMORPH;};', '''enum{SPELL_EFFECT_WEAPON_DAMAGE=1,SPELL_EFFECT_WEAPON_DAMAGE_NOSCHOOL,SPELL_EFFECT_NORMALIZED_WEAPON_DMG,SPELL_EFFECT_WEAPON_PERCENT_DAMAGE,TYPEID_UNIT=1,TYPEID_PLAYER=2};
struct SpellEntry{unsigned Id=19775,Mechanic=MECHANIC_POLYMORPH;unsigned Effect[3]={};bool damage=false;};
struct SpellAuraHolder{ObjectGuid caster;ObjectGuid GetCasterGuid(){return caster;}};
struct Reference{ObjectGuid guid;ObjectGuid getUnitGuid()const{return guid;}};
struct ThreatManager{std::list<Reference*>refs;const std::list<Reference*>&getThreatList(){return refs;}};''')
code=code.replace('std::set<unsigned>auras;', '''std::set<unsigned>auras;Unit*GetOwner(){return owner;}
 std::map<unsigned,SpellAuraHolder>holders;SpellAuraHolder*GetSpellAuraHolder(unsigned s){return holders.count(s)?&holders[s]:nullptr;}
 ThreatManager threat;ThreatManager&getThreatManager(){return threat;}unsigned GetTypeId(){return IsPlayer()?TYPEID_PLAYER:TYPEID_UNIT;}bool CanInitiateAttack(){return true;}bool CanAttackOnSight(Unit*){return !friendly;}float GetAttackDistance(Unit*){return 12;}''')
code=code.replace('GroupReference*GetFirstMember(){', '''ObjectGuid GetLeaderGuid(){return refs.empty()?ObjectGuid():refs.front().p->GetObjectGuid();}
 unsigned GetId(){return 1;}
 bool IsMember(ObjectGuid guid)const{for(const auto&ref:refs)if(ref.p->guid==guid)return true;return false;}
 GroupReference*GetFirstMember(){''')
code=code.replace('struct Context{', '''#include "playerbot/strategy/LavaTrashCombatPolicy.h"
namespace ai{struct LavaTrashControl{LavaTrashAllocation allocation;unsigned groupId=0,map=0,instance=0,observedAt=0;std::vector<ObjectGuid>observedElementals,observedPriorities;};}
struct Context{Cached<ai::LavaTrashControl>lava;''')
code=code.replace('if constexpr(std::is_same_v<T,ai::GeddonControl>)','if constexpr(std::is_same_v<T,ai::LavaTrashControl>)return &lava;else if constexpr(std::is_same_v<T,ai::GeddonControl>)')
if 'HasRealPlayerMaster()' not in code:
 code=code.replace('bool IsRealPlayer(){return real;}','bool IsRealPlayer(){return real;}bool owned=true;bool HasRealPlayerMaster(){return owned;}')
stubs='Unit*LavaTrashBanishTarget(PlayerbotAI*){return nullptr;}bool LavaTrashReservedTarget(PlayerbotAI*,Unit*){return false;}bool PlanLavaTrashCarrier(PlayerbotAI*,EncounterPosition&){return false;}bool PlanLavaTrashBanish(PlayerbotAI*,EncounterPosition&){return false;}'
assert stubs in code;code=code.replace(stubs,'')
from behavior_regression import block
for signature in ('bool MoltenCoreGroupEnemy(', 'bool MoltenCoreRecoveryTrash('):code=code.replace(block(code,signature),'')
# Replace the support fixture's small fire-position boundary with the native
# route fixture's map-aware version; keep one common HazardPosition type.
code=code.replace('struct WorldPosition{float x=0,y=0,z=0;float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}};',
    'struct WorldPosition{unsigned map;float x,y,z;WorldPosition(unsigned m,float a,float b,float c):map(m),x(a),y(b),z(c){}WorldPosition(Unit*u):WorldPosition(u->map,u->x,u->y,u->z){}unsigned getMapId()const{return map;}float getX()const{return x;}float getY()const{return y;}float getZ()const{return z;}};')
code+='''
struct WorldObject{};
unsigned now=1000;struct WorldTimer{static unsigned getMSTime(){return now;}static unsigned getMSTimeDiff(unsigned a,unsigned b){return b-a;}};
namespace ai{
bool MoltenCoreGroupEnemy(PlayerbotAI*,Unit*);bool MoltenCoreRecoveryTrash(unsigned);Unit*MoltenCoreTrashAggroTarget(PlayerbotAI*);
bool garrActive=false;bool GarrEncounterActive(PlayerbotAI*){return garrActive;}
enum class CasterArea{None,Ground};CasterArea CasterSpellArea(const std::string&name){return name=="blizzard"?CasterArea::Ground:CasterArea::None;}
bool CasterDamageSpell(const SpellEntry*spell){return spell&&spell->damage;}
Unit*LavaTrashBanishTarget(PlayerbotAI*);Unit*LavaTrashFocusTarget(PlayerbotAI*);bool LavaTrashReservedTarget(PlayerbotAI*,Unit*);
bool LavaTrashCombatActive(PlayerbotAI*);
bool LavaTrashSpellAllowed(PlayerbotAI*,const std::string&,Unit*,const SpellEntry*);bool PlanLavaTrashCarrier(PlayerbotAI*,EncounterPosition&);bool PlanLavaTrashBanish(PlayerbotAI*,EncounterPosition&);
bool LavaTrashRouteSafe(PlayerbotAI*,const std::vector<WorldPosition>&);
}
'''
# The focus object interface is irrelevant to the controlled grid visitor, but
# retain the native predicates and complete route segment implementation.
native=(R/'playerbot/strategy/actions/MoltenCoreLavaTrashActions.cpp').read_text()
native=native[native.index('using namespace ai;'):]
native=native.replace('WorldObject const& GetFocusObject() const { return *bot; }','Player const& GetFocusObject() const { return *bot; }')
from behavior_regression import block
safety=(R/'playerbot/strategy/actions/MovementPathSafety.h').read_text()
code+='namespace ai{'+block(safety,'inline bool IsFiniteMovementPoint(')+block(safety,'inline bool IsHazardSafeSegment(')+'}\n'
code+=native
code+=r'''
int main(){
 LavaTrashAllocation allocation;std::vector<uint32_t>owners{1,2,3,4};std::vector<uint32_t>adds{101,102};
 allocation.Reconcile(owners,adds,{},true);assert(allocation.banishes.size()==2&&allocation.banishes.at(1)==101&&allocation.banishes.at(2)==102);
 std::map<uint32_t,uint32_t>auras{{101,1},{102,2}};allocation.Reconcile(owners,adds,auras,false);assert(allocation.focus==101&&allocation.released.count(101)&&!allocation.Reserved(101)&&allocation.Reserved(102));
 allocation.Reconcile(owners,adds,auras,false);assert(allocation.focus==101&&allocation.banishes.size()==1); // still waiting for native expiry, no rebanish
 allocation.Reconcile(owners,{102},{{102,2}},false);assert(allocation.focus==102&&allocation.banishes.empty()&&allocation.released.count(102));
 allocation.Reconcile(owners,{101,102,103,104},{},true);assert(!allocation.Reserved(101)&&!allocation.Reserved(102)&&allocation.banishes.size()==2); // second pack cannot rebanish released GUIDs
 LavaTrashAllocation doubled;doubled.Reconcile(owners,{1,2,3,4},{},true);assert(doubled.banishes.size()==4);
 doubled.Reconcile(owners,{1,2,3,4},{},false);for(unsigned target=1;target<=4;++target){assert(doubled.focus==target&&doubled.released.count(target));std::vector<uint32_t>left;for(unsigned i=target+1;i<=4;++i)left.push_back(i);doubled.Reconcile(owners,left,{},false);}
 LavaTrashAllocation human;human.Reconcile(owners,{1,2},{{1,99}},true);assert(!human.banishes.count(99)&&human.banishes.size()==1);human.Reconcile(owners,{1,2},{{1,99}},false);assert(human.focus==2);

 Player tank,casters[4],dps;Group group;tank.guid=10;tank.tank=true;group.Add(&tank);PlayerbotAI tankAI(&tank);
 std::vector<PlayerbotAI*>locks;for(unsigned i=0;i<4;++i){casters[i].guid=20+i;casters[i].cls=CLASS_WARLOCK;casters[i].ranged=true;casters[i].x=-20;group.Add(&casters[i]);locks.push_back(new PlayerbotAI(&casters[i]));locks.back()->learned={"banish"};}
 dps.guid=30;dps.ranged=true;dps.x=-20;group.Add(&dps);PlayerbotAI damageAI(&dps);
 Unit elemental[4],danger[2],unpulled,otherRaid;for(unsigned i=0;i<4;++i){elemental[i].guid=100+i;elemental[i].entry=i%2?12100:12076;elemental[i].x=5+i;}
 for(unsigned i=0;i<2;++i){danger[i].guid=200+i;danger[i].entry=i?11667:11666;danger[i].x=5;danger[i].victim=&tank;}
 for(unsigned i=0;i<2;++i)elemental[i].victim=&tank;for(unsigned i=2;i<4;++i)elemental[i].combat=false;
 unpulled.guid=300;unpulled.entry=12076;unpulled.combat=false;unpulled.x=35;
 Player stranger;stranger.guid=999;otherRaid.guid=301;otherRaid.entry=12076;otherRaid.victim=&stranger;
 units={&tank,&dps,&unpulled,&otherRaid};for(auto&caster:casters)units.push_back(&caster);for(auto&target:elemental)units.push_back(&target);for(auto&target:danger)units.push_back(&target);
 elemental[0].entry=11665;assert(LavaTrashBanishTarget(locks[0])==&elemental[0]);assert(LavaTrashBanishTarget(locks[1])==&elemental[1]);assert(!LavaTrashBanishTarget(locks[2])&&!LavaTrashBanishTarget(locks[3]));
 garrActive=true;assert(!LavaTrashBanishTarget(locks[0])&&!LavaTrashFocusTarget(&damageAI));garrActive=false;
 assert(LavaTrashReservedTarget(&tankAI,&elemental[0])&&LavaTrashReservedTarget(&tankAI,&elemental[1])&&!LavaTrashReservedTarget(&tankAI,&unpulled));
 damageAI.context.attack.value=elemental[1].guid;locks[1]->context.attack.value=elemental[1].guid;
 assert(LavaTrashBanishTarget(locks[1])==&elemental[1]); // Attack on a Reaver does not cancel its reservation.
 EncounterPosition station;assert(PlanLavaTrashBanish(locks[0],station)&&station.destination.x==casters[0].x); // cast from native usable range; do not reposition first
 SpellEntry damage;damage.damage=true;assert(!LavaTrashSpellAllowed(&damageAI,"frostbolt",&elemental[0],&damage));assert(!LavaTrashSpellAllowed(&damageAI,"fear",&danger[0],&damage));assert(!LavaTrashSpellAllowed(&damageAI,"blizzard",&danger[0],&damage));
 assert(LavaTrashFocusTarget(&damageAI)==&danger[0]);assert(LavaTrashSpellAllowed(&damageAI,"frostbolt",&danger[0],&damage));assert(!LavaTrashSpellAllowed(&damageAI,"frostbolt",&danger[1],&damage));
 for(unsigned i=0;i<2;++i){elemental[i].auras={18647};elemental[i].holders[18647].caster=casters[i].guid;}
 assert(!LavaTrashBanishTarget(locks[0])); // never recast an active native Banish
 for(unsigned i=2;i<4;++i){elemental[i].combat=true;elemental[i].victim=&tank;}now+=201;
 assert(LavaTrashBanishTarget(locks[2])==&elemental[2]&&LavaTrashBanishTarget(locks[3])==&elemental[3]);
 for(auto&target:danger)target.alive=false;assert(!LavaTrashBanishTarget(locks[0])&&!LavaTrashFocusTarget(&damageAI));
 elemental[0].auras.clear();elemental[0].holders.clear();assert(!LavaTrashBanishTarget(locks[0])&&LavaTrashFocusTarget(&damageAI)==&elemental[0]);
 elemental[0].alive=false;assert(!LavaTrashBanishTarget(locks[1]));elemental[1].auras.clear();elemental[1].holders.clear();assert(LavaTrashFocusTarget(&damageAI)==&elemental[1]);
 // A dead/removed controller and ordinary reset cannot lose the release record.
 tank.world=false;assert(!LavaTrashBanishTarget(locks[0])&&!LavaTrashBanishTarget(locks[1]));tank.world=true;
 elemental[1].victim=&dps;dps.attackers={&elemental[1]};damageAI.context.possible.value={elemental[1].guid};assert(PlanLavaTrashCarrier(&damageAI,station)&&station.destination.x==tank.x&&station.source==tank.guid);
 tank.alive=false;assert(!PlanLavaTrashCarrier(&damageAI,station));tank.alive=true;
 std::vector<WorldPosition>route{WorldPosition(409,0,0,0),WorldPosition(409,50,0,0)};assert(!LavaTrashRouteSafe(&damageAI,route));unpulled.combat=true;otherRaid.combat=true;assert(LavaTrashRouteSafe(&damageAI,route));
 assert(locks[0]->context.lava.value.allocation.released.count(100)&&locks[0]->context.lava.value.allocation.released.count(101));
 for(auto*lock:locks)delete lock;
 std::cout<<"PASS real trash allocation/native membership, two/four locks, sequential release, reset/controller loss, carrier-to-tank and unpulled route guard\n";
}
'''
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='lava-native-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(code,encoding='utf-8')
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','/I'+str(R),'test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
 print('PASS Lava trash',era,flush=True)
