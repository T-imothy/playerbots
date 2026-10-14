"""Execute native-facing Garr allocation, casting, handoff and position bodies."""
from pathlib import Path
import ast, subprocess, tempfile, re
r=Path(__file__).resolve().parents[1]
tree=ast.parse((r/'tests/molten_core_support_regression.py').read_text())
node=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
while isinstance(node,ast.Call): node=node.func.value
code=ast.literal_eval(node)
code=code[:code.index('__METHODS__')]
code=re.sub(r'Unit\*GarrTankTarget\(PlayerbotAI\*\)\{return nullptr;\}Unit\*GarrBanishTarget\(PlayerbotAI\*\)\{return nullptr;\}bool GarrTankHandoff\(PlayerbotAI\*,Unit\*\)\{return false;\}bool PlanGarrPosition\(PlayerbotAI\*,EncounterPosition&\)\{return false;\}', '', code)
code=code.replace('constexpr float M_PI=', 'constexpr float M_PI=')
code=code.replace('struct ObjectGuid{unsigned id=0;', 'struct ObjectGuid{unsigned GetCounter()const{return id;}unsigned id=0;')
code=code.replace('struct SpellEntry{unsigned Id=19775,Mechanic=MECHANIC_POLYMORPH;};', '''enum {SPELL_EFFECT_WEAPON_DAMAGE=1,SPELL_EFFECT_WEAPON_DAMAGE_NOSCHOOL,SPELL_EFFECT_NORMALIZED_WEAPON_DMG,SPELL_EFFECT_WEAPON_PERCENT_DAMAGE};
struct SpellEntry{unsigned Id=19775,Mechanic=MECHANIC_POLYMORPH;unsigned Effect[3]={0,0,0};bool damage=false;};
struct SpellAuraHolder{ObjectGuid caster;ObjectGuid GetCasterGuid(){return caster;}};''')
code=code.replace('std::set<unsigned>auras;', 'std::set<unsigned>auras;std::map<unsigned,SpellAuraHolder>holders;SpellAuraHolder*GetSpellAuraHolder(unsigned id){return holders.count(id)?&holders[id]:nullptr;}')
code=code.replace('struct Context{', '''#include "playerbot/strategy/GarrCombatPolicy.h"
namespace ai{struct GarrControl{ObjectGuid boss;GarrAllocation allocation;float laneAngle=0;};}
struct Context{Cached<ai::GarrControl>garr;''')
code=code.replace('if constexpr(std::is_same_v<T,ObjectGuid>)', 'if constexpr(std::is_same_v<T,ai::GarrControl>)return &garr;else if constexpr(std::is_same_v<T,ObjectGuid>)')
code,replaced=re.subn(r'float NativeEncounterSpellRadius\(unsigned id\)\{.*?\}', 'float NativeEncounterSpellRadius(unsigned id){return id==19497?15.0f:10.0f;}', code)
assert replaced==1
code+='''
namespace ai {
enum class CasterArea{None,Ground};
CasterArea CasterSpellArea(const std::string& n){return n=="rain of fire"||n=="blizzard"?CasterArea::Ground:CasterArea::None;}
bool CasterDamageSpell(const SpellEntry* s){return s&&s->damage;}
Unit* GarrBanishTarget(PlayerbotAI*);Unit* GarrFocusTarget(PlayerbotAI*);Unit* GarrTankTarget(PlayerbotAI*);
bool GarrTankHandoff(PlayerbotAI*,Unit*);bool PlanGarrPosition(PlayerbotAI*,EncounterPosition&);
bool GarrSpellAllowed(PlayerbotAI*,const std::string&,Unit*,const SpellEntry*);
bool GarrEncounterActive(PlayerbotAI*);
bool LavaTrashSpellAllowed(PlayerbotAI*,const std::string&,Unit*,const SpellEntry*){return true;}
}
'''
native=(r/'playerbot/strategy/actions/MoltenCoreGarrActions.cpp').read_text()
code+=native[native.index('using namespace ai;'):]
from behavior_regression import block
cc=(r/'playerbot/strategy/values/CcTargetValue.cpp').read_text()
code+=block(cc,'bool GarrBanishAssignment(')
code+=r'''
int main(){
 GarrAllocation pure;
 std::vector<uint32_t> locks={101,102,103,104},adds={201,202,203,204,205,206,207,208};
 pure.Reconcile(locks,adds,{},true);assert(pure.banishes.size()==4&&pure.focus==201);
 auto first=pure.banishes;adds.erase(adds.begin());pure.Reconcile(locks,adds,{},true);
 assert(pure.banishes==first&&pure.focus==202);
 pure.Reconcile(locks,adds,{{202,999}},true);assert(pure.focus==203); // human CC is protected
 pure.Reconcile(locks,adds,{{208,101}},false);assert(pure.banishes==first&&pure.focus==203);
 GarrAllocation joined;joined.Reconcile(locks,{205,206,207,208},{{205,104},{206,103},{207,102},{208,101}},true);
 assert(joined.banishes.size()==4&&joined.focus==0); // late join doesn't release a native banish
 // Variable raid composition: zero through eight warlocks, preserving one
 // initial kill add and releasing exactly one owned Banish per cleanup step.
 for(unsigned n=0;n<=8;++n){GarrAllocation a;std::vector<uint32_t> ls,live={201,202,203,204,205,206,207,208};
  for(unsigned k=0;k<n;++k)ls.push_back(101+k);a.Reconcile(ls,live,{},true);
  assert(a.banishes.size()==std::min(n,7u));std::map<uint32_t,uint32_t> native;
  for(auto pair:a.banishes)native[pair.second]=pair.first;
  while(a.focus){live.erase(std::find(live.begin(),live.end(),a.focus));a.Reconcile(ls,live,native,true);}
  unsigned remaining=live.size();while(!live.empty()){
   a.Reconcile(ls,live,native,false);assert(a.focus&&a.banishes.size()==remaining);
   unsigned selected=a.focus;a.Reconcile(ls,live,native,false);assert(a.focus==selected);
   live.erase(std::find(live.begin(),live.end(),selected));native.erase(selected);--remaining;
  }a.Reconcile(ls,live,native,false);assert(!a.focus&&a.banishes.empty());
 }
 Player mainTank,killTank,parkTank,warlocks[4],mage,melee;Group raid;
 mainTank.guid=1;killTank.guid=2;parkTank.guid=3;mainTank.tank=killTank.tank=parkTank.tank=true;
 PlayerbotAI tankAI(&mainTank),killAI(&killTank),parkAI(&parkTank),mageAI(&mage),meleeAI(&melee);
 mage.guid=10;mage.ranged=true;melee.guid=11;
 raid.Add(&mainTank);raid.Add(&killTank);raid.Add(&parkTank);raid.Add(&mage);raid.Add(&melee);
 std::vector<PlayerbotAI*> lockAI;
 for(unsigned i=0;i<4;i++){warlocks[i].guid=101+i;warlocks[i].cls=CLASS_WARLOCK;warlocks[i].ranged=true;raid.Add(&warlocks[i]);lockAI.push_back(new PlayerbotAI(&warlocks[i]));lockAI.back()->learned.insert("banish");}
 Unit garr,fire[8];garr.guid=1000;garr.entry=12057;garr.victim=&mainTank;
 units={&mainTank,&killTank,&parkTank,&mage,&melee,&garr};
 for(unsigned i=0;i<8;i++){fire[i].guid=201+i;fire[i].entry=12099;fire[i].victim=&killTank;units.push_back(&fire[i]);}
 for(auto* brain:{&tankAI,&killAI,&parkAI,&mageAI,&meleeAI})brain->context.possible.value={1000};
 for(auto* brain:lockAI)brain->context.possible.value={1000};
 assert(GarrEncounterActive(&mageAI));
 for(unsigned i=0;i<4;i++){
  Unit* target=GarrBanishTarget(lockAI[i]);assert(target==&fire[7-i]);
  EncounterPosition station;assert(PlanGarrPosition(lockAI[i],station)&&station.destination.x==warlocks[i].x&&station.destination.y==warlocks[i].y);
  warlocks[i].los=false;assert(PlanGarrPosition(lockAI[i],station)&&std::hypot(station.destination.x,station.destination.y)>=19);warlocks[i].los=true;
  target->auras.insert(710);target->holders[710].caster=warlocks[i].guid;
  assert(!GarrBanishTarget(lockAI[i])); // never cancel a working banish
  Unit* assigned=nullptr;assert(GarrBanishAssignment(lockAI[i],"banish",assigned)&&!assigned);
 }
 assert(GarrFocusTarget(&mageAI)==&fire[0]);assert(GarrTankTarget(&tankAI)==&garr);
 assert(GarrTankTarget(&killAI)==&fire[0]);assert(GarrTankTarget(&parkAI)==&fire[1]);
 assert(GarrTankHandoff(&parkAI,&fire[1]));assert(!GarrTankHandoff(&parkAI,&fire[0]));
 SpellEntry damage;damage.damage=true;
 assert(!GarrSpellAllowed(&mageAI,"blizzard",&fire[0],&damage));
 assert(!GarrSpellAllowed(&mageAI,"fireball",&fire[7],&damage));
 assert(!GarrSpellAllowed(&mageAI,"fireball",&garr,&damage));
 assert(GarrSpellAllowed(&mageAI,"fireball",&fire[0],&damage));
 SpellEntry physical;physical.Effect[0]=SPELL_EFFECT_WEAPON_DAMAGE;
 assert(!GarrSpellAllowed(&meleeAI,"mortal strike",&fire[7],&physical));
 fire[0].health=29;assert(!GarrSpellAllowed(&mageAI,"fireball",&fire[0],&damage)); // isolate before execute
 fire[0].x=24;for(unsigned i=1;i<4;i++)fire[i].x=-24;
 assert(GarrSpellAllowed(&mageAI,"fireball",&fire[0],&damage));
 fire[0].health=25;assert(!GarrSpellAllowed(&meleeAI,"mortal strike",&fire[0],&physical));
 EncounterPosition plan;assert(PlanGarrPosition(&meleeAI,plan));assert(std::hypot(plan.destination.x-fire[0].x,plan.destination.y)>=18);
 assert(PlanGarrPosition(&killAI,plan));assert(std::hypot(plan.destination.x,plan.destination.y)<=25);
 parkAI.path=false;assert(!PlanGarrPosition(&parkAI,plan));parkAI.path=true;
 for(unsigned i=0;i<4;i++)fire[i].alive=false;
 assert(GarrFocusTarget(&mageAI)==&garr);assert(!GarrBanishTarget(lockAI[0]));
 garr.alive=false;assert(!GarrFocusTarget(&mageAI));
 assert(GarrEncounterActive(&mageAI)); // Remaining native adds keep Garr's CC ownership exclusive.
 assert(!GarrSpellAllowed(lockAI[0],"banish",&fire[7],&damage)); // no post-kill renewal
 // Only the selected lock releases. The other three continue native renewals.
 for(int next=7;next>=4;--next){
  assert(!GarrFocusTarget(&mageAI)); // selected native Banish expires naturally
  fire[next].auras.clear();fire[next].holders.clear();
  assert(GarrFocusTarget(&mageAI)==&fire[next]);assert(GarrTankTarget(&tankAI)==&fire[next]);
  unsigned owner=7-next;assert(!GarrBanishTarget(lockAI[owner]));
  Unit* assigned=nullptr;assert(GarrBanishAssignment(lockAI[owner],"banish",assigned)&&!assigned);
  for(int held=next-1;held>=4;--held){unsigned lock=7-held;
   fire[held].auras.clear();fire[held].holders.clear();
   assert(GarrBanishTarget(lockAI[lock])==&fire[held]);
   assert(GarrSpellAllowed(lockAI[lock],"banish",&fire[held],&damage));
   assigned=nullptr;assert(GarrBanishAssignment(lockAI[lock],"banish",assigned)&&assigned==&fire[held]);
   fire[held].auras.insert(710);fire[held].holders[710].caster=warlocks[lock].guid;
  }
  fire[next].alive=false;
 }
 assert(!GarrFocusTarget(&mageAI));
 assert(!GarrEncounterActive(&mageAI)); // A retained corpse cannot block later trash control.
 Unit trash;trash.guid=5000;trash.entry=11665;units.push_back(&trash);
 assert(!GarrSpellAllowed(lockAI[0],"banish",&trash,&damage));
 trash.entry=11666;assert(!GarrSpellAllowed(lockAI[0],"banish on cc",&trash,&damage));
 Unit* assigned=nullptr;assert(GarrBanishAssignment(lockAI[0],"banish",assigned)&&!assigned);
 // A corpse disappearing must not re-enable generic MC trash Banish.
 units.erase(std::find(units.begin(),units.end(),&garr));
 assert(!GarrSpellAllowed(lockAI[0],"banish",&fire[7],&damage));
 units.push_back(&garr);
 garr.alive=true;garr.combat=false;assert(!GarrFocusTarget(&mageAI));assert(mageAI.context.garr.value.boss.IsEmpty());
 mageAI.real=true;assert(!GarrFocusTarget(&mageAI));
 for(auto* brain:lockAI)delete brain;
 std::cout<<"PASS Garr: stable/native/human banish ownership, one-add focus, tank handoffs, isolation, physical/AoE admission, retreat, boss-death cleanup and wipe reset\n";
}
'''
with tempfile.TemporaryDirectory(prefix='mantech-garr-') as tmp:
    folder=Path(tmp);(folder/'test.cpp').write_text(code)
    for era in ('ZERO','ONE','TWO'):
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'/I'+str(r),'test.cpp','/Fe:test.exe'],cwd=folder,check=True)
        subprocess.run([str(folder/'test.exe')],cwd=folder,check=True)
