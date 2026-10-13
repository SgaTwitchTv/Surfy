# Etap 6 — przejazdy, obserwacje i trwały zapis

**Przygotowany do odbioru**, 2026-10-13. Zaakceptowana baza etapu 5:
**13858b06051a4183bfc7e0559962611c8be2eae2**.
Worktree: `C:/Users/konra/.codex/worktrees/school-app/Surfy`, `codex/school-app`.
Na wejściu HEAD był zgodny, status i staging puste. Przeczytano obowiązujący
pusty AGENTS oraz contract, stage3–5, stages, run i ai-usage. Nie czytano prywatnego
`data/runs/` ani starego `runtime/school/`, nie importowano danych. Nie zmieniono
main, vision-camera, solvera, predykcji ani warunków rekomendacji live.
PUBLISH-01 pozostaje osobnym problemem historycznej publikacji.

## Zakres i architektura

Nowy pakiet `greenwave.school_records` zawiera:

- `writes.py`: walidację, operacje zapisu, idempotency i audyt;
- `lists.py`, `paging.py`: listy ograniczone uprawnieniami, RFC3339 i keyset;
- `recording.py`: trwałe intencje, pojedynczą rezerwację i recovery;
- `raw.py`: kontrolowane odczyty i weryfikację integralności RunLoggera.

`Repository.atomic` wiąże metody repozytorium z jednym połączeniem. Dane i audyt
SQLite commitują lub rollbackują razem. Sesja i Actor są sprawdzane na tym samym
połączeniu przed zapisem; request_id nadaje serwer. HTTP ma jawne trasy, bez
przekazywania do odziedziczonego Handlera.

Backend zapisów działa bez docelowych tabel UI. Z etapu 9 podłączono jedynie
konieczny zakres kontraktu M01/M02/M03: SIMULATION start, status i FINISH.
Powstaje jawnie syntetyczny, stacjonarny ślad: RUN_START, TELEMETRY z prędkością
0 i pozycją 0 (bez GPS), ręczne zdarzenia, RUN_END. Nie jest to pełny silnik
nawigacji lub symulacji. PAUSE/RESUME, mapa, telefon, live i kamera pozostają
na etap 9; UI użytkownika i role na 7–8. Demo zapisu nie wymaga ADB ani YOLO.
Konta, publikacja konfiguracji i korekty nie nadają wiarygodności światłom.

## Endpointy i pola formularzy

Prefix: **/school/api/v1**. Mutacje wymagają aktualnej sesji, CSRF i dokładnego
Origin. Właściciel i rola wynikają wyłącznie z DB, nie z danych klienta.

| Metoda i ścieżka | Pola | Wynik |
|---|---|---|
| POST /trips | title (1–120), mode (SIMULATION/LIVE), note? (0–1000), route_version_id? | 201; LIVE wymaga opublikowanej ROUTE, ale start LIVE jest niedostępny |
| PATCH /trips/{id} | expected_revision; title? lub note?, co najmniej jedno | 200; 409 dla starej revision lub archiwum |
| DELETE /trips/{id} | expected_revision, reason (3–500) | 204; archiwizacja PLANNED/COMPLETE/INTERRUPTED, bez usunięcia danych |
| POST /trips/{id}/observations | signal_id, state, event_type, source_event_id (1–128) | 201; 202 przy zachowanym fakcie i FAILED journaling |
| POST /observations/{id}/corrections | expected_revision >= 0, client_operation_id (32–64), changes: state?/event_type?/valid?, reason (3–500) | 201; osobna korekta i efektywna obserwacja |
| POST /trips/{id}/share | analyst_email | 201 READ_ANALYZE; limit 10 prób/użytkownika/godzinę |
| DELETE /trips/{id}/share | expected_share_id | 204; stary revoked ID nie cofa nowego grantu |
| POST /navigation | trip_id; nagłówek Idempotency-Key (32–64) | 201; tylko SIM, druga aktywna jazda 409 |
| GET /navigation/{id} | — | 200; kontekst związany z sesją, credential i właścicielem |
| POST /navigation/{id}/control | command=FINISH, expected_revision; Idempotency-Key | 200 COMPLETE po rzeczywistej finalizacji |

