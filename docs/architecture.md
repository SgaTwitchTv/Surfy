# GreenWave — architektura i plan

## Stan i decyzje

Repozytorium początkowo zawierało tylko README i nieśledzony `.gitignore`.
Pierwszy pionowy etap używa Python 3.11+ i Tkinter bez zewnętrznych zależności.
To decyzja robocza do konsultacji; rdzeń nie importuje UI i można go przenieść
do innego frontendu. Nazwa repozytorium Surfy pozostaje bez zmian.

**Aktualnie wykonane: M1–M4 (do P08), wraz z uzgodnionym ekranem mapy.**
Domyślne `python -m greenwave` otwiera lokalny widok przeglądarkowy z rdzeniem
Python. Tkinter jest dostępny przez `--lab` jako starszy panel P02. Brak zależności
pip dla widoku mapy. Kontrakty: [m2.md](m2.md) oraz [m3.md](m3.md).

## Kierunek interfejsu — konsultacja 2026-09-11

Tkinter jest tymczasowym panelem laboratoryjnym. Docelowy główny ekran ma
przypominać nawigację: mapa z aktualną pozycją i trasą, duży panel prędkości
u góry, zakres prędkości i krótka akcja oraz lista kolejnych świateł podobna
do listy przystanków. Użytkownik chce rozważyć lekko przezroczyste nakładki.
Wskazanie światła pozwala ręcznie zgłosić początek zielonego lub innej fazy.
Docelowy przepływ: obserwacja → aktualizacja predykcji → przeliczenie trajektorii.

Stan zaobserwowany, przewidywany i nieznany muszą być widocznie rozróżnione.
Lokalna obserwacja sygnalizacji zależnej od ruchu nie potwierdza automatycznie
stanów dalszych punktów. Widok diagnostyczny pozostaje osobnym narzędziem.

Przygotowano interaktywną makietę w rozmowie. Używa geometrii ulic OpenStreetMap,
ale pozycja pojazdu, limit, fazy i zmiana rekomendacji są demonstracyjne;
nie jest podłączona do solvera ani aplikacji Tkinter. To propozycja wyglądu
do konsultacji, nie zatwierdzony projekt końcowy.

Ekran z mapą stałego korytarza i symulowaną pozycją może wejść przed M10.
Pełny routing A–B nadal należy do M10. Dostawca map i technologia docelowego
frontendu pozostają do wyboru; użycie OSM w makiecie nie rozstrzyga tej decyzji.

## Podział odpowiedzialności

- `greenwave/models.py`: niemutowalne SignalModel i Corridor, walidacja i odczyt JSON.
- `greenwave/simulation.py`: syntetyczny stan sygnalizacji; źródło prawdy eksperymentu.
- `greenwave/positioning.py`: PositionProvider i SimulationPositionProvider.
- `greenwave/clocks.py`: SimulationClock, niezależny czas UTC i czas symulacji.
- `greenwave/events.py`: niemutowalne obserwacje i synchroniczny EventBus.
- `greenwave/observations.py`: przyjmowanie eventów, sesje, deduplikacja i historia.
- `greenwave/prediction.py`: zielone okna, resynchronizacja i niepewność.
- `greenwave/solver.py`: solver jednego punktu i stabilizacja rekomendacji.
- `greenwave/vehicle.py`: dynamika symulowanego pojazdu i reakcja na światła.
- `greenwave/application.py`: wspólny stan i przepływ eventów.
- `greenwave/server.py`, `greenwave/web/`: lokalny ekran mapy, obserwacje i debug.
- `greenwave/ui.py`: starszy panel Tkinter z P02.
- `data/corridors/`: osobne dane syntetyczne i niezweryfikowana inwentaryzacja Warszawy.
- `tests/`: testy logiki domenowej.
- Moduły M4–M6: `trajectory`, `telemetry`, `replay`; analiza i storage pochodne są dalszym zakresem.

