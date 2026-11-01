"""Compile complete cast and target-recovery methods against controlled interfaces.

Reproduces a decision-turn regression, not native timing or full class rotations.
An injured ally is available while no hostile replacement is available. Native
casts complete between decisions; the engine stops on a successful action.
--history also compares both sides of the introducing recovery commit.
"""
from pathlib import Path
import subprocess,sys,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
def git(*args):
 return subprocess.check_output(['git','-c','safe.directory='+root.as_posix(),'-C',str(root),*args],text=True)
recovery_path='playerbot/strategy/actions/ChooseTargetActions.cpp'
cast_source=(root/'playerbot/PlayerbotAI.cpp').read_text()
versions=[('corrected recovery',(root/recovery_path).read_text(),12)]
if '--history' in sys.argv:
 versions[:0]=[(label,git('show',rev+':'+recovery_path),count) for label,rev,count in
 [('before recovery change','d07d9dbe^',12),('introduced recovery change','d07d9dbe',6)]]
def cast_fixture(cast_source):
    """Compile the complete production Unit CastSpell path and exercise target cleanup."""
    from pathlib import Path
    import ast,subprocess,tempfile,sys
    from behavior_regression import block
    root=Path(__file__).resolve().parents[1]
    source=cast_source
    method=block(source,'bool PlayerbotAI::CastSpell(uint32 spellId, Unit* target, Item* itemTarget, bool waitForSpell, uint32* outSpellDuration)')
    tree=ast.parse((root/'tests/cast_dispatch_lifetime_regression.py').read_text())
    code=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and '#include <cassert>' in n.value)
    guard='#include "'+(root/'playerbot/SpellSelectionGuard.h').as_posix()+'"\n'
    code=code.split('int main(){')[0].replace('__FUNCTIONS__',guard+method)
    code=code.replace('UNIT_STAT_CHASE=1,','SPELL_ATTR_ALLOW_WHILE_SITTING=999,CAST_ANGLE_IN_FRONT=1,UNIT_STAT_CHASE=1,')
    code=code.replace('bool channel=false;','bool HasAttribute(int)const{return false;}bool channel=false;')
    code=code.replace('struct WorldObject {bool world=true;','struct WorldObject {unsigned guid=1;bool world=true;')
    code=code.replace('ObjectGuid GetObjectGuid(){return 1;}','ObjectGuid GetObjectGuid(){return guid;}')
    code=code.replace('struct Player:Unit {bool falling=false,','struct Player:Unit {ObjectGuid selection=42;bool falling=false,')
    code=code.replace('ObjectGuid GetSelectionGuid(){return 1;}void SetSelectionGuid(ObjectGuid){}','ObjectGuid GetSelectionGuid(){return selection;}void SetSelectionGuid(ObjectGuid g){selection=g;}')
    code=code.replace('struct Facade {bool moving=false;','struct Facade {bool moving=false,front=true;bool IsInFront(Player*,WorldObject*,unsigned,unsigned){return front;}void SetFacingTo(Player*,WorldObject*){}')
    code=code.replace('unsigned globalCoolDown=1500;','unsigned globalCoolDown=1500,sightDistance=60;')
    code=code.replace('bool IsJumping(){return jumping;}','void PlayAttackEmote(int){}bool HasRealPlayerMaster(){return master;}bool IsJumping(){return jumping;}')
    return code

