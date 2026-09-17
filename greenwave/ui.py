from pathlib import Path
import tkinter as tk
from tkinter import ttk
from greenwave.clocks import SimulationClock
from greenwave.events import EventBus, ObservationType, SignalState
from greenwave.models import load_corridor
from greenwave.observations import ObservationService
from greenwave.positioning import SimulationPositionProvider
from greenwave.simulation import SignalSimulator, SimulationSettings

DATA = Path(__file__).resolve().parent.parent / 'data' / 'corridors'


class App:
    def __init__(self, root, clock=None):
        self.root = root
        root.title('GreenWave · laboratorium sygnalizacji · P02')
        root.geometry('1120x880')
        self.position = SimulationPositionProvider()
        self.clock = clock if clock is not None else SimulationClock()
        self.bus = EventBus()
        self.observations = ObservationService(self.bus)
        self.dataset = tk.StringVar(value='synthetic_s1_s5')
        self.speed = tk.DoubleVar(value=36)
        self.rate = tk.StringVar(value='1')
        self.jitter = tk.BooleanVar(value=False)
        self.status = tk.StringVar()
        self.warning = tk.StringVar()
        self.selected_signal = tk.StringVar()
        self.observation_type = tk.StringVar(value='Początek fazy')
        self.observation_status = tk.StringVar()
        self.session_status = tk.StringVar()
        frame = ttk.Frame(root, padding=24)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='GreenWave / Signal Lab', font=('Segoe UI', 24, 'bold')).pack(anchor='w')
        ttk.Label(frame, textvariable=self.warning, wraplength=950).pack(anchor='w', pady=12)
        controls = ttk.Frame(frame)
        controls.pack(fill='x')
        box = ttk.Combobox(controls, textvariable=self.dataset, values=['synthetic_s1_s5', 'zwirki_wigury'], state='readonly', width=24)
        box.pack(side='left')
        box.bind('<<ComboboxSelected>>', lambda _: self.reset())
        self.start_button = ttk.Button(controls, text='Start / Pauza', command=self.toggle)
        self.start_button.pack(side='left', padx=8)
        ttk.Button(controls, text='Reset', command=self.reset).pack(side='left')
        ttk.Label(controls, text='  Tempo: ').pack(side='left')
        rate_box = ttk.Combobox(controls, textvariable=self.rate, values=['1','2','5','10'], state='readonly', width=4)
        rate_box.pack(side='left')
        rate_box.bind('<<ComboboxSelected>>', self.change_rate)
        ttk.Checkbutton(frame, text='Scenariusz testowy: jitter ±2 s i 10% szans na wydłużenie zielonego o 8 s (reset)', variable=self.jitter, command=self.reset).pack(anchor='w', pady=12)
        ttk.Label(frame, text='Prędkość sondy [km/h] — ruch testowy bez modelu hamowania i reakcji na czerwone').pack(anchor='w')
        self.slider = ttk.Scale(frame, from_=0, to=50, variable=self.speed)
        self.slider.pack(fill='x')
        ttk.Label(frame, textvariable=self.status, font=('Segoe UI',16)).pack(anchor='w', pady=14)
        self.canvas = tk.Canvas(frame, height=100, background='#122822', highlightthickness=0)
        self.canvas.pack(fill='x', pady=8)
        self.table = ttk.Treeview(frame, columns=('name','distance','type','state'), show='headings', height=5)
        for key, label, width in [('name','Punkt kontroli',390),('distance','Pozycja [m]',110),('type','Model',150),('state','Stan symulacji',140)]:
            self.table.heading(key,text=label)
            self.table.column(key,width=width)
        self.table.pack(fill='x')
        ttk.Label(frame,text='TARGET SPEED: —   |   Prognoza i solver: kolejne etapy. UNKNOWN oznacza brak podstaw do wyznaczenia stanu.',wraplength=950).pack(anchor='w',pady=12)
        ttk.Separator(frame).pack(fill='x', pady=4)
        ttk.Label(frame, text='Obserwacje ręczne', font=('Segoe UI', 14, 'bold')).pack(anchor='w')
        ttk.Label(frame, textvariable=self.session_status).pack(anchor='w')
        observer = ttk.Frame(frame)
        observer.pack(fill='x', pady=8)
        self.signal_box = ttk.Combobox(observer, textvariable=self.selected_signal, state='readonly', width=35)
        self.signal_box.pack(side='left')
        ttk.Combobox(observer, textvariable=self.observation_type, values=['Początek fazy', 'Widzę stan teraz'], state='readonly', width=20).pack(side='left', padx=8)
        self.observation_buttons = {}
        for state in SignalState:
            button = ttk.Button(observer, text=f'{state.value} NOW', command=lambda state=state: self.observe(state))
            button.pack(side='left', padx=3)
            self.observation_buttons[state] = button
        ttk.Label(frame, textvariable=self.observation_status, wraplength=1050).pack(anchor='w')
        history_frame = ttk.Frame(frame)
        history_frame.pack(fill='both', expand=True, pady=8)
        columns = ('utc', 'simulation', 'session', 'signal', 'state', 'kind', 'source', 'order')
        self.history_table = ttk.Treeview(history_frame, columns=columns, show='headings', height=6)
        for key, label, width in zip(columns,
                ('Czas UTC', 'Czas sym. [s]', 'Sesja', 'Punkt', 'Stan', 'Zdarzenie', 'Źródło', 'Kolejność'),
                (215, 90, 85, 60, 70, 110, 75, 110)):
            self.history_table.heading(key, text=label)
            self.history_table.column(key, width=width, minwidth=50)
        scrollbar = ttk.Scrollbar(history_frame, orient='vertical', command=self.history_table.yview)
        self.history_table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.history_table.pack(side='left', fill='both', expand=True)
        ttk.Label(frame, text='Historia w pamięci: reset zachowuje wpisy, zamknięcie aplikacji je usuwa. Zapis do pliku będzie w M5.').pack(anchor='w')
        self.bus.subscribe(self.on_observation)
        self.reset()
        root.after(50,self.tick)

    def reset(self):
        self.clock.reset()
        self.position.reset()
        self.corridor = load_corridor(DATA / (self.dataset.get()+'.json'))
        self.session_id = self.observations.start_session(self.corridor)
        self.signal_choices = {f'{signal.id} — {signal.name}': signal.id for signal in self.corridor.signals}
        self.signal_box.configure(values=list(self.signal_choices))
        self.selected_signal.set(next(iter(self.signal_choices)))
        self.session_status.set(f'Sesja {self.session_id[:8]} · {self.corridor.id} · reset rozpoczyna nową sesję')
        self.observation_status.set('NOW rejestruje wybrany rodzaj obserwacji. Dokładność reakcji operatora jest nieznana.')
        self.simulator = SignalSimulator(SimulationSettings(jitter_seconds=2 if self.jitter.get() else 0, extension_probability=.1 if self.jitter.get() else 0, extension_seconds=8 if self.jitter.get() else 0))
        self.available = self.corridor.speed_limit_mps is not None and all(s.road_position_m is not None for s in self.corridor.signals)
        self.start_button.configure(state='normal' if self.available else 'disabled')
        self.warning.set('DANE SYNTETYCZNE / PLACEHOLDER — odległości, limit i fazy nie opisują rzeczywistej sygnalizacji w Warszawie.' if self.available else 'INWENTARYZACJA NIEZWERYFIKOWANA — parametry są nieznane (null). Symulacja pozycji wyłączona do czasu zebrania danych.')
        self.render()

    def toggle(self):
        if self.available:
            self.sync_position(self.clock.read())
            self.clock.set_running(not self.clock.running)

    def change_rate(self, _event=None):
        self.clock.set_rate(float(self.rate.get()))
        self.sync_position(self.clock.read())

    def sync_position(self, reading):
        if self.available:
            seconds = reading.simulation_seconds - self.position.sample().elapsed_seconds
            self.position.advance(max(0, seconds), self.speed.get()/3.6, self.corridor.speed_limit_mps)
            if self.position.sample().road_position_m >= self.corridor.signals[-1].road_position_m:
                self.clock.set_running(False)

    def observe(self, state):
        reading = self.clock.read()  # Capture at button handling, not at the previous UI tick.
        self.sync_position(reading)
        event_type = ObservationType.STATE_START if self.observation_type.get() == 'Początek fazy' else ObservationType.STATE_SEEN
        self.observations.observe_now(self.session_id, self.signal_choices[self.selected_signal.get()], state, event_type, reading)

    def on_observation(self, event):
        observation = event.observation
        stamp = observation.timestamp.isoformat(timespec='microseconds').replace('+00:00', 'Z')
        self.history_table.insert('', 'end', iid=observation.observation_id, values=(
            stamp, f'{observation.simulation_seconds:.3f}', observation.session_id[:8],
            observation.signal_id, observation.state.value, observation.event_type.value,
            observation.source, 'SPÓŹNIONE' if event.out_of_order else 'OK'))
        self.history_table.see(observation.observation_id)
        self.observation_status.set(f'Przyjęto {observation.signal_id} {observation.state.value} / {observation.event_type.value} · UTC {stamp} · symulacja {observation.simulation_seconds:.3f} s')

    def tick(self):
        self.sync_position(self.clock.read())
        self.render()
        self.root.after(50,self.tick)

    def render(self):
        sample = self.position.sample()
        self.status.set(f'Czas modelu: {sample.elapsed_seconds:.1f} s    Pozycja: {sample.road_position_m:.0f} m    Prędkość: {sample.speed_mps*3.6:.0f} km/h')
        self.table.delete(*self.table.get_children())
        self.canvas.delete('all')
        width = max(self.canvas.winfo_width(),800)
        colors={'GREEN':'#58df93','YELLOW':'#ffd86b','RED':'#ff6f73','UNKNOWN':'#9ca9b0'}
        self.canvas.create_line(35,65,width-35,65,fill='#638478',width=3)
        end = self.corridor.signals[-1].road_position_m
        for i,s in enumerate(self.corridor.signals):
            state = self.simulator.state_at(s,sample.elapsed_seconds)
            self.table.insert('', 'end',values=(s.id+' — '+s.name,s.road_position_m if s.road_position_m is not None else 'UNKNOWN',s.signal_type,state))
            x=35+(width-70)*(s.road_position_m/end if end is not None else (i+1)/5)
            self.canvas.create_oval(x-8,28,x+8,44,fill=colors[state],outline='')
            self.canvas.create_text(x,17,text=s.id,fill='white')
        if end is not None:
            x=35+(width-70)*min(sample.road_position_m/end,1)
            self.canvas.create_rectangle(x-9,57,x+9,73,fill='#79b9ff',outline='')


def main():
    root=tk.Tk()
    App(root)
    root.mainloop()
