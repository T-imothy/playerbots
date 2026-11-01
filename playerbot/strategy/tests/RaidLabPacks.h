#pragma once
#ifdef MANTECH_RAID_LAB
#include "World/RaidLab.h"
#include "Entities/CreatureLinkingMgr.h"
#include "Entities/Creature.h"
#include "Globals/ObjectMgr.h"
#include <algorithm>
#include <map>
#include <set>
#include <vector>

namespace ai {
inline std::map<uint32,std::vector<uint32>> RaidLabLinkedComponents(const std::map<uint32,std::set<uint32>>& adjacency) {
 std::map<uint32,std::vector<uint32>> result;std::set<uint32> seen;
 for(const auto& item:adjacency) {
  if(seen.count(item.first))continue;
  std::vector<uint32> pending{item.first},members;
  while(!pending.empty()) {
   const uint32 guid=pending.back();pending.pop_back();
   if(!seen.insert(guid).second)continue;
   members.push_back(guid);
   const auto edge=adjacency.find(guid);
   if(edge!=adjacency.end())pending.insert(pending.end(),edge->second.begin(),edge->second.end());
  }
  std::sort(members.begin(),members.end());
  if(members.size()>1 && members.size()<=64) {
   const uint32 id=members.front();result.emplace(id,std::move(members));
  }
 }
 return result;
}
inline const std::map<uint32,std::vector<uint32>>& RaidLabLinkedPacks() {
 static const auto packs=[] {
  std::map<uint32,std::set<uint32>> adjacency;
  if(RaidLab::Enabled()) {
   auto collect=[&](const CreatureDataPair& pair) {
    const auto& data=pair.second;
    if(!RaidLab::AllowedMap(data.mapid))return false;
    const auto* link=sCreatureLinkingMgr.GetLinkedTriggerInformation(data.id,pair.first,data.mapid);
    if(!link || !link->masterDBGuid || (link->linkingFlag&3)!=3)return false;
    const auto* master=sObjectMgr.GetCreatureData(link->masterDBGuid);
    if(!master || master->mapid!=data.mapid)return false;
    adjacency[pair.first].insert(link->masterDBGuid);adjacency[link->masterDBGuid].insert(pair.first);
    return false;
   };
   sObjectMgr.DoCreatureData(collect);
  }
  return RaidLabLinkedComponents(adjacency);
 }();
 return packs;
}
}
#endif
