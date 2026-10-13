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

## 10. Etap 5 — chronione odczyty, syntetyczny odbiór ról

Konta etapu4 nadal działają według sekcji9. Nowe API odczytu jest podłączone,
ale docelowe tabele UI, tworzenie rekordów,share przez HTTP i telefon nie są
jeszcze podłączone. [stage5.md](stage5.md) zawiera dokładną allowlistę i granice.
Nie korzystaj ze starego runtime/school ani data/runs. Przykład poniżej tworzy
NOWY pusty runtime,syntetyczne raw.csv/CV i konta example.test. Serwer musi być
zatrzymany podczas operatorskich fixture/migracji (maintenance/runtime lease).
Fixture odmówi przy jakimkolwiek istniejącym koncie;nie importuje Twoich danych.

Terminal1 (tylko jeśli chcesz sprawdzić pocztę/reset,nie jest konieczny do odczytów):

```powershell
Set-Location C:\Users\konra\.codex\worktrees\school-app\Surfy
python -m greenwave.school_accounts.demo_mail --smtp-port 1025 --web-port 8771
```

Terminal2:

```powershell
Set-Location C:\Users\konra\.codex\worktrees\school-app\Surfy
git branch --show-current
git status --short
$schoolStage5Root = Join-Path (Get-Location) ('runtime\stage5-demo-' + [guid]::NewGuid().ToString('N'))
python -m greenwave.school_data --root "$schoolStage5Root" init
python -m greenwave.school_data --root "$schoolStage5Root" status
python -m greenwave.school_accounts secrets --output "$schoolStage5Root\deployment-keys.json"
python -m scripts.school_resource_fixtures --root "$schoolStage5Root" --confirm-synthetic
```

Wpisz przez getpass jedno własne hasło fixture(12–128 znaków) i confirmation.
CLI używa rzeczywistego scrypt N131072,nie słabszego testowego KDF.
Operator jawnie tworzy ACTIVE zweryfikowane syntetyczne konta:driver@example.test,
other@example.test,analyst@example.test,admin@example.test. To nie publiczna
rejestracja ani domyślne hasło. Rejestracja/SMTP aktywacja pozostaje sekcja9.
Skopiuj wypisane JSON IDs: trips.shared,private,other;observations.shared;captures.shared.

```powershell
$env:SCHOOL_SECRET_FILE = "$schoolStage5Root\deployment-keys.json"
$env:SCHOOL_PROFILE = 'demo'
$env:SCHOOL_PUBLIC_BASE_URL = 'http://127.0.0.1:8770'
$env:SCHOOL_ALLOWED_HOSTS = '127.0.0.1:8770'
$env:SMTP_HOST = '127.0.0.1'
$env:SMTP_PORT = '1025'
$env:SMTP_MODE = 'plain'
$env:SMTP_SENDER = 'greenwave@example.test'
$env:SMTP_USER = ''
$env:SMTP_PASSWORD = ''
python -m greenwave.school_accounts serve --root "$schoolStage5Root" --host 127.0.0.1 --port 8770
```

Otwórz http://127.0.0.1:8770. Formularz kont działa;po loginie nie udaje tabel.
Ctrl+C zatrzymuje ten serwer. Bazowy GreenWave pozostaje osobny:
`python -m greenwave --no-browser --port 8767`;testy bazowe wyłącznie w świeżym
izolowanym eksporcie z sekcji3,bez nagrywania w prywatnym checkout.

Terminal3 — rzeczywiste cookies/fetch równoważne PowerShell HTTP bez bearer:

