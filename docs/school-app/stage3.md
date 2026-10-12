# Etap 3 — warstwa danych po niezależnym przeglądzie

Status: **Przygotowany do ponownego odbioru**. Poprzednia implementacja:
**6c3364997bd26cd8a0a0a67ee7505371bf93feef**. Kontrakt zaakceptowany:
77c074cdc24eb14795eb8eb593167945d74eead4. Worktree:
C:/Users/konra/.codex/worktrees/school-app/Surfy, branch codex/school-app.
Na wejściu HEAD6c33649, status/staging puste; AGENTS.md globalny pusty,
dodatkowych obowiązujących AGENTS w repo nie znaleziono. Main i vision-camera bez zmian.

## Cztery problemy: przyczyny, poprawki, dowody

|Problem|Przyczyna|Poprawka|Regresja|
|---|---|---|---|
|Atomowość migracji|Pierwsze słowo split() było komentarzem zamiast COMMIT|set_authorizer odmawia SQLITE_TRANSACTION/SAVEPOINT/ATTACH/DETACH/PRAGMA dla rzeczywiście wykonywanych operacji; osobny zakaz VACUUM po usunięciu leading comments; runner poza authorizer scope|Dokładny reproduktor użytkownika: odmowa SchemaError, zero tabel, user_version0; upgrade zachowuje dane/wersję; 33 warianty komentarzy/komend; legalne triggery/literały PASS|
|UTC sekundy zamiast ms|REAL i time.time() w repo nie odpowiadały kontraktowi|Nowa migracja0002, INTEGER ms we wszystkich trwałych czasach i Actor; centralny clock adapter/validation; TTL także ms|Wszystkie rekordy 14 tabel i historyczny checksum zachowane; wszystkie dawne REAL mają INTEGER; rollback błędnych wartości i po pełnej konwersji PASS; granice TTL PASS|
|Nieistniejący format GPS|transition_trip oczekiwał gps.jsonl|Własny run-root/raw.csv; brak zmian RunLogger|Istniejący RunLogger tworzy raw.csv/metadata.json/complete.json w TemporaryDirectory; COMPLETE przyjmuje raw.csv; cudzy owner/trip/../ odrzucone; hashe plików niezmienione|
|Zakres dat domknięty z obu stron|SQL <= before i brak pełnej walidacji|>=after i <before; from>=to błędne; tylko integer ms, bez bool/float/NaN/inf|5 punktów wokół obu granic; trip created_at, observation server_received_at, measured_at niezależny; złe typy i zakresy odrzucone|

Przy zakazanej operacji autorizer jest zdejmowany w finally zanim runner wykonuje
rollback/commit/status. SQLite rozpoznaje trigger BEGIN/END jako CREATE_TRIGGER,
a nie komendę transakcyjną. Parser complete_statement tylko dzieli SQL z literałami,
średnikami i komentarzami; nie jest już granicą bezpieczeństwa transakcji.
COMMIT,END,ROLLBACK,BEGIN,SAVEPOINT,RELEASE,ATTACH,DETACH,PRAGMA oraz VACUUM
nie mogą sterować transakcją migracji. Runner BEGIN IMMEDIATE/COMMIT/user_version
nadal działa. Błąd przywraca poprzedni stan, kontroluje FK/integrity i zamyka connection.
Test tego samego connection potwierdza działającą transakcję przed rollback i brak
transakcji po nim; po nieudanej świeżej migracji ponowna inicjalizacja działa.

## Architektura i granice

Pakiet greenwave.school_data używa biblioteki standardowej Python>=3.11:
storage,locking,database,migrations/SQL,backup,accounts,security_records,trips,
observations,configurations,repository_base,repositories,validation,time_units.
Import nie wykonuje I/O; brak automatycznych migracji/kont. Jawny absolutny root
jest obowiązkowy; legacy data/runs,data/derived,runtime/school są odrzucane bez
odczytu ich zawartości. DB=root/school.sqlite3; pozostałe rooty właściciel/trip/run,
derived,CV,indexes/shared-config wynikają z ID hex32 i kontekstu, bez fallbacku M8.
Resolver odrzuca symlink/junction/reparse oraz resolved escape. Katalog musi mieć
ACL operatora; nie obiecujemy ochrony przed wyścigiem niezaufanego lokalnego procesu
zmieniającego junction po kontroli. Wszystkie procesy wspieranego dostępu respektują Lease.

