"""Actual Naxx group-engagement guard and unfiltered safety discovery wiring."""
from pathlib import Path
import ast, subprocess, tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
tree=ast.parse((root/'tests/vashj_core_relay_regression.py').read_text())
fixture=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
fixture=fixture.split('int main(){',1)[0].replace('__METHODS__','')
fixture=fixture.replace('Unit*GetVictim(){return victim;}',
    'Unit*master=nullptr;Unit*GetMaster(){return master;}struct Threat{std::set<Unit*>targets;float getThreat(Unit*u){return targets.count(u)?1:0;}}threat;Threat&getThreatManager(){return threat;}Unit*GetVictim(){return victim;}')
fixture+='\nnamespace ai{bool NaxxramasEncounterEngaged(Player*,Unit*);}\n'
fixture+=block((root/'playerbot/strategy/values/NaxxramasPositionValue.cpp').read_text(),'bool ai::NaxxramasEncounterEngaged(')
fixture+=r'''
int main(){
 Player bot,member,foreign;bot.map=member.map=foreign.map=533;Group raid,other;raid.Add(&bot);raid.Add(&member);other.Add(&foreign);
 Creature boss,pet;boss.map=pet.map=533;
 auto engaged=[&](){return ai::NaxxramasEncounterEngaged(&bot,&boss);};
 assert(!engaged());boss.victim=&foreign;assert(!engaged()); // nearby unrelated combat is not our encounter
 boss.victim=&member;assert(engaged());member.teleport=true;assert(!engaged());member.teleport=false;
 member.instance=2;assert(!engaged());member.instance=1;member.alive=false;assert(!engaged());member.alive=true;
 boss.victim=&pet;pet.master=&member;assert(engaged());pet.master=&foreign;assert(!engaged());boss.victim=nullptr;
 member.victim=&boss;assert(engaged());member.victim=nullptr;boss.attackers.insert(&member);assert(engaged());boss.attackers.clear();
 boss.threat.targets.insert(&member);assert(engaged());boss.combat=false;assert(!engaged());boss.combat=true;
 boss.alive=false;assert(!engaged());boss.alive=true;boss.world=false;assert(!engaged());boss.world=true;
 boss.instance=2;assert(!engaged());boss.instance=1;boss.charm=true;assert(!engaged());boss.charm=false;
 bot.teleport=true;assert(!engaged());bot.teleport=false;bot.map=409;assert(!engaged());bot.map=533;
 bot.group=nullptr;assert(!engaged());bot.group=&raid;boss.threat.targets.clear();assert(!engaged());
 std::cout<<"PASS Naxx actual group/instance/native threat perception, pet ownership and reset\n";
}
'''
for era in ('ZERO','ONE','TWO'):
 with tempfile.TemporaryDirectory(prefix='naxx-perception-') as folder:
  p=Path(folder);(p/'test.cpp').write_text(fixture)
  subprocess.run(['cl','/nologo','/std:c++17','/EHsc',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=p,check=True)
  subprocess.run([str(p/'test.exe')],cwd=p,check=True)
for file,signature in (
 ('values/HeiganPositionValue.cpp','EncounterPosition HeiganPositionValue::Calculate('),
 ('values/BossCastPositionValue.cpp','EncounterPosition BossCastPositionValue::Calculate('),
 ('values/BossCoverPositionValue.cpp','EncounterPosition BossCoverPositionValue::Calculate('),
 ('actions/EncounterDispelPolicy.cpp','bool ai::ShouldAvoidEncounterDispel(')):
 body=block((root/'playerbot/strategy'/file).read_text(),signature)
 assert '"possible targets", "100:1"' in body and 'NaxxramasEncounterEngaged' in body,file
trigger=block((root/'playerbot/strategy/triggers/HostileGroundDamageTrigger.cpp').read_text(),'bool HostileGroundDamageTrigger::IsActive(')
assert 'AppendNativeEncounterActorHazards(ai, warnings)' in trigger and 'inside = true' in trigger
