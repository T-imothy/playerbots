"""Actual movement-state copying and controlled vehicle selection."""
from pathlib import Path
import subprocess
import tempfile
from behavior_regression import block

repo=Path(__file__).resolve().parents[1]
state=block((repo/'playerbot/strategy/values/LastMovementValue.h').read_text(),'class LastMovement')+';'
mover=block((repo/'playerbot/strategy/actions/MovementActions.cpp').read_text(),'Unit* MovementAction::GetMover(')
code=r'''
#include <cassert>
#include <cstdint>
#include <ctime>
#include <iostream>
#include <vector>
using uint32=uint32_t;using int32=int32_t;using ObjectGuid=unsigned;
struct WorldPosition{};struct Event{};struct TravelPath{void clear(){}};
enum {SEAT_FLAG_CAN_CONTROL=1};
struct VehicleSeatEntry{bool control=false;bool HasFlag(int)const{return control;}};
struct VehicleInfo{VehicleSeatEntry* seat=nullptr;VehicleSeatEntry* GetSeatEntry(int){return seat;}};
struct Unit{VehicleInfo* vehicle=nullptr;VehicleInfo* GetVehicleInfo(){return vehicle;}};
struct TransportInfo{bool onVehicle=false;Unit* transport=nullptr;bool IsOnVehicle(){return onVehicle;}
 Unit* GetTransport(){return transport;}int GetTransportSeat(){return 0;}};
struct Player:Unit {TransportInfo* info=nullptr;TransportInfo* GetTransportInfo(){return info;}};
struct MovementAction{Unit* GetMover(Player*);};
__STATE__
__MOVER__
int main(){
 LastMovement original;original.lastFlee=1234;original.failedPathRetryUntil=9000;original.failedPathMap=4;
 LastMovement copied(original);assert(copied.lastFlee==1234&&copied.failedPathRetryUntil==9000&&copied.failedPathMap==4);
 copied.clear();assert(copied.lastFlee==0&&copied.failedPathRetryUntil==0&&copied.failedPathMap==UINT32_MAX);
 Player bot;MovementAction action;assert(action.GetMover(&bot)==&bot);
 TransportInfo info;bot.info=&info;assert(action.GetMover(&bot)==&bot);
#ifdef MANGOSBOT_TWO
 info.onVehicle=true;assert(action.GetMover(&bot)==nullptr);
 Unit vehicle;info.transport=&vehicle;assert(action.GetMover(&bot)==nullptr);
 VehicleInfo vehicleInfo;vehicle.vehicle=&vehicleInfo;assert(action.GetMover(&bot)==nullptr);
 VehicleSeatEntry seat;vehicleInfo.seat=&seat;assert(action.GetMover(&bot)==nullptr);
 seat.control=true;assert(action.GetMover(&bot)==&vehicle);
#endif
 std::cout<<"PASS: flee/retry state copy/reset and passenger/controller movement admission\n";
}
'''.replace('__STATE__',state).replace('__MOVER__',mover)
with tempfile.TemporaryDirectory(prefix='mantech-movement-state-') as folder:
    tmp=Path(folder);(tmp/'test.cpp').write_text(code)
    for era in ('ZERO','ONE','TWO'):
        subprocess.run(['cl','/nologo','/std:c++17','/EHsc','/DMANGOSBOT_'+era,'test.cpp','/Fe:test.exe'],cwd=tmp,check=True)
        subprocess.run([str(tmp/'test.exe')],cwd=tmp,check=True)
