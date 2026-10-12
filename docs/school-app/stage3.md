# Etap 3 — baza danych i repozytoria

Status: **Przygotowany do odbioru**. Kontrakt zaakceptowany przez użytkownika:
77c074cdc24eb14795eb8eb593167945d74eead4. Worktree:
C:/Users/konra/.codex/worktrees/school-app/Surfy, gałąź codex/school-app.
Na wejściu HEAD był równy kontraktowi, status i staging były puste.
Obowiązujący C:/Users/konra/.codex/AGENTS.md był pusty; dodatkowych AGENTS.md
w repozytorium nie znaleziono. Nie zmieniano main ani codex/vision-camera.

## Implementacja i granice

Nowy niezależny pakiet greenwave.school_data, biblioteka standardowa Python>=3.11:

- storage: jawny absolutny root, kontrolowane ID hex32, containment, symlinki/reparse;
- locking: nieblokująca wyłączna dzierżawa procesu/runtime, msvcrt na Windows,
  flock na POSIX; wszystkie wspierane odczyty i maintenance respektują dzierżawę;
- database: krótkie połączenia i transakcje BEGIN IMMEDIATE, rollback/finally-close;
- migrations/sql: numerowany SQL, SHA-256 źródła, wersja i kontrola integralności;
- backup: SQLite backup API, walidowany snapshot i restore z poprzednim snapshotem;
- accounts/security_records: wewnętrzne rekordy kont i hashów credentials;
- trips/observations/configurations: własność, udostępnianie, korekty, wersje/intencje;
- repository_base/repositories/validation: zaufany Actor, świeża polityka, walidacja.

Import nie wykonuje I/O, nie migruje bazy i nie tworzy kont. Database otwiera tylko
już przygotowaną bieżącą bazę. Brak fallbacku do data/runs, data/derived i starego
runtime/school; takie jawne korzenie także są odrzucane bez czytania danych.
Nie korzystano z historii prototypu i nie odtworzono jego serwera/UI.

To nie jest jeszcze login, KDF, SMTP, CSRF HTTP ani parowanie telefonu z portalem.
Hash hasła jest wynikiem przyszłego KDF dostarczonym z zaufanej usługi; testy
jawnie używają fixture$NOT_AUTHENTICATION. Sekrety sesji, CSRF, account tokens,
HMAC kodu parowania i urządzeń muszą być hex64; surowy sekret jest odrzucany.
Repozytorium nie hashuje tych wartości i nie udaje uwierzytelniania.

Actor(user_id, reauthenticated_at) jest wewnętrznym kontekstem przyszłego serwera,
nie obiektem formularza. Konstruktor Actor nie uwierzytelnia. Rola/status/version
są odczytywane z DB wewnątrz transakcji; DTO nie dostarcza owner_id ani roli.
create_user/get_user/issue_account_token są zaufanym API provisioningu/auth,
nie katalogiem kont dla przeglądarki. Publiczna rejestracja etapu 4 musi wymuszać DRIVER.
Token consume może wywołać zaufany callback apply(connection,token_record): przyszła
zmiana hasła/aktywacja musi nastąpić w tej samej transakcji co zużycie tokenu.
Test błędu callbacku potwierdza rollback obu zmian. Brak SMTP workflow.

## Schemat v1 — dokładnie 14 tabel domenowych

