# GreenWave School — kontrakt aplikacji

Etap 2, wersja 1.0-proposal, 2026-10-12. **Propozycja do przeglądu użytkownika**.
Dokument definiuje docelowe wymagania, nie potwierdza ich implementacji.
Etap 1 zaakceptowany przez użytkownika; po etapie 2 zatrzymujemy się.

## 0. Stan i źródła

Worktree `C:/Users/konra/.codex/worktrees/school-app/Surfy`, codex/school-app.
HEAD na wejściu: a9f7259cf13702a4a001ee6959922df909e6e8f7.
Audyt: bb99de3d808db8898426b42203e6c5e979e527be.
Baza kodu: 7ece85993bf860e0bdec0ecb43b65532242166eb.
Po poleceniu użytkownika prototyp przywrócono lokalnie do bazy bez commita.
Dlatego HEAD zawiera school.py/school_store.py/school.js/testy, ale katalog
roboczy ma ich usunięcia. Przegląd przez `git show a9f7259:...`, bez odtwarzania.
Zachowujemy wcześniejsze usunięcia/modyfikacje i runtime/; nie stagingujemy ich.
Nie czytamy runtime ani prywatnego data/runs. Main/CV pozostają nietknięte.

Odczytano audit/stages/ai-usage oraz historyczne moduły/testy szkolne, aktualne
server/application/live_navigation, logger/replay/jobs/indeksy SQLite/CV,
Android TelemetrySample i odświeżanie sesji. AGENTS w repo nie znaleziono;
nadrzędny C:/Users/konra/.codex/AGENTS.md ma 0 bajtów i został odczytany.

## 1. Problem domenowy i widoki

Kierowca chce ograniczyć postoje i gwałtowne zmiany prędkości na kolejnych
światłach, zgodnie z limitami. Profil prędkości wymaga wiarygodnego GPS,
właściwej kierunkowej linii, limitu, faz i zegara predykcji. Pojedynczy kolor
lub detekcja lampy nie dostarcza automatycznie tych informacji.
Scenariusz: konto → przejazd/trasa → symulacja albo Android LIVE → nawigacja
→ obserwacje pasażera → zakończenie → tabela/replay/raport/korekta → jawne
udostępnienie analitykowi i jego cofnięcie. STATE_SEEN nie dowodzi STATE_START.
Obserwacje obsługuje pasażer; kierowca nie musi klikać podczas jazdy.

| Widok | Granica |
|---|---|
|Nawigacja|Mapa perspektywiczna, prędkość, znany limit, najbliższe światła/nazwy/źródła/wiek; diagnostyka poza tym widokiem|
|Moje przejazdy|Własne rekordy, filtry/paginacja, tytuł/notatka, eksport, archiwizacja, replay, udostępnienia|
|Moje obserwacje|Własne oryginały i wartości po korekcie, filtry, korekta z powodem i historią|
|Laboratorium|Własna symulacja/replay/analiza/CV; analityk dodatkowo jawnie udostępnione przejazdy; wspólne konfiguracje|
|Administracja|Konta/role/blokady/konfiguracja; prywatne dane tylko przez osobną audytowaną operację, bez domyślnej listy wszystkich GPS/filmów|

**GATE**: zachować evaluate_live_navigation i _live_recommendation_eligibility:
świeże dopuszczone GPS, MATCHED/FORWARD, FIELD_CHECKED geometria/linia/limit,
prawidłowy sygnał, zweryfikowane fazy/ważne okna i zgodny zegar. UI dodatkowo
sprawdza status solvera, zakres/limit/prędkość i świeżość odpowiedzi (2 s).
Brak przesłanki → null target/range i brak „Przyspiesz/Zwolnij”, widoczny powód.
Nie zachowywać ostatniej pewnej rady. GPS provider nadal ustala wiek pomiaru.
Replay nigdy nie daje rady live. Konto, rola, korekta i review CV nie zmienia GATE.
CV jest diagnostyczne; nie uczy ani nie potwierdza faz automatycznie.

Demo Docker: osobny wolumen/DB, syntetyczne dane/adresy example.test, etykieta
DEMO, symulacja i replay fixture'ów bez ADB/telefonu/YOLO. Bez stałych publicznych
haseł; konta przykładowe opcjonalnie tworzone CLI z własnymi hasłami operatora.
Brak mountu prywatnych danych, prawdziwej kamery i parowania telefonu w profilu
demo. Realny profil: osobny runtime, HTTPS dla sieci, native Android Fused
Location; localhost/ADB jako jawny tryb lokalny. Symulacja nigdy nie udaje GPS.
Nie normalizujemy GPS na trasę demo; nie budujemy ogólnomiejskiego routingu A–B.
CV opcjonalne z osobnym modelem/licencją; nierozstrzygniętych wag nie publikujemy.

## 2. Konta, hasła i sesje

Role rozłączne DRIVER/ANALYST/ADMIN. Każda rola może mieć własne dane; rola
nie daje dostępu do cudzych. Rejestracja przyjmuje email,display_name,password,
password_confirmation; rolę DRIVER ustala serwer. role/active/owner_id/verified
w body są niedozwolone.

Email: trim, ASCII, <=254 znaków, local-part<=64, jedna @, bez control/whitespace;
domena DNS z kropką, etykiety1–63 litery/cyfry/myślnik bez myślnika na brzegu.
Cały email lower-case jest jawną regułą identyfikatora aplikacji. Nie usuwamy
kropek ani +tagów. Unicode/EAI poza v1, odrzucane bez transliteracji.
email_normalized UNIQUE binary; email_display zachowuje trim dla SMTP.
Display_name trim Unicode1–80 bez control, nie identyfikuje konta. Zmiana email
poza v1, aby nie obchodzić weryfikacji i resetu.

Prawidłowa rejestracja nowego/istniejącego email zawsze202 z tą samą treścią:
„Jeśli adres może zostać użyty, wysłaliśmy dalsze instrukcje”. Nowe konto
PENDING_VERIFICATION, SMTP link aktywacji (token>=32B, hash, jednorazowy,24h).
Brak dostępu przed aktywacją. Dla istniejącego email brak publicznego konfliktu;
neutralny mail o próbie jest dopuszczony w limitach. GET linku nie zużywa tokenu.
Demo odbiera mail w Mailpit. Weryfikacja email jest dodatkową pracą wobec
prototypu; to proponowany sposób pogodzenia rejestracji z anti-enumeration.

Bootstrap pierwszego admina tylko CLI create-admin z getpass (nie hasło w argv),
transakcja wymaga braku aktywnego ADMIN, audyt BOOTSTRAP_ADMIN. Konto ACTIVE,
bez publicznego endpointu bootstrap i admin/admin. Kolejni admini: zmiana roli
aktywnego zweryfikowanego konta przez admina po reauth. Ostatniego aktywnego
admina nie można zablokować/zdegradować. Emergency CLI recovery operatorskie
z audytem, nigdy anonimowe HTTP. Operator OS/backupów nie jest rolą API.

Hasło12–128 znaków Unicode, <=512B UTF-8, bez trim/normalizacji, potwierdzenie
równe; bez sztucznego obowiązku mieszanki znaków. Scrypt n=131072,r=8,p=1,
dklen32,sól>=16B losowa, format z wersją/parametrami, maxmem256MiB, max2 równoległe
hashowania. Parametry zmierzyć na docelowym sprzęcie przed deploy; nie obniżać
po cichu. compare_digest, rehash starszych parametrów przy poprawnym loginie,
dummy hash dla nieistniejącego konta. Login jednolite401 przy błędnym haśle,
nieistniejącym, zablokowanym lub nieaktywowanym koncie. Bez haseł/sekretów w logach.

Trwałe rate limits przed kosztownym hash: login5 błędów/email/15min i30 prób/IP/
15min; register5/IP/h; reset/activation3/email/h i10/IP/h; reset-use10/IP/15min;
reauth5 błędów/session/15min; pair5 błędów/IP/5min i5/code (unieważnia kod).
Klucz email HMAC(normalized), także nieistniejący. Jednolity429/Retry-After,
bez trwałego blokowania konta przez napastnika. Liczniki prób/sukcesów rozdzielone;
sukces zeruje tylko błędy tego email. Nie ufać X-Forwarded-For bez trusted proxy.

Zmiana hasła: current password+CSRF, transakcja nowy hash+security_version++,
revokacja wszystkich browser/device/reset tokens, koniec aktywnych kontekstów;
bez auto-login. Block account robi tę samą revokację; unblock nie przywraca
starych sekretów. Role change: role+version+audit atomowo, wszystkie sesje,
device tokens, nav/replay i joby tej osoby unieważnione; nowa rola wymaga loginu.
Granty dla odbiorcy cofane przy utracie ANALYST. Nie ufać roli ze starego snapshotu.

Browser: sekret>=32B tylko SHA256 w DB, stabilny nietajny session_id, user_id,
created,last_activity,absolute_expiry,revoked,authenticated_at,security_version.
Idle30min, absolute8h; activity update max1/min. Aktywny własny telefon może
odświeżać idle sesji nadrzędnej podczas nagrania, nigdy absolute8h.
Nowy token przy każdym loginie; session fixation odrzucona. POST /auth/renew
rotuje token i CSRF atomowo, pozostawia session_id/absolute deadline;
stary sekret od razu nieważny. Frontend serializuje renew/mutacje i powiadamia
inne karty bez sekretu. Reauth potwierdza hasło, także rotuje sekret i CSRF;
authenticated_at świeże5min dla privileged operations. Brak localStorage tokens.

