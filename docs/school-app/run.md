# Uruchomienie aktualnej gałęzi GreenWave

Stan po etapie 4: działa bazowe GreenWave M8/CV oraz **osobny portal kont**.
Stary prototyp został usunięty; nowa implementacja kont ma SMTP, aktywację,
sesje i reset hasła. Przejazdy/GPS/CV nie są jeszcze podłączone do kont.
Bazowe polecenie z sekcji 2 uruchamia M8/CV, portal uruchamia sekcja 9.

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

Normalny checkout używa własnego data/runs i data/derived. To osobna lokalna aplikacja
badawcza; jej API nie jest serwerem kont z sekcji 9 ani wdrożeniem Docker.
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
[stages.md](stages.md): etap 3 zaakceptowany (2020b84d68ef3720c1b2d2345cf381c98a2a603b),
etap 4 przygotowany do odbioru. Etapy 5–12 Do zrobienia.
Działa portal kont (sekcja 9); pełna integracja domeny i M8/CV pozostaje na kolejne etapy.

## 7. Szkolna baza — maintenance CLI (etap 3)

Maintenance CLI przygotowuje bazę; serwer kont uruchamia osobne polecenie sekcji 9. Jawny nowy root
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


## 9. Portal kont i lokalna poczta demo — etap 4

Portal używa nowego jawnego runtime root. Profile demo jest wyłącznie lokalny
(HTTP/127.0.0.1) i dopuszcza adresy @example.test. Potrzebny Python>=3.11 ze scrypt;
bez pip dla aplikacji. Docker nie jest potrzebny; Mailpit/Docker deployment to etap 11.

**Terminal 1 — lokalny odbiornik SMTP i skrzynka operatora:**

```powershell
cd C:\Users\konra\.codex\worktrees\school-app\Surfy
python -m greenwave.school_accounts.demo_mail --smtp-port 1025 --web-port 8771
```

Otwórz http://127.0.0.1:8771. Odświeżaj stronę i kopiuj pełny link z wiadomości.
Skrzynka jest tylko w RAM, znika po restarcie, nie służy prawdziwym danym. Nie jest
publicznym endpointem portalu; wiadomość musi najpierw dotrzeć przez SMTP.
Zatrzymanie: Ctrl+C. Używaj tylko własnych adresów syntetycznych @example.test.

**Terminal 2 — przygotowanie nowej bazy i konfiguracji:**

```powershell
cd C:\Users\konra\.codex\worktrees\school-app\Surfy
$schoolAccountRoot = Join-Path (Get-Location) ('runtime\stage4-demo-' + [guid]::NewGuid().ToString('N'))
python -m greenwave.school_data --root "$schoolAccountRoot" init
python -m greenwave.school_data --root "$schoolAccountRoot" migrate
python -m greenwave.school_accounts secrets --output "$schoolAccountRoot\deployment-keys.json"

$env:SCHOOL_SECRET_FILE = "$schoolAccountRoot\deployment-keys.json"
$env:SCHOOL_PROFILE = 'demo'
$env:SCHOOL_PUBLIC_BASE_URL = 'http://127.0.0.1:8770'
$env:SCHOOL_ALLOWED_HOSTS = '127.0.0.1:8770'
$env:SCHOOL_SMTP_HOST = '127.0.0.1'
$env:SCHOOL_SMTP_PORT = '1025'
$env:SCHOOL_SMTP_MODE = 'plain'
$env:SCHOOL_SMTP_SENDER = 'greenwave@example.test'
$env:SCHOOL_SMTP_USER = ''
$env:SCHOOL_SMTP_PASSWORD = ''
```

Zachowaj wartość $schoolAccountRoot do kolejnych uruchomień. Nie generuj ponownie
kluczy nad istniejącym plikiem; polecenie odmawia nadpisania. Nowe GUID oznacza nową
bazę, a nie import wcześniejszych danych. Runtime/klucze/DB/mailbox nie trafiają do Git.
Public base URL, przeglądarka, Host i Origin muszą wskazywać ten sam adres.
Jeśli port zajęty, zmień jednocześnie port, PUBLIC_BASE_URL i ALLOWED_HOSTS.

**Opcjonalny pierwszy administrator, przed uruchomieniem serwera:**

```powershell
python -m greenwave.school_accounts bootstrap-admin --root "$schoolAccountRoot" --email admin@example.test --name "Administrator demo" --confirm-email-ownership
```

Wprowadź hasło dwukrotnie przez getpass (12–128 znaków,<=512B UTF-8). Nie podawaj
hasła w argv. Flagą potwierdzasz operatorsko własność adresu: konto ADMIN jest od
razu ACTIVE/verified. Drugi aktywny administrator nie zostanie zbootstrapowany.
Nie ma publicznego bootstrap API. Panel ról i innych kont pozostaje na etap 8.
Przy aktywnym portalu maintenance/bootstrap odmawia Busy — najpierw zatrzymaj swój serwer.