|Tabela|Przeznaczenie / integralność|
|---|---|
|schema_migrations|version INTEGER PK, checksum i czas/aplikacja; kanoniczne wersje|
|users|email normalized UNIQUE, role/status CHECK, ACTIVE wymaga verified_email_at, revision/security_version>=1|
|browser_sessions|FK użytkownika, unikalny secret_hash, csrf_hash, idle i absolute expiry, revoke/version|
|account_tokens|RESET/VERIFY_EMAIL, jednorazowe hashe, TTL, partial UNIQUE aktywnego user/purpose|
|auth_rate_limits|key_hash PK, okno/licznik, blocked_until i retention|
|devices|FK owner/parent session, hash bieżącego tokenu, boot_id/version/expiry; UNIQUE owner/client i hash|
|pairing_challenges|FK owner/session, HMAC, TTL<=300s, attempts 0..5; partial UNIQUE kod/session|
|trips|FK właściciela i snapshotu trasy, ograniczone stany/mode/title/note, revision/archive; komplet metadanych COMPLETE|
|observations|FK trip/actor, enum koloru/rodzaju, oryginalne fakty; UNIQUE trip/source/event, transport journaling|
|observation_corrections|FK observation/actor, before/after JSON, sequence=previous+1, reason/time, idempotency/request_hash|
|trip_shares|FK trip/analyst/grantor; tylko READ_ANALYZE, partial UNIQUE jednej aktywnej zgody|
|audit_events|autoincrement sequence, actor/action/resource/time/request/outcome, append-only|
|config_versions|FK creator, UNIQUE kind/logical/version, payload JSON/hash, revision/status, immutable published payload|
|recording_operations|FK trip/actor, START/FINISH/JOURNAL_OBSERVATION, UNIQUE actor/kind/key, hash/state/result_ref|

SQLite sqlite_sequence to techniczna tabela AUTOINCREMENT, nie piętnasta tabela aplikacji.
Definicje typów, NOT NULL, CHECK i indeksów: greenwave/school_data/sql/0001_initial.sql.
Czasy REAL to UTC epoch serwera; terminy kończą się przy expiry<=now. IDs TEXT hex32;
hashe sekretów TEXT hex64; JSON jest kanoniczny, bez NaN. Nullable pola odpowiadają
niezaistniałym zdarzeniom (revoke/use/start/end), brakowi pomiaru lub artefaktu.
FK bez kaskadowego kasowania chronią powiązania. Nie ma API fizycznego usuwania.
Wstrzyknięte clock/ids pozwalają testować wygasanie i deterministyczne identyfikatory.

Indeksy: owner/date/id i owner/route/status/date przejazdów; trip/date/id oraz
trip/signal/state/event/date obserwacji; recipient/revoked/trip udostępnień;
user/revoked i expiry sesji, token user/purpose/expiry, actor/resource/time audytu.
Listy mają parametryzowane filtry, limit 1..100, offset>=0 i stałe sortowanie
created/received DESC,id DESC; efektywne kolory/rodzaje po korekcie są filtrowane
w SQL przez ostatnią korektę. Oryginał jest nadal zwracany osobno od effective.
Integracja tabel obejmująca wszystkie przejazdy kierowcy i paginację HTTP zostaje
na etap 6; obecne list_observations jest celowo ograniczone do konkretnego trip.

## Atomowość i polityka domenowa

Odczyt własny jest dostępny wszystkim aktywnym rolom tylko dla owner_id=actor.
ADMIN nie ma globalnej ścieżki do GPS/trips/observations. Osobny get_shared_trip,
list_observations(shared=True),correction_history(shared=True) wymaga ACTIVE ANALYST,
aktualnej zgody, COMPLETE i braku archive. Analityk nie uzyskuje uprawnień do
edycji, eksportu ani CV. Każdy odczyt ponawia kontrolę; integracja jobs/replay/media
musi ponawiać ją również w etapach 5–6.

Share przyjmuje dokładny znormalizowany email aktywnego analityka, odrzuca właściciela,
nieukończony/archiwalny trip i drugi aktywny grant. Cofnięcie jest idempotentne dla
konkretnego starego ID i nie odwołuje nowszego grantu. Archive cofa grant. Zmiana roli
lub blokada analityka także cofa zgody. Zmiana konta wymaga ADMIN i zaufanej świeżej
reauth<=300s; ostatniego aktywnego ADMIN nie można zdegradować/zablokować. Zmiana
kont zwiększa security_version i cofa sesje/tokeny/device/pairing. Sam timestamp
nie zastępuje przyszłej serwerowej weryfikacji hasła.