Cookie gw_session: HttpOnly,SameSite=Strict,Path=/,bez Domain,Max-Age<=absolute TTL;
Secure obowiązkowe HTTPS. Tylko jawny localhost dev/demo HTTP może wyłączyć
Secure; brak produkcyjnego „ignoruj TLS”. CSRF to 32B wynik HMAC(CSRF_KEY, raw cookie secret + session_id),
powiązany z bieżącym sekretem sesji. W DB tylko csrf_hash, a /auth/me może
odtworzyć wartość z cookie; CSRF_KEY w prywatnym deployment secret, nie Git; X-CSRF-Token na POST/PATCH/DELETE.
Origin dokładnie PUBLIC_BASE_URL scheme/host/port, Host allowlist, brak CORS.
CSP nowego UI bez unsafe-inline, no-store/nosniff, Referrer-Policy=no-referrer,
proxy HTTPS/HSTS, statyczna allowlist. Nie wystawiać runtime/DB/backupów.

Anon auth także ma preauth cookie i CSRF wyliczany analogicznie z preauth secret z GET /auth/preflight (TTL15min,limit IP);
nie daje praw konta. Chroni loginCSRF i formularz resetu/aktywacji; GET linku
nie consume. Cookie nie zawiera email/roli. Logout current: revoke+clear,
stop nav/capture tej sesji, revoke jej code/device credentials/replay;
inne sesje konta mogą zostać. Logout-all kończy wszystko. Expiry egzekwować
backend+cleanup bez czekania na kliknięcie.401 frontend zatrzymuje polling/media,
czyści prywatny cache/mapę/rady i pokazuje login. Draft formularza tylko w pamięci,
bez haseł/tokenów; nie powtarzać mutacji automatycznie po zmianie tożsamości.

## 3. Reset i SMTP

1. Preflight+request-reset email: syntax i limit niezależnie od istnienia;
   zawsze jednakowe202/message, bez tokenu/linku/recipient ID w publicznym API.
2. ACTIVE user: losowy token32B, hash,TTL15min, poprzednie unused reset revoked,
   security_version snapshot+audit bez sekretu. PENDING dostaje najwyżej
   instrukcję aktywacji; BLOCKED nie może zresetować blokady.
3. Link wyłącznie PUBLIC_BASE_URL + /#reset=<sekret>, nie z Host request.
   Fragment nie trafia do access logs; klient trzyma sekret w pamięci, czyści URL,
   nie ładuje external assets. GET formularza nie consume ani nie potwierdza
   publicznie ważności tokenu.
4. POST reset-password z token/new password/confirmation i preauthCSRF:
   BEGIN IMMEDIATE, hash/TTL/unused/status/version, zmiana hasła+used+revokacja
   wszystkich user reset/browser/device credentials i kontekstów atomowo.
   Dwie równoległe próby: max1 sukces. Invalid/expired/used jednolite422 INVALID_TOKEN.
5.200 „Hasło zmienione; zaloguj się”, bez auto-login. Mail notification bez hasła.
   Awaria po commit nie cofa hasła.

SMTP poza transakcją DB, timeout5s; realne STARTTLS z cert verify/SMTPS,
sekrety z prywatnych secret files poza Git. **Nie przechowywać raw reset tokenu
w SQLite outbox.** Kolejka pamięci max100; worker wysyła posiadany sekret po
commit hash. SMTP failure/restart utraconej kolejki: token nie staje się ważnym
wysłanym dowodem; unieważnić niewysłany jeśli możliwe, audit DELIVERY_FAILED;
ponowne żądanie generuje nowy token po cooldown. Nie obiecujemy trwałego retry
sekretu, którego nie przechowujemy. Maile bez tokenu mogą mieć trwały outbox.
Publiczne API nie ujawnia dla którego adresu SMTP zawiodło; operator widzi
zagregowany stan usługi. Walidacja konfiguracji SMTP przy start, brak potrzebnej
konfiguracji blokuje uruchomienie realnego deploymentu.

Demo: Mailpit SMTP w prywatnej sieci Docker bez auth/TLS, tylko example.test;
UI skrzynki bind127.0.0.1 dla operatora demonstracji, SMTP port nie publiczny.
Nie używać tej skrzynki/DB/volume do realnych danych. Demo nadal nie zwraca
reset tokenu przez publiczne API. Production: DEMO=off,osobny root,HTTPS baseURL,
SMTP host/port/from+secrets/TLS, bez seedhaseł i skrzynki debug. Operator zapewnia
nadawcę/SMTP. Neutralna odpowiedź i jednakowa klasa kosztu nie oznacza obietnicy
zerowego fizycznego wycieku czasowego;testy badają response/status i ścieżkę.

## 4. Macierz uprawnień

O=właściciel (każda zalogowana rola może mieć własne dane).
S.READ w tabelach oznacza dokładnie S.READ_ANALYZE (nie osobną zgodę).
S=aktywny grant od O dla ANALYST na jeden **ukończony** przejazd.
B=czasowa audytowana operacja admina na konkretny zasób. Rola sama nie daje S/B.

| Zasób/akcja | Anonimowy | Kierowca | Analityk | Administrator |
|---|---|---|---|---|
|Shell/health/preflight/auth/reset|Tylko publiczne kontrakty|Tak|Tak|Tak|
|Własna nawigacja/SIM,start/pause/finish|—|O+lease|O+lease|O+lease|
|Read przejazdów/obserwacji|—|O|O lub S.READ_ANALYZE|O lub B.READ|
|Create przejazdu/obserwacji|—|O|O|O|
|Edit title/note,archive|—|O|O|O; cudze tylko B.ARCHIVE|
|Korekta/valid=false obserwacji|—|O|O;S tylko read|O;B nie daje korekty|
|Fizyczne DELETE raw/oryginałów|—|—|—|— w API v1|
|Historia korekt|—|O|O/S.READ_ANALYZE|O/B.READ|
|ZIP/CSV/JSON export|—|O|O/S.EXPORT|O/B.EXPORT|
|Replay/seek/play/pause|—|O|O/S.READ_ANALYZE|O/B.READ|
|Analysis job create/read/cancel|—|O|O/S.READ_ANALYZE|O/B.ANALYZE|
|CV preview/raw media|—|O|O/S.CV_MEDIA|O/B.CV_MEDIA|
|CV start/stop/live assignment|—|O+lease|O+lease,nie S|O+lease,nie B|
|CV review|—|O,oddzielny zapis|O;S notatka raportu|O;B tylko read|
|Devices/pair/list/label/revoke|—|O|O|O;cudze revoke B.REVOKE_DEVICE|
|Wspólne route/signal read|—|Tak|Tak|Tak|
|Wspólne route/signal DRAFT version|—|—|Tak|Tak|
|Config publish/archive|—|—|—|Tak+reauth/audit|
|Ustawienie FIELD_CHECKED/verified w UI/API|—|—|—|—;procedura terenowa|
|Share/revoke grant|—|O|O własnych trip|O własnych trip|
|Konta/role/block/system config|—|—|—|Tak+reauth/audit|
|Cudze prywatne dane|—|—|Tylko S|Tylko B|
|Trip audit|—|O|—|B.READ;system audit bez GPS|

**S rekomendowany**: exact email aktywnego verified ANALYST,bez publicznej
wyszukiwarki kont. READ_ANALYZE obejmuje pełne GPS,zdarzenia/korekty/replay trip;
UI mówi to wprost. EXPORT i CV_MEDIA osobne checkboxy defaultoff,export filmu
wymaga obu. TTL domyślnie7dni,max30. Bez projektów/grup i dziedziczenia nowych trip.
Analityk nie zmienia danych właściciela;notatka w swoim raporcie ma autor/czas.
Grant check na każdej stronie,Range,export,replay/job status i wykonaniu.
Revoke/expiry/block/rolechange odcina przyszłe reads,stop contexts/jobs,cache;
nie cofa już pobranych bajtów. Wynik analizy pozostaje O,analityk traci go z S.
Nakład:1 grants table,3 scopes,wspólny policy resolver,mały shareform+testy
propagacji. Alternatywa prostsza: analityk tylko config/synthetic,bez prywatnej
analizy;nie zastępować S globalnym read ani tą alternatywą bez decyzji.

**B**: admin+reauth <5 min,trip/device ID,powód10–500,scope,TTL <=15 min bound session.
Na request X-Admin-Access-ID;sam nagłówek bez activeB nie daje praw.
Tworzenie B i każdy prywatny read/action audyt:actor/resource/scope/reason/UTC/
request_id/outcome. Właściciel widzi powiadomienie i audit;SMTP notice bez GPS,
błądSMTP nie ukrywa B. Brak wildcard globalnego zakresu. Device revoke osobne B bez
prawa czytania trip. Nie pozwala edytować owner/originals ani czytać haseł.
Self-approved „break glass”,bez drugiego approvera w v1 — do przeglądu.

## 5. Dane, migracje i awarie

SQLite school.sqlite3 to źródło prawdy kont/polityk/metadanych/korekt/audytu;
raw/media+manifesty źródłem surowych faktów. Nie odtwarzamy owner z folderu/logu.
ID serwerowe losowe32 lowercasehex,UTC intmilisekundy,NULL=brak wiedzy.
FK ON,busy_timeout5s,WAL,synchronousFULL,parametry SQL. Każdy FK user/trip/resource
musi istnieć;nie używać client owner_id. Poniżej model do migracji etapu3.

