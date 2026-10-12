# GreenWave — audyt szkolnego rozszerzenia (etap 1)

Data: 2026-10-12. Zakres tego etapu: audyt, sprawdzenie istniejącego worktree,
regresja bazy, dokumentacja. W tym etapie nie implementowano kont, migracji ani UI.
Status: **Zweryfikowany — audyt wykonany; akceptacja użytkownika oczekuje**.
Pozostałe etapy: **Do zrobienia**, niezależnie od wcześniejszego prototypu.

## 1. Git, instrukcje i ochrona danych

- Repozytorium główne: `C:/Users/konra/source/repos/SgaTwitchTv/Surfy`.
- Worktree użyty ponownie: `C:/Users/konra/.codex/worktrees/school-app/Surfy`.
- Gałąź: `codex/school-app`.
- Dokładna baza: `7ece85993bf860e0bdec0ecb43b65532242166eb`.
- `git merge-base --is-ancestor 7ece859 codex/vision-camera`: exit 0.
  `codex/vision-camera` wskazuje właśnie bazę. Nie ma rozbieżności bazy.
- `main`: `28cd1cc98ef809aae29daac206118c4ff112e4bb`, czysty przy rozpoczęciu;
  nie został zmieniony. Obie gałęzie referencyjne pozostają nietknięte.
- Istnieją również worktree: `.worktrees/ui-desktop` (56a83d3),
  `.worktrees/ui-mobile` (010dec8), `.worktrees/vision-association` (010dec8),
  `.worktrees/vision-camera` (7ece859). Nie resetowano ani nie edytowano ich.
- Przed tym etapem szkolny worktree miał HEAD
  `6a33be246d5239f34a888a61787169aaaf811034` i trzy wcześniejsze commity:
  `faa8ca9` (stary audyt), `f0aff93` (backend), `6a33be2` (UI).
  To wcześniejszy, niezaakceptowany prototyp, a nie ukończone etapy nowego procesu.
- Zachowano wcześniejsze zmiany: `greenwave/school.py`, `greenwave/school_store.py`,
  `greenwave/web/school.js`, `tests/test_school_http.py`; nieśledzone
  `.coveragerc`, `requirements-school-dev.txt`. Nie wchodzą do commita etapu 1.
- Sprawdzono AGENTS.md w repozytorium i na ścieżkach nadrzędnych obu checkoutów.
  Znaleziony `C:/Users/konra/.codex/AGENTS.md` ma 0 bajtów; został odczytany.
  Brak repozytoryjnego AGENTS.md. Instrukcje ReactLY dotyczą jego repozytorium,
  nie narzucają architektury GreenWave.
- Nie czytano zawartości prywatnego `data/runs/`, nie kopiowano ani nie
  modyfikowano nagrań. `git ls-tree -r --name-only 7ece859 data/runs` zwrócił
  pusty wynik (sprawdzenie indeksu Git, nie katalogu nagrań).
- Testy bazy wykonano z `git archive` dokładnego commita w osobnym, ignorowanym
  katalogu `artifacts/school-audit-20261012/base`. Testy zapisują wyłącznie dane
  syntetyczne w katalogach tymczasowych lub w tym eksporcie. Nie użyto
  symlinków ani kopii prywatnych danych.

## 2. Przeczytane źródła i rozbieżności dokumentacji

Odczytano README, `docs/architecture.md`, dokumenty M8 mapping plan,
implementation i field test, `docs/phone-gps.md`, `docs/observation-history.md`,
plan UI/CV oraz dokumenty vision probe i kroków 5, 6, 7–8. Zweryfikowano je
przez kod: `application`, `server`, `positioning`, `telemetry`, `analysis`,
`gps_replay`, `route_geometry`, `map_matching`, `route_events`, `live_navigation`,
`observation_history`, `observation_review`, `vision_capture`, `vision_workbench`,
`vision_tracking`, kontrakty CV oraz adaptery webowe. Przejrzano także wcześniejszy
prototyp `school.py`, `school_store.py`, `school.js`, testy i ich lokalny diff.

