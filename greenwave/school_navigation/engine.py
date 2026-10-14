"""One M8 engine and clock per recording; UTC milliseconds end at this adapter."""
from dataclasses import asdict
from datetime import datetime, timezone
from greenwave.application import GreenWaveApplication
from greenwave.clocks import SimulationClock
from greenwave.school_accounts.errors import AuthError
from greenwave.school_records.writes import fields, revision


class Drive:
    def __init__(self, recorder, context, mode='SIMULATION'):
        self.recorder, self.context, self.mode = recorder, context, mode
        self.app = GreenWaveApplication(
            clock=SimulationClock(utc_now=lambda: datetime.fromtimestamp(recorder.repo.clock()/1000, timezone.utc)),
            runs_root=context['logger'].root)
        # Reset only before attaching the coordinator's writer. Never a second run.
        if mode == 'LIVE': self.app.reset('zwirki_wigury')
        self.app.logger = context['logger']
        self.app.set_view_mode(mode)
        self.revision = 0
        self.closed = False
        self.state = None

    def start(self):
        if self.mode == 'SIMULATION': self.app.control(running=True)
        self.tick()

    def tick(self):
        if self.closed: return
        self.state = self.app.snapshot()
        if self.app.logger.active: self.app.logger.stream.flush()

    def close(self):
        if self.closed: return
        self.app.clock.set_running(False)
        self.closed = True
        # Manifest finalization belongs to Recording, not app.close().

    def metadata(self):
        return {'application_version':'school-navigation-9', 'dataset':self.app.dataset,
                'corridor_id':self.app.corridor.id, 'corridor':asdict(self.app.corridor),
                'timebase':'SIMULATION' if self.mode=='SIMULATION' else 'UTC_ELAPSED',
                'school_engine':'M8', 'utc_epoch':self.app.utc_epoch}

    def dto(self):
        # Freshness is recomputed at every read. No raw paths or engine sessions leak.
        s=self.app.snapshot() if not self.closed else self.state
        mapping=self.app.mapping_snapshot()
        sample=self.app.external_position.sample()
        sim=self.mode=='SIMULATION'
        quality=self.app.external_position.status()
        fresh=quality['state']=='RECEIVING' and quality['freshness_status']=='FRESH'
        return {'mode':self.mode, 'running':s['running'] and not self.closed,
            'control_revision':self.revision, 'rate':s['rate'], 'response_at':self.recorder.repo.clock(),
            'simulation_seconds':s['simulation_seconds'], 'dataset':s['dataset'],
            'synthetic':sim, 'speed_mps':s['position']['speed_mps'] if sim else (None if sample is None or not fresh else sample.speed_mps),
            'speed_source':'SIMULATION' if sim else (None if sample is None else sample.speed_source),
            'speed_limit_mps':s['speed_limit_mps'] if sim else (mapping['recommendation_eligibility'].get('solver_input') or {}).get('speed_limit_mps'),
            'heading_deg':None if sample is None else sample.heading_deg,
            'position':s['position'] if sim else (None if sample is None or quality['state']=='STALE' else {k:getattr(sample,k) for k in ('latitude','longitude','speed_mps')}),
            'signals':s['signals'] if sim else [], 'mapping':mapping,
            'quality':{'source':'SYNTHETIC','state':'DEMO'} if sim else self.app.external_position.status(),
            'simulation_recommendation':s['recommendation'] if sim else None,
            'live_recommendation':None if sim else mapping['live_recommendation'],
            'eligibility':{'allowed':False,'reason_codes':['SIMULATION_NOT_LIVE']} if sim else mapping['recommendation_eligibility']}

    def control(self, command, expected):
        if self.closed: raise AuthError(409,'NAVIGATION_CLOSED')
        revision(expected)
        if expected != self.revision: raise AuthError(409,'REVISION_CONFLICT')
        if self.mode != 'SIMULATION': raise AuthError(403,'SIMULATION_REQUIRED')
        if command not in {'PAUSE','RESUME'}: raise AuthError(422,'VALIDATION')
        self.app.control(running=command=='RESUME'); self.revision+=1; self.tick()

    def configure(self, body):
        fields(body,{'expected_revision'},{'rate','speed_kmh','follow_recommendation'})
        if len(body)==1: raise AuthError(422,'VALIDATION')
        revision(body['expected_revision'])
        if body['expected_revision']!=self.revision: raise AuthError(409,'REVISION_CONFLICT')
        if self.mode!='SIMULATION' or self.closed: raise AuthError(403,'SIMULATION_REQUIRED')
        try: self.app.control(**{k:v for k,v in body.items() if k!='expected_revision'})
        except ValueError: raise AuthError(422,'VALIDATION') from None
        self.revision+=1;self.tick()
