"""Actual MC mage selection, cast admission, route reuse and native fear-end transition."""
from pathlib import Path
import ast,subprocess,tempfile,sys
from behavior_regression import block
R=Path(__file__).resolve().parents[1]
support=ast.parse((R/'tests/molten_core_support_regression.py').read_text())
prefix=None
# The shared fixture's code is a raw literal followed by replace(). Read that
# literal through AST rather than importing a script which executes compilers.
for n in support.body:
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets):
  node=n.value
  while isinstance(node,ast.Call):node=node.func.value
  prefix=node.value.split('__METHODS__')[0]
assert prefix
prefix=prefix.replace('struct Player;struct PlayerbotAI;struct Group;', '''struct Player;struct PlayerbotAI;struct Group;
enum SpellSchoolMask{SPELL_SCHOOL_MASK_FIRE=4,SPELL_SCHOOL_MASK_FROST=16,SPELL_SCHOOL_MASK_ARCANE=64};
struct DynamicObject{unsigned owner=0,spell=0,duration=0;bool affects=true;unsigned GetCasterGuid(){return owner;}unsigned GetSpellId(){return spell;}unsigned GetDuration(){return duration;}bool IsAffecting(void*){return affects;}};
struct Map{std::map<unsigned,DynamicObject*>fields;DynamicObject*GetDynamicObject(unsigned g){return fields.count(g)?fields[g]:nullptr;}};
namespace ai{struct Action;}using ai::Action;
''')
prefix=prefix.replace('float x=0,y=0,z=0,o=0,health=100;', 'unsigned immune=0;bool IsImmuneToDamage(SpellSchoolMask m){return immune&m;}float x=0,y=0,z=0,o=0,health=100;')
prefix=prefix.replace('bool los=true;', 'Map nativeMap;Map*GetMap(){return &nativeMap;}bool los=true;')
prefix=prefix.replace('struct Context{', 'struct Context{std::map<std::string,Action*>actions;Action*GetAction(const std::string&n){return actions.count(n)?actions[n]:nullptr;}')
prefix=prefix.replace('bool PlanMoltenCoreMageCleave(PlayerbotAI*,EncounterPosition&){return false;}', 'bool PlanMoltenCoreMageCleave(PlayerbotAI*,EncounterPosition&);')
prefix+='''
namespace ai {
struct Action{PlayerbotAI*ai;Player*bot;std::string name;bool ready=true,possible=true;unsigned count=0,duration=1500;
 Action(PlayerbotAI*a,const std::string&n):ai(a),bot(a->bot),name(n){}virtual ~Action()=default;
 virtual bool isUseful(){return ready;}virtual bool isPossible(){return possible;}virtual bool Execute(Event&){++count;return true;}
 Unit*GetTarget(){return ai->GetUnit(ai->context.current.value);}unsigned GetDuration(){return duration;}void SetDuration(unsigned n){duration=n;}};
struct MoltenCoreMageAoeAction:Action{MoltenCoreMageAoeAction(PlayerbotAI*a):Action(a,"molten core mage aoe"){}Action*Select();bool isUseful();bool Execute(Event&);};
struct CastMeleeAoeSpellAction:Action{CastMeleeAoeSpellAction(PlayerbotAI*a,const char*n,float):Action(a,n){}};
bool MoltenCorePackStackRequired(PlayerbotAI*){return false;}
bool safe=true,allowed=true;bool CasterAreaSafe(PlayerbotAI*,Unit*,float){return safe;}bool CasterAreaSafe(PlayerbotAI*,float,float,float,float){return safe;}
bool CasterSpellAreaSafe(PlayerbotAI*,const std::string&,Unit*){return safe;}
bool MoltenCoreTrashSpellAllowed(PlayerbotAI*,const std::string&){return allowed;}unsigned CasterSpell(PlayerbotAI*,const std::string&){return 2120;}
}
'''
mage=(R/'playerbot/strategy/mage/MageActions.cpp').read_text()
actions=(R/'playerbot/strategy/actions/MoltenCoreDungeonActions.cpp').read_text()
mageMethods='\n'.join(block(s,m) for s,m in ((actions,'bool ai::MoltenCoreRecoverableImp('),(actions,'bool ai::MoltenCoreImpUnderPressure('),(mage,'bool MoltenCoreMageCluster('),(mage,'unsigned MoltenCoreMageHits('),(mage,'bool ai::PlanMoltenCoreMageCleave('),(mage,'Action* MoltenCoreMageAoeAction::Select('),(mage,'bool MoltenCoreMageAoeAction::isUseful('),(mage,'bool MoltenCoreMageAoeAction::Execute(')))
mageMethods+='\n'+block((R/'playerbot/strategy/mage/MageActions.h').read_text(),'class CastFrostNovaAction')+';\n'
mageCase=r'''
int main(){Player tank,mage;Group g;tank.guid=1;tank.tank=true;mage.guid=2;mage.cls=CLASS_MAGE;mage.ranged=true;g.Add(&tank);g.Add(&mage);PlayerbotAI ai(&mage);
 Creature boss,add;boss.guid=10;boss.entry=12118;add.guid=11;add.entry=12119;boss.x=add.x=4;add.y=1;boss.victim=add.victim=&tank;
 units={&tank,&mage,&boss,&add};ai.context.possible.value={10,11};ai.context.current.value=10;
 Action flame(&ai,"flamestrike"),cone(&ai,"cone of cold"),explosion(&ai,"arcane explosion"),blizzard(&ai,"blizzard");
 ai.context.actions={{flame.name,&flame},{cone.name,&cone},{explosion.name,&explosion},{blizzard.name,&blizzard}};
 MoltenCoreMageAoeAction rotation(&ai);Event event;EncounterPosition plan;
#ifdef MANGOSBOT_ZERO
 CastFrostNovaAction nova(&ai);assert(!nova.isUseful()); // emergency generic root cannot dominate a controlled cleave rotation
 assert(rotation.Execute(event)&&flame.count==1&&rotation.GetDuration()==flame.duration);
 DynamicObject field;field.owner=2;field.spell=2120;field.duration=8000;mage.nativeMap.fields[99]=&field;ai.context.possible.value.push_back(99);
 assert(rotation.Execute(event)&&cone.count==1);cone.ready=false;
 assert(rotation.Execute(event)&&explosion.count==1);assert(rotation.Execute(event)&&explosion.count==2&&flame.count==1);
 field.affects=false;assert(rotation.Execute(event)&&flame.count==2);field.affects=true;
 field.owner=5;assert(rotation.Execute(event)&&flame.count==3);field.owner=2;
 mage.o=3.14159f;cone.ready=true;assert(rotation.Execute(event)&&explosion.count==3); // cone does not hit enemies behind
 mage.o=0;boss.immune=add.immune=SPELL_SCHOOL_MASK_FROST;assert(rotation.Execute(event)&&explosion.count==4);boss.immune=add.immune=0;
 boss.entry=add.entry=11669;assert(rotation.Execute(event)&&blizzard.count==1);assert(!PlanMoltenCoreMageCleave(&ai,plan));
 boss.entry=11673;add.entry=12119;assert(rotation.Execute(event)&&blizzard.count==2);assert(!PlanMoltenCoreMageCleave(&ai,plan));
 boss.entry=12118;assert(PlanMoltenCoreMageCleave(&ai,plan)&&plan.destination.x==mage.x);
 mage.x=-30;assert(PlanMoltenCoreMageCleave(&ai,plan)&&plan.destination.x>0);
 assert(rotation.Execute(event)&&blizzard.count==3);mage.x=0;
 safe=false;assert(!rotation.isUseful()&&!rotation.Execute(event));safe=true;
 allowed=false;assert(!rotation.isUseful()&&!PlanMoltenCoreMageCleave(&ai,plan));allowed=true;
 boss.entry=12018;assert(!rotation.isUseful());boss.entry=12118;
 boss.combat=add.combat=false;assert(!rotation.isUseful());boss.combat=add.combat=true;
 mage.instance=2;assert(!rotation.isUseful());mage.instance=1;
 // Native resource/cooldown/learned admission is delegated, never bypassed.
 for(auto& row:ai.context.actions)row.second->possible=false;assert(!rotation.Execute(event));
 for(auto& row:ai.context.actions)row.second->possible=true;
 boss.entry=11669;boss.victim=&mage;assert(MoltenCoreImpUnderPressure(&ai));tank.mobile=false;assert(!MoltenCoreImpUnderPressure(&ai));tank.mobile=true;
 tank.x=50;assert(!MoltenCoreImpUnderPressure(&ai));tank.x=0;
 mage.teleport=true;assert(!MoltenCoreImpUnderPressure(&ai)&&!rotation.isUseful());
#else
 assert(!rotation.isUseful()&&!rotation.Execute(event)&&!PlanMoltenCoreMageCleave(&ai,plan));
#endif
 std::cout<<"PASS MC context-aware mage AoE, native delegation and recoverable imp pressure\n";
}
'''
movementSource=actions
if '--before-cast' in sys.argv:
 movementSource=subprocess.run(['git','-C',str(R),'show','HEAD:playerbot/strategy/actions/MoltenCoreDungeonActions.cpp'],capture_output=True,text=True,check=True).stdout