SignalModel opisuje kierunkową linię zatrzymania, nie pojedynczą lampę.
Odległość jest w metrach, prędkość w m/s, fazy w sekundach względem epoki modelu.
Offset oznacza początek zielonego w cyklu: offset + n * cycle_seconds.
Przedziały są lewostronnie domknięte, prawostronnie otwarte.
Nieznane wartości są null; confidence to opcjonalna liczba 0–1.
W M1 nie wyliczamy confidence i nie pokazujemy sztucznych procentów.

## P02 — wykonany

`SignalObservation` zawiera observation_id, session_id, corridor_id, signal_id,
state (GREEN/YELLOW/RED), event_type (STATE_START/STATE_SEEN), timestamp UTC,
simulation_seconds, source i opcjonalną timestamp_uncertainty_seconds.
Pomiar ręczny ma źródło MANUAL oraz nieznaną niepewność czasową (null).
UI nie wnioskuje początku fazy z samego zaobserwowania koloru.

SimulationClock używa zegara monotonicznego do przesuwania symulacji i osobnego
zegara UTC do timestampów. Zmiana tempa rozlicza poprzedni odcinek czasu według
starego tempa; pauza nie zatrzymuje UTC. Kliknięcie pobiera świeży odczyt zegara,
nie timestamp ostatniego odświeżenia UI. Zmiana zegara systemowego nie cofa
symulacji. Timestamp UTC oznacza czas obsługi kliknięcia, nie gwarantowany
moment fizycznej zmiany lampy. Nie przeliczamy czasu symulacji na UTC.

ObservationService przyjmuje eventy niezależnie od Tkinter. Waliduje sesję,
korytarz i punkt, zapisuje niemutowalny event, następnie publikuje SignalObserved.
Ten sam ID i payload są ignorowane przy ponownym dostarczeniu; konflikt payloadu
dla tego samego ID powoduje błąd. Osobne kliknięcia mają osobne ID nawet przy
identycznym czasie symulacji. Nie usuwamy ich heurystycznie.

Historia zachowuje kolejność przyjęcia. Spóźnienie jest ustalane względem czasu
symulacji ostatniej obserwacji **tego samego punktu i sesji**. Spóźniony event
pozostaje w historii i jest publikowany z flagą out_of_order. Widok chronological
sortuje po czasie symulacji, stabilnie dla remisów. Przy nieruchomym zegarze
symulacji zachowana jest kolejność dostarczenia; UTC pozostaje surowym pomiarem.

Reset/zmiana korytarza/zakłóceń tworzy nową sesję; poprzednia historia pozostaje.
Opóźnione eventy istniejących sesji mogą być przyjęte, ale nie mieszają porządku
nowej sesji. Historia jest tylko w pamięci; trwały zapis należy do M5.
EventBus działa synchronicznie w wątku aplikacji. Przyszłe źródła asynchroniczne
będą przekazywać eventy do tego wątku. P02 nie zmienia modelu faz ani nie
implementuje jeszcze PredictionEngine.

## Kontrakty predykcji i przyszłego solvera

`GreenWindow`: signal_id, start/end, confidence, source, model_version.
`Recommendation`: target/range, action, candidate trajectory, cost breakdown,
confidence, valid_until i uzasadnienie braku rozwiązania.

SignalModel przechowuje wiedzę. PredictionEngine konsumuje obserwacje i zwraca
zielone okna z niepewnością. TrajectorySolver konsumuje okna, lokalizację,
ograniczenia dynamiki i wagi celu. Solver nie ma dostępu do przyszłej prawdy
symulatora. ReplayPositionProvider i ExternalGPSPositionProvider zaimplementują
PositionProvider dopiero w odpowiednich etapach.

Obserwacje są typowanymi eventami obsługiwanymi przez warstwę aplikacji. UI
przekazuje je przez ObservationService. Zmiany pozycji, resynchronizacja i
rekomendacje otrzymają własne eventy w kolejnych etapach.

## Ryzyka i niewiadome

- Brief nie dostarcza potwierdzonych faz, geometrii, limitów ani współrzędnych.
  Nazwy skrzyżowań są inwentaryzacją z briefu, nie wynikiem weryfikacji terenowej.
