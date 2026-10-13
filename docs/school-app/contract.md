# GreenWave School — kontrakt v1, końcowy przegląd etapu 2

Wersja 1.1, 2026-10-12. **Przygotowany do końcowego odbioru**.
Decyzje produktowe zostały ustalone aktualnym promptem użytkownika i zastępują
propozycje z commita 3ff54d9d3c4a7dfb23b53db9095f69f1112427f0.
Nie wracamy do wyboru D1–D7. Ten dokument określa implementację przyszłych
etapów; bieżące działające zakresy i dowody są w stage3–8.md. Stan na wejściu
etapu2 (usunięty prototyp) opisany niżej jest historyczny.

## 1. Stan repozytorium i prywatność

Worktree: C:/Users/konra/.codex/worktrees/school-app/Surfy, codex/school-app.
HEAD na wejściu: 3476d133006a948887899e8b75dcc210ce084248.
Baza kodu: 7ece85993bf860e0bdec0ecb43b65532242166eb; audyt:
bb99de3d808db8898426b42203e6c5e979e527be. Usunięcie prototypu było decyzją
użytkownika; nie odtwarzamy go. Obowiązują instrukcje czatu; repozytoryjnego
AGENTS.md brak, nadrzędny C:/Users/konra/.codex/AGENTS.md jest pusty.

Wykonano wyłącznie kontrolę nazw i metadanych Git oraz lokalnego istnienia,
rozmiaru i mtime plików runtime; nie otwierano DB, logów, mediów, prywatnego
data/runs ani zawartości runtime. Reguły ignorowania zachowują wcześniejsze
reguły i obejmują runtime, artifacts, coverage oraz używane środowiska/raporty.
7a2899770075cc6ac12c826234f620f1de97a380 usuwa 7 ścieżek runtime tylko z Git.
Wszystkie siedem pozostaje lokalnie, z niezmienionym rozmiarem i mtime.

**Otwarty problem PUBLISH-01**: wcześniejszy commit 3476d13 nadal zawiera
runtime. Lokalny origin/codex/school-app zawiera ten commit, a użytkownik
wskazał wcześniejszą publikację. Nowy commit nie usuwa danych z historii,
klonów ani cache hostingu. Bez czytania danych nie określamy ich charakteru
ani nie nazywamy ich syntetycznymi; nie potwierdzamy także braku wrażliwych danych.
Dalsze opcje do osobnej decyzji: prywatny przegląd przez właściciela danych,
ocena dostępu do repo i ewentualna zmiana credentials, jeżeli takie ujawniono;
pozostawienie historii dopiero po świadomej ocenie; albo uzgodnione z innymi
użytkownikami repo usunięcie historii/odniesień i kontakt z hostingiem w sprawie
cache. Niczego z tych działań nie wykonano. Brak rewrite, force push, nowego
worktree, automatycznego push lub merge. PUBLISH-01 jest osobnym problemem,
nie warunkiem ukrytym w implementacji szkolnego demo.

## 2. Problem domenowy, scenariusze i zakres

GreenWave bada płynny przejazd przez kolejne światła zgodnie z ograniczeniami
prędkości. Wiarygodny profil wymaga GPS/prędkości, właściwej kierunkowej linii,
limitu, faz i zgodnego zegara. Konto ani rozpoznanie lampy nie dostarcza tego
zestawu. Obserwacja STATE_SEEN nie dowodzi STATE_START; moment kliknięcia ma
nieznane opóźnienie reakcji. Obserwacje w czasie jazdy obsługuje pasażer.

| Scenariusz | Przepływ i kategoria |
|---|---|
|SC-AUTH|Rejestracja DRIVER, aktywacja email, login/logout, zmiana/reset hasła — obowiązkowe v1|
|SC-ADMIN|Bootstrap CLI, role/blokady/reauth i audyt bez czytania cudzych przejazdów — obowiązkowe v1|
|SC-TRIP|Utworzenie własnego przejazdu, filtrowanie, tytuł/notatka, archiwizacja i własny eksport — obowiązkowe v1|
|SC-OBS|Własne obserwacje i osobne korekty, filtry i historia — obowiązkowe v1|
|SC-SHARE|Jeden ukończony przejazd udostępniony jednemu aktywnemu analitykowi, cofnięcie — obowiązkowe v1|
|SC-CONFIG|Odczyt opublikowanych konfiguracji; ANALYST/ADMIN tworzy DRAFT, ADMIN publikuje — obowiązkowe v1|
|SC-PHONE|Własne parowanie, rozdzielone tokeny i revokacja — polityka obowiązkowa v1, transport Android wymaga integracji M8|
|SC-NAV|Jedna sesja jazdy na deployment, SIM/LIVE i blokady GATE — zachowana funkcja M8 z bezpieczną integracją|
|SC-REPLAY|Własny lub jawnie udostępniony replay, bez zmiany live — zachowana funkcja M8|
|SC-ANALYSIS|Zadanie/raport własnego lub udostępnionego przejazdu — zachowana funkcja M8|
|SC-CV|Diagnostyka, capture, review i media wyłącznie właściciela — zachowana funkcja CV|
|SC-RECOVERY|Migracje, backup, odzyskanie zapisu po awarii i niezmienność oryginałów — obowiązkowe v1|

| Widok | Zachowanie |
|---|---|
|Nawigacja|Mapa perspektywiczna, prędkość, znany limit, następne światła/nazwy/źródła/wiek; diagnostyka poza głównym ekranem|
|Moje przejazdy|Wyłącznie własne rekordy i akcje; analityk ma osobny filtr udostępnionych przejazdów|
|Moje obserwacje|Oryginał i efektywna wartość, filtry, korekta z powodem i historią|
|Laboratorium|Własna symulacja/replay/analiza/CV; analityk tylko replay i analiza udostępnionych przejazdów, bez filmu|
|Administracja|Konta, role, blokady i konfiguracja; nie jest przeglądarką wszystkich GPS/nagrań|

Poza v1: awaryjne udostępnianie danych adminowi, oddzielne zgody eksportu/mediów,
grupy/projekty, powiadomienia o dostępie admina, upload i biblioteka filmów,
operacyjny import starych danych, fizyczne usuwanie raw/kont, wiele równoczesnych
jazd, ogólnomiejski routing i automatyczne uczenie faz z CV. Import operatorski
może być osobno zlecony później; nie jest warunkiem ukończenia demo.

### GATE pozostaje niezmienione

Zachować evaluate_live_navigation i _live_recommendation_eligibility: świeże
kwalifikowane GPS, MATCHED/FORWARD, FIELD_CHECKED geometria/linia/limit,
prawidłowy sygnał, zweryfikowane fazy z ważnymi oknami i zgodny zegar.
UI dodatkowo sprawdza status/zakres solvera, limit/prędkość i świeżość odpowiedzi
(2 s); GPS provider nadal ocenia wiek pomiaru. Brak przesłanki daje null target/
range, brak „Przyspiesz/Zwolnij” i jawny powód. Replay nie daje rady live.
CV pozostaje diagnostyczne; role, publikacja config i korekty nie nadają
wiarygodności fazom/liniom/YOLO ani nie zasilają learningu.

Demo: osobny runtime/DB, syntetyczne fixture'y/adresy example.test i Mailpit,
stała etykieta DEMO; bez telefonu/ADB/kamery/YOLO i bez mountu realnych danych.
Brak publicznych haseł: opcjonalne konta demo tworzone CLI z hasłem operatora.
Realny profil używa osobnego root, poprawnej poczty i HTTPS dla sieci; localhost/
ADB jest jawnym trybem lokalnym. Prawdziwy GPS nigdy nie udaje punktów demo.

## 3. Tożsamość, sesje i SMTP

Role rozłączne DRIVER, ANALYST, ADMIN; wszystkie mogą mieć własne dane.
Register przyjmuje email,display_name,password,password_confirmation; zawsze
DRIVER/PENDING_VERIFICATION. role/owner/active/verified z body odrzucone.
Email: ASCII, trim, <=254 znaków, local-part<=64, jedna @, bez control/whitespace,
domena z kropką i etykietami DNS1–63 bez brzegowego myślnika. Całość lowercase
jako jawna reguła identyfikatora; nie usuwać kropek ani +tagów, nie transliterować
EAI/Unicode. UNIQUE email_normalized; display_name trim Unicode1–80 bez control.
Zmiana email poza v1. Format nie zastępuje aktywacji.

Poprawny request rejestracji dla nowego/istniejącego email daje jednakowe202.
Nowe konto otrzymuje SMTP link VERIFY_EMAIL z tokenem>=32B, hash,24h,single-use;
nie ma dostępu przed aktywacją. Istniejący adres nie powoduje publicznego
conflict/existence response. Login jest jednolity401 dla błędnego hasła,
nieistniejącego, zablokowanego lub nieaktywowanego konta.

Bootstrap pierwszego ADMIN przez CLI/getpass, transakcja sprawdza brak aktywnego
admina, audyt BOOTSTRAP_ADMIN. Brak stałych publicznych credentials i publicznego
bootstrap API. Kolejni admini przez zmianę roli aktywnego verified konta po reauth.
Ostatniego aktywnego admina nie można zablokować ani zdegradować. Operator OS/DB
ma własne uprawnienia infrastruktury, nie jest ukrytym uprawnieniem API ADMIN.

