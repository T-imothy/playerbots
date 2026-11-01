#pragma once
#ifdef MANTECH_RAID_LAB
#include "TestComponent.h"
namespace ai {
class CommandRaidLabPack : public TestCommand {
public:
 TestResult Execute(const std::string&, Player*, PlayerbotAI*, TestContext&, std::string&) override;
protected:
 std::string GetName() const override { return "raidlab pack"; }
};
class CommandRaidLabCorridor : public TestCommand {
public:
 TestResult Execute(const std::string&, Player*, PlayerbotAI*, TestContext&, std::string&) override;
protected:
 std::string GetName() const override { return "raidlab corridor"; }
};
class CommandRaidLabLeader : public TestCommand {
public:
 TestResult Execute(const std::string&, Player*, PlayerbotAI*, TestContext&, std::string&) override;
protected:
 std::string GetName() const override { return "raidlab leader"; }
};
class CommandRaidLabSeed : public TestCommand {
public:
 TestResult Execute(const std::string&, Player*, PlayerbotAI*, TestContext&, std::string&) override;
protected:
 std::string GetName() const override { return "raidlab seed"; }
};
class CommandRaidLabProgression : public TestCommand {
public:
 TestResult Execute(const std::string&, Player*, PlayerbotAI*, TestContext&, std::string&) override;
protected:
 std::string GetName() const override { return "raidlab progression"; }
};
class CommandRaidLabProvision : public TestCommand {
public:
 TestResult Execute(const std::string&, Player*, PlayerbotAI*, TestContext&, std::string&) override;
protected:
 std::string GetName() const override { return "raidlab provision"; }
};
class CommandRaidLabEvent : public TestCommand {
public:
 TestResult Execute(const std::string&, Player*, PlayerbotAI*, TestContext&, std::string&) override;
protected:
 std::string GetName() const override { return "raidlab event"; }
};
class CommandRaidLabLanding : public TestCommand {
public:
 TestResult Execute(const std::string&, Player*, PlayerbotAI*, TestContext&, std::string&) override;
protected:
 std::string GetName() const override { return "raidlab landing"; }
};
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
class MonitorRaidLabCompletion : public TestMonitor {
protected:
 std::string GetName() const override { return "raidlab encounter complete"; }
 bool IsConditionMet(const std::string&, Player*, TestContext&) const override;
};
class MonitorRaidLabNoEngagement : public TestMonitor {
protected:
 std::string GetName() const override { return "raidlab no engagement"; }
 bool IsConditionMet(const std::string&, Player*, TestContext&) const override;
};
}
#endif