UPDATE/DELETE oryginalnych faktów obserwacji, korekt i audytu zatrzymują triggery.
Journaling zmienia wyłącznie raw_sequence/journaling_state; próba jednoczesnej zmiany
state nie przechodzi. Trigger korekty sprawdza właściciela i aktualną sekwencję.
BEGIN IMMEDIATE serializuje read-compare-append; dwóch autorów z expected_revision=0
nie dopisuje dwóch korekt. Ten sam operation key i treść zwraca poprzedni wynik;
inna treść jest konfliktem. Before/after/reason/author/time są oddzielne od oryginału.

Wiele rekordów i czas nie nadają się do zwykłego CHECK: ostatni admin, świeża reauth,
ACTIVE rola i grant, upływ TTL, rotacja tokenów, revision, przydział nav. Repozytoria
sprawdzają je wewnątrz transakcji, część relacji wzmacniają triggery/partial UNIQUE.
Przejście PLANNED->STARTING atomowo odmawia, gdy istnieje STARTING/RECORDING/FINALIZING;
komunikat nie ujawnia ownera. To rezerwacja danych, nie HTTP409 ani działający logger.
Jeden proces per root oraz ta transakcja zapobiegają konfliktującemu startowi v1.

## Migracje, backup, restore i awarie

SQLite: foreign_keys=ON, busy_timeout=5000ms, journal_mode=WAL, synchronous=FULL.
Blokada pliku .school.lock to wyłączność runtime/maintenance, odrębna od SQLite
BEGIN IMMEDIATE/EXCLUSIVE i oczekiwania na transakcję. Można otwierać wiele krótkich
połączeń z jednego Database, np. wątków; drugi runtime/CLI maintenance dostaje Busy.
Windows używa blokady bajtu msvcrt, Linux kodu flock; Windows sprawdzony rzeczywiście,
Linux uruchomienie i kontener pozostają do etapu 11 (bez deklaracji testu na Linux).

0001_initial.sql jest jedną rzeczywistą migracją, SHA-256 treści UTF-8. Nie zmieniaj
zastosowanego źródła; następna zmiana schematu wymaga kolejnego numeru. Test v2 tworzy
wyłącznie kontrolowaną syntetyczną tabelę, nie dopisuje pozornych migracji do produktu.
schema_migrations to źródło prawdy, user_version to dokładne odwzorowanie; przy gap,
rozbieżności, checksum mismatch, unknown legacy DB lub future version odmowa.
Wszystkie oczekujące migracje to jeden BEGIN IMMEDIATE; bez executescript i niejawnych
COMMIT. FK/integrity checks są wykonywane przed/po; błąd SQL/komendy transaction/
postcheck oznacza rollback i kontrolę poprzedniej wersji. Fresh failure zostawia pusty
schemat v0; upgrade failure zachowuje v1 i sprawdzony snapshot before-migration.
Powtórna migracja bieżącego schematu jest no-op. Wyłączenie procesu w transakcji
polega na recovery SQLite; nie testowano odcięcia zasilania sprzętu.

Przed zmianą istniejącej bazy migrate robi SQLite backup API do backups/. Backup
obejmuje zatwierdzone strony WAL, nie zwykłą kopię aktywnego pliku. Restore waliduje
źródło/current schema/checksum/FK/integrity, robi sprawdzony plik staging, blokuje
runtime, checkpointuje WAL, zachowuje snapshot before-restore i atomowo zastępuje DB.
Nieprawidłowy backup nie zastępuje DB. Poprzedni snapshot pozostaje do kontrolowanego
kolejnego restore. Nie nadpisuje istniejącej ścieżki backupu. CLI nie odczytuje haseł,
nie tworzy prawdziwych kont i nie drukuje credentials.

Każdy wspierany konsument MUSI używać Lease/Database. Obcy proces omijający tę
warstwę nie podlega gwarancji procesu; checkpoint wykrywa zajęty WAL, lecz nie jest
zamiennikiem poprawnych ACL i zatrzymania wszystkich zewnętrznych klientów SQLite.
Katalog należy do operatora i nie może być zapisywany przez niezaufane lokalne
procesy. Resolver sprawdza symlink/reparse/resolve przed operacją; nie obiecuje
odporności na wyścig lokalnego napastnika zmieniającego junction po sprawdzeniu.

