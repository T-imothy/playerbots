"""Select a native configured bear preset only for local level-60 tank fixtures."""
from pathlib import Path
import subprocess,tempfile
from behavior_regression import block
source=(Path(__file__).resolve().parents[1]/'playerbot/PlayerbotMgr.cpp').read_text()
code=r'''
#include <cassert>
#include <vector>
#include <map>
#include <algorithm>
#include <iostream>
using uint8=unsigned char;using uint32=unsigned;
enum BotRoles {BOT_ROLE_NONE=0,BOT_ROLE_TANK=1,BOT_ROLE_HEALER=2,BOT_ROLE_DPS=4};
constexpr unsigned CLASS_DRUID=11,MAX_TALENT_RANK=5;
struct TalentEntry {unsigned RankID[5]={0,0,0,0,0};};
struct Talent {int rank=0;TalentEntry* talentInfo=nullptr;};
struct Spec {int tree=0;std::vector<Talent> talents;int highestTree(){return tree;}};
struct Path {int id=0;std::vector<Spec> talentSpec;};
struct ClassSpecs {std::vector<Path> talentPath;};
struct Config {std::map<unsigned,ClassSpecs> classSpecs;}sPlayerbotAIConfig;
__SELECT__
int main(){
 assert(RaidLabDruidTankPreset(11,60,BOT_ROLE_TANK)==-1);
 TalentEntry bear;bear.RankID[0]=16958;bear.RankID[1]=16961;
 TalentEntry cat;cat.RankID[0]=12345;
 sPlayerbotAIConfig.classSpecs[11].talentPath={{9,{}},{4,{{2,{{2,&bear}}}}},{3,{{1,{{1,&cat}}}}},{7,{{1,{{2,&bear}}}}}};
 assert(RaidLabDruidTankPreset(11,60,BOT_ROLE_TANK)==7);
 assert(RaidLabDruidDamagePreset(11,60,BOT_ROLE_DPS,7)==3);
 sPlayerbotAIConfig.classSpecs[11].talentPath.push_back({5,{{0,{{1,&cat}}}}});
 assert(RaidLabDruidDamagePreset(11,60,BOT_ROLE_DPS,0)==3);
 assert(RaidLabDruidDamagePreset(11,60,BOT_ROLE_DPS,1)==5);
 assert(RaidLabDruidDamagePreset(11,60,BOT_ROLE_DPS,100)==3);
 for(BotRoles role:{BOT_ROLE_NONE,BOT_ROLE_HEALER,BOT_ROLE_TANK})assert(RaidLabDruidDamagePreset(11,60,role,0)==-1);
 assert(RaidLabDruidDamagePreset(1,60,BOT_ROLE_DPS,0)==-1);
 assert(RaidLabDruidDamagePreset(11,59,BOT_ROLE_DPS,0)==-1);
 sPlayerbotAIConfig.classSpecs[11].talentPath.pop_back();
 for(unsigned cls:{1u,2u,3u,5u,8u,9u})assert(RaidLabDruidTankPreset(cls,60,BOT_ROLE_TANK)==-1);
 for(unsigned level:{1u,59u,61u,70u,80u})assert(RaidLabDruidTankPreset(11,level,BOT_ROLE_TANK)==-1);
 for(BotRoles role:{BOT_ROLE_NONE,BOT_ROLE_HEALER,BOT_ROLE_DPS})assert(RaidLabDruidTankPreset(11,60,role)==-1);
 auto& talents=sPlayerbotAIConfig.classSpecs[11].talentPath.back().talentSpec.back().talents;
 talents[0].rank=0;assert(RaidLabDruidTankPreset(11,60,BOT_ROLE_TANK)==-1);
 talents[0].rank=6;assert(RaidLabDruidTankPreset(11,60,BOT_ROLE_TANK)==-1);
 talents[0].rank=1;talents[0].talentInfo=nullptr;assert(RaidLabDruidTankPreset(11,60,BOT_ROLE_TANK)==-1);
 std::cout<<"PASS local native druid tank preset: learned bear talents, role/class/level and malformed paths\n";
}
'''.replace('__SELECT__',block(source,'int RaidLabDruidTankPreset(')+'\n'+block(source,'int RaidLabDruidDamagePreset('))
assert '#if defined(MANTECH_RAID_LAB) && defined(MANGOSBOT_ZERO)' in source
assert 'if (temporary && role==BOT_ROLE_TANK && cls==CLASS_DRUID && level==60)' in source
with tempfile.TemporaryDirectory(prefix='raidlab-bear-preset-') as directory:
    p=Path(directory);(p/'test.cpp').write_text(code)
    subprocess.run(['cl','/nologo','/EHsc','/std:c++17','test.cpp','/Fe:test.exe'],cwd=p,check=True)
    subprocess.run([str(p/'test.exe')],cwd=p,check=True)
