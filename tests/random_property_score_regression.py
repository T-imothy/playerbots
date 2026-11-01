"""Exercise the actual item scorer with Classic DBC property/enchant ID collisions."""
from pathlib import Path
import subprocess, tempfile
from behavior_regression import block
r = Path(__file__).resolve().parents[1]
source = (r / 'playerbot/RandomItemMgr.cpp').read_text()
methods = '\n'.join(block(source, name) for name in (
    'uint32 RandomItemMgr::CalculateRandomPropertyWeight(',
    'uint32 RandomItemMgr::GetBestRandomEnchantStatWeight('))
code = r'''
#include <cassert>
#include <cstdlib>
#include <map>
#include <vector>
#include <iostream>
using uint32=unsigned;using uint8=unsigned char;using int32=int;
constexpr unsigned PROP_ENCHANTMENT_SLOT_0=7;
struct ItemRandomPropertiesEntry {unsigned enchant_id[3];};
struct Store {std::map<unsigned,ItemRandomPropertiesEntry> rows;
 const ItemRandomPropertiesEntry* LookupEntry(unsigned id)const{auto i=rows.find(id);return i==rows.end()?nullptr:&i->second;}} sItemRandomPropertiesStore;
struct ItemInfoEntry{};
struct Scale{struct Info{unsigned id=0,classId=0;}info;};
struct RandomItemMgr{
 std::map<unsigned,ItemInfoEntry*>itemInfoCache;
 std::map<unsigned,Scale>m_weightScales;
 std::map<unsigned,unsigned>best,enchants;
 unsigned CalculateBestRandomEnchantId(uint8,uint8,unsigned item){return best[item];}
 unsigned CalculateEnchantWeight(uint8,uint8,unsigned id){return enchants[id];}
 unsigned CalculateRandomPropertyWeight(uint8,uint8,int32);
 unsigned GetBestRandomEnchantStatWeight(unsigned,unsigned);
};
__METHODS__
int main(){
 RandomItemMgr mgr;ItemInfoEntry info;
 mgr.itemInfoCache[10366]=&info;mgr.m_weightScales[3].info={3,1};
 // Actual local DBC: property1206 -> enchants361(+10sta),362(+10str).
 // Enchant1206, a DIFFERENT record, is +44str. Native prot weights sta6/str7.
 sItemRandomPropertiesStore.rows[1206]={{361,362,0}};
 mgr.best[10366]=1206;mgr.enchants={{361,60},{362,70},{1206,308}};
 assert(mgr.CalculateRandomPropertyWeight(1,3,1206)==130);
 assert(mgr.CalculateRandomPropertyWeight(1,3,0)==0);
 assert(mgr.CalculateRandomPropertyWeight(1,3,99999)==0);
#if defined(MANTECH_RAID_LAB) && defined(MANGOSBOT_ZERO)
 assert(mgr.GetBestRandomEnchantStatWeight(10366,3)==130);
 assert(108+mgr.GetBestRandomEnchantStatWeight(10366,3)<405); // Face of Death wins.
#else
 assert(mgr.GetBestRandomEnchantStatWeight(10366,3)==308); // No production/other-era change.
#endif
 assert(mgr.GetBestRandomEnchantStatWeight(0,3)==0);
 assert(mgr.GetBestRandomEnchantStatWeight(10366,0)==0);
 assert(mgr.GetBestRandomEnchantStatWeight(999,3)==0);
 mgr.best[10366]=0;assert(mgr.GetBestRandomEnchantStatWeight(10366,3)==0);
 mgr.best[10366]=1206;mgr.m_weightScales[3].info.classId=0;
 assert(mgr.GetBestRandomEnchantStatWeight(10366,3)==0);
 std::cout<<"PASS property score namespace, missing records, candidate ranking and scope\n";
}
'''.replace('__METHODS__', methods)
for era,lab in [('ZERO',True),('ZERO',False),('ONE',True),('TWO',True)]:
    with tempfile.TemporaryDirectory(prefix='property-score-') as tmp:
        d=Path(tmp);(d/'test.cpp').write_text(code)
        defs=['/DMANGOSBOT_'+era]+(['/DMANTECH_RAID_LAB'] if lab else [])
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',*defs,'test.cpp','/Fe:test.exe'],cwd=d,check=True)
        subprocess.run([str(d/'test.exe')],cwd=d,check=True)
