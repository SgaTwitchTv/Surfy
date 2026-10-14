# Etap 9 — nawigacja, Android GPS, replay i diagnostyczne CV

Baza przyjęta przez użytkownika: **7927fc233f48a90ee238fc2ecacf1566b9a0a6fa**.
Worktree `C:\Users\konra\.codex\worktrees\school-app\Surfy`, gałąź `codex/school-app`.
Stan: **Przygotowany do odbioru** po implementacji i wykonanych sprawdzeniach. Wyniki końcowe poniżej.
Nie rozpoczęto etapu 10. Main i vision-camera nie są zmieniane.

## Macierz integracji oparta na kodzie

|Funkcja|Moduł bazowy → chroniony adapter|Endpoint pod `/school/api/v1`|Własność / storage|Odbiór|
|---|---|---|---|---|
|Lease, logger, recovery|school_records.recording + telemetry.RunLogger → school_navigation.engine.Drive|POST /navigation; GET /navigation/{id}; POST control|DB trip owner + parent browser session/credential, jeden SQL slot; owners/{uid}/trips/{tid}/runs/{rid}|17 testów nowej suite, wcześniejsze granice awarii i prawdziwe HTTP|
|M8 symulacja i solver|GreenWaveApplication, SimulationClock, PredictionEngine, DynamicVehicle|PATCH /navigation/{id}/simulation; PAUSE/RESUME|Oddzielny engine/clock/matcher; ten sam logger koordynatora|Deterministyczne zegary, brak przyszłego truth w planowaniu, E2E|
|GPS|ExternalPositionProvider, MapMatcher, evaluate_live_navigation|POST /device/position; GET /device/session|Odrębny bearer hash, owner/parent/boot/security_version i konkretna credential urządzenia|Syntetyczny nadajnik HTTP, jakości/freshness regresja M8; sprzęt niewykonany|
|Parowanie|school_data.SecurityRecords → school_navigation.devices|devices, pairing-challenges, device/pair|Challenge 6 cyfr/5min/single-use, trwałe limity HMAC, expiry <= parent absolute expiry|Barrier race, TTL, one-use, podmiana pól, revoke i re-pair|
|Mapy / trasa|route_geometry → school_navigation.maps|GET /maps/{allowlisted id}; config/versions|4 jawne bundled mapy; zamrożony DB snapshot i hash, kontrolowany shared/config/{version}/route.json|Containment, hash, testy geografii i publikacji; bez wymyślania linii drogowych|
|Replay GPS|GPSReplaySession → Contexts|trip/replay-options, POST trip/replays; GET/control/DELETE replay|OWN albo konkretny SHARE, session/credential/TTL; własny matcher i zegar|Regresja pinned share oraz isolation|
|Replay symulacji|ReplaySession → school_navigation.replay.SimulationReplay|Te same endpointy, mode=SIMULATION|Read-only raw.csv; bounded public state; rate 1/2/5/10|HTTP, seek/play/pause, provenance i E2E|
|CV capture / tracker|CaptureController, worker, VisionWorkbench → school_navigation.cv|capture POST/status/stop/frames/events/media/associations/reviews|Owner only, per-trip cv root; capture związany z tą samą navigation lease|Rzeczywisty wygenerowany klip + osobne syntetyczne detekcje/stub tracker; nie YOLO ani kamera|

## Konteksty i trwałość

Nie powstał drugi mechanizm rezerwacji. STARTING/RECORDING/FINALIZING w SQLite
pozostają źródłem prawdy; drugi start daje **409 ACTIVE_SESSION_BUSY** bez
identyfikacji właściciela. Pause zatrzymuje wyłącznie zegar symulacji, nie lease.
Drive ma własny GreenWaveApplication, SimulationClock i matcher. Konstruktor
zawsze dostaje jawny runs root; po inicjalizacji silnik używa dokładnie loggera
koordynatora. Ten sam format raw.csv/metadata.json/complete.json jest zachowany.

Serwerowy UTC jest integer epoch milliseconds; na granicy zegara/logowania
konwersja do UTC datetime i sekund modelu jest jawna. Zegar symulacji nie jest
zegarem epoki ani zegarem monotonicznym telefonu.