| Tabela | Pola/relacje/klucze | Ograniczenia/indeksy |
|---|---|---|
|schema_migrations|version PK,checksum,applied_at,app_version|Ciągłość wersji i niezmienny checksum|
|users|id PK,email_normalized,email_display,display_name,password_hash,role,status,verified_email_at,security_version,revision,created/updated|UNIQUE email_normalized;role enum;PENDING_VERIFICATION/ACTIVE/BLOCKED;versions>=1|
|browser_sessions|id PK,secret_hash,user_id FK,csrf_hash,security_version,created/activity/absolute TTL,authenticated_at,revoked|UNIQUE hash;idx(user_id,revoked),idx(expiry)|
|preauth_sessions|secret_hash PK,csrf_hash,expires,peer_key|TTL,index expiry;nie FK user|
|account_tokens|id PK,hash,user_id FK,purpose RESET/VERIFY_EMAIL,issued/expires/used/revoked,security_version,delivery_state|UNIQUE hash;max1 unused/user/purpose w transaction;idx(user,purpose,expiry)|
|rate_limits|key_hmac,purpose,window_start compositePK,attempts/failures,blocked_until|Counts>=0,retencja;email nie plaintext|
|devices|id PK,owner_id FK,client_device_id,label,status,created/revoked|UNIQUE(owner,client_device_id);ACTIVE/REVOKED;idx(owner,status)|
|pairing_challenges|id PK,code_hmac,owner_id/browser_session_id FK,expires,attempts,used/revoked,boot_id|UNIQUE active code;1 active/session;TTL 5 min,max5prób|
|device_credentials|id PK,token_hash,device_id/parent_session_id FK,expires/revoked,security_version,boot_id|UNIQUE hash;scope TELEMETRY;osobno browser;idx(device,revoked)|
|trips|id PK,owner_id FK,title,note,mode,route_version_id FKnullable,status,created/start/end,revision,archived,import_idnullable|SIMULATION/LIVE;PLANNED/STARTING/RECORDING/FINALIZING/COMPLETE/INTERRUPTED;idx(owner,created,id),idx(owner,route,status,created)|
|runs|id PK,trip_id FK UNIQUE,relative_path,metadata/raw/manifest hashesnullable,state,last_sequence|COMPLETE wymaga hashów;path serwerowa;idx(trip,state)|
|navigation_sessions|id PK,trip/user/browser_session/device FK,app_session_id,boot_id,state,lease_expires,slot|UNIQUE aktywny slot DRIVING globalnie;STARTING/ACTIVE/PAUSED/STOPPING/CLOSED/INTERRUPTED|
|observations|id PK,trip_id FK,signal_id,source,state,event_type,server_received,measured_atnullable,geometry_hash,raw_sequencenullable,source_event_id|Append-only;UNIQUE(trip,source,source_event_id);idx(trip,server_received,id),idx(trip,signal,state,type,time)|
|observation_corrections|id PK,observation_id/actor_id FK,sequence,before/after JSON,reason,UTC,previous_revision|UNIQUE(obs,sequence);append-only;idx(obs,sequence)|
|trip_grants|id PK,trip/analyst/grantor FK,scopes,expires/revoked,created|UNIQUE active(trip,analyst);READ_ANALYZE required;grantor=owner in transaction;idx(analyst,expires)|
|admin_access|id PK,admin/session FK,resource_type/id,scopes,reason,expires/revoked|TTL <=15 min,reauth;bez wildcard;idx(session,expires)|
|operations|id PK,user FK,resource_id,kind,idempotency_key,request_hash,state,result_ref|UNIQUE(user,kind,key);PENDING/APPLIED/FAILED;DB/file recovery|
|analysis_jobs|id PK,trip/actor FK,authorization_kind/id,type,status,progress,result_ref/hash,params_hash,created/end,note/revision|PENDING/RUNNING/COMPLETE/FAILED/CANCELLED/INTERRUPTED;idx(trip,created)|
|replay_contexts|id PK,trip/actor/session FK,authorization reference,mode/time/rate,expiry,boot_id|Max1/session,TTL30min;stan odtwarzania w pamięci,nie restore live;idx(session,trip)|
|media_assets|id PK,owner_id FK,relative_path,source_hash,mime,approved_by FK,created,trip_id FK nullable|Ścieżka z operator staging; UNIQUE fingerprint/owner; idx(owner,created); bez upload publicznego|
|cv_captures|id PK,trip FK,relative_root,manifest_hash,state,source_mode,synchronization,created|Owner z trip;film historyczny != LIVE;idx(trip,created)|
|cv_reviews|id PK,capture FK,source_event_id,actor FK,status,association,reason,UTC,revision|Append-only;idempotency operation;nie zmienia detection|
|audit_events|sequence PK,actor nullable/type,action,resource_type/id,scopes,reason,UTC,request_id,outcome|Append-only;idx(actor,UTC),idx(resource,id,UTC);bez secrets/kopii GPS|
|imports|id PK,owner/operator FK,source_fingerprint/hash,approved,state,target_trip FK|UNIQUE fingerprint;audyt;bez owner z pliku|
|config_versions|id PK,kind ROUTE/SIGNAL/MODEL,logical_id,version,payload/hash,status,creator FK,created/published,revision|UNIQUE(kind,logical_id,version);DRAFT/PUBLISHED/ARCHIVED;published immutable|
|notifications|id PK,user FK,type,resource_id,created/read_at|Bez token/link reset;idx(user,created)|

Observation owner wyłącznie przez trip FK. Source MANUAL/CV,knownstate
RED/YELLOW/GREEN/RED_YELLOW/OFF/UNKNOWN,STATE_SEEN/STATE_START;czas otrzymania
oddzielnie od pomiaru. CV source_event_id musi wskazywać capture tego trip.
Efektywna wartość=oryginał+najnowszy prawidłowy ciąg korekt. Korekta zmienia
state/event_type/valid,nie czas,GPS,source,trip;author z sesji,serverUTC,powód3–500,
before/after,expected_revision wymagane. UNKNOWN nie STATE_START. valid=false
zastępuje usunięcie błędnej obserwacji. Triggery blokują zwykłe UPDATE/DELETE
oryginałów/korekt/audytu;kolejne decyzje to nowe wpisy.

Edit trip: title1–120,note0–1000;route_version tylko PLANNED,revision wymagane.
Po start zamrożone owner/mode/route/hash/run/timestampy. Status tylko operacje
serwera,recovery,nie PATCHdowolne. Soft archive tylko po zamknięciu;cofa granty
/jobs,nie usuwa raw. Restore nie odtwarza grantów. Phys purge/retencja kont/raw
pozaAPIv1,osobny kontrakt operatorski;nie deklarować trwałego delete.

Read-only seeds data/maps/routes/corridors/prediction;nowe wspólne wersje
runtime/shared/config/{version_id}. Active trip dostaje snapshot hash/version.
UI nie nadaje FIELD_CHECKED/verified;osobny protokół terenowy/CLI z dowodem,
nie realizowany przez rozszerzenie szkolne.

Storage: runtime/owners/{uid}/trips/{tid}/runs/{runid} (raw/metadata/complete),
trip-root/derived (raporty/attestations),trip-root/cv/{cid} (media/manifest/journals).
Indeks M8 runtime/owners/{uid}/indexes z jawnym path;CV reviews w trip-root.
Logger/history/capture/replay/jobs dostają root/context dopiero po autoryzacji.
Brak default DATA/derived/runs odziedziczonych po LocalServer. Resolver plików
nie przyjmuje arbitrarypath,sprawdza containment i symlink/reparse-point escape.
Indeksy M8/CV to rebuildable caches keyed run/sequence/geometry;school corrections,
cv_reviews,owner/audit nie są cache i nie mogą zostać nadpisane rebuildem.
Index import bierze autoryzowane runs z DB,nie skanuje globalnie data/runs.

DB i plik nie są jedną transakcją. Operations/outbox bez sekretów+
idempotency_key32–64ASCII dla create/start/finish/observation/correction/job/grant/
import. Key+payload powtórzone=same result,inny payload409. Start: DBintent+
lease STARTING→nowyrun/flush/fsync→RECORDING. Finish: FINALIZING→close raw,
manifest temp+fsync+atomicrename samefilesystem→hashcheck→COMPLETE.
Błąd: evidence zachowane,INTERRUPTED/FAILED,bez wymyślonego complete.json.

Manual: atomowo observation+operation+audit w DB,worker dopisuje raw z tym samym
source ID;retry sprawdza już zapisane ID/sequence. Nie dopisuje do completedraw:
brakujący wpis zostaje w DB ze journaling_status FAILED i audytem. Active SIM
manual może aktualizować syntetyczny model;LIVE zapisuje fakt bez weryfikacji faz.
Korekta nigdy nie modyfikuje raw ani nie uruchamia learningu. Odpowiedź jawnie
PENDING/APPLIED/FAILED,nie fałszywe „zapisano wszystko” po błędzie drugiego magazynu.