```powershell
$schoolBase = 'http://127.0.0.1:8770/school/api/v1'
function New-SchoolLogin([string]$email) {
    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $pre = Invoke-RestMethod "$schoolBase/auth/preflight" -WebSession $session
    $secure = Read-Host 'Hasło syntetycznej fixture' -AsSecureString
    $credential = New-Object System.Management.Automation.PSCredential($email, $secure)
    $body = @{email=$email; password=$credential.GetNetworkCredential().Password} | ConvertTo-Json
    $result = Invoke-RestMethod "$schoolBase/auth/login" -Method Post -WebSession $session -ContentType 'application/json' -Headers @{Origin='http://127.0.0.1:8770';'X-CSRF-Token'=$pre.data.csrf} -Body $body
    return @{session=$session;csrf=$result.data.csrf}
}
$schoolDriver = New-SchoolLogin 'driver@example.test'
$schoolOther = New-SchoolLogin 'other@example.test'
$schoolAnalyst = New-SchoolLogin 'analyst@example.test'
$schoolAdmin = New-SchoolLogin 'admin@example.test'
$schoolOwn = Invoke-RestMethod "$schoolBase/trips" -WebSession $schoolDriver.session
$schoolShared = Invoke-RestMethod "$schoolBase/trips?scope=shared" -WebSession $schoolAnalyst.session
$schoolTrip = $schoolShared.data.items[0].id
Invoke-RestMethod "$schoolBase/trips/$schoolTrip" -WebSession $schoolDriver.session
Invoke-RestMethod "$schoolBase/observations?trip_id=$schoolTrip&scope=shared" -WebSession $schoolAnalyst.session
# Oczekiwane404;PowerShell pokazuje błąd HTTP,to pozytywny test odmowy:
Invoke-RestMethod "$schoolBase/trips/$schoolTrip" -WebSession $schoolOther.session
Invoke-RestMethod "$schoolBase/trips/$schoolTrip" -WebSession $schoolAdmin.session
Invoke-RestMethod "$schoolBase/trips/$schoolTrip/export" -WebSession $schoolAnalyst.session
# Owner-only ZIP w ignorowanym artifacts,bez prywatnych danych:
New-Item -ItemType Directory -Path artifacts -Force | Out-Null
Invoke-WebRequest "$schoolBase/trips/$schoolTrip/export" -WebSession $schoolDriver.session -OutFile artifacts/stage5-synthetic.zip
# Logout ->kolejneGET401:
Invoke-RestMethod "$schoolBase/auth/logout" -Method Post -WebSession $schoolDriver.session -ContentType 'application/json' -Headers @{Origin='http://127.0.0.1:8770';'X-CSRF-Token'=$schoolDriver.csrf} -Body '{}'
Invoke-RestMethod "$schoolBase/trips" -WebSession $schoolDriver.session
```

Odbiór raw/export:ZIP ma tylko metadata.json,raw.csv,complete.json;hashy nie zmienia.
Replay:POST trips/{id}/replays body {"mode":"GPS"},potemGET /replays/{id};
POST control {"command":"SEEK","value":1};DELETE {} zamyka handle.
Analysis:POST trips/{id}/analysis-jobs {"type":"GPS_QUALITY"},GET job aż COMPLETE,
GET trips/{id}/reports/{report_id}. Wszystkie POST/DELETE używają Origin i CSRF
bieżącej sesji jak przykład logout. Brak MAPPING/SIMULATION/capture start.
CV read:GET trips/{id}/cv/captures;GET /{capture}/events;GET /{capture}/media/0
z Range bytes=0-8 daje206 własnemu kontu. Fixture wideo to testowe bajty,nie film.
Analityk nie dostaje eksportu/CV nawet dla shared. ADMIN nie ma globalnego dostępu.
Share/revoke/archive/role/block przez UI/HTTP dopiero6/8;teraz sprawdza je test
wewnętrznego API+kolejneHTTP,nie publiczny provisioning endpoint.

Testy dokładnie używane w tym etapie:

```powershell
python -m unittest discover -s tests -p 'test_school_resources.py' -v
python -m unittest discover -s tests -p 'test_school*.py' -v
.venv-school/Scripts/python.exe -m coverage run --branch --source=greenwave.school_resources,greenwave.school_accounts,greenwave.school_data --data-file=artifacts/stage5-final.coverage -m unittest discover -s tests -p 'test_school*.py' -v
.venv-school/Scripts/python.exe -m coverage report --data-file=artifacts/stage5-final.coverage -m
.venv-school/Scripts/python.exe -m coverage json --data-file=artifacts/stage5-final.coverage -o artifacts/stage5-final-coverage.json
$env:GW_PLAYWRIGHT_MODULE = 'C:/Users/konra/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
node scripts/check_school_resources.cjs
node scripts/check_school_accounts.cjs
node --test tests/driver_ui.cjs tests/vision_workbench_ui.cjs
node tests/mobile_flow.cjs
```

Coverage pakietów etapowych nie zastępuje szerokiego zakresu etapu10.
Pełna regresja w eksporcie z sekcji3: `python -m unittest discover -s tests -v`.
Żadnych nowych sekretów,SQLite,nagrań,skrzynek ani coverage do Git.


### Ponowny odbiór etapu 5 — revoke i ponowny share

Nowy test na TemporaryDirectory nie czyta replay pomiędzy cofnięciem starego
udostępnienia a utworzeniem nowego. Zasilanie i revoke są wewnętrznym API,
nie publicznym provisioning ani przedwczesnym formularzem etapu6.

```powershell
python -m unittest discover -s tests -p 'test_school_share_contexts.py' -v
python -m unittest discover -s tests -p 'test_school*.py' -v
.venv-school/Scripts/python.exe -m coverage run --branch --source=greenwave.school_resources,greenwave.school_accounts,greenwave.school_data --data-file=artifacts/stage5-share-final.coverage -m unittest discover -s tests -p 'test_school*.py' -v
.venv-school/Scripts/python.exe -m coverage report --data-file=artifacts/stage5-share-final.coverage -m
```

