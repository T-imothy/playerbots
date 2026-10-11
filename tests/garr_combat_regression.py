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
code=code.replace('struct ObjectGuid{unsigned id=0;', 'struct ObjectGuid{unsigned GetCounter()const{return id;}bool IsEmpty()const{return !id;}unsigned id=0;')
code=code.replace('struct SpellEntry{unsigned Id=19775;};', '''enum {SPELL_EFFECT_WEAPON_DAMAGE=1,SPELL_EFFECT_WEAPON_DAMAGE_NOSCHOOL,SPELL_EFFECT_NORMALIZED_WEAPON_DMG,SPELL_EFFECT_WEAPON_PERCENT_DAMAGE};
struct SpellEntry{unsigned Id=19775;unsigned Effect[3]={0,0,0};bool damage=false;};
struct SpellAuraHolder{ObjectGuid caster;ObjectGuid GetCasterGuid(){return caster;}};''')
code=code.replace('std::set<unsigned>auras;', 'std::set<unsigned>auras;std::map<unsigned,SpellAuraHolder>holders;SpellAuraHolder*GetSpellAuraHolder(unsigned id){return holders.count(id)?&holders[id]:nullptr;}')
code=code.replace('struct Context{', '''#include "playerbot/strategy/GarrCombatPolicy.h"
namespace ai{struct GarrControl{ObjectGuid boss;GarrAllocation allocation;float laneAngle=0;};}
struct Context{Cached<ai::GarrControl>garr;''')
code=code.replace('if constexpr(std::is_same_v<T,ObjectGuid>)', 'if constexpr(std::is_same_v<T,ai::GarrControl>)return &garr;else if constexpr(std::is_same_v<T,ObjectGuid>)')
code=code.replace('assert(id==19408||id==20602);return id==19408?45.0f:10.0f;', 'return id==19497?15.0f:10.0f;')
code+='''
namespace ai {
enum class CasterArea{None,Ground};
CasterArea CasterSpellArea(const std::string& n){return n=="rain of fire"||n=="blizzard"?CasterArea::Ground:CasterArea::None;}
bool CasterDamageSpell(const SpellEntry* s){return s&&s->damage;}
Unit* GarrBanishTarget(PlayerbotAI*);Unit* GarrFocusTarget(PlayerbotAI*);Unit* GarrTankTarget(PlayerbotAI*);
bool GarrTankHandoff(PlayerbotAI*,Unit*);bool PlanGarrPosition(PlayerbotAI*,EncounterPosition&);
bool GarrSpellAllowed(PlayerbotAI*,const std::string&,Unit*,const SpellEntry*);
}
'''
native=(r/'playerbot/strategy/actions/MoltenCoreGarrActions.cpp').read_text()
code+=native[native.index('using namespace ai;'):]
code+=r'''
int main(){
 GarrAllocation pure;
 std::vector<uint32_t> locks={101,102,103,104},adds={201,202,203,204,205,206,207,208};
 pure.Reconcile(locks,adds,{},true);assert(pure.banishes.size()==4&&pure.focus==201);
 auto first=pure.banishes;adds.erase(adds.begin());pure.Reconcile(locks,adds,{},true);
 assert(pure.banishes==first&&pure.focus==202);
 pure.Reconcile(locks,adds,{{202,999}},true);assert(pure.focus==203); // human CC is protected
 pure.Reconcile(locks,adds,{{208,101}},false);assert(pure.banishes.empty()&&pure.focus==203);
 GarrAllocation joined;joined.Reconcile(locks,{205,206,207,208},{{205,104},{206,103},{207,102},{208,101}},true);
 assert(joined.banishes.size()==4&&joined.focus==0); // late join doesn't release a native banish
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
 for(unsigned i=0;i<4;i++){
  Unit* target=GarrBanishTarget(lockAI[i]);assert(target==&fire[7-i]);
  target->auras.insert(710);target->holders[710].caster=warlocks[i].guid;
  assert(!GarrBanishTarget(lockAI[i])); // never cancel a working banish
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
 assert(!GarrSpellAllowed(lockAI[0],"banish",&fire[7],&damage)); // no post-kill renewal
 fire[4].auras.clear();fire[4].holders.clear();assert(GarrFocusTarget(&mageAI)==&fire[4]);
 assert(GarrTankTarget(&tankAI)==&fire[4]); // boss tank joins post-kill cleanup
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