Restart: nowy boot_id,revoke stare leases/nav/replay/devicecredentials,matcher/
clock nie wznawiają ostatniej próbki jako FRESH. Aktywny trip bez validmanifest
INTERRUPTED;validmanifest po utracie DBcommit→idempotentny COMPLETE+RECOVERYaudit.
Orphan files quarantine,nie publikacja;RUNNING/PENDING jobs INTERRUPTED,
retry nowyjob. Recovery nie poprawia raw. Awaria indeksu nie pozwala na cudzy read.

Starebez właściciela dane domyślnie niedostępne. Import tylko operatorCLI maintenance,
jeden wskazany run/media,jawny existingowner+uzasadnienie+zgoda przypisania;
manifest/hash/sequence/geometrycheck,snapshotcopy do runtime,bez edycji źródła.
Imports/trip/audit zachowuje źródłowe ID/hash/operator. Niekompletne→quarantine.
Nieprzypisane pliki nie trafiają do nowych kont. Nie wykonujemy importu ani
czytania prywatnych nagrań w tym etapie.

Migracje etapu3:0001... SQL/Python,manifestSHA256,schema_migrations,PRAGMA
user_version tylko mirror. Każda migration transaction+FKcheck/integritycheck,
bez wewnętrznego COMMIT executescript rozrywającego upgrade. Maintenance lock;
newer/mismatchschema blokuje start. Brak automatycznej migracji prywatnych raw.
Przed upgrade stop ingest/job/capture i finish nagrań;SQLite backup API (nie
samo copy.db przy WAL),backupmanifest version/config/artefacts hashes;ważne
raw/media read-only backup osobno pozaGit/demo. SQLfailROLLBACK;postcheckfail
app nie startuje,operator restoreDBsnapshot+pasującykod. Filesystemintents
recovery osobno,brak obietnicy autodowngrade. DB prototypu nie przyjmować
po cichu;controlledimport do nowejDB dopiero z osobnym zleceniem.

## 6. Izolacja i telefony

Propozycja v1: jeden proces i jeden writer SQLite, **jedna aktywna sesja
nawigacji/nagrywania na cały serwer**. Atomowy lease DRIVING obejmuje SIM albo
LIVE oraz opcjonalny worker CV. PAUSE w SIM zachowuje lease i nagranie;
FINISH, logout lub expiry je kończy. Drugi użytkownik, także administrator,
otrzymuje 409 ACTIVE_SESSION_BUSY: „Inny użytkownik ma aktywną sesję jazdy.
Możesz przeglądać własne dane lub replay”. Bez ujawnienia tożsamości/pozycji.
Admin nie może po cichu przejąć lease. Worker odnawia lease, deadline wynosi
10 s od ostatniego heartbeat; awaria powoduje cleanup i INTERRUPTED,
nie wieczną blokadę. Własny idempotentny retry startu nie tworzy nowej sesji.

GreenWaveApplication, matcher i zegar SIM są oddzielne dla navigation_session.
app_session_id M8 identyfikuje ingest i zegar modelu, nie konto/login.
Replay/GPSReplay jest osobny dla browser_session+replay_id, max1 aktywny na
sesję, TTL30min; nie zmienia live. Analiza: max2 jobs globalnie, max1 job na
actor/trip, kolejka max20. Actor i scope są sprawdzane przed wykonaniem i przy
każdym status/result. Globalny limit nie daje dostępu do danych innych osób.
Capture max1 w aktualnym własnym lease; oddzielne roots i assignments chronią
przed przeciekiem klatek/statusu. Backend musi wstrzyknąć te zależności jawnie.

Browser secret, device bearer i app_session_id to trzy odrębne wartości oraz
tabele. Challenge parowania:6 cyfr, HMAC z deployment secret, TTL 5 min,
unikalny aktywny kod (ponowne losowanie przy kolizji), związany z owner,
browser_session_id i boot_id. Telefon wysyła code,client_device_id,label.
Owner wynika wyłącznie z challenge; owner_id/user_id w body odrzucamy.
Client_device_id identyfikuje próbki, nie jest dowodem tożsamości konta.

Device credential: losowy sekret>=32B, hash w oddzielnej tabeli, scope TELEMETRY,
max8h i nie dłużej niż parent absolute TTL, związany z boot/device/parent/
security_version. Nie może czytać list/eksportów, nadawać ról, wybierać trasy
ani sterować nagrywaniem. Start LIVE wskazuje własne urządzenie, max1 aktywne
na sesję jazdy. Ingest wymaga active LIVE, właściwego device i app_session_id.
Walidujemy source/stream/sequence/czasy i GPS istniejącym providerem;
duplikat jest potwierdzany bez ponownego zapisu. Telefon nie wybiera dowolnego
trip/owner poza kontekstem zatwierdzonym przez właściciela.

Logout parent, revoke, expiry, role change, block i password reset odcinają
odpowiednie credentials natychmiast:403 DEVICE_REPAIR_REQUIRED bez sekretu.
Po restarcie browser cookie może przetrwać do TTL po security_version check,
ale trzeba rozpocząć nową jazdę i **ponownie sparować telefon**. Buforowane
próbki starego boot nie trafiają do nowego runu ani nie przywracają FRESH.
Logout innej sesji nie odcina niepowiązanego device; logout-all/version odcina all.

Aktualny Android przy409 odświeża /api/state bez tokenu. Potrzebna będzie później
zmiana HttpJson/TelemetryTransmitter, nie upublicznienie globalnego state.
PairingClient dziś wysyła sam code; docelowo code+client_device_id+label.
To jawna zmiana Androida do implementacji i odbioru. Przy zmianie app_session_id
w tym samym boot:409 SESSION_CHANGED, po którym minimalny GET session wymaga
właściwego device bearer. N19 może zwracać null przed startem LIVE; klient
musi wyświetlać oczekiwanie zamiast wysyłać telemetry bez aktywnego kontekstu.

## 7. API i formularze

Namespace /school/api/v1; ścieżki tabel względne, poza aliasami Androida.
Domyślna odmowa; sprawdzenie scope przed SELECT, plikiem i jobem.
Actor/owner z backendu, nie client body. JSON object UTF-8, Content-Type
application/json, body<=8192B; wyjątek /config/versions <=262144B.
Odrzucać nieznane/duplikowane pola JSON i query, NaN/Infinity, niewłaściwe ID,
enums i control. Brak uploadu wideo przez API v1: operator staging daje
własny zatwierdzony asset_id i hash, nie dowolną ścieżkę z przeglądarki.

C=browser CSRF+Origin, P=preauth CSRF+Origin, D=device bearer bez cookie/CSRF.
GET nie zmienia trwałych danych/polityk. Sekrety bez query URL i logów;
publiczne assets nie zawierają prywatnych danych. Wszystkie mutacje mają C/P/D
jawnie w tabeli. Pairing code to jednorazowa capability, nie publiczny login.

Sukces: {data:DTO,request_id}; listy dodatkowo page:{limit,next_cursor}.
Błąd: {error:{code,message,fields?},request_id}, bez stacktrace/SQL/path/sekretu.
200 read/update;201 create;202 async/neutral;204 revoke/archive;
400 malformed/cursor;401 brak/wygasła sesja użytkownika;403 rola/CSRF/device/
preauth;404 brak **lub** cudze prywatne ID;409 revision/state/idempotency/lease;
413 body;415 typ;422 pole/invalid token;429 z Retry-After;503 I/O/capacity;
500 neutralny z request_id. Anonymous restricted401 bez informacji o istnieniu ID.
Scope sprawdzać przez parent trip; ukrycie przycisku nie zabezpiecza endpointu.

DTO:

- User: id,email,display_name,role,status.
- Trip: id,title,note,mode,route_version/hash,status,UTC created/start/end,
  revision,archived,journaling_status.
- Observation: id,trip_id,signal_id,source,original{state,event_type,
  server_received_at,measured_at},effective{state,event_type,valid},revision,
  corrections_count,geometry_hash.
- Correction: id,actor,server_at,before/after,reason,revision.
- Navigation: id,trip_id,mode,sample/quality,route/match/lights,recommendation
  nullable,eligibility.reason_codes,response_at. Bez globalnej historii.
- Job: id,trip_id,type,status,progress nullable0..1,result/error,created/end.
- Replay: id,trip_id,mode,duration,time,rate,paused,sample/provenance,bez live rady.
- Capture: id,trip_id,status,source_mode,frame_ref/age/events,
  diagnostic_only=true,synchronization.
- Grant: id,trip_id,analyst,scopes,expires_at,revoked.
- Version: id,logical_id,version,hash,status,validated payload.
- Audit: actor,action,resource,scope,reason,UTC,outcome.

Nigdy password/hash/token/path w DTO. Dla endpointów auth/pair jedynie jawnie
opisane wydanie własnej capability/cookie jest wyjątkiem od sekretów w odpowiedzi;
publiczny reset nigdy nie zwraca tokenu.

Listy: limit25 default, max100, sort created_at DESC,id DESC albo obie ASC.
Keyset cursor HMAC związany z actor,filter hash,sort,as_of,last key,TTL15min.
Inny actor/filtr/sort →400. Uprawnienia przy każdej stronie, nie zamrożone
w cursor. Daty UTC RFC3339 z wymaganą TZ, from inclusive/to exclusive,
from<to,zakres<=366dni. Bez dat pełna historia stronicowana, nie pierwsze500.
UI przelicza dni lokalne Europe/Warsaw na UTC z DST; serwer nie zgaduje TZ.
Filtry trip:from,to,route_id,status,archived,scope own/shared.
Filtry observation:from,to,route_id,trip_id,signal_id,state efektywny,event_type,
source,valid,scope own/shared. ID hex32; route logical_id [a-z0-9_-]{1,80}.
Sort observation wykorzystuje server_received_at zamiast created_at.

