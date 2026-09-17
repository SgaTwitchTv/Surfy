"""M3: analytical reaction/ramp/cruise profiles for ONE control point.

Ranges are valid cruise setpoints for a specified ramp, not arbitrary average
speeds. All outputs are conditional on the supplied prediction windows.
"""
from dataclasses import dataclass, replace
import json
import math
from pathlib import Path
from greenwave.prediction import Prediction


@dataclass(frozen=True)
class VehicleSettings:
    comfortable_acceleration: float = 1.0
    max_acceleration: float = 2.0
    comfortable_deceleration: float = 1.5
    max_deceleration: float = 4.5
    coast_deceleration: float = .15
    engine_braking_deceleration: float = .45
    reaction_delay: float = 1.0
    stop_buffer_m: float = 2.0

    def __post_init__(self):
        for key,value in vars(self).items():
            if isinstance(value,bool) or not math.isfinite(value) or value < 0:
                raise ValueError(f'Invalid vehicle setting: {key}')
        if not 0 < self.coast_deceleration <= self.engine_braking_deceleration <= self.comfortable_deceleration <= self.max_deceleration:
            raise ValueError('Invalid braking limits')
        if not 0 < self.comfortable_acceleration <= self.max_acceleration:
            raise ValueError('Invalid acceleration limits')


@dataclass(frozen=True)
class SolverSettings:
    min_moving_speed_mps: float = 5.0
    edge_margin_seconds: float = .5
    minimum_hold_seconds: float = 2.0
    deadband_kmh: float = 1.0
    smoothing_alpha: float = .35
    max_uncertainty_for_acceleration: float = 8.0
    minimum_confidence_for_acceleration: float = .6
    unknown_confidence_acceleration: float = .8
    acceleration_slack_seconds: float = 8.0

    def __post_init__(self):
        for key,value in vars(self).items():
            if isinstance(value,bool) or not math.isfinite(value) or value < 0:
                raise ValueError(f'Invalid solver setting: {key}')
        if self.min_moving_speed_mps <= 0 or not 0 < self.smoothing_alpha <= 1:
            raise ValueError('Invalid minimum speed or smoothing')
        if not 0 <= self.minimum_confidence_for_acceleration <= 1 or self.unknown_confidence_acceleration <= 0:
            raise ValueError('Invalid acceleration confidence policy')


