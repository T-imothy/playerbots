"""Execute native pet spell saves with a delayed write queue and stale reload.

No live player/database rows are modified. The fixture models the native primary
key and FIFO writes, and checks each core's actual transaction/load contracts.
"""
from pathlib import Path
import subprocess
import sys
import tempfile
from behavior_regression import block
root=Path(__file__).resolve().parents[1]
refs={'classic':'b41cd828fa62dd4fc752a95dff1ed9c0912ac07e','tbc':'a12a42f2d54ce2117310331724a6eaa619d9a885','wotlk':'2e0ca8a70eb94a08e021f3b85a1ff0cde6f596b6'}
code=r'''
#include <cassert>
#include <map>
#include <vector>
#include <string>
#include <stdexcept>
#include <iostream>
using uint32=unsigned;
enum PetSpellState {PETSPELL_REMOVED,PETSPELL_CHANGED,PETSPELL_NEW,PETSPELL_UNCHANGED};
enum PetSpellType {PETSPELL_NORMAL,PETSPELL_FAMILY};
struct PetSpell {PetSpellState state;PetSpellType type=PETSPELL_NORMAL;unsigned active=193;};
using PetSpellMap=std::map<unsigned,PetSpell>;
struct SqlStatementID{};
struct Request {std::string sql;std::vector<unsigned> args;};
std::vector<Request> queue;
struct SqlStatement {std::string sql;template<class...Args>void PExecute(Args...args){queue.push_back({sql,{unsigned(args)...}});}};
struct Database {SqlStatement CreateStatement(SqlStatementID&,const char*sql){return {sql};}}CharacterDatabase;
struct CharmInfo {unsigned number=7;unsigned GetPetNumber(){return number;}};
struct Pet {CharmInfo charm;CharmInfo* m_charmInfo=&charm;PetSpellMap m_spells;void _SaveSpells();};
__METHOD__
using Key=std::pair<unsigned,unsigned>;
std::map<Key,unsigned> database;
void flush(){
 auto transaction=database; // Abort the transaction on a duplicate, as native SQL does.
 for(auto&r:queue){
  assert(r.args.size()>=2);Key key{r.args[0],r.args[1]};
  if(r.sql=="DELETE FROM pet_spell WHERE guid = ? and spell = ?")transaction.erase(key);
  else {assert(r.sql=="INSERT INTO pet_spell (guid,spell,active) VALUES (?, ?, ?)"&&r.args.size()==3);
   if(!transaction.emplace(key,r.args[2]).second)throw std::runtime_error("duplicate pet_spell primary key");}
 }
 database=transaction;queue.clear();
}
int main(){
 database[{7,3110}]=193;database[{8,6307}]=193;
 Pet original;original.m_spells[6307]={PETSPELL_NEW};original._SaveSpells();
 assert(original.m_spells[6307].state==PETSPELL_UNCHANGED&&database.count({7,6307})==0);
 // Reload on the synchronous connection before the queued unsummon save commits.
 Pet reloaded;assert(database.count({7,6307})==0);
 reloaded.m_spells[6307]={PETSPELL_NEW,PETSPELL_NORMAL,129}; // Relearned; autocast changed by latest owner state.
 flush();assert(database.at({7,6307})==193);
 reloaded._SaveSpells();flush();assert(database.at({7,6307})==129);
 assert(database.at({7,3110})==193&&database.at({8,6307})==193); // Exact pet/spell key only.
 reloaded._SaveSpells();assert(queue.empty()); // Unchanged spells remain write-free.
 reloaded.m_spells[6307].state=PETSPELL_CHANGED;reloaded.m_spells[6307].active=193;
 reloaded._SaveSpells();flush();assert(database.at({7,6307})==193);
 reloaded.m_spells[6307].state=PETSPELL_REMOVED;reloaded._SaveSpells();flush();
 assert(reloaded.m_spells.empty()&&database.count({7,6307})==0);
 reloaded.m_spells[6307]={PETSPELL_NEW};reloaded.m_spells[99]={PETSPELL_NEW,PETSPELL_FAMILY};
 reloaded._SaveSpells();flush();assert(database.at({7,6307})==193&&database.count({7,99})==0);
 assert(reloaded.m_spells[99].state==PETSPELL_NEW);
 std::cout<<"PASS: actual native pet saves, stale reload before queued commit, active state, removal and family exclusion\n";
}
'''
for era,realm in (('ZERO','classic'),('ONE','tbc'),('TWO','wotlk')):
    core=root.parent/f'mangos-{realm}-behavior';relative='src/game/Entities/Pet.cpp'
    source=(core/relative).read_text()
    if '--before' in sys.argv:
        source=subprocess.check_output(['git','-c','safe.directory='+core.as_posix(),'-C',str(core),'show',refs[realm]+':'+relative],text=True)
    method=block(source,'void Pet::_SaveSpells()')
    save=block(source,'void Pet::SavePetToDB(')
    assert save.index('CharacterDatabase.BeginTransaction()')<save.index('_SaveSpells()')<save.index('CharacterDatabase.CommitTransaction()')
    db=(core/'src/shared/Database/Database.cpp').read_text()
    assert 'm_threadBody->Delay(m_currentTransaction.release())' in block(db,'bool Database::CommitTransaction()')
    with tempfile.TemporaryDirectory(prefix='mantech-pet-save-') as folder:
        tmp=Path(folder);(tmp/'test.cpp').write_text(code.replace('__METHOD__',method))
        subprocess.run(['cl','/nologo','/EHsc','/std:c++17',f'/DMANGOSBOT_{era}','test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