### 7.1 Konta — endpointy A

Wszystkie wiersze podlegają wspólnym błędom i limitom §7 oraz §2/§3.

| ID | Metoda / ścieżka | Konto / scope | Żądanie | Odpowiedź | Walidacja / dodatkowe błędy | CSRF |
|---|---|---|---|---|---|---|
|A01|GET /auth/preflight|Anon lub sesja|—|csrf,expires_at + preauth cookie|TTL15min, limit IP,503 capacity|—|
|A02|POST /auth/register|Anon|email,display_name,password,password_confirmation|202 neutral message|§2,422 fields,429; bez conflict existence|P|
|A03|POST /auth/verify-email|Anon|token|200 activation message|24h, jednorazowy,422 INVALID_TOKEN; nie login|P|
|A04|POST /auth/login|Anon|email,password|User,csrf + nowe cookie|Jednolite401,429; §2|P|
|A05|GET /auth/me|Sesja dowolnej roli|—|User,csrf,expires_at,demo|401 revoked/expiry; nie device secret|—|
|A06|POST /auth/renew|Sesja|{}|csrf,expires_at + nowe cookie|Absolute deadline zachowany;401|C|
|A07|POST /auth/reauth|Sesja|password|authenticated_until,csrf + nowe cookie|401/429; nie zmienia roli|C|
|A08|POST /auth/logout|Bieżąca sesja|{}|204 + clear cookie|Idempotentne; nieważna sesja tylko clearcookie, bez cudzych mutacji|C gdy active|
|A09|POST /auth/logout-all|Sesja|{}|204 + clear cookie|Wszystkie własne konteksty; audit|C|
|A10|POST /auth/change-password|Sesja|current_password,new_password,password_confirmation|200 message + clear cookie|§2,401 current password,422 fields; bez auto-login|C|
|A11|POST /auth/request-reset|Anon|email|202 neutral message|§3,429; nigdy token/link|P|
|A12|POST /auth/reset-password|Anon|token,password,password_confirmation|200 message + clear cookie|15min, jednorazowy,422 INVALID_TOKEN|P|

### 7.2 Przejazdy, obserwacje i udostępnienia — T

| ID | Metoda / ścieżka | Konto / scope | Body / query | Odpowiedź | Walidacja / dodatkowe błędy | CSRF |
|---|---|---|---|---|---|---|
|T01|GET /trips|O; ANALYST własne/shared|from,to,route_id,status,archived=false,scope=own/shared,limit,cursor,sort|Trip[] + page|§7 filtry/cursor; PRIVATE_SCOPE z backendu|—|
|T02|POST /trips|O|title,note?,mode,route_version_id?; idempotency key|201 Trip|§5; LIVE wymaga trasy; SIM tylko synthetic; owner/status zakazane|C|
|T03|GET /trips/{trip_id}|O/S.READ/B.READ|ID|Trip + capabilities|404 foreign/missing; bez paths|—|
|T04|PATCH /trips/{trip_id}|O|expected_revision,title?,note?,route_version_id? (PLANNED)|Trip|Min1 zmiana;409 revision/state|C|
|T05|DELETE /trips/{trip_id}|O/B.ARCHIVE|expected_revision,reason|204 soft archive|Reason3–500; tylko closed;409 active; nie kasuje raw|C|
|T06|POST /trips/{trip_id}/restore|O|expected_revision|Trip|Tylko archived; granty nie odżywają;409|C|
|T07|GET /trips/{trip_id}/export|O/S.EXPORT/B.EXPORT|format=zip/csv/json,include_media=false|Binary Content-Disposition|COMPLETE + hash; media wymaga CV_MEDIA; max1 export/actor;409 corrupt/not complete|—|
|T08|GET /observations|O; ANALYST shared|from,to,route_id,trip_id?,signal_id,state,event_type,source?,valid?,scope,limit,cursor,sort|Observation[] + page|Kolor efektywny, enums §5,422 fields/cursor400|—|
|T09|POST /trips/{trip_id}/observations|O|signal_id,state,event_type,source_event_id; idempotency key|201 Observation + journaling_status|Source MANUAL z backendu; signal w route/synthetic; UNKNOWN nie START|C|
|T10|GET /observations/{observation_id}|O/S.READ/B.READ poprzez trip|ID|Observation|404 foreign/missing|—|
|T11|POST /observations/{observation_id}/corrections|O|expected_revision,changes:{state?,event_type?,valid?},reason; idempotency key|201 Correction + Observation|Allowlist zmian;409 revision;valid=false zamiast delete|C|
|T12|GET /observations/{observation_id}/corrections|O/S.READ/B.READ|limit,cursor,sort|Correction[] + page|Actor/time/reason; parent scope;nie ukrywa oryginału|—|
|T13|POST /trips/{trip_id}/grants|O|analyst_email,scopes,expires_at; idempotency key|201 Grant|COMPLETE, ACTIVE ANALYST, TTL<=30dni,READ_ANALYZE required;422 recipient,409 duplicate|C|
|T14|GET /trips/{trip_id}/grants|O|limit,cursor|Grant[] + page|Analityk nie widzi innych grantów;404 foreign|—|
|T15|DELETE /trips/{trip_id}/grants/{grant_id}|O|{}|204 revoke|Idempotentne; odcina pochodne uprawnienia analityka|C|

Kolory RED_YELLOW/OFF zachowane z CV i jawnie dostępne w manual, nigdy
nie mapowane na GREEN. UNKNOWN tylko STATE_SEEN. Source CV tylko wewnętrzny
worker, nie pole body. T09 na zakończonym przejeździe zapisuje historyczną
adnotację DB: measured_at=null,server_received_at=teraz, bez dopisywania raw.
UI mówi „adnotacja historyczna”, nie „widziany teraz”. Active passenger click:
client event ID, czas przyjęcia serwera, jawnie nieznane opóźnienie reakcji.

### 7.3 Nawigacja, replay, jobs, urządzenia — N

| ID | Metoda / ścieżka | Konto / scope | Body / query | Odpowiedź | Walidacja / dodatkowe błędy | CSRF |
|---|---|---|---|---|---|---|
|N01|POST /navigation|O|trip_id,device_id?; idempotency key|201 Navigation|PLANNED; mode z trip;LIVE own device;409 lease;demo LIVE403|C|
|N02|GET /navigation/{navigation_id}|O + parent browser session|ID|Navigation|GATE;404 foreign;409 closed runtime|—|
|N03|POST /navigation/{navigation_id}/control|O + parent session|command=PAUSE/RESUME/FINISH,expected_revision|Navigation lub202 FINALIZING|SIM pause/resume;LIVE PAUSE/RESUME422;finish obu;409 state|C|
|N04|PATCH /navigation/{navigation_id}/simulation|O + SIM lease|rate?,speed_kmh?,follow_recommendation?,revision|Navigation|rate1/2/5/10,speed0..syntheticlimit,bool ścisłe;LIVE403|C|
|N05|POST /trips/{trip_id}/replays|O/S.READ/B.READ|mode GPS/SIMULATION|201 Replay|COMPLETE i prawidłowy hash;1/session;mode zgodny z evidence;409/422|C|
|N06|GET /replays/{replay_id}|Actor context + nadal trip scope|ID|Replay|TTL30min,parent scope na każdym odczycie;404 foreign|—|
|N07|POST /replays/{replay_id}/control|Jak N06|command PLAY/PAUSE/SEEK/RATE,value?|Replay|seek0..duration,rate1/2/5/10;nieznane pola422|C|
|N08|DELETE /replays/{replay_id}|Jak N06|{}|204 close|Idempotentne; nie zmienia live|C|
|N09|POST /trips/{trip_id}/analysis-jobs|O/S.READ/B.ANALYZE|type GPS_QUALITY/MAPPING/COMPLETENESS,route_version_id?; idempotency key|202 Job|COMPLETE;routehash zgodny;1/actor/trip,queue20;429/503|C|
|N10|GET /analysis-jobs/{job_id}|O/requester + nadal trip scope|ID|Job|Grant/expiry ponownie;404 foreign;bez paths|—|
|N11|DELETE /analysis-jobs/{job_id}|Requester + scope; O|{}|204 cancellation|Gotowy wynik zostaje O,nie kasuje metryk|C|
|N12|PATCH /analysis-jobs/{job_id}/note|Requester + scope; O własnego job|expected_revision,note|Job + autor/czas note|0–1000,409 revision; metrics immutable|C|
|N13|GET /devices|O|limit,cursor,status|Device[] + page|id,label,status,created,last_seen;bez tokens/hash|—|
|N14|PATCH /devices/{device_id}|O|label|Device|1–80,status tylko revoke;404 foreign|C|
|N15|DELETE /devices/{device_id}|O/B.REVOKE_DEVICE|reason|204 revoke|Reason3–500; kończy linked LIVE;§6|C|
|N16|POST /pairing-challenges|O|label|201 code,expires_at,challenge_id|TTL 5 min,1/session,label1–80;demo403;code tylko O|C|
|N17|DELETE /pairing-challenges/{challenge_id}|O + issuing session|{}|204 revoke|Spent code nie odzyskuje ważności|C|
|N18|POST /device/pair|Posiadacz code|code,client_device_id,label|device_token,device_id,app_session_id nullable,server_version|6cyfr,deviceID1–80ASCII;jednorazowy;429;invalid403;bez owner_id|D code, bez cookie|
|N19|GET /device/session|TELEMETRY bearer|—|app_session_id nullable,active,repair_required|Bound device;revoked403;nie globalny state|D|
|N20|POST /device/position|TELEMETRY bearer + active own LIVE|Android TelemetrySample + session_id|accepted,duplicate,external_status,external_position własnej próbki|Existing provider ranges;session409;binding403;body <=8192B;100/min/device|D|