Symulacja używa bundlowanego `synthetic_s1_s5`. Nazwy ulic w zestawie są etykietami
syntetycznych sygnałów — nie dowodem faz na rzeczywistej drodze. Opcjonalny
school_route_snapshot pozostaje zamrożoną geometrią GPS/metadanymi przejazdu;
nie jest potajemnie zamieniany w fizykę tego bundlowanego demo. LIVE wybiera
konkretną opublikowaną wersję ROUTE, jej payload/hash i oddzielny niesyntetyczny
kontekst M8 bez syntetycznej pozycji.

Rewizje są jawnie rozdzielone: `revision` to trwała rewizja trip (FINISH z etapu6),
`control_revision` to pamięciowa rewizja PAUSE/RESUME i parametrów symulacji.
W polu request `expected_revision` dla control PAUSE/RESUME/PATCH simulation
podaje się control_revision; dla FINISH — revision. Frontend pobiera aktualne
wartości, a nie wymyśla ich. Parametry: rate 1/2/5/10, speed_kmh 0–50,
follow_recommendation boolean. LIVE odmawia symulacyjnego sterowania 403.

Po zwykłym FINISH identyczny klucz nadal zwraca ten sam zakończony rezultat;
watchdog nie usuwa go przed retry. GET zamkniętej navigation daje 409,
po revokacji/usunięciu kontekstu 404. Ukończony DTO nie utrzymuje rady live.

Logout/reset/password/block/role i revoke/expiry urządzenia odcinają credentials,
ingest i zależny capture, a rozpoczęty raw finalizuje ograniczony systemowy
koordinator. Re-pair tego samego device ID zmienia credential: stary context
nie przejmuje nowego tokenu. Nowy boot unieważnia urządzenia/challenges, recovery
rozstrzyga intencje i nie wznawia jazdy ani świeżości GPS.

Awaria loggera przy ingest daje 503 RECORDING_WRITE_FAILED zamiast accepted=true.
Logger jest zamknięty bez fabrykowania manifestu; przy dostępnej DB trip staje
się INTERRUPTED. Cleanup poza transakcją ingest może zostać ponowiony przez
istniejący watchdog/recovery, gdy SQLite odzyska sprawność. Nie ma transakcji
obejmującej filesystem i DB; nie obiecujemy odzyskania każdego bajtu po awarii.

## Endpointy i polityka

Wszystkie browser mutations: aktualna sesja, dokładny Origin, CSRF i walidacja
JSON (brak unknown/duplicate fields, bool-as-number, NaN/Infinity). Odczyty
anonym 401, cudze private IDs 404; admin nie ma wyjątku.

|Endpoint|Pola / rezultat|Polityka|
|---|---|---|
|GET /navigation|Own active parent-session DTO lub null|Wyłącznie aktualna browser session; nie global state|
|POST /navigation|trip_id, device_id tylko LIVE; Idempotency-Key|Own PLANNED; LIVE real HTTPS + own parent-bound device|
|GET /navigation/{id}|stan, prędkość nullable, quality, mapping, signals, eligibility, response_at|Owner + dokładna parent session/credential|
|POST navigation/{id}/control|command PAUSE/RESUME/FINISH, expected_revision; FINISH stabilny Idempotency-Key|SIM pause/resume, oba tryby finish|
|PATCH navigation/{id}/simulation|expected_revision, rate?, speed_kmh?, follow_recommendation?|SIM only|
|GET devices|status?,limit,cursor|Owner; podpisana paginacja; DTO id,label,status,last_seen_at, bez hash/parent|
|PATCH /devices/{id}|label 1–80|Owner|
|DELETE /devices/{id}|reason 3–500|Owner, linked LIVE finalization|
|POST /pairing-challenges|label → code/id/expiry|Owner issuing session; demo HTTP 403|
|DELETE challenge/{id}|{}|Owner i issuing session|
|POST /device/pair|code,client_device_id,label → device_token/id/app_session_id|Code single-use, neutral 403, IP/code rate limits|
|GET /device/session|active,app_session_id,repair_required|TELEMETRY bearer tylko własnego parent/boot/version|
|POST /device/position|Ścisły payload Androida z kontraktu|Bearer do własnego aktywnego LIVE; 409 session changed, 403 repair required|
|GET /maps/{id}|warsaw/radom/chomiczowka/arkadia|Logged-in allowlist, bez dowolnego URL/path|
|GET /trips/{id}/replay-options|modes GPS/SIMULATION z rzeczywistych sealed artefacts|Owner lub aktywny konkretny share; COMPLETE/nonarchive|
|POST /trips/{id}/replays|mode GPS/SIMULATION|Jak wyżej, pinned authorization i read-only source|
|GET/POST control/DELETE /replays/{id}|PLAY/PAUSE/SEEK/RATE|Dokładna session/credential/OWN lub SHARE; zawsze bez live advice|
|GET /cv/sources|Operator source labels i detector_configured, bez paths|Active account; kamera tylko profil real|
|POST /trips/{id}/cv/captures|source_type,source_ref lub camera_index, dimensions/fps/detection/realtime|Owner active navigation + operator allowlist|
|GET capture / POST stop|safe status / {}|Owner; aktywny stop wymaga właściwego parent navigation|
|GET capture/frames/{n}|bounded JPEG, max1MiB|Owner, containment, każdy odczyt osobno|
|GET capture/events|limit,offset; safe events + ostatnie 10 review|Owner; bounded index/import lub sealed digest|
|GET capture/media/{n}|Range single, max1MiB zakresu|Owner, complete capture/hash, recheck co <=64KiB|
|POST associations / DELETE associations/{track}|track_id, route_version_id, stop_line_id,movement / {}|Owner active parent, exact route, fresh current track; nie FIELD_CHECKED|
|POST reviews|event_id,status,reason,expected_revision,client_operation_id|Owner; immutable evidence + append-only audited decision|