Sprawdź stare read/control/close404,nowy replay200,własny replay200;queued oraz
running job po revoke→reshare CANCELLED bez nowego manifestu. Status/cancel
starego joba analityka404;właściciel status200 i cancel204. Stary grant nie zmienia się na nowy w żadnym kontekście.
Raport poprawnie opublikowany przed revokacją pozostaje właścicielowi;nowe
udostępnienie pozwala na świeży dozwolony odczyt raportu,ale nie starego joba.
Pełna regresja jak sekcja3 w nowym eksporcie. Bez zmian komend serwera,
schematu v2/14 tabel,poczty,formatu raw.csv ani warunków rekomendacji live.


### Końcowy odbiór owner management — status → revoke → status → cancel

Zatrzymany serwer i nowa syntetyczna fixture z sekcji10;nie importuj starych danych.
Revoke/share HTTP należy do etapu6,więc powtarzalny scenariusz używa wewnętrznego
repozytorium w izolowanym teście,a wszystkie status/cancel wykonywane są przez
rzeczywiste HTTP,cookies,Origin i CSRF:

```powershell
python -m unittest discover -s tests -p 'test_school_share_contexts.py' -k owner_status_reproducer -v
python -m unittest discover -s tests -p 'test_school_share_contexts.py' -v
python -m unittest discover -s tests -p 'test_school_resources.py' -v
python -m unittest discover -s tests -p 'test_school*.py' -v
.venv-school/Scripts/python.exe -m coverage run --branch --source=greenwave.school_resources,greenwave.school_accounts,greenwave.school_data --data-file=artifacts/stage5-owner.coverage -m unittest discover -s tests -p 'test_school*.py' -v
.venv-school/Scripts/python.exe -m coverage report --data-file=artifacts/stage5-owner.coverage -m
```

OwnerGET200 przed revoke,ownerGET200 po revoke i po regrant,ownerDELETE204.
AnalystGET/DELETE starego joba404,niezależnie od wcześniejszego owner odczytu.
Queued/running CANCELLED bez publikacji,completed COMPLETE/report_id zachowane.
Owner archived parent status200/cancel204 doTTL;nowa analiza archive409.
Other/adminforeign404,anonymous/expired/revoked401,DELETE badCSRF/Origin403.
Polecenia serwera/poczty i bazowego GreenWave nie zmieniają się. Nie ma nowego
provisioning/revoke/resume endpointu,nowych tabel ani trwałej historii jobów.


## 11. Etap 6 — zapis i powtarzalny odbiór HTTP

Nowy backend działa bez docelowych tabel UI, live, telefonu i kamery.
Użyj NOWEGO root, nie starego runtime/school ani prywatnego data/runs.
Schema v3 wymaga jawnego init/migrate; serve nie aktualizuje bazy po cichu.
W istniejącym dedykowanym szkolnym root upgrade wykonuje się przy zatrzymanym
serwerze i z automatycznym backupem SQLite, ale odbiór poniżej używa nowego root.

Terminal 1 — przygotowanie syntetycznego deploymentu:

```powershell
Set-Location C:\Users\konra\.codex\worktrees\school-app\Surfy
git branch --show-current
git status --short
$schoolStage6Root = Join-Path (Get-Location) ('runtime\stage6-demo-' + [guid]::NewGuid().ToString('N'))
python -m greenwave.school_data --root "$schoolStage6Root" init
python -m greenwave.school_data --root "$schoolStage6Root" migrate
python -m greenwave.school_data --root "$schoolStage6Root" status
python -m greenwave.school_accounts secrets --output "$schoolStage6Root\deployment-keys.json"
python -m scripts.school_resource_fixtures --root "$schoolStage6Root" --confirm-synthetic
```

Fixture wymaga pustej DB i getpass (12–128 znaków Unicode, maksymalnie 512 bajtów UTF-8).
Tworzy tylko syntetyczne konta example.test: driver, other, analyst, admin.
Operator podaje wspólne hasło tych fixture; brak domyślnego hasła i hasła w argv.
To skrypt operatorski, nie publiczny endpoint. Rejestracja/aktywacja SMTP: sekcja 9.

```powershell
$env:SCHOOL_SECRET_FILE = "$schoolStage6Root\deployment-keys.json"
$env:SCHOOL_PROFILE = 'demo'
$env:SCHOOL_PUBLIC_BASE_URL = 'http://127.0.0.1:8770'
$env:SCHOOL_ALLOWED_HOSTS = '127.0.0.1:8770'
$env:SMTP_HOST = '127.0.0.1'
$env:SMTP_PORT = '1025'
$env:SMTP_MODE = 'plain'
$env:SMTP_SENDER = 'greenwave@example.test'
$env:SMTP_USER = ''
$env:SMTP_PASSWORD = ''
python -m greenwave.school_accounts serve --root "$schoolStage6Root" --host 127.0.0.1 --port 8770
```