Actor jest zaufanym kontekstem przyszłego serwera, konstruktor nie uwierzytelnia.
user_id nie pochodzi z DTO; role/status/version są sprawdzane afresh w transakcji.
Własne dane dla wszystkich aktywnych ról, ADMIN bez globalnego dostępu; ANALYST tylko
jawnie udostępniony COMPLETE nonarchived trip. Shared read nie daje edycji/eksportu/CV.
Revoke/archive/zmiana roli cofają dostęp. Korekty mają author/server_at/reason/before/
after/revision/idempotency; triggery zabraniają zwykłego UPDATE/DELETE oryginałów,
korekt i audytu. Journal updates dotykają wyłącznie transportu. BEGIN IMMEDIATE
serializuje dwie korekty z tą samą revision; konflikt i duplicate content są jawne.
Jedna STARTING/RECORDING/FINALIZING rezerwacja na deployment, bez ujawnienia ownera.

Zachowano blokadę ostatniego aktywnego ADMIN, trusted reauth i unieważnienie hashów
credentials przy zmianach kont. Hashy nie wytwarza ten etap: fixtures opisują brak
KDF/auth. API provisioning/get_user jest wewnętrzne, nie katalogiem użytkowników.
Account-token callback umożliwia przyszłą zmianę hasła/aktywację w tej samej transakcji
co zużycie tokenu. Brak SMTP, loginu, CSRF HTTP, UI i integracji telefonu.

## Schema v2 — 14 tabel, bez zmiany 0001

schema_migrations,users,browser_sessions,account_tokens,auth_rate_limits,devices,
pairing_challenges,trips,observations,observation_corrections,trip_shares,audit_events,
config_versions,recording_operations. sqlite_sequence to techniczna tabela SQLite.

0001_initial.sql pozostaje historyczną wersją REAL seconds. Niezmienność porównano
z treścią Git w 6c3364997bd26cd8a0a0a67ee7505371bf93feef. SHA256 znormalizowanego
UTF-8/LF: **3341933b714ccf9fcd01add836ff395541a5d4e8a99baa39143cccc5c0723156**.
0002_epoch_milliseconds.sql jest statycznym numerowanym SQL: tworzy tymczasowe ms_*
tabele z tymi samymi ograniczeniami/FK, kopiuje dane konwertując czasy, usuwa stare
w odwrotnej kolejności zależności, zmienia nazwy i odtwarza indeksy/triggery. Wszystko
w jednej transakcji, FK ON; nie wyłączamy ich PRAGMA. Nazwy ms_* nie pozostają po
sukcesie ani rollback. Zachowany high-water AUTOINCREMENT audytu, także ponad max(row).

schema_migrations jest źródłem wersji; user_version mirror. Checksum/gap/future/
unknown DB powodują odmowę. Bez executescript/niejawnego COMMIT. Przed zmianą
istniejącej DB snapshot przez SQLite backup API. Fresh/no-op oraz synthetic next
version testowane; test v1 powstaje wyłącznie z load()[:1] w TemporaryDirectory.

### Jednostki czasu i konwersja

Wszystkie trwałe czasy, w tym applied_at, audit, sessions/tokens/rate limits,
obserwacje i intencje: INTEGER UTC epoch milliseconds. NULL pozostaje NULL.
Kolumny mają CHECK(typeof(value)='integer',0..253402300799999) oprócz dopuszczalnego
NULL; NOT NULL zachowane. Zakres to 1970..ostatnia ms roku9999, zgodny z RFC3339.
Ograniczenia TTL przeskalowane do ms, wszystkie pozostałe klucze/CHECK/UNIQUE/FK
oraz indeksy i triggery zachowane. Role/zakres produktu nie zostały zmienione.

Reguła historycznej konwersji: **floor(Decimal(str(seconds))*1000)**; jawne odcięcie
sub-ms, bez zgadywania jednostek i bez binarnego round(). NULL zostaje NULL; NaN,
inf,nienumeryczne,ujemne i ponad granicą wartości odrzucają upgrade z rollback.
Nie przeliczamy żadnych czasów/payloadów plików GPS ani JSONów before/after.