Hasło12–128 znaków Unicode i <=512B UTF-8, bez trim/normalizacji; confirmation
równe. Scrypt: początkowo n=131072,r=8,p=1,dklen32,sól>=16B,wersjonowany format,
maxmem256MiB i max2 kosztowne równoległe operacje. **Wymagany pomiar czasu/RAM
na docelowym sprzęcie przed wdrożeniem**; zmiana parametrów jawna, z testami,
bez cichego osłabienia. compare_digest, dummy hash przy braku konta i rehash
starszych parametrów przy poprawnym loginie. Bez haseł/raw tokenów w DB/logach.

Trwałe rate limits: login5 błędów/email/15min i30 prób/IP/15min; register5/IP/h;
reset/activation3/email/h i10/IP/h; reset-use10/IP/15min; reauth5/session/15min;
pair5 nieudanych/IP/5min i5/code. Email kluczowany HMAC, także nieistniejący;
jednakowy algorytm/429/Retry-After, bez trwałego blokowania kont przez napastnika.
Nie ufać forwarded IP bez trusted proxy. Udostępnianie max10 prób/user/h;
błąd odbiorcy neutralny, brak publicznej wyszukiwarki kont.

Browser session: losowy>=32B secret, tylko SHA256 w DB, stabilny nietajny id,
user/security_version/authenticated_at, idle30min/absolute8h. Activity zapis
max1/min; podczas aktywnego nagrania własny autoryzowany telefon może odświeżać
idle parent, nigdy absolute. Nowy sekret przy loginie i reauth, stare nieważne,
CSRF rotuje razem z nim; deadline absolute nie rośnie. Brak osobnego procesu
odnawiania kont/zasobów ani localStorage bearer. Cookie gw_session:
HttpOnly,SameSite=Strict,Path=/,bez Domain,Secure w HTTPS,Max-Age<=absolute TTL.
Wyłączenie Secure tylko jawne localhost dev/demo HTTP.

CSRF: 32B HMAC(CSRF_KEY,raw cookie secret+session id), hash w DB;
/auth/me może odtworzyć token z bieżącego cookie. Wszystkie browser POST/PATCH/
DELETE wymagają X-CSRF-Token i exact Origin PUBLIC_BASE_URL. Preauth cookie+
CSRF w pamięci,TTL15min dla anonymous login/register/reset/verify, bez praw konta;
po restart odświeżyć preflight. Host allowlist dokładna, nie sam port; brak CORS,
no-store/nosniff, Referrer-Policy no-referrer, nowy UI CSP bez unsafe-inline;
TLS/HSTS na proxy. Sekrety deploymentu/SMTP poza Git, bez tokenów w URL query.

Logout revokuje bieżącą sesję, jej pair challenges/device credential i kończy
związane nagranie/nav/replay; inne sesje konta nie są automatycznie wylogowane.
Password change/reset, block i role change: security_version++, revoke wszystkich
browser/device/account tokens konta, stop aktywnych kontekstów. Zmiana roli
wymaga nowego loginu; granty cofane gdy odbiorca przestaje być aktywnym ANALYST.
Unblock nie ożywia sekretów; ACTIVE wymaga verified_email_at. Ostatni admin409.
Backend i cleanup egzekwują expiry, nie tylko UI.401 czyści prywatny cache i rady,
stop polling/media, pokazuje login; nie powtarza automatycznie niezapisanej mutacji.

### Wspólny mechanizm aktywacji/resetu

Account token ma purpose VERIFY_EMAIL lub RESET, random32B, tylko hash,
issued/expiry/used/revoked/security_version i delivery_state. Reset ACTIVE konta:
neutralne202, poprzedni niewykorzystany RESET revoke, TTL15min; link tylko SMTP,
nie odpowiedź anonimowemu API. VERIFY_EMAIL TTL24h. GET linku nie consume;
POST z preauth CSRF zużywa właściwy purpose raz w transakcji BEGIN IMMEDIATE.
RESET zmienia hash i odcina sesje/urządzenia; VERIFY_EMAIL aktywuje tylko
PENDING account bez blokady. Expired/used/invalid:jednolite422 INVALID_TOKEN.
Dwa równoległe użycia: max1 sukces. Po resecie brak auto-login.

Link z zaufanego PUBLIC_BASE_URL i fragmentu /#reset=... albo /#verify=...;
UI bierze token do pamięci, czyści fragment, nie ładuje external resources.
Nie logować tokenu ani payloadu SMTP. SMTP poza transakcją DB, timeout5s,
STARTTLS/SMTPS z cert verify dla realnych danych. Nie utrwalać surowego tokenu
w outbox DB. Kolejka pamięci max100; po awarii/restart niewysłane tokeny revoke,
notification bez sekretu może być ponowiona, użytkownik może zażądać nowego
linku po cooldown. Crash po wysyłce przed SENT może unieważnić dostarczony link:
jawny bezpieczny kompromis, nie obietnica trwałego retry sekretu.

Docker demo: Mailpit SMTP w prywatnej sieci, UI skrzynki bind127.0.0.1 tylko dla
operatora, wyłącznie adresy/treści syntetyczne; bez publicznego portu SMTP.
Realny profil: DEMO off, osobny wolumen, HTTPS base URL, nadawca i poprawna
konfiguracja SMTP/secrets/TLS. Nie używać demo mailbox dla realnych danych.
Brak poprawnej wymaganej konfiguracji zatrzymuje start deploymentu portalu.
To przyszła implementacja; obecna baza M8 nie ma tych mechanizmów kont.

## 4. Końcowa polityka dostępu

O=właściciel niezależnie od jego roli. S=jedno aktywne READ_ANALYZE dla aktywnego
ANALYST na konkretny ukończony trip. Brak automatycznego dostępu ADMIN do cudzych
danych; rola nie zastępuje O/S. UI nie jest jedyną kontrolą.

| Zasób/akcja | Anonimowy | DRIVER | ANALYST | ADMIN |
|---|---|---|---|---|
|Publiczny shell/health/auth/reset|Publiczne kontrakty|Tak|Tak|Tak|
|Własne trip/observation create/read|—|O|O|O|
|Edit title/note,archive zamkniętego trip|—|O|O|O|
|Korekta i historia własnych obserwacji|—|O|O|O|
|Udostępnione metadata/observation/history|—|—|S,tylko read|—|
|GPS replay/analysis/result|—|O|O lub S|O|
|Eksport i raw/media/preview CV|—|O|O,nie S|O|
|Własne urządzenia/nav/capture/review|—|O;nav/capture+lease|O;nav/capture+lease|O;nav/capture+lease|
|Share/cofnięcie|—|O|O własnego trip|O własnego trip|
|Wspólne config read|—|Published|Published oraz DRAFT|Published oraz DRAFT|
|Nowy wspólny config DRAFT|—|—|Tak|Tak|
|Config publish/archive|—|—|—|Tak+reauth/audit|
|Konta/role/block/audit administracyjny|—|—|—|Tak+reauth dla mutacji;bez GPS/media|
|Fizyczne delete raw/oryginałów|—|—|—|— w API v1|
|Nadanie FIELD_CHECKED/verified przez UI|—|—|—|—;niezależna procedura terenowa|

Share: O wybiera jeden COMPLETE niearchiwalny trip i aktywnego ANALYST po
exact email. V1 dopuszcza najwyżej jedno aktywne udostępnienie na trip, bez grup,
projektów, TTL/scopes wyboru i automatycznego dziedziczenia kolejnych trip.
Permission zawsze READ_ANALYZE: metadata,obserwacje,historia korekt,GPS replay,
wynik analizy. Formularz jawnie mówi „Udostępniasz przebieg GPS tego przejazdu”.
Analityk nie edytuje danych O. Eksport endpoint i CV (także podglądy/filenames)
wyłącznie O. Żadne dodatkowe checkboxy zgód lub przekazywanie dostępu dalej.

Revoke/archiwizacja/block/zmiana roli odbiorcy odcina kolejne odczyty i jobs;
check przy każdej stronie,replay,job execution/status/result. Stop zależnych
contexts i cache; raport pozostaje O. Już obejrzanych/pobranych odpowiedzi
nie można cofnąć ani zagwarantować, że analityk nie wykona ich kopii; UI nie
obiecuje takiej ochrony. Własność zawsze przez parent trip FK.

## 5. Trwałe tabele, runtime i storage

**14 obowiązkowych nowych tabel**. Każda poniżej ma scenariusz; liczba wynika
z trwałości, integralności i polityki, nie z arbitralnego limitu tabel.
SQLite school.sqlite3 jest źródłem kont/polityk/metadanych/korekt/audytu.
Raw/media+manifest są źródłem surowych faktów. ID losowe32 lowercase hex;
UTC integer milisekundy; NULL oznacza brak wiedzy. FK ON, WAL, synchronous FULL,
busy_timeout5s, SQL parametryzowane. Ograniczenia wersji/statusów/CHECK wymagane.

