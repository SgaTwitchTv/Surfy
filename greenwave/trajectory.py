"""M4 bounded beam search over physical profiles and predicted green windows.

No simulator access. A sampled optimum is not a global optimum. Each branch
retains crossing speed (which can differ from its cruise setpoint).
"""
from dataclasses import dataclass, replace
import json
import math
from pathlib import Path

from greenwave.solver import Recommendation, arrival_time


@dataclass(frozen=True)
class TrajectorySettings:
    max_signals: int = 5
    beam_width: int = 12
    horizon_seconds: float = 240
    stop_weight: float = 10000
    braking_weight: float = 30
    variation_weight: float = 4
    time_weight: float = 1
    risk_weight: float = 20
    unknown_risk: float = .5
    stop_speed_mps: float = .05
    switch_cost_tolerance: float = 2

    def __post_init__(self):
        for name, value in vars(self).items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f'Invalid trajectory setting: {name}')
        if not isinstance(self.max_signals, int) or not 1 <= self.max_signals <= 8:
            raise ValueError('max_signals must be 1..8')
        if not isinstance(self.beam_width, int) or not 1 <= self.beam_width <= 64:
            raise ValueError('beam_width must be 1..64')
        if not 0 < self.horizon_seconds <= 600 or self.unknown_risk > 1:
            raise ValueError('Invalid horizon or unknown risk')
        if not 0 < self.stop_speed_mps <= .5:
            raise ValueError('Invalid stop threshold')