Dodano 10 kombinacji metoda/ścieżka; razem działa 30 tras zasobów z etapem 5.
Listy GET /trips i /observations zastępują przejściowe listy etapu 5. Konta,
SMTP i reauth nadal działają. Dziedziczone /api/*, urządzenia, parowanie, live,
capture, administracja i mutacje konfiguracji pozostają niedostępne.
Nie ma publicznego endpointu testowego ani provisioningu.

Błędy: 401 anonimowa/wygasła/cofnięta sesja; 404 brak/cudze prywatne ID;
409 revision/stan/idempotency; 422 walidacja formularza; 400 błędny JSON/cursor;
403 CSRF/Origin/rola; 503 błąd DB lub I/O. Bool nie zastępuje liczby. Nieznane
lub duplikowane pola oraz NaN/Infinity są odrzucane. DTO nie zawierają hashów,
sekretów ani ścieżek filesystem. Właściciel widzi aktywny share_id przy GET trip,
aby po odświeżeniu móc cofnąć konkretną zgodę; analityk nie dostaje tego pola.

## Obserwacje, korekty i uprawnienia

Ręczny formularz ma źródło MANUAL nadawane przez serwer; podszycie pod CV daje
422. server_received_at nadaje serwer, measured_at w tym formularzu jest NULL.
Obserwacja aktywnej jazdy wymaga jej właściwej sesji. Adnotacja COMPLETE lub
INTERRUPTED jest historyczna i nie dopisuje raw. UNKNOWN nie może być STATE_START.
Korekta dotyczy wyłącznie state/event_type/valid, zawiera autora, czas, powód,
before/after i revision. Oryginały, GPS, czasy i raw pozostają niezmienne.
Archiwizacja jest czytelna dla właściciela, nie ma fizycznego delete ani restore API.

Wszystkie aktywne role mają własne dane. DRIVER nie widzi cudzych. ANALYST może
czytać i analizować COMPLETE niearchiwalny przejazd z aktualnym READ_ANALYZE,
ale nie eksportować lub czytać CV. ADMIN nie ma wyjątku dla cudzych danych.
Udostępnienie jest pojedynczym grantem do aktywnego analityka po dokładnym emailu;
nie istnieje wyszukiwarka kont. Błąd odbiorcy jest neutralny. Cofnięcie i archiwizacja
proaktywnie unieważniają replay/jobs według konkretnego share_id. Regrant nie
odtwarza starych kontekstów. Właściciel nadal ma status/cancel istniejącego joba,
bez przejęcia jego pierwotnej podstawy wykonania. Kontrola publikacji pozostaje
serializowana z revokacją przez BEGIN IMMEDIATE.

## Filtry, daty i cursory

GET /trips: from, to, route_id, status, archived=true/false, scope=own/shared,
sort=asc/desc, limit, cursor. route_id to logical_id ROUTE, obejmujący jej wersje.
GET /observations: wszystkie przejazdy w danym scope, bez obowiązkowego trip_id;
opcjonalne trip_id, route_id, signal_id, from, to, state, event_type, source,
valid, scope, sort, limit, cursor. Kolor, typ i valid dotyczą efektywnej wartości
ostatniej korekty. Opcjonalny trip_id nadal wymaga dostępu do parent trip (404).
Listy wynikają z DB, nie ze skanowania nagrań.

Daty API to RFC3339 z T i wymaganą strefą (Z lub offset), ułamek 1–6 cyfr.
Konwersja do INTEGER UTC epoch milliseconds odcina mikrosekundy poniżej ms.
Przedział [from,to), from < to, maksymalnie 366 dni. Jedna granica uzupełnia
drugą o 366 dni; bez dat dostępna jest pełna historia stronicowana. Dawny format
query w ms nie jest obsługiwany. Daty trip dotyczą created_at, obserwacji
server_received_at. Różne offsety i DST Europe/Warsaw są sprawdzone; UI strefy
czasu należy do etapu 7. Raw zachowuje dotychczasowe czasy ISO/model seconds;
adapter jawnie przelicza UTC ms. ended_at w recovery pochodzi z end_time manifestu.

Keyset ma domyślny limit 25, maksymalny 100, sortowanie timestamp + stabilny ID
w obu kierunkach. Cursor HMAC z purpose school-list-v1 wiąże actor, rodzaj listy,
filtry, sortowanie, as_of, ostatni klucz i TTL 15 minut. Nie zawiera snapshotu
credentials ani zgód. Każda strona sprawdza aktualne uprawnienia. Inny actor,
zmienione filtry/sortowanie, uszkodzenie lub expiry dają 400. Publiczny offset
nie jest obsługiwany. Test odczytuje wszystkie **10007** rekordów, bez ucięcia.

as_of ogranicza czas utworzenia/przyjęcia, nie tworzy pełnego snapshotu DB.
Późniejsze timestampy nie wchodzą na dalsze strony; nowy rekord o identycznym
czasie może wejść zależnie od ID. Korekta, archiwizacja lub revoke może zmienić
członkostwo filtrów między stronami. Po zmianie filtrów trzeba zacząć nową listę.

## Schema i idempotency

Schema **v3**, nadal **14 tabel**. Migracje 0001/0002 są niezmienione. 0003 dodaje
observations.historical oraz parent_session_id, boot_id, observation_id do
recording_operations, indeksy daty obserwacji i trip/state/kind intencji.
Triggery chronią nowe fakty, kontekst intencji i relacje właściciela. Historical=1
wymaga measured_at NULL. Stare rekordy zachowują historical=0, bez domyślania
pochodzenia. ALTER z CHECK wywoływał wewnętrzny PRAGMA SQLite blokowany przez
authorizer: zamiast osłabiać guard użyto walidacji INSERT i immutable UPDATE trigger.
Migracje, checksumy, FK/integrity, WAL i SQLite backup API zachowują gwarancje
etapu 3. Runtime wymaga jawnej migracji, import/serve nie wykonuje jej po cichu.

START/FINISH wiążą actor/kind/key z request hash; inny payload daje 409.
Retry nie tworzy nowego run/manifestu i zachowuje tożsamość kontekstu, ale DTO
pokazuje aktualny status/revision, nie historyczny snapshot. Po nieodwracalnym
błędzie startu trzeba utworzyć nowy PLANNED trip; jazda nie jest wznawiana.
Observation jest unikalna po trip/MANUAL/source_event_id, z kontrolą zgodności
faktów. JOURNAL ma klucz wynikający ze źródłowego zdarzenia i FK obserwacji.
Correction jest unikalna po actor/client_operation_id; fingerprint oryginalnego
żądania pozwala ponowić również częściową zmianę po następnych korektach.
Inne mutacje chroni revision lub konkretny share_id.

Audyt zapisuje actor/action/resource/czas/request_id i wymagany powód, w tej
samej transakcji co dane SQLite. Finalizacja systemowa ma actor_type SYSTEM;
nie podszywa się pod wylogowanego użytkownika. Brak haseł, tokenów, kopii GPS i poczty.

## Koordynacja loggera i recovery

Start rezerwuje globalny trip i PENDING START w BEGIN IMMEDIATE, zapisując
parent session, boot i kontrolowany run ID przed filesystem. RunLogger.start
otrzymał opcjonalny keyword run_id; stare wywołania nadal tworzą UUID. Format
raw.csv/metadata.json/complete.json nie został zmieniony. Root pochodzi ze Storage,
nie z klienta. Logger zapisuje RUN_START/TELEMETRY i flush/fsync; dopiero potem DB
przechodzi w RECORDING/APPLIED, po ponownej kontroli sesji. Błąd pozostawia
INTERRUPTED; close_unfinished nie fabrykuje manifestu.

Obserwacja i PENDING JOURNAL commitują najpierw do DB. Potem append/flush/fsync raw,
a na końcu raw_sequence/APPLIED w DB. Retry/recovery sprawdza istniejące zdarzenie
i jego fakty, więc utrata checkpointu DB nie dubluje raw. Błąd zapisu raw zachowuje
obserwację i jawny FAILED journaling (202), bez fałszywej deklaracji obu sukcesów.

Finish: FINALIZING + intent, rozstrzygnięcie pending journal, RunLogger.finish,
walidacja rzeczywistego manifestu i hashów, dopiero COMPLETE w DB. Kontrolowane są
root/run/owner/trip, schema, sekwencje, czas, liczba rekordów i zdarzeń, SHA raw/meta.
Nie przyjmuje się hashów klienta ani nie naprawia korupcji przeliczeniem manifestu.
Resolver odrzuca traversal, symlink i reparse escape.

Startup ma nowy boot i dotyczy tylko jawnego szkolnego root. Odczytuje aktywne tripy
z DB, nie skanuje globalnych katalogów. Bez zaufanego START jest INTERRUPTED bez
odczytu plików. Poprawny manifest po utracie ostatniego commit daje kontrolowane
COMPLETE i audyt systemowy; brak, uszkodzenie lub błędny kształt manifestu daje
INTERRUPTED. Pending journal rozpoznaje już zapisany fakt jako APPLIED; brak lub
korupcja daje FAILED, bez dopisywania do zamkniętego raw. Nie wznawia jazdy, GPS
ani kamery i nie importuje niepowiązanych plików.

Logout/all/reset/change-password uruchamia wspólny credentials_changed/reconcile.
Watchdog co 0.25 s sprawdza też status/role/security_version/idle/absolute expiry,
bez odświeżania idle. Finalizacja po revokacji używa wcześniej związanego kontekstu,
root i audytu systemowego, nie odzyskuje sesji ani nie daje prawa odczytu. Przyszły
panel blokady/roli wykorzysta ten sam punkt integracji; panel i Android nie powstały.

**Nie ma jednej transakcji SQLite–filesystem.** Przed intencją błąd DB nie tworzy
pliku. Po append fakt pozostaje trwały/PENDING; po manifest/przed DB COMPLETE
startup weryfikuje pliki. Przy trwającym błędzie DB/FS finalizacja może czekać na
retry watchdog lub recovery. Credentials pozostają cofnięte. Kill przed manifestem
daje INTERRUPTED bez dopisywania RUN_END; graceful shutdown próbuje finish.
Backup DB nie obejmuje raw/mediów: wymagają osobnej kopii operatorskiej.

## Wykonane sprawdzenia

Własne środowisko: Windows, Python 3.14.4, coverage 7.13.1, Node 24, headless Edge.
Końcowy kod sprawdzono przy HEAD **bf6af53f72365cdb95523db40f9fb48b0d0a1fe1**.
Dokumentacja dodana po testach nie zmienia kodu wykonawczego.

| Sprawdzenie | Faktyczny wynik |
|---|---|
| Nowe testy test_school_records.py | 25 testów; wszystkie przeszły w końcowym zestawie szkolnym |
| Wszystkie test_school*.py, z coverage | 133 testy, 132 PASS, 1 skip; 309.084 s |
| Pełna Python regresja w izolowanym git eksporcie | 359 testów, 358 PASS, 1 skip; 329.174 s |
| Node driver_ui i vision_workbench_ui | 7/7 PASS |
| mobile_flow | PASS |
| Browser resources: desktop 1280×900 i phone 390×844 | PASS |
| Browser accounts: register/mail/verify/login/reauth/logout/reset/change/all, oba rozmiary | PASS z rzeczywistym KDF |
| CLI fresh init/status/migrate no-op/backup/restore | PASS |
| Historyczna syntetyczna v2 → v3 z automatycznym backupem | PASS; bez starego lokalnego runtime |
| Rzeczywisty serwer CLI i check_school_records, następnie restart/read archive | PASS, rzeczywisty KDF, hasło tylko w pamięci/stdin/getpass |
| Bazowy GreenWave w osobnym eksporcie | HTML 200, /api/state 200 |

W obu Python zestawach pominięto POSIX symlink na Windows (WinError 1314).
Windows junction PASS. Tkinter działał, nie było błędu importu i nie ukrywano testu.
Nie wykonano własnego Linux testu, Docker deploymentu, ADB, jazdy ani YOLO.
Browser sprawdza istniejące konta i odczyt zasobów; nie zastępuje przyszłego UI tabel.

Testy obejmują HTTP role/CSRF/spoofing, atomowy audyt, concurrent revisions i
idempotency (Barrier/Event), niezmienność raw/oryginałów, historyczne adnotacje,
effective filters, DST/granice dat, 10007 rekordów, cursory i aktualną zgodę.
Faulty DB/filesystem sprawdzono na granicach start intent/files/commit, journal
checkpoint, finish manifest/commit; restart sprawdzono z pending intents,
częściowym CSV, korupcją hashów, malformed JSON/shapes i niepowiązanym root.
Logout/all/reset/password/role/idle kończą związane nagranie. Revoke/regrant nie
ożywia replay/jobs; owner nadal zarządza jobem. Export sprawdza integralność.

Pierwsze próby wykryły ALTER CHECK/authorizer, stare oczekiwania kolumn w testach,
nieaktualny mock list adaptera, cudzy opcjonalny trip filter 200 zamiast 404,
klienta scenariusza oczekującego data w error DTO oraz bool/pusty route_version_id.
Poprawiono kod/testy i ponowiono sprawdzenia. Backup poza kontrolowanym root był
odrzucony zgodnie z containment, potem wykonano poprawny backup w root/backups.
Nie osłabiono auth/CSRF/migration guard ani nie wyłączono ścieżek coverage.
Kontrola dokumentacji: UTF-8, zbilansowane code fences i istniejące względne
odnośniki PASS; wszystkie 35 bloków PowerShell w run.md parsują się poprawnie.
Diff zastosowanych migracji 0001/0002 względem zaakceptowanego etapu 5 pusty.
Staging kontrolowany przez konkretne nazwy plików i git diff --cached --check;
żadnych DB, runtime, nagrań, mailboxów, sekretów lub środowisk w nowym drzewie.

## Coverage z branch=True

Pomiar obejmuje całe cztery szkolne pakiety oraz zmieniony greenwave.telemetry,
bez wyłączeń linii (excluded_lines=0). Tylko testy szkolne zasilały ten pomiar;
pełna regresja była osobnym wykonaniem, nie dopisano jej pokrycia do tego wyniku.

- Cztery szkolne pakiety: linie **2701/2837 (95.2062%)**, gałęzie
  **765/1030 (74.2718%)**, combined **89.6302%**.
- Z całym telemetry: linie **2784/2970 (93.7374%)**, gałęzie **771/1060 (72.7358%)**,
  combined **88.2134%**. Telemetry ma niższe pokrycie w samym zestawie szkolnym.

Combined = (covered lines + covered branches)/(statements + branches).
To pomiar etapowy, nie końcowy szeroki zakres M8/CV/backend i osobny JS z audytu.
Raport JSON lokalnie: artifacts/stage6-accepted-coverage.json (ignorowany, nie Git).
Polecenia reprodukcji i report -m: [run.md, sekcja 11](run.md#11-etap-6--zapis-i-powtarzalny-odbiór-http).

| Moduł (greenwave/) | Linie | Gałęzie | Combined |
|---|---|---|---|
| school_accounts/__init__.py | 0/0 (100.00%) | 0/0 (100.00%) | 100.00% |
| school_accounts/__main__.py | 56/67 (83.58%) | 9/12 (75.00%) | 82.28% |
| school_accounts/config.py | 51/55 (92.73%) | 16/20 (80.00%) | 89.33% |
| school_accounts/crypto.py | 60/62 (96.77%) | 16/18 (88.89%) | 95.00% |
| school_accounts/demo_mail.py | 70/80 (87.50%) | 30/38 (78.95%) | 84.75% |
| school_accounts/errors.py | 4/4 (100.00%) | 0/0 (100.00%) | 100.00% |
| school_accounts/http.py | 216/239 (90.38%) | 69/100 (69.00%) | 84.07% |
| school_accounts/limits.py | 28/28 (100.00%) | 2/2 (100.00%) | 100.00% |
| school_accounts/mail.py | 57/60 (95.00%) | 7/8 (87.50%) | 94.12% |
| school_accounts/service.py | 170/177 (96.05%) | 27/36 (75.00%) | 92.49% |
| school_accounts/sessions.py | 58/60 (96.67%) | 13/14 (92.86%) | 95.95% |
| school_data/__init__.py | 3/3 (100.00%) | 0/0 (100.00%) | 100.00% |
| school_data/__main__.py | 32/33 (96.97%) | 7/8 (87.50%) | 95.12% |
| school_data/accounts.py | 50/50 (100.00%) | 20/20 (100.00%) | 100.00% |
| school_data/backup.py | 71/74 (95.95%) | 9/12 (75.00%) | 93.02% |
| school_data/configurations.py | 38/38 (100.00%) | 10/16 (62.50%) | 88.89% |
| school_data/database.py | 59/62 (95.16%) | 8/8 (100.00%) | 95.71% |
| school_data/errors.py | 11/11 (100.00%) | 0/0 (100.00%) | 100.00% |
| school_data/locking.py | 33/37 (89.19%) | 5/8 (62.50%) | 84.44% |
| school_data/migrations.py | 110/111 (99.10%) | 43/44 (97.73%) | 98.71% |
| school_data/observations.py | 80/80 (100.00%) | 27/42 (64.29%) | 87.70% |
| school_data/repositories.py | 8/8 (100.00%) | 0/0 (100.00%) | 100.00% |
| school_data/repository_base.py | 51/51 (100.00%) | 14/16 (87.50%) | 97.01% |
| school_data/security_records.py | 94/94 (100.00%) | 16/22 (72.73%) | 94.83% |
| school_data/storage.py | 48/49 (97.96%) | 15/16 (93.75%) | 96.92% |
| school_data/time_units.py | 26/26 (100.00%) | 14/14 (100.00%) | 100.00% |
| school_data/trips.py | 133/133 (100.00%) | 45/62 (72.58%) | 91.28% |
| school_data/validation.py | 39/39 (100.00%) | 16/16 (100.00%) | 100.00% |
| school_records/__init__.py | 0/0 (100.00%) | 0/0 (100.00%) | 100.00% |
| school_records/lists.py | 62/62 (100.00%) | 33/38 (86.84%) | 95.00% |
| school_records/paging.py | 56/58 (96.55%) | 16/24 (66.67%) | 87.80% |
| school_records/raw.py | 54/56 (96.43%) | 27/44 (61.36%) | 81.00% |
| school_records/recording.py | 181/188 (96.28%) | 36/58 (62.07%) | 88.21% |
| school_records/writes.py | 114/115 (99.13%) | 24/38 (63.16%) | 90.20% |
| school_resources/__init__.py | 0/0 (100.00%) | 0/0 (100.00%) | 100.00% |
| school_resources/api.py | 80/80 (100.00%) | 46/52 (88.46%) | 95.45% |
| school_resources/contexts.py | 199/202 (98.51%) | 43/62 (69.35%) | 91.67% |
| school_resources/files.py | 154/161 (95.65%) | 48/72 (66.67%) | 86.70% |
| school_resources/policy.py | 63/64 (98.44%) | 23/28 (82.14%) | 93.48% |
| school_resources/reads.py | 82/120 (68.33%) | 31/62 (50.00%) | 62.09% |
| telemetry.py | 83/133 (62.41%) | 6/30 (20.00%) | 54.60% |

## Commity i ręczny odbiór

1. bc459fb628861bd40b26404805840c66f45f0850 — schema v3, atomowe repozytorium, zgodny logger.
2. 1e3ae7126fa5d6d5dac0aa38be42cb3cf9565f7b — usługi, API, recording, scenariusz i testy.
3. 9b0d0e5d18031c0d027ba63a5ceb421b4a5e3e83 — malformed manifest i regresja recovery.
4. bf6af53f72365cdb95523db40f9fb48b0d0a1fe1 — typ opcjonalnego route reference i testy.
5. Commit dodający ten raport — dokumentacja; hash w odpowiedzi oraz:
   `git log -1 --diff-filter=A --format=%H -- docs/school-app/stage6.md`.

Dokładne komendy i scenariusz są w [run.md, sekcja 11](run.md#11-etap-6--zapis-i-powtarzalny-odbiór-http).
Skrypt używa rzeczywistego HTTP/cookies/CSRF i getpass, bez hasła w argv/tokenów w logach.

- [ ] Nowy root, schema v3, klucze i syntetyczna fixture z własnym hasłem.
- [ ] Login → create → SIM start → observation → finish → read/export.
- [ ] Edit → correction → filters/keyset → share → revoke → archive.
- [ ] Restart → odczyt archiwum, bez wznowienia dawnej jazdy.
- [ ] Role/CSRF/revisions, raw immutability, owner job management i fault recovery.
- [ ] Przegląd powyższych wyników i granic; akceptacja użytkownika.

STOP przed etapem 7. Bez push/merge/rewrite; bez DB/runtime/nagrań/mailboxów/sekretów w Git.