| Tabela | Klucze, relacje i istotne pola | Indeksy/ograniczenia | Scenariusz |
|---|---|---|---|
|schema_migrations|version PK,checksum,applied_at,app_version|Ciągłość i checksum niezmienny;PRAGMA user_version mirror|SC-RECOVERY|
|users|id PK,email_normalized/display,display_name,password_hash,role,status,verified_email_at,security_version,revision,times|UNIQUE email_normalized;enum roli/statusu;versions>=1;ON DELETE RESTRICT|SC-AUTH,SC-ADMIN|
|browser_sessions|id PK,secret_hash,csrf_hash,user_id FK,security_version,authenticated_at,created/activity/absolute_expiry,revoked|UNIQUE secret_hash;idx(user,revoked),idx(expiry)|SC-AUTH,SC-PHONE|
|account_tokens|id PK,user FK,purpose,secret_hash,issued/expiry/used/revoked,security_version,delivery_state|UNIQUE hash;1 unused/user/purpose w transaction;idx(user,purpose,expiry)|SC-AUTH|
|auth_rate_limits|key_hmac,purpose,window_start composite PK,attempts/failures,blocked_until|Counts>=0,ograniczona retencja;email bez plaintext|SC-AUTH,SC-PHONE,SC-SHARE|
|devices|id PK,owner FK,client_device_id,label,status,token_hash nullable,parent_browser_session FK,boot_id,security_version,expiry/revoked,last_seen|UNIQUE(owner,client_device_id),UNIQUE token_hash;idx(owner,status);jedna bieżąca credential/device|SC-PHONE|
|pairing_challenges|id PK,code_hmac,owner/parent_session FK,boot_id,label,expiry,attempts,used/revoked|UNIQUE aktywny code;1 active/session;TTL5min,max5prób|SC-PHONE|
|trips|id PK,owner FK,title,note,mode,route_version FKnullable,status,created/start/end,run_id/path/hashes nullable,revision,archived|idx(owner,created,id),idx(owner,route,status,created);mode SIMULATION/LIVE,status enum;COMPLETE wymaga manifestu|SC-TRIP,SC-NAV,SC-RECOVERY|
|observations|id PK,trip FK,signal_id,source,state,event_type,server_received/measured nullable,geometry_hash,raw_sequence nullable,source_event_id,journaling_state|UNIQUE(trip,source,source_event_id);idx(trip,received,id),idx(trip,signal,state,type,time);append-only|SC-OBS,SC-CV|
|observation_corrections|id PK,observation/actor FK,sequence,before/after,reason,server_at,previous_revision,client_operation_id|UNIQUE(obs,sequence),UNIQUE(actor,client_operation_id);append-only;idx(obs,sequence)|SC-OBS|
|trip_shares|id PK,trip/analyst/grantor FK,permission READ_ANALYZE,created,revoked|UNIQUE active trip;grantor=owner w transaction;idx(analyst,revoked);odbiorca ACTIVE ANALYST|SC-SHARE|
|audit_events|sequence PK,actor nullable/type,action,resource_type/id,reason,UTC,request_id,outcome|append-only;idx(actor,UTC),idx(resource,id,UTC);bez sekretów/GPS|SC-AUTH,SC-ADMIN,SC-TRIP,SC-OBS,SC-SHARE,SC-CONFIG,SC-RECOVERY|
|config_versions|id PK,kind ROUTE/SIGNAL/MODEL,logical_id,version,payload/hash,status,creator FK,created/published,revision|UNIQUE(kind,logical_id,version);DRAFT/PUBLISHED/ARCHIVED;published immutable|SC-CONFIG|
|recording_operations|id PK,trip/actor FK,kind START/FINISH/JOURNAL_OBSERVATION,idempotency_key,request_hash,state,result_ref|UNIQUE(actor,kind,key);PENDING/APPLIED/FAILED;bounded trusted paths;recovery nie gubi intent|SC-NAV,SC-OBS,SC-RECOVERY|

Device przechowuje tylko bieżący hash credential; poprzedni jest revokowany,
a audyt zachowuje metadane zdarzenia bez secretu. Osobna tabela wielokrotnych
credentials jest zbędna w v1. Own observations wynikają z trip FK, nie dowolnego
owner_id. Trigger/warstwa storage zabrania zwykłego UPDATE/DELETE oryginału,
korekt i audytu; mutable journaling_state jest metadanym transportu, nie faktem
obserwacji. Jeśli trigger obejmuje observations, dopuszcza wyłącznie zmianę
journaling_state/raw_sequence po porównaniu niezmiennych kolumn.

Stany trip: PLANNED,STARTING,RECORDING,FINALIZING,COMPLETE,INTERRUPTED.
Archive to znacznik, nie nadpisanie oryginału. Edit przez O tylko title1–120
i note0–1000 z expected_revision; mode/route/owner/run/times wybrane przy create
lub przez serwer i nie są edytowalne po starcie. Route wersja przy tworzeniu
ma immutable snapshot/hash. Archive tylko zamkniętego trip (PLANNED/COMPLETE/
INTERRUPTED), revoke share i pochodnych contexts/jobs. Bez restore/purge endpoint
w v1; archived pozostaje dostępny właścicielowi w jawnym filtrze archiwum.

Observation source MANUAL albo diagnostyczny CV; kolor RED/YELLOW/GREEN/
RED_YELLOW/OFF/UNKNOWN, type STATE_SEEN/STATE_START. UNKNOWN nie START.
Actor/source/czas serwera nie z body. Korekta może zmienić state,event_type,valid
z reason3–500,before/after,actor,UTC i expected_revision; nie zmienia GPS,źródła,
czasu pomiaru,trip ani raw. Oryginał i efektywna wartość widoczne osobno.
Retrospektywna adnotacja ukończonego trip ma measured_at=null i etykietę
historyczną; nie udaje kliknięcia live ani nie dopisuje do ukończonego raw.

### Dane odtwarzalne — bez nowych tabel domenowych

| Stan | Gdzie i dlaczego | Restart / revoke |
|---|---|---|
|Preauth CSRF|Pamięć,TTL15min,limit IP;nie daje praw konta i nie wymaga trwałości|Nowy preflight;stare tokeny nieważne|
|Globalny lease/nav/matcher/clock|Pamięć jednego procesu,mutex + trip/recording intent w DB;nie wznawiamy jazdy po crash|Nowy boot,cleanup,trip INTERRUPTED;drugi start409|
|Replay contexts|Pamięć per browser session+replay_id,max1,TTL30min;pozycja suwaka nie jest domeną|Handle znika;trzeba ponownie load,bez wpływu na live|
|Analysis jobs|Pamięć:actor,trip,authorization,status/progress;max2global/max1actortrip/queue20|Nie wznawiać po crash;audyt i manifest raportu wskazują przerwany job;nowe zlecenie|
|Wyniki analizy|Trwały plik derived z metadanymi,hash,trip ID i snapshot korekt;źródło auth nadal DB trip/share|O zachowuje raport;analityk czyta go tylko z aktywnym share|
|Capture/assignment|Istniejący worker/manifest i per-trip CV SQLite;stare globalne defaults zabronione|Nie wznawiać świeżości/assignment;dane źródłowe zachowane O|

Ograniczenie: jeden proces na runtime volume. Startup lock operatorski nie
pozwala uruchomić dwóch procesów portalu na tym samym root. Nie zastępujemy
tego niejawnie rozproszonym schedulerem. Nie potrzeba nowych tabel preauth,
nav/replay/jobs,powiadomień/zgód medialnych/biblioteki filmów. Job result to trwały
artefakt, podczas gdy jego uchwyt/status wykonania jest runtime.

Istniejące SQL caches do integracji (nie 14 nowych tabel): jedna tabela
observations w indeksie historii M8 oraz events,cursors,decisions,assignments
w per-trip reviews.sqlite3 CV. Zachować te funkcje, ale wstrzyknąć poprawny root,
autor review z sesji i audyt. Są odtwarzalnymi indeksami lub oddzielnym
append-only dziennikiem CV; nie nadają ról/owner. Nie budujemy nowej biblioteki.

### Storage i źródła prawdy

Read-only seeds data/maps/routes/corridors/prediction. Nowe wersje wspólne
runtime/shared/config/{version_id}, bez prywatnych GPS. Portal root:
runtime/owners/{uid}/trips/{tid}/runs/{runid}, trip-root/derived i trip-root/cv/{cid}.
Indeks M8 runtime/owners/{uid}/indexes, CV reviews w trip-root. Każdy logger,
history,capture,replay/job dostaje jawny autoryzowany context; nie dziedziczy
DATA/runs ani DATA/derived z LocalServer. Resolver najpierw DB owner/share,
potem resolved containment i zakaz symlink/reparse escape; nie path z query.

Indeksy importują tylko runs własnego/scoped trip, nigdy całe data/runs.
Korekty i owner w szkolnej DB nie mogą zostać zastąpione rebuildem cache.
Raw manifesty nie są nadpisywane przez korekty. Raport zapisuje raw/config/geometry
hash i watermark korekt; kolejne korekty wymagają nowego job, stary raport
nie zmienia się po cichu i nie zasila modelu faz.

### Transakcje, recovery i migracje

DB i plik nie są jedną transakcją. Durable recording intent/idempotency obejmuje
start/finish/manual journaling. Key32–64ASCII + request hash,repeat=same result,
inny payload409. Start:DB STARTING+intent → nowy run+flush/fsync → RECORDING.
Finish:FINALIZING → close raw → manifest temp/fsync/atomic rename w tym samym
filesystem → hashcheck → COMPLETE. File/DBfail zachowuje evidence i INTERRUPTED/
FAILED; nigdy nie fabrykuje complete.json. Source_event_id i client_operation_id
zapobiegają mnożeniu obserwacji/korekt; grant repeat idempotentny dla tego samego
odbiorcy, inny aktywny odbiorca wymaga revoke poprzedniego share.

Manual:DB immutable event+intent+audit,worker dopisuje raw z tym samym ID;
recovery sprawdza ID/sequence, nie dopisuje do zakończonego raw. Brakujący zapis
zostaje DB z journaling error,UI nie obiecuje sukcesu obu magazynów. Active SIM
manual może przeliczyć model syntetyczny; LIVE tylko zapisuje fakt. Korekta
nie zmienia raw ani nie nadaje fazom verified.

