# Reproduce dynamic ranged spell selection before the real spell-capability gate.
from pathlib import Path
import subprocess,tempfile,sys
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/GenericSpellActions.cpp').read_text()
pull=(root/'playerbot/strategy/actions/PullActions.cpp').read_text()
if '--before' in sys.argv:
 source=subprocess.check_output(['git','-c','safe.directory='+root.as_posix(),'-C',str(root),'show','0df8d31e45508c41fe04748ac7a493fd9c01cc51:playerbot/strategy/actions/GenericSpellActions.cpp'],text=True)
if '--before' in sys.argv:
 pull=subprocess.check_output(['git','-c','safe.directory='+root.as_posix(),'-C',str(root),'show','0df8d31e45508c41fe04748ac7a493fd9c01cc51:playerbot/strategy/actions/PullActions.cpp'],text=True)
# Reuse only interface fixtures; execute the full production base usefulness function.
fixture=(root/'tests/reflect_cast_regression.py').read_text().split("code = r'''"+"\n",1)[1].split("int main(){",1)[0]
fixture=fixture.replace('using uint32=unsigned;','using uint32=unsigned;\nconstexpr int INVENTORY_SLOT_BAG_0=0,EQUIPMENT_SLOT_RANGED=17,ITEM_SUBCLASS_WEAPON_GUN=3,ITEM_SUBCLASS_WEAPON_BOW=2,ITEM_SUBCLASS_WEAPON_CROSSBOW=18,ITEM_SUBCLASS_WEAPON_WAND=19,ITEM_SUBCLASS_WEAPON_THROWN=16;\nstruct ItemPrototype {int SubClass;unsigned Delay=2000;};struct Item {ItemPrototype proto;const ItemPrototype* GetProto()const{return &proto;}};\nstruct Config {unsigned globalCoolDown=1500;}sPlayerbotAIConfig;')
fixture=fixture.replace('struct Player:Unit {','struct Player:Unit {Item* weapon=nullptr;const Item* GetItemByPos(int,int){return weapon;}')
fixture=fixture.replace('struct PlayerbotAI {bool learned=true;bool HasSpell(unsigned){return learned;}', 'struct PlayerbotAI {Player* bot=nullptr;std::set<unsigned> spells;bool GetSpellRange(std::string,float* r){*r=30;return true;}bool learned=true;bool HasSpell(unsigned id){return learned&&spells.count(id);}')
start=fixture.index('struct CastSpellAction {');end=fixture.index('__METHOD__',start)
fixture=fixture[:start]+r'''
unsigned Resolve(std::string n){if(n=="shoot bow")return 2480;if(n=="shoot gun")return 7918;if(n=="shoot crossbow")return 7919;if(n=="throw")return 2764;if(n=="shoot")return 5019;return 0;}
struct CastSpellAction {Player* bot;PlayerbotAI* ai;Unit* target=nullptr;unsigned spellId=0;float range=30;std::string spellName;bool useful=true;
 CastSpellAction(PlayerbotAI*a,std::string n):bot(a->bot),ai(a),spellName(n){}virtual ~CastSpellAction()=default;
 void RefreshSpellId(){spellId=ai->HasSpell(Resolve(spellName))?Resolve(spellName):0;}
 Unit* GetTarget(){return target;}virtual bool isUseful();void SetSpellName(std::string n){spellName=n;RefreshSpellId();}std::string GetSpellName(){return spellName;}
};
#define AI_VALUE2(type,key,value) useful
'''+fixture[end:]
fixture=fixture.replace('__METHOD__',block(source,'bool CastSpellAction::isUseful('))
method='bool isUseful() override;' if 'bool CastShootAction::isUseful()' in source else ''
fixture+=r'''
#undef AI_VALUE2
unsigned ammo=200;
#define AI_VALUE2(type,key,value) ammo
struct CastShootAction:CastSpellAction {const Item* rangedWeapon=nullptr;unsigned weaponDelay=0;bool needsAmmo=false;
 CastShootAction(PlayerbotAI*a):CastSpellAction(a,"shoot"){}void UpdateWeaponInfo();__DECL__};
'''.replace('__DECL__',method)
fixture+=block(source,'void CastShootAction::UpdateWeaponInfo(')+'\n'
if method:fixture+=block(source,'bool CastShootAction::isUseful(')+'\n'
fixture+=r'''
struct PullStrategy {static PullStrategy* current;static PullStrategy* Get(PlayerbotAI*){return current;}std::string spell;std::string GetSpellName(){return spell;}};PullStrategy* PullStrategy::current=nullptr;
struct PullAction:CastSpellAction{PullAction(PlayerbotAI*a):CastSpellAction(a,"pull action"){InitPullAction();}void InitPullAction();__PULL_DECL__};
'''.replace('__PULL_DECL__','bool isUseful() override;' if 'bool PullAction::isUseful()' in pull else '')
fixture+=block(pull,'void PullAction::InitPullAction(')+'\n'
if 'bool PullAction::isUseful()' in pull:fixture+=block(pull,'bool PullAction::isUseful(')+'\n'
fixture+=r'''
int main(){
 Player bot;Unit enemy;PlayerbotAI ai;ai.bot=&bot;Item bow{{ITEM_SUBCLASS_WEAPON_BOW}},gun{{ITEM_SUBCLASS_WEAPON_GUN}},wand{{ITEM_SUBCLASS_WEAPON_WAND}};
#ifdef MANGOSBOT_ZERO
 ai.spells={2480,7918};
#else
 ai.spells={5019};
#endif
 PullAction pullAction(&ai);pullAction.target=&enemy;PullStrategy strategy;
#ifdef MANGOSBOT_ZERO
 strategy.spell="shoot bow";
#else
 strategy.spell="shoot";
#endif
 PullStrategy::current=&strategy;
#ifdef EXPECT_BEFORE
 assert(!pullAction.isUseful());
#else
 assert(pullAction.isUseful());PullStrategy::current=nullptr;assert(!pullAction.isUseful());PullStrategy::current=&strategy;
#endif
 bot.weapon=&bow;CastShootAction shoot(&ai);shoot.target=&enemy;
 bool ready=shoot.isUseful();
#ifdef EXPECT_BEFORE
#ifdef MANGOSBOT_ZERO
 if(ready)return 1;std::cout<<"REPRODUCED: equipped bow rejected before weapon-specific spell selection\n";
#else
 if(!ready)return 1;std::cout<<"CONTROL: generic Shoot works in later expansions\n";
#endif
#else
 assert(ready);bot.weapon=&gun;assert(shoot.isUseful());
#ifdef MANGOSBOT_ZERO
 assert(shoot.GetSpellName()=="shoot gun");ammo=0;assert(!shoot.isUseful());ammo=200;
#endif
 bot.weapon=nullptr;assert(!shoot.isUseful());bot.weapon=&bow;assert(shoot.isUseful());
 ai.learned=false;assert(!shoot.isUseful());ai.learned=true;
 bot.weapon=&wand;ai.spells.insert(5019);ammo=0;assert(shoot.isUseful());
 enemy.world=false;assert(!shoot.isUseful());
 std::cout<<"PASS: weapon resolved before capability checks; weapon swap, no weapon, ammo, unlearned spell, wand and invalid target\n";
#endif
}
'''
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='bot-ranged-readiness-') as folder:
  tmp=Path(folder);(tmp/'test.cpp').write_text(fixture)
  flags=['/DEXPECT_BEFORE'] if '--before' in sys.argv else []
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}',*flags,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
  subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