now_ms() adaptuje time.time() centralnie. Repo(clock=...) i migrate(clock=...) przyjmują
już wyłącznie integer ms. Actor.reauthenticated_at,verified_at,measured_at i granice
filtrów także ms; bool i float odrzucane. Migracja runnera zapisuje historyczny
applied_at w sekundach tylko do REAL schematu v1 przed jego konwersją; od v2 zawsze ms.
Idle1800000,absolute/device28800000,reset900000,verify86400000,pairing300000,
reauth300000; rate_attempt window_ms,default60000. Expiry<=now oznacza koniec.

### Backup/restore i recovery

Backup API obejmuje zatwierdzony WAL; nie jest kopią pojedynczego aktywnego pliku.
SQLite FK ON,WAL,synchronousFULL,busy_timeout5000. Lease to nieblokująca wyłączna
blokada procesu/runtime, Windows msvcrt/POSIX flock, oddzielna od SQLite transakcji.
Drugi runtime/maintenance odmawia Busy. Obcy proces omijający Lease nie podlega
tej gwarancji; checkpoint WAL jest dodatkową kontrolą, nie zamiennikiem ACL.

Backup/restore akceptuje zweryfikowaną znaną wersję1 lub2, z jej ciągłą historią,
checksumami i FK/integrity. Puste/obce/nowsze/uszkodzone bazy odrzucane. Restore
waliduje staging, blokuje runtime, checkpointuje WAL i zachowuje previous snapshot,
potem atomowo zastępuje DB. Zwraca schema:{version,latest,current}. Restore v1
zwraca version1/latest2/currentfalse; status wymaga upgrade, runtime odmawia startu.
Dopiero jawne migrate aktualizuje do v2 i robi backup poprzedniej wersji. Test legacy
backup wykonano także przy istniejącym WAL; wspierane dane zachowane po ponownym upgrade.

Backup dotyczy tylko DB, nie GPS/complete.json/config-artefaktów/filmów. Repository
COMPLETE sprawdza właściwą ścieżkę raw.csv i zestaw metadanych/hashów, nie fizyczną
spójność plików. recording_operations utrwala intent, ale nie koordynuje DB–raw–manifest,
nie kończy loggera po logout i nie naprawia crash. To etap6, a telefon/SMTP/auth etapy4–6.
Listy teraz filtrują [after,before) z offsetem wewnętrznym; HTTP keyset cursor,
pozostałe filtry UI i obserwacje między tripami zostają do etapu6.

## Wyniki sprawdzeń

Własne wykonanie: Windows, Python3.14.4,coverage7.13.1. Wszystkie testy nowych danych
w TemporaryDirectory; CLI w nowych ignorowanych runtime/stage3-review-<GUID> i
runtime/stage3-legacy-<GUID>. Stare runtime/school/private data/runs nieczytane.

- 48 testów school_data: **47 PASS,1skip**,15.752s.
- Pełna Python regresja z izolowanego eksportu HEAD023198a: **274 testy,273 PASS,
  1skip**,39.289s. Tkinter działał w tym środowisku, nie zmieniano/ukrywano testu.
- Skip zwykłego symlinka Windows: WinError1314,brak wymaganego privilege.
  Windows junction rzeczywiście wykonany: PASS. Linux nie był tu uruchamiany.
- Node7/7 PASS,mobile_flow PASS; CLI GreenWave HTML/state HTTP200 PASS.
- CLI init/status/migrate/backup/restore/status: version2/latest2/currenttrue,no-op PASS.
- CLI historycznej v1/status/backup/upgrade/restore/status/upgrade: version1 pending
  po restore, następnie version2 current; before-migration/previous snapshots PASS.
- Exact review reproducer oraz wszystkie cztery regresje opisane wyżej PASS.
- Początkowa nowa fixture RunLogger.finish nie podała wymaganego context; był to
  błąd testu, poprawiony zgodnie z istniejącym API. RunLogger nie zmieniany.