Restart:new boot,revoke device credentials/challenges,nav/replay handles znikają;
active trip bez validmanifest INTERRUPTED. Validmanifest po utracie ostatniego
DBcommit można odtworzyć jako COMPLETE+RECOVERY audit,bez zmiany raw. Orphans
kwarantanna,nie automatyczna publikacja. Authorization sprawdzać przed job
execution i przy result; revoke/block/role odcina future reads. Ograniczona
systemowa finalizacja rozpoczętego raw może działać po logout z audytem,bez
prawa ujawniania go innemu użytkownikowi.

Migration0001... SQL/Python z checksum,transakcją,FK/integritycheck i
schema_migrations;user_version mirror,nowsza/niezgodna DB odmawia startu.
Maintenance lock,stop ingest/job/capture,finish aktywnych nagrań;SQLite backup API
(nie samo copy.db przy WAL),manifest backupu DB/config/version/artefacts.
Raw/media backup prywatny poza Git/demo. SQLfail ROLLBACK;failed postcheck
blokuje start i operator restore snapshot+pasujący kod. Bez cichego downgrade.
Istniejący runtime prototypu nie jest automatycznie migrowany. Stare ownerless
pliki niewidoczne; ewentualny późniejszy import operatorski osobno zlecany,
read-only źródło, jawny owner,hash/manifest i audyt — poza szkolnym demo v1.

## 6. Izolacja nawigacji i telefonu

Jedna active nav/recording na deployment. O startuje własny PLANNED trip SIM
albo LIVE; mutex/lease i record intent atomowo rezerwują slot. Drugi user/admin409
ACTIVE_SESSION_BUSY: „Inny użytkownik ma aktywną sesję jazdy. Możesz przeglądać
własne dane lub replay”; bez jego identity/pozycji. Admin nie przejmuje slotu.
Pause SIM zachowuje nagranie/slot; LIVE nie zamraża GPS,tylko FINISH. Worker
heartbeat deadline10s;cleanup po awarii uwalnia slot i oznacza INTERRUPTED.

Device bearer odrębny od browser cookie/app_session_id, zapisany jako hash
w devices i boundowner,parent session,boot,security_version;max8h i<=parent TTL.
Challenge6cyfr HMAC deploymentsecret,unikalny active,5min,single-use,max5prób.
Owner wyłącznie z challenge, nie owner_id telefonu. Token scope TELEMETRY:
minimum own device session/status i ingest, bez list/export/role/route/control.
StartLIVE wybiera wcześniej sparowane własne urządzenie,max1active/session.
GPS source/stream/sequence/czasy i devicebinding weryfikuje backend;duplicate ack
bez kolejnego zapisu. Demo nie paruje realnego telefonu/kamery.

Logout parent kończy phone i nagranie;revoke/block/role/password odcina credentials.
Browser session może przetrwać restart do TTL, ale nav nowa i **nowe parowanie**.
Buffered samples poprzedniego boot nie mogą wejść do nowego run lub stać się FRESH.
403 DEVICE_REPAIR_REQUIRED,409 SESSION_CHANGED;minimalnyGET device/session z
bearer. Obecny PairingClient wysyła tylko code; potrzebna późniejsza zmiana na
code+client_device_id+label, obsługa null app_session_id przed startem,authenticated
session refresh w HttpJson/TelemetryTransmitter (dziś GET /api/state bez tokenu).
Regresja legacy/native transportu i sprzętowy odbiór pozostają w etapie9.

## 7. API, DTO i formularze

Docelowy namespace /school/api/v1. C01–C37 to **37 obowiązkowych kontraktów
szkolnego v1**. M01–M26 to **26 adapterów zachowanych funkcji M8/CV**, które
muszą mieć bezpieczną integrację; nie stanowią nowych procesów biblioteki mediów.
Metoda+ścieżka liczone raz; trzy aliases Android opisane niżej nie są dodatkowymi
funkcjami. Każdy endpoint ma scenariusz z §2. Shell/assets statyczne nie są API.

Defaultdeny;user/actor/owner z backendu,scope przed SELECT/plik/job. C=browser
X-CSRF-Token+exactOrigin,P=preauth+Origin,D=ograniczony device bearer (pair:code),
bez cookie/CSRF telefonu. Browser mutacje nie mogą używać D. Unknown/duplicate
fields/query,NaN/Infinity/control/niepoprawneID odrzucane. JSON UTF-8 object,
Content-Type application/json,body<=8192B; configpayload<=262144B. UUID zasobu
hex32,client event ID32–64ASCII. GET nie mutuje trwałej polityki.

Success:{data:DTO,request_id};listy dodatkowo page:{limit,next_cursor}.
Error:{error:{code,message,fields?},request_id},bez SQL/stack/path/sekretu.
200read/update,201create,202async/neutral,204revoke/archive,400malformed/cursor,
401brak/expiredsession,403rola/CSRF/device,404missing **lub foreign privateID**,
409revision/state/idempotency/busy,413body,415type,422fields/invalidtoken,
429Retry-After,503I/O/capacity,500neutralrequestid. Te kody obowiązują wszystkie
wiersze. Anon restricted zawsze401 bez ujawniania istnienia ID;zasób udostępniony
niedostępny po revoke daje404 nawet gdy dawniej był czytelny.

DTO:
User{id,email,display_name,role,status,revision};Session{User,csrf,expires_at,demo};
Trip{id,title,note,mode,route_version/hash,status,created/start/end,revision,
archived,journaling_status,share tylko dla O};Observation{id,trip_id,signal_id,
source,original{state,event_type,server_received_at,measured_at},effective{state,
event_type,valid},revision,corrections_count};Correction{id,actor,server_at,
before,after,reason,revision};Share{id,trip_id,analyst,permission READ_ANALYZE,
created,revoked};Device{id,label,status,created,last_seen};Version{id,kind,
logical_id,version,hash,status,payload,revision};Navigation{id,trip_id,revision,mode,
sample/quality,route/match/nextlights,recommendationnullable,eligibility.reason_codes,
response_at};Replay{id,trip,mode,duration,time,rate,paused,sample/provenance};
Job{id,trip,type,status,progressnullable,result_id?,error?};Report{id,trip,type,
source_hashes,correction_watermark,created,metrics};Capture{id,trip,status,
source_mode,frame_ref/age,diagnostic_only=true,synchronization};Audit{actor,
action,resource_type/id,UTC,reason,outcome}. Sekrety/hash/path nie trafiają do DTO,
poza jawnie wydanym własnym CSRF/device credential;reset/verify token nigdy w API.

Listy default25,max100,sort created_at DESC,id DESC lub obieASC;observations
używa server_received_at. KeysetcursorHMAC boundactor+filterhash+sort+as_of+
lastkey,TTL15min;zmiana actor/filters/sort→400. Auth przy każdej stronie.
Datefrom inclusive,to exclusive,UTC RFC3339 z TZ,from<to,max366dni;bezdat pełna
historia stronicowana. UI Europe/Warsaw przelicza lokalne dni z DST na UTC.
Trip filters:created_at daty,route_id,status,archived,scopeown/shared.
Observations:server_received_at daty,route_id,trip_id,signal_id,stateefektywny,
event_type,source,valid,scopeown/shared. Actualstart/end osobno w TripDTO.

### 7.1 Obowiązkowe endpointy v1

