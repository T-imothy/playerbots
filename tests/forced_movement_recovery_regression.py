"""Compile the real once-per-landing wakeup without faking movement or spell control."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
R=Path(__file__).resolve().parents[1];source=(R/'playerbot/PlayerbotAI.cpp').read_text()
method=block(source,'void PlayerbotAI::PrepareForForcedMovementRecovery(')
code=r'''
#include <cassert>
#include <iostream>
#include <string>
struct Player{bool world=true,alive=true,transfer=false,charm=false,control=true;unsigned map=409;bool IsInWorld(){return world;}bool IsAlive(){return alive;}bool IsBeingTeleported(){return transfer;}bool HasCharmer(){return charm;}bool CanReactInCombat(){return control;}unsigned GetMapId(){return map;}};
struct EncounterPosition{};template<class T>struct Value{unsigned resets=0;void Reset(){++resets;}};
struct Context{Value<EncounterPosition>position;template<class T>Value<T>*GetValue(const char*){return &position;}};
struct Reaction{unsigned wakes=0;void NotifyPartyCombat(){++wakes;}};
struct PlayerbotAI{Player*bot;Context*aiObjectContext;Reaction*reactionEngine;bool forcedMovementRecoveryPending=true,real=false,jumping=false,anchor=true,isWaiting=true;unsigned resets=0;
 bool IsRealPlayer(){return real;}bool IsJumping(){return jumping;}void ResetAIInternalUpdateDelay(){++resets;}void PrepareForForcedMovementRecovery();};
namespace ai{Player*GetPartyCombatAnchor(PlayerbotAI*a){return a->anchor?a->bot:nullptr;}}
__METHOD__
int main(){Player bot;Context context;Reaction reactions;PlayerbotAI a{&bot,&context,&reactions};
 for(unsigned map:{409u,1u,532u,489u,631u}){bot.map=map;a.forcedMovementRecoveryPending=true;a.isWaiting=true;unsigned before=a.resets,positions=context.position.resets,wakes=reactions.wakes;
  a.jumping=true;a.PrepareForForcedMovementRecovery();assert(a.forcedMovementRecoveryPending&&a.resets==before);a.jumping=false;bot.control=false;a.PrepareForForcedMovementRecovery();assert(a.forcedMovementRecoveryPending&&a.resets==before);
  bot.control=true;a.PrepareForForcedMovementRecovery();assert(!a.forcedMovementRecoveryPending&&!a.isWaiting&&a.resets==before+1&&reactions.wakes==wakes+1);assert(context.position.resets==positions+(map==409));
  for(unsigned i=0;i<10;++i)a.PrepareForForcedMovementRecovery();assert(a.resets==before+1);}
 for(unsigned mode=0;mode<5;++mode){a.forcedMovementRecoveryPending=true;unsigned before=a.resets;switch(mode){case 0:a.real=true;break;case 1:bot.alive=false;break;case 2:bot.world=false;break;case 3:bot.transfer=true;break;case 4:bot.charm=true;break;}a.PrepareForForcedMovementRecovery();assert(!a.forcedMovementRecoveryPending&&a.resets==before);a.real=bot.transfer=bot.charm=false;bot.alive=bot.world=true;}
 a.anchor=false;a.forcedMovementRecoveryPending=true;unsigned wakes=reactions.wakes;a.PrepareForForcedMovementRecovery();assert(reactions.wakes==wakes&&!a.isWaiting);
 std::cout<<"PASS: native landing/control return, deferred stun/fear, one wake, all-map scope and no cast cancellation\n";
}
'''.replace('__METHOD__',method)
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='forced-recovery-') as d:
  p=Path(d);(p/'test.cpp').write_text(code)
  r=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=p,capture_output=True,text=True)
  if r.returncode:raise RuntimeError(r.stdout+r.stderr)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
landing=source[source.index('// normal landing'):source.index('// falling after hitting something')]
assert 'forcedMovementRecoveryPending = true;' in landing and 'jumpTime = 0;' in landing
assert landing.index('jumpTime = 0;') < landing.index('PrepareForForcedMovementRecovery();')
assert 'PrepareForForcedMovementRecovery();' in block(source,'void PlayerbotAI::UpdateAI(')
assert 'Interrupt' not in method and 'CastSpell' not in method and 'RemoveAura' not in method
