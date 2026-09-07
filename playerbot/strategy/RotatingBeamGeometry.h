#pragma once
#include "EncounterGeometry.h"

namespace ai { namespace encounter {
    struct RotatingBeam
    {
        Point origin;
        float orientation = 0, halfAngle = 0, sweep = 0, radius = 0, angularSpeed = 0;
        bool shelteredInWater = false;
    };

    inline bool OutsideRotatingBeam(Point point, const RotatingBeam& beam)
    {
        constexpr float pi = 3.14159265358979323846f;
        const float distance = Distance2d(point, beam.origin);
        if (!std::isfinite(distance) || !std::isfinite(beam.radius) || beam.radius <= 0 ||
            !std::isfinite(point.z) || !std::isfinite(beam.origin.z) ||
            !std::isfinite(beam.halfAngle) || beam.halfAngle <= 0 || beam.halfAngle >= pi ||
            !std::isfinite(beam.orientation) || !std::isfinite(beam.sweep)) return false;
        if (distance > beam.radius + 2) return true;
        if (distance < 1) return false;
        const float offset = std::remainder(std::atan2(point.y - beam.origin.y, point.x - beam.origin.x) -
            beam.orientation - beam.sweep / 2, 2 * pi);
        return std::fabs(offset) > beam.halfAngle + std::fabs(beam.sweep) / 2 + 0.08f;
    }

    inline bool RotatingBeamRouteSafe(Point start, const std::vector<Point>& route, const RotatingBeam& beam, float runSpeed)
    {
        if (route.empty() || !std::isfinite(runSpeed) || runSpeed <= 0 ||
            !std::isfinite(beam.angularSpeed)) return false;
        bool outside = OutsideRotatingBeam(start, beam);
        unsigned samples = 0;
        float travelled = 0;
        for (const Point& end : route)
        {
            const float length = Distance2d(start, end);
            if (!std::isfinite(length) || length > 256) return false;
            // Fine samples also cover narrow cones near the boss. Bound the
            // complete route, including detours, before entering this loop.
            const unsigned steps = unsigned(std::ceil(length / 0.2f));
            if (steps > 1024 || samples + steps > 1024) return false;
            samples += steps;
            for (unsigned step = 1; step <= steps; ++step)
            {
                const float t = float(step) / steps;
                const Point point{start.x + (end.x - start.x) * t, start.y + (end.y - start.y) * t, start.z + (end.z - start.z) * t};
                RotatingBeam predicted = beam;
                predicted.sweep += beam.angularSpeed * (travelled + length * t) / runSpeed;
                const bool safe = OutsideRotatingBeam(point, predicted);
                // A threatened bot may leave the beam. A route that is already
                // clear must not cross back through its current/upcoming sweep.
                if (outside && !safe) return false;
                outside = outside || safe;
            }
            travelled += length;
            start = end;
        }
        RotatingBeam predicted = beam;
        predicted.sweep += beam.angularSpeed * travelled / runSpeed;
        return outside && OutsideRotatingBeam(start, predicted);
    }
}}