Backup dotyczy wyłącznie DB. NIE jest backupem GPS, manifestów, config artefaktów ani
filmów; pełny zestaw artefaktów i jego manifest/recovery wymaga integracji etapu 6.
COMPLETE w repo sprawdza zestaw metadanych/hashy i własną ścieżkę, nie fizyczny raw.
recording_operations utrwala intencję i wynik/idempotency, pending_intents odczytuje
je po restarcie. Nie uruchamia capture, nie naprawia raw/manifest, nie kończy loggera
po logout. Serwis etapów 4–6 musi tworzyć świeży boot_id po restarcie i faktycznie
zatrzymywać ingest/recording po logout/block/role/password/revoke. Device lookup
odrzuca inny boot_id i wygasłą/cofniętą sesję już teraz.

## Faktyczne sprawdzenia 2026-10-12

Python 3.14.4, coverage.py 7.13.1, Windows. Wszystkie nowe testy używają
TemporaryDirectory, nowe CLI próbowało tylko runtime/stage3-cli-<GUID> (syntetyczny).
Nie otwierano starego runtime/school ani prywatnych data/runs. Git staging dokładny.

- 34 testy warstwy danych: OK, 1 skip (WinError1314, zwykły symlink wymaga privilege);
  33 wykonane PASS. Junction Windows rzeczywiście utworzony i ucieczka odrzucona.
- Fresh/no-op/status, synthetic upgrade, rollback fresh/upgrade, checksum/future/
  user_version/history/FK odmowy: PASS. Backup przy istniejącym WAL i restore z
  zachowanym poprzednim stanem: PASS. Lease konflikt także w subprocess: PASS.
- Własność/ADMIN deny/ANALYST before-after-revoke, role/block revocation, trwałość,
  immutable SQL, expected_revision concurrency/idempotency, recording reservation: PASS.
- Ostatnia pełna regresja izolowanego eksportu c6fd304: 260 testów, OK, 1 skip,
  31.127s. Po ostatniej poprawce containment a64adff ponownie 34 testy danych OK
  (7.822s), bez zmian rdzenia; nie powtarzano jeszcze raz niezmienionych 226 testów.
- Node: 7/7 PASS; node tests/mobile_flow.cjs PASS, izolowany eksport.
- CLI python -m greenwave --no-browser --port <wolny>: HTML/state HTTP200, PASS,
  oddzielny proces w eksporcie; brak publikacji pairing code/token w wyniku.
- Dokładne PowerShell init/status/migrate/backup/restore/status: v1 current, PASS,
  previous snapshot utworzony. Init nie tworzy kont.
- Początkowo test zakazu COMMIT wykrył błąd parsera (COMMIT; zawierało separator);
  poprawiono parser, ponowne testy PASS. Przegląd ścieżek wykrył lexical containment
  z ../ między tripami; poprawiono na resolved containment i dodano test odmowy PASS.

Pominięcia: pełne browser E2E/Android build/telefon/ADB/YOLO/Docker, bo te komponenty
nie są zmieniane/podłączane. Linux locking nie wykonany na tym Windows. Skip symlinka
to ograniczenie środowiska, nie zielony wynik tego testu. Brak nierozwiązanych błędów
wykonanych testów. PUBLISH-01 pozostaje otwarty: wcześniejsza historia nadal zawiera
runtime z 3476d133; nie oceniano natury danych i nie przepisywano historii.

Polecenia testów nowej warstwy (worktree, TemporaryDirectory):

```powershell
python -m unittest discover -s tests -p 'test_school_data*.py' -v
.venv-school/Scripts/python.exe -m coverage run --branch --source=greenwave.school_data --data-file=artifacts/stage3.coverage -m unittest discover -s tests -p 'test_school_data*.py' -v
.venv-school/Scripts/python.exe -m coverage report --data-file=artifacts/stage3.coverage -m
.venv-school/Scripts/python.exe -m coverage json --data-file=artifacts/stage3.coverage -o artifacts/stage3-coverage.json
```