| ID | Metoda / ścieżka | Konto / polityka | Pola żądania | Odpowiedź | Walidacja / szczególne błędy | CSRF | Scenariusz |
|---|---|---|---|---|---|---|---|
|C01|GET /auth/preflight|Anon lub session|—|csrf,expiry + preauth cookie|TTL15min,limit IP,503capacity|—|SC-AUTH|
|C02|POST /auth/register|Anon|email,display_name,password,password_confirmation|202 neutral message|§3,email/password limits,role forbidden|P|SC-AUTH|
|C03|POST /auth/verify-email|Anon|token|200 activation message|24h,purpose,single-use,422INVALID_TOKEN|P|SC-AUTH|
|C04|POST /auth/login|Anon|email,password|Session + cookie|Jednolite401,429,dummyhash|P|SC-AUTH|
|C05|GET /auth/me|Active session|—|Session|401revoked/expired,no private globalstate|—|SC-AUTH|
|C06|POST /auth/reauth|Session|password|authenticated_until,csrf + rotatedcookie|5min,401/429,no rolechange|C|SC-AUTH,SC-ADMIN|
|C07|POST /auth/logout|Bieżąca session|{}|204clearcookie|Idempotentny;active wymagaCSRF;expired tylko clearcookie|C gdy active|SC-AUTH,SC-PHONE|
|C08|POST /auth/change-password|Session|current_password,new_password,password_confirmation|200message + clearcookie|401current,422fields;revokeallcredentials|C|SC-AUTH|
|C09|POST /auth/request-reset|Anon|email|202neutralmessage|§3,no token/link,purposeRESET,rate limits|P|SC-AUTH|
|C10|POST /auth/reset-password|Anon|token,password,password_confirmation|200message + clearcookie|15min,single-use,422INVALID_TOKEN,no auto-login|P|SC-AUTH|
|C11|GET /trips|O;ANALYST także S|from,to,route_id,status,archived=false,scope=own/shared,limit,cursor,sort|Trip[] + page|§7 filters/cursor;ADMIN nie global listing|—|SC-TRIP,SC-SHARE|
|C12|POST /trips|O|title,note?,mode,route_version_id?|201Trip|title1–120,note0–1000,LIVE route required,SIM synthetic;no owner/status|C|SC-TRIP|
|C13|GET /trips/{trip_id}|O lub S|ID|Trip + capabilities|Share details tylko O;404foreign|—|SC-TRIP,SC-SHARE|
|C14|PATCH /trips/{trip_id}|O|expected_revision,title?,note?|Trip|Min1 editablefield;409revision;no route/owner/status edit|C|SC-TRIP|
|C15|DELETE /trips/{trip_id}|O|expected_revision,reason|204softarchive|reason3–500,closed only;409active,no rawdelete|C|SC-TRIP|
|C16|GET /trips/{trip_id}/export|O,nie S|—|ZIP Content-Disposition|Validcomplete/hash,max1export/actor;409corrupt/notcomplete|—|SC-TRIP|
|C17|GET /observations|O lub ANALYST S|from,to,route_id,trip_id?,signal_id,state,event_type,source?,valid?,scope,limit,cursor,sort|Observation[] + page|Enums §5,effective state,datefilter received|—|SC-OBS,SC-SHARE|
|C18|POST /trips/{trip_id}/observations|O|signal_id,state,event_type,source_event_id|201Observation + journalingstate|SourceMANUAL backend;signal in frozenroute/SIM;UNKNOWN nieSTART|C|SC-OBS|
|C19|POST /observations/{observation_id}/corrections|O|expected_revision,client_operation_id,changes:{state?,event_type?,valid?},reason|201Correction + Observation|Allowlist,reason3–500,409revision;immutableoriginal|C|SC-OBS|
|C20|GET /observations/{observation_id}/corrections|O lub S|limit,cursor,sort|Observation + page Correction[]|Parenttripauth;actor/time/reason,before/after;404foreign|—|SC-OBS,SC-SHARE|
|C21|POST /trips/{trip_id}/share|O|analyst_email|201Share|COMPLETE/nonarchived,ACTIVEANALYST,1active/trip;10attempt/user/h;neutral422recipient;409othershare|C|SC-SHARE|
|C22|DELETE /trips/{trip_id}/share|O|expected_share_id|204revoke|Idempotentne;409SHARE_CHANGED chroni nowszy grant;future read/jobs stop|C|SC-SHARE|
|C23|GET /devices|O|status?,limit,cursor|Device[] + page|No raw token/hash,parent binding|—|SC-PHONE|
|C24|PATCH /devices/{device_id}|O|label|Device|label1–80,404foreign,no statusedit|C|SC-PHONE|
|C25|DELETE /devices/{device_id}|O|reason|204revoke|reason3–500,ownlinkedLIVEfinish,no adminforeignaction|C|SC-PHONE|
|C26|POST /pairing-challenges|O|label|201code,challenge_id,expiry|5min,1/session,6digits;demo403;code only O|C|SC-PHONE|
|C27|DELETE /pairing-challenges/{challenge_id}|O + issuing session|{}|204revoke|Spentcode never reactivated|C|SC-PHONE|
|C28|GET /config/versions|Active account|kind,logical_id,status,limit,cursor|Version[] + page|DRIVER onlyPUBLISHED,DRAFT ANALYST/ADMIN|—|SC-CONFIG|
|C29|GET /config/versions/{version_id}|Active;DRAFT ANALYST/ADMIN|ID|Version|No privatecontent,verification read-only|—|SC-CONFIG|
|C30|POST /config/versions|ANALYST/ADMIN|kind,logical_id,base_version_id?,payload,reason|201DRAFTVersion|262144B,existing schema,coords2..10000,finitephase/dynamics,reason3–500;verificationfields forbidden|C|SC-CONFIG|
|C31|POST /config/versions/{version_id}/publish|ADMIN + reauth|expected_revision,reason|PUBLISHEDVersion|ValidatedDRAFT,409revision,no FIELD_CHECKED shortcut|C|SC-CONFIG,SC-ADMIN|
|C32|DELETE /config/versions/{version_id}|ADMIN + reauth|reason|204archive|reason3–500,oldtrip snapshots unchanged|C|SC-CONFIG,SC-ADMIN|
|C33|GET /admin/users|ADMIN|email exact?,role,status,limit,cursor|User[] + page|No GPS/film/password/hash/token|—|SC-ADMIN|
|C34|PATCH /admin/users/{user_id}|ADMIN + reauth|expected_revision,role?,status? ACTIVE/BLOCKED,reason|User|reason3–500,verified beforeACTIVE,securityversion/revoke,lastactiveADMIN409|C|SC-ADMIN|
|C35|GET /admin/audit|ADMIN|actor?,action?,from,to,limit,cursor|Audit[] + page|Tylko administracja/auth/config;bez trip/observation reasons,GPS/eventpayload/secrets|—|SC-ADMIN|
|C36|GET /maps/{map_id}|Active account|AllowlistedID|BundledGeoJSON + attribution|No arbitrarypath,404unknown,no verificationclaim|—|SC-CONFIG,SC-NAV|
|C37|GET /health|Anon|—|ok,deployment_mode|No users/privatecounts/paths/SMTPsecret,503notready|—|SC-RECOVERY|

### 7.2 Adaptery zachowanych funkcji M8/CV

M01–M26 też podlegają v1 auth/CSRF,rootom,recovery i szerokiemu coverage.
Nie są wyjątkiem od ochrony ani zgodą na nowy rozbudowany workflow mediów.

| ID | Metoda / ścieżka | Konto / polityka | Pola żądania | Odpowiedź | Walidacja / szczególne błędy | CSRF | Scenariusz |
|---|---|---|---|---|---|---|---|
|M01|POST /navigation|O|trip_id,device_id?;Idempotency-Key|201Navigation|PLANNED,mode z trip,LIVE owndevice;globalbusy409,demoLIVE403|C|SC-NAV,SC-PHONE|
|M02|GET /navigation/{navigation_id}|O + parent session|ID|Navigation|GATE/stale/null;404foreign,409closedcontext|—|SC-NAV|
|M03|POST /navigation/{navigation_id}/control|O + parent session|command PAUSE/RESUME/FINISH,expected_revision;Idempotency-Key FINISH|Navigation lub202FINALIZING|SIMpause/resume,LIVE tylkoFINISH;409state|C|SC-NAV,SC-RECOVERY|
|M04|PATCH /navigation/{navigation_id}/simulation|O + SIMlease|rate?,speed_kmh?,follow_recommendation?,revision|Navigation|rate1/2/5/10,speed0..syntheticlimit,bool;LIVE403;reset/model nowytrip|C|SC-NAV|
|M05|POST /trips/{trip_id}/replays|O lub S|mode GPS/SIMULATION|201Replay|COMPLETE+hash,1/session,sourcecompatible;409/422|C|SC-REPLAY,SC-SHARE|
|M06|GET /replays/{replay_id}|Actorcontext + O/S ponownie|ID|Replay|TTL30min,404expired/foreignshare;bez liveguide|—|SC-REPLAY|
|M07|POST /replays/{replay_id}/control|Jak M06|command PLAY/PAUSE/SEEK/RATE,value?|Replay|seek0..duration,rate1/2/5/10,422unknownfields|C|SC-REPLAY|
|M08|DELETE /replays/{replay_id}|Jak M06|{}|204close|Nie mutuje live/raw|C|SC-REPLAY|
|M09|POST /trips/{trip_id}/analysis-jobs|O lub S|type GPS_QUALITY/MAPPING/COMPLETENESS,route_version_id?|202Job|COMPLETE,hashcompatible;max2global,1actortrip,queue20;429/503|C|SC-ANALYSIS,SC-SHARE|
|M10|GET /analysis-jobs/{job_id}|O lub requester z S|ID|Job|Trip/share na każdej próbie;404foreign,no path|—|SC-ANALYSIS|
|M11|DELETE /analysis-jobs/{job_id}|O lub requester z S|{}|204cancel|Report pozostaje O;runtimeworker safeclose|C|SC-ANALYSIS|
|M12|GET /trips/{trip_id}/reports|O lub S|type?,limit,cursor|Report[] + page|Scoped derivedroot,manifest/hashcheck,nie global listing|—|SC-ANALYSIS,SC-SHARE|
|M13|GET /trips/{trip_id}/reports/{report_id}|O lub S|ID|Report + metrics|Trip/hashcheck,currentshare;no media/rawZIP links|—|SC-ANALYSIS,SC-SHARE|
|M14|POST /device/pair|Posiadacz code|code,client_device_id,label|device_token,device_id,app_session_id nullable,server_version|6digits,deviceID1–80ASCII,single-use,rate;403invalid;no owner|D code|SC-PHONE|
|M15|GET /device/session|TELEMETRY bearer|—|app_session_id nullable,active,repair_required|Bounddevice/parent/boot/version,403revoked,no globalstate|D|SC-PHONE|
|M16|POST /device/position|TELEMETRY bearer + own LIVE|Payload §7.3|accepted,duplicate,ownexternal_status/sample|Source/binding/clock/quality;session409;100/min/device;no owner|D|SC-PHONE,SC-NAV|
|M17|GET /trips/{trip_id}/cv/captures|O,nie S|limit,cursor|Capture[] + page|Owntrip CVroot,no filenames otherusers|—|SC-CV|
|M18|POST /trips/{trip_id}/cv/captures|O + ownlease|source_type CAMERA/FILE,source_ref? lub camera_index?,width,height,fps,detection,realtime|202Capture|Existing supervisor;allowlisted own local source,not arbitraryURL;missingmodel422;demoCAMERA403|C|SC-CV|
|M19|GET /trips/{trip_id}/cv/captures/{capture_id}|O,nie S|IDs|Capture|trip-root bound,diagnostic_only;404foreign|—|SC-CV|
|M20|POST /trips/{trip_id}/cv/captures/{capture_id}/stop|O + owncontext|{}|202Capture|Stop własnego workera,nie globalny cudzy|C|SC-CV|
|M21|GET /trips/{trip_id}/cv/captures/{capture_id}/frames/{frame_id}|O,nie S|frame integer>=0|image/jpeg|Boundroot/frame,previewcache32;404missing/foreign|—|SC-CV|
|M22|GET /trips/{trip_id}/cv/captures/{capture_id}/media/{segment}|O,nie S|Range single bytes|206binary Content-Range|segment>=0,max1MiB/chunk,416invalid,scope każdychunk|—|SC-CV|
|M23|GET /trips/{trip_id}/cv/captures/{capture_id}/events|O,nie S|state?,limit,cursor|DiagnosticEvents/reviews + page|Actor/provenance;nie learning,nie publikacja media|—|SC-CV|
|M24|POST /trips/{trip_id}/cv/captures/{capture_id}/associations|O + freshowncontext|track_id,route_version_id,stop_line_id,movement|Diagnostic association|Session/hash/continuity,stale409,movement422,no verifiedflag|C|SC-CV|
|M25|DELETE /trips/{trip_id}/cv/captures/{capture_id}/associations/{track_id}|O + owncontext|IDs|204unassign|Zachowuje detection/audit|C|SC-CV|
|M26|POST /trips/{trip_id}/cv/captures/{capture_id}/reviews|O|event_id,status ACCEPTED/REJECTED,reason,association?,expected_revision,client_operation_id|201Review|Author z sesji,reason3–500,wronggeometry422,revision409,append-only|C|SC-CV|

