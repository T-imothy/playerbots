"""Balanced native subgroup fixture; preserve identities and five-player caps."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
code=r'''
#include <cassert>
#include <iostream>
#include <numeric>
#include <random>
#include "playerbot/strategy/tests/RaidLabSubgroupPlan.h"
using namespace ai;
int main(){
 for(unsigned size:{20u,40u}) {
  const unsigned groups=size/5,healers=size==40?16:5,tanks=size==40?4:2;
  std::vector<RaidLabMemberRole> members;
  for(unsigned i=0;i<size;++i)members.push_back({i+1,i>=healers&&i<healers+tanks,i<healers,i<3});
  std::mt19937 random(12259);
  for(unsigned trial=0;trial<100;++trial) {
   std::shuffle(members.begin(),members.end(),random);
   const auto plan=RaidLabSubgroups(members);assert(plan.size()==size);
   std::array<unsigned,8> counts{},h{},t{},p{};
   for(unsigned i=0;i<size;++i){assert(plan[i]<groups);++counts[plan[i]];h[plan[i]]+=members[i].healer;t[plan[i]]+=members[i].tank;p[plan[i]]+=members[i].provider;}
   for(unsigned g=0;g<groups;++g){assert(counts[g]==5);assert(h[g]>=healers/groups&&h[g]<=(healers+groups-1)/groups);assert(t[g]<=1&&p[g]<=1);}
   // Determinism is by GUID/role, independent of linked-list insertion order.
   auto sorted=members;std::sort(sorted.begin(),sorted.end(),[](auto a,auto b){return a.guid<b.guid;});
   auto sortedPlan=RaidLabSubgroups(sorted);
   for(unsigned i=0;i<size;++i)assert(plan[i]==sortedPlan[members[i].guid-1]);
   // Exercise the exact ordered pair-swap algorithm with shuffled full groups.
   std::vector<uint8_t> current(size);for(unsigned i=0;i<size;++i)current[i]=i/5;
   std::shuffle(current.begin(),current.end(),random);
   for(unsigned i=0;i<size;++i) {
    if(current[i]==plan[i])continue;
    unsigned j=i+1;while(j<size&&(current[j]!=plan[i]||plan[j]==plan[i]))++j;
    assert(j<size);std::swap(current[i],current[j]);
   }
   assert(current==plan);
  }
  auto invalid=members;invalid[1].guid=invalid[0].guid;assert(RaidLabSubgroups(invalid).empty());
  invalid=members;invalid[0].guid=0;assert(RaidLabSubgroups(invalid).empty());
  invalid=members;invalid[0].tank=invalid[0].healer=true;assert(RaidLabSubgroups(invalid).empty());
  members.pop_back();assert(RaidLabSubgroups(members).empty());
 }
 assert(RaidLabSubgroups({}).empty());
 std::cout<<"PASS local20/40-player subgroup capacity, healer/provider/tank balance, identity and deterministic swaps\n";
}
'''
with tempfile.TemporaryDirectory(prefix='raidlab-subgroups-') as folder:
 p=Path(folder);(p/'test.cpp').write_text(code)
 subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/I{root}','test.cpp','/Fe:test.exe'],cwd=p,check=True)
 subprocess.run([str(p/'test.exe')],cwd=p,check=True)
