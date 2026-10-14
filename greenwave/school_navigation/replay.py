"""Bounded public state over the existing read-only simulation replay engine."""
from greenwave.replay import ReplaySession


class SimulationReplay(ReplaySession):
    def state(self):
        row=self._last or {}
        return {'model_seconds':self.time,'duration':self.duration,'running':self.running,
                'rate':self.rate,'position':row.get('position'),'speed_mps':row.get('speed_mps'),
                'target_speed_mps':row.get('target_speed_mps')}