Poczta nie jest potrzebna do loginu aktywnych fixture i scenariusza rekordów.
Do register/reset uruchom w osobnym terminalu lokalny odbiornik z sekcji 9:
`python -m greenwave.school_accounts.demo_mail --smtp-port 1025 --web-port 8771`.

Terminal 2 w worktree — podaj przez getpass to samo hasło:

```powershell
python -m scripts.check_school_records --base-url http://127.0.0.1:8770
```

Skrypt wykonuje rzeczywisty HTTP z cookies/CSRF: login właściciela i analityka,
create, SIM start, observation, finish, read/export, edit, correction, filtry/keyset,
share/shared read, revoke/analyst 404, archive/owner read. Drukuje tylko PASS i
syntetyczny trip_id. Nie loguje haseł, cookies, CSRF ani tokenów. Nie obsługuje
arbitralnego zewnętrznego URL ani publicznego provisioningu.

Zatrzymaj serwer Ctrl+C w terminalu 1. Ponów tę samą komendę serve z tym samym
schoolStage6Root i env. W terminalu 2 podstaw wypisany trip_id:

```powershell
python -m scripts.check_school_records --base-url http://127.0.0.1:8770 --read-trip TU_WYPISANY_32_HEX_TRIP_ID
```

Login i odczyt archiwalnego trip po nowym boot powinny dać PASS, bez wznowienia jazdy.
Kill podczas nagrywania bez prawidłowego manifestu oznacza INTERRUPTED po startup.
Poprawny manifest po utracie DB commit pozwala na kontrolowane COMPLETE z audytem.
Szczegółowe testy awarii i podstawy autoryzacji: stage6.md.

Lista trips: route_id (logical_id ROUTE), status, archived, scope, sort=asc/desc,
limit (25, max 100), from/to RFC3339 ze strefą i cursor. Observations są globalne,
bez obowiązkowego trip_id; opcjonalne trip/route/signal/daty/efektywny kolor/typ/
source/valid/scope/sort/limit/cursor. Używaj urlencode lub URLSearchParams dla
offsetów (+02:00) i cursora. Query w ms i offset nie są akceptowane w tych listach.
Zmiana filtra wymaga nowego cursora.

CLI backup/restore DB przy zatrzymanym serwerze (nie obejmuje raw/mediów):

```powershell
$schoolStage6Backup = Join-Path $schoolStage6Root ('backups\manual-' + [guid]::NewGuid().ToString('N') + '.sqlite3')
python -m greenwave.school_data --root "$schoolStage6Root" backup "$schoolStage6Backup"
python -m greenwave.school_data --root "$schoolStage6Root" restore "$schoolStage6Backup"
python -m greenwave.school_data --root "$schoolStage6Root" migrate
python -m greenwave.school_data --root "$schoolStage6Root" status
```

Nie nadpisuj backupu; CLI odrzuca istniejący target. Nie kopiuj aktywnego pliku DB
przy WAL. Backup musi być w kontrolowanym root; restore zachowuje poprzednią DB.

Testy i pomiar (coverage 7.13.1 w tym środowisku; .venv-school według wcześniejszej
sekcji testów, nie dodawaj jej do Git):

```powershell
New-Item -ItemType Directory -Force -Path artifacts | Out-Null
python -m unittest discover -s tests -p 'test_school_records.py' -v
python -m unittest discover -s tests -p 'test_school*.py' -v
.venv-school/Scripts/python.exe -m coverage run --branch --source=greenwave.school_records,greenwave.school_resources,greenwave.school_accounts,greenwave.school_data,greenwave.telemetry --data-file=artifacts/stage6-accepted.coverage -m unittest discover -s tests -p 'test_school*.py' -v
.venv-school/Scripts/python.exe -m coverage report --data-file=artifacts/stage6-accepted.coverage -m
.venv-school/Scripts/python.exe -m coverage json --data-file=artifacts/stage6-accepted.coverage -o artifacts/stage6-accepted-coverage.json
$env:GW_PLAYWRIGHT_MODULE = 'C:/Users/konra/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
node scripts/check_school_resources.cjs
node scripts/check_school_accounts.cjs
node --test tests/driver_ui.cjs tests/vision_workbench_ui.cjs
node tests/mobile_flow.cjs
```

Pełna regresja Python tylko w nowym git eksporcie (sekcja 3):
`python -m unittest discover -s tests -v`.
Bazowy GreenWave pozostaje odrębną lokalną aplikacją:
`python -m greenwave --no-browser --port 8767`; smoke/nagrania testowe tylko w eksporcie.
Nie ma pełnej nav/live/Android/CV ani UI rekordów — odpowiednie etapy 7–9.