Simulation reset/jitter/model zmieniać przez nowy PLANNED trip, nie zerowanie
aktywnego nagrania. LIVE nie zamrażamy przez PAUSE. N18 wymaga przyszłej zmiany
PairingClient (dziś sam code). Tylko kod fallback bez device binding nie należy
do kontraktu v1. Owner UI uruchamia LIVE dopiero po pair; do tego czasu N19
może zwrócić app_session_id=null (Android musi obsłużyć oczekiwanie).
Idempotency-Key header obowiązuje wskazane mutacje;GET state nie zastępuje lease.

### 7.4 CV, konfiguracja, admin — V

| ID | Metoda / ścieżka | Konto / scope | Body / query | Odpowiedź | Walidacja / dodatkowe błędy | CSRF |
|---|---|---|---|---|---|---|
|V01|GET /trips/{trip_id}/captures|O/S.CV_MEDIA/B.CV_MEDIA|limit,cursor|Capture[] + page|READ bez media nie daje filenames/thumbs|—|
|V02|POST /trips/{trip_id}/captures|O + lease|source_type CAMERA/ASSET,source_asset_id? lub camera_index?,width,height,fps,detection,realtime|202 Capture|camera0..16,res160..3840/120..2160,fps1..60,bool;własny asset z allowlist;brak modelu422;demoCAMERA403|C|
|V03|GET /captures/{capture_id}|O/S.CV_MEDIA/B.CV_MEDIA|ID|Capture|diagnostic_only=true;404 foreign|—|
|V04|POST /captures/{capture_id}/stop|O + own lease|{}|202 Capture|Stop własnego procesu;nie globalnego zatrzymania cudzy|C|
|V05|GET /captures/{capture_id}/frames/{frame_id}|O/S.CV_MEDIA/B.CV_MEDIA|frame ID>=0|image/jpeg|Previewcache32/capture;404 foreign/missing;bez tokenuURL|—|
|V06|GET /captures/{capture_id}/media/{segment}|O/S.CV_MEDIA/B.CV_MEDIA|Range singlebytes|206 binary + Content-Range|segmentint>=0,max1MiB/chunk,416invalid;path/hashbound;grant każdy chunk|—|
|V07|GET /captures/{capture_id}/events|O/S.READ/B.READ|limit,cursor,state?|DiagnosticEvent[] + reviews|READ bez media może czytać DTO,nie klatki/film|—|
|V08|POST /captures/{capture_id}/associations|O + fresh own capture|track_id,route_version_id,stop_line_id,movement|diagnostic association|Session/geometry/continuityscope;stale409;movement422;no VERIFIED|C|
|V09|DELETE /captures/{capture_id}/associations/{track_id}|O + own context|{}|204 unassign|Nie kasuje audit/detection|C|
|V10|POST /captures/{capture_id}/reviews|O|event_id,status ACCEPTED/REJECTED,reason,association?,expected_revision;idempotency key|201 Review|Actor z sesji;reason3–500;wrongevent/geometry422;bez learningu|C|
|V11|GET /config/versions|Aktywne konto|kind,logical_id,status,limit,cursor|Version[] + page|DRIVER tylko PUBLISHED;scope z backendu|—|
|V12|GET /config/versions/{version_id}|Aktywne;DRAFT tylko ANALYST/ADMIN|ID|Version|Bez prywatnych danych;existing verification read-only|—|
|V13|POST /config/versions|ANALYST/ADMIN|kind,logical_id,base_version_id?,payload,reason|201 DRAFT Version|262144B;existing schema+coords2..10000;finite durations;verification/verified fields denied;reason3–500|C|
|V14|POST /config/versions/{version_id}/publish|ADMIN + reauth|expected_revision,reason|Version PUBLISHED|Validateddraft;nie FIELD_CHECKED;active trips frozen;409 revision|C|
|V15|DELETE /config/versions/{version_id}|ADMIN + reauth|reason|204 archive|Snapshoty historycznych trip zostają;published immutable|C|
|V16|GET /admin/users|ADMIN|email exact?,role,status,limit,cursor|User[] + page|Bez GPS/hash/token; bez public usersearch|—|
|V17|PATCH /admin/users/{user_id}|ADMIN + reauth|role? lub status ACTIVE/BLOCKED,reason,expected_revision|User|Lastadmin409,pending nie shortcutACTIVE;version/revocationaudit|C|
|V18|POST /admin/access-operations|ADMIN + reauth|resource_type TRIP/DEVICE,resource_id,scopes,reason,expires_at|201 AccessOperation|§4B,reason10–500,TTL <=15 min,404missing,notify/audit|C|
|V19|DELETE /admin/access-operations/{access_id}|Issuing ADMIN|{}|204 revoke|Nie kasuje historii ani kopii pobranych|C|
|V20|GET /admin/audit|ADMIN|actor?,action?,from,to,limit,cursor|Audit[] + page|Metadane bez GPS/sekretów;retencja jawna|—|
|V21|GET /trips/{trip_id}/audit|O/B.READ|limit,cursor|Audit[] + page|O widzi admin/grant swojego trip,nie cudze emailpróby|—|
|V22|GET /notifications|O|unread?,limit,cursor|Notification[] + page|Bez linku resetu ani sekretu|—|
|V23|POST /notifications/{notification_id}/read|O|{}|204 marked|Idempotentne;404 foreign|C|
|V24|GET /health|Anon|—|ok,deployment_mode|Bez usercounts,paths,SMTPdetails;503notready|—|
|V25|GET /admin/health|ADMIN|—|Zagregowany storage/SMTP/worker/queue|Bez private nav/secret|—|
|V27|GET /media-assets|O|limit,cursor|Asset[] + page (id,label,mime,hash)|Tylko własny zatwierdzony staging, bez paths;404 foreign|—|
|V26|GET /maps/{map_id}|Aktywne konto|allowlisted ID|BundledGeoJSON + attribution|Nie path;404unknown;nie dowód verified świateł|—|

V10 association tylko route/version/line/movement istniejące, nie dowolny model
ani reviewer. Operator staging/import/bootstrap to CLI,nie ukryty video-upload
endpoint. Cudze device revoke też wymaga B ID nagłówka. Zdjęcia/rawexports są
pobierane przez autoryzowany endpoint, nie staticruntime ani URL z tokenem.

### 7.5 Odziedziczone endpointy

Nowy kontroler polityk adaptuje core; brak catch-all super().do_*() przepuszczanego
adminowi. Legacy lokalna komenda badawcza może zostać na localhost, poza Docker
portalem, z oddzielnym root;nie montuje szkolnejDB/runtime i nie obchodzi ACL.

| Legacy metoda / ścieżka | Decyzja w portalu |
|---|---|
|GET /, /app.js, /style.css, /driver-ui.js, /capture-ui.js, /vision-workbench-ui.js|Nowy shell/assets allowlist,bez wspólnego server.token;staryindex niedostępny|
|GET /mobile, /mobile.js|Web GPS diagnostyczny niedostępny w v1 portalu;natywny Android zachowany|
|GET /api/state|Jedyny alias D do N19;minimalna sesja telefonu,anon/browser nie dostaje globalnego stanu|
|POST /api/pair|Alias N18,te same fields/policy/limits;wymaga zgodnego Android|
|POST /api/position|Alias N20,device-owner-parent-LIVEbinding;nie server.token|
|GET /api/routes, /map-data.json, /map-data/{obszar}.json|Stare404;V11/V12/V26 z login i allowlist|
|GET /api/vision-demos|Stare404;fixture'y we własnym authenticated lab context|
|GET /api/runs, /api/runs/{id}.zip|Stare404;T01/T03/T07 z parenttrip scope|
|GET /api/analysis/{id}, /api/analysis/compare|Stare404;N09/N10;UI porównuje wyniki dwóch osobno autoryzowanych jobs|
|GET /api/replay/state, /api/gps-replay/state|Stare404;N06 replay_id z kontrolą zakresu|
|GET /api/mapping/jobs/{job_id}|Stare404;N10 parenttrip ACL|
|GET /api/observation-history, /api/observation-history/completeness|Stare404;T08/N09 COMPLETENESS,indeksu z ograniczonym zakresem|
|POST /api/observation-history/sync|Stare404;odbudowa z ograniczonym zakresem w job,nie globalimport|
|POST /api/control, /api/reset, /api/view, /api/recording, /api/mapping/select|Stare404;T02/T04/N01/N03/N04 bez globalnego zegara/route mutations|
|POST /api/observe, /api/observe-route|Stare404;T09 z trip/owner i zachowaniem źródła/czasu|
|POST /api/replay, /api/gps-replay, /api/mapping/analyze|Stare404;N05/N07/N09|
|GET /api/vision/status, /api/vision/recordings, /api/vision/frame, /api/vision/history, /api/vision/export, /api/vision/media|Stare404;V01/V03/V05/V06/V07/T07 z trip/capture ACL|
|POST /api/vision/control, /api/vision/workbench|Stare404;V02/V04/V08/V09/V10;server.token media cookie usunięte|
|GET /lab, /school-lab-bridge.js|Stare404;nowe zalogowane Laboratorium;bez fetch monkeypatch|
|Każda inna legacy/filesystem URL|404;bez aliasu jeśli nie opisany powyżej|