Operator może ustawić allowlist istniejących lokalnych źródeł CV dla danego owner;
source_ref jest nietajnym kluczem tej konfiguracji, nie dowolnym path dostarczonym
przez browser. Nie budujemy media_assets, uploadu, staging API ani wyszukiwarki
filmów. Wymiary160..3840/120..2160,fps1..60,camera0..16,booleans ścisłe;
source_ref musi być przypisany O i resolved we właściwym root,bez symlink escape.
File replay jest historyczny, nie live road state; brak modelu nie blokuje demo.

### 7.3 Walidacja telefonu i konfiguracji

M16 przyjmuje wyłącznie: session_id,timestamp_seconds,latitude,longitude,
gps_accuracy_m,speed_mps,speed_accuracy_mps,heading_deg,heading_accuracy_deg,
altitude_m,vertical_accuracy_m,is_mock,source,device_id,stream_id,sample_sequence,
elapsed_realtime_nanos,sent_elapsed_realtime_nanos. Source ANDROID_FUSED,
device_id zgodny z client_device_id credential;session aktywny LIVE.
Required:czas finite>=0,lat[-90,90],lon[-180,180],identity/stream/sequence,
oba monotoniczne zegary,is_mock bool. ID streamASCII1–80,sequence/nanosint64>=0,
sent>=captured,bool nie int. Pozostałe nullable/finite,speed/accuracy>=0,
heading[0,360),altitude finite,NULL nie0. Dalej istniejące quality/freshness/
physical checks;parowanie nie nadaje live_control_eligible. owner_id,trip_id,
server_received_at,road_position_m od telefonu odrzucone. Buffered telemetry
poprzedniej sesji nie jest przenoszona do nowego run jako bieżąca.

Configpayload allowlist geometry/phase/source/dynamics wg rodzaju;serwer
wstrzykuje DRAFT/verified=false przed existingvalidators. Klient nie może
podawać/zmieniać verification flags także wewnątrz stop line/speed section;
source URLs są metadanymi,nie ścieżką do otwierania serwerowych plików.
DRAFT jest stanem config_versions i verification geometrii; dla modeli sygnałów
serwer używa istniejącej reprezentacji UNVERIFIED/verified=false, zgodnej
z walidatorem, zamiast wymyślać nową jakość danych. Publication nie oznacza
FIELD_CHECKED ani kalibracji faz. Zachowane wersje
terenowe mogą być read-only danymi źródłowymi, nie skutkiem admincheckbox.

### 7.4 Ochrona odziedziczonego API

Portal ma ograniczony namespace i allowlist adapterów; nie wykonuje catch-all
super().do_*() dla admina. Publiczne shell/assets bez wspólnego server.token.
Własność/grant w DB sprawdzane przed globalnym stanem,plikami,jobem i każdym
Range. Proxy/static nie serwuje runtime/DB/backupów. W trybie portalu legacy
ścieżki są niedostępne poza trzema identycznie chronionymi aliases Android.

