"""One application state shared by the map, observation inputs and diagnostics."""
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from greenwave.clocks import SimulationClock
from greenwave.events import EventBus, ModelResynchronized, ObservationType, PredictionUpdated, SignalObserved, SignalState
from greenwave.models import load_corridor
from greenwave.observations import ObservationService
from greenwave.prediction import PredictionEngine, load_prediction_config
from greenwave.simulation import SignalSimulator, SimulationSettings
from greenwave.solver import SingleSignalSolver, Recommendation, RecommendationStabilizer, load_solver_config
from greenwave.vehicle import DynamicVehicle
from greenwave.trajectory import TrajectorySolver, load_trajectory_config
from greenwave.telemetry import RunLogger
from greenwave.positioning import ExternalPositionProvider
from greenwave.route_geometry import RouteRegistry
from greenwave.map_matching import MapMatcher
from greenwave.route_events import StopLineCrossingDetector, next_stop_line
from greenwave.live_navigation import evaluate_live_navigation

DATA = Path(__file__).resolve().parent.parent / 'data'
DATASETS = ('synthetic_s1_s5', 'zwirki_wigury')


class GreenWaveApplication:
    def __init__(self, clock=None, runs_root=None):
        self.clock = clock if clock is not None else SimulationClock()
        self.bus = EventBus()
        self.observations = ObservationService(self.bus)
        self.speed_kmh = 36.0
        self.jitter = False
        self.follow_recommendation = True
        self.last_change = None
        self.logger = RunLogger(DATA/'runs' if runs_root is None else runs_root)
        self._next_sample_at = 0
        self.external_position = ExternalPositionProvider()
        self.routes = RouteRegistry(DATA / 'routes')
        self.selected_route = None
        self.map_matcher = MapMatcher()
        self.route_events = StopLineCrossingDetector()
        self.mapping_events = []
        self.route_observations = []
        self.view_mode = 'SIMULATION'
        self.bus.subscribe(self._log_observation, SignalObserved)
        self.bus.subscribe(self._on_observation, SignalObserved)
        self.reset()

    def set_view_mode(self, mode):
        if mode not in ('SIMULATION', 'LIVE', 'GPS_REPLAY'):
            raise ValueError('Unknown view mode')
        self.view_mode = mode
        self._record('VIEW_MODE', payload=dict(mode=mode))

    def select_route(self, route_id):
        route = None if route_id is None else self.routes.load(route_id)
        self.selected_route = route
        self.map_matcher.set_route(route)
        self.route_events.set_route(route, f'live-{self.session_id}')
        self.mapping_events = []
        self._record('ROUTE_SELECTED', payload=None if route is None else dict(
            route_id=route.route_id, geometry_version=route.geometry_version,
            geometry_hash=route.geometry_hash))
        return self.mapping_snapshot()

    def mapping_snapshot(self):
        external_status = self.external_position.status()
        result = self.map_matcher.current(external_status.get('receipt_age_seconds'))
        eligibility = self._live_recommendation_eligibility(result, external_status)
        live_recommendation = None
        if eligibility['allowed']:
            solver_input = eligibility['solver_input']
            prediction = self.prediction.predict(
                solver_input['signal_id'], solver_input['prediction_time_seconds'])
            live_recommendation = asdict(self.solver.solve(
                prediction, distance=solver_input['distance_m'],
                speed=solver_input['speed_mps'], speed_limit=solver_input['speed_limit_mps'],
                now=solver_input['prediction_time_seconds']))
            eligibility['target_speed_kmh'] = live_recommendation['target_kmh']
        return dict(
            selected_route=None if self.selected_route is None else self.selected_route.public_dict(),
            result=result.as_dict(), next_stop_line=next_stop_line(self.selected_route, result),
            crossing_events=list(self.mapping_events[-100:]),
            route_observations=list(self.route_observations[-100:]),
            recommendation_eligibility=eligibility,
            live_recommendation=live_recommendation)

    def _live_recommendation_eligibility(self, result, external_status):
        route = self.selected_route
        sample = self.external_position.sample()
        next_line = next_stop_line(route, result)
        signal = (None if next_line is None or next_line.get('signal_id') is None else
                  self.prediction.signals.get(next_line['signal_id']))
        phase_verified = bool(signal is not None and signal.verified and
                              signal.data_quality == 'VERIFIED')
        server_utc_seconds = self.clock.read().timestamp.timestamp()
        clock_compatible = bool(
            sample is not None and self.utc_epoch is not None and
            sample.elapsed_seconds > 1_000_000_000 and
            abs(sample.elapsed_seconds - server_utc_seconds) <= 30)
        prediction_time = (sample.elapsed_seconds - self.utc_epoch
                           if clock_compatible else None)
        if phase_verified and prediction_time is not None:
            prediction = self.prediction.predict(signal.id, prediction_time)
            phase_verified = bool(not prediction.reason and prediction.windows)
        return evaluate_live_navigation(
            route, result, sample, external_status,
            prediction_time_seconds=prediction_time,
            phase_data_verified=phase_verified)

    def reset(self, dataset='synthetic_s1_s5', jitter=False):
        if dataset not in DATASETS or not isinstance(jitter, bool):
            raise ValueError('Unknown dataset or invalid jitter option')
        # Validate all files before replacing an active session.
        corridor = load_corridor(DATA / 'corridors' / f'{dataset}.json')
        settings, relations = load_prediction_config(DATA / 'prediction' / f'{dataset}.json')
        engine = PredictionEngine(corridor, '', settings, relations)
        vehicle_settings,solver_settings=load_solver_config(DATA/'solver.json')
        trajectory_settings=load_trajectory_config(DATA/'trajectory.json')
        if self.logger.active:
            self._advance(self.clock.read())
            self._finish_recording('RESET')
        self.clock.reset()
        self.position=DynamicVehicle(vehicle_settings)
        self.solver=SingleSignalSolver(vehicle_settings,solver_settings)
        self.stabilizer=RecommendationStabilizer(self.solver)
        self.trajectory_solver=TrajectorySolver(self.solver,trajectory_settings)
        self.trajectory=None
        self.recommendation=None
        self._next_plan_at=0.0
        self.corridor = corridor
        self.dataset = dataset
        self.jitter = jitter
        self.available = corridor.speed_limit_mps is not None and all(s.road_position_m is not None for s in corridor.signals)
        self.session_id = self.observations.start_session(corridor)
        self.route_events.set_route(self.selected_route, f'live-{self.session_id}')
        self.map_matcher.reset()
        self.mapping_events = []
        reading = self.clock.read()
        self.utc_epoch = None if self.available else reading.timestamp.timestamp()
        engine.session_id = self.session_id
        engine.utc_epoch = self.utc_epoch
        self.prediction = engine
        self.simulator = SignalSimulator(SimulationSettings(jitter_seconds=2 if jitter else 0,
            extension_probability=.1 if jitter else 0, extension_seconds=8 if jitter else 0))
        self.last_change = None
        self._plan()

    def _on_observation(self, event):
        before = self.prediction.version
        changed = self.prediction.observe(event.observation)
        if changed:
            self.last_change = ModelResynchronized(self.session_id, event.observation.observation_id, changed, self.prediction.version)
            self.bus.publish(self.last_change)
        if self.prediction.version != before:
            self.bus.publish(PredictionUpdated(self.session_id, self.prediction.version))
            self._plan(max(self.position.elapsed,self.prediction.observation_time(event.observation)))

    def _next_signal(self):
        return next((s for s in self.corridor.signals if s.road_position_m is not None and s.road_position_m>self.position.position),None)

    def _plan(self, now=None):
        self._compute_plan(now)
        self._record('RECOMMENDATION', model_time=now, payload=dict(recommendation=asdict(self.recommendation),
            trajectory=self.trajectory))

    def _compute_plan(self, now=None):
        if self.position.incident:
            self.trajectory=None
            self.recommendation=Recommendation('UNSAFE',None,None,None,None,'BRAKE',self.position.incident,self.prediction.version)
            return
        signal=self._next_signal() if self.available else None
        if signal is None:
            self.trajectory=None
            self.recommendation=Recommendation('COMPLETE' if self.available else 'NO_PREDICTION',None,None,None,None,'HOLD',
                'Koniec odcinka.' if self.available else 'Brak geometrii lub limitu.',self.prediction.version)
            return
        now=self.position.elapsed if now is None else now
        distance=signal.road_position_m-self.position.position
        committed=self.position.last_command if self.follow_recommendation and len(self.position.pending)<=1 else None
        remaining_reaction=max(0,self.position.pending[0][0]-self.position.elapsed) if self.position.pending else 0
        points=[(s.road_position_m,self.prediction.predict(s.id,now)) for s in self.corridor.signals if s.road_position_m>self.position.position]
        raw,self.trajectory=self.trajectory_solver.solve(points,position=self.position.position,speed=self.position.speed,speed_limit=self.corridor.speed_limit_mps,now=now,
                             committed_command=committed,committed_reaction_seconds=remaining_reaction)
        self.recommendation=self.stabilizer.update(raw,now=now,distance=distance,speed=self.position.speed)
        if self.follow_recommendation:
            self.position.command(self.recommendation.target_kmh/3.6 if self.recommendation.status=='READY' else 0,
                self.recommendation.acceleration_mps2 or None,self.recommendation.deceleration_mps2 or None)
        else:
            self.position.command(min(self.speed_kmh/3.6,self.corridor.speed_limit_mps))

    def _advance(self, reading):
        if self.available:
            while self.position.elapsed+.1 <= reading.simulation_seconds+1e-8:
                if self.position.incident or self._next_signal() is None:
                    self.clock.set_running(False)
                    break
                if self.position.elapsed+1e-8>=self._next_plan_at:
                    self._plan()
                    self._next_plan_at=self.position.elapsed+.5
                crossings_before=len(self.position.crossings)
                self.position.step(.1,self.corridor.speed_limit_mps,self._next_signal(),self.simulator.state_at)
                for crossing in self.position.crossings[crossings_before:]:
                    self._record('PASS_STOP_LINE', model_time=crossing['time'], signal_id=crossing['signal_id'],
                        speed_mps=crossing['speed_mps'], current_corridor_position=self.prediction.signals[crossing['signal_id']].road_position_m, payload=crossing)
                if self.logger.active and self.position.elapsed+1e-8>=self._next_sample_at:
                    self._record('TELEMETRY')
                    self._next_sample_at=self.position.elapsed+1
                if self.position.incident:
                    self._record('INCIDENT', payload=dict(reason=self.position.incident))
                    self._finish_recording('INCIDENT')
                    self.clock.set_running(False)
                    self.recommendation=Recommendation('UNSAFE',None,None,None,None,'BRAKE',self.position.incident,self.prediction.version)
                    break
            if self._next_signal() is None:
                self.clock.set_running(False)
                self._plan()
                self._finish_recording('ROUTE_COMPLETE')

    def control(self, *, running=None, rate=None, speed_kmh=None, follow_recommendation=None):
        # Validate before any mutation; JSON boolean is not a numerical speed.
        if running is not None and not isinstance(running, bool):
            raise ValueError('running must be boolean')
        if rate is not None and (isinstance(rate, bool) or rate not in (1, 2, 5, 10)):
            raise ValueError('Allowed rates: 1, 2, 5, 10')
        if speed_kmh is not None and (isinstance(speed_kmh, bool) or not isinstance(speed_kmh, (int, float)) or not 0 <= speed_kmh <= 50):
            raise ValueError('Speed must be in [0, 50] km/h')
        if running and not self.available:
            raise ValueError('Simulation requires known geometry and speed limit')
        if follow_recommendation is not None and not isinstance(follow_recommendation,bool):
            raise ValueError('follow_recommendation must be boolean')
        self._advance(self.clock.read())
        if rate is not None:
            self.clock.set_rate(rate)
        if speed_kmh is not None:
            self.speed_kmh = speed_kmh
        if follow_recommendation is not None:
            self.follow_recommendation=follow_recommendation
        if speed_kmh is not None or follow_recommendation is not None:
            self._plan()
        if running is not None:
            at_end = self.available and self.position.sample().road_position_m >= self.corridor.signals[-1].road_position_m
            self.clock.set_running(running and not at_end and not self.position.incident)

        self._record('CONTROL', payload=dict(running=self.clock.running, rate=self.clock.rate,
            speed_kmh=self.speed_kmh, follow_recommendation=self.follow_recommendation))

    def observe(self, signal_id, state, event_type):
        if self.view_mode != 'SIMULATION':
            raise ValueError('Synthetic signal observations require simulation view')
        state, event_type = SignalState(state), ObservationType(event_type)
        if signal_id not in self.prediction.signals:
            raise ValueError('Unknown signal')
        reading = self.clock.read()
        self._advance(reading)
        return self.observations.observe_now(self.session_id, signal_id, state, event_type, reading)

    def observe_route(self, stop_line_id, state, event_type):
        if self.view_mode != 'LIVE' or self.selected_route is None:
            raise ValueError('Select a GPS route in live mode before observing its lights')
        colour, kind = SignalState(state), ObservationType(event_type)
        line = next((item for item in self.selected_route.stop_lines
                     if item.stop_line_id == stop_line_id), None)
        if line is None:
            raise ValueError('Unknown stop line on selected route')
        reading = self.clock.read()
        sample = self.external_position.sample()
        external_status = self.external_position.status()
        match = self.map_matcher.current(external_status.get('receipt_age_seconds'))
        observation = dict(
            observation_id=str(uuid4()), session_id=self.session_id,
            route_id=self.selected_route.route_id,
            geometry_version=self.selected_route.geometry_version,
            geometry_hash=self.selected_route.geometry_hash,
            stop_line_id=stop_line_id, state=colour.value, event_type=kind.value,
            timestamp=reading.timestamp.isoformat(), source='MANUAL_PASSENGER',
            line_verification=line.verification['status'],
            gps_freshness=external_status.get('freshness_status'),
            gps_receipt_age_seconds=external_status.get('receipt_age_seconds'),
            sample_ref=None if sample is None else
                f'{sample.device_id}:{sample.stream_id}:{sample.sample_sequence}',
            map_match_status=match.status,
            gps_latitude=None if sample is None else sample.latitude,
            gps_longitude=None if sample is None else sample.longitude)
        self.route_observations.append(observation)
        self._record('ROUTE_OBSERVATION', payload=observation,
                     signal_id=stop_line_id, source='MANUAL_PASSENGER',
                     latitude=observation['gps_latitude'],
                     longitude=observation['gps_longitude'])
        return observation

    def snapshot(self):
        reading = self.clock.read()
        self._advance(reading)
        now = reading.simulation_seconds if self.utc_epoch is None else reading.timestamp.timestamp() - self.utc_epoch
        if self.recommendation.valid_until is not None and self.recommendation.valid_until<=now:
            self._plan(now)
        if not self.available and self.logger.active and now>=self._next_sample_at:
            self._record('TELEMETRY', model_time=now)
            self._next_sample_at=now+1
        predictions = {p.signal_id: p for p in self.prediction.predict_all(now)}
        sample = self.position.sample()
        rows = []
        for signal in self.corridor.signals:
            prediction = predictions[signal.id]
            row = asdict(prediction)
            observation = row['last_observation']
            if observation:
                observation['timestamp'] = observation['timestamp'].isoformat()
            distance = None if signal.road_position_m is None else signal.road_position_m - sample.road_position_m
            row.update(name=signal.name, signal_type=signal.signal_type.value, road_position_m=signal.road_position_m,
                       distance_m=distance, passed=distance is not None and distance <= 0,
                       data_quality=signal.data_quality,
                       truth_state=self.simulator.state_at(signal, reading.simulation_seconds) if self.available else 'UNKNOWN')
            rows.append(row)
        history = []
        for event in self.observations.history[-100:]:
            row = asdict(event.observation)
            row['timestamp'] = row['timestamp'].isoformat()
            row['out_of_order'] = event.out_of_order
            history.append(row)
        external = self.external_position.sample()
        return dict(recording=self.logger.status(),dataset=self.dataset, session_id=self.session_id, running=self.clock.running,
            view_mode=self.view_mode, routes=self.routes.list(), mapping=self.mapping_snapshot(),
            trajectory=self.trajectory,trajectory_settings=asdict(self.trajectory_solver.settings),
            recommendation=asdict(self.recommendation),follow_recommendation=self.follow_recommendation,
            acceleration_mps2=self.position.acceleration,incident=self.position.incident,crossings=self.position.crossings,
            vehicle_settings=asdict(self.solver.vehicle),solver_settings=asdict(self.solver.settings),
            rate=self.clock.rate, speed_setting_kmh=self.speed_kmh, jitter=self.jitter,
            utc=reading.timestamp.isoformat(), model_time=now, simulation_seconds=reading.simulation_seconds,
            timebase='SIMULATION' if self.available else 'UTC_ELAPSED', position=asdict(sample),
            speed_limit_mps=self.corridor.speed_limit_mps, available=self.available,
            model_version=self.prediction.version, signals=rows, history=history,
            history_total=len(self.observations.history), settings=asdict(self.prediction.settings),
            external_position=None if external is None else asdict(external),
            external_status=self.external_position.status(),
            relations=[asdict(r) for r in self.prediction.relations],
            last_change=None if self.last_change is None else asdict(self.last_change))

    def ingest_external_position(self, **payload):
        """Accept one validated phone sample and retain it for the live bridge.

        Route projection remains optional.  Every accepted current sample is
        passed through the matcher and crossing detector; uncertain samples
        explicitly break crossing continuity.
        """
        sample = self.external_position.update(**payload)
        match = None
        if (self.external_position.last_update_accepted and
                sample is self.external_position.sample()):
            sample_ref = (f'{sample.device_id}:{sample.stream_id}:{sample.sample_sequence}'
                          if sample.device_id is not None else f'external:{self.external_position.count}')
            match = self.map_matcher.update(
                sample, sample_ref=sample_ref, receipt_age_seconds=0.0,
                measurement_age_lower_bound_seconds=sample.measurement_age_lower_bound_seconds,
                continuity_reset=self.external_position.last_update_continuity_reset)
            sample_time = (sample.elapsed_realtime_nanos / 1_000_000_000
                           if sample.elapsed_realtime_nanos is not None else sample.elapsed_seconds)
            created_events = self.route_events.update(
                match, sample_time_seconds=sample_time, sample_ref=sample_ref)
            self.mapping_events.extend(created_events)
            for event in created_events:
                event_name = ('ROUTE_STOP_LINE_CROSSING' if event['status'] == 'CONFIRMED'
                              else 'ROUTE_STOP_LINE_UNCONFIRMED')
                self._record(event_name, signal_id=event.get('signal_id'),
                             current_corridor_position=match.accepted_s_m,
                             source='MAP_MATCHING', payload=event)
        if self.logger.active and self.external_position.last_update_accepted:
            self._record('EXTERNAL_TELEMETRY', latitude=sample.latitude, longitude=sample.longitude,
                         heading=sample.heading_deg, gps_accuracy=sample.gps_accuracy_m,
                         speed_mps=sample.speed_mps,
                         current_corridor_position=sample.road_position_m,
                         source=sample.source,
                         payload=dict(phone_timestamp_seconds=sample.elapsed_seconds,
                                      acceleration_mps2=sample.acceleration_mps2,
                                      raw_speed_mps=sample.raw_speed_mps,
                                      calculated_speed_mps=sample.calculated_speed_mps,
                                      speed_source=sample.speed_source,
                                      position_quality=sample.position_quality,
                                      usable_for_live=sample.usable_for_live,
                                      quality_reasons=sample.quality_reasons,
                                      device_id=sample.device_id,
                                      stream_id=sample.stream_id,
                                      sample_sequence=sample.sample_sequence,
                                      elapsed_realtime_nanos=sample.elapsed_realtime_nanos,
                                      sent_elapsed_realtime_nanos=sample.sent_elapsed_realtime_nanos,
                                      measurement_age_lower_bound_seconds=sample.measurement_age_lower_bound_seconds,
                                      freshness_status=sample.freshness_status,
                                      live_control_eligible=sample.live_control_eligible,
                                      speed_accuracy_mps=sample.speed_accuracy_mps,
                                      heading_accuracy_deg=sample.heading_accuracy_deg,
                                      altitude_m=sample.altitude_m,
                                      vertical_accuracy_m=sample.vertical_accuracy_m,
                                      is_mock=sample.is_mock,
                                      map_match=None if match is None else match.as_dict()))
        return sample


    def _record_context(self, model_time=None):
        reading=self.clock.read()
        now=(self.position.elapsed if self.available else reading.timestamp.timestamp()-self.utc_epoch) if model_time is None else model_time
        return dict(timestamp=reading.timestamp, simulation_seconds=now if self.available else reading.simulation_seconds, model_seconds=now)

    def _record(self, event, model_time=None, payload=None, **fields):
        if not self.logger.active:return
        signal=self._next_signal() if self.available else None
        values=dict(source='SIMULATION' if self.available else 'UNAVAILABLE',
            speed_mps=self.position.speed if self.available else None,
            current_corridor_position=self.position.position if self.available else None,
            next_signal=signal.id if signal else None,
            target_speed_mps=self.recommendation.target_kmh/3.6 if self.recommendation and self.recommendation.target_kmh is not None else None)
        values.update(fields)
        self.logger.append(event, payload=payload, **self._record_context(model_time), **values)

    def _log_observation(self, event):
        observation=event.observation
        if not self.logger.active or observation.session_id!=self.session_id:return
        kind=observation.state.value+'_START' if observation.event_type==ObservationType.STATE_START else 'STATE_SEEN'
        self.logger.append(kind, timestamp=observation.timestamp, simulation_seconds=observation.simulation_seconds,
            model_seconds=self.prediction.observation_time(observation), signal_id=observation.signal_id, source=observation.source,
            payload=dict(observation=asdict(observation),out_of_order=event.out_of_order))

    def recording(self, command):
        if command not in ('start','stop'):raise ValueError('Unknown recording command')
        self._advance(self.clock.read())
        if command=='stop':
            self._finish_recording('USER_STOP')
            return
        if self.logger.active:raise ValueError('Nagranie już trwa')
        # A connected phone and an explicitly selected GPS route indicate a
        # field recording. Keep synthetic S1-S5 observations out of that run.
        if (self.selected_route is not None and self.view_mode != 'LIVE' and
                self.external_position.status()['state'] == 'RECEIVING'):
            self.set_view_mode('LIVE')
        reading=self.clock.read()
        metadata=dict(start_time=reading.timestamp,session_id=self.session_id,corridor_id=self.corridor.id,
            direction=self.corridor.direction,dataset=self.dataset,timebase='SIMULATION' if self.available else 'UTC_ELAPSED',
            start_model_seconds=self.position.elapsed if self.available else reading.timestamp.timestamp()-self.utc_epoch,
            application_version='M8-mapping-1',corridor=asdict(self.corridor),
            vehicle=asdict(self.solver.vehicle),solver=asdict(self.solver.settings),trajectory=asdict(self.trajectory_solver.settings),
            prediction_settings=asdict(self.prediction.settings),relations=[asdict(r) for r in self.prediction.relations],
            estimates={key:asdict(value) for key,value in self.prediction.estimates.items()},
            model_version=self.prediction.version,utc_epoch=self.utc_epoch,
            view_mode=self.view_mode,
            selected_route=None if self.selected_route is None else dict(
                route_id=self.selected_route.route_id,
                geometry_version=self.selected_route.geometry_version,
                geometry_hash=self.selected_route.geometry_hash),
            latest_observation_times=dict(self.prediction._latest_observation),
            simulator=asdict(self.simulator.settings),
            initial_vehicle=dict(target=self.position.target,acceleration=self.position.acceleration,
                accel_limit=self.position.accel_limit,decel_limit=self.position.decel_limit,
                pending=list(self.position.pending),last_command=self.position.last_command),
            initial_position=asdict(self.position.sample()) if self.available else None,
            initial_recommendation=asdict(self.recommendation),
            controls=dict(running=self.clock.running,rate=self.clock.rate,speed_kmh=self.speed_kmh,follow_recommendation=self.follow_recommendation))
        self.logger.start(metadata)
        self._record('RUN_START')
        self._record('TELEMETRY')
        self._next_sample_at=metadata['start_model_seconds']+1

    def _finish_recording(self, reason):
        if self.logger.active:
            self._record('TELEMETRY')
            self.logger.finish(reason,**self._record_context())

    def close(self):
        self._advance(self.clock.read())
        self._finish_recording('SERVER_SHUTDOWN')
