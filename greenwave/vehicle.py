"""Synthetic driver/plant. Signal truth stays here, outside the solver.

Cruise commands have reaction delay. A separate idealized signal guard may
override them to brake, and reports impossible cases rather than teleporting.
"""
from collections import deque
import math
from greenwave.positioning import PositionSample
from greenwave.solver import VehicleSettings


class DynamicVehicle:
    def __init__(self, settings=VehicleSettings()):
        self.settings=settings
        self.reset()

    def reset(self):
        self.elapsed=self.position=self.speed=self.acceleration=0.0
        self.target=0.0
        self.accel_limit=self.settings.comfortable_acceleration
        self.decel_limit=self.settings.comfortable_deceleration
        self.pending=deque()
        self.last_command=None
        self.incident=None
        self.crossings=[]

    def sample(self):
        return PositionSample(self.elapsed,self.position,self.speed)

    def command(self,target,acceleration=None,deceleration=None):
        if not math.isfinite(target) or target<0:
            raise ValueError('Invalid target speed')
        if any(v is not None and (not math.isfinite(v) or v<=0) for v in (acceleration,deceleration)):
            raise ValueError('Command acceleration/deceleration must be positive')
        command=(target,acceleration or self.settings.comfortable_acceleration,deceleration or self.settings.comfortable_deceleration)
        if command != self.last_command:
            self.pending.append((self.elapsed+self.settings.reaction_delay,command))
            self.last_command=command

    def step(self,dt,limit,signal=None,truth=None):
        if not math.isfinite(dt) or not 0 < dt <= .1+1e-9 or not math.isfinite(limit) or limit <= 0:
            raise ValueError('Vehicle step must be in (0, .1] and limit positive')
        if self.incident:return
        while self.pending and self.pending[0][0] <= self.elapsed+1e-8:
            _,(self.target,self.accel_limit,self.decel_limit)=self.pending.popleft()
        target=min(limit,max(0,self.target))
        acceleration=min(self.accel_limit,self.settings.max_acceleration,(target-self.speed)/dt) if target>=self.speed else max(-self.decel_limit,(target-self.speed)/dt)
        if signal is not None and truth(signal,self.elapsed) != 'GREEN':
            usable=signal.road_position_m-self.position-self.settings.stop_buffer_m
            stopping=self.speed*self.settings.reaction_delay+self.speed*self.speed/(2*self.settings.comfortable_deceleration)
            if usable <= stopping+1:
                if usable <= .05 and self.speed <= .1:
                    acceleration=-self.speed/dt
                elif usable <= 0 or self.speed*self.speed/(2*self.settings.max_deceleration) > usable+1e-6:
                    self.incident=f'{signal.id}: niewykonalne zatrzymanie w granicach modelu. Symulacja przerwana.'
                    return
                else:
                    needed=self.speed*self.speed/(2*max(.01,usable))
                    acceleration=min(acceleration,-min(self.settings.max_deceleration,max(self.settings.comfortable_deceleration,needed)))
        acceleration=max(-self.settings.max_deceleration,min(self.settings.max_acceleration,acceleration))
        moving=min(dt,self.speed/-acceleration) if acceleration<0 else dt
        distance=self.speed*moving+.5*acceleration*moving*moving
        next_position=self.position+distance
        if signal is not None and self.position < signal.road_position_m <= next_position:
            d=signal.road_position_m-self.position
            crossing_time=d/self.speed if abs(acceleration)<1e-12 else 2*d/(self.speed+math.sqrt(max(0,self.speed*self.speed+2*acceleration*d)))
            colour=truth(signal,self.elapsed+crossing_time)
            if colour!='GREEN':
                self.incident=f'{signal.id}: próba przekroczenia linii przy {colour}. Symulacja przerwana bez przestawiania pojazdu.'
                return
            self.crossings.append(dict(signal_id=signal.id,time=self.elapsed+crossing_time,state=colour,speed_mps=self.speed+acceleration*crossing_time))
        self.position=next_position
        self.speed=max(0,min(limit,self.speed+acceleration*dt))
        self.acceleration=acceleration
        self.elapsed+=dt
