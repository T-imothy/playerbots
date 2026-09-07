"""Actual cold movement policy delegates to ordinary native packet-based jumping."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
source=(root/'playerbot/strategy/actions/ColdMovementAction.cpp').read_text()
methods='\n'.join(block(source,s) for s in ('uint32 ColdMovementAction::GetColdStacks(', 'bool ColdMovementAction::isUseful(', 'bool ColdMovementAction::ShouldReactionInterruptCast(', 'bool ColdMovementAction::Execute('))
code=r'''
#include <cassert>
#include <iostream>
#include <list>
#include <map>
#include <set>
#include <string>
using uint32=unsigned;using ObjectGuid=unsigned;
enum{CURRENT_GENERIC_SPELL=0,SPELL_STATE_CASTING=1};
struct SpellEntry{unsigned Id=61968;};struct Spell{SpellEntry*m_spellInfo;unsigned state=1;unsigned getState()const{return state;}};
struct SpellAuraHolder{unsigned stacks=2;unsigned GetStackAmount()const{return stacks;}};
struct Unit{unsigned entry=26723,map=576,phase=1;bool world=true,alive=true,combat=true,charmed=false;Spell*cast=nullptr;
 bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsInCombat(){return combat;}bool HasCharmer(){return charmed;}
 unsigned GetEntry(){return entry;}const Spell*GetCurrentSpell(unsigned){return cast;}};
struct Player:Unit{bool teleport=false,group=true,casting=false;unsigned aura=48095;SpellAuraHolder holder;std::set<unsigned>auras;
 bool IsBeingTeleported(){return teleport;}bool GetGroup(){return group;}unsigned GetMapId(){return map;}
 bool IsInMap(Unit*u){return u&&world&&u->world&&map==u->map&&phase==u->phase;}float GetDistance(Unit*){return 10;}
 bool HasAura(unsigned id){return auras.count(id);}const SpellAuraHolder*GetSpellAuraHolder(unsigned id){return id==aura&&holder.stacks?&holder:nullptr;}
};
template<class T>struct Value{T data;T Get(){return data;}};
struct Context{Value<std::list<ObjectGuid>>attackers;template<class T>Value<T>*GetValue(const char*){return &attackers;}};
struct PlayerbotAI{Player*bot;Unit*boss;Context context;bool real=false,canMove=true,jumping=false;unsigned jumps=0;
 bool IsRealPlayer(){return real;}bool CanMove(){return canMove;}bool IsJumping(){return jumping;}
 Context*GetAiObjectContext(){return &context;}Unit*GetUnit(unsigned){return boss;}};
struct Event{};
struct JumpAction{PlayerbotAI*ai;Player*bot;std::string qualifier;
 void Qualify(const char*q){qualifier=q;}bool Execute(Event&){assert(qualifier=="inplace");if(bot->casting)return false;++ai->jumps;return true;}};
struct ColdMovementAction:JumpAction{using JumpAction::JumpAction;unsigned GetColdStacks()const;bool isUseful();bool ShouldReactionInterruptCast()const;bool Execute(Event&);};
__METHODS__
int main(){
 Player bot;Unit boss;PlayerbotAI ai{&bot,&boss};ai.context.attackers.data={1};ColdMovementAction action;action.ai=&ai;action.bot=&bot;Event event;
#ifdef MANGOSBOT_TWO
 assert(action.isUseful()&&!action.ShouldReactionInterruptCast());assert(action.Execute(event)&&ai.jumps==1&&bot.holder.stacks==2);
 bot.casting=true;assert(!action.Execute(event));bot.holder.stacks=4;assert(action.ShouldReactionInterruptCast());bot.casting=false;
 bot.teleport=true;assert(!action.isUseful());bot.teleport=false;
 ai.jumping=true;assert(!action.isUseful());ai.jumping=false;
 ai.canMove=false;assert(!action.isUseful());ai.canMove=true;
 ai.real=true;assert(!action.isUseful());ai.real=false;
 boss.phase=2;assert(!action.isUseful());boss.phase=1;
 boss.alive=false;assert(!action.isUseful());boss.alive=true;
 bot.holder.stacks=1;assert(!action.isUseful());bot.holder.stacks=2;
 bot.map=boss.map=603;boss.entry=32845;bot.aura=62039;assert(action.isUseful());
 bot.auras.insert(62821);assert(!action.isUseful());bot.auras.clear();
 SpellEntry info;Spell cast{&info};boss.cast=&cast;assert(!action.isUseful());cast.state=2;assert(action.isUseful());
#else
 assert(!action.isUseful()&&!action.Execute(event)&&ai.jumps==0);
#endif
 std::cout<<"PASS: cold stacks, casting escalation, native jump delegation, Flash Freeze/warmth and lifecycle gates\n";
}
'''.replace('__METHODS__',methods)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='mantech-cold-') as directory:
  tmp=Path(directory);(tmp/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
  subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
core=root.parent/'mangos-wotlk-behavior'
native=(core/'src/game/AI/ScriptDevAI/scripts/northrend/ulduar/ulduar/boss_hodir.cpp').read_text()
assert 'target->IsMoving() || target->HasAura(SPELL_TOASTY_FIRE)' in native
assert 'RemoveAuraHolderFromStack(SPELL_BITING_COLD_AURA)' in native
unit=(core/'src/game/Entities/Unit.h').read_text()
assert 'bool IsMoving() const { return m_movementInfo.HasMovementFlag(movementFlagsMask); }' in unit
flags=(core/'src/game/Entities/Object.h').read_text().split('MovementFlags const movementFlagsMask =',1)[1].split(';',1)[0]
assert 'MOVEFLAG_FALLING' in flags
movement=(root/'playerbot/strategy/actions/MovementActions.cpp').read_text()
jump=block(movement,'bool JumpAction::DoJump(')
assert 'MOVEFLAG_FALLING' in jump and 'ai->QueuePacket(jump)' in jump
assert '"inplace"' in block(movement,'bool JumpAction::Execute(')