def load_solver_config(path: str | Path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    if data['schema_version'] != 1: raise ValueError('Unsupported solver configuration')
    return VehicleSettings(**data['vehicle']), SolverSettings(**data['solver'])


def profile_distance(seconds, initial, target, acceleration, deceleration, reaction):
    """Exact integral of reaction at initial speed, bounded ramp, then cruise."""
    if seconds <= reaction: return initial * max(0,seconds)
    time=seconds-reaction
    signed=acceleration if target >= initial else -deceleration
    ramp=abs(target-initial)/abs(signed)
    active=min(time,ramp)
    return initial*reaction+initial*active+.5*signed*active*active+target*max(0,time-ramp)


def arrival_time(distance, initial, target, acceleration, deceleration, reaction):
    if distance <= 0: return 0.0
    if initial > 0 and distance <= initial*reaction: return distance/initial
    remaining=distance-initial*reaction
    signed=acceleration if target >= initial else -deceleration
    ramp=abs(target-initial)/abs(signed)
    ramp_distance=(initial+target)*ramp/2
    if remaining <= ramp_distance and ramp > 0:
        # Stable root of d = v*t + a*t²/2, including deceleration.
        return reaction+2*remaining/(initial+math.sqrt(max(0,initial*initial+2*signed*remaining)))
    if target <= 0: return math.inf
    return reaction+ramp+(remaining-ramp_distance)/target


def average_speed_window(distance, now, start, end, min_speed, speed_limit):
    """P05 diagnostic only: instantaneous-speed approximation, not a command."""
    if distance <= 0 or end <= now or end <= start or min_speed > speed_limit: return None
    low=max(min_speed,distance/(end-now))
    high=min(speed_limit,distance/(start-now)) if start > now else speed_limit
    return (low,high) if low <= high else None


@dataclass(frozen=True)
class Recommendation:
    status: str
    signal_id: str | None
    target_kmh: int | None
    range_min_kmh: int | None
    range_max_kmh: int | None
    action: str
    reason: str
    model_version: int
    window_start: float | None = None
    window_end: float | None = None
    arrival_at: float | None = None
    acceleration_mps2: float = 0
    deceleration_mps2: float = 0
    confidence: float | None = None
    valid_until: float | None = None
    candidates: tuple[dict, ...] = ()
    reaction_seconds: float = 1.0


class SingleSignalSolver:
    def __init__(self, vehicle=VehicleSettings(), settings=SolverSettings()):
        self.vehicle,self.settings=vehicle,settings

    def fallback(self, prediction, distance, speed, status, reason):
        signal_id=prediction.signal_id if prediction else None
        version=prediction.model_version if prediction else 0
        usable=max(0,distance-self.vehicle.stop_buffer_m)
        stopping=speed*self.vehicle.reaction_delay+speed*speed/(2*self.vehicle.max_deceleration)
        if speed > .05 and stopping > usable:
            return Recommendation('UNSAFE',signal_id,None,None,None,'BRAKE',
                reason+' Zatrzymanie z przyjętym czasem reakcji nie jest wykonalne.',version)
        return Recommendation(status,signal_id,None,None,None,'STOP' if speed < .1 else 'BRAKE',reason,version)

    def solve(self, prediction: Prediction | None, *, distance: float, speed: float, speed_limit: float, now: float,
              committed_command=None, committed_reaction_seconds=0):
        if not all(math.isfinite(x) for x in (distance,speed,speed_limit,now)) or speed < 0 or speed_limit <= 0:
            raise ValueError('Invalid solver input')
        if distance <= 0:
            return Recommendation('PASSED',prediction.signal_id if prediction else None,None,None,None,'HOLD','Punkt już przekroczony.',prediction.model_version if prediction else 0)
        if speed > speed_limit+1e-6:
            return self.fallback(prediction,distance,speed,'LIMIT_EXCEEDED','Aktualna prędkość przekracza limit.')
        if prediction is None or prediction.reason or prediction.valid_until <= now:
            return self.fallback(prediction,distance,speed,'NO_PREDICTION','Brak ważnych danych do rekomendacji prędkości.')
        settings,vehicle=self.settings,self.vehicle
        acceleration=min(vehicle.comfortable_acceleration,vehicle.max_acceleration)
        if prediction.confidence is None:
            acceleration=min(acceleration,settings.unknown_confidence_acceleration)
        candidates=[]
        for window in prediction.windows:
            if window.interior_start is None or window.interior_end is None: continue
            start=max(window.interior_start,now)+settings.edge_margin_seconds
            end=min(window.interior_end,prediction.valid_until)-settings.edge_margin_seconds
            if end <= start: continue
            low=settings.min_moving_speed_mps
            high=speed_limit
            uncertain=(window.confidence is not None and window.confidence < settings.minimum_confidence_for_acceleration) or window.uncertainty_seconds > settings.max_uncertainty_for_acceleration
            if uncertain or end-now < settings.acceleration_slack_seconds:
                high=min(high,speed)  # No chasing a closing/low-quality window.
            if low > high: continue
            for mode,deceleration in [('COAST',vehicle.coast_deceleration),('ENGINE_BRAKE',vehicle.engine_braking_deceleration),('BRAKE',vehicle.comfortable_deceleration)]:
                def travel(t,u):return profile_distance(t-now,speed,u,acceleration,deceleration,vehicle.reaction_delay)
                # Distance at fixed time is monotone in the cruise setpoint.
                if travel(end,high) < distance or travel(start,low) > distance: continue
                lo,hi=low,high
                if travel(end,lo) < distance:
                    a,b=lo,hi
                    for _ in range(45):
                        mid=(a+b)/2
                        if travel(end,mid) < distance:a=mid
                        else:b=mid
                    lo=b
                if travel(start,hi) > distance:
                    a,b=lo,hi
                    for _ in range(45):
                        mid=(a+b)/2
                        if travel(start,mid) > distance:b=mid
                        else:a=mid
                    hi=a
                min_kmh,max_kmh=math.ceil(lo*3.6-1e-8),math.floor(hi*3.6+1e-8)
                if min_kmh > max_kmh: continue
                # Prefer the middle of a broad feasible range; revalidation handles stabilization.
                target=round((min_kmh+max_kmh)/2)
                arrival=now+arrival_time(distance,speed,target/3.6,acceleration,deceleration,vehicle.reaction_delay)
                if not start-1e-7 <= arrival <= end+1e-7: continue
                slowing=target/3.6 < speed-.15
                penalty=(0 if mode=='COAST' else 1 if mode=='ENGINE_BRAKE' else 2) if slowing else 0
                candidates.append(dict(target_kmh=target,range_min_kmh=min_kmh,range_max_kmh=max_kmh,
                    mode=mode,window_start=window.start,window_end=window.end,interior_start=start,interior_end=end,
                    arrival_at=arrival,deceleration_mps2=deceleration,acceleration_mps2=acceleration,
                    penalty=penalty,confidence=window.confidence,reaction_seconds=vehicle.reaction_delay))
            # Continuing an already-issued command does not restart human reaction time.
            if committed_command is not None:
                target_mps,committed_accel,committed_decel=committed_command
                target=round(target_mps*3.6)
                if low <= target_mps <= high and abs(target/3.6-target_mps)<1e-6 and committed_accel<=acceleration:
                    arrival=now+arrival_time(distance,speed,target_mps,committed_accel,committed_decel,committed_reaction_seconds)
                    if start <= arrival <= end:
                        mode='COAST' if committed_decel<=vehicle.coast_deceleration else 'ENGINE_BRAKE' if committed_decel<=vehicle.engine_braking_deceleration else 'BRAKE'
                        penalty=(0 if mode=='COAST' else 1 if mode=='ENGINE_BRAKE' else 2) if target_mps<speed-.15 else 0
                        candidates.append(dict(target_kmh=target,range_min_kmh=target,range_max_kmh=target,mode=mode,
                            window_start=window.start,window_end=window.end,interior_start=start,interior_end=end,
                            arrival_at=arrival,deceleration_mps2=committed_decel,acceleration_mps2=committed_accel,
                            penalty=penalty,confidence=window.confidence,reaction_seconds=committed_reaction_seconds))
        if not candidates:
            return self.fallback(prediction,distance,speed,'STOP_REQUIRED',
                'Brak wykonalnego profilu bez zatrzymania w dostępnych oknach i limitach M3.')
        best=min(candidates,key=lambda c:(c['penalty'],c['arrival_at'],-(c['range_max_kmh']-c['range_min_kmh'])))
        command=self.command(best['target_kmh'],speed,best['mode'])
        return Recommendation('READY',prediction.signal_id,best['target_kmh'],best['range_min_kmh'],best['range_max_kmh'],command,
            'Profil dla najbliższego punktu; przejazd warunkowy względem prognozy.',prediction.model_version,
            best['window_start'],best['window_end'],best['arrival_at'],best['acceleration_mps2'],best['deceleration_mps2'],
            best['confidence'],min(prediction.valid_until,best['interior_end']),tuple(candidates),best['reaction_seconds'])

    def command(self,target_kmh,speed,mode):
        delta=target_kmh-speed*3.6
        if abs(delta) <= self.settings.deadband_kmh:return 'HOLD'
        return 'ACCELERATE' if delta > 0 else mode


class RecommendationStabilizer:
    def __init__(self, solver):
        self.solver=solver
        self.previous=None
        self.changed_at=-math.inf

    def update(self, raw, *, now, distance, speed):
        previous=self.previous
        if raw.status != 'READY':
            self.previous=raw
            self.changed_at=now
            return raw  # Invalid recommendations are never held or smoothed.
        target=raw.target_kmh
        same=previous and previous.status=='READY' and previous.signal_id==raw.signal_id and previous.model_version==raw.model_version and previous.window_start==raw.window_start
        if same and raw.range_min_kmh <= previous.target_kmh <= raw.range_max_kmh:
            if now-self.changed_at < self.solver.settings.minimum_hold_seconds or abs(target-previous.target_kmh) <= self.solver.settings.deadband_kmh:
                target=previous.target_kmh
            else:
                target=round(previous.target_kmh+self.solver.settings.smoothing_alpha*(target-previous.target_kmh))
                target=max(raw.range_min_kmh,min(raw.range_max_kmh,target))
        best=next(c for c in raw.candidates if c['target_kmh']==raw.target_kmh and c['deceleration_mps2']==raw.deceleration_mps2 and c['window_start']==raw.window_start and c['reaction_seconds']==raw.reaction_seconds)
        arrival=now+arrival_time(distance,speed,target/3.6,raw.acceleration_mps2,raw.deceleration_mps2,raw.reaction_seconds)
        if not best['interior_start']-1e-6 <= arrival <= best['interior_end']+1e-6:
            target,arrival=raw.target_kmh,raw.arrival_at
        result=replace(raw,target_kmh=target,arrival_at=arrival,action=self.solver.command(target,speed,best['mode']))
        if previous is None or previous.target_kmh!=target or not same:self.changed_at=now
        self.previous=result
        return result