Niezależny Linux wynik dostarczony przez użytkownika/ChatGPT dla **6c33649**:
33 testy danych PASS; Windows junction skipped,POSIX symlink PASS. Pełna regresja260:
jeden błąd importu Tkinter z powodu brakującej biblioteki środowiska. To relacja
przeglądu, nie własny pomiar na Linux ani wynik naprawionego kodu. Pełnego tracebacku
nie dostarczono; nie fabrykujemy nazwy brakującego modułu. Własne Windows wykonanie
nie miało tej blokady. Docker/Android/telefon/YOLO/browserE2E niepowtarzane — niezmieniane.
PUBLISH-01 pozostaje otwarty, wcześniejsza historia nadal zawiera runtime; bez oceny danych,
bez przepisywania historii/push/merge. Brak nierozwiązanych błędów własnych wykonanych testów.

Dokładne polecenia:

```powershell
python -m unittest discover -s tests -p 'test_school_data*.py' -v
.venv-school/Scripts/python.exe -m coverage run --branch --source=greenwave.school_data --data-file=artifacts/stage3-review.coverage -m unittest discover -s tests -p 'test_school_data*.py' -v
.venv-school/Scripts/python.exe -m coverage report --data-file=artifacts/stage3-review.coverage -m
.venv-school/Scripts/python.exe -m coverage json --data-file=artifacts/stage3-review.coverage -o artifacts/stage3-review-coverage.json
```

Z izolowanego artifacts/stage3-review/source:
`python -m unittest discover -s tests -v`,
`node --test tests/driver_ui.cjs tests/vision_workbench_ui.cjs`,
`node tests/mobile_flow.cjs`.
Rzeczywisty `python -m greenwave --no-browser --port <wolny>` jako własny subprocess,
HTTP HTML/state i zamknięcie tego procesu; pairing code nie drukowany w raportach.
CLI init/legacy/upgrade/backup/restore: [run.md](run.md).

## Aktualne coverage — cały pakiet danych, branch=True

**Linie870/883=98.5277%;gałęzie245/298=82.2148%;combined94.4115%.**
13 niepokrytych linii,53 gałęzie;zero wyłączeń. SQL testowany integracyjnie, nie jest
tekstem mierzalnym przez coverage.py. Nie zastępuje to szerokiego końcowego backend/
M8/CV oraz osobnego JS pomiaru. Nie dodano wąskiej .coveragerc ani omit trudnych ścieżek.

|Moduł|Linie wykonane/wszystkie|Gałęzie wykonane/wszystkie|Combined|
|---|---:|---:|---:|
|__init__.py|3/3|0/0|100.0000%|
|__main__.py|32/33|7/8|95.1220%|
|accounts.py|50/50|19/20|98.5714%|
|backup.py|71/74|9/12|93.0233%|
|configurations.py|38/38|10/16|88.8889%|
|database.py|59/62|8/8|95.7143%|
|errors.py|11/11|0/0|100.0000%|
|locking.py|33/37|5/8|84.4444%|
|migrations.py|110/111|43/44|98.7097%|
|observations.py|78/78|26/40|88.1356%|
|repositories.py|8/8|0/0|100.0000%|
|repository_base.py|37/37|12/12|100.0000%|
|security_records.py|94/94|16/22|94.8276%|
|storage.py|48/49|15/16|96.9231%|
|time_units.py|26/26|14/14|100.0000%|
|trips.py|133/133|45/62|91.2821%|
|validation.py|39/39|16/16|100.0000%|

## Commity i odbiór

Poprzedni etap:6c3364997bd26cd8a0a0a67ee7505371bf93feef.
Naprawy:
1. fb80ef609632a78fd268ce864ede713c2b98df71 — faktyczne authorizer i dokładny reproduktor.
2. 023198ae149b4953e2311be7c9729ac128d6e405 — schema v2/ms, legacy backup,raw.csv,[from,to),testy.
3. Commit aktualizujący ten raport — dokumentacja ponownego odbioru;
   `git log -1 --format=%H -- docs/school-app/stage3.md` (hash także w odpowiedzi).

- [ ] Potwierdzić branch/status,niezmienny checksum0001,14 tabel/version2.
- [ ] Powtórzyć exact guard test i fresh/legacy CLI workflow z run.md.
- [ ] Powtórzyć 48 testów i pełną regresję w nowym eksporcie.
- [ ] Porównać per-module coverage i granice jednostek/filtrów/owned raw.csv.
- [ ] Zaakceptować etap3 osobno przed promptem na etap4.

STOP przed etapem4. Żadnych DB/runtime/logów/coverage w stagingu.