Tylko trzy jawne aliasy: POST /api/pair, POST /api/position, GET /api/state.
Ostatni zwraca minimum /device/session i wymaga device bearer; nigdy snapshot
LocalServer. Nie istnieje ogólny legacy bridge. Token telefonu nie czyta tables,
config, exports, CV ani administracji. Publiczny namespace kont działa jak etap4.

Replay-options rozwiązuje rzeczywisty problem dawnych syntetycznych GPS fixtures,
których trip.mode nie opisuje typu raw. UI nie zgaduje po mode. Rate10 jest
udostępniony tylko adapterowi simulation; GPS nadal wspiera 1/2/5.
LEGACY_MINIMAL_SYNTHETIC jest jawnie oznaczony, nie przepisany na pełne M8.
GPS replay korzysta z zamrożonego school_route_snapshot, gdy taki istnieje,
nie z globalnego live matchera. Cofnięcie SHARE i regrant nie ożywiają uchwytów.

## CV i granice opcjonalnych zależności

Default demo nie potrzebuje kamery, ADB, OpenCV ani YOLO. Opcjonalny klip z
school_navigation_demo jest tworzony na nowo w root/operator. Capture jest
oddzielnym workerem istniejącej bazy; stdin=DEVNULL zapobiega dziedziczeniu
operatorskiego kanału fixture. Biblioteki numeryczne workera są ograniczone do
jednego wątku BLAS/OMP; kolejki i cache 32 preview pozostają bounded.
Brak zależności w workerze daje jawne FAILED/CV_RUNTIME_UNAVAILABLE, a nie
awarię portalu. Nie wykonywano testu brakującego fizycznego urządzenia.

Opcjonalny detector wymaga operator-provided .pt pod nowym school root,
SCHOOL_CV_MODEL, SCHOOL_CV_LICENSE_ACK=operator-verified-license i właściwego
SCHOOL_CV_PYTHON. Nie pobrano, nie przeczytano i nie opublikowano prywatnych wag.
Deklaracja operatora nie zastępuje przeglądu licencji konkretnego pliku.
Nie testowano rzeczywistego YOLO. Synthetic detector events i stub workbench są
osobną kategorią testów autoryzacji; klip/preview dekoduje rzeczywisty OpenCV worker.

Reviews są oddzielnymi append-only faktami CV_REVIEW w prywatnym audytowanym
ledgerze trip, z author/server_at/reason/revision/before-history i idempotency.
Oryginalne detekcje i media nie są modyfikowane. Association korzysta z istniejącego
VisionWorkbench i dodatkowego author/time audit; jego SQLite index jest per-trip.
Żaden review, association, publikacja ani rola nie zmienia weryfikacji drogowej.

