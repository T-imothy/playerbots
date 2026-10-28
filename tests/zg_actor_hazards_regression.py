"""Native ZG death spirits/infernals: real helper, aura/source ownership and lifecycle."""
from pathlib import Path
import ast
import subprocess
import tempfile
from behavior_regression import block

root=Path(__file__).resolve().parents[1]
tree=ast.parse((root/'tests/vashj_core_relay_regression.py').read_text())
code=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in node.targets))
code=code.split('int main(){',1)[0].replace('__METHODS__','')
code=code.replace('float panicRadius=8;float NativeEncounterSpellRadius(unsigned id){assert(id==38258);return panicRadius;}',
    'std::map<unsigned,float> radii;float NativeEncounterSpellRadius(unsigned id){return radii[id];}')
code=code.replace('Unit*GetVictim(){return victim;}',
    'bool friendly=false;unsigned created=0;unsigned GetUInt32Value(unsigned){return created;}unsigned GetTypeId(){return player?4:3;}Unit*GetMaster(){return nullptr;}bool CanReachWithMeleeAttack(Unit*u){return GetDistance(u)<=5;}Unit*GetVictim(){return victim;}')
code=code.replace('struct Creature:Unit{', 'struct Creature:Unit{Group*lootGroup=nullptr;Group*GetGroupLootRecipient(){return lootGroup;}')
code+='\nenum{UNIT_CREATED_BY_SPELL=777,TYPEID_UNIT=3};\nstruct Facade{bool IsFriendlyTo(Unit*,Unit*u){return u->friendly;}}sServerFacade;\n'
code+=(root/'playerbot/strategy/ZulGurubEncounter.h').read_text().replace('#pragma once','')
code+='\nnamespace ai{void AppendZulGurubActorHazards(PlayerbotAI*,std::list<HazardPosition>&);}\n'
code+=block((root/'playerbot/strategy/values/ZulGurubActorHazards.cpp').read_text(),'void ai::AppendZulGurubActorHazards(')
code+=r'''
int main(){
 struct Row{unsigned actor,owner,summon,aura,payload;};
#ifdef MANGOSBOT_ZERO
 const unsigned infernal=89;
#else
 const unsigned infernal=22203;
#endif
 for(Row row: {Row{15009,11831,24052,24051,24050},Row{infernal,14883,24670,19483,20153}}){
  Player bot,member;bot.guid=1;member.guid=2;bot.map=member.map=309;
  Group group,foreign;group.Add(&bot);group.Add(&member);PlayerbotAI ai(&bot);
  Creature owner,actor;owner.guid=10;owner.entry=row.owner;owner.map=309;owner.victim=&member;
  actor.guid=11;actor.entry=row.actor;actor.map=309;actor.spawner=owner.guid;actor.created=row.summon;actor.auras={row.aura};actor.combat=false;
  units={&bot,&member,&owner,&actor};radii[row.payload]=5;std::list<HazardPosition> hazards;
  auto collect=[&](){hazards.clear();AppendZulGurubActorHazards(&ai,hazards);};
  collect();assert(hazards.size()==1&&hazards.front().second==6);
  actor.x=20;collect();assert(hazards.front().first.x==20);actor.x=0;
  actor.created=1;collect();assert(hazards.empty());actor.created=row.summon;
  actor.auras.clear();collect();assert(hazards.empty());actor.auras={row.aura};
  if(row.actor==infernal){actor.entry=infernal==89?22203:89;collect();assert(hazards.empty());actor.entry=infernal;}
  owner.entry=1;collect();assert(hazards.empty());owner.entry=row.owner;
  actor.spawner=88;collect();assert(hazards.empty());actor.spawner=owner.guid;
  actor.friendly=true;collect();assert(hazards.empty());actor.friendly=false;
  owner.friendly=true;collect();assert(hazards.empty());owner.friendly=false;
  actor.charm=true;collect();assert(hazards.empty());actor.charm=false;
  actor.instance=2;collect();assert(hazards.empty());actor.instance=1;
  actor.world=false;collect();assert(hazards.empty());actor.world=true;
  actor.alive=false;collect();assert(hazards.empty());actor.alive=true;
  actor.z=9;collect();assert(hazards.empty());actor.z=0;
  owner.combat=false;collect();assert(hazards.empty());owner.combat=true;
  member.group=&foreign;collect();assert(hazards.empty());member.group=&group;
  // Source death is the spawn trigger, not the end of the Spirit's native life.
  owner.alive=false;owner.combat=false;bot.combat=false;owner.lootGroup=&group;
  collect();assert(hazards.size()==1);
  owner.lootGroup=&foreign;collect();assert(hazards.empty());owner.lootGroup=&group;
  if(row.actor==15009){actor.victim=&member;member.x=3;collect();assert(hazards.size()==2&&hazards.back().first.x==3);
   member.x=20;collect();assert(hazards.size()==1);member.x=0;actor.victim=nullptr;}
  radii[row.payload]=0;collect();assert(hazards.empty());radii[row.payload]=5;
  bot.teleport=true;collect();assert(hazards.empty());bot.teleport=false;
  ai.dungeon=false;collect();assert(hazards.empty());ai.dungeon=true;
  ai.real=true;collect();assert(hazards.empty());ai.real=false;
  units.clear();collect();assert(hazards.empty());
 }
 std::cout<<"PASS: ZG native actor hazards, death-source group credit, victim-centred burst and aura/summon/hostility/lifecycle gates\n";
}
'''
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='mantech-zg-actor-') as folder:
        temp=Path(folder);(temp/'test.cpp').write_text(code)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=temp,check=True)
        subprocess.run([str(temp/'test.exe')],cwd=temp,check=True)
collector=(root/'playerbot/strategy/values/NativeEncounterActorHazards.cpp').read_text()
assert 'AppendZulGurubActorHazards(ai, hazards);' in collector
trigger=(root/'playerbot/strategy/triggers/HostileGroundDamageTrigger.cpp').read_text()
assert 'bot->GetMapId() == 309' in block(trigger,'bool HostileGroundDamageTrigger::IsActive(')
for era in ('classic','tbc','wotlk'):
    assert 'Group* GetGroupLootRecipient() const' in (root.parent/era/'src/game/Entities/Creature.h').read_text()
