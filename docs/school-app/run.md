# Uruchomienie aktualnej gałęzi GreenWave

Stan po implementacji warstwy danych etapu 3: działa **bazowe GreenWave M8/CV** z kodem
7ece859. Portal szkolny został usunięty decyzją użytkownika i nie jest jeszcze
zaimplementowany według [kontraktu v1](contract.md). Nie ma obecnie kont,
SMTP/resetu ani ról portalu; poniższa komenda nie udaje ich uruchomienia.

## 1. Worktree i gałąź

PowerShell:

```powershell
cd C:\Users\konra\.codex\worktrees\school-app\Surfy
git branch --show-current
git status --short
python --version
```

Oczekiwana gałąź: codex/school-app. Nie przełączaj main/vision-camera i nie
resetuj zmian, jeśli status nie jest pusty. Python>=3.11; bieżący smoke wykonano
Python3.14.4. Rdzeń używa biblioteki standardowej, bez obowiązkowego pip install.

## 2. Normalne uruchomienie bazy

```powershell
python -m greenwave --port 8767
```

Otwiera przeglądarkę: http://127.0.0.1:8767. Bez automatycznej przeglądarki:

```powershell
python -m greenwave --no-browser --port 8767
```

Jeżeli port zajęty, wybierz np.8768 albo `--port 0` (adres zostanie wypisany).
Opcje można sprawdzić:

```powershell
python -m greenwave --help
```

Symulacja/offline mapa działa bez telefonu/ADB/kamery/YOLO. Kamera/detektor
w Laboratorium są opcjonalne i wymagają właściwego środowiska/źródła/modelu.
Nie uruchamiają się samodzielnie. Native Android i USB opisuje istniejące
[phone-gps.md](../phone-gps.md); nie wykonywano fizycznego odbioru w tym etapie.
Rekomendacje live nadal wymagają zweryfikowanych danych niezależnie od UI.

Normalny checkout używa własnego data/runs i data/derived. To lokalna aplikacja
badawcza bez kont szkolnych, nie gotowy chroniony portal ani polecenie Docker.
Do prób/testów nagrywania używaj świeżego izolowanego eksportu opisanego poniżej.

Zatrzymanie: Ctrl+C w terminalu uruchomionego serwera; główny kod obsługuje
KeyboardInterrupt i zamyka aktywne nagranie. Przed końcem ręcznie zakończ zapis
w UI, jeśli zależy Ci na jawnym manifest/finish. Nie zamykaj innych serwerów.

## 3. Izolowany test bez prywatnych nagrań

Z katalogu worktree, eksportuj tylko śledzone źródła/konfiguracje; bez runtime,
data/runs i data/derived. Nie kopiuj lokalnych plików danych do eksportu.

```powershell
$gwExportRoot = Join-Path (Get-Location) ('artifacts\smoke-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $gwExportRoot | Out-Null
$gwExportZip = Join-Path $gwExportRoot 'source.zip'
$gwExportSource = Join-Path $gwExportRoot 'source'
git archive --format=zip --output=$gwExportZip HEAD greenwave tests scripts data android README.md requirements-vision.txt
Expand-Archive -LiteralPath $gwExportZip -DestinationPath $gwExportSource
Set-Location $gwExportSource
python -m greenwave --no-browser --port 0
```

Otwórz adres z terminala. Dane nagrania utworzone przez tę próbę są wyłącznie
w **eksporcie**, nie w prywatnych katalogach checkoutu. Zatrzymaj Ctrl+C.
Eksport HEAD odpowiada bieżącemu kodowi przy czystych źródłach; przy lokalnych
zmianach najpierw sprawdź różnicę zamiast ukrywać ją resetem. Nie używaj git clean
lub usuwania runtime do przygotowania testu.

## 4. Dostępne testy

Uruchamiaj z katalogu źródłowego eksportu, po zatrzymaniu serwera, poza browser
E2E wymagającymi osobnego działającego serwera eksportu.

```powershell
python -m unittest discover -s tests -p test_live_navigation.py -v
node --check greenwave/web/app.js
node --test tests/driver_ui.cjs tests/vision_workbench_ui.cjs
node tests/mobile_flow.cjs
```

Pełna regresja (aktualny wynik etapu 3: 274 testy OK, 1 jawny skip):

```powershell
python -m unittest discover -s tests -v
```

Opcjonalne browser E2E (Playwright i Edge, osobny syntetyczny serwer eksportu):

```powershell
$env:GW_TEST_URL = 'http://127.0.0.1:8767'
# Tylko gdy moduł nie jest dostępny jako playwright, podaj jego lokalną ścieżkę:
# $env:GW_PLAYWRIGHT_MODULE = 'C:/path/to/playwright'
node scripts/check_web.cjs
node scripts/check_driver_ui.cjs
```