## UI i live gate

Główny widok Nawigacja ma mapę w perspektywie, orientację, najbliższe światło,
pełną listę następnych świateł, duży łuk prędkościomierza, limit/source i quality.
GPS jest projektowany lokalnie z rzeczywistych WGS84, nie na syntetyczny schemat.
Demo jest jawnie oznaczone. Mock GPS ma etykietę TEST GPS; brak speed to „—”.
Zaawansowane replay/raporty/CV pozostają w Laboratorium. Obsługa zdarzeń jazdy
jest przeznaczona dla pasażera. Menu nie nadaje uprawnień.

Backend nadal używa niezmienionego evaluate_live_navigation: fresh qualified GPS,
MATCHED/FORWARD, FIELD_CHECKED geometry/line/limit, verified phase windows,
compatible prediction clock i legal solver result. UI nie tworzy eligibility.
Guidance zachowuje hamowanie, stop, legalny limit i hysteresis; po stale response,
network error, utracie sesji lub zakończeniu jazdy usuwa zakres/polecenie.
Nie istnieje pozytywny terenowy odbiór zweryfikowanych faz tej aplikacji.

Screenshoty są rzeczywistym headless Edge na desktop1360×900/phone390×844,
narrow320 oraz landscape844×390. Po obejrzeniu usunięto nakładanie się nazw
odległych świateł; dalsze nazwy/stany pozostają czytelne na liście. Sprawdzono
focus/Escape dialogu i brak page overflow. Nie jest to test fizycznego telefonu.

## Sprawdzenia i coverage

Wyniki końcowe są uzupełniane po zakończeniu uruchomień; żadna liczba poniżej
nie ma zastępować szerokiego odbioru etapu10. Szczegółowy pomiar obejmuje wszystkie
szkolne pakiety oraz jawnie używane application/clocks/GPS/replay/positioning/
matcher/live gate/telemetry/CV supervisor/workbench. Bez omit trudnych I/O.
Worker subprocess i fizyczny sprzęt nie są zaliczone do parent-process coverage.
Istotna pure JS: api,dates,driving,filters,roles,state,validation; DOM/renderery
sprawdza E2E, ich kompletne pokrycie nie jest deklarowane tym pomiarem V8.

## Ograniczenia i odbiór

Nie sprawdzono fizycznego Android/Fused/Keystore, kamery, YOLO ani jazdy terenowej.
ADB devices zwróciło pustą listę. APK/JUnit nie zastępują sprzętu. Nie wykonano
Docker deploymentu ani wdrożenia na drugim PC — etap11. DB schema nadal v3,
14 tabel; żadna zastosowana migracja nie została zmieniona. PUBLISH-01 pozostaje
otwarty, historia nie jest przepisywana. Nie obiecujemy transakcyjnego recovery
DB+filesystem ani cofnięcia już pobranych bajtów.

- [ ] Nowy root, demo bez telefonu, start/pause/resume/observation/finish/export.
- [ ] Replay zgodnego typu, zero live advice, revoke/regrant nie odżywia starego.
- [ ] Drugie konto nie widzi cudzej navigation/GPS/CV; slot409 bez identity.
- [ ] GPS nullable/stale/mock, brak rady, prawidłowa nazwa źródła.
- [ ] Capture ze świeżego klipu, preview/status/events/review tylko owner.
- [ ] Desktop/phone/narrow/landscape i czyszczenie po logout.
- [ ] Uruchomienia i coverage poniżej; sprzęt odrębnie, etap10 nadal Do zrobienia.


## Końcowe wyniki własnego wykonania — Windows, 2026-10-14

- `python -m unittest discover -s tests -p test_school_navigation.py -q`: **17 PASS**,
  ostatnie wykonanie 72.788 s; real HTTP/temp DB i syntetyczne dane.
- `python -m scripts.school_stage9_verify --coverage-python .venv-school/Scripts/python.exe`:
  **400 testów, OK, 1 skip**, 501.479 s; sprawdzony origin eksportowanego modułu.
  To obejmuje school_accounts/passwords/SMTP/data/resources/share_contexts/records/admin
  i pełną Python regresję M8/GPS/replay/matcher/CV. Tkinter dostępny; bez błędu importu.
