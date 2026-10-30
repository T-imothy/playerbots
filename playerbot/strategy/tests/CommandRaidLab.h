#pragma once
#ifdef MANTECH_RAID_LAB
#include "TestComponent.h"
namespace ai {
class CommandRaidLabStaging : public TestCommand {
public:
 TestResult Execute(const std::string&, Player*, PlayerbotAI*, TestContext&, std::string&) override;
protected:
 std::string GetName() const override { return "raidlab staging"; }
};
class CommandRaidLab : public TestCommand {
public:
 TestResult Execute(const std::string&, Player*, PlayerbotAI*, TestContext&, std::string&) override;
protected:
 std::string GetName() const override { return "raidlab"; }
};
class MonitorRaidLabDeath : public TestMonitor {
protected:
 std::string GetName() const override { return "raidlab boss dead"; }
 bool IsConditionMet(const std::string&, Player*, TestContext&) const override;
};
}
#endif