- Koordynacja i sposób akomodacji wymagają pomiarów. GREEN NOW aktualizuje lokalny
  model; propagacja do innych punktów wymaga jawnych, potwierdzonych relacji.
- Confidence wymaga kalibracji na danych. Nie utożsamiamy typu światła z pewnością.
- Początek zielonego, reakcja operatora i przekroczenie linii to różne zdarzenia.
- Kolejki pojazdów mogą uniemożliwiać przejazd mimo zielonego; sam model faz nie
  stanowi gwarancji przejezdności. Pierwszy eksperyment terenowy zbiera dane.
- Trzeba ustalić minimalną prędkość jazdy, próg pełnego zatrzymania, horyzont,
  dopuszczalne opóźnienie i wagi. M4 ma jawne ustawienia tych parametrów w data/trajectory.json.
- Solver z dyskretyzacją nie może deklarować dowodu globalnej optymalności.
- M1 to sonda o zadanej prędkości: może przekroczyć czerwone. Nie jest symulatorem
  bezpiecznego kierowcy ani źródłem zaleceń drogowych.

## Pierwsze cztery milestones

1. **M1 — wykonany:** modele i walidacja, dwie oddzielne konfiguracje S1–S5,
   desktopowy symulator faz i pozycji, pauza/reset, tempo, deterministyczny jitter
   i wydłużenie zielonego. Testy granic cyklu, offsetów, UNKNOWN i ograniczenia
   prędkości sondy. Parametry faz edytuje się w JSON.
2. **M2 — wykonany:** eventy obserwacji GREEN/YELLOW/RED NOW, precyzyjny czas UTC, lokalna
   resynchronizacja, PredictionEngine, jawne relacje między punktami, debug okien.
   Testy lokalności aktualizacji, niepewności i braku deterministycznej prognozy
   dla nieznanej sygnalizacji.
3. **M3 — wykonany:** solver pojedynczego punktu, osiągalne przedziały prędkości, limit,
   aktualna prędkość i dynamika, przypadki niemożliwe, margines od granic okna.
   UI z całkowitą prędkością docelową i stabilizacją nieukrywającą nieważnej rady.
4. **M4 — wykonany (P07/P08):** przeszukiwanie kombinacji okien wielu punktów (beam search),
   konfigurowalny koszt zatrzymań, hamowania, zmian przyspieszenia, czasu i ryzyka.
   Raport składników kosztu; test, w którym wybór najlepszego okna S2 pogarsza S3,
   porównanie z baseline, przypadek bez rozwiązania bez zatrzymań.

M5 zapisuje niezmienne surowe logi z run_id i metadanymi konfiguracji. M6 dodaje
deterministyczny replay z seek i odtwarzaniem ostatniej próbki stanu z logu.
Analiza prawdziwych przejazdów oraz zalecenia live pozostają dalszymi etapami.

M4: `trajectory.py` łączy profile `solver.py` w ograniczonym beam search;
`application.py` wykonuje pierwsze polecenie i przelicza cały plan po obserwacji.
Konfiguracja celu jest w `data/trajectory.json`, kontrakty i ograniczenia w `m4.md`.

M5/L09: `telemetry.py` zapisuje append-only `raw.csv`, niezmienne `metadata.json`
i manifest `complete.json` z hashami. `application.py` emituje próbki, obserwacje,
rekomendacje, przekroczenia linii, incydenty i zakończenie; `server.py` udostępnia
listę nagrań oraz lokalny eksport ZIP. Brak manifestu oznacza zapis niedokończony.

M6: `replay.py` czyta wyłącznie zakończone logi, rekonstruuje stan przez seek i
udostępnia niezależny zegar odtwarzania przez lokalne API.

M7/L10: `analysis.py` sprawdza hash i kolejność raw CSV, oblicza metryki przejazdu
oraz delty baseline/GreenWave. Raport jest pochodny i read-only; nie nadpisuje
surowych danych ani nie zmienia modelu.