moveMethods='\n'.join(block(movementSource,m) for m in ('bool MoltenCorePositionAction::isUseful(', 'bool MoltenCorePositionAction::ShouldReactionInterruptCast(', 'bool MoltenCorePositionAction::Execute('))
fear=block((R/'playerbot/PlayerbotAI.cpp').read_text(),'void PlayerbotAI::PrepareForMoltenCoreFearRecovery(')
movePrefix=r'''
#include <cassert>
#include <cmath>
#include <map>
#include <vector>
#include <string>
#include <iostream>
using ObjectGuid=unsigned;constexpr unsigned SPELL_AURA_MOD_FEAR=1;
struct Player;struct Unit{unsigned entry=11982;bool world=true,alive=true;Player*victim=nullptr;float o=0;
 unsigned GetEntry(){return entry;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}Player*GetVictim(){return victim;}float GetOrientation(){return o;}float GetAngle(Player*);};
struct Spline{bool done=true;struct Point{float x=10,y=0,z=0;}end;bool Finalized(){return done;}Point FinalDestination(){return end;}};
struct Player{bool casting=false,fear=false,world=true,alive=true,transfer=false,charm=false;unsigned map=409;float x=-30,y=0;Spline spline;Spline*movespline=&spline;
 bool IsNonMeleeSpellCasted(bool,bool,bool skip){assert(skip);return casting;}bool HasAuraType(unsigned){return fear;}bool IsInWorld(){return world;}bool IsAlive(){return alive;}
 bool IsBeingTeleported(){return transfer;}bool HasCharmer(){return charm;}unsigned GetMapId(){return map;}void*GetGroup(){return this;}unsigned GetObjectGuid(){return 2;}bool IsInMap(Unit*){return true;}
 float GetDistance(float a,float b,float){return std::hypot(x-a,y-b);}float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return 0;}};
float Unit::GetAngle(Player*p){return std::atan2(p->y,p->x);}
struct Guid{unsigned n=0;bool IsEmpty(){return n==0;}operator unsigned()const{return n;}};
namespace encounter{struct Point{float x=-40,y=0,z=0;};struct Circle{};bool OutsideCircles(Point,const std::vector<Circle>&){return true;}}
struct EncounterPosition{bool active=true;unsigned spell=19272,map=409;Guid source,boss;encounter::Point destination;};
template<class T>struct Cached{unsigned resets=0;void Reset(){++resets;}};
struct Context{Cached<EncounterPosition>position;Cached<ObjectGuid>target;template<class T>Cached<T>*GetValue(const char*){if constexpr(std::is_same_v<T,EncounterPosition>)return &position;else return &target;}};
struct ReactionEngine{unsigned wakes=0;void NotifyPartyCombat(){++wakes;}};
struct PlayerbotAI{Player*bot;Unit boss;Context context;Context*aiObjectContext=&context;ReactionEngine reactions;ReactionEngine*reactionEngine=&reactions;
 bool movable=true,real=false,owned=true,isWaiting=true,moltenCoreFeared=false;unsigned stops=0,delay=9000;
 Player*GetBot(){return bot;}bool CanMove(){return movable&&!bot->fear;}bool IsRealPlayer(){return real;}bool HasRealPlayerMaster(){return owned;}
 Unit*GetUnit(Guid){return &boss;}bool IsRanged(Player*){return true;}bool IsHeal(Player*){return false;}void StopMoving(){++stops;}void ResetAIInternalUpdateDelay(){delay=0;}
 void PrepareForMoltenCoreFearRecovery();};
struct Event{};EncounterPosition admitted;
bool GetPlan(PlayerbotAI*,EncounterPosition&plan){plan=admitted;return true;}
bool MoltenCoreThreats(PlayerbotAI*,EncounterPosition&,std::vector<encounter::Circle>&){return false;}
bool ValidateEncounterDestination(PlayerbotAI*,EncounterPosition&,bool=true){return true;}bool PlanRagnarosFormation(PlayerbotAI*,EncounterPosition&p){p=admitted;return true;}
bool PlanMoltenCoreTrash(PlayerbotAI*,EncounterPosition&p){p=admitted;return true;}
struct JumpAction{JumpAction(PlayerbotAI*){}void Qualify(const char*){}bool Execute(Event&){return false;}};
struct MoltenCorePositionAction{PlayerbotAI*ai;Player*bot;unsigned moves=0,duration=0;bool isUseful();bool ShouldReactionInterruptCast()const;bool Execute(Event&);
 void SetDuration(unsigned n){duration=n;}bool IsReaction(){return true;}bool MoveTo(unsigned,float,float,float,bool,bool,bool,bool){++moves;return true;}};
namespace ai {bool engaged=true;Player*GetPartyCombatAnchor(PlayerbotAI*a){return engaged?a->bot:nullptr;}}
'''
moveCase=r'''
int main(){Player bot;PlayerbotAI ai{&bot};MoltenCorePositionAction move{&ai,&bot};Event event;
 // A normal formation cannot machine-gun interrupt Frostbolt, Shadow Bolt,
 // a heal, Slam or a channel. Instant abilities have no casting hold.
 ai.boss.entry=12118;admitted.boss.n=3;
 for(unsigned spell:{116u,686u,2061u,1464u,10u,1510u}){bot.casting=true;assert(!move.ShouldReactionInterruptCast()&&!move.isUseful()&&!move.Execute(event)&&move.moves==0);}
 bot.casting=false;assert(move.isUseful()&&move.Execute(event)&&move.moves==1);
 bot.spline.done=false;bot.spline.end={-40,0,0};assert(move.Execute(event)&&move.moves==1&&move.duration==100);
 bot.x=-40;bot.spline.done=true;assert(!move.isUseful());bot.x=-30;
 admitted.source.n=2;bot.casting=true;assert(move.ShouldReactionInterruptCast()&&move.isUseful());admitted.source.n=0;
 ai.boss.entry=11982;bot.x=20;assert(move.ShouldReactionInterruptCast()&&move.isUseful());bot.x=-30;assert(!move.ShouldReactionInterruptCast());
 // One native fear-end transition wakes movement/action bookkeeping exactly
 // once, preserving casts and native GCD. No enemy means no post-kill wake.
 bot.fear=true;ai.PrepareForMoltenCoreFearRecovery();assert(ai.moltenCoreFeared&&ai.delay==9000);
 bot.fear=false;ai.PrepareForMoltenCoreFearRecovery();assert(!ai.moltenCoreFeared&&ai.delay==0&&!ai.isWaiting&&ai.reactions.wakes==1&&ai.context.position.resets==1&&bot.casting);
 ai.PrepareForMoltenCoreFearRecovery();assert(ai.reactions.wakes==1);
 bot.fear=true;ai.PrepareForMoltenCoreFearRecovery();ai::engaged=false;bot.fear=false;ai.delay=9000;ai.PrepareForMoltenCoreFearRecovery();assert(ai.delay==9000&&ai.reactions.wakes==1);
 std::cout<<"PASS all-class cast/channel protection, active route reuse and one-shot native fear recovery\n";
}
'''
for era in ('ZERO','ONE','TWO'):
 for name,code in (('rotation',prefix+mageMethods+mageCase),('recovery',movePrefix+moveMethods+'\n'+fear+moveCase)):
  with tempfile.TemporaryDirectory(prefix='mc-'+name+'-') as tmp:
   d=Path(tmp);(d/'test.cpp').write_text(code)
   subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=d,check=True)
   subprocess.run([str(d/'test.exe')],cwd=d,check=True)
