# Uruchomienie aktualnej gałęzi GreenWave

Stan po doprecyzowaniu etapu 2: działa **bazowe GreenWave M8/CV** z kodem
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

Pełna regresja istnieje, ale nie była powtarzana przy tym doprecyzowaniu dokumentów:

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

## 5. Faktyczny smoke tego przeglądu

Izolowany eksport pod artifacts/stage2-final-review/source, bez runtime i
prywatnych nagrań. Uruchomiono rzeczywiste CLI `python -m greenwave --no-browser
--port 0` jako proces testowy. Przez HTTP sprawdzono HTML/mapę/state,syntetyczny
start nagrania/start symulacji/pause/finish/ZIP oraz LIVE bez kwalifikowanych
danych (rekomendacja null,eligibility.allowed=false). Po finish zakończono
proces testowy. Wynik PASS;school.py nie istnieje. Metadane wyniku lokalnie
artifacts/stage2-final-review/smoke-result.json, bez tokenów/danych użytkownika.

Sprawdzenia bieżące: --help OK;2 live_navigation tests OK;7 Node tests OK;
mobile_flow PASS;node --check app.js OK. Nie powtarzano pełnej regresji,builda
Androida,Playwright E2E ani YOLO/hardware. Nie mierzono nowego coverage.

## 6. Stan etapu szkolnego

[contract.md](contract.md): ustalony zakres do końcowego odbioru.
[stages.md](stages.md): etap2 „Przygotowany do końcowego odbioru”,etapy3–12
„Do zrobienia”. [ai-usage.md](ai-usage.md): prompty i rzeczywiste działania.
Nie istnieje działająca komenda uruchomienia portalu szkolnego według v1.
Przejście do migracji/backendu wymaga kolejnego promptu użytkownika.