**Uruchomienie kont w tym samym terminalu:**

```powershell
python -m greenwave.school_accounts serve --root "$schoolAccountRoot" --host 127.0.0.1 --port 8770
```

Otwórz http://127.0.0.1:8770. Zatrzymanie Ctrl+C. Nie uruchamia migracji po cichu.
Restart używa tych samych kluczy i root; preauth trzeba odświeżyć, niewysłane
PENDING tokeny są unieważnione. Sesje mają idle30min/absolute8h; role/status/version
sprawdzane na żądaniach, brak auto-login po zmianie/resecie hasła.

### Ręczny przebieg bez zgadywania

1. Rejestracja: np. kierowca@example.test, nazwa, hasło12–128 Unicode i powtórzenie.
   Nie używaj realnego adresu. Odpowiedź jest neutralna również dla istniejącego email.
2. W skrzynce8771 odśwież, skopiuj link VERIFY do portalu. Adres po otwarciu traci
   fragment; samo GET nie aktywuje konta. Kliknij „Potwierdź aktywację”.
3. Zaloguj się wybranym hasłem; konto pokazuje własny email/nazwę/rolę, bez tabel,
   które nie zostały jeszcze podłączone. „Potwierdź tożsamość” wykonuje reauth.
4. „Wyloguj” kończy bieżącą sesję; „Wyloguj wszystkie sesje” kończy wszystkie.
5. Reset: „Reset hasła”, ten sam email, sprawdź nową wiadomość RESET w skrzynce.
   Otwórz link, podaj i powtórz nowe hasło, potwierdź. Zaloguj się ponownie nowym hasłem.
   Link jest jednorazowy, RESET15min/VERIFY24h; po ponownym żądaniu stary jest cofnięty.
6. „Zmień hasło”: obecne hasło, nowe i potwierdzenie. Sukces odcina wszystkie
   credentials; musisz zalogować się ponownie. Możesz wrócić do konta przyciskiem.

Limity: register5/IP/h; wspólny budżet aktywacji/resetu3/email/h i10/IP/h;
login5 błędów/email/15min i30 prób/IP/15min; reauth5/session/15min; tokenuse10/IP/15min.
429 ma Retry-After. Pełna kolejka lub błąd SMTP nie stanowi dowodu wysłania; startup
unieważnia utracone PENDING. Użytkownik może ponowić po cooldown; nie ma trwałego raw outbox.

### Profil z prawdziwymi danymi

Oddzielny root i sekret; SCHOOL_PROFILE=real, PUBLIC_BASE_URL=https://własna-domena,
exact ALLOWED_HOSTS, SMTP starttls/smtps z certverify i rzeczywisty nadawca/credentials
poza Git. Secure cookie jest obowiązkowe. DirectTLS: SCHOOL_TLS_CERT/SCHOOL_TLS_KEY;
albo jawny SCHOOL_TRUSTED_PROXY (IP lokalnego proxy), bind127.0.0.1 i HTTPS na proxy.
Proxy musi nadpisywać Host oraz Forwarded headers, nie przekazywać wartości klienta.
Bez zaufanego peer/proto w takim profilu odmowa; Forwarded od innych peer ignorowane.
Nie używaj lokalnego demo mailbox do realnych danych. To konfiguracja warstwy kont,
nie dowód wdrożenia realnego TLS/SMTP/Dockera — odbiór deploymentu pozostaje później.

### Testy etapu 4

```powershell
python -m unittest discover -s tests -p 'test_school_accounts*.py' -v
python -m unittest discover -s tests -p 'test_school_passwords.py' -v
python -m unittest discover -s tests -p 'test_school_data*.py' -v
New-Item -ItemType Directory -Path artifacts -Force | Out-Null
.venv-school/Scripts/python.exe -m coverage run --branch --source=greenwave.school_accounts,greenwave.school_data --data-file=artifacts/stage4.coverage -m unittest discover -s tests -p 'test_school*.py' -v
.venv-school/Scripts/python.exe -m coverage report --data-file=artifacts/stage4.coverage -m
python -m greenwave.school_accounts benchmark
```

Przeglądarka (Playwright i Edge; harness sam tworzy nową SQLite,SMTP i portal,
z produkcyjnym KDF, nie używa Twojej działającej instancji):

```powershell
$env:GW_PLAYWRIGHT_MODULE = 'C:/Users/konra/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
node scripts/check_school_accounts.cjs
```

Na innym komputerze dostosuj ścieżkę zainstalowanego Playwright lub pomiń zmienną,
jeśli moduł jest rozwiązywany jako playwright. Skrypt wymaga Edge headless.
Dowody, coverage per moduł i ograniczenia: [stage4.md](stage4.md).
Pełną regresję nadal uruchamiaj w izolowanym Git eksporcie z sekcji 3.