## 12. Etap 6 — odbiór cleanup nieudanego startu

Nie wstrzykuj awarii w prywatnym lub działającym deployment. Dokładny reproduktor
jest automatycznym scenariuszem prawdziwego HTTP z nową tymczasową SQLite i plikami:

```powershell
Set-Location C:\Users\konra\.codex\worktrees\school-app\Surfy
python -m unittest discover -s tests -p test_school_records.py -k failed_start_storage_run -v
python -m unittest discover -s tests -p test_school_records.py -k failed_start -v
python -m unittest discover -s tests -p test_school_records.py -v
```

Pierwszy test potwierdza STARTING/PENDING wewnątrz storage.run przed OSError,
neutralne 503, następnie INTERRUPTED/FAILED oraz start drugiego użytkownika 201
bez restartu. Pozostałe sprawdzają konstruktor, częściowe pliki/append, rollback
RECORDING, close failure, DB cleanup failure, rzeczywisty watchdog i startup recovery.
Jeżeli DB cleanup nadal nie działa, rezerwacja pozostaje i drugi start daje 409.
Po ustąpieniu błędu retry kończy cleanup bez dublowania audytu. Retry nieudanego
START nie wznawia jazdy; należy utworzyć nowy PLANNED trip.

Nie dodano publicznego endpointu naprawczego. Normalny ręczny HTTP scenariusz oraz
start/stop/backup/testy/coverage są nadal w sekcji 11. Fault tests nie wymagają
telefonu, kamery ani modyfikacji uprawnień prywatnych katalogów.

Pomiar poprawki, taki sam zakres jak w etapie 6, bez wyłączeń nowych ścieżek:

```powershell
New-Item -ItemType Directory -Force -Path artifacts | Out-Null
.venv-school/Scripts/python.exe -m coverage run --branch --source=greenwave.school_records,greenwave.school_resources,greenwave.school_accounts,greenwave.school_data,greenwave.telemetry --data-file=artifacts/stage6-start.coverage -m unittest discover -s tests -p 'test_school*.py' -v
.venv-school/Scripts/python.exe -m coverage report --data-file=artifacts/stage6-start.coverage -m
.venv-school/Scripts/python.exe -m coverage json --data-file=artifacts/stage6-start.coverage -o artifacts/stage6-start-coverage.json
```

Pełna regresja w nowym eksporcie (nie uruchamiaj jej na prywatnych nagraniach):

```powershell
$schoolStartReviewRoot = Join-Path (Get-Location) ('artifacts\stage6-start-review-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path "$schoolStartReviewRoot\source" | Out-Null
git archive HEAD --output="$schoolStartReviewRoot\source.tar"
if ($LASTEXITCODE -ne 0) { throw 'git archive failed' }
tar -xf "$schoolStartReviewRoot\source.tar" -C "$schoolStartReviewRoot\source"
if ($LASTEXITCODE -ne 0) { throw 'tar failed' }
Push-Location "$schoolStartReviewRoot\source"
try { python -m unittest discover -s tests -v } finally { Pop-Location }
```

Testy JS/browser: komendy z sekcji 11. Nie trzeba zmieniać istniejącej konfiguracji
serwera lub dodawać narzędzia HTTP do naprawy runtime. Akceptacja nowych stanów i
granic jest opisana w końcowej sekcji stage6.md.

## 13. Etap 7 — pełny ręczny odbiór interfejsu

Frontend jest vanilla JS/ES modules, nie wymaga npm ani bundlera do uruchomienia.
Użyj nowego syntetycznego root. Portal nie importuje starych kont/nagrań. Konto
analityka i administratora ma własne dane; dodatkowe ekrany ról działają od etapu 8.

Terminal 1, PowerShell:

```powershell
Set-Location C:\Users\konra\.codex\worktrees\school-app\Surfy
git branch --show-current
git status --short
$schoolStage7Root = Join-Path (Get-Location) ('runtime\stage7-demo-' + [guid]::NewGuid().ToString('N'))
python -m greenwave.school_data --root "$schoolStage7Root" init
python -m greenwave.school_data --root "$schoolStage7Root" status
python -m greenwave.school_accounts secrets --output "$schoolStage7Root\deployment-keys.json"
python -m scripts.school_resource_fixtures --root "$schoolStage7Root" --confirm-synthetic
$env:SCHOOL_SECRET_FILE = "$schoolStage7Root\deployment-keys.json"
$env:SCHOOL_PROFILE = 'demo'
$env:SCHOOL_PUBLIC_BASE_URL = 'http://127.0.0.1:8770'
$env:SCHOOL_ALLOWED_HOSTS = '127.0.0.1:8770'
$env:SMTP_HOST = '127.0.0.1'
$env:SMTP_PORT = '1025'
$env:SMTP_MODE = 'plain'
$env:SMTP_SENDER = 'greenwave@example.test'
$env:SMTP_USER = ''
$env:SMTP_PASSWORD = ''
python -m greenwave.school_accounts serve --root "$schoolStage7Root" --host 127.0.0.1 --port 8770
```