for label,recovery_source,expected in versions:
    code=cast_fixture(cast_source)
    recovery=block(recovery_source,"bool SelectNewTargetAction::Execute")
    code=code.replace('#include <cassert>','#include <cassert>\n#include <list>\n#include <algorithm>\nusing std::find;\nstruct Event {};\nstruct Spell;\nenum CurrentSpellTypes { CURRENT_MELEE_SPELL,CURRENT_AUTOREPEAT_SPELL,CURRENT_CHANNELED_SPELL };\nenum {ACT_COMMAND,COMMAND_FOLLOW,CMSG_PET_ACTION};\nstruct WorldPacket {WorldPacket(int){}template<class T>WorldPacket&operator<<(T){return *this;}};\nstruct Session {void HandlePetAction(WorldPacket&){}};\nstruct UnitAI {};')
    code=code.replace('BOT_STATE_NON_COMBAT}', 'BOT_STATE_NON_COMBAT,BOT_STATE_COMBAT}')
    code=code.replace('bool operator!=(ObjectGuid', 'bool operator==(ObjectGuid g)const{return id==g.id;}bool operator!=(ObjectGuid')
    code=code.replace('struct Unit:WorldObject {};','struct Unit:WorldObject {Unit*victim=nullptr;Unit*GetVictim(){return victim;}};\nstruct Creature:Unit {UnitAI*AI(){return nullptr;}};')
    code=code.replace('struct Pet:Unit', 'struct Pet:Creature')
    code=code.replace('Pet* GetPet(){', 'Spell*GetCurrentSpell(CurrentSpellTypes){return nullptr;}void InterruptSpell(CurrentSpellTypes){}void AttackStop(){victim=nullptr;}Session*GetSession(){static Session s;return &s;}Pet* GetPet(){')
    code=code.replace('struct Facade {', 'struct Facade {bool UnitIsDead(Unit*){return false;}')
    code=code.replace('void Set(Base v){data=v;}', 'void Set(Base v){data=v;}void Reset(){}')
    code=code.replace('GetValue(std::string,unsigned=0){static Value<T> v;return &v;}', 'GetValue(std::string name,unsigned=0){static std::map<std::string,Value<T>> values;return &values[name];}')
    code=code.replace('#define AI_VALUE(type,name)', '#define SET_AI_VALUE(type,name,value) context->GetValue<type>(name)->Set(value)\n#define AI_VALUE(type,name)')
    code=code.replace('Item* item=nullptr;void setItemTarget', 'ObjectGuid getUnitTargetGuid(){return 0;}Item* item=nullptr;void setItemTarget')
    code=code.replace('struct Spell {', 'struct Spell {const SpellEntry*m_spellInfo=&entry;bool CanBeInterrupted(){return true;}')
    code=code.replace('struct ChatHelper {', 'bool IsPositiveSpell(const SpellEntry*){return true;}\nstruct ChatHelper {')
    code=code.replace('bool HasStrategy(const char*,BotState)', 'void InterruptSpell(){}void SpellInterrupted(unsigned){}bool DoSpecificAction(const char*,Event&,bool){return false;}bool HasStrategy(const char*,BotState)')
    code=code.replace('Unit* GetUnit(ObjectGuid){return nullptr;}', 'Unit* known=nullptr;Unit* GetUnit(ObjectGuid g){return known&&known->GetObjectGuid().id==g.id?known:nullptr;}')
    code+='\nbool activeRaidControl=false; bool HasNaxxramasControlCast(PlayerbotAI*){return activeRaidControl;}\nstruct SelectNewTargetAction {Player*bot;PlayerbotAI*ai;Context*context;bool Execute(Event&);};\n'+recovery
    code+=r'''
int main(){
 Player bot;PlayerbotAI ai{&bot};Unit patient;patient.guid=2;ai.known=&patient;Event event;
 // Exercise the complete production Unit CastSpell method, including each
 // early return after temporary self/ally/enemy selection is installed.
 for(unsigned original:{0u,42u})for(unsigned targetGuid:{1u,2u,42u})for(int failure=0;failure<6;++failure){
  bot.selection=original;patient.guid=targetGuid;bot.stand=true;bot.falling=false;
  ai.master=true;ai.jumping=false;sServerFacade.moving=false;sServerFacade.front=true;
  Spell::result=SPELL_CAST_OK;entry.Targets=0;entry.channel=false;entry.casttime=1000;
  if(failure==0)bot.stand=false;
  if(failure==1){sServerFacade.front=false;ai.master=false;}
  if(failure==2){sServerFacade.moving=true;bot.falling=true;}
  if(failure==3)Spell::result=SPELL_FAILED_NO_POWER;
  if(failure==4){entry.channel=true;entry.casttime=0;}
  if(failure==5)entry.casttime=0;
  bool accepted=ai.CastSpell(1,&patient,nullptr,true,nullptr);
  assert(accepted==(failure>=4));assert(bot.selection.id==original);
  for(Spell*s:Spell::events)delete s;Spell::events.clear();assert(Spell::live==0);
 }
 bot.stand=true;bot.falling=false;ai.jumping=false;sServerFacade.moving=false;sServerFacade.front=true;
 Spell::result=SPELL_CAST_OK;entry.channel=false;entry.casttime=1000;patient.guid=2;
 SelectNewTargetAction recovery{&bot,&ai,&context};bot.selection=0;ai.master=true;
 entry.Targets=0;int healed=0,cleanupTurns=0;
 // An injured ally remains available; no hostile replacement is available.
 // Engine::DoNextAction ends its decision turn on a successful action.
 // Complete each cast before the next turn; this is not a wall-clock simulation.
 for(int turn=0;turn<12;++turn){
  if(recovery.Execute(event)){++cleanupTurns;continue;}
  if(ai.CastSpell(1,&patient,nullptr,true,nullptr))++healed;
  for(Spell*s:Spell::events)delete s;Spell::events.clear();
 }
 std::cout<<"heals="<<healed<<" cleanup-only turns="<<cleanupTurns<<"\n";
 assert(healed==EXPECTED);assert(Spell::live==0);
 // A real stale combat target or active attack still counts as recovery.
 context.GetValue<ObjectGuid>("current target")->Set(patient.GetObjectGuid());bot.selection=patient.GetObjectGuid();
 assert(recovery.Execute(event)==CLEAN_SUCCESS);assert(!context.GetValue<ObjectGuid>("current target")->Get());
 assert(!bot.selection);assert(!recovery.Execute(event));
 bot.victim=&patient;assert(recovery.Execute(event)==CLEAN_SUCCESS);assert(!bot.GetVictim());
 assert(!recovery.Execute(event));
}
'''.replace('EXPECTED',str(expected)).replace('CLEAN_SUCCESS','false' if label=='before recovery change' else 'true')
    if label=='corrected recovery':
        code=code.replace('entry.Targets=0;int healed=0,cleanupTurns=0;',
            'bot.selection=42;activeRaidControl=true;assert(!recovery.Execute(event));assert(bot.selection.id==42);activeRaidControl=false;bot.selection=0;entry.Targets=0;int healed=0,cleanupTurns=0;')
    for era in ('ZERO','ONE','TWO'):
        with tempfile.TemporaryDirectory(prefix='recovery-interaction-') as folder:
            p=Path(folder);(p/'test.cpp').write_text(code)
            result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
            if result.returncode: print(result.stdout,result.stderr,flush=True)
            result.check_returncode()
            print(label,era,flush=True)
            subprocess.run([str(p/'test.exe')],cwd=p,check=True)
print('PASS: complete shared methods across three expansion defines; healthy class rotations and live gameplay not simulated.')
