from pathlib import Path
import re,subprocess,tempfile,shutil
from turtle_cpp_fixture import run
r=Path(__file__).resolve().parents[3]
s=(r/'src/playerbot_overrides/LootSecurityCheckAction.cpp').read_text(encoding='utf-8')
s=re.sub(r'^#include.*$','',s,flags=re.M)
run(r'''#include <cassert>
#include <cstdio>
namespace ai {struct Event{};struct SecurityCheckAction {int loot=0,threshold=0;bool passive=false,stay=false;bool isUseful();bool Execute(Event&);bool RequiresWorldOwner()const;};}
'''+s+r'''
int main(){ai::SecurityCheckAction a;ai::Event event;for(int loot=0;loot<=4;++loot)for(int threshold=0;threshold<=6;++threshold){a.loot=loot;a.threshold=threshold;assert(!a.isUseful()&&!a.Execute(event)&&!a.RequiresWorldOwner());assert(!a.passive&&!a.stay);}a.passive=a.stay=true;assert(!a.Execute(event)&&a.passive&&a.stay);puts("PASS actual Classic realm override: every loot method/threshold; no passive/stay mutations or unnecessary owner handoff");}
''')
cmake=shutil.which('cmake') or r'C:/Program Files/CMake/bin/cmake.exe'
original=(r/'modules/ManTechPlayerbots/playerbot/strategy/actions/SecurityCheckAction.cpp').read_text(encoding='utf-8')
with tempfile.TemporaryDirectory(prefix='turtle-loot-policy-') as directory:
 root=Path(directory);source=root/'modules/ManTechPlayerbots/playerbot/strategy/actions/SecurityCheckAction.cpp';source.parent.mkdir(parents=True)
 policy=(r/'cmake/playerbot_loot_policy.cmake').as_posix()
 for case in ('valid','changed','missing','duplicate'):
  source.write_text(original+('\n// changed upstream\n' if case=='changed' else ''),encoding='utf-8')
  files=[] if case=='missing' else [source.as_posix()]*(2 if case=='duplicate' else 1)
  script=root/'test.cmake'
  script.write_text('cmake_minimum_required(VERSION 3.20)\nset(CMAKE_SOURCE_DIR "'+root.as_posix()+'")\nset(MANTECH_LOOT_POLICY_TARGET fixture)\nfunction(get_target_property out target property)\nset(${out} "'+';'.join(files)+'" PARENT_SCOPE)\nendfunction()\nfunction(set_property)\nset(replaced "${ARGN}" PARENT_SCOPE)\nendfunction()\ninclude("'+policy+'")\nif(NOT replaced MATCHES "LootSecurityCheckAction.cpp")\nmessage(FATAL_ERROR "override not selected")\nendif()\n',encoding='utf-8')
  result=subprocess.run([cmake,'-P',str(script)],capture_output=True,text=True)
  assert (result.returncode==0)==(case=='valid'),case+result.stdout+result.stderr
print('PASS actual CMake policy: valid source replacement; changed upstream, missing and duplicate source rejection')
