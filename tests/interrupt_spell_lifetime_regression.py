"""The common cancellation helper must capture metadata before native callbacks."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
repo=Path(__file__).resolve().parents[1]
method=block((repo/'playerbot/PlayerbotAI.cpp').read_text(),'void PlayerbotAI::InterruptSpell(bool')
code=r'''
#include <cassert>
#include <iostream>
#include <stdexcept>
#include <vector>
using uint32=unsigned;
enum CurrentSpellTypes{CURRENT_MELEE_SPELL,CURRENT_GENERIC_SPELL,CURRENT_AUTOREPEAT_SPELL,CURRENT_CHANNELED_SPELL};
struct SpellEntry{unsigned Id;};
struct CheckedEntry{SpellEntry*entry;bool retired=false;SpellEntry*operator->(){if(retired)throw std::logic_error("spell metadata read after cancellation boundary");return entry;}};
struct Spell{CheckedEntry m_spellInfo;bool interruptible=true;bool CanBeInterrupted(){return interruptible;}};
struct Player{Spell*casts[4]{};std::vector<unsigned>stopped;
 Spell*GetCurrentSpell(CurrentSpellTypes slot){return casts[slot];}
 void InterruptSpell(CurrentSpellTypes slot){stopped.push_back(slot);casts[slot]->m_spellInfo.retired=true;casts[slot]=nullptr;}};
struct PlayerbotAI{Player*bot;std::vector<unsigned>notified;void InterruptSpell(bool);void SpellInterrupted(unsigned id){notified.push_back(id);}};
__METHOD__
int main(){try{
 for(bool all:{false,true}){Player bot;PlayerbotAI ai{&bot};SpellEntry e[4]{{10},{11},{12},{13}};
  Spell casts[4]{{{&e[0]}},{{&e[1]}},{{&e[2]}},{{&e[3]}}};for(unsigned i=0;i<4;++i)bot.casts[i]=&casts[i];
  ai.InterruptSpell(all);assert((ai.notified==(all?std::vector<unsigned>{10,11,12}:std::vector<unsigned>{11})));
  assert(bot.casts[CURRENT_CHANNELED_SPELL]==&casts[3]); // Preserve the existing helper's channel policy.
  if(!all)assert(bot.casts[CURRENT_MELEE_SPELL]&&bot.casts[CURRENT_AUTOREPEAT_SPELL]);
  auto count=ai.notified.size();ai.InterruptSpell(all);assert(ai.notified.size()==count);
 }
 Player bot;PlayerbotAI ai{&bot};SpellEntry e{99};Spell spell{{&e},false};bot.casts[CURRENT_GENERIC_SPELL]=&spell;
 ai.InterruptSpell(true);assert(ai.notified.empty()&&bot.stopped.empty());
 std::cout<<"PASS common cancellation metadata lifetime and preserved slot policy\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
'''.replace('__METHOD__',method)
with tempfile.TemporaryDirectory(prefix='mantech-interrupt-lifetime-') as directory:
 tmp=Path(directory);(tmp/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
 subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