README opisuje historię w pamięci, lecz osobny indeks M8 jest już w SQLite.
`architecture.md` nadal podaje M1–M4, plan UI twierdzi „nie wdrożono”, dokument
vision step 5 opisuje stan sprzed trackera, a phone-gps mówi o braku mapowania.
To historyczne opisy. Nie traktujemy ich jako aktualnego dowodu funkcjonalności.
Kod i regresja potwierdzają M8, perspektywiczną nawigację i diagnostykę CV;
nie potwierdzają jakości drogowej ani zweryfikowanych faz rzeczywistych świateł.

## 3. Architektura i przepływ danych

Python: biblioteka standardowa, HTTPServer/BaseHTTPRequestHandler, SQLite,
niemutowalne DTO i synchroniczny EventBus. `GreenWaveApplication` zarządza
stanem symulacji, zegarem, predykcją, solverem, GPS, trasą i loggerem.
Jeden wątek serwera serializuje akcje; analiza mapowania działa w zadaniach,
a capture CV w osobnym procesie z ograniczonymi kolejkami.

Przepływ: Android Fused Location → POST /api/position → ExternalPositionProvider
(walidacja, deduplikacja, wiek, źródło prędkości, dryf postoju) → matcher wybranej
wersji trasy → następna linia / crossing / diagnostyka → snapshot → fetch → UI.
Logger zapisuje surowe zdarzenia. Replay i analiza weryfikują ukończenie, hashe
oraz sekwencję. Obserwacja STATE_SEEN nie dowodzi początku fazy STATE_START.
Symulacja ma osobną prawdę testową; predykcja nie podgląda przyszłości symulatora.

Live solver wymaga jednocześnie: świeżego dopuszczonego GPS, MATCHED/FORWARD,
FIELD_CHECKED geometrii, linii i limitu, zweryfikowanego sygnału/faz oraz zgodnego
zegara predykcji (`live_navigation.evaluate_live_navigation`,
`application._live_recommendation_eligibility`). CV nie zasila tego mostu.
Konta i akceptacja kandydata CV nie mogą zastąpić tych warunków.

Frontend bazy: lokalny HTML/CSS/vanilla JS, canvas mapy, SVG prędkościomierza,
fetch z odświeżaniem; widoki nawigacji i Laboratorium. Brak bundlera i backendowego
frameworka. Tkinter to historyczny panel P02. Android: Java, Gradle 8.13,
usługa pierwszoplanowa Fused Location i ograniczona kolejka ponowień.

### Uruchomienie i zależności

Baza: `python -m greenwave --no-browser --port 8766`; domyślnie localhost.
`--lab` uruchamia Tkinter, `--host` zmienia bind, `--vision-python` wybiera worker.
Ta komenda na zwykłym checkout odczytuje jego dane; audyt uruchamiał serwer tylko
w izolowanym eksporcie z jawnym `runs_root` dla danych syntetycznych.
Python deklarowany >=3.11; sprawdzony tutaj 3.14.4. Node 24.18.0 dla testów.
Java Temurin 17.0.19 i lokalny Android SDK umożliwiły build offline.

Rdzeń nie wymaga pip. Capture wymaga OpenCV, inferencja dodatkowo Ultralytics,
PyTorch i lokalnych wag. Piny są w `requirements-vision.txt`; nie instalowano ich
w etapie 1. Globalny Python ma cv2, nie ma ultralytics ani coverage. Coverage
7.13.1 jest dostępne we wcześniej utworzonym `.venv-school`. Playwright jest
w bundlowanym runtime Codex, Edge jest dostępny. Docker CLI nie jest dostępne.
Nie sprawdzono fizycznego telefonu/kamery ani wszystkich pinów CV.

### Storage

- `data/corridors`, `prediction`, `routes`, `maps`, solver/trajectory JSON:
  śledzone konfiguracje i mapy, z jawnie oddzieloną weryfikacją.
- `data/runs/<id>`: append-only `raw.csv`, metadata, manifest complete.json
  z SHA-256; zakończone logi nie są otwierane do zapisu (`telemetry.RunLogger`).
