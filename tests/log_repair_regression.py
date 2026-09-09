from pathlib import Path
import sys,subprocess,tempfile
import argparse
parser=argparse.ArgumentParser()
for era in ('classic','tbc','wotlk'): parser.add_argument('--'+era+'-core',required=True,type=Path)
args=parser.parse_args()
cores={era:getattr(args,era+'_core') for era in ('classic','tbc','wotlk')}
PB=Path(__file__).resolve().parents[1]
def read(path): return path.read_text(encoding='utf-8-sig')
def block(s,marker):
 a=s.index(marker);b=s.index('{',a);depth=0
 for i in range(b,len(s)):
  depth+=(s[i]=='{')-(s[i]=='}')
  if not depth:return s[a:i+1]
 raise ValueError(marker)
fixture=r'''
#include <cassert>
#include <vector>
#include <set>
#include <cstdint>
using uint32=uint32_t; using uint64=uint64_t; using int32=int32_t;
using SpellEffectIndex=int;
const int EFFECT_INDEX_2=2,SPELL_AURA_DUMMY=4,SPELLMOD_COST=2;
const int TRIGGERED_IGNORE_GCD=512,TRIGGERED_IGNORE_CURRENT_CASTED_SPELL=4096,TRIGGERED_IGNORE_HIT_CALCULATION=2,TRIGGERED_HIDE_CAST_IN_COMBAT_LOG=8192,TRIGGERED_OLD_TRIGGERED=1;
bool roll_chance_i(int){return false;} bool roll_chance_f(float){return false;}
struct SpellEntry {uint32 Id=0,SpellIconID=0,manaCost=0;uint64 Attributes=0;int value=0;bool seal=true;int CalculateSimpleValue(int)const{return value;}};
struct Storage {template<class T> const T* LookupEntry(uint32 id){static T entry;return id==123 ? &entry : nullptr;}} sSpellTemplate;
bool IsSealSpell(const SpellEntry* e){return e->seal;}
struct Unit; struct Player;
struct Modifier {int m_amount=0;};
struct Aura {SpellEntry info;int eff=2;Unit* caster=nullptr;Unit* target=nullptr;Modifier mod;const SpellEntry* GetSpellProto(){return &info;}int GetEffIndex(){return eff;}uint32 GetId(){return info.Id;}Modifier* GetModifier(){return &mod;}Unit* GetCaster(){return caster;}Unit* GetTarget(){return target;}};
struct Unit {using AuraList=std::vector<Aura*>;AuraList auras;std::vector<uint32> casts,removed;std::set<int> overrides;bool alive=true;bool IsAlive(){return alive;}AuraList const& GetAurasByType(int){return auras;}void RemoveAurasDueToSpell(uint32 id){removed.push_back(id);}void CastSpell(Unit*,uint32 id,int){assert(id);casts.push_back(id);}bool HasAura(int){return false;}bool HasOverrideScript(int id){return overrides.count(id);}Player* GetSpellModOwner(){return nullptr;}void CastCustomSpell(Unit*,int,int32*,void*,void*,int){} };
struct Player:Unit{void ApplySpellMod(uint32,int,int32&){} };
struct Spell {Unit* caster;Unit* target;Unit* GetCaster(){return caster;}Unit* GetUnitTarget(){return target;} };
struct SpellScript {virtual void OnEffectExecute(Spell*,SpellEffectIndex)const{};};
struct AuraScript {virtual void OnPeriodicTickEnd(Aura*)const{};};
'''
for era in ('classic','tbc'):
 root=cores[era]/'src/game/Spells/Scripts/Scripting/ClassScripts'
 code=fixture+block(read(root/'Paladin.cpp'),'struct spell_judgement')+';\n'
 if era=='classic':code+=block(read(root/'Mage.cpp'),'struct Blizzard')+';\n'
 code+=r'''
int main(){
 Unit caster,target;Spell spell{&caster,&target};spell_judgement script;
 script.OnEffectExecute(&spell,0);assert(caster.casts.empty()&&caster.removed.empty());
 Aura invalid;invalid.info.Id=77;caster.auras={&invalid};
 for(int n:{0,1,777}){invalid.info.value=n;script.OnEffectExecute(&spell,0);assert(caster.casts.empty()&&caster.removed.empty());}
 Aura valid;valid.info.Id=88;valid.info.value=123;caster.auras={&invalid,&valid};
 target.alive=false;script.OnEffectExecute(&spell,0);assert(caster.casts.empty());target.alive=true;
 script.OnEffectExecute(&spell,0);assert(caster.casts==std::vector<uint32>{123}&&caster.removed==std::vector<uint32>{88});
'''
 if era=='classic':code+=r'''
 Blizzard blizzard;Aura periodic;periodic.caster=&caster;periodic.target=&target;caster.casts.clear();
 blizzard.OnPeriodicTickEnd(&periodic);assert(caster.casts.empty());
 for(int n=0;n<3;++n){caster.overrides={n==0?836:n==1?988:989};blizzard.OnPeriodicTickEnd(&periodic);assert(caster.casts.back()==uint32(12484+n));}
'''
 code+='}\n'
 with tempfile.TemporaryDirectory(prefix='log-repair-test-') as t:
  p=Path(t);(p/'test.cpp').write_text(code);subprocess.run(['cl','/nologo','/EHsc','/std:c++17',str(p/'test.cpp'),'/Fe:'+str(p/'test.exe'),'/Fo:'+str(p/'test.obj')],check=True);subprocess.run([str(p/'test.exe')],check=True)
 print(era,'actual class-script code passed applicable seal, missing-trigger, dead-target and talent cases',flush=True)