- Skip: Windows symlink permission (`WinError1314`), nie ukryty test; junction PASS.
- `node --test tests/driver_ui.cjs tests/vision_workbench_ui.cjs`: **7 PASS**.
  `node tests/mobile_flow.cjs`: PASS (mock flow, nie fizyczny Android).
- Node pure school logic: **35 PASS**, V8 lines99.56%,branches96.38%,functions98.81%.
- Edge navigation E2E: desktop/phone/narrow/landscape **PASS**; prawdziwy HTTPS/KDF,
  M8 simulation, generated OpenCV clip/decoded preview, simulation replay, synthetic
  authenticated GPS, unknown speed/no advice, owner isolation i logout/revoke.
  Edycja device label, Escape i przywracanie focusu wykonane. Nie sprzęt.
- Stage7 UI regression: **3 rozmiary PASS**; stage8 role regression po poprawce
  source replay: **3 rozmiary PASS**. Reauth regression: **desktop i phone PASS** (real403, draft/focus, conscious second submit, revision/cancel/role loss/account switch).
- Android `gradlew.bat -p android/GreenWaveSensor testDebugUnitTest assembleDebug
  --no-daemon --offline`: **BUILD SUCCESSFUL**, JUnit7 (3 queue,2 epoch,2 clocks),
  0 errors/failures/skips, APK debug wygenerowany. SDK XML v4/v3 i Gradle deprecations
  to ostrzeżenia środowiska; actual Fused/Keystore niewykonane. `adb devices`: brak.
- Base GreenWave: rzeczywisty HTTP200 `/api/state` w osobnym source export,
  explicit synthetic runs root, shutdown/server_close: **PASS**. Bez private runs.

### Coverage Python: branch=True, bez omit/exclude

Zakres to etapowy zestaw w verifierze; tabela obejmuje każdy raportowany moduł,
w tym trudne odmowy i I/O. Worker subprocess/hardware nie jest udawany jako
parent-process coverage. Niskie pokrycie supervisor38% jest jawne — wymaga
poszerzenia w końcowym odbiorze, nie usunięcia z mianownika.