Ustaw GW_TEST_URL zgodnie z faktycznym portem serwera eksportu, nie cudzej sesji.
Browser testy zmieniają symulację; nie uruchamiaj przeciw prywatnemu pomiarowi.
Test dekodera generuje własny klip, wymaga OpenCV:

```powershell
python -m scripts.check_capture
```

Android (dostępne, nie powtórzone w tym etapie):

```powershell
cd android\GreenWaveSensor
$env:ANDROID_HOME = 'C:/Users/konra/AppData/Local/Android/Sdk'
.\gradlew.bat testDebugUnitTest assembleDebug --no-daemon --offline
```

Dostosuj ANDROID_HOME do lokalnego SDK. Tkinter/loopback mogą być pomijane gdy
środowisko ich nie zapewnia; zależności i wyniki zawsze raportować oddzielnie.
Wąska usunięta konfiguracja coverage prototypu nie jest aktualnym kryterium;
szeroki plan i wyniki historycznego audytu: [audit.md](audit.md).

## 5. Historyczny smoke przeglądu etapu 2

Izolowany eksport pod artifacts/stage2-final-review/source, bez runtime i
prywatnych nagrań. Uruchomiono rzeczywiste CLI `python -m greenwave --no-browser
--port 0` jako proces testowy. Przez HTTP sprawdzono HTML/mapę/state,syntetyczny
start nagrania/start symulacji/pause/finish/ZIP oraz LIVE bez kwalifikowanych
danych (rekomendacja null,eligibility.allowed=false). Po finish zakończono
proces testowy. Wynik PASS;school.py nie istnieje. Metadane wyniku lokalnie
artifacts/stage2-final-review/smoke-result.json, bez tokenów/danych użytkownika.

Historyczne sprawdzenia etapu 2: --help OK;2 live_navigation tests OK;7 Node tests OK;
mobile_flow PASS;node --check app.js OK. Nie powtarzano pełnej regresji,builda
Androida,Playwright E2E ani YOLO/hardware. Nie mierzono nowego coverage.

## 6. Stan etapu szkolnego

[contract.md](contract.md): etap 2 zaakceptowany w 77c074cdc24eb14795eb8eb593167945d74eead4.
[stages.md](stages.md): etap 3 przygotowany do ponownego odbioru, etapy 4–12 Do zrobienia.
Nie istnieje działająca komenda uruchomienia portalu szkolnego według v1.
Migracje i repozytoria są zaimplementowane; login/SMTP/HTTP/UI wymagają kolejnych etapów.

## 7. Nowa szkolna baza — maintenance CLI (etap 3)

To działa już teraz i nie uruchamia loginu ani serwera portalu. Jawny nowy root
jest obowiązkowy; poniżej wyłącznie nowa baza syntetyczna, bez importu starego runtime:

```powershell
cd C:\Users\konra\.codex\worktrees\school-app\Surfy
$schoolStage3Root = Join-Path (Get-Location) ('runtime\stage3-cli-' + [guid]::NewGuid().ToString('N'))
python -m greenwave.school_data --root "$schoolStage3Root" init
python -m greenwave.school_data --root "$schoolStage3Root" status
python -m greenwave.school_data --root "$schoolStage3Root" migrate
python -m greenwave.school_data --root "$schoolStage3Root" backup "$schoolStage3Root\backups\manual.sqlite3"
python -m greenwave.school_data --root "$schoolStage3Root" restore "$schoolStage3Root\backups\manual.sqlite3"
python -m greenwave.school_data --root "$schoolStage3Root" status
```

Komendy sprawdzono: version/latest=2,current=true; ponowna migracja no-op;
restore pozostawił backups/before-restore-<time>.sqlite3 z poprzednim stanem.
DB w root/school.sqlite3; WAL/SHM i .school.lock są runtime, nie źródłami.
Backup nie nadpisuje istniejącej ścieżki; do kolejnego użyj innej nazwy.
Maintenance wymaga zamknięcia Database i dzierżawy; konflikt daje Busy/exit1,
sukces JSON/exit0. Nie usuwaj .school.lock w celu obchodzenia blokady.

Backup obejmuje tylko SQLite przez backup API (także zatwierdzony WAL), bez GPS,
manifestów czy CV. Restore waliduje wersję/checksum/integrity/FK, utrwala previous
snapshot i odmawia aktywnemu runtime. Poprzedni stan można przywrócić kolejnym
restore ze ścieżką previous. Wszystkie procesy dostępu do DB muszą respektować
Lease; nie zapisuj aktywnej DB z zewnętrznego narzędzia. Katalog operatora musi
mieć odpowiednie ACL. Publiczny portal jeszcze nie istnieje.