Fixture pyta getpass i confirmation, bez hasła w argv/default hasła. Tworzy cztery
aktywne syntetyczne konta: driver/other/analyst/admin@example.test z podanym hasłem.
To operator CLI na PUSTEJ DB, nie publiczne HTTP. Nie używaj tej fixture dla realnych
osób. Zakończenie serwera: Ctrl+C. Upgrade istniejącego właściwego szkolnego root
przy zatrzymanym serwerze: `python -m greenwave.school_data --root <root> migrate`.

Dla rejestracji/aktywacji/resetu uruchom w terminalu 2 lokalny odbiornik:

```powershell
python -m greenwave.school_accounts.demo_mail --smtp-port 1025 --web-port 8771
```

Portal: http://127.0.0.1:8770; syntetyczna skrzynka operatora: http://127.0.0.1:8771.
Nie zapisuj screenshotów skrzynki/linków do dokumentacji. Realne dane wymagają
HTTPS/Secure cookies/prawidłowej poczty zgodnie z sekcją 9, nie profilu demo.

Ręczny scenariusz:

1. Login driver@example.test, zobacz Konto; menu Moje przejazdy/Moje obserwacje.
2. Nowy przejazd: tytuł/notatka, SIM, opcjonalna dozwolona wersja trasy. Zwykła
   fixture nie ma opublikowanych ROUTE, można wybrać Bez trasy.
3. Szczegóły → Rozpocznij zapis syntetyczny → Obserwacja pasażera. Przy Bez trasy
   podaj np. synthetic-light, RED, STATE_SEEN. UNKNOWN + STATE_START ma błąd.
4. Zakończ zapis; status Ukończony. Eksport pobiera rzeczywisty ZIP. HEAD najpierw
   sprawdza prawa/integralność bez tworzenia ZIP; GET sprawdza je ponownie.
5. Edytuj metadane. W drugiej karcie zmień ten sam rekord, a w pierwszej spróbuj
   stary revision: zobacz aktualny rekord i świadomie wybierz nowy revision.
6. Historia / korekta → GREEN + powód. Oryginał RED pozostaje; historia pokazuje
   autora/czas/przed/po. Adnotacja historyczna nie dopisuje do ukończonego raw.
7. Obie tabele: filtry dnia (Europe/Warsaw), trasy, statusu/archiwum lub sygnalizatora,
   efektywnego koloru/typu/valid/source; sort i kolejne strony przy >25 rekordach.
   Zmiana filtra usuwa stary cursor. Tabela telefonu ma własny poziomy scroll.
8. Udostępnij complete trip analyst@example.test; jasna informacja o GPS. Cofnij
   konkretną zgodę. Stare okno nie cofa nowszego share. Nie ma EXPORT/CV checkboxów.
9. Archiwizuj z powodem i potwierdzeniem; odczytaj przez filtr Archiwalne.
10. Wyloguj; zaloguj other@example.test: brak list/szczegółów/filtrów starego konta.
11. Konto: reauth, change-password i logout-all. Register/verify/reset według sekcji 9.
12. Przetestuj Escape, Tab/Shift+Tab, przywrócenie focus dialogu, 1360/390/320 px.

Po timeout nie twórz automatycznie nowego START z innym kluczem. Ponów świadomie
identyczne żądanie; po INTERRUPTED potrzebny nowy trip. Pełny reload usuwa pamięciowy
uchwyt nawigacji; obecne API nie odtwarza go, wylogowanie kończy zapis na serwerze.

Jednostkowe JS, V8 coverage oraz odpowiednia regresja HTTP:

```powershell
New-Item -ItemType Directory -Force -Path artifacts | Out-Null
node --test --experimental-test-coverage --test-coverage-include="**/portal/state.mjs" --test-coverage-include="**/portal/api.mjs" --test-coverage-include="**/portal/dates.mjs" --test-coverage-include="**/portal/filters.mjs" --test-coverage-include="**/portal/validation.mjs" tests/school_portal.cjs
python -m unittest discover -s tests -p test_school_ui_static.py -v
python -m unittest discover -s tests -p 'test_school_accounts*.py' -v
python -m unittest discover -s tests -p test_school_resources.py -v
node --test tests/driver_ui.cjs tests/vision_workbench_ui.cjs
node tests/mobile_flow.cjs
```