|Moduł|Linie pokryte / wszystkie|Linie %|Gałęzie pokryte / wszystkie|Gałęzie %|Combined %|
|---|---:|---:|---:|---:|---:|
|greenwave/application.py|282/303|93.07|82/94|87.23|91.69|
|greenwave/clocks.py|37/38|97.37|5/6|83.33|95.45|
|greenwave/gps_replay.py|133/143|93.01|30/46|65.22|86.24|
|greenwave/live_navigation.py|38/40|95.00|25/28|89.29|92.65|
|greenwave/map_matching.py|189/206|91.75|55/70|78.57|88.41|
|greenwave/positioning.py|302/323|93.50|107/128|83.59|90.69|
|greenwave/replay.py|63/66|95.45|23/34|67.65|86.00|
|greenwave/school_accounts/__init__.py|0/0|100.00|0/0|100.00|100.00|
|greenwave/school_accounts/__main__.py|56/67|83.58|9/12|75.00|82.28|
|greenwave/school_accounts/config.py|55/59|93.22|16/20|80.00|89.87|
|greenwave/school_accounts/crypto.py|60/62|96.77|16/18|88.89|95.00|
|greenwave/school_accounts/demo_mail.py|70/80|87.50|30/38|78.95|84.75|
|greenwave/school_accounts/errors.py|4/4|100.00|0/0|100.00|100.00|
|greenwave/school_accounts/http.py|233/252|92.46|77/104|74.04|87.08|
|greenwave/school_accounts/limits.py|28/28|100.00|2/2|100.00|100.00|
|greenwave/school_accounts/mail.py|57/60|95.00|7/8|87.50|94.12|
|greenwave/school_accounts/service.py|170/177|96.05|27/36|75.00|92.49|
|greenwave/school_accounts/sessions.py|58/60|96.67|13/14|92.86|95.95|
|greenwave/school_admin/__init__.py|0/0|100.00|0/0|100.00|100.00|
|greenwave/school_admin/service.py|83/85|97.65|23/34|67.65|89.08|
|greenwave/school_admin/validation.py|101/106|95.28|67/92|72.83|84.85|
|greenwave/school_data/__init__.py|3/3|100.00|0/0|100.00|100.00|
|greenwave/school_data/__main__.py|32/33|96.97|7/8|87.50|95.12|
|greenwave/school_data/accounts.py|52/52|100.00|22/22|100.00|100.00|
|greenwave/school_data/backup.py|71/74|95.95|9/12|75.00|93.02|
|greenwave/school_data/configurations.py|38/38|100.00|10/16|62.50|88.89|
|greenwave/school_data/database.py|59/62|95.16|8/8|100.00|95.71|
|greenwave/school_data/errors.py|11/11|100.00|0/0|100.00|100.00|
|greenwave/school_data/locking.py|33/37|89.19|5/8|62.50|84.44|
|greenwave/school_data/migrations.py|110/111|99.10|43/44|97.73|98.71|
|greenwave/school_data/observations.py|80/80|100.00|27/42|64.29|87.70|
|greenwave/school_data/repositories.py|8/8|100.00|0/0|100.00|100.00|
|greenwave/school_data/repository_base.py|51/51|100.00|14/16|87.50|97.01|
|greenwave/school_data/security_records.py|95/95|100.00|16/22|72.73|94.87|
|greenwave/school_data/storage.py|48/49|97.96|15/16|93.75|96.92|
|greenwave/school_data/time_units.py|26/26|100.00|14/14|100.00|100.00|
|greenwave/school_data/trips.py|133/133|100.00|45/62|72.58|91.28|
|greenwave/school_data/validation.py|39/39|100.00|16/16|100.00|100.00|
|greenwave/school_navigation/__init__.py|0/0|100.00|0/0|100.00|100.00|
|greenwave/school_navigation/cv.py|142/179|79.33|44/94|46.81|68.13|
|greenwave/school_navigation/devices.py|137/146|93.84|33/54|61.11|85.00|
|greenwave/school_navigation/engine.py|53/53|100.00|10/18|55.56|88.73|
|greenwave/school_navigation/maps.py|27/30|90.00|10/20|50.00|74.00|
|greenwave/school_navigation/replay.py|5/5|100.00|0/0|100.00|100.00|
|greenwave/school_records/__init__.py|0/0|100.00|0/0|100.00|100.00|
|greenwave/school_records/lists.py|62/62|100.00|33/38|86.84|95.00|
|greenwave/school_records/paging.py|56/58|96.55|16/24|66.67|87.80|
|greenwave/school_records/raw.py|54/56|96.43|27/44|61.36|81.00|
|greenwave/school_records/recording.py|273/277|98.56|66/94|70.21|91.37|
|greenwave/school_records/writes.py|114/115|99.13|24/38|63.16|90.20|
|greenwave/school_resources/__init__.py|0/0|100.00|0/0|100.00|100.00|
|greenwave/school_resources/api.py|122/123|99.19|97/108|89.81|94.81|
|greenwave/school_resources/contexts.py|230/235|97.87|55/78|70.51|91.05|
|greenwave/school_resources/files.py|170/177|96.05|55/88|62.50|84.91|
|greenwave/school_resources/policy.py|63/64|98.44|23/28|82.14|93.48|
|greenwave/school_resources/reads.py|91/125|72.80|34/62|54.84|66.84|
|greenwave/telemetry.py|120/133|90.23|20/30|66.67|85.89|
|greenwave/vision_capture.py|57/127|44.88|14/58|24.14|38.38|
|greenwave/vision_workbench.py|141/152|92.76|41/64|64.06|84.26|

Cały jawny zakres etapowy: lines 4825/5178 (93.1827%), branches 1467/2030 (72.2660%), combined 87.2919%.

Same szkolne pakiety: lines 3463/3647 (94.9548%), branches 1065/1472 (72.3505%), combined 88.4548%.

Nowy school_navigation: lines 364/413 (88.1356%), branches 97/186 (52.1505%), combined 76.9616%.


### Node/V8 — jawny zakres pure logiki, nie całe UI

|Moduł|Linie %|Branches %|Functions %|
|---|---:|---:|---:|
|api.mjs|100.00|92.45|87.50|
|dates.mjs|94.74|96.43|100.00|
|driving.mjs|100.00|100.00|100.00|
|filters.mjs|100.00|88.89|100.00|
|roles.mjs|100.00|100.00|100.00|
|state.mjs|100.00|100.00|100.00|
|validation.mjs|100.00|87.50|100.00|

