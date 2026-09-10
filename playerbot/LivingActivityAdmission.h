#ifndef LIVING_ACTIVITY_ADMISSION_H
#define LIVING_ACTIVITY_ADMISSION_H
#include <cstddef>
#include <cstdint>

namespace LivingActivity {
    // A tested gate for the existing observer loop, not another scheduler.
    // It never discards an accepted write or an unacknowledged receipt.
    enum class ObservationWork { Wait, Probe, Decode, Flush, Load, Import, CachePressure, HistoryPressure };
    struct ObservationQueue {
        bool enabled = false, ioPending = false, due = false, schemaReady = false, loaded = false;
        size_t cached = 0, pending = 0, incoming = 0, cacheLimit = 20000;
        uint64_t retained = 0, historyLimit = 200000;
    };
    inline ObservationWork NextObservationWork(const ObservationQueue& q) {
        if (!q.enabled || q.ioPending || !q.due) return ObservationWork::Wait;
        if (!q.schemaReady) return ObservationWork::Probe;
        // Flush already decoded rows before requesting more cache space. A full
        // pending batch must not deadlock behind its own admission capacity.
        if (q.retained >= q.historyLimit || q.pending > q.historyLimit - q.retained)
            return ObservationWork::HistoryPressure;
        if (q.pending) return ObservationWork::Flush;
        if (q.cached >= q.cacheLimit) return ObservationWork::CachePressure;
        if (q.incoming) return ObservationWork::Decode;
        return q.loaded ? ObservationWork::Import : ObservationWork::Load;
    }
    inline unsigned NextImportFamily(unsigned family) { return (family + 1) % 4; }
}
#endif
