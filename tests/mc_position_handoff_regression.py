"""Exercise actual arrival handoff, native fire candidates and item cast waits."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
R=Path(__file__).resolve().parents[1]
actions=(R/'playerbot/strategy/actions/MoltenCoreDungeonActions.cpp').read_text()
fire=(R/'playerbot/strategy/values/MoltenCorePositionValue.cpp').read_text()
source=(R/'playerbot/PlayerbotAI.cpp').read_text()
methods='\n'.join((block(actions,'bool MoltenCorePositionAction::isUseful('),block(fire,'EncounterPosition MoltenCorePositionValue::Calculate('),block(source,'uint32 PlayerbotAI::GetSpellCastDuration(')))
code=r'''
#include <cassert>
#include <iostream>
#include <string>
#include "__GEOMETRY__"
using namespace ai;using uint32=unsigned;using int32=int;
struct Spline{bool done=true;encounter::Point end;bool Finalized(){return done;}auto FinalDestination(){return end;}};
struct Player{float x=0,y=0,z=0;Spline spline;Spline*movespline=&spline;
 bool HasAura(unsigned){return false;}bool IsNonMeleeSpellCasted(bool,bool,bool){return false;}
 float GetPositionX(){return x;}float GetPositionY(){return y;}float GetPositionZ(){return z;}float GetDistance(float a,float b,float c){return std::hypot(x-a,y-b);}};
struct SpellEntry{unsigned Id=1;bool channel=false;int duration=0;};
struct Spell{SpellEntry*m_spellInfo;unsigned cast=0;unsigned GetCastTime(){return cast;}};
bool IsChanneledSpell(const SpellEntry*s){return s->channel;}int GetSpellDuration(const SpellEntry*s){return s->duration;}
struct PlayerbotAI{Player*bot;unsigned nativeGcd=1500;uint32 CalculateGlobalCooldown(unsigned){return nativeGcd;}uint32 GetSpellCastDuration(Spell*);};
struct{unsigned reactDelay=100;}sPlayerbotAIConfig;
struct EncounterPosition{bool active=true;encounter::Point destination;};
bool GetPlan(PlayerbotAI*,EncounterPosition&p){p.destination={0,0,0};return true;}
struct MoltenCorePositionAction{PlayerbotAI*ai;Player*bot;bool isUseful();bool ShouldReactionInterruptCast(){return false;}};
struct MoltenCorePositionValue{PlayerbotAI*ai;Player*bot;EncounterPosition Calculate();};
unsigned checked=0,reject=8;bool danger=true;std::vector<encounter::Circle>circles;
bool MoltenCoreThreats(PlayerbotAI*,EncounterPosition&,std::vector<encounter::Circle>&out){out=circles;return danger;}
bool PlanMoltenCoreTrash(PlayerbotAI*,EncounterPosition&p){p.active=false;return false;}
bool ValidateEncounterDestination(PlayerbotAI*,EncounterPosition&){return ++checked>reject;}
__METHODS__
int main(){Player bot;PlayerbotAI ai{&bot};MoltenCorePositionAction position{&ai,&bot};
 assert(!position.isUseful()); // arrival with retained generator/moving flag cannot suppress attacks
 bot.spline.done=false;bot.spline.end={0,0,0};assert(!position.isUseful());
 bot.spline.end={10,0,0};assert(position.isUseful()); // actually travelling beyond station must stop
 bot.x=2;bot.spline.done=true;assert(position.isUseful());bot.x=0;
 circles={{{0,0,0},3}};MoltenCorePositionValue value{&ai,&bot};
 auto p=value.Calculate();assert(p.active&&checked==9&&encounter::OutsideCircles(p.destination,circles));
 checked=0;reject=999;p=value.Calculate();assert(!p.active&&checked==32); // no illegal path fallback
 checked=0;reject=8;circles.push_back({{8,0,0},6});p=value.Calculate();assert(p.active&&encounter::OutsideCircles(p.destination,circles));
 danger=false;p=value.Calculate();assert(!p.active);
 SpellEntry instant,channel;channel.channel=true;channel.duration=5000;Spell potion{&instant},cast{&instant,3000},chan{&channel};
 assert(ai.GetSpellCastDuration(&potion)==1600); // instant item has native GCD + one reaction interval
 assert(ai.GetSpellCastDuration(&cast)==3100&&ai.GetSpellCastDuration(&chan)==5100); // channels/casts remain native
 ai.nativeGcd=0;assert(ai.GetSpellCastDuration(&potion)==100); // no synthetic potion pause
 std::cout<<"PASS actual MC arrival releases offense, ninth legal fire escape, overlapping hazards, bounded no-path failure and native potion/cast/channel waits\n";
}
'''.replace('__METHODS__',methods).replace('__GEOMETRY__',str(R/'playerbot/strategy/EncounterGeometry.h').replace('\\','/'))
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='mc-handoff-') as tmp:
  d=Path(tmp);(d/'test.cpp').write_text(code)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=d,check=True)
  subprocess.run([str(d/'test.exe')],cwd=d,check=True)