Browser wymaga Playwright jako narzędzia testowego i zainstalowanego Edge. W tym
środowisku dostępny jest moduł bundlowanego runtime; na innym komputerze wskaż jego
lokalną instalację przez GW_PLAYWRIGHT_MODULE (nie jest zależnością produkcyjnego UI).

```powershell
$env:GW_PLAYWRIGHT_MODULE = 'C:/Users/konra/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
node scripts/check_school_ui.cjs
node scripts/check_school_accounts.cjs
node scripts/check_school_resources.cjs
```

Opcjonalne przygotowanie testowego Playwright na innym komputerze (Node 24/Edge),
wyłącznie w ignorowanym artifacts, bez dodawania dependency do aplikacji:

```powershell
npm install --prefix artifacts/browser-tools playwright
$env:GW_PLAYWRIGHT_MODULE = Join-Path (Get-Location) 'artifacts\browser-tools\node_modules\playwright'
node scripts/check_school_ui.cjs
```

Ta opcjonalna instalacja nie była wykonywana tutaj — użyto istniejącego runtime.
Browser skrypt tworzy nową tymczasową DB/SMTP, używa realnego KDF i testuje trzy
rozmiary przy browser timezone America/New_York. Generuje rzeczywiste screenshoty
w docs/school-app/screenshots; nie zapisuje haseł/tokenów/mailboxa. Raporty tymczasowe
w artifacts nie trafiają do Git. Wyniki i jawny zakres coverage: stage7.md.


## 14. Etap8 — odbiór trzech ról

Vanilla JS, bez nowego frameworka/bundlera. Świeży root, serwer zatrzymany przy init.
Nie wskazuj starego runtime/school, data/runs albo prywatnych nagrań.

```powershell
Set-Location C:\Users\konra\.codex\worktrees\school-app\Surfy
git branch --show-current
git status --short
$schoolStage8Root = Join-Path (Get-Location) ('runtime\stage8-demo-' + [guid]::NewGuid().ToString('N'))
python -m greenwave.school_data --root "$schoolStage8Root" init
python -m greenwave.school_data --root "$schoolStage8Root" status
python -m greenwave.school_accounts secrets --output "$schoolStage8Root\deployment-keys.json"
python -m scripts.school_resource_fixtures --root "$schoolStage8Root" --confirm-synthetic
$env:SCHOOL_SECRET_FILE = "$schoolStage8Root\deployment-keys.json"
$env:SCHOOL_PROFILE = 'demo'
$env:SCHOOL_PUBLIC_BASE_URL = 'http://127.0.0.1:8770'
$env:SCHOOL_ALLOWED_HOSTS = '127.0.0.1:8770'
$env:SMTP_HOST = '127.0.0.1'
$env:SMTP_PORT = '1025'
$env:SMTP_MODE = 'plain'
$env:SMTP_SENDER = 'greenwave@example.test'
$env:SMTP_USER = ''
$env:SMTP_PASSWORD = ''
python -m greenwave.school_accounts serve --root "$schoolStage8Root" --host 127.0.0.1 --port 8770
```

Fixture jest wewnętrznym operatorskim CLI na PUSTEJ syntetycznej DB. Pyta getpass i
confirmation, nie ma hasła w argv ani publicznego provisioning HTTP. Tworzy
`driver@example.test`, `other@example.test`, `analyst@example.test`, `admin@example.test`
z wybranym hasłem i syntetycznymi ukończonymi przejazdami. Ma MODEL draft/published
zgodne ze schematem domenowym. Nie podłącza kamery ani YOLO. Nie używaj dla realnych osób.
Ctrl+C zatrzymuje serwer. Dla register/reset w osobnym terminalu:

```powershell
python -m greenwave.school_accounts.demo_mail --smtp-port 1025 --web-port 8771
```

Portal http://127.0.0.1:8770, skrzynka operatora http://127.0.0.1:8771.
Realny profil wymaga HTTPS/Secure cookies/SMTP TLS jak w sekcji9. Istniejący właściwy
root aktualizuj wyłącznie przy zatrzymanym serwerze przez `school_data --root <root> migrate`.
Bazowy GreenWave pozostaje osobną lokalną aplikacją: `python -m greenwave`; nowy portal
nie przekazuje do niej HTTP. Nie uruchamiaj zapisu bazowego GreenWave na prywatnych
katalogach podczas szkolnego odbioru.

Scenariusz ręczny, najlepiej osobne profile/incognito przeglądarek:

1. DRIVER: własne tabele/konto i PUBLISHED konfiguracje; bez menu Konta/Audyt/Draft.
   Bezpośrednie `/school/api/v1/admin/users` daje403; anonim daje401.
2. ANALYST: Udostępnione przejazdy → Synthetic shared → obserwacja/historia.
   Nie ma edit/correct/share/archive/export/CV. Query jest scope=shared.
