"""Compile the actual three AI telemetry entry blocks with observable collaborators."""
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / 'playerbot/PlayerbotAI.cpp').read_text()
blocks = re.findall(
    r'    std::unique_ptr<PerformanceMonitorOperation> pmo;\n'
    r'    if \(sPlayerbotAIConfig.perfMonEnabled\)\n    \{\n'
    r'.*?PlayerbotAI::(UpdateAI|UpdateAIReaction|UpdateAIInternal) .*?\n    \}',
    source, re.S)
assert blocks == ['UpdateAI', 'UpdateAIReaction', 'UpdateAIInternal']
functions = []
for name in blocks:
    start = source.index('PlayerbotAI::' + name + '(')
    declaration = source.index('    std::unique_ptr<PerformanceMonitorOperation> pmo;', start)
    end = source.index('\n    }', declaration) + len('\n    }')
    functions.append('void ' + name + '(Bot* bot) {\n' + source[declaration:end] + '\n}')

fixture = r'''
#include <cassert>
#include <memory>
#include <string>
#include <iostream>
int lookups=0, starts=0, finishes=0;
std::string label;
struct Bot { unsigned map=0, instance=0;
 unsigned GetMapId(){++lookups;return map;}
 unsigned GetInstanceId(){++lookups;return instance;}
};
struct WorldPosition { Bot* bot; explicit WorldPosition(Bot* b):bot(b){++lookups;}
 bool isInstance(){++lookups;return bot->instance!=0;}
};
struct Config { bool perfMonEnabled=false; } sPlayerbotAIConfig;
struct PerformanceMonitorOperation { ~PerformanceMonitorOperation(){++finishes;} };
constexpr int PERF_MON_TOTAL=0;
struct Monitor { bool available=true;
 std::unique_ptr<PerformanceMonitorOperation> start(int,std::string name,void*,unsigned,unsigned) {
  ++starts; label=name;
  if(!available)return {};
  return std::make_unique<PerformanceMonitorOperation>();
 }
} sPerformanceMonitor;
__FUNCTIONS__
int main(){
 Bot bot;
 void(*calls[])(Bot*)={UpdateAI,UpdateAIReaction,UpdateAIInternal};
 const char* names[]={"UpdateAI","UpdateAIReaction","UpdateAIInternal"};
 for(int i=0;i<3;++i){
  lookups=starts=finishes=0;sPlayerbotAIConfig.perfMonEnabled=false;
  for(int tick=0;tick<10000;++tick)calls[i](&bot);
  assert(lookups==0 && starts==0 && finishes==0);
  sPlayerbotAIConfig.perfMonEnabled=true;
  bot.map=0;bot.instance=0;calls[i](&bot);
  assert(starts==1 && finishes==1 && label==std::string("PlayerbotAI::")+names[i]+" 0");
  bot.map=70;bot.instance=33;calls[i](&bot);
  assert(starts==2 && finishes==2 && label==std::string("PlayerbotAI::")+names[i]+" I");
  sPerformanceMonitor.available=false;calls[i](&bot);
  assert(starts==3 && finishes==2);
  sPerformanceMonitor.available=true;
 }
 std::cout<<"PASS: disabled hooks do no lookup/monitor work; enabled labels and operation lifetime preserved\n";
}
'''.replace('__FUNCTIONS__', '\n'.join(functions))
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='disabled-telemetry-') as tmp:
        p=Path(tmp);(p/'test.cpp').write_text(fixture)
        subprocess.run(['cl','/nologo','/std:c++20','/EHsc','/UNDEBUG','/DMANGOSBOT_'+era,
                        str(p/'test.cpp'),'/Fe:'+str(p/'test.exe'),'/Fo:'+str(p/'test.obj')],check=True)
        subprocess.run([str(p/'test.exe')],check=True)