def load_trajectory_config(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data['schema_version'] != 1:
        raise ValueError('Unsupported trajectory configuration')
    return TrajectorySettings(**data['trajectory'])


class TrajectorySolver:
    def __init__(self, single, settings=TrajectorySettings()):
        self.single, self.settings = single, settings

    def cost(self, legs):
        previous_acceleration = variation = 0
        for leg in legs:
            for acceleration in leg['accelerations']:
                variation += abs(acceleration-previous_acceleration)
                previous_acceleration = acceleration
        values = dict(stops=sum(l['stops'] for l in legs),
                      braking=sum(l['braking'] for l in legs),
                      variation=variation,
                      time=sum(l['duration'] for l in legs),
                      risk=sum(l['risk'] for l in legs))
        weights = dict(stops=self.settings.stop_weight, braking=self.settings.braking_weight,
                       variation=self.settings.variation_weight, time=self.settings.time_weight,
                       risk=self.settings.risk_weight)
        weighted = {k: values[k]*weights[k] for k in values}
        return dict(raw=values, weighted=weighted, total=sum(weighted.values()))

    def _moving(self, prediction, distance, speed, limit, now, committed=None, reaction=0):
        raw = self.single.solve(prediction, distance=distance, speed=speed, speed_limit=limit, now=now,
                                committed_command=committed, committed_reaction_seconds=reaction)
        seen = set()
        for c in raw.candidates:
            for target in sorted({c['range_min_kmh'], c['target_kmh'], c['range_max_kmh']}):
                key = (target, c['mode'], c['window_start'], c['reaction_seconds'])
                if key in seen: continue
                seen.add(key)
                duration = arrival_time(distance, speed, target/3.6, c['acceleration_mps2'],
                                        c['deceleration_mps2'], c['reaction_seconds'])
                at = now+duration
                if not c['interior_start']-1e-7 <= at <= c['interior_end']+1e-7: continue
                ramp_time = max(0, duration-c['reaction_seconds'])
                crossing = min(target/3.6, speed+c['acceleration_mps2']*ramp_time) if target/3.6 >= speed else max(target/3.6, speed-c['deceleration_mps2']*ramp_time)
                delta = crossing-speed
                signed = c['acceleration_mps2'] if target/3.6 > speed else -c['deceleration_mps2']
                accelerations = [0] if c['reaction_seconds'] > 0 else []
                if abs(delta) > 1e-8: accelerations.append(signed)
                if abs(crossing-target/3.6) < 1e-8: accelerations.append(0)
                braking = max(0, -delta)*(1 if c['mode']=='BRAKE' else .15 if c['mode']=='ENGINE_BRAKE' else 0)
                risk = self.settings.unknown_risk if c['confidence'] is None else 1-c['confidence']
                yield dict(signal_id=prediction.signal_id, start_at=now, arrival_at=at, duration=duration,
                    start_speed_mps=speed, crossing_speed_mps=crossing, distance_m=distance,
                    target_kmh=target, mode=c['mode'], stops=0, wait_seconds=0,
                    braking=braking, accelerations=accelerations, risk=risk,
                    candidate=dict(c, target_kmh=target, range_min_kmh=target, range_max_kmh=target, arrival_at=at))

    def _edges(self, prediction, distance, speed, limit, now, committed=None, reaction=0):
        yield from self._moving(prediction, distance, speed, limit, now, committed, reaction)
        v = self.single.vehicle
        # Stop at the actual integrated position, never teleport to the stop line.
        delay = reaction if committed is not None and committed[0] == 0 else v.reaction_delay
        stop_distance = speed*delay + speed*speed/(2*v.comfortable_deceleration)
        if stop_distance > distance-v.stop_buffer_m: return
        stopped_at = now + (delay+speed/v.comfortable_deceleration if speed > 1e-8 else 0)
        remaining = distance-stop_distance
        accel = min(v.comfortable_acceleration, self.single.settings.unknown_confidence_acceleration) if prediction.confidence is None else v.comfortable_acceleration
        for window in prediction.windows:
            if window.interior_start is None: continue
            for target in {self.single.settings.min_moving_speed_mps, limit}:
                travel = arrival_time(remaining, 0, target, accel, v.comfortable_deceleration, v.reaction_delay)
                depart = max(stopped_at, window.interior_start+self.single.settings.edge_margin_seconds-travel)
                only = replace(prediction, windows=(window,))
                for leg in self._moving(only, remaining, 0, limit, depart):
                    # Starting from rest is not a new complete stop.
                    yield dict(leg, start_at=now, duration=leg['arrival_at']-now,
                        start_speed_mps=speed, distance_m=distance, stops=int(speed > self.settings.stop_speed_mps),
                        wait_seconds=depart-stopped_at, stop_at=stopped_at,
                        stop_distance_m=stop_distance, departure_at=depart,
                        braking=leg['braking']+speed,
                        accelerations=([0,-v.comfortable_deceleration,0] if speed>1e-8 else [0])+leg['accelerations'],
                        stop_reaction_seconds=delay)

    def solve(self, points, *, position, speed, speed_limit, now, committed_command=None, committed_reaction_seconds=0):
        if not all(math.isfinite(x) for x in (position, speed, speed_limit, now)) or speed < 0 or speed_limit <= 0:
            raise ValueError('Invalid trajectory input')
        selected = []
        boundary = None
        boundary_position = None
        for x, prediction in points:
            if not math.isfinite(x): raise ValueError('Invalid point position')
            if x <= position: continue
            if selected and x <= selected[-1][0]: raise ValueError('Points must be ordered')
            if len(selected) == self.settings.max_signals: break
            if prediction.reason or prediction.valid_until <= now or not prediction.windows:
                boundary = prediction.signal_id
                boundary_position = x
                break  # Never jump over an unknown control point.
            selected.append((x, prediction))
        info = dict(status='NO_PLAN', legs=[], alternatives=[], cost=None, baseline=None,
                    analyzed_signals=[p.signal_id for _,p in selected], boundary=boundary,
                    algorithm='bounded beam search', model_version=points[0][1].model_version if points else 0)
        if not selected:
            p = points[0][1] if points else None
            return self.single.fallback(p, points[0][0]-position if points else 0, speed,
                'NO_PREDICTION', 'Brak ważnej prognozy najbliższego punktu.'), info
        beam = [()]
        for index, (x, prediction) in enumerate(selected):
            expanded = []
            for legs in beam:
                t = legs[-1]['arrival_at'] if legs else now
                u = legs[-1]['crossing_speed_mps'] if legs else speed
                distance = x-(selected[index-1][0] if index else position)
                for leg in self._edges(prediction, distance, u, speed_limit, t,
                        committed_command if not legs else None, committed_reaction_seconds if not legs else 0):
                    if leg['arrival_at'] > now+self.settings.horizon_seconds: continue
                    if index == len(selected)-1 and boundary_position is not None:
                        v = self.single.vehicle
                        crossing_speed = leg['crossing_speed_mps']
                        stopping = crossing_speed*v.reaction_delay+crossing_speed**2/(2*v.comfortable_deceleration)
                        if stopping > boundary_position-x-v.stop_buffer_m: continue
                    expanded.append(legs+(leg,))
            if not expanded:
                info['boundary'] = prediction.signal_id
                if index:
                    v = self.single.vehicle
                    space = x-selected[index-1][0]-v.stop_buffer_m
                    beam = [path for path in beam if path[-1]['crossing_speed_mps']*v.reaction_delay
                            + path[-1]['crossing_speed_mps']**2/(2*v.comfortable_deceleration) <= space] or [()]
                break
            # Preserve different first commands/windows when pruning similar branches.
            expanded.sort(key=lambda path: self.cost(path)['total'])
            unique = {}
            for path in expanded:
                first, last = path[0], path[-1]
                key = (first['target_kmh'], first.get('stop_at'), first['candidate']['window_start'],
                       round(last['arrival_at'], 1), round(last['crossing_speed_mps'], 1))
                unique.setdefault(key, path)
                if len(unique) >= self.settings.beam_width: break
            beam = list(unique.values())
        best = min(beam, key=lambda path: self.cost(path)['total'])
        # Hysteresis selects a whole revalidated path, never smooths just its first
        # target while leaving downstream crossing times inconsistent.
        if best and committed_command is not None:
            continuing = [path for path in beam if path and 'stop_at' not in path[0]
                          and abs(path[0]['target_kmh']/3.6-committed_command[0])<1e-8
                          and path[0]['candidate']['reaction_seconds']==committed_reaction_seconds]
            if continuing:
                held = min(continuing, key=lambda path: self.cost(path)['total'])
                if self.cost(held)['total'] <= self.cost(best)['total']+self.settings.switch_cost_tolerance:
                    best = held
        if not best:
            return self.single.fallback(selected[0][1], selected[0][0]-position, speed,
                'STOP_REQUIRED', 'Brak wykonalnej trajektorii w przeszukanym horyzoncie.'), info
        info.update(status='COMPLETE' if len(best)==len(selected) and boundary is None and info['boundary'] is None else 'PARTIAL',
                    legs=list(best), cost=self.cost(best),
                    alternatives=[dict(target_kmh=p[0]['target_kmh'], stops=self.cost(p)['raw']['stops'],
                        arrival_at=p[-1]['arrival_at'], cost=self.cost(p)['total']) for p in beam[:5]])
        # Greedy baseline uses the same dynamics/windows and cost, but never looks ahead.
        baseline = []
        for index, (x, prediction) in enumerate(selected[:len(best)]):
            t = baseline[-1]['arrival_at'] if baseline else now
            u = baseline[-1]['crossing_speed_mps'] if baseline else speed
            distance = x-(selected[index-1][0] if index else position)
            edges = list(self._edges(prediction, distance, u, speed_limit, t))
            edges = [e for e in edges if e['arrival_at'] <= now+self.settings.horizon_seconds]
            if not edges: break
            baseline.append(min(edges, key=lambda leg: self.cost([leg])['total']))
        info['baseline'] = dict(complete=len(baseline)==len(best), legs=baseline,
                                cost=self.cost(baseline) if len(baseline)==len(best) else None)
        first, prediction = best[0], selected[0][1]
        c = first['candidate']
        if 'stop_at' in first and (speed > 1e-8 or first['departure_at'] > now+1e-6):
            raw = self.single.fallback(prediction, selected[0][0]-position, speed,
                'STOP_REQUIRED', 'Plan korytarza: zatrzymanie i oczekiwanie na wybrane zielone.')
            return replace(raw, valid_until=min(p.valid_until for _,p in selected)), info
        raw = Recommendation('READY', prediction.signal_id, first['target_kmh'], first['target_kmh'], first['target_kmh'],
            self.single.command(first['target_kmh'], speed, first['mode']),
            f'Plan przez {len(best)} punktów; prognozowane zatrzymania: {info["cost"]["raw"]["stops"]}.',
            prediction.model_version, c['window_start'], c['window_end'], first['arrival_at'],
            c['acceleration_mps2'], c['deceleration_mps2'], c['confidence'],
            min(c['interior_end'], *(p.valid_until for _,p in selected)), (c,), c['reaction_seconds'])
        return raw, info
