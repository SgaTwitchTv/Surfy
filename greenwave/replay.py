"""Deterministic, read-only playback of a completed M5 raw CSV."""
import csv
import json
from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class ReplayPositionProvider:
    """Position source used by replay consumers; never writes to a run."""
    timestamp: str
    model_seconds: float
    position_m: float | None
    speed_mps: float | None
    target_speed_mps: float | None


class ReplaySession:
    def __init__(self, logger):
        self.logger = logger
        self.reset()

    def reset(self):
        self.run_id = None; self.rows = []; self.time = 0.0; self.cursor = 0
        self.running = False; self.rate = 1.0; self.error = None; self._last = None

    def state(self):
        row = self._last or {}
        return dict(loaded=self.run_id is not None, run_id=self.run_id, running=self.running,
                    rate=self.rate, model_seconds=self.time, duration=self.duration,
                    cursor=self.cursor, position=row.get('position'), speed_mps=row.get('speed_mps'),
                    target_speed_mps=row.get('target_speed_mps'), event=row.get('event'),
                    signal_id=row.get('signal_id'), timestamp=row.get('timestamp'),
                    events=self.events(self.time), error=self.error)

    @property
    def duration(self):
        return self.rows[-1]['model_seconds'] if self.rows else 0.0

    def load(self, run_id):
        directory = self.logger._directory(run_id)
        if not (directory/'complete.json').exists(): raise ValueError('Replay wymaga zakończonego nagrania')
        rows=[]
        with (directory/'raw.csv').open(encoding='utf-8', newline='') as stream:
            for row in csv.DictReader(stream):
                try:
                    row['model_seconds']=float(row['model_seconds']); row['sequence']=int(row['sequence'])
                    row['position']=float(row['current_corridor_position']) if row['current_corridor_position'] else None
                    row['speed_mps']=float(row['speed_mps']) if row['speed_mps'] else None
                    row['target_speed_mps']=float(row['target_speed_mps']) if row['target_speed_mps'] else None
                    row['payload']=json.loads(row['payload_json'] or '{}')
                except (ValueError, TypeError, json.JSONDecodeError) as error:
                    raise ValueError(f'Niepoprawny rekord replay sequence={row.get("sequence")}: {error}') from error
                rows.append(row)
        if not rows or rows[0]['event'] != 'RUN_START': raise ValueError('Brak poprawnego RUN_START')
        if any(b['sequence'] != a['sequence']+1 for a,b in zip(rows,rows[1:])): raise ValueError('Nieciągła kolejność replay')
        self.run_id=run_id; self.rows=rows; self.time=rows[0]['model_seconds']; self.cursor=0; self.running=False; self.error=None
        self._rebuild(); return self.state()

    def _rebuild(self):
        self._last=None; self.cursor=0
        for index,row in enumerate(self.rows):
            if row['model_seconds'] <= self.time+1e-9: self._last=row; self.cursor=index+1
            else: break

    def seek(self, seconds):
        if self.run_id is None: raise ValueError('Najpierw wczytaj nagranie')
        if not isinstance(seconds,(int,float)) or isinstance(seconds,bool) or not 0 <= seconds <= self.duration: raise ValueError('Seek poza nagraniem')
        self.time=float(seconds); self._rebuild(); self.running=False; return self.state()

    def advance(self, real_seconds):
        if not self.running or self.run_id is None:return self.state()
        if not isinstance(real_seconds,(int,float)) or real_seconds < 0: raise ValueError('Invalid replay delta')
        self.time=min(self.duration,self.time+real_seconds*self.rate); self._rebuild()
        if self.time >= self.duration-1e-9:self.running=False
        return self.state()

    def events(self, until):
        return [dict(sequence=r['sequence'],event=r['event'],signal_id=r['signal_id'],timestamp=r['timestamp'],model_seconds=r['model_seconds'],payload=r['payload']) for r in self.rows if r['model_seconds'] <= until+1e-9]

    def command(self, command, value=None):
        if command=='load': return self.load(value)
        if command=='play':
            if self.run_id is None: raise ValueError('Najpierw wczytaj nagranie')
            self.running=True; return self.state()
        if command=='pause': self.running=False; return self.state()
        if command=='seek': return self.seek(value)
        if command=='rate':
            if value not in (1,2,5,10): raise ValueError('Allowed replay rates: 1, 2, 5, 10')
            self.rate=value; return self.state()
        raise ValueError('Unknown replay command')