### 7.6 Formularze i błędy

| Formularz | Client i server walidacja | Zachowanie |
|---|---|---|
|Register|Email/displayname/password/confirmation §2|202 neutral, SMTP activation;nie auto-login|
|Login/reauth|Email na login,password;limits|401 neutral,429cooldown;nie ujawnia istnienia|
|Activation/reset|Token,potwierdzenie nowego hasła(reset)|GET nie consume;422neutralinvalid;success→login|
|Requestreset|Emailsyntax/length|202jednakowe,bez linku w odpowiedzi|
|Passwordchange|Current/new/confirmation|Revoke po sukcesie;bez przechowywania passworddraft|
|Tripcreate/edit|Title/note,routeversion/mode,revision|422fields,409refreshporównanie;nie silentoverwrite|
|Tablefilters|DatesTZ/range/enums/limit/cursor|Nowy filtr clearscursor;empty/error/loading,zachowane filtry|
|Passenger/historyobservation|Trip/signal/state/type/eventID|UNKNOWN nie START;źródło/czas backend;historia jawna|
|Correction|Reason/changesallowlist/revision|Oryginał widoczny;409wymaga review|
|Share|Exactanalystemail,TTL,scopes,EXPORT/CVcheckboxes|Jawny zakres GPS/media/download;revoke propagowany|
|Pair/device|Label,6cyfr,deviceID(Android)|Owner z code;revoke/expiry→repair|
|Navigation/replay|Trip/device/command/rate/seek bounds|409busy bez identity;disconnectwithdrawguidance|
|Analysis/reportnote|Type/routehash,note<=1000|Pending/progress/cancel,metricsimmutable|
|CVsource/association/review|Allowlistedasset/camera,movement/geometry/status/reason|Bez arbitrarypath;diagnosticlabel;stale409|
|Config route/signal|Existingschemas,finitevalues,forbiddenverification,reason|DRAFTversion,active snapshots unchanged|
|Admin role/block/access|Enums/revision/reason/TTL/scope/reauth|Lastadmin409;audit/notify;expiredgrantdeny|
|Archive/restore/logout/revoke|Scope/revision/reason|CSRF;archiveconfirmation;nie kasuje raw|

HTML constraints + jawne JS validators/enums,serwer niezależnie każde pole.
Błąd przy polu+aria-live,formularz zachowany poza password/token. Disable submit
inflight + idempotencyretry.401clear privatecache/rady,stop polls/media→login;
po login ponowny scope i potwierdzenie niezapisanej operacji. Brak auto-replay
mutacji po zmianie identity. Nie traktować ukrytego UI jako sprawdzenia uprawnień.

## 8. Przegląd prototypu i dowody

Źródło przeglądu: commit a9f7259, a nie przywrócona aplikacja robocza.

| Plik / obszar | Co zachować jako materiał | Co zmienić i czego brakuje | Test zgodności |
|---|---|---|---|
|school.py: app_for i runs_root|Rozdzielenie kontekstów aplikacji i reuse rdzenia M8|Usunąć domyślne roots LocalServer, dodać globalny jawny lease i scoped replay/jobs/CV|Dwóch właścicieli bez cross-talk; busy409; recovery po crash|
|school.py: Handler|Walidacja Host, limity JSON, sesja i CSRF|Brak catch-all legacy dla ADMIN; pełna polityka endpointów, preauth, reauth i B|Anon/foreign ID, każde API i Range/job/replay; CSRF/Origin|
|school.py: device/pair|Kod związany z kontem; minimalny odczyt sesji telefonu|Osobne credentials zamiast csrf='DEVICE', device binding, challenge TTL/unikalność/boot i logout revocation|Owner injection, kolizja, jednorazowe użycie kodu, dwa telefony, restart/revoke/block|
|school.py: demo/CLI|Syntetyczne dane i getpass administratora|Usunąć stałe hasło czterech kont, bootstrap lock, SMTP reset/aktywacja|Brak publicznych domyślnych haseł; mail testowy bez API tokenu|
|school_store.py: hasła/sesje/reset|Losowa sól, stałoczasowe porównanie, hash tokenów|Mocniejsze jawne parametry, normalizacja email, verification, idle/rotation/reauth, SMTP|KDF salt/version, expiry/jednorazowy/race, unique normalized email, neutralne odpowiedzi|
|school_store.py: scope i listy|Parametry SQL i relacje trip/observation|Globalny odczyt ANALYST/ADMIN zastąpić S/B; date filters i paginacja|Nieudostępnione404, revoke grantów, date/cursor/limit, audyt B|
|school_store.py: corrections|Append-only state/reason/autor/czas|Before/after, type/valid, revision i trigger immutable|niezmieniony hash raw, concurrent409, actor spoof denied|
|school_store.py: migrations/recovery|Kontrola wersji i odmowa nowszej DB|Numerowane migracje/checksum/backup, DB-file intents i import quarantine|Rollback, backup restore, upgrade idempotent, source log niezmienny|
|school.js|fetch, textContent, prędkościomierz i wygaszanie stale|Podział na moduły API/validators/guidance, share/adminB, SMTP workflow, daty/cursors, nowy styl/ARIA|Unit JS coverage, E2E formularzy/błędów/sesji, desktop/mobile/GATE|
|test_school_store.py i test_school_http.py|Syntetyczne fixtures, expiry, cudze ID, CSRF, ostatni admin, ZIP|Oczekiwanie globalnego read analityka jest niezgodne; dodać SMTP/verification/shares/B/revoke/I/O|Nowa macierz ról, reset race, trwałość/restart, bez prywatnych data/runs|
|school_ui.cjs i check_school.cjs|Fail-closed guidance i E2E zapisu/korekty/filtrów/network|Brak polegania na stałym demo haśle; dodatkowe role/formularze oraz JS coverage|E2E kont i grantów, GATE, responsive; nie sama liczba testów|
|Prototyp .coveragerc|branch=True|Dwa szkolne moduły nie spełniają końcowego zakresu|Pełny denominator core+backend i osobny JS|

Faktyczny eksperyment etapu 2: `git show a9f7259:greenwave/school_store.py`
→ compile/exec w pamięci → TemporaryDirectory z syntetyczną SQLite i kontami
owner/analyst/admin example.test. Bez HTTP, bez prywatnych plików, bez
odtwarzania prototypu do worktree. Wynik:

```json
{"prototype_commit":"a9f7259",
 "analyst_reads_unshared_trip":true,
 "admin_reads_private_trip_without_access_operation":true,
 "device_token_survives_browser_logout":true,
 "database_user_version":2}
```

To trzy potwierdzone niezgodności z propozycją, nie zaliczenie nowych funkcji.
Migracje wykonywał wyłącznie historyczny kod w tymczasowej DB; nie zmieniono
schematu żadnej bazy aplikacji. Nie powtarzano całej regresji M8 przy zmianie
samych dokumentów; wyniki etapu 1 pozostają przypisane do tamtego audytu.

## 9. Odbiór etapów 3–9 i zakres coverage

| Etap / scenariusze | Wymagany dowód |
|---|---|
|3 MIG-01..05|Fresh schema, upgrade, noop, newer-schema refusal, checksum/FK/integrity; failed migration rollback i backup restore; bez automatycznego importu starych danych|
|3 OWN-01..03|Owner z sesji, parent trip scope, orphan quarantine; synthetic CLI import z niezmiennym źródłowym SHA256|
|4 AUTH-01..08|Register tylko DRIVER, unique normalized email, neutralne odpowiedzi, SMTP verification, limity loginu, bootstrap bez default; expiry/logout/renew/block/role version|
|4 RESET-01..06|Mailpit link bez API tokenu, hash-only, GET scanner nie consume, expired/used/invalid, concurrent max1 success; wszystkie sesje/device credentials revoked; SMTP fail/restart|
|5 ACL-01..08|Każdy restricted endpoint anon401, foreign404, S/B dla ZIP/replay/job/Range, TTL/revoke, admin reason/reauth/audit/notification, CSRF/Origin, device nie browser|
|6 DATA-01..08|Create/save/restart/read, edit revision, korekta before/after/actor/UTC/reason, niezmieniony SHA raw, filtry dat/trasy/status/koloru/type, stable keyset25/100, idempotency, archive bez purge|
|6 FAIL-01..04|DB/file failures start/finish/manual journaling, bez fałszywego COMPLETE, validmanifest recovery, retry nie mnoży eventów|
|7 UI-01..06|Design odebrany przez użytkownika, walidacja każdego formularza klient/server, loading/empty/error/401, fetch bez reload, keyboard/ARIA, bez unsafe HTML|
|8 ROLE-01..05|Analityk widzi tylko granty/shared i config; notatki raportu bez edycji raw; admin account/config bez domyślnego private read, B audyt, ostatni admin409|
|9 NAV-01..08|Demo bez ADB/telefonu/modelu; native LIVE osobny odbiór sprzętowy,320/390/desktop/landscape, źródła/UTC/STALE/reverse/off-route, brak CV gate override, replay isolation, busy komunikat drugiemu user|
|9 PHONE-01..05|Owner/code/device binding, mismatch device, logout/revoke/block/role/password/restart odcina credentials, authenticated409 refresh, buffered samples nie stają się świeże po zmianie runu|