s=read(PB/'playerbot/RandomPlayerbotMgr.cpp');method=block(s,'bool RandomPlayerbotMgr::ProcessBot(Player* player)');guard=block(method,'if (player->GetGuildId())')
code=r'''
#include <cassert>
using uint32=unsigned;using int32=int;
struct MemberSlot{uint32 accountId=0;};struct Guild{MemberSlot member;bool present=true;int rank=0;unsigned GetLeaderGuid(){return 1;}MemberSlot* GetMemberSlot(unsigned){return present?&member:nullptr;}int GetRank(unsigned){return rank;}};
struct GuildMgr{Guild* guild=nullptr;Guild* GetGuildById(unsigned){return guild;}}sGuildMgr;
struct Config{bool IsInRandomAccountList(unsigned n){return n==9;}}sPlayerbotAIConfig;
struct Player{unsigned guild=1;unsigned GetGuildId(){return guild;}unsigned GetObjectGuid(){return 2;}};
bool Check(Player* player){bool randomiser=true;
'''+guard+r'''
return randomiser;}
int main(){Player p;assert(!Check(&p));Guild g;sGuildMgr.guild=&g;assert(!Check(&p));g.member.accountId=5;g.rank=3;assert(!Check(&p));g.rank=4;assert(Check(&p));g.member.accountId=9;g.rank=0;assert(Check(&p));g.present=false;assert(!Check(&p));}
'''
with tempfile.TemporaryDirectory(prefix='guild-policy-test-') as t:
 p=Path(t);(p/'test.cpp').write_text(code);subprocess.run(['cl','/nologo','/EHsc','/std:c++17',str(p/'test.cpp'),'/Fe:'+str(p/'test.exe'),'/Fo:'+str(p/'test.obj')],check=True);subprocess.run([str(p/'test.exe')],check=True)
print('Actual guild policy passed offline-member account, ranks and missing-state tests without any DB API')
for era in ('classic','tbc','wotlk'):
 root=cores[era]/'src/game'
 s=read(root/'AI/EventAI/CreatureEventAI.cpp');a=s.index('case ACTION_T_SET_RANGED_MODE:');section=s[a:s.index('case ',a+10)]
 condition=section[section.index('if (')+4:section.index(')\n')]
 s=read(root/'Globals/ObjectMgr.cpp');a=s.index('if (itemTemplate->item == itemVendor->item');end=s.index(')',a);vendor=s[a+4:end]
 code=r'''
#include <cassert>
#include <initializer_list>
const int TYPE_NONE=0,TYPE_NO_MELEE_MODE=3;
struct Action {struct {int type;} rangedMode;} action;
struct Item{int item=1,conditionId=0,ExtendedCost=0;};
bool NeedsSpell(bool m_mainSpellInfo,int mode){action.rangedMode.type=mode;return CONDITION;}
bool Duplicate(Item* itemTemplate,Item* itemVendor){return VENDOR;}
int main(){assert(!NeedsSpell(false,0));assert(!NeedsSpell(false,3));for(int m:{1,2,4}){assert(NeedsSpell(false,m));assert(!NeedsSpell(true,m));}Item a,b;assert(Duplicate(&a,&b));b.conditionId=1;assert(!Duplicate(&a,&b));b.conditionId=0;EXTRA}
'''.replace('CONDITION',condition).replace('VENDOR',vendor).replace('EXTRA','b.ExtendedCost=1;assert(!Duplicate(&a,&b));' if era!='classic' else '')
 with tempfile.TemporaryDirectory(prefix='native-validation-test-') as t:
  p=Path(t);(p/'test.cpp').write_text(code);subprocess.run(['cl','/nologo','/EHsc','/std:c++17',str(p/'test.cpp'),'/Fe:'+str(p/'test.exe'),'/Fo:'+str(p/'test.obj')],check=True);subprocess.run([str(p/'test.exe')],check=True)
 print(era,'actual ranged-mode prerequisite and vendor matching tests passed')
