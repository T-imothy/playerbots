from pathlib import Path
root=Path(__file__).resolve().parents[3]
s=(root/'src/shared/Database/SqlOperations.cpp').read_text(encoding='utf-8')
method=s[s.index('bool SqlTransaction::Execute(SqlConnection *conn)'):s.index('SqlPreparedRequest::SqlPreparedRequest')]
code=r'''
#include <cassert>
#include <vector>
#include <cstdio>
#include <cstdint>
using uint32=uint32_t;
struct Logger {template<class...T>void outError(const char*,T...){} }sLog;
struct SqlConnection {bool safe=true,deadlock=false,beginOk=true,rollbackOk=true,commitOk=true;int begins=0,rollbacks=0,commits=0;std::vector<int> pending,stored;
 bool CanReplayTransaction()const{return safe;}void SetStatementDeadlock(bool v){deadlock=v;}bool LastStatementWasDeadlock()const{return deadlock;}
 bool BeginTransaction(){++begins;pending.clear();return beginOk;}bool RollbackTransaction(){++rollbacks;pending.clear();deadlock=false;return rollbackOk;}bool CommitTransaction(){++commits;if(commitOk){stored=pending;pending.clear();}return commitOk;}
};
#define LOCK_DB_CONN(conn)
struct SqlOperation {int number,calls=0,failures=0;bool deadlock=true;bool Execute(SqlConnection*c){++calls;if(failures){--failures;c->deadlock=deadlock;return false;}c->pending.push_back(number);return true;}};
struct SqlTransaction {std::vector<SqlOperation*>m_queue;bool m_retryDeadlock=true;uint32 GetSerialId()const{return 42;}bool Execute(SqlConnection*);};
''' + method + r'''
int main(){
 {SqlConnection c;SqlOperation a{1},b{2},d{3};b.failures=1;SqlTransaction t{{&a,&b,&d}};assert(t.Execute(&c));assert((c.stored==std::vector<int>{1,2,3}));assert(a.calls==2&&b.calls==2&&d.calls==1&&c.begins==2&&c.rollbacks==1&&c.commits==1);}
 {SqlConnection c;SqlOperation a{1},b{2};b.failures=5;SqlTransaction t{{&a,&b}};assert(!t.Execute(&c));assert(a.calls==3&&b.calls==3&&c.rollbacks==3&&c.commits==0&&c.stored.empty());}
 {SqlConnection c;c.safe=false;SqlOperation a{1},b{2};b.failures=1;SqlTransaction t{{&a,&b}};assert(!t.Execute(&c)&&a.calls==1);}
 {SqlConnection c;SqlOperation a{1},b{2};b.failures=1;SqlTransaction t{{&a,&b},false};assert(!t.Execute(&c)&&a.calls==1);}
 {SqlConnection c;SqlOperation a{1},b{2};b.failures=1;b.deadlock=false;SqlTransaction t{{&a,&b}};assert(!t.Execute(&c)&&a.calls==1);}
 {SqlConnection c;c.beginOk=false;SqlOperation a{1};SqlTransaction t{{&a}};assert(!t.Execute(&c)&&a.calls==0&&c.commits==0);}
 {SqlConnection c;c.rollbackOk=false;SqlOperation a{1};a.failures=1;SqlTransaction t{{&a}};assert(!t.Execute(&c)&&a.calls==1);}
 {SqlConnection c;c.commitOk=false;SqlOperation a{1};SqlTransaction t{{&a}};assert(!t.Execute(&c)&&a.calls==1&&c.commits==1&&c.rollbacks==1);}
 {SqlConnection c;c.deadlock=true;SqlOperation a{1};a.failures=1;a.deadlock=false;SqlTransaction t{{&a}};assert(!t.Execute(&c)&&a.calls==1);}
 {SqlConnection c;SqlTransaction t;assert(t.Execute(&c)&&c.begins==0);}
 puts("PASS native whole-transaction deadlock replay, bounded exhaustion, mixed-schema/opt-out refusal, begin/rollback/commit errors, and stale-error clearing");
}
'''
player=(root/'src/game/Objects/Player.cpp').read_text(encoding='utf-8');save=player[player.index('bool Player::SaveToDB('):player.index('void Player::_SaveAuras()')]
assert 'BeginTransaction(GetGUIDLow(), true)' in save
assert 'uberInsert.DirectExecute()' not in save and 'uberInsert.Execute()' in save
mysql=(root/'src/shared/Database/DatabaseMysql.cpp').read_text(encoding='utf-8')
assert 'mysql_stmt_errno(m_stmt) == ER_LOCK_DEADLOCK' in mysql and 'lErrno == ER_LOCK_DEADLOCK' in mysql
from turtle_cpp_fixture import run
run(code)