Potwierdzamy zakres z audytu: **cały nowy backend** (auth, polityki, storage,
migracje, SMTP, sesje, import, API, worker intents) oraz używany rdzeń:
application/server; clocks/events/models/observations/prediction/simulation/
vehicle/solver/trajectory/positioning; telemetry/analysis/replay/gps_replay;
route_geometry/map_matching/route_events/live_navigation/mapping_analysis;
observation_history/review/completeness; CV contracts/tracking/validation/
workbench/capture. Każdy nowy moduł biznesowy wchodzi do pomiaru.

coverage.py branch=True, raport combined/lines/branches/per-module, JSON/HTML.
Próg >=70% combined uzgodnionego backendu; osobno wykazać nowy backend i core,
bez ukrywania trudnych security/I/O/recovery. Istotna logika JS (guidance,
perspective, validators, filters, pagination, session expiry) osobny Node/V8
pomiar i testy; Playwright to E2E, nie mianownik coverage Pythona. Java Android:
osobno JUnit/build/device acceptance; ewentualny Java coverage jawny, bez sumowania
procentów między językami.

Wyłączenia jawne jak w audycie: ui.py historyczny Tkinter nieużywany przez portal;
__main__.py entrypoint sprawdzany smoke; vision_probe benchmark; vision_detector
oraz vision_capture_worker adapter/hardware/ML z oddzielnym synthetic smoke i
walidacją offline; vision_demos fixture DTO; tools/testfixtures/vendor;
HTML/CSS/Android poza Python denominator; deklaracja Protocol.sample z `...`.
Polityka/owner/auth nie może trafić do wyłączeń nawet po przeniesieniu do workera.
Bazowe85.9985% dotyczy 7ece859; wąskie83% prototypu nie jest końcowym dowodem.
Etap2 nie mierzy nowego coverage ani nie implementuje SMTP/shares/GATE.

## 10. Decyzje produktowe do przeglądu

- **D1** Rekomendacja: sharing per ukończony trip, READ_ANALYZE oraz osobne
  EXPORT/CV_MEDIA; analityk nie koryguje danych O. Alternatywa uproszczona:
  tylko konfiguracje i synthetic bez analiz prywatnych danych. Bez globalnego odczytu.
- **D2** Rekomendacja: admin B self-approved po reauth, jedno ID,15min,
  audyt i powiadomienie O. Drugi approver rozszerza workflow poza v1.
- **D3** Rekomendacja: jedna active jazda/capture na deployment; scoped replay
  i jobs równolegle. Wielu kierowców live wymaga kolejnego runtime/schedulera.
- **D4** Rekomendacja: email verification i SMTP reset, Mailpit tylko demo,
  bootstrap bez domyślnych haseł; po utracie reset mail queue nowa prośba zamiast
  trzymania plaintext tokenu w DB. Konfiguracja poczty zależy od operatora.
- **D5** Rekomendacja: archive/valid=false bez fizycznego purge raw/oryginałów.
  Jeśli potrzebne trwałe usuwanie, osobny kontrakt retencji i zgód.
- **D6** Rekomendacja: logout parent kończy telefon i zapis, restart wymaga
  ponownego parowania, role/password/block odcinają wszystkie credentials.
- **D7** Rekomendacja: nie włączać starego runtime prototypu ani bez właściciela logów
  do nowych kont. Import CLI wyłącznie na osobne zlecenie. Nowy UI inspirowany
  ReactLY, istniejące funkcje M8 i wszystkie bramki live zachowane.

## 11. Weryfikacja etapu dokumentacyjnego

Kontrola dokumentu obejmuje: 7 obszarów promptu, role/scopes, DTO/endpointy/
CSRF i legacy, formularze, model/FK/indeksy/recovery/migracje, coverage,
scenariusze3–9 i decyzje D1–D7. Sprawdzenie tabel oraz staged diff jest odrębne
od testów implementacji. W commicie tylko contract.md, stages.md, ai-usage.md.
SHA256 zastanych zmian poza docs/school-app na wejściu:
80674326e7b927a660e3caecf9d95ba1c7558edc849659da81af0a6c751745e3
(`git diff --binary -- . :!docs/school-app`); sprawdzić identyczność na końcu.
Status po wykonaniu przeglądu: zweryfikowany dokumentacyjnie, oczekuje akceptacji.
Nie pushować/merge i nie rozpoczynać implementacji etapu3.

### Doprecyzowanie spójności kontraktu

- `verified_email_at` jest wymagane do ACTIVE przy zmianie statusu konta;
  odblokowanie nie może ominąć aktywacji. Bootstrap CLI ustawia jawny zweryfikowany
  stan operatorski. `delivery_state` tokenu ma QUEUED/SENT/FAILED; po restarcie
  QUEUED jest unieważniany. Crash po wysłaniu, a przed oznaczeniem SENT może
  unieważnić dostarczony link — bezpieczny kompromis, wymagający nowej prośby.
- CSRF preauth jest wyprowadzany przez HMAC analogicznie do sesji użytkownika;
  preauth key/cookie i browser key/cookie są różnymi kontekstami. Po rotacji cookie
  zmienia się też CSRF. Hash-only sekretu sesji nie uniemożliwia odtworzenia CSRF
  z sekretu dostarczonego w cookie bieżącego autoryzowanego żądania.
- Dates w T01 filtrują created_at (planowanie); daty faktycznej jazdy start/end
  są osobnymi kolumnami DTO. T08 filtruje server_received_at; measured_at nie
  jest wymyślane i może być null. Sortowanie/cursor używa tych samych pól co filtr.
- Listy własnych danych są available dla każdej roli; shared tylko ANALYST z S.
  Admin B czyta wskazany trip/zasób, nie dostaje globalnego listing query.
  T03 może zwrócić minimalne diagnostic capture IDs przy READ do V07, bez
  filenames/thumbnails; V01 i same media nadal wymagają CV_MEDIA.
- Analiza zapisuje snapshot raw/geometry/config hash oraz watermark korekt.
  Nowa korekta nie zmienia istniejącego raportu; kolejny job ma nowy snapshot.
  Raport wyraźnie rozdziela oryginalne fakty i efektywne korekty. Nie zasila faz.
- Backend sprawdza user status/role/security_version i resource grant także
  przy wykonaniu zadania, nie tylko enqueue. Łańcuch delegacji nie daje workerowi
  prawa czytania innych katalogów. Finalizacja rozpoczętego raw po revoke może
  działać jako ograniczona operacja systemowa z audytem, bez prawa ekspozycji danych.
- Rate limits stosują ten sam algorytm/window dla adresów istniejących i nie.
  Nie dodaje się szczegółów account status w publicznym 401/202/429.
- media_assets (operator staging) umożliwia wybór ASSET w Laboratorium; V27
  listuje tylko własne zaakceptowane metadane, nie ścieżki ani cudze pliki.
- Po kliknięciu revoke telefon traci credential natychmiast. Dowód utraty praw
  to denied ingest/read, nie ukrycie przycisku ani wyczyszczenie jednego cookie.

### Dokładny payload Androida i walidacja konfiguracji

N20 / alias /api/position przyjmuje następującą listę pól (inne są odrzucane):
session_id, timestamp_seconds, latitude, longitude, gps_accuracy_m, speed_mps,
speed_accuracy_mps, heading_deg, heading_accuracy_deg, altitude_m,
vertical_accuracy_m, is_mock, source, device_id, stream_id, sample_sequence,
elapsed_realtime_nanos, sent_elapsed_realtime_nanos.

W profilu portalu source musi być ANDROID_FUSED, device_id musi odpowiadać
client_device_id uwierzytelnionego urządzenia. Required: session_id zgodny z
active LIVE, timestamp_seconds finite>=0, latitude[-90,90],longitude[-180,180],
source/device/stream/sequence/oba zegary monotoniczne i is_mock bool. Stream ID
ASCII1–80, sequence i nanos int64>=0 (bool nie jest int); sent_nanos>=captured.
Pozostałe pola są nullable, lecz gdy podane muszą być finite; speed i accuracy
nieujemne, heading [0,360), altitude dowolna finite. Null nie zamienia się na0.
Backend zachowuje dalej istniejące quality/freshness/physical checks providera;
nie przełącza flagi live_control_eligible na podstawie parowania. Body nie
przyjmuje road_position_m, owner_id, trip_id ani server_received_at z telefonu.

Config payload z klienta zawiera tylko allowlist geometry/phase/source/dynamics
według rodzaju konfiguracji. Serwer wstrzykuje verification=DRAFT oraz
verified=false przed użyciem istniejących walidatorów wymagających tych pól.
Klient nie może podać lub nadpisać tych flag, także wewnątrz stop line/speed
section/source metadata. Opublikowany config nie oznacza weryfikacji drogowej.
Arbitrary filesystem source URL/path nie jest rozwiązywany przez backend.
