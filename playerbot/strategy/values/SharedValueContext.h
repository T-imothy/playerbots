#pragma once

#include "PvpValues.h"
#include "QuestValues.h"
#include "TrainerValues.h"
#include "VendorValues.h"
#include "TravelValues.h"
#include "LootValues.h"
#include "MountValues.h"
#include "playerbot/PlayerbotAI.h"
#include <memory>
#include <mutex>
#include <utility>
#include <type_traits>

namespace ai
{
    // Only process-wide values use this wrapper. Per-bot calculated/manual
    // values remain owned by their AI/map execution context.
    template<class V> class SynchronizedSharedValue : public V
    {
        using Result = decltype(std::declval<V&>().Get());
        std::recursive_mutex valueMutex;
    public:
        explicit SynchronizedSharedValue(PlayerbotAI* ai) : V(ai) {}
        Result Get() override { std::lock_guard<std::recursive_mutex> lock(valueMutex); return V::Get(); }
        Result LazyGet() override { std::lock_guard<std::recursive_mutex> lock(valueMutex); return V::LazyGet(); }
        void Set(Result value) override { std::lock_guard<std::recursive_mutex> lock(valueMutex); V::Set(value); }
        void Reset() override
        {
            std::lock_guard<std::recursive_mutex> lock(valueMutex);
            // Reset value storage, retaining the Qualified lookup identity.
            if constexpr (std::is_base_of_v<CalculatedValue<Result>, V>)
                CalculatedValue<Result>::Reset();
            else
                ManualSetValue<Result>::Reset();
        }
        bool Expired() override { std::lock_guard<std::recursive_mutex> lock(valueMutex); return V::Expired(); }
        bool Expired(uint32 interval) override { std::lock_guard<std::recursive_mutex> lock(valueMutex); return V::Expired(interval); }
        std::string Format() override { std::lock_guard<std::recursive_mutex> lock(valueMutex); return V::Format(); }
        std::string Save() override { std::lock_guard<std::recursive_mutex> lock(valueMutex); return V::Save(); }
        bool Load(std::string value) override { std::lock_guard<std::recursive_mutex> lock(valueMutex); return V::Load(value); }
    };

    class SharedValueContext : public NamedObjectContext<UntypedValue>
    {
    public:
        SharedValueContext() : NamedObjectContext(true)
        {
            creators["bg masters"] = [](PlayerbotAI* ai) { return new SynchronizedSharedValue<BgMastersValue>(ai); };

            creators["item drop map"] = [](PlayerbotAI* ai) { return new SynchronizedSharedValue<ItemDropMapValue>(ai); };
            creators["drop map"] = [](PlayerbotAI* ai) { return new SynchronizedSharedValue<DropMapValue>(ai); };
            creators["item drop list"] = [](PlayerbotAI* ai) { return new SynchronizedSharedValue<ItemDropListValue>(ai); };
            creators["entry loot list"] = [](PlayerbotAI* ai) { return new SynchronizedSharedValue<EntryLootListValue>(ai); };
            creators["loot chance"] = [](PlayerbotAI* ai) { return new SynchronizedSharedValue<LootChanceValue>(ai); };

            creators["vendor map"] = [](PlayerbotAI* ai) { return new SynchronizedSharedValue<VendorMapValue>(ai); };
            creators["item vendor list"] = [](PlayerbotAI* ai) { return new SynchronizedSharedValue<ItemVendorListValue>(ai); };

            creators["entry quest relation"] = [](PlayerbotAI* ai) { return new SynchronizedSharedValue<EntryQuestRelationMapValue>(ai); };

            creators["quest guidp map"] = [](PlayerbotAI* ai) { return new SynchronizedSharedValue<QuestGuidpMapValue>(ai); };
            creators["quest givers"] = [](PlayerbotAI* ai) { return new SynchronizedSharedValue<QuestGiversValue>(ai); };

            creators["trainable spell map"] = [](PlayerbotAI* ai) { return new SynchronizedSharedValue<TrainableSpellMapValue>(ai); };

          

            creators["entry travel purpose"] = [](PlayerbotAI* ai) { return new SynchronizedSharedValue<EntryTravelPurposeMapValue>(ai); };
            creators["entry guidps"] = [](PlayerbotAI* ai) { return new SynchronizedSharedValue<EntryGuidpsValue>(ai); };

            creators["full mount list"] = [](PlayerbotAI* ai) { return new SynchronizedSharedValue<FullMountListValue>(ai); };

            creators["global string"] = [](PlayerbotAI* ai) { return new SynchronizedSharedValue<StringManualSetValue>(ai); };
        }
    };


    class SharedObjectContext
    {
    public:
        SharedObjectContext() : sharedValues(new SharedValueContext()) { valueContexts.Add(sharedValues.get()); }

    public:
        virtual UntypedValue* GetUntypedValue(const std::string& name)
        {
            return valueContexts.GetObject(name, &sharedAi);
        }

        template<class T>
        Value<T>* GetValue(const std::string& name)
        {
            return dynamic_cast<Value<T>*>(GetUntypedValue(name));
        }

        template<class T>
        Value<T>* GetValue(const std::string& name, const std::string& param)
        {
            return GetValue<T>((std::string(name) + "::" + param));
        }

        template<class T>
        Value<T>* GetValue(const std::string& name, int32 param)
        {
            std::ostringstream out; out << param;
            return GetValue<T>(name, out.str());
        }
    protected:
        // Destruction order: list, owned shared values, then their AI context.
        // NamedObjectContextList deliberately does not delete shared contexts.
        PlayerbotAI sharedAi;
        std::unique_ptr<SharedValueContext> sharedValues;
        NamedObjectContextList<UntypedValue> valueContexts;
    };
#define sSharedObjectContext MaNGOS::Singleton<SharedObjectContext>::Instance()
}