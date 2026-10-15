# Etap 10 — końcowa weryfikacja i odbiór

Aktualna korekta po przeglądzie commita9395f1a jest opisana w końcowej sekcji
„Ponowny przegląd CI”. Pierwsze wyniki i tabele poniżej są historycznym odbiorem
lokalnym tego commita, a nie dowodem zielonego CI dla poprawionej wersji.

Baza zaakceptowanego etapu 9: dabe41356c6028b855506ffd8e93aa3a844ad126.
Zakres zapisany przed uzupełnianiem testów. Brak zmian lokalnych na wejściu.

## Stały zakres i próg

Python: `source=greenwave`, wszystkie sześć school_* w całości, również ich CLI,
SMTP, HTTP, autoryzacja, migracje, filesystem i recovery. Cały rdzeń M8: application,
server, clocks, events, models, observations, prediction, simulation, vehicle,
solver, trajectory, positioning, telemetry, analysis, replay, gps_replay,
route_geometry, map_matching, route_events, live_navigation, mapping_analysis,
observation_history/review/completeness oraz wszystkie kontrakty/tracking/
validation/workbench/capture CV. Włączono także vision_detector i
vision_capture_worker (szerszy zakres niż historyczne wyłączenie z audytu).
Syntetyczny detector/worker test nie dowodzi działania YOLO lub kamery.

Jedyne cztery wyłączenia Python, jawne ścieżki w .coveragerc:
- ui.py: historyczny, nieużywany przez portal panel Tkinter; jego istniejący test
  nadal jest uruchamiany. Brak Tkinter pozostaje błędem testu, nie ukrytym sukcesem.
- greenwave/__main__.py: launcher lokalnej bazy, osobny HTTP smoke; szkolne CLI są mierzone.
- vision_probe.py: operatorski benchmark ML, poza aplikacją szkolną.
- vision_demos.py: generator syntetycznych fixture, poza logiką aplikacji.
Nie wyłączamy obsługi błędów, walidacji, I/O, uprawnień ani recovery. Testy,
scripts/tools, vendor i Android nie należą do source=greenwave. SQL i HTML/CSS
nie są mierzalnymi liniami Python. Nie ma dodatkowych exclude_lines.

Wymagany próg: combined coverage.py >=70%, czyli
(wykonane linie + wykonane wyjścia gałęzi)/(wszystkie linie + wszystkie wyjścia).
Raportujemy osobno linie, gałęzie, combined, szkołę i rdzeń; nie średnią procentów
modułów. Próg egzekwuje CLI coverage report (kod wyjścia 2 poniżej progu).

JS: oddzielny V8/Istanbul, wszystkie pliki JS/MJS portalu kont (account.js i
portal/*.mjs, w tym formularze/DOM/polling), oraz używane odpowiedniki bazowej
logiki guidance/perspective i CV UI: greenwave/web/driver-ui.js oraz
vision-workbench-ui.js. Brak importu/wykonania pliku oznacza 0%, nie usunięcie
z mianownika. Unit V8 i real-browser V8 są scalane do wspólnego JS raportu;
nie łączymy procentów Python i JS. Stare app.js/mobile.js/capture-ui.js to
nieużywany przez portal legacy shell/telefon web; test mobile_flow jest osobnym
regresyjnym mockiem. HTML/CSS oceniamy E2E, nie jako JS coverage.
JS próg 70% linii i gałęzi całego tego zakresu; per-file raport pozostaje jawny.

## Macierz ryzyka i bazowe testy

|Obszar|Istniejące dowody|Sprawdzenie/luka etapu 10|
|---|---|---|
|Konta/SMTP|HTTP + rzeczywisty SMTP/KDF, expiry/reset/CSRF|Pełna regresja i real browser register/reset|
|Dane/migracje|SQLite temporary, v1 upgrade/backup/rollback, authorizer|Ponowienie na czystym interpreterze, Windows/Linux CI|
|Własność/shares/jobs|HTTP macierz, exact grant, owner management|Ponowienie, bez zmiany polityki|
|Zapisy/recovery|intents, raw, revision, cursor/DST, start-failure|Pełna regresja, slot/cleanup i durable ingest|
|Admin/config|last-admin race, reauth, nested flags, audit|Real modal expired reauth i świadomy drugi submit|
|Navigation/device|HTTP, boot/TTL/re-pair, live gates|Dobór granic po raporcie coverage|
|CV|synthetic contracts, fake capture, supervisor|Uzupełnienie awarii procesu/manifestu/braku runtime|
|Frontend|35 unit + role/account/UI/navigation browser|Stały pełny mianownik JS, DOM/form coverage|
|Android|7 JUnit + debug APK|Ponowienie; sprzęt/Keystore/Fused osobno niewykonane|

GitHub Actions: nie uruchomiono zdalnie; brak push w zakresie polecenia.
Docker/drugi komputer/raport końcowy: etapy 11–12, tutaj niewykonane.


## Środowisko i sposób wykonania

Własne wykonanie Windows, Python3.14.4 x64, coverage7.13.1, Node24.18.0,
Playwright1.64.1/installed Edge, numpy2.4.4, opencv-python-headless4.13.0.92.
JDK17, Android compileSdk36, Gradle8.13/AGP8.12.0. Clean venv utworzono poleceniem
`python -m venv artifacts/stage10/clean-env`; nie ma system-site-packages.
`pip install -r requirements-test.txt` oraz `npm ci --ignore-scripts --no-audit --no-fund`
rzeczywiście zakończyły się sukcesem. Worker E2E używa tego samego clean interpretera.

Punkt odniesienia, przed nowymi testami:
- `python -m scripts.school_stage9_verify --coverage-python .venv-school/Scripts/python.exe`:
  400 testów,399 PASS/1skip,372.566s, izolowany origin i bazowy HTTP smoke PASS.
  To historyczny etapowy mianownik, nie wynik końcowy.
- Dotychczasowe35 Node/V8 PASS; bazowe7 Node PASS; mobile_flow mock PASS.
- Browser konta desktop/phone PASS; Android pierwsze build SUCCESS korzystał z cache,
  dlatego końcowe JUnit/build wymuszono --rerun-tasks.

Dokładne końcowe polecenia (PowerShell w istniejącym worktree):

```powershell
$env:GW_PYTHON = (Resolve-Path artifacts/stage10/clean-env/Scripts/python.exe).Path
& $env:GW_PYTHON -m scripts.school_verify --output artifacts/stage10-final
$env:GW_BROWSER_CHANNEL = 'msedge'
npm run coverage:js
node tests/mobile_flow.cjs
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
.\android\GreenWaveSensor\gradlew.bat -p android/GreenWaveSensor testDebugUnitTest assembleDebug --no-daemon --offline --rerun-tasks
```

Finalne Python raporty z stage10-final skopiowano do standardowego artifacts/stage10
(po zakończeniu wcześniejszego nieudanego runnera). Nie zmieniano ani nie scalano
liczników coverage. Świeże odtworzenie normalnie używa domyślnego output stage10.
Pełny runner nie wymaga istniejącego portalu/SMTP/sekretów; eksporter kopiuje kod
oraz allowlist publicznych seedów i odmawia default-root testów w checkout.

## Wykryte błędy i testy regresyjne

1. **Walidacja startu CV**: width/height/fps/realtime trafiały do kontrolera i błąd
   ValueError był mapowany jako503 runtime unavailable. Teraz service sprawdza typ
   (bool nie jest liczbą), przedział i boolean przed utworzeniem kontrolera:422.
   Jego własne defensywne walidatory nadal działają. Real HTTP test pięciu błędnych
   pól sprawdza też brak utworzenia kontrolera. Przed:503; po:422.
2. **Capture po awarii indeksu**: try obejmował spawn, ale nie utworzenie workbench,
   rejestrację i pierwszy status. OSError po starcie zostawiał uruchomiony kontroler.
   Cała inicjalizacja ma teraz cleanup/pop/close, neutralne503, bez tworzenia fałszywego
   manifestu. Test real HTTP wymusza dokładnie błąd workbench po start i sprawdza
   close/brak ctx oraz poprawny finish nawigacji. Przed close0; po close1.
3. **Nowy reporter**: fixture WorkbenchTests ma pole id, co zasłania TestCase.id().
   Błąd nowego narzędzia przerywał szeroki przebieg; nie zaliczono go jako PASS.
   Reporter używa bazowej metody TestCase.id, poprawnie liczy także nieudane subtests.
   Dodano2 testy samego narzędzia i ponowiono cały zestaw.

Nowy plik test_school_final_boundaries.py:10 testów (4 real HTTP/SQLite,6 jednostkowych
supervisor/worker/maps). Dodatkowe istotne granice: brak optional OpenCV, nieudany
spawn, close timeout, worker abnormal exit unieważnia manifest, watchdog nie zabija
FINALIZING, brak runtime nie zatrzymuje nawigacji, kontrolowana mapa missing/too-large,
corrupt snapshot i frozen route. Bez przypadkowych sleep do sterowania wyścigiem.
Przed poprawką:10 testów,6 failure assertions (5 subtests jednego testu + orphan close).
Po:10 PASS,15.287s. `test_verification_tools.py`:2 PASS,0.002s.

Naprawa powtarzalności testów: fixture wybiera openssl przez PATH zamiast zakładać
Windows path; domyślne Edge można zamienić na zainstalowany Chromium. Kod aplikacji
poza CV service nie był zmieniany. Solver, logger/formats, live gate i zastosowane
migracje mają pusty diff do bazy dabe413. Nie ma nowej funkcji produktu.

## Końcowe wyniki testów

|Zestaw|Wynik|Ograniczenie|
|---|---|---|
|Python pełna regresja, unit + integracyjne HTTP/SQLite/SMTP/files|412 wykonanych:411 PASS,0FAIL,0ERROR,1skip;430.630s|Nowy izolowany export, jeden clean interpreter|
|Nowe testy10 + reporter2|PASS; zawarte w powyższych412|Nie doliczać drugi raz|
|Node pure logika + zachowane UI contracts|42 PASS,0FAIL/skip|35 szkolnych +7 bazowych, pomiar z całością browser|
|mobile_flow|PASS|Mock web sender, nie natywny telefon|
|Browser Edge|6 zestawów,16 przebiegów rozmiarów PASS|Actual server/KDF/SMTP/temp DB, nie mock backendu|
|Android|7 JUnit PASS,0FAIL/ERROR/skip;debug APK SUCCESS,37/37 zadań wykonanych|--rerun-tasks, nie rezultat z cache|
|Bazowy GreenWave|Actual HTTP200/state/shutdown PASS|Wyłącznie izolowany synthetic root|
|Próg coverage|50% synthetic experiment:exit2;aktualny pełny raport:exit0|Próg70 faktycznie egzekwowany|
|CI YAML|Parse/triggers/push/PR/read-only permissions/always-artifacts PASS|Nie jest to zdalny run|

Jedyny skip: StorageTests.test_symlink_escape, Windows WinError1314 (brak privilege).
Windows junction test PASS; Tcl/Tk test rzeczywiście PASS. Braku tkinter nie ukryto.
Własnego Linux wykonania brak. Workflow instaluje zależności/Tk/Xvfb i ma Linux
symlink oraz Windows junction; ich zdalnych wyników jeszcze nie znamy.

### Pokryte scenariusze i rodzaje testów

- Jednostkowe: solver/trajectory/models/prediction, mapping/guidance, expiry/KDF,
  migracja SQL authorizer/time units, filtry/cursor/DST, worker queue/stop/errors,
  frontend state/validation/abort/stale-response/idempotency/reauth draft.
- Integracyjne: real SQLite init/v1 upgrade/checksum/rollback/backup/restore/locks;
  real HTTP auth/CSRF/Host/Origin/DTO/SMTP, own/shared/admin/anonymous matrix,
  share-regrant handles, owner job management, actual raw/manifest/export/corrections,
  failure injection/recovery/revisions/races, device binding and durable write failure.
- Przeglądarkowe: formularze/modale/tabele i świadomy reauth drugi submit; patrz niżej.
- Sprzętowe: fizyczny telefon/Fused/Keystore/ADB/kamera/YOLO/droga nie były uruchamiane.
  JUnit i synthetic sender/clip nie są przypisane do tej kategorii jako PASS.

## Końcowy Python coverage (branch=True)

Brak exclude_lines;0excluded lines w zakresie. 81 modułów, w tym puste __init__.
Wynik główny obejmuje cały stały mianownik; szkoła i rdzeń są podzbiorami,
nie odrębnymi alternatywnymi zakresami do wyboru.

|Zakres|Linie wykonane/wszystkie|Gałęzie wykonane/wszystkie|Combined|
|---|---:|---:|---:|
|Cały ustalony zakres|7054/7651 (92.1971%)|2316/3084 (75.0973%)|87.2846%|
|Sześć pakietów szkolnych|3473/3654 (95.0465%)|1068/1478 (72.2598%)|88.4840%|
|Cały objęty rdzeń GreenWave|3581/3997 (89.5922%)|1248/1606 (77.7086%)|86.1860%|

Główny próg70 combined jest spełniony bez zmniejszenia mianownika; także same
linie i same gałęzie przekraczają70%. Nie doliczano E2E do Python coverage:
worker subprocess ma tylko bezpośrednie unit synthetic pokrycie, nie coverage
przeniesione z innego interpretera. Wszystkie brakujące ścieżki są w JSON/HTML.

|Moduł greenwave/|Linie|Gałęzie|Combined|
|---|---:|---:|---:|
|__init__.py|0/0|0/0|100.0000%|
|analysis.py|168/184|52/66|88.0000%|
|application.py|282/303|82/94|91.6877%|
|clocks.py|37/38|5/6|95.4545%|
|events.py|47/48|18/20|95.5882%|
|gps_replay.py|133/143|30/46|86.2434%|
|live_navigation.py|38/40|25/28|92.6471%|
|map_matching.py|189/206|55/70|88.4058%|
|mapping_analysis.py|125/132|32/36|93.4524%|
|models.py|49/55|30/36|86.8132%|
|observation_completeness.py|52/54|34/36|95.5556%|
|observation_history.py|102/105|33/36|95.7447%|
|observation_review.py|44/46|17/20|92.4242%|
|observations.py|44/44|8/8|100.0000%|
|positioning.py|303/324|108/130|90.5286%|
|prediction.py|181/190|73/82|93.3824%|
|replay.py|63/66|23/34|86.0000%|
|route_events.py|79/80|25/28|96.2963%|
|route_geometry.py|200/234|60/90|80.2469%|
|school_accounts/__init__.py|0/0|0/0|100.0000%|
|school_accounts/__main__.py|56/67|9/12|82.2785%|
|school_accounts/config.py|55/59|16/20|89.8734%|
|school_accounts/crypto.py|60/62|16/18|95.0000%|
|school_accounts/demo_mail.py|70/80|30/38|84.7458%|
|school_accounts/errors.py|4/4|0/0|100.0000%|
|school_accounts/http.py|233/252|77/104|87.0787%|
|school_accounts/limits.py|28/28|2/2|100.0000%|
|school_accounts/mail.py|57/60|7/8|94.1176%|
|school_accounts/service.py|170/177|27/36|92.4883%|
|school_accounts/sessions.py|58/60|13/14|95.9459%|
|school_admin/__init__.py|0/0|0/0|100.0000%|
|school_admin/service.py|83/85|23/34|89.0756%|
|school_admin/validation.py|101/106|67/92|84.8485%|
|school_data/__init__.py|3/3|0/0|100.0000%|
|school_data/__main__.py|32/33|7/8|95.1220%|
|school_data/accounts.py|52/52|22/22|100.0000%|
|school_data/backup.py|71/74|9/12|93.0233%|
|school_data/configurations.py|38/38|10/16|88.8889%|
|school_data/database.py|59/62|8/8|95.7143%|
|school_data/errors.py|11/11|0/0|100.0000%|
|school_data/locking.py|33/37|5/8|84.4444%|
|school_data/migrations.py|110/111|43/44|98.7097%|
|school_data/observations.py|80/80|27/42|87.7049%|
|school_data/repositories.py|8/8|0/0|100.0000%|
|school_data/repository_base.py|51/51|14/16|97.0149%|
|school_data/security_records.py|95/95|16/22|94.8718%|
|school_data/storage.py|48/49|15/16|96.9231%|
|school_data/time_units.py|26/26|14/14|100.0000%|
|school_data/trips.py|133/133|45/62|91.2821%|
|school_data/validation.py|39/39|16/16|100.0000%|
|school_navigation/__init__.py|0/0|0/0|100.0000%|
|school_navigation/cv.py|151/186|48/100|69.5804%|
|school_navigation/devices.py|137/146|33/54|85.0000%|
|school_navigation/engine.py|53/53|9/18|87.3239%|
|school_navigation/maps.py|29/30|11/20|80.0000%|
|school_navigation/replay.py|5/5|0/0|100.0000%|
|school_records/__init__.py|0/0|0/0|100.0000%|
|school_records/lists.py|62/62|33/38|95.0000%|
|school_records/paging.py|56/58|16/24|87.8049%|
|school_records/raw.py|54/56|27/44|81.0000%|
|school_records/recording.py|272/277|65/94|90.8356%|
|school_records/writes.py|114/115|24/38|90.1961%|
|school_resources/__init__.py|0/0|0/0|100.0000%|
|school_resources/api.py|122/123|97/108|94.8052%|
|school_resources/contexts.py|230/235|55/78|91.0543%|
|school_resources/files.py|170/177|55/88|84.9057%|
|school_resources/policy.py|63/64|23/28|93.4783%|
|school_resources/reads.py|91/125|34/62|66.8449%|
|server.py|238/311|113/152|75.8099%|
|simulation.py|40/44|14/18|87.0968%|
|solver.py|177/186|78/92|91.7266%|
|telemetry.py|120/133|20/30|85.8896%|
|trajectory.py|159/163|78/86|95.1807%|
|vehicle.py|59/63|19/24|89.6552%|
|vision_capture.py|107/127|33/58|75.6757%|
|vision_capture_worker.py|148/215|34/70|63.8596%|
|vision_contracts.py|156/171|69/92|85.5513%|
|vision_detector.py|0/26|0/2|0.0000%|
|vision_tracking.py|55/55|22/24|97.4684%|
|vision_validation.py|45/59|17/28|71.2644%|
|vision_workbench.py|141/152|41/64|84.2593%|

## Końcowy JS — osobny mianownik i V8/Istanbul

22 pliki: cały account.js i19 portal/*.mjs oraz2 zachowane legacy UI adapters.
Brak plików pominiętych z powodu niewykonania; runner wstawia0dla niezaładowanego
pliku. Źródło z browser jest porównywane z bajtami checkoutu; brak bundlera/map.
Każde wykonanie ma nowy raw V8 folder — wyniki wcześniejszego sukcesu nie zasilają
nowego przebiegu. Scalane są tylko te same aplikacyjne źródła, nie eval/fixture.

Linie **777/1021=76.10%**, gałęzie/bloki V8 **1201/1215=98.84%**, funkcje 162/192=84.37%.
Oba egzekwowane progi70 (linie i gałęzie) PASS. Te gałęzie są wyjściami bloków/ranges
V8 mapowanymi przez v8-to-istanbul; nie stanowią tego samego licznika co Python ani
pełnej analizy składni wszystkich niewykonanych JS warunków. Wysoki branch wynik
nie ukrywa niższych linii/funkcji ani brakującego legacy DOM; per-file poniżej.
Nie wyliczamy wspólnej średniej z Python i JS.

|Plik|Linie %|V8 branches %|Functions %|
|---|---:|---:|---:|
|school_accounts/web/account.js|97.22|92.85|100.00|
|school_accounts/web/portal/api.mjs|100.00|98.24|100.00|
|school_accounts/web/portal/auth.mjs|100.00|94.20|83.33|
|school_accounts/web/portal/dates.mjs|94.73|100.00|100.00|
|school_accounts/web/portal/details.mjs|98.27|100.00|85.71|
|school_accounts/web/portal/devices.mjs|80.00|100.00|75.00|
|school_accounts/web/portal/dom.mjs|100.00|93.87|100.00|
|school_accounts/web/portal/drive_view.mjs|89.74|100.00|100.00|
|school_accounts/web/portal/driving.mjs|100.00|100.00|100.00|
|school_accounts/web/portal/filters.mjs|100.00|100.00|100.00|
|school_accounts/web/portal/forms.mjs|96.55|100.00|100.00|
|school_accounts/web/portal/laboratory.mjs|100.00|100.00|92.30|
|school_accounts/web/portal/lists.mjs|100.00|100.00|60.00|
|school_accounts/web/portal/navigation.mjs|100.00|100.00|100.00|
|school_accounts/web/portal/records.mjs|100.00|100.00|100.00|
|school_accounts/web/portal/role_views.mjs|64.03|100.00|76.19|
|school_accounts/web/portal/roles.mjs|100.00|100.00|100.00|
|school_accounts/web/portal/state.mjs|100.00|100.00|100.00|
|school_accounts/web/portal/validation.mjs|100.00|100.00|100.00|
|school_accounts/web/portal/vision.mjs|92.85|100.00|83.33|
|web/driver-ui.js|16.20|95.55|15.78|
|web/vision-workbench-ui.js|18.75|90.90|50.00|

## Browser — faktyczne zachowania, nie tylko screenshoty

- accounts:desktop1280×900 i phone390×844;register/client invalid confirmation,
  real SMTP/verify GET nonconsume+POST,login/reauth/logout/reset/change/logout-all,
  no localStorage, fragment usunięty. Bez wypisywania tokenu/poczty w raporcie.
- resources:desktop1280×900/phone390×844, rzeczywiste own/shared reads i odmowy
  foreign/admin/export, po logout401.
- ui:desktop1360×900/phone390×844/320×844:synthetic create/start/observation/finish,
  export/edit/correction/history, filtry obu tabel/cursor kolejna strona,
  share/revoke/archive, conflict409/network failure/expired session, zmiana konta,
  Escape/keyboard/focus/overflow.
- roles:te same3 rozmiary, shared readonly/replay/GPS_QUALITY/report/revoke,
  config draft/edit/publish, admin reauth/role/block/unblock/audit, private DTO.
- reauth:desktop1360×900/phone390×844, synthetic clock fixture wymusza real403 po
  otwarciu modalu. Dostępny formularz hasła, draft tylko ten sam user, brak automatycznej
  mutacji, drugi submit; revision adoption, bad password401, cancel/Escape,
  utrata zasobu/roli i logout/login innego konta. Bez publicznego clock endpointu.
- navigation:desktop1360×900/phone390×844/320×844/landscape844×390;actual HTTPS
  fixture,synthetic simulation/start/pause/finish/export/replay, real generated clip
  decoder/preview/stop, synthetic authenticated GPS missing-speed gate i odmowa
  cudzej navigation/device logout. Nie jest to fizyczny Android lub YOLO.

Zero błędów strony i page horizontal overflow w wykonanych asercjach; tabele mają
kontrolowany scroll. Obejrzano dodatkowo nowy phone-navigation PNG: czytelny gauge,
jasne DEMO/synthetic, lista i brak nakładania. Screenshoty w ignorowanym
artifacts/stage10/screenshots/ i artifacts/school-accounts, komplet raportowy etap12.

## CI, luki i status odbioru

Nie było wcześniejszego workflow. Dodano jeden .github/workflows/verify.yml:
push/pull_request/manual,contents:read, Windows+Linux full Python/70 gate,
Linux actual Chromium/V8/JS gate i Android7JUnit/debug. fail-fast:false i
upload-artifact if:always();upload tylko raportów/syntetycznych screenshotów,
nie DB/mailbox/secret/runtime/video/weights. Tcl/Tk/Xvfb instalowane na Linux,
nie wyłączono testu importującego tkinter. Browser sources wybierane allowlistą.
Na moment przygotowania commita9395f1a zdalnego uruchomienia jeszcze nie było.
Użytkownik następnie wykonał push i run38706404163 zakończył się failure;
aktualne ustalenia i ograniczenia logów są w sekcji ponownego przeglądu poniżej. Lokalny YAML parse i
kontrola triggerów/uprawnień/always-artifacts PASS. Konfiguracja jest gotowa do
uruchomienia po osobno autoryzowanym pushu.

Istotne pozostałe luki są jawne: vision_detector0% (prawdziwe ML nie uruchomione),
vision_capture_worker63.8596%combined (sprzęt/niektóre error paths/subprocess bez
tracing), supervisor75.6757%, niektóre odmowy/błędy SMTP/plików/Windows-vs-POSIX;
nie wyłączono ich. JS legacy renderer driver-ui16.20% i vision-workbench18.75%,
role_views64.03%lines; aktualny portal jako całość92.87%portal/*.mjs i97.22%account.js.
Wysoki ogólny wynik nie oznacza kompletności wszystkich gałęzi ani bezpieczeństwa
potwierdzonego niezależnym pentestem. Nie modyfikowano mechanizmu dopuszczenia live.

Sprzęt:Fused location/Keystore/TLS na fizycznym Androidzie, background service,
kamera, model YOLO/licencja/jakość drogowa i jazda terenowa pozostają niewykonane.
Nie pobrano wag ani nie dotykano prywatnych nagrań. PUBLISH-01 pozostaje osobno;
wcześniejsza opublikowana historia runtime nie została przepisana.

**Historyczny stan commita9395f1a: kryteria lokalne spełnione.** Po przeglądzie
CI etap wymaga korekty opisanej poniżej; pełne zamknięcie wymaga zielonego
rzeczywistego Actions poprawionej wersji. Sprzęt pozostaje osobno niewykonany. Docker/drugi komputer etap11 oraz końcowy raport etap12 nadal Do zrobienia.
STOP przed etapem11. Nie pushowano,nie scalono,main/vision refs bez zmian.

Commity:
- 6a4e02cb1a2bb85e0cb574d307da1ddc67c2b1b9 — dwa błędy CV i10testów granic;
- 40f98642a32d05b074e92931442c65fb27e159b8 — scope/runner/CI/lockfile/browser+V8 i2testy raportera;
- commit tej dokumentacji: `git log -1 --format=%H -- docs/school-app/stage10.md`.
Pełne hashe i końcowy status w odpowiedzi; nie wpisuje się przyszłego hasha do własnego commita.


## Ponowny przegląd CI — baza 9395f1a5780c7b7ab99dc21237441342dd6d1f41

### Faktycznie dostępne dowody zdalne

[Run38706404163](https://github.com/SgaTwitchTv/Surfy/actions/runs/38706404163)
zweryfikowano przez publiczne GitHub REST jobs/check-runs/annotations oraz artefakt
javascript-browser. W momencie kontroli jest to jedyny run gałęzi codex/school-app.
Lokalne HEAD było zgodne z bazą i bez cudzych zmian.

|Job|Potwierdzony krok/wynik|Diagnoza i granica dowodu|
|---|---|---|
|Python/ubuntu-latest (116326789746)|success,Python3.14|Rzeczywisty zdalny sukces starej wersji; nie wynik obecnych poprawek|
|Python/windows-latest (116326789802)|Full isolated Python tests and70percent combined coverage:exit1;brak raportów Python|Pełny log403. Nie da się potwierdzić szczegółowej przyczyny. Osobno odtworzono lokalnie błąd locale/UTF8 runnera i naprawiono go; nie przypisujemy go jako udowodnionej przyczyny starego CI|
|JS/Chromium (116326789322)|browser-roles:narrow overflow;42unitPASS,pozostałe5suitesPASS|Potwierdzona wada układu raportu w320px,nie próg coverage:JS76.10%lines/98.83%V8branches;browserExit1|
|Android (116326789656)|Run android-actions/setup-android@v3:failure;test/build skipped|Pełny log403. Powód wewnątrz instalatora nieznany;nie przypisujemy go Javie/licencjom/downloadowi bez dowodu|

Pobrano wyłącznie publiczny syntetyczny javascript-browser artefakt przez
https://nightly.link/SgaTwitchTv/Surfy/actions/runs/38706404163/javascript-browser.zip ;
wewnętrzne browser-*.txt i js-scope.json potwierdzają powyższe. Pliki tylko w ignorowanym
artifacts/stage10-review/ci;nie dodawano ZIP/logów do Git ani nie wykonywano pobranego kodu.

Dostęp do pełnych logów całego runu i jobów przez api.github.com zwraca403
„Must have admin rights to Repository”;API artefaktów401„Requires authentication”.
Brak gh,GH_TOKEN/GITHUB_TOKEN oraz zalogowanego browsera w dostępnych narzędziach.
Publiczne adnotacje mają tylko exit1 i ostrzeżenia deprecacji, nie stos przyczyny.
**Brakujące logi**:Windows job116326789802/step7 oraz Android job116326789656/step4.
Ostrzeżenia Node20/setup-java-v4 i zmiany ubuntu-latest nie są uznawane za przyczynę.
Poproszono opcjonalnie o końcówki tych dwóch błędów; niezależna praca kontynuowana.

Relacja niezależnego przeglądu dostarczona przez użytkownika, nie własny pomiar:
Linux/Python3.12,412tests:409PASS,1FAIL(map mock),1ERROR(brak tkinter),1skip;
coverage92.22%lines/78.57%branches/88.35%combined. Brak tkinter to ograniczenie
środowiska recenzenta, nie dowód błędu aplikacji.42JSPASS. Same procenty nie zaliczają
nieudanych testów. Lokalnie dostępny tylko Python3.14.4;Py3.12 dodano do pełnej
macierzy Windows/Linux CI bez podnoszenia deklarowanego minimum3.12+.

### Poprawki i odtworzenia

- Mapa:usunięto globalny mock pathlib.Path.stat. Na3.12mock st_mode dawał TypeError
  i422zamiast wejścia w limit. Test przekierowuje tylko __file__ modułu map do nowego
  TemporaryDirectory i tworzy prawdziwy syntetyczny sparse file8MiB+1. Sprawdza
  dokładnie404NOT_FOUND,404MAP_UNAVAILABLE,409MAP_TOO_LARGE. Path.is_file/stat
  zachowują rzeczywistą semantykę; produkcyjna mapa/obsługa błędów bez zmian.
- Runner:kontrolowany rodzic cp1252 + dziecko UTF8 z tekstem„Zażółć → ā” odtwarza
  UnicodeDecodeError przed poprawką. run_captured jawnie dekoduje UTF8 strict,
  a show obsługuje terminal z ograniczonym kodowaniem bez utraty UTF8 w artefaktach.
 2nowe regresje sprawdzają tekst i zachowanie exit7;nie zamieniają błędu dziecka
  w sukces. runner-progress/error.txt powstają także przy błędzie przed testami i są
  uploadowane if:always. Izolowany eksport,scope,threshold i propagacja kodów zachowane.
- UI:potwierdzony zdalnie overflow po rozwinięciu raportu analityka. Wzmocniony test
  z większym monospace i tym samym pełnym32hexID daje320→395px przed poprawką,
  po overflow-wrap:anywhere w lab summary320px bez obcinania ID. Nie usunięto
  asercji,nie zwiększono timeoutu. Dodatkowe diagnostyczne fazy i stack w testach
  pomagają odróżnić timeout od nieprawidłowego stanu.
- Android CI:usunięto zależność od ponownej instalacji SDK przez setup-android-v3.
  Jawny Ubuntu24.04 ma już SDK/cmdline-tools;step weryfikuje wykonywalny sdkmanager,
  wypisuje wersje i instaluje zadeklarowane platform36/build-tools35.0.0/36.0.0.
  Java17pozostaje,setup-java@v5;bez nieograniczonych retry i bez continue-on-error.
  Zachowane JUnit/APK oraz always raporty/setup log. To zmiana przygotowania eliminująca
  wadliwy etap, nie deklaracja poznania nieodczytanego błędu instalatora ani sukcesu
  nowego CI. Lokalny rzeczywisty build korzysta z istniejącego SDK Windows.

Źródło deklaracji SDK hosted image:
https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md .
Przypięcie ubuntu24.04 unika zapowiedzianej migracji etykiety latest. Nie jest to
zmiana platformy aplikacji. CI pełna macierz3.12/3.14×Linux/Windows,JS nadal pełny
mianownik i oba progi70;stare raporty nie są używane do zaliczenia nowego przebiegu.


### Aktualne własne wyniki po korekcie

Własne środowisko Windows/Python3.14.4/Node24.18.0/Playwright1.64.1,
bundled Chromium156.0.8078.4(v1248),nowe synthetic roots. Python3.12niezainstalowany;
pełna macierzCIsprawdzi3.12oraz3.14,nie deklarujemy lokalnego wykonaniaLinux.

|Sprawdzenie|Aktualny wynik|
|---|---|
|Mapa+pozostałe granice CV|10PASS,20.389s;trzy kody mapy potwierdzone|
|Reporter+runnerUTF8|4PASS,0.213s;dwie nowe regresje|
|Pełny izolowany Python|414tests:413PASS,0FAIL,0ERROR,1skip;429.724s;exit0|
|Python runner diagnostics|START→EXPORT→TESTS→DONE,codes=0,0,0,0,0,0;XML/JSON/HTML/text zapisane|
|JS units|42PASS,0FAIL/skip,aktualny przebieg|
|Pełny Chromium|6suites/16viewport runs PASS;browserExit0,unitsExit0|
|UIprzednaprawąwyścigu|timeout po logout wskazywał check_school_ui.cjs:78;nie zaliczono|
|UIpo synchronizacji real401|desktop/phone/320PASS;bezsleep/timeoutincrease|
|Role/raport320|przedwidth395/viewport320FAIL;poCSS+largermonospacePASS|
|mobile_flow|PASS,osobny zachowany mock|
|Android|7JUnitPASS,0FAIL/ERROR/skip;BUILD SUCCESSFUL45s,37tasksEXECUTED;--rerun-tasks|
|BaseHTTPsmoke|PASS,izolowany root;nie czytano lokalnych prywatnych nagrań|
|CIconfig|YAML/matrix3.12×3.14,4Pythonjobs,requiredJS/Android,alwaysartifacts,Bash-n PASS|

Jedyny Python skip:Windows symlink WinError1314;brakprivilege. Windowsjunction iTkinter
rzeczywiście PASS. BuildAPK/JUnit i syntheticclip nie są dowodem sprzętowegoGPS,
Keystore,Fused,kamera,YOLO ani drogi. Docker/drugi komputer/raport końcowy niewykonane.

Dodatkowe lokalne odkrycia nie są przypisywane do starego CI bez dowodu:
pierwszy pełny Chromium miał jednorazowy timeout resources initial login;
diagnostyczny rerun i końcowy pełny zestaw przechodzą. Inny przebieg wykrył powtarzalny
wyścig testu expiry:poprawna odpowiedź401 mogła wyczyścić przycisk przed clickiem.
Eventgate konkretnego GET + rzeczywisty logout + rzeczywisty401 naprawia założenie
testu bez ingerencji w obsługę sesji. Nie zaliczono żadnego z tych nieudanych
przebiegów jako sukcesu. Jeden taki run miał JS71.20%lines/98.74%V8branches i mimo
przejścia progów poprawnie zakończył sięexit1 przez browserExit1.

Końcowy JS pomiar powstał od zera w
artifacts/stage10-review/chromium-verified/v8-<nowy-sufiks>,nie scalał danych z
chromium-baseline/chromium-final ani z artefaktu zdalnego. Mianownik22pliki,wszystkie
załadowane;nie zmieniono targets ani70%lines/branches. Python .coveragerc bez zmian,
81modułów/4historyczne wyłączenia/0excludedlines,całe sześćpakietów+rdzeń.

|Zakres|Linie|Gałęzie|Combined|
|---|---:|---:|---:|
|Całość Python|7055/7651 (92.2102%)|2316/3084 (75.0973%)|87.2939%|
|Szkolne pakiety|3474/3654 (95.0739%)|1067/1478 (72.1922%)|88.4840%|
|Objęty rdzeń|3581/3997 (89.5922%)|1249/1606 (77.7709%)|86.2038%|

JS osobno:lines778/1021=76.19%;V8blocks1214/1228=98.85%;functions163/192=84.89%.
V8branches to nie składniowy mianownik Python;a dynamiczne V8ranges mogą różnić się
między przebiegami mimo tych samych plików. Nie łączymy procentów języków.
Dokładne per-module dane maszynowe iHTML w ścieżkach poniżej;aktualny skrót tabel:

|Python moduł greenwave/|Linie|Gałęzie|Combined|
|---|---:|---:|---:|
|__init__.py|0/0|0/0|100.0000%|
|analysis.py|168/184|52/66|88.0000%|
|application.py|282/303|82/94|91.6877%|
|clocks.py|37/38|5/6|95.4545%|
|events.py|47/48|18/20|95.5882%|
|gps_replay.py|133/143|30/46|86.2434%|
|live_navigation.py|38/40|25/28|92.6471%|
|map_matching.py|189/206|55/70|88.4058%|
|mapping_analysis.py|125/132|32/36|93.4524%|
|models.py|49/55|30/36|86.8132%|
|observation_completeness.py|52/54|34/36|95.5556%|
|observation_history.py|102/105|33/36|95.7447%|
|observation_review.py|44/46|17/20|92.4242%|
|observations.py|44/44|8/8|100.0000%|
|positioning.py|303/324|108/130|90.5286%|
|prediction.py|181/190|73/82|93.3824%|
|replay.py|63/66|23/34|86.0000%|
|route_events.py|79/80|25/28|96.2963%|
|route_geometry.py|200/234|60/90|80.2469%|
|school_accounts/__init__.py|0/0|0/0|100.0000%|
|school_accounts/__main__.py|56/67|9/12|82.2785%|
|school_accounts/config.py|55/59|16/20|89.8734%|
|school_accounts/crypto.py|60/62|16/18|95.0000%|
|school_accounts/demo_mail.py|70/80|30/38|84.7458%|
|school_accounts/errors.py|4/4|0/0|100.0000%|
|school_accounts/http.py|233/252|77/104|87.0787%|
|school_accounts/limits.py|28/28|2/2|100.0000%|
|school_accounts/mail.py|57/60|6/8|92.6471%|
|school_accounts/service.py|170/177|27/36|92.4883%|
|school_accounts/sessions.py|58/60|13/14|95.9459%|
|school_admin/__init__.py|0/0|0/0|100.0000%|
|school_admin/service.py|83/85|23/34|89.0756%|
|school_admin/validation.py|101/106|67/92|84.8485%|
|school_data/__init__.py|3/3|0/0|100.0000%|
|school_data/__main__.py|32/33|7/8|95.1220%|
|school_data/accounts.py|52/52|22/22|100.0000%|
|school_data/backup.py|71/74|9/12|93.0233%|
|school_data/configurations.py|38/38|10/16|88.8889%|
|school_data/database.py|59/62|8/8|95.7143%|
|school_data/errors.py|11/11|0/0|100.0000%|
|school_data/locking.py|33/37|5/8|84.4444%|
|school_data/migrations.py|110/111|43/44|98.7097%|
|school_data/observations.py|80/80|27/42|87.7049%|
|school_data/repositories.py|8/8|0/0|100.0000%|
|school_data/repository_base.py|51/51|14/16|97.0149%|
|school_data/security_records.py|95/95|16/22|94.8718%|
|school_data/storage.py|48/49|15/16|96.9231%|
|school_data/time_units.py|26/26|14/14|100.0000%|
|school_data/trips.py|133/133|45/62|91.2821%|
|school_data/validation.py|39/39|16/16|100.0000%|
|school_navigation/__init__.py|0/0|0/0|100.0000%|
|school_navigation/cv.py|151/186|48/100|69.5804%|
|school_navigation/devices.py|137/146|33/54|85.0000%|
|school_navigation/engine.py|53/53|9/18|87.3239%|
|school_navigation/maps.py|29/30|11/20|80.0000%|
|school_navigation/replay.py|5/5|0/0|100.0000%|
|school_records/__init__.py|0/0|0/0|100.0000%|
|school_records/lists.py|62/62|33/38|95.0000%|
|school_records/paging.py|56/58|16/24|87.8049%|
|school_records/raw.py|54/56|27/44|81.0000%|
|school_records/recording.py|273/277|65/94|91.1051%|
|school_records/writes.py|114/115|24/38|90.1961%|
|school_resources/__init__.py|0/0|0/0|100.0000%|
|school_resources/api.py|122/123|97/108|94.8052%|
|school_resources/contexts.py|230/235|55/78|91.0543%|
|school_resources/files.py|170/177|55/88|84.9057%|
|school_resources/policy.py|63/64|23/28|93.4783%|
|school_resources/reads.py|91/125|34/62|66.8449%|
|server.py|238/311|113/152|75.8099%|
|simulation.py|40/44|14/18|87.0968%|
|solver.py|177/186|78/92|91.7266%|
|telemetry.py|120/133|21/30|86.5031%|
|trajectory.py|159/163|78/86|95.1807%|
|vehicle.py|59/63|19/24|89.6552%|
|vision_capture.py|107/127|33/58|75.6757%|
|vision_capture_worker.py|148/215|34/70|63.8596%|
|vision_contracts.py|156/171|69/92|85.5513%|
|vision_detector.py|0/26|0/2|0.0000%|
|vision_tracking.py|55/55|22/24|97.4684%|
|vision_validation.py|45/59|17/28|71.2644%|
|vision_workbench.py|141/152|41/64|84.2593%|

|JS plik|Linie %|V8blocks %|Functions %|
|---|---:|---:|---:|
|school_accounts/web/account.js|97.22|92.85|100.00|
|school_accounts/web/portal/api.mjs|100.00|98.24|100.00|
|school_accounts/web/portal/auth.mjs|100.00|94.20|83.33|
|school_accounts/web/portal/dates.mjs|94.73|100.00|100.00|
|school_accounts/web/portal/details.mjs|98.27|100.00|85.71|
|school_accounts/web/portal/devices.mjs|80.00|100.00|75.00|
|school_accounts/web/portal/dom.mjs|100.00|93.87|100.00|
|school_accounts/web/portal/drive_view.mjs|89.74|100.00|100.00|
|school_accounts/web/portal/driving.mjs|100.00|100.00|100.00|
|school_accounts/web/portal/filters.mjs|100.00|100.00|100.00|
|school_accounts/web/portal/forms.mjs|96.55|100.00|100.00|
|school_accounts/web/portal/laboratory.mjs|100.00|100.00|92.30|
|school_accounts/web/portal/lists.mjs|100.00|100.00|60.00|
|school_accounts/web/portal/navigation.mjs|100.00|100.00|100.00|
|school_accounts/web/portal/records.mjs|100.00|100.00|100.00|
|school_accounts/web/portal/role_views.mjs|64.03|100.00|76.19|
|school_accounts/web/portal/roles.mjs|100.00|100.00|100.00|
|school_accounts/web/portal/state.mjs|100.00|100.00|100.00|
|school_accounts/web/portal/validation.mjs|100.00|100.00|100.00|
|school_accounts/web/portal/vision.mjs|96.42|100.00|100.00|
|web/driver-ui.js|16.20|95.55|15.78|
|web/vision-workbench-ui.js|18.75|90.90|50.00|

Polecenia faktycznego odbioru (PowerShell,ten samworktree):

```powershell
$env:GW_PYTHON = (Resolve-Path artifacts/stage10/clean-env/Scripts/python.exe).Path
& $env:GW_PYTHON -m scripts.school_verify --output artifacts/stage10-review/python
$env:GW_BROWSER_CHANNEL = 'chromium'
$env:GW_TEST_OUTPUT = 'artifacts/stage10-review/chromium-verified'
npm run coverage:js
node tests/mobile_flow.cjs
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
.\android\GreenWaveSensor\gradlew.bat -p android/GreenWaveSensor testDebugUnitTest assembleDebug --no-daemon --offline --rerun-tasks
```

Raporty tylko ignorowane artifacts/stage10-review/python/python-tests.json/txt,
python-coverage.json/xml/txt i python-html;chromium-verified/browser-tests.json,
js-scope.json,js/coverage-final.json,coverage-summary.json,lcov.info,HTML.
JSprzebieg był uruchomiony npmruncoverage:js z przechwyceniem jawnego LASTEXITCODE,
a wewnętrzne statusy42unit i6suite sprawdzono niezależnie;sam próg nie maskujefailure.
Nie wprowadzono zmian migracji,solver/prediction/logger/raw formatów lublive gates.

### Stan końcowy korekty

**poprawki lokalne gotowe, oczekuje na push i weryfikację ci**.
Nie ma nowego zdalnego runu poprawionej wersji;ostatni odczyt API nadal wskazuje
wyłącznie38706404163/9395f1a/failure. Pełne zamknięcie etapu10 jest zablokowane
warunkiem zielonego rzeczywistegoCIpo pushu użytkownika. Nie wykonano push/merge,
nie przepisano historii,nie uruchomiono etapu11. Do szczegółowej diagnozy starego
Windows/Android nadal brak pełnych logówjob116326789802step7/job116326789656step4;
nie przypisujemy im niepotwierdzonych przyczyn. NoweCI udostępni diagnostykę wcześniej.

Commity korekty:e53c346(map/UTF8),f9a2c9b(overflow/matrix/SDK),1df0e3b(real401gate),
225b7e5(reuseSDKpackages),commitniniejszejdokumentacji przez
`git log -1 --format=%H -- docs/school-app/stage10.md`.