- `data/derived`: pochodne raporty i `observation-history.sqlite3`.
  Indeks obserwacji ma klucz `(run_id, sequence)`, filtr route_id, transakcyjny
  import i zachowuje wersję geometrii. Brak właściciela użytkownika w bazie M8.
- CV: capture manifest, frames/vision/events JSONL i oryginalne media;
  `reviews.sqlite3` ma events, cursors, decisions i assignments.
  Decyzja przeglądu jest osobnym wpisem; tekst reviewer nie jest kontem.
- Prototyp szkolny: `runtime/school/school.sqlite3`, konta, sesje, przejazdy,
  obserwacje, corrections, account_audit; osobne katalogi użytkowników.
  Używa PRAGMA user_version. Wciąż wymaga przeglądu migracji i wszystkich
  ścieżek storage: odziedziczony LocalServer tworzy CV pod DATA/derived,
  co nie zapewnia izolacji tego obszaru przez samo przekazanie root portalu.

### Parowanie i zabezpieczenia API bazy

Sześciocyfrowy kod serwera wydaje wspólny losowy token lokalny i session_id.
Pięć błędów blokuje próby przez 30 s. Android zachowuje token, wysyła próbki,
ponawia transport i odświeża sesję po HTTP 409. To uwierzytelnienie urządzenia
w jednym lokalnym procesie, bez kont, ról i właścicieli nagrań.

