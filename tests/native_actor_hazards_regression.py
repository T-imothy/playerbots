"""Exercise actual actor hazard collection, ownership and difficulty variants."""
from pathlib import Path
import ast,subprocess,tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
# Reuse the controlled world fixture without importing its executable runner.
tree=ast.parse((root/'tests/vashj_core_relay_regression.py').read_text())
fixture=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in node.targets))
fixture=fixture.split('int main(){',1)[0]
fixture=fixture.replace('float panicRadius=8;float NativeEncounterSpellRadius(unsigned id){assert(id==38258);return panicRadius;}',
    'float panicRadius=8;std::map<unsigned,float>radii;float NativeEncounterSpellRadius(unsigned id){return radii[id];}')
fixture=fixture.replace('Unit*GetVictim(){return victim;}', 'unsigned created=0;unsigned GetUInt32Value(unsigned){return created;}Unit*GetVictim(){return victim;}')
fixture=fixture.replace('void Add(Player*p){', 'bool IsMember(ObjectGuid g){for(auto&r:refs)if(r.p->guid==g)return true;return false;}void Add(Player*p){')
fixture=fixture.replace('__METHODS__','')
fixture+='\nenum{UNIT_CREATED_BY_SPELL=777};\nnamespace ai{void AppendNativeEncounterActorHazards(PlayerbotAI*,std::list<HazardPosition>&);}\n'
fixture+=block((root/'playerbot/strategy/values/NativeEncounterActorHazards.cpp').read_text(),'void ai::AppendNativeEncounterActorHazards(')
fixture+=r'''
int main(){
 struct Row{unsigned map,boss,actor,aura,payload,ownerSpell;float padding;};
 const Row rows[]={
  {534,17968,18095,31945,31943,0,2},{546,17770,17990,31690,34168,31692,1},
  {568,23578,23920,42629,42630,0,1},{568,23863,24136,43120,43121,0,4},
  {568,23863,24187,43218,43217,0,1},{564,22898,23085,42055,42052,0,1},
  {564,22898,23095,40980,40253,0,2},
  {603,33186,34188,64709,64709,0,1},{603,33186,34188,64734,64734,0,1},
  {603,32930,33632,63347,63346,63343,4},{603,32930,33632,63977,63976,63343,4},
  {603,32930,33802,63347,63346,63701,4},{603,32930,33802,63977,63976,63701,4},
  {631,36612,36672,69145,69146,0,2},{631,37955,38163,71267,71268,71266,1},
  {632,36502,36536,68854,68863,0,1}};
 for(auto row:rows){
  Player bot,member;bot.guid=1;member.guid=2;bot.map=member.map=row.map;
  PlayerbotAI ai(&bot);Group group;group.Add(&bot);group.Add(&member);
  Creature boss,actor,duplicate;boss.guid=10;boss.entry=row.boss;boss.map=row.map;
  actor.guid=20;actor.entry=row.actor;actor.map=row.map;actor.x=10;actor.combat=false;
  actor.spawner=row.ownerSpell?member.guid:boss.guid;actor.created=row.ownerSpell;actor.auras.insert(row.aura);
  units={&bot,&member,&boss,&actor};radii.clear();radii[row.payload]=7;
  std::list<HazardPosition>hazards;
  auto collect=[&](){hazards.clear();AppendNativeEncounterActorHazards(&ai,hazards);};
  collect();
#ifdef MANGOSBOT_ZERO
  assert(hazards.empty());continue;
#elif defined(MANGOSBOT_ONE)
  if(row.map==603||row.map==631||row.map==632){assert(hazards.empty());continue;}
#endif
  assert(hazards.size()==1&&hazards.front().second==7+row.padding); // Passive actors still count.
  actor.x=25;collect();assert(hazards.front().first.x==25);
  actor.alive=false;collect();assert(hazards.empty());actor.alive=true;
  actor.world=false;collect();assert(hazards.empty());actor.world=true;
  actor.auras.clear();collect();assert(hazards.empty());actor.auras.insert(row.aura);
  actor.instance=2;collect();assert(hazards.empty());actor.instance=1;
  actor.z=10;collect();assert(hazards.empty());actor.z=0;
  actor.spawner=99;collect();assert(hazards.empty());actor.spawner=row.ownerSpell?member.guid:boss.guid;
  boss.combat=false;collect();assert(hazards.empty());boss.combat=true;
  boss.alive=false;collect();assert(hazards.empty());boss.alive=true;
  boss.entry++;collect();assert(hazards.empty());boss.entry--;
  ai.dungeon=false;collect();assert(hazards.empty());ai.dungeon=true;
  bot.combat=false;collect();assert(hazards.empty());bot.combat=true;
  radii[row.payload]=0;collect();assert(hazards.empty());radii[row.payload]=7;
  if(row.ownerSpell){
   actor.created++;collect();assert(hazards.empty());actor.created--;
   member.alive=false;collect();assert(hazards.size()==1);member.alive=true; // Native hazard can outlive its player.
   duplicate=boss;duplicate.guid=11;units.push_back(&duplicate);collect();assert(hazards.empty());units.pop_back();
  }
  duplicate=actor;duplicate.guid=21;duplicate.x=-15;units.push_back(&duplicate);collect();assert(hazards.size()==2);
 }
 std::cout<<"PASS: native actor hazards, passive summons, difficulty payloads, ownership and lifecycle\n";
}
'''
for era in ('ZERO','ONE','TWO'):
    with tempfile.TemporaryDirectory(prefix='native-actor-hazards-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(fixture)
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
hazards=(root/'playerbot/strategy/values/HazardsValue.cpp').read_text()
assert 'AppendNativeEncounterActorHazards(ai, hazards);' in block(hazards,'std::list<HazardPosition> HazardsValue::Calculate(')
