#pragma once

#include "Action.h"
#include "Queue.h"
#include "Trigger.h"
#include "Multiplier.h"
#include "AiObjectContext.h"
#include "Strategy.h"
#include "playerbot/BotState.h"

#include <atomic>
#include <unordered_map>

namespace ai
{
    class ActionExecutionListener
    {
    public:
        virtual bool Before(Action* action, const Event& event) = 0;
        virtual bool AllowExecution(Action* action, const Event& event) = 0;
        virtual void After(Action* action, bool executed, const Event& event) = 0;
        virtual bool OverrideResult(Action* action, bool executed, const Event& event) = 0;
        virtual ~ActionExecutionListener() {};
    };

    // -----------------------------------------------------------------------------------------------------------------------

    class ActionExecutionListeners : public ActionExecutionListener
    {
    public:
        virtual ~ActionExecutionListeners() override;

    // ActionExecutionListener
    public:
        virtual bool Before(Action* action, const Event& event) override;
        virtual bool AllowExecution(Action* action, const Event& event) override;
        virtual void After(Action* action, bool executed, const Event& event) override;
        virtual bool OverrideResult(Action* action, bool executed, const Event& event) override;

    public:
        void Add(ActionExecutionListener* listener)
        {
            listeners.push_back(listener);
        }
        void Remove(ActionExecutionListener* listener)
        {
            listeners.remove(listener);
        }

    private:
        std::list<ActionExecutionListener*> listeners;
    };

    // -----------------------------------------------------------------------------------------------------------------------

    enum ActionResult
    {
        ACTION_RESULT_UNKNOWN,
        ACTION_RESULT_OK,
        ACTION_RESULT_IMPOSSIBLE,
        ACTION_RESULT_USELESS,
        ACTION_RESULT_FAILED
    };

    class Engine : public PlayerbotAIAware
    {
    public:
        Engine(PlayerbotAI* ai, AiObjectContext *factory, BotState state);

	    void Init();
        void addStrategy(const std::string& name);
		void addStrategies(std::string first, ...);
        bool removeStrategy(const std::string& name, bool init = true);
        bool HasStrategy(const std::string& name);
        Strategy* GetStrategy(const std::string& name) const;
        void removeAllStrategies();
        void toggleStrategy(const std::string& name);
        std::string ListStrategies();
        std::list<std::string_view> GetStrategies();
		bool ContainsStrategy(StrategyType type);
		void ChangeStrategy(const std::string& names);
		void PrintStrategies(Player* requester, const std::string& engineType);
        std::string GetLastAction() { return lastAction; }
        const Action* GetLastExecutedAction() const { return lastExecutedAction; }
        static uint64 GetSuppressedImpossibleActions();
        static uint64 GetSuppressedFailedActions();
        static uint64 GetActionFailureCacheEntries();
        static uint64 GetActionFailureCachePeakEntries();
        static uint64 GetExpiredActionFailureEntries();
        static uint64 GetEvictedActionFailureEntries();

    public:
	    virtual bool DoNextAction(Unit*, int depth, bool minimal, bool isStunned);
	    ActionResult ExecuteAction(const std::string& name, Event& event);
        bool CanExecuteAction(const std::string& name, bool isUseful = true, bool isPossible = true);

    public:
        void AddActionExecutionListener(ActionExecutionListener* listener)
        {
            actionExecutionListeners.Add(listener);
        }
        void removeActionExecutionListener(ActionExecutionListener* listener)
        {
            actionExecutionListeners.Remove(listener);
        }

    public:
	    virtual ~Engine(void);

    protected:
        bool MultiplyAndPush(NextAction** actions, float forceRelevance, bool skipPrerequisites, const Event& event, const char* pushType);
        void Reset();
        void ProcessTriggers(bool minimal);
        void PushDefaultActions();
        void PushAgain(ActionNode* actionNode, float relevance, const Event& event);
        ActionNode* CreateActionNode(const std::string& name);
        virtual Action* InitializeAction(ActionNode* actionNode);
        virtual bool ListenAndExecute(Action* action, Event& event);

    private:
        void LogAction(const char* format, ...);
        void LogValues();
        std::string GetFailureKey(Action* action, const Event& event, ActionResult reason) const;
        bool IsFailureBackedOff(Action* action, const Event& event, ActionResult reason) const;
        void RecordFailure(Action* action, const Event& event, ActionResult reason);
        void ClearFailures(Action* action, const Event& event);
        void PruneActionFailures(uint32 now, bool enforceLimit = false);
        void ClearActionFailures();
        static void UpdateActionFailureCachePeak(uint64 value);

        struct FailureState
        {
            uint32 failures = 0;
            uint32 retryAfter = 0;
            uint32 lastFailure = 0;
        };

    protected:
	    Queue queue;
	    std::list<TriggerNode*> triggers;
        std::list<Multiplier*> multipliers;
        AiObjectContext* aiObjectContext;
        std::map<std::string, Strategy*> strategies;
        float lastRelevance;
        std::string lastAction;
        ActionExecutionListeners actionExecutionListeners;
        BotState state;
        Action* lastExecutedAction;
        std::unordered_map<std::string, FailureState> actionFailures;
        uint32 lastActionFailurePrune = 0;
        static std::atomic<uint64> suppressedImpossibleActions;
        static std::atomic<uint64> suppressedFailedActions;
        static std::atomic<uint64> actionFailureCacheEntries;
        static std::atomic<uint64> actionFailureCachePeakEntries;
        static std::atomic<uint64> expiredActionFailureEntries;
        static std::atomic<uint64> evictedActionFailureEntries;

    public:
		bool testMode;
        bool initMode = true;
    };
}