POST: token, session_id, walidacja hosta/origin, JSON object, body <=8192 B,
timeout i kontrola domenowa. GET historii i CV jest częściowo chroniony tokenem,
media mają cookie HttpOnly/SameSite i ograniczone Range. /api/state, /api/runs,
/api/analysis/* i stany replay w bazie są dostępne bez logowania. Token jest
wstrzykiwany w HTML lokalnego UI. Przy bind sieciowym Host/Origin w bazie są
sprawdzane głównie według portu. Są nagłówki CSP, no-store, nosniff, lecz CSP
pozwala unsafe-inline. Lokalnego serwera nie można po prostu wystawić publicznie.

Prototyp szkolny ma scrypt, cookie sesji, CSRF, throttling, role i filtr owner_id.
Reset wymaga ręcznego wydania linku przez CLI (15 min, jednorazowy hash tokenu);
nie ma automatycznego dostarczenia maila. Nie zatwierdzamy teraz tego kontraktu.
Trzeba także przejrzeć odziedziczone endpointy, sesje urządzeń i reset/wylogowanie.

## 4. Macierz 16 wymagań

Stan w kolumnie „Baza” dotyczy dokładnie 7ece859. „Prototyp” opisuje zastany kod,
nie akceptację kolejnych etapów. Istnienie pliku nie oznacza pozytywnego odbioru.

| # | Wymaganie | Baza | Zastany prototyp | Dowód w kodzie | Brakująca praca | Odbiór |
|---|---|---|---|---|---|---|
|1|Problem domenowy|istnieje|częściowo|README; application.mapping_snapshot; live_navigation.evaluate_live_navigation|Opis dla użytkownika i raport, jawne ograniczenia|UI + raport; test braku rady przy nieznanych danych|
|2|Konta, login, reset|brak|częściowo|server.pair nie jest loginem; school_store.register/login/reset_password|Uzgodnić i odebrać kontrakt kont i kanał resetu|Rejestracja/login/logout; token jednorazowy, expiry, revocation, próby błędne|
|3|Trzy role|brak|częściowo|school_store.ROLES/change_user; brak ról w server|Jawna macierz akcji i jej pełny przegląd|Test HTTP każdej roli dla odczytów i mutacji|
|4|Ochrona i własność|częściowo|częściowo|server.do_GET public state/runs/analysis; school_store.scope, trips.owner_id|Objąć wszystkie zasoby, eksport, media, job/replay i urządzenia|Anonim, cudze ID, rola zmieniona, konto zablokowane, token telefonu|
|5|Dwie filtrowalne tabele kierowcy|częściowo|częściowo|app.js historia i run-list; school.js trip-filter/observation-filter; SchoolStore.trips/observations|Własność, użyteczne filtry, limity i stany puste/błędy|Dwie tabele na koncie kierowcy; filtry API i UI nie ujawniają cudzych danych|
|6|Estetyka UI|niezweryfikowane|niezweryfikowane|driver-ui.js/style.css; school.html/css|Projekt w kierunku ReactLY, zatwierdzenie wyglądu|Rzeczywiste zrzuty i odbiór użytkownika; testy nie rozstrzygają estetyki|
|7|Responsywność|istnieje w sprawdzonym zakresie|niezweryfikowane w etapie 1|check_driver_ui.cjs, CSS, check_web.cjs|Odbiór nowych formularzy/tabel, portrait/landscape, czytelność podczas nawigacji|Desktop 1360; 390/320 px; brak overflow; później nowy UI i fizyczny telefon|
|8|Walidacja formularzy|częściowo|częściowo|server.do_POST; positioning.update; route/model validators; school.js form; SchoolStore.text/email/password|Pełna lista formularzy; walidacja klient+serwer, granice i nieznane pola|Błędne payloady, puste/długie wartości, NaN, enums; bez pomijania walidacji backendu|
|9|Zapis/modyfikacja rekordów|częściowo|częściowo|telemetry.RunLogger; vision_workbench.review; school_store.update_trip/correct|Trwałe rekordy należące do kont; historia korekt i spójność indeks/raw|Zapis, restart, odczyt, korekta actor/time/reason; hash oryginału niezmienny|
|10|AJAX/fetch|istnieje|częściowo|app.js request/action; driver-ui.js loadVision; school.js api|Spójna obsługa błędów i wygasłych sesji nowych widoków|E2E bez reload; nieudany fetch, timeout, utrata łączności|
|11|Praktyki/architektura|częściowo|częściowo|DTO/EventBus; oddzielne solver/replay; SQLite transakcje; school_store.migrate|Migracje z upgrade/recovery, konfiguracja, izolacja runtime i bezpieczny deployment|Testy migracji, błędów I/O, restartu, utraty sesji; przegląd kodu|
|12|Historia Git|istnieje|częściowo|git log/worktree; trzy zastane commity|Małe commity kolejnych zaakceptowanych etapów|Historia na school-app, main/CV nietknięte; staging konkretnych plików|
|13|Prompty i pomoc AI|brak|częściowo|stare docs/ai-usage.md; nowy docs/school-app/ai-usage.md|Kontynuować dokładne prompty, działania, wyniki i korekty|Dokument spójny z historią, bez fałszywych twierdzeń o odbiorze|
|14|Docker na innym komputerze / hosting|brak|brak|Brak Dockerfile/compose i dowodu deploymentu|Demo syntetyczne, obraz, wolumen, brak prywatnych danych; drugi host|Build/start/health/login/zapis/restart na drugim komputerze; Docker CLI tutaj brak|
|15|Unit/integration/automatic, coverage >=70%|częściowo|częściowo|226 testów bazy, skrypty browser; zastane tests/test_school_* i .coveragerc|Rozszerzyć jawny zakres o używany rdzeń, raport per moduł, CI/E2E|Coverage rzeczywiste całego uzgodnionego zakresu; osobno JS, Android, scenariusze E2E|
|16|Raport, screenshoty, źródła, instrukcja|częściowo|częściowo|README/docs/test scripts; brak końcowego raportu szkolnego|Idea/dataflow/role/architektura, główne widoki i komplet instrukcji|Reprodukcja przez inną osobę, zrzuty działającej aplikacji i finalna akceptacja|

## 5. Testy etapu 1

Wszystkie poniższe wyniki dotyczą izolowanego eksportu **dokładnej bazy**,
nie późniejszych zmian szkolnych. Logi i obrazy lokalne:
`artifacts/school-audit-20261012/`. Nie są prywatnymi nagraniami.

Przygotowanie (cwd szkolnego worktree):

```powershell
git archive --format=zip --output=artifacts/school-audit-20261012/base.zip 7ece859
Expand-Archive -LiteralPath artifacts/school-audit-20261012/base.zip -DestinationPath artifacts/school-audit-20261012/base
cd artifacts/school-audit-20261012/base
```

| Polecenie | Wynik | Pominięcia / ograniczenia |
|---|---|---|
|`python -m unittest discover -s tests -v`|226 testów, OK, 22.357 s|0 pominięć; testy HTTP/Tkinter działały; synthetic/mocks nie dowodzą jakości drogowej|
|`node --check greenwave/web/app.js` i analogicznie driver-ui.js, capture-ui.js, vision-workbench-ui.js|exit 0 każdy|Sprawdzenie składni, nie odbiór funkcjonalny|
|`node tests/mobile_flow.cjs`|PASS|Automatyczny scenariusz browser GPS z mockami; nie fizyczny Android|
|`node --test tests/driver_ui.cjs tests/vision_workbench_ui.cjs`|7 testów PASS; 0 failures/skips|Logika JS; nie pełny rendering|
|`node scripts/check_web.cjs` na izolowanym LocalServer|PASS, errors=[], external=[]; width/scroll=390/390|Playwright + Edge; screenshoty desktop/dark/mobile|
|`node scripts/check_driver_ui.cjs` na tym serwerze|PASS, errors=[], external=[]|Desktop, 390/320, scenariusze CV, live/replay bez rady, utrata sieci; syntetyczne dane|
|`python -m scripts.check_capture`|PASS: 40 frames, artifact hashes, bounded preview, replay, seek, stop, corrupt-source rejection|Generowany MJPEG w TemporaryDirectory; bez YOLO i kamery|
|Android: `./gradlew.bat testDebugUnitTest assembleDebug --no-daemon --offline` z ANDROID_HOME|BUILD SUCCESSFUL, 37 tasks executed; 4 unit tests, 0 errors/failures/skips|SDK XML warning v4/v3; Gradle deprecations. Nie są błędami kodu ani testem telefonu|

Dokładny harness przeglądarkowy był tymczasowym plikiem
`base/audit-browser-temp.py`: tworzony TemporaryDirectory/synthetic-runs,
`LocalServer(0, application=GreenWaveApplication(runs_root=...))`, wątek
serve_forever, oba skrypty Node uruchamiane kolejno, shutdown/join/server_close.
Odtworzenie (z tego samego eksportu):

```powershell
$env:GW_PLAYWRIGHT_MODULE='C:/Users/konra/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
python audit-browser-temp.py
```

Do trwałej reprodukcji wystarczy uruchomić bazowy serwer **w świeżym eksporcie**,
ustawić `GW_TEST_URL` na jego port i wykonać oba istniejące skrypty Node.
Android SDK: `C:/Users/konra/AppData/Local/Android/Sdk`; jego komendy wykonano
z `base/android/GreenWaveSensor`. Raporty JUnit XML potwierdzają 2 testy
TelemetryQueueTest i 2 TelemetrySampleClockTest.

Nie uruchomiono inferencji YOLO (`scripts.check_tracking`, `check_tracking.cjs`,
`check_workbench.cjs`): wymagają pakietów ML, lokalnych wag i właściwych fixture'ów.
Brak globalnego ultralytics; nie kopiowano lokalnych filmów/wag i nie pobierano
ich na potrzeby audytu. Unit testy trackera/workbench przechodzą, ale to inny dowód.
Nie wykonano ADB/telefonu/kamery, jazdy terenowej ani Dockera/drugiego hosta.
Nie wykryto błędów kodu w uruchomionych testach bazy. Braki środowiska i pominięte
sprawdzenia są powyżej oddzielone od błędów kodu.

## 6. Proponowany zakres coverage

Zakres do odbioru szkolnego: **cały backend portalu** (obecne school.py i
school_store.py oraz każdy nowy moduł kont, sesji, polityk, storage, migracji,
resetu i API) **plus używany rdzeń GreenWave**: application/server, analysis,
clocks/events/models/observations/prediction/simulation/vehicle/solver/trajectory,
positioning, telemetry/replay/gps_replay, route_geometry/map_matching/route_events,
live_navigation/mapping_analysis, observation_history/review/completeness,
vision_contracts/tracking/validation/workbench/capture. Każdy nowy moduł biznesowy
wchodzi automatycznie do zakresu. Nie wyłączamy trudnych gałęzi API, security,
I/O czy recovery tylko dlatego, że obniżają wynik.

Pomiar: coverage.py z branch=True, source=greenwave; raport linii i gałęzi,
łączny i per moduł, JSON/HTML. Próg >=70% dla uzgodnionego zakresu backendu,
z osobnym wynikiem warstwy szkolnej i używanego rdzenia. Nie wolno zastępować
raportu liczbą testów ani wcześniejszym wąskim wynikiem prototypu (83%).
Frontendowe guidance/perspective/filtry i ważne reguły widoków mierzyć osobno
przez Node/V8 coverage; Playwright zapewnia E2E, nie udaje coverage Pythona.
Android testować osobno JUnit/build, a coverage Java przedstawić oddzielnie,
jeśli będzie częścią kryterium końcowego. Nie dodawać procentów między językami.

Proponowane wyłączenia, każde jawne:

- `ui.py`: historyczny Tkinter P02, portal szkolny go nie wykorzystuje.
- `__main__.py`: trzywierszowy entrypoint; uruchomienie sprawdza smoke test.
  CLI we właściwych modułach server/school pozostaje w zakresie.
- `vision_probe.py`: osobne narzędzie benchmarku, poza przepływem portalu.
- `vision_detector.py` i `vision_capture_worker.py`: adapter inferencji/decoder
  i proces wymagający pakietów/wag/hardware; oddzielne testy worker smoke i
  walidacja offline. To ograniczenie coverage, nie deklaracja bezpieczeństwa CV.
  Jeśli rozszerzenie przeniesie tam autoryzację lub własność, ta logika musi
  wrócić do mierzonego backendu.
- `vision_demos.py`: same syntetyczne przykłady DTO, bez produkcyjnej polityki.
- Narzędzia OSM, jednorazowe scripts, test fixtures i zewnętrzne biblioteki:
  nie stanowią kodu aplikacji; zachować ich osobne testy gdy zmieniane.
- HTML/CSS/Android nie należą do mianownika coverage.py; mają osobne sposoby
  weryfikacji opisane wyżej. Nowej logiki JS nie wyłączamy z jej pomiaru.

Rzeczywisty pomiar bazowy i jego dokładne polecenia: patrz dopisek poniżej.
Nie jest to końcowy wynik aplikacji szkolnej, której kolejne etapy oczekują.

## 7. Ryzyka i następne etapy

1. Zachować zastaną pracę, lecz przejrzeć ją w nowym procesie — nie zakładać
   automatycznej akceptacji. Istniejąca gałąź ma wymagany przodek, nie jest już
   czystym checkoutem bazy. Nie resetować jej bez osobnej instrukcji.
2. Uzgodnić granice Laboratorium, widoki analityka/admina oraz pełną własność
   GPS/CV/replay/job/export; dotychczas lokalny proces ma stan współdzielony.
3. Migracje i indeksy muszą rozdzielać nowe dane kont od nieprzypisanych
   historycznych nagrań; bez dopisywania właścicieli do raw.csv.
4. Reset musi mieć prawdziwy, bezpieczny kanał dostarczenia; ręczny CLI
   prototypu wymaga decyzji przy etapie kont. Sesje urządzeń są odrębne.
5. Dopisać recovery przy restarcie, obsługę awarii zapisu, spójność SQLite/raw
   i audyt kto/kiedy/powód. Przejrzeć izolację CV odziedziczoną z LocalServer.
6. UI: kierunek ReactLY (ciemny, limonka, mocna typografia), z czytelną
   nawigacją i bez upodabniania niepewnego CV do zweryfikowanych faz.
7. Docker CLI/engine i drugi host są zależnością wdrożenia; demo nie może
   kopiować prywatnych GPS/filmów ani wymagać ADB/YOLO. Licencja wag CV
   w dokumentach repozytorium pozostaje nierozstrzygnięta; nie redystrybuować.
8. Coverage liczyć szerzej niż wcześniejsze dwa szkolne moduły; unit/E2E
   nie zastępują odbioru telefonu, drogi, danych faz i fizycznej kamery.

Kolejność dalszej pracy zachowuje ustalenie użytkownika: kontrola aplikacji →
baza/migracje → konta/sesje → uprawnienia/API → przejazdy/obserwacje → nowy UI →
widoki analityka/admina → nawigacja/responsywność → pełne testy/coverage →
Docker/drugi host → raport i finalny odbiór. Po każdym etapie: status,
commit tylko jeśli zlecony, dowody, blokady i oczekiwanie na potwierdzenie.
Rejestr: [stages.md](stages.md). Prompty i działania: [ai-usage.md](ai-usage.md).

### Pomiar bazowy wykonany w etapie 1

Coverage.py 7.13.1, branch=True, source=greenwave z sześcioma wyłączeniami
modułów wymienionymi wyżej. Konfiguracja jest zachowana w
`artifacts/school-audit-20261012/coverage-audit.ini`; **nie** użyto zastanej
`.coveragerc`, która ogranicza pomiar do dwóch szkolnych plików.

Z cwd izolowanego eksportu wykonano dokładnie:

```powershell
& 'C:/Users/konra/.codex/worktrees/school-app/Surfy/.venv-school/Scripts/python.exe' -m coverage run --rcfile=../coverage-audit.ini -m unittest discover -s tests -q
& 'C:/Users/konra/.codex/worktrees/school-app/Surfy/.venv-school/Scripts/python.exe' -m coverage report --rcfile=../coverage-audit.ini
& 'C:/Users/konra/.codex/worktrees/school-app/Surfy/.venv-school/Scripts/python.exe' -m coverage json --rcfile=../coverage-audit.ini -o ../coverage-baseline.json
```

Wynik: 226 testów OK (38.900 s); **85.9985% łącznie linii+gałęzi**,
**89.6211% linii (3359/3748)**, **77.1242% gałęzi (1180/1530)**.
Raport tekstowy: `coverage-baseline.log`; maszynowy: `coverage-baseline.json`.
30 plików raportowanych, w tym pusty __init__.py (0 instrukcji, nie podbija wyniku).
Domyślna reguła coverage.py wyłącza także 3 linie deklaracji metody protokołu
PositionProvider.sample w positioning.py:43–45 (ciało `...`, interfejs,
bez wykonywalnej implementacji; konkretne providery pozostają w mianowniku).

Istotne wyniki per moduł (łączne linie+gałęzie, zaokrąglone): application 90%,
server 76%, positioning 91%, map_matching 88%, route_geometry 80%,
live_navigation 93%, telemetry 79%, observation_history 96%,
vision_workbench 84%, vision_capture 38%. Nadzorca capture jest objęty pomiarem
mimo niskiego wyniku. Osobny udany smoke dekodera nie był dołączany do coverage,
ponieważ używa innego procesu Pythona. Nie ukrywamy tej różnicy.

To wynik istniejącej bazy, bez późniejszych school.py/school_store.py.
Wymaganie końcowe szkolnej aplikacji **pozostaje częściowe / do zrobienia**:
po wdrożeniu uzgodnionych etapów należy powtórzyć pomiar pełnego zakresu
obejmującego nowy backend i przeprowadzić osobny pomiar istotnej logiki JS.

### Kontrola niezatwierdzonych plików

SHA-256 wcześniej zastanych sześciu plików pozostały identyczne przed i po
przygotowaniu dokumentacji (pełne hashe dostępne w historii narzędzi czatu).
Commit etapu obejmuje wyłącznie audit.md, ai-usage.md i stages.md w tym katalogu.

Konfiguracja do odtworzenia bazowego coverage (coverage-audit.ini):

```ini
[run]
branch = True
source = greenwave
omit =
    */greenwave/ui.py
    */greenwave/__main__.py
    */greenwave/vision_probe.py
    */greenwave/vision_detector.py
    */greenwave/vision_capture_worker.py
    */greenwave/vision_demos.py
[report]
show_missing = False
```