3. Laboratorium: Otwórz GPS replay, Play/Pause, seek0, rate2, Zamknij. Zleć GPS_QUALITY;
   poczekaj COMPLETE, rozwiń raport, sprawdź metryki/jednostki. Anulowanie nie usuwa
   wcześniej opublikowanego raportu. Nie ma rekomendacji live.
4. DRIVER cofa zgodę w szczegółach. Otwarty widok analityka usuwa dane przy następnym
   sprawdzeniu. Ponowne share nie ożywia starego replay/joba; nowy kontekst działa.
   Właściciel nadal ma dozwolone status/cancel joba.
5. ANALYST → Konfiguracje → Nowy draft MODEL. Podaj logical_id, reason, popraw settings.
   DRAFT edytujesz z revision; nie możesz publikować lub zmieniać cudzego draft.
   Szablony ROUTE/SIGNAL w edytorze JSON zawierają nazwane pola z jednostkami domeny.
   Celowo błędny JSON, fazy lub nested verified zostają odrzucone.
6. ADMIN → Konto → Potwierdź tożsamość hasłem. Konfiguracje → DRAFT → szczegóły →
   Opublikuj z powodem. DRIVER widzi PUBLISHED; opis mówi, że to nie weryfikacja terenowa.
   Zmiany wymagają nowej wersji; archive nie kasuje historycznego payloadu.
7. ADMIN → Konta → Zarządzaj kontem other. Zmień rolę z powodem. Stara sesja other
   dostaje401. Zaloguj other ponownie, zablokuj konto; następny odczyt ponownie401.
   Unblock nie przywraca wcześniejszych credentials/grants. PENDING nie aktywuje się
   zwykłym unblock. Degradacja/blokada ostatniego aktywnego ADMIN daje409.
8. Po >5 minutach bez reauth mutacja daje REAUTH_REQUIRED. Potwierdź hasło w Koncie,
   wróć do panelu i świadomie ponów; żądanie nie wykonuje się automatycznie.
9. Konflikt revision w dwóch kartach: zobacz aktualny rekord/payload, świadomie
   przyjmij revision i zapisz ponownie. Nie nadpisuj automatycznie zmian.
10. Audit: filtrowanie dat/akcji/actor, kolejne strony; rozwijany pełny powód. Brak
    prywatnych powodów korekt, GPS i sekretów. Tab/Shift+Tab/Escape/focus restore,
    1360×900,390×844,320px, lokalny scroll tabel i długie dane.

Komendy testów:

```powershell
python -m unittest discover -s tests -p test_school_admin.py -v
python -m unittest discover -s tests -p 'test_school*.py' -v
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/school_roles.cjs tests/school_portal.cjs
node --test --experimental-test-coverage --test-coverage-include="**/portal/roles.mjs" --test-coverage-include="**/portal/state.mjs" --test-coverage-include="**/portal/api.mjs" --test-coverage-include="**/portal/dates.mjs" --test-coverage-include="**/portal/filters.mjs" --test-coverage-include="**/portal/validation.mjs" tests/school_roles.cjs tests/school_portal.cjs
.\.venv-school\Scripts\python.exe -m coverage run --branch --source=greenwave.school_admin,greenwave.school_accounts,greenwave.school_data,greenwave.school_resources,greenwave.school_records,greenwave.telemetry -m unittest discover -s tests -p 'test_school*.py' -v
.\.venv-school\Scripts\python.exe -m coverage report -m
$env:GW_PLAYWRIGHT_MODULE = 'C:/Users/konra/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
node scripts/check_school_roles.cjs
$env:GW_SCREENSHOT_ROOT = 'artifacts/stage8-stage7-regression'
node scripts/check_school_ui.cjs
node scripts/check_school_accounts.cjs
node scripts/check_school_resources.cjs
node --test tests/driver_ui.cjs tests/vision_workbench_ui.cjs
node tests/mobile_flow.cjs
```

Coverage wymaga środowiska z pakietem coverage (istniejące .venv-school lub
`python -m venv .venv-school`, potem pip install coverage). Node24 i Playwright/Edge
jak w sekcji13, wyłącznie narzędzia testowe. E2E tworzą własne tymczasowe SQLite/SMTP,
nie potrzebują uruchomionego serwera ani publicznego test endpointu. Nowe role screenshoty:
`docs/school-app/screenshots/stage8-{desktop,phone}-{analyst,admin,configs,audit}.png`.
GW_SCREENSHOT_ROOT pozwala zachować zaakceptowane screenshoty etapu7 podczas regresji.
Pełna regresja w tym etapie jest wykonana w izolowanym eksporcie kodu bez runtime/data/runs;
wyniki, zakres coverage i pominięcia w stage8.md. Etap9 nie rozpoczęty.