Testy danych można wykonać bez eksportu, używają tylko TemporaryDirectory:

```powershell
python -m unittest discover -s tests -p 'test_school_data*.py' -v
```

Coverage (istniejące środowisko .venv-school z coverage.py):

```powershell
New-Item -ItemType Directory -Path artifacts -Force | Out-Null
.venv-school/Scripts/python.exe -m coverage run --branch --source=greenwave.school_data --data-file=artifacts/stage3-review.coverage -m unittest discover -s tests -p 'test_school_data*.py' -v
.venv-school/Scripts/python.exe -m coverage report --data-file=artifacts/stage3-review.coverage -m
.venv-school/Scripts/python.exe -m coverage json --data-file=artifacts/stage3-review.coverage -o artifacts/stage3-review-coverage.json
```

Na nowym komputerze do opcjonalnego pomiaru (persistence nie wymaga pip):

```powershell
python -m venv .venv-school
.venv-school/Scripts/python.exe -m pip install coverage==7.13.1
```

Wynik: 48 testów, 1 jawny skip symlinka Windows; junction test wykonany PASS.
Coverage branch=True 94.4115% combined, linie98.5277%,gałęzie82.2148%.
To pomiar danych etapu 3, nie szeroki końcowy wynik aplikacji/JS.
Szczegóły i ograniczenia: [stage3.md](stage3.md). Pełną regresję wykonuj z
izolowanego eksportu sekcji3: `python -m unittest discover -s tests -v`.
Rdzeń nadal uruchamia się `python -m greenwave --no-browser --port 8767`.


## 8. Odbiór upgrade i restore starszej v1

Wyłącznie nowa syntetyczna historyczna baza, tworzona z niezmienionego SQL0001;
nie wskazuj starego runtime/school ani prywatnych danych:

```powershell
$schoolLegacyRoot = Join-Path (Get-Location) ('runtime\stage3-legacy-' + [guid]::NewGuid().ToString('N'))
python -c "import sys; from greenwave.school_data import Storage; from greenwave.school_data.migrations import migrate,load; migrate(Storage(sys.argv[1]),load()[:1])" "$schoolLegacyRoot"
python -m greenwave.school_data --root "$schoolLegacyRoot" status
python -m greenwave.school_data --root "$schoolLegacyRoot" backup "$schoolLegacyRoot\backups\v1.sqlite3"
python -m greenwave.school_data --root "$schoolLegacyRoot" migrate
python -m greenwave.school_data --root "$schoolLegacyRoot" restore "$schoolLegacyRoot\backups\v1.sqlite3"
python -m greenwave.school_data --root "$schoolLegacyRoot" status
python -m greenwave.school_data --root "$schoolLegacyRoot" migrate
python -m greenwave.school_data --root "$schoolLegacyRoot" status
```

Sprawdzono dokładnie te komendy: pierwszy status1/latest2/currentfalse; upgrade2;
restore zwraca schema.version1,currentfalse,po nim runtime odmawia startu aż do
migrate. Backup i restore respektują ciągłą historię/checksum/FK/integrity v1/v2,
odrzucają empty/unknown/future/corrupt DB. Before-migration i previous snapshots
pozostają do odzyskania wcześniejszego stanu. Nie migracja w trakcie importu/startu.

Bieżące czasy DB i zaufanego Actor są **integer UTC ms**, default now_ms adaptuje
time.time(); wstrzyknięty clock musi już zwracać integer ms. Migracja odcina sub-ms:
floor(Decimal(str(seconds))*1000),NULL zachowuje,invalid values rollback. Nie zmienia
GPS CSV ani formatu loggera: właściwy owned run-root/raw.csv. Filtry dat są [from,to)
w ms. Offset repozytorium to nie końcowy HTTP keyset cursor (etap6).

Regresje czterech napraw są częścią wszystkich school_data tests; można wybrać:

```powershell
python -m unittest discover -s tests -p 'test_school_data_migration_guard.py' -v
python -m unittest discover -s tests -p 'test_school_data_epoch_upgrade.py' -v
python -m unittest discover -s tests -p 'test_school_data_contract_boundaries.py' -v
```

Własna pełna Windows regresja274 OK,1skip. Niezależne Linux wyniki dla6c33649
zostały dostarczone przez użytkownika; brak Tkinter tam jest osobną zależnością,
nie usunięciem testu. Szczegóły [stage3.md](stage3.md).