Komenda: `node --experimental-test-coverage --test --test-coverage-include='**/portal/*.mjs'
 tests/school_portal.cjs tests/school_roles.cjs tests/school_reauth.cjs tests/school_driving.cjs`.
DOM/form/visual adapters nie są przedstawiane jako zmierzone Node unit coverage;
sprawdza je rzeczywiste E2E. Cały końcowy mianownik JS pozostaje na etap10.

### Wykryte problemy i ich rozstrzygnięcie

Pierwsze szkolne uruchomienie163 miało5 failures: cztery stare oczekiwania
niepodłączonych endpointów/aliasów i rzeczywisty premature FINISH cleanup.
Naprawiono je; pełna regresja później400 PASS. Test re-pair początkowo oczekiwał
409 zamiast prawidłowego404 usuniętego uchwytu po revokacji; testconcurrency
oczekiwał Conflict zamiast nowego neutralnego AuthError409 ACTIVE_SESSION_BUSY.
Nie zmieniono zabezpieczeń ani nie ukryto testów.

Jedno przerwane uruchomienie13 trwało2429.867s i timeoutowało w fixture login;
nie jest zaliczone. Nieprzerwane17 i full400 są osobnymi faktycznymi wykonaniami.
Zerowy wstępny coverage wynikał z reportowania relative_files inną konfiguracją;
arcs były zmierzone. Finalny run/report używa identycznego rcfile i nie pomija
plików. Rzeczywisty worker CV przetworzył nowy klip; usunięto blokujący import
z requestu i odziedziczony stdin, a not-yet-current/mock GPS jest odrzucany
zgodnie z oryginalnym providerem. Timeout nowego E2E na błędnym oczekiwaniu
bieżącego mock sample poprawiono etykietą diagnostycznego odrzucenia, nie gate.


## Screenshoty obejrzane po końcowej poprawce

- [Desktop — nawigacja demo](screenshots/stage9-desktop-navigation.png)
- [Telefon — nawigacja demo](screenshots/stage9-phone-navigation.png)
- [Desktop — brak prędkości GPS](screenshots/stage9-desktop-gps-missing-speed.png)
- [Telefon — brak prędkości GPS](screenshots/stage9-phone-gps-missing-speed.png)
- [Desktop — CV generated clip](screenshots/stage9-desktop-cv.png)
- [Telefon — CV generated clip](screenshots/stage9-phone-cv.png)

Ocena: dark/lime hierarchy i gauge czytelne, duży symbol nieznanej prędkości,
zero page overflow w E2E/4 rozmiarach, kontrolowany scroll tabel. Po oględzinach
powiększono komunikat braku pozycji i skrócono główny status do2 przyczyn;
pełne quality/match/eligibility są w zamkniętym panelu Laboratorium. Nie ma
nakładających się nazw distant lights, wszystkie nazwy/stany są na liście.
Kodów, bearerów, haseł i mailboxa nie ma na screenshotach. Wszystkie dane synthetic.

## Commity implementacji i odbiór

- 92c07c80fd6658c5464c7de5e232e2e6529f16c1 feat(school): integrate isolated M8 navigation and scoped phone/CV adapters
- 77798fd202728f76df7c9b28008b129bb2899810 fix(school): preserve navigation completion and scoped CV evidence lifecycle
- 844e633c48e56ac6c8adb72e183e9598a9bdba5e feat(android): bind school telemetry to HTTPS device and session credentials
- 546c37241843c6f4de5db8215b61494ee4379f1b fix(school): acknowledge durable GPS writes and inspect compatible replay evidence
- c23e8b8698064a39a880d0e74784a5af5e59c819 feat(school-ui): add responsive navigation gauge and diagnostic laboratory

Commit dokumentacyjny można jednoznacznie odczytać przez
`git log -1 --format=%H -- docs/school-app/stage9.md`; nie zapisujemy przyszłego
hasha w jego własnej treści. Komendy/manual/demo/hardware są w run.md sekcje16–18.
Nie pushowano, nie scalono, nie przepisano historii; schema3/14tables, main i vision
pozostają bazowymi refami. PUBLISH-01 otwarte. Etap10–12 Do zrobienia.
