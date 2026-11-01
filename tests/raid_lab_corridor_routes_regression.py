"""Validate native corridor map, group and finite destination contracts."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
header=(root/'playerbot/strategy/tests/RaidLabRoutes.h').as_posix()
code=r'''
#include <cassert>
#include <cmath>
#include <set>
#include <string>
#include <iostream>
#define MANTECH_RAID_LAB
'''+f'#include "{header}"\n'+r'''
int main(){
 std::set<unsigned> maps;std::set<std::string> names;
 for(const auto& route:ai::RaidLabCorridorRoutes){
  assert(maps.insert(route.map).second&&names.insert(route.name).second);
  assert(ai::FindRaidLabCorridor(route.name)==&route);
  assert(route.size==((route.map==309||route.map==509)?20:40));
  assert(std::isfinite(route.x)&&std::isfinite(route.y)&&std::isfinite(route.z));
  assert(route.boss>0);
 }
 assert((maps==std::set<unsigned>{249,309,409,469,509,531,533}));
 for(const auto& name:{"", "unknown", "suppression extra", "SUPPRESSION"})assert(!ai::FindRaidLabCorridor(name));
 assert(ai::FindRaidLabCorridor("suppression")->boss==12017);
 std::cout<<"PASS seven native corridor identities, group sizes, finite destinations and unknown-route refusal\n";
}
'''
with tempfile.TemporaryDirectory(prefix='raid-corridors-') as folder:
 path=Path(folder);(path/'test.cpp').write_text(code)
 result=subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=path,capture_output=True,text=True)
 if result.returncode:print(result.stdout,result.stderr)
 result.check_returncode();subprocess.run([str(path/'test.exe')],cwd=path,check=True)