| Legacy ścieżka / rodzina | Zachowanie w portalu |
|---|---|
|GET /api/state|Alias M15,device bearer,minimum ownsession;nie global snapshot ani anonymousGET|
|POST /api/pair|Alias M14,code/device binding i te same limity|
|POST /api/position|Alias M16,own device-parent-boot-LIVE,nie server.token|
|GET /api/routes i /map-data*.json|404;C28/C29/C36 z login i allowlist|
|GET /api/runs i /api/runs/{id}.zip|404;C11/C13/C16,export wyłącznie O|
|GET /api/analysis/{id}, /api/analysis/compare, /api/mapping/jobs/{id}|404;M09–M13,scope każdego trip/job/result|
|GET/POST /api/replay* i /api/gps-replay*|404;M05–M08 z runtimecontext i parenttrip|
|GET/POST /api/observation-history*|404;C17/M09 COMPLETENESS,scopedindex;nie global import|
|POST /api/control, /api/reset, /api/view, /api/recording, /api/mapping/select|404;M01–M04,frozen trip route;bez mutacji globalnej sesji|
|POST /api/observe i /api/observe-route|404;C18,autor/czas z backendu|
|POST /api/mapping/analyze|404;M09|
|GET /api/vision-demos|404;synthetic fixture w own authenticated Lab|
|GET/POST /api/vision/*|404;M17–M26,wyłącznie O;sharedanalyst/admin nie dostaje rawmedia|
|GET /mobile,/mobile.js,/lab,/school-lab-bridge.js|Stare404;nowe widoki ownlogin;bez fetch monkeypatch i webGPSfallback w portalu|
|Pozostałe legacy lub filesystem URL|404;nie ma nieopisanego publicznego fallback|

Obecny bazowy localhost M8 pozostaje działający jako osobna aplikacja badawcza;
nie ma jeszcze powyższych kont/ACL. Po implementacji deployment portalu nie
uruchamia równolegle publicznego legacyserwera na swoim runtime. Lokalny legacy
laboratoryjny proces nie montuje DB/storage portalu. Baza dziś nie może być
opisywana jako gotowy chroniony portal szkolny.

### 7.5 Formularze obowiązkowe i walidacja

| Formularz / kontrolki | Client i server | Błąd / recovery | Scenariusz |
|---|---|---|---|
|Register/verify/login/reauth|Email/name/password/confirmation/token §3|Neutralne401/202/422,429cooldown;GETmail nieconsume|SC-AUTH|
|Request reset/reset/password change|Emailsyntax/tokenpurpose/TTL/current/new/confirmation|Bez APIlinku;SMTPinstrukcja;success→login,revokecredentials|SC-AUTH|
|Create/edit/archive trip|title/note,mode/routecreate,revision/reasonarchive|422field,409reviewchangedrecord;bez rawedit|SC-TRIP|
|Filtry dwóch tabel|UTCdates/range<=366dni,enums,route/signal,page25/100|Nowyfiltr clearscursor;loading/empty/error,filtry zachowane|SC-TRIP,SC-OBS|
|Passenger/history observation|signal/state/type,event ID,parenttrip|UNKNOWN nieSTART;historyczna adnotacja jawna|SC-OBS|
|Correction|changesallowlist/revision,reason3–500,clientopID|Oryginał obok;409wymaga porównania;autor z login|SC-OBS|
|Share/revoke|Exactanalystemail,COMPLETE,1activegrant|Jawny komunikat o GPS;bez export/media checkboxów;revoke future access|SC-SHARE|
|Device/pair/revoke|Label,6cyfr,clientidentity,parent/boot|Expiry/revoke→repair;owner nie z body|SC-PHONE|
|Navigation/replay/analysis|Owntrip/device albo Sread,command/rate/seek bounds,jobtype|409busy bez ownerinfo;401/disconnect clearsguide;revoke cancelscontexts|SC-NAV,SC-REPLAY,SC-ANALYSIS|
|CV controls|Allowlistedownsource,camera/res/fps/bools,track/geometry/movement/status/reason|STALE/conflict jawne;mediaOonly;bez uploadworkflow|SC-CV|
|Configuration draft/publish|Existing schema,finitevalues,reason,forbiddenverification,revision|DRAFT,reauth dla publish;active trip snapshots unchanged|SC-CONFIG|
|Admin role/block|Enums/revision/reason,verifiedstatus,reauth|Lastadmin409;audyt/revoke bez private data read|SC-ADMIN|

Client HTML constraints i jawne JS validators;backend waliduje niezależnie każde
pole. Inlineerror+aria-live,formularz zachowany poza hasłami/tokenami. Submit
inflight disabled,bez dublowania zapisów;idempotency tam gdzie §5.
401stop polls/media i clear privatecache/rady→login;po login ponowna autoryzacja
oraz potwierdzenie draft. Nie auto-replay mutacji po zmianie konta.

## 8. Przegląd uproszczenia, odbiór i coverage

Usunięto z obowiązkowego modelu poprzednie operacje awaryjnego dostępu admina,
notifications o takich operacjach,rozbudowane scopes udostępniania,media_assets,
imports,oddzielne credentialhistory i trwałe tabele preauth/nav/replay/jobs.
Zmiana nie usuwa odpowiedzialności:privateread nadal musi być O/S,owner device
w DB,revoke na wynikach/Range,jobruntime nie działa bez polityki,recordintents
nie tracą raw po crash. BootstrapCLI i backup/migracje nie są „opcjonalną tabelą”.

Zachować z prototypu jako materiał:hashowanie z solą/tokenhash,parameterSQL,
fetch/textContent,gauge/stale withdrawal,synthetic tests i per-user loggerroot.
Zmienić:globalread ANALYST/ADMIN,CSRF='DEVICE',domyślneCVroots,defaultdemo hasła,
CLI-only reset,wąski coverage,limitpierwsze500 bezdat/cursor. Historyczny review
w 3ff54d9 obejmował eksperyment w temporaryDB; nie odtwarzamy prototypu ani
nie uruchamiamy go z lokalną bazą w tym doprecyzowaniu.

| Etap / testy | Wymagany dowód |
|---|---|
|3 MIG/RECOVERY|Fresh/upgrade/noop,checksum/nowszaDBrefusal,transactionrollback i backuprestore;FK/integrity;staryruntime nieimportowany|
|3 OWNER|Parenttrip FK,owner z sesji,brak dowolnego ownerwbody;privatedata niewidoczne nowym kontom|
|4 AUTH/SMTP|RegisterDRIVER,normalizedunique,VERIFY/RESETpurpose i SMTP,neutralne responses,bootstrap bezdefaults,reauth/TTL/role/block revocation|
|4 RESET|Mailpit bez APItokenu,hashonly,GETscanner notconsume,expired/used/bad,race max1success,SMTPfail/restart,no plaintextlogs|
|5 ACL|Każdy restrictedanon401,foreign404,ADMIN bez cudzychGPS/filmów;sharedREAD tylko,jobs/replays po revoke denied,sharedexport/media denied;CSRF/Origin/device scopes|
|6 DATA|Zapis/restart/read,metadatarevision,korekta actor/UTC/reason/beforeafter,rawhashunchanged;daty/trasa/state/signal/color/type,paginacja;archive bezpurge|
|6 FAIL|DB/filefail w start/finish/manualjournal,INTERRUPTED,no fabricatedCOMPLETE,idempotent retry,manifestrecovery|
|7 UI|Designreview,wszystkieclient/servervalidators,loading/empty/error/401,fetch bezreload,keyboard/ARIA;no scopecheckboxes/mediaupload|
|8 ROLE|ANALYST tylko own/shared + DRAFTconfig;ADMIN roles/config/auditbezprivatecontent;lastadmin409;share jawnie GPS|
|9 NAV/PHONE|Demo bez phone/ADB/camera/YOLO,globalbusy409,320/390/desktop/landscape,STALE/reverse/OFF_ROUTE/noCVgateoverride,replayisolation,device binding/logout/restart/roleblock/409refresh|

Zakres coverage pozostaje szeroki: cały nowy backend (auth/policy/storage/
migrations/SMTP/device/API/recordintents) plus używany rdzeń application/server,
clocks/events/models/observations/prediction/simulation/vehicle/solver/trajectory/
positioning,telemetry/analysis/replay/gps_replay,route_geometry/map_matching/
route_events/live_navigation/mapping_analysis,observation_history/review/
completeness,CVcontracts/tracking/validation/workbench/capture. branch=True,
>=70% uzgodnionego backendu,raport combined/lines/branches/per-module oraz osobno
nowybackend/core. Istotna logika JS (guidance/perspective/validators/filters/
pagination/session expiry) osobny pomiar Node/V8;Playwright E2E nie jest coverage
Pythona. Android osobnyJUnit/build/device acceptance;nie sumować procentów.

Jawne wyłączenia jak w audycie:legacy ui.py (nieużywany Tkinter),__main__.py
(entrypoint smoke),vision_probe (benchmark),vision_detector/vision_capture_worker
(hardware/ML adapter z osobnymi synthetic/offline checks),vision_demos (fixtures),
tools/testfixtures/vendor,HTML/CSS/Android poza Python. Protocol.sample `...`
nie jest wykonywalną implementacją. Auth/polityk/I/Orecovery nigdy nie wyłączać,
nawet przeniesionych do workerów. Wąskie dwa szkolne moduły nie spełniają odbioru.
Baseline85.9985% to etap1/baza,nie działający nowy portal;tu nowego pomiaru brak.

## 9. Dowody tego doprecyzowania i końcowa checklista

Smoke w izolowanym archiwum bieżącego kodu (bez runtime/data/runs/data/derived):
CLI python -m greenwave --no-browser --port0 uruchomiło się;HTML,map,state200;
synthetic start/pause/finish i ZIP PASS;LIVE bez zweryfikowanych danych BLOCKED;
school.py nie istnieje. Proces testowy zamknięto po finish. Ukierunkowane testy:
2 live_navigation OK,7 Node driver/CV OK,mobile_flow PASS,node --check app.js OK.
Nie powtarzano226testów/Androidbuild ani inferencji przy samej dokumentacji.
Pełne komendy i instrukcja aktualnej bazy: [run.md](run.md).

Metadane Git/runtime przed i po:7 localfiles zachowane,size/mtime identyczne;
nowe tree/index0 runtime paths,check-ignore wskazuje /runtime/. Pozostałe nazwy
tracked sprawdzono pod kątem DB/WAL/SHM/nagrań/środowisk/raportów;bez zawartości.
Usunięcie z historii nie nastąpiło;PUBLISH-01 pozostaje otwarte w §1.
Reguły .gitignore zachowują wcześniejsze linie. Staged commit2 może zawierać
tylko contract/run/stages/ai-usage/README;żadnych nowych DB/nagrań/sekretów/backendu.

Do końcowego odbioru etapu2:

- [ ] Role O/S i brak prywatnego dostępu administratora odpowiadają ustaleniu.
- [ ] Sharing jeden trip/jeden ANALYST/READ_ANALYZE z jawną informacją GPS.
- [ ] SMTP/reset/aktywacja/bootstrap oraz ograniczony koszt hash są opisane.
- [ ] Jedna jazda,logout/restart telefonu i późniejsze zmiany Androida są jawne.
- [ ] 14 trwałych tabel i 37+26 endpointów mają scenariusze,walidację i politykę.
- [ ] Runbook uruchamia aktualną bazę,nie nieistniejący portal;smoke izolowany.
- [ ] Runtime poza nowym tree,localfiles zachowane;wcześniejsza publikacja jawna.
- [ ] Etapy3–12 nadal Do zrobienia;dalsza praca dopiero po osobnym prompcie.

Decyzje produktowe nie są ponownie otwierane przez tę checklistę. Sprawdzenie
opisanej implementacji nastąpi w następnych etapach,nie na podstawie pliku.

### Doprecyzowania integralności v1

- Prawidłowy register/request-reset dla istniejącego PENDING konta może ponowić
  mail VERIFY_EMAIL w tym samym mechanizmie i limitach, bez publicznej informacji
  o statusie. ACTIVE dostaje wyłącznie RESET przy request-reset; BLOCKED pozostaje
  nieaktywne. Nie trzeba nowego endpointu do ponowienia aktywacji.
- DELETE share wymaga expected_share_id: nie cofa w tle nowszego udostępnienia
  z innej karty. Powtórzenie cofnięcia tego samego grantu daje204; inny bieżący
  grant daje409. Nie odtwarza zgód ani nie pozwala analitykowi delegować dalej.
- Administrative audit C35 pokazuje tylko zdarzenia auth/administracji/config.
  Prywatne powody korekt i payloady przejazdów pozostają poza jego DTO.
- SIM w opisach to skrót enum JSON SIMULATION; drugi tryb to LIVE.
  NavigationDTO ma revision runtime, a zmiana instance/restart unieważnia handle.
- Index CV pozostaje dodatkową istniejącą bazą z właściwym root i autorem z sesji;
  nie trzeba tworzyć centralnej biblioteki filmów. Shared ObservationDTO nie
  ujawnia ścieżek/klatek; permission READ_ANALYZE nie rozszerza się na endpointy CV.


### Techniczne doprecyzowanie po przeglądzie etapu 3

Bez zmian ról,polityki i zakresu v1. Aktualna schema2 ma nadal14 tabel. Historyczna
0001 REAL seconds jest niezmienna;0002 przebudowuje kolumny czasu do INTEGER UTC
ms, zachowując ID/FK/indeksy/triggery/dane. Wszystkie repo clock,Actor reauth,
verified_at,measured_at i granice dat są integer ms (bool,float,NaN,inf odrzucone).
Centralny now_ms adaptuje time.time();konwersja legacy to floor(Decimal(str(seconds))*1000),
NULL pozostaje NULL;zakres epoch0..253402300799999 (rok9999);invalid legacy rollback,
nie zgadywanie jednostek. TTL także ms:reset900000,verify86400000,pairing/reauth300000,
idle1800000,absolute28800000. Metadane applied_at także ms od schema2.

Runner wykonuje SQL z authorizer zabraniającym rzeczywistych TRANSACTION/SAVEPOINT/
ATTACH/DETACH/PRAGMA;VACUUM jest zakazany po usunięciu leading comments. CREATE TRIGGER
BEGIN/END i literały ze średnikami są legalne. Operacje runnera poza authorizer scope.
Backup/restore znanej v1 jest wspierany, walidowany przez jego historię/checksum;
restore nie migruje po cichu,zwraca schema.version/current,status wymaga jawnego upgrade,
runtime odmawia do migrate. Nie backup GPS/media.

RunLogger pozostaje bez zmian:owned run-root/raw.csv,metadata.json,complete.json.
Szkolne raw_ref wskazuje raw.csv,z własnym owner/trip/run i containment;nie wymagamy
gps.jsonl. Spójność fizycznych plików/manifestu/recovery pozostaje etap6.
Filtry repo używają created_at trip i server_received_at obserwacji:>=from i <to,
from>=to jest błędem. HTTP parsowanie RFC3339 do integer ms,keyset cursor i reszta
filtrów UI nadal wymagane w etapie6;wewnętrzny offset ich nie zastępuje.


## Doprecyzowanie etapu 5 — trwała podstawa kontekstu autoryzacji

Replay i analysis job pamiętają wewnętrzną, niezmienną podstawę autoryzacji:
OWN(actor_id,trip_id) albo SHARE(actor_id,trip_id,share_id). Podstawa pochodzi
z uwierzytelnionej sesji i aktualnej DB podczas tworzenia kontekstu, nigdy
z żądania klienta. Identyfikatory podstawy nie są publicznym DTO.
SHARE wymaga tego samego rekordu, właściwego analityka i trip, aktywnego
ANALYST, READ_ANALYZE oraz revoked_at IS NULL. Nowy grant nie zastępuje starego
w istniejącym replay/jobie. Nie ma automatycznego fallbacku do innej podstawy.

Revoke → ponowny share bez odczytu pomiędzy tymi mutacjami nadal unieważnia
stary kontekst. Read/control/close starego replay dają neutralne404; nowy replay
może powstać na nowym grancie. Jobs sprawdzają dokładny grant przed plikami,
analizą i publikacją. Nieważna podstawa wykonania jest oznaczana jako
authorization_invalid;queued/running przechodzi do CANCELLED. Zarządzanie
właściciela jest odrębnym prawem opisanym poniżej. Sesja, credential, expiry i security_version nadal
obowiązują niezależnie od podstawy. Właściciel nie zmienia podstawy wykonania
cudzego zadania przez odczyt jego statusu lub próbę zamknięcia.

Końcowa kontrola sesji i konkretnego grantu oraz publikacja manifestu raportu
są serializowane względem revokacji przez transakcję BEGIN IMMEDIATE.
Nie oznacza to transakcyjnego recovery filesystem/DB; granice awarii zapisu
pozostają jak w etapie5, pełna koordynacja nagrania w etapie6.
Raport już poprawnie opublikowany jest danymi właściciela. Jego świeży odczyt
jest niezależną operacją O/S; nowe udostępnienie może pozwolić czytać taki
raport, lecz nigdy nie ożywia starego handle zadania.


## Etap 5 — execution authorization i owner management authorization

Wykonanie: worker, odczyt źródła i publikacja używają wyłącznie pierwotnych
actor_id,session_id,credential i AuthorizationBasis OWN/SHARE. Revoke konkretnego
share,archive albo utrata aktywnej sesji blokują dalsze wykonanie. Nowy grant
nie zastępuje starego. Końcowa kontrola i manifest pozostają synchronizowane
z revokacją w transakcji BEGIN IMMEDIATE,bez deklaracji recovery DB/filesystem.

Zarządzanie: GET i DELETE /analysis-jobs/{job_id} najpierw uwierzytelniają bieżącą
sesję i sprawdzają rzeczywiste owner_id parent trip w DB. Aktywny właściciel
ma safe status200 i idempotent cancel204 także po revoke,regrant lub archive,
dopóki pamięciowy handle istnieje. Jego dostęp nie zależy od authorization_invalid
ani ważności share analityka. Nie przejmuje actor/session/credential/basis joba.
Dla niewłaściciela obowiązuje pierwotna sesja/credential i nadal ważny konkretny
share na COMPLETE nonarchive. ADMIN nie ma wyjątku dla cudzych jobów.

Owner status odświeża ważność pierwotnego wykonania;queued/running z nieważną
podstawą pokazuje CANCELLED. completed zachowuje COMPLETE i report_id prawidłowo
opublikowanego raportu. Cancel nie usuwa raportu,nie zabija wątku i nie cofa CPU.
Nie ma resume/restart endpointu;nowa analiza wymaga nowego joba. TTL/usunięcie/
restart serwera nadal daje404,anonymous/expired/revoked sesja401.


## Doprecyzowania implementacyjne etapu 6

Schema v3 zachowuje 14 tabel. Dodaje historyczne oznaczenie obserwacji oraz kontekst
sesji/boot/obserwacji dla intencji nagrywania. Zastosowane 0001/0002 pozostają
niezmienione; stare obserwacje mają historical=0, bez domyślania pochodzenia.
Niezmienność nowych faktów i spójność kontekstu egzekwują triggery.

route_id oznacza logical_id konfiguracji ROUTE i obejmuje jej wersje. Sort asc/desc
używa timestamp i ID w jednym kierunku. Daty API są RFC3339 ze strefą, ułamkiem 1–6
cyfr i konwersją do integer UTC ms przez odcięcie mikrosekund. Jedna granica zakresu
uzupełnia drugą o maksymalne 366 dni; bez dat pełna historia jest stronicowana.
Cursor HMAC wiąże actor/rodzaj/filtry/sort, TTL 15 minut i as_of. Nie zamraża
uprawnień ani pełnego zestawu mutable rekordów. Korekty, archive i revoke mogą
zmieniać członkostwo między stronami. Publiczny offset/query w ms nie jest wspierany.

Publiczna ręczna obserwacja ma measured_at NULL i source MANUAL nadane przez serwer.
COMPLETE/INTERRUPTED oznacza adnotację historyczną, bez dopisywania raw. Aktywne
nagranie ma journal z czasem przyjęcia przez serwer. START/FINISH/JOURNAL są trwałymi
intencjami z kontrolowanymi root, nie jedną transakcją DB–filesystem. Przy błędzie
raw fakt DB pozostaje trwały, a odpowiedź 202 jawnie wskazuje FAILED journaling.
Idempotentny retry zachowuje tożsamość operacji/zasobu bez duplikowania zapisu;
DTO statusu/revision pozostaje aktualne, nie historycznym snapshotem odpowiedzi.

M01/M02/M03 w etapie 6 to konieczny minimalny SIM start/status/FINISH z Idempotency-Key,
jedną globalną rezerwacją i stacjonarnym syntetycznym śladem. Bez PAUSE/RESUME/M04,
live, telefonu i kamery; pełna integracja należy do etapu 9. Drugi start daje 409
bez ujawniania właściciela. Nowy boot nie odtwarza jazdy ani świeżości GPS.
Finalizacja po revokacji używa wcześniej powiązanego kontekstu/root i audytu
systemowego, nie przywraca credentials. Watchdog nie odświeża idle i daje wspólny
punkt integracji blokady/zmiany roli bez panelu administracji. Poprawny manifest po
utracie DB commit pozwala na recovery COMPLETE. Brak/błędny manifest lub brak
zaufanej intencji daje INTERRUPTED, bez zmiany zakończonego raw.

Dokładny zakres i sprawdzone granice awarii: [stage6.md](stage6.md).


## Doprecyzowanie transportu etapu 7 — HEAD eksportu

HEAD /school/api/v1/trips/{trip_id}/export używa tej samej polityki właściciela i
integralności co GET, bez tworzenia ZIP/body. Tylko ta ścieżka obsługuje HEAD;
inne pozostają niedostępne. Status + bezpieczny enum X-School-Error umożliwia UI
odmowę bez dużego Blob i bez anulowanego konkurencyjnego GET. GET ponownie sprawdza
prawa i integralność; HEAD nie jest grantem ani gwarancją przyszłego transferu.
Brak nowych tabel, scopes, ról lub zmiany DTO zapisów. Szczegóły/testy w stage7.md.


## Doprecyzowanie etapu8 — role, audyt i konfiguracje

Ustalenia ról v1 bez zmiany. ANALYST edytuje wyłącznie własne DRAFT; ADMIN wszystkie
DRAFT. Odczyt draftów wspólnej konfiguracji jest dostępny ANALYST/ADMIN; publish i
archive wyłącznie ADMIN po świeżym reauth. Dodany PATCH /config/versions/{id} przyjmuje
payload, expected_revision, reason (C30b); istniejąca wersja określa kind/logical_id.
C32 zgodnie z kontraktem ma reason i idempotentną archiwizację konkretnego ID.
C28–C29 bezpieczne DTO; cursor dla listy, offset zachowany dla wcześniejszych klientów.
C33/C35 podpisane keyset cursory,25/max100,UTC ms w DTO/RFC3339 w filtrach dat.
Admin audit ma allowlistę akcji i resource_type USER/CONFIG oraz bezpieczną projekcję
powodu. Nie wybiera zdarzeń prywatnego przejazdu lub korekty.

Konfiguracje ROUTE/SIGNAL/MODEL mają ścisłe allowlisty i istniejące domain validators,
nie samą poprawność JSON. Source geometrii: attribution, description?, url? wyłącznie
metadata http/https bez credentials, bez pobierania. Pozostałe URL i ścieżki zabronione.
Geometria dostaje obiekt verification.status=DRAFT; sygnały i relacje UNVERIFIED/false.
Klient nigdy nie dostarcza tych flag, także nested. Publish ich nie podnosi. Nowe
nagrania szkolne przechowują school_route_snapshot (ID/payload/hash) w metadata;
archiwizacja/publikacja nowej wersji nie zmieniają starych snapshotów, hashów ani raw.

Zmiana konta atomowo unieważnia credentials i niewłaściwe grants; po commit wspólny
callback finalizuje nagrywanie i unieważnia wykonanie kontekstów. Owner management
jobów jest nadal odrębne od execution authorization; nie podmienia podstawy OWN/SHARE.
Admin nie ma wyjątku dla cudzych danych. Unblock nie aktywuje niezweryfikowanego email.
