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
fixture=fixture.replace('bool IsEmpty()const{return !id;}', 'bool IsEmpty()const{return !id;}bool IsPlayer()const{return id>0&&id<10;}')
fixture=fixture.replace('float GetCollisionHeight(){return 2;}', 'float GetCollisionHeight(){return 2;}float speed=2,body=1;float GetSpeed(unsigned){return speed;}float GetObjectBoundingRadius(){return body;}')
fixture='enum{MOVE_RUN=1};\n'+fixture
fixture=fixture.replace('WorldPosition(Unit*u):', 'WorldPosition(unsigned,float a,float b,float c):x(a),y(b),z(c){}WorldPosition(Unit*u):')
fixture+='\nenum{UNIT_CREATED_BY_SPELL=777};\nnamespace ai{bool NaxxramasEncounterEngaged(Player* bot,Unit* u){return u&&u->world&&u->alive&&u->combat&&!u->charm&&bot->IsInMap(u);}void AppendNativeEncounterActorHazards(PlayerbotAI*,std::list<HazardPosition>&);}\n'
fixture+='\nnamespace ai{void AppendZulGurubActorHazards(PlayerbotAI*,std::list<HazardPosition>&){}}\n'
fixture+=block((root/'playerbot/strategy/values/NativeEncounterActorHazards.cpp').read_text(),'void ai::AppendNativeEncounterActorHazards(')
fixture+=r'''
int main(){
 {Player bot,owner;bot.map=owner.map=533;bot.combat=false;owner.guid=2;owner.entry=16082;PlayerbotAI ai(&bot);
  Creature poison;poison.guid=80;poison.map=533;poison.entry=16027;poison.spawner=owner.guid;poison.combat=false;
  units={&owner,&poison};radii[28433]=5;std::list<HazardPosition>h;
  auto collect=[&](){h.clear();AppendNativeEncounterActorHazards(&ai,h);};
  collect();assert(h.size()==1&&h.front().second==8); // native blast/collision +1sec actor travel
  poison.x=22;collect();assert(h.front().first.x==22);poison.speed=0;collect();assert(h.front().second==6);poison.speed=2;
  poison.alive=false;collect();assert(h.empty());poison.alive=true;
  poison.instance=2;collect();assert(h.empty());poison.instance=1;
  poison.charm=true;collect();assert(h.empty());poison.charm=false;
  poison.z=20;collect();assert(h.empty());poison.z=0;
  poison.spawner=99;collect();assert(h.empty());poison.spawner=owner.guid;
#ifdef MANGOSBOT_TWO
  units={&poison};collect();assert(h.size()==1);units={&owner,&poison}; // summoned blob survives owner departure
#else
  owner.entry=1;collect();assert(h.empty());owner.entry=16082;
#endif
  radii[28433]=0;collect();assert(h.empty());radii[28433]=5;
  bot.teleport=true;collect();assert(h.empty());bot.teleport=false;
  ai.dungeon=false;collect();assert(h.empty());ai.dungeon=true;
  units.clear();collect();assert(h.empty());}
 {Player bot;bot.map=533;PlayerbotAI ai(&bot);Group group;group.Add(&bot);
  Creature boss,fissure;boss.guid=10;boss.entry=15990;boss.map=533;
  fissure.guid=11;fissure.entry=16129;fissure.map=533;fissure.combat=false;
  fissure.spawner=boss.guid;fissure.created=27810;units={&boss,&fissure};radii[27812]=5;
  std::list<HazardPosition> h;auto collect=[&](){h.clear();AppendNativeEncounterActorHazards(&ai,h);};
  collect();assert(h.size()==1&&h.front().second==6); // no aura/cast needed during native warning
  fissure.created=1;collect();assert(h.empty());fissure.created=27810;
  fissure.alive=false;collect();assert(h.empty());fissure.alive=true;
  fissure.world=false;collect();assert(h.empty());fissure.world=true;
  fissure.instance=2;collect();assert(h.empty());fissure.instance=1;
  fissure.charm=true;collect();assert(h.empty());fissure.charm=false;
  boss.combat=false;collect();assert(h.empty());boss.combat=true;
  boss.entry=1;collect();assert(h.empty());boss.entry=15990;
  fissure.spawner=42;collect();assert(h.empty());fissure.spawner=boss.guid;
  radii[27812]=0;collect();assert(h.empty());radii[27812]=5;
  bot.teleport=true;collect();assert(h.empty());bot.teleport=false;
  bot.combat=false;collect();assert(h.empty());bot.combat=true;
  ai.dungeon=false;collect();assert(h.empty());ai.dungeon=true;
  units.clear();collect();assert(h.empty());}
 {Player bot;bot.map=249;PlayerbotAI ai(&bot);Group group;group.Add(&bot);
  std::list<HazardPosition> h;AppendNativeEncounterActorHazards(&ai,h);assert(h.size()==2);
  bot.alive=false;h.clear();AppendNativeEncounterActorHazards(&ai,h);assert(h.empty());bot.alive=true;
  bot.combat=false;AppendNativeEncounterActorHazards(&ai,h);assert(h.empty());bot.combat=true;
  ai.dungeon=false;AppendNativeEncounterActorHazards(&ai,h);assert(h.empty());ai.dungeon=true;
  bot.map=409;AppendNativeEncounterActorHazards(&ai,h);assert(h.empty());}
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