Pełna regresja była wykonywana z artifacts/stage3-final/source po git archive:
`python -m unittest discover -s tests -v`.
Node z artifacts/stage3-regression/source:
`node --test tests/driver_ui.cjs tests/vision_workbench_ui.cjs`, `node tests/mobile_flow.cjs`.
Eksporty/logi/coverage są ignorowane i nie są materiałem źródłowym w commicie.

## Pomiar coverage etapu 3

branch=True, source=greenwave.school_data, żadnych omit/exclude ani podmiany globalnej
konfiguracji. Licznik linii **807/821 = 98.2948%**; gałęzi **218/274 = 79.5620%**;
łączny wynik coverage.py **93.6073%**. 14 niepokrytych linii, 56 brakujących gałęzi.
SQL ograniczenia są sprawdzane integracyjnie; coverage.py nie mierzy tekstu SQL.
Poniżej raport per moduł: wykonane/wszystkie linie i gałęzie oraz combined.

|Moduł|Linie|Gałęzie|Combined|
|---|---:|---:|---:|
|__init__.py|3/3|0/0|100.00%|
|__main__.py|32/33|7/8|95.12%|
|accounts.py|47/47|17/18|98.46%|
|backup.py|67/70|7/10|92.50%|
|configurations.py|38/38|10/16|88.89%|
|database.py|59/62|8/8|95.71%|
|errors.py|11/11|0/0|100.00%|
|locking.py|33/37|5/8|84.44%|
|migrations.py|90/92|38/40|96.97%|
|observations.py|75/75|25/40|86.96%|
|repositories.py|8/8|0/0|100.00%|
|repository_base.py|31/31|8/8|100.00%|
|security_records.py|94/94|16/22|94.83%|
|storage.py|48/49|15/16|96.92%|
|trips.py|132/132|46/64|90.82%|
|validation.py|39/39|16/16|100.00%|

To wynik tylko etapu 3, NIE końcowe pokrycie aplikacji. Zachowano zaakceptowany
szeroki mianownik backendu i używanego M8/CV z contract/audit oraz osobny pomiar
istotnej logiki JS w etapie 10. Brak zmian JS, więc teraz nie mierzono JS ponownie.
Nie zastosowano nowej wąskiej .coveragerc.

## Commity i ręczny odbiór

1. 2af534f84fe766dd982d6d69beeafb9eb660fe85 — schema/migracje/backup/restore/lease/CLI.
2. 37de1cd491650aed75e3c593c4e0cfccfb8fce7f — repozytoria i integralność domenowa.
3. c6fd304dc4e6965da19dd431773b3dfb8e8dc691 — rezerwacja i trwałość intencji/FK.
4. a64adff4c14d1475422f1abd4270df14472b34ec — resolved containment wyników recording.
5. Commit dodający stage3.md — dokumentacja i dowody odbioru; hash:
   `git log -1 --diff-filter=A --format=%H -- docs/school-app/stage3.md`.
Nie wpisujemy przyszłego hasha we własną treść commita; pełny hash w odpowiedzi.

- [ ] Odczytać aktualny status/gałąź i potwierdzić zmiany tylko etapu 3.
- [ ] Wykonać świeże init/status/no-op/backup/restore według run.md, bez starego root.
- [ ] Uruchomić 34 testy i sprawdzić pojedynczy jawny skip oraz junction PASS.
- [ ] Odtworzyć raport coverage linii/gałęzi i sprawdzić wszystkie moduły.
- [ ] Przejrzeć granice: brak HTTP auth/SMTP/UI oraz brak DB–raw–manifest recovery.
- [ ] Potwierdzić ACL ADMIN/ANALYST, niezmienne oryginały i oczekiwane revision.
- [ ] Zaakceptować etap 3 oddzielnie przed wydaniem promptu etapu 4.

Brak push/merge; STOP przed etapem 4. Polecenia CLI i bazowego GreenWave: [run.md](run.md).
