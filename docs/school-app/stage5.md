# Etap 5 — uprawnienia i ochrona API zasobów

Data: 2026-10-13. Przygotowany do odbioru po sprawdzeniach opisanych poniżej.
Baza zaakceptowanego etapu 4: **45eef418efa9ca0afc9af8a6137a286fa990f5a7**.
Worktree C:/Users/konra/.codex/worktrees/school-app/Surfy, codex/school-app.
Na wejściu HEAD zgodny, status i staging puste. Nadrzędny AGENTS.md pusty,
repozytoryjnego brak. Przeczytano kontrakt i rejestry etapów 1–4.
Nie czytano prywatnego data/runs ani starego runtime/school. PUBLISH-01 osobno.
Nie zmieniano 14 tabel, migracji (schema v2), solvera, loggera ani live GATE.

## Polityka i architektura

Nowe moduły school_resources: policy (bieżąca sesja/DB), reads (SQL/DTO),
files (manifesty, kontrolowane korzenie, eksport/CV), contexts (GPS replay/jobs),
api (jawna allowlista tras). AccountsHTTPServer nadal jest osobnym serwerem:
nie importuje starego Handlera i nie przekazuje mu żądań. Importy bez I/O.
Domyślna odmowa; tylko poniższe operacje zasobów są podłączone.

Actor wyłącznie z Sessions.lookup; status/security_version/expiry i rola pobierane
z DB. Polityka trip sprawdza owner albo aktywny ANALYST + grant READ_ANALYZE na
COMPLETE niearchiwalny parent. Odczyt obserwacji/korekty idzie przez parent trip.
ADMIN nie ma nadpisania polityki. role/owner/reauth z klienta niczego nie nadają.
role(...,reauth=True) wymaga świeżego serwerowego authenticated_at <=5min;
mutacje administracyjne HTTP pozostają niedostępne do etapu 8.
401 anonymous/expired/revoked;404 missing/foreign bez rozróżnienia;403 jawna
operacja niedostępnej roli;409 conflict/manifest/state;422 validation. DataError
Denied/Conflict/Invalid nie są globalnie zamieniane na503. Błędy neutralne,
JSON request_id, pliki X-Request-ID. Host/Origin/CSRF/body/headers etapu4 zachowane.

| Zasób/akcja | Anonimowy | DRIVER | ANALYST | ADMIN |
|---|---|---|---|---|
|Auth/shell/health|Kontrakty etapu4|Tak|Tak|Tak|
|Trip/observation/correction read|401|Własne|Własne + S|Własne|
|GPS replay/analysis/report|401|Własne COMPLETE|Własne + S|Własne COMPLETE|
|Export/CV metadata/events/media/Range|401|Własne|Własne; nigdy S|Własne|
|Config published|401|Tak|Tak|Tak|
|Config DRAFT/ARCHIVED read|401|403|Tak|Tak|
|Shared listing|401|403|S|403|
|Admin mutation|Niedostępne|Niedostępne|Niedostępne|Etap8 + reauth/audyt|

S oznacza jeden jawny READ_ANALYZE. Uprawnienia do jobs: właściciel lub
analityk-requester z aktualnym S oraz powiązaniem jego sesji/credential.
Inny analityk nie odczytuje cudzych job handles; może czytać autoryzowane
raporty parent trip. Replay handles są zawsze powiązane z sesją + jej aktualnym
hashem credential; rotacja nie zachowuje praw do starego replay.

## Inwentaryzacja działających endpointów

Prefix wszędzie **/school/api/v1**. Status wszystkich poniższych zasobów:
zaimplementowane i sprawdzone w etapie5. O=właściciel każdej aktywnej roli.

| Metoda/ścieżka | Polityka i źródło danych |
|---|---|
|GET /trips|SQLite owner_id;scope=shared wyłącznie active ANALYST/grant/COMPLETE/nonarchive|
|GET /trips/{trip_id}|SQLite O/S, bez run path/hash/owner email|
|GET /observations|SQLite;wymagany trip_id i jawny scope own/shared; parent O/S|
|GET /observations/{observation_id}/corrections|Parent trip O/S;immutable historia z autorem/czasem/before/after,SQL LIMIT|
|GET /trips/{trip_id}/export|O,COMPLETE/nonarchive,bezpośredni kontrolowany run-root,hash manifestu DB i raw/metadata|
|GET /config/versions|SQLite;DRIVER published,ANALYST/ADMIN także draft/archive|
|GET /config/versions/{version_id}|SQLite ta sama polityka;publication_is_field_verification=false|
|POST /trips/{trip_id}/replays|O/S,COMPLETE/hash,body {mode:GPS};GPSReplaySession ze scoped logger|
|GET /replays/{replay_id}|Sesja/credential + bieżące O/S;bez live recommendation|
|POST /replays/{replay_id}/control|Ta sama polityka + CSRF/Origin;PLAY/PAUSE/SEEK/RATE|
|DELETE /replays/{replay_id}|Ta sama polityka + CSRF/Origin,{};zamyka własny handle|
|POST /trips/{trip_id}/analysis-jobs|O/S,COMPLETE/hash + CSRF/Origin;{type:GPS_QUALITY}|
|GET /analysis-jobs/{job_id}|Owner albo requester z S, ponowna sesja/parent;bez path/result payload|
|DELETE /analysis-jobs/{job_id}|Jak GET + CSRF/Origin,{};cancel,bez usuwania raportu|
|GET /trips/{trip_id}/reports|O/S,scoped derived root,manifest/hash check|
|GET /trips/{trip_id}/reports/{report_id}|O/S,parent/raw hash i report manifest;bez surowych linków/filenames|
|GET /trips/{trip_id}/cv/captures|O;wyłącznie per-trip CV root,bez skanowania globalnych katalogów|
|GET /trips/{trip_id}/cv/captures/{capture_id}|O;manifest session_id/run_id + safe DTO,diagnostic only|
|GET /trips/{trip_id}/cv/captures/{capture_id}/events|O;hash events.jsonl,istniejący decode_vision,bez media_ref/source path|
|GET /trips/{trip_id}/cv/captures/{capture_id}/media/{segment}|O;VIDEO artifact/hash/path;każdy Range i chunk reauthorized|

20 nowych działających method/path. C01–C10 oraz C37 health pozostają działające
zgodnie z etapem4: GET preflight/me/health; POST register,verify-email,login,
reauth,logout,change-password,request-reset,reset-password,logout-all.
Publiczne pliki: /, /school/static/account.js, /school/static/account.css.
Brak publicznych test/provisioning endpointów. Fixture wyłącznie operatorski CLI
na PUSTEJ syntetycznej bazie, z getpass i produkcyjnym KDF.

Listy: stały sort created_at/id DESC (obserwacje server_received_at/id DESC),
limit1..100,offset0..10000. Nieznane/duplikowane query fields odmowa422.
Trips:from/to ms [from,to),route_id,status,archived,scope. Observations wymagają
trip_id:from/to,signal_id,state,event_type,scope. Config kind/logical_id/status.
Keyset cursor,global observations list,route/source/valid/sort filters i pełne UI
pozostają etap6/7; obecny offset nie oznacza ukończonej paginacji kontraktu.
Config payload z polami sekretów/storage lub absolutnymi path odmawiany409;
pełna walidacja formularzy konfiguracji przed jej zapisem/publikacją w etapie8.

## Niedostępne endpointy i późniejszy odbiór

404 oznacza niedostępność, nie dowód wdrożenia ochrony tej funkcji.

| Endpoint / powierzchnia | Stan i etap integracji | Docelowy owner/source |
|---|---|---|
|POST /trips;PATCH /trips/{id};POST archive|Niedostępne,6|Actor/SQLite;raw immutable|
|POST /trips/{id}/observations;POST corrections|Niedostępne,6|Parent O;osobne korekty/audyt|
|POST/DELETE /trips/{id}/share|Niedostępne,6|Parent O,exact analyst email,READ_ANALYZE,revokacja|
|GET /devices;PATCH/DELETE /devices/{id};POST/DELETE pairing-challenges|Niedostępne,9|Owner/browser parent/device hashes|
|POST /device/pair;GET /device/session;POST /device/position|Niedostępne,9|Code/bearer,parent/boot/version,nie local token|
|POST /navigation;GET navigation/{id};POST control;GET events|Niedostępne,9|O+jedna global lease;GATE bez zmian|
|Replay SIMULATION oraz RATE10|Niepodłączone,9|Istniejący odrębny SIM adapter;nie GPS fallback|
|Analysis MAPPING/COMPLETENESS/route snapshots|Niepodłączone,6/9;422 type unavailable|Scoped M8 index/route/derived integration|
|POST config;POST publish;PATCH draft|Niedostępne,8|Role,draft creator,ADMIN reauth,audit,schema validation|
|GET/PATCH admin/users;GET admin/audit|Niedostępne,8|Admin,bez prywatnych GPS/correction reasons;reauth mutations|
|GET maps/{id}|Niedostępne,9|Bundled allowlist i login|
|POST cv/captures;POST capture/stop|Niedostępne,9|O+lease/worker;nie globalny capture|
|GET capture/frames/{frame_id};preview/status live|Niedostępne,9|Capture+segment/frame context,nie arbitrary path|
|POST/DELETE cv associations;POST reviews|Niedostępne,9|O,fresh context,append provenance;no learning|
|Stare /api/state,/pair,/position,/routes,/runs i .zip|404;lokalna baza osobna|Ewentualne aliasy Android tylko w9 z nową polityką|
|Stare /api/analysis*,/mapping*,/replay*,/gps-replay*,/observation-history*|404|Tylko jawne nowe adaptery;pozostałe później|
|Stare /api/control,/reset,/view,/recording,/observe,/observe-route,/vision*|404|Bez globalnego Handler/state/token|
|/map-data*.json,/mobile,/mobile.js,/lab,/school-lab-bridge.js|404|Widoki i bundled resources po właściwej integracji|
|Runtime/DB/WAL/SHM/backups/secrets/pliki dowolną ścieżką|Nigdy publiczne|Brak ogólnego static root/listingu|

Nie wdrażamy break-glass/admin_access ani globalnego odczytu administratora.

## Adaptery, integralność i revokacja

Eksport ma dokładnie raw.csv,metadata.json,complete.json z RunLogger.
Sprawdza DB raw_ref (dokładny owned root),raw_hash,manifest_hash,schema/run IDs
oraz sha256 raw/metadata. ZIP tworzony w TemporaryFile,nie w wielkim BytesIO;
max64MiB wejścia,1 export/actor. Logger i format niezmienione.
Storage odrzuca traversal i wszystkie symlink/reparse ancestors; filenames CV
z allowlisty prostych nazw VIDEO,segment liczbowy. Brak klient path/URL.
OS operator z możliwością podmiany plików podczas odczytu jest granicą zaufania:
ACL/owner wolumenu ma blokować obcych writerów. Nie obiecujemy ochrony przed
złośliwym operatorem OS. Junction test własny Windows,POSIX nie wykonano tutaj.

Transfer: hash w chunk64KiB z ponownym sprawdzeniem sesji i O/S przed każdym;
przed headers i przed każdym wysłanym chunk<=64KiB ponowna kontrola. Revokacja
po headers zamyka transfer bez dopisywania JSON. Nie cofa wysłanych/pobranych
bajtów; revokacja między check a write może dopuścić ostatni chunk. Sockettimeout5s.
Media max256MiB,Range single bytes=start-end (bez suffix/multiple),max1MiB odpowiedzi
Range;invalid416. Pełny GET streamuje bez buforowania całego filmu. Obsługa
niepełnych/live capture,preview i dekodowanych frames jest dopiero etap9.
Syntetyczny video fixture sprawdza politykę/bytes/Range,nie dekodowalność wideo.
CV events używają istniejących VisionObservation DTO,obsługują segment session cid:0;
nie ujawniają media_ref/camera source i nigdy nie dają live eligibility.

Replay używa GPSReplaySession/RunAnalysis i scoped RunLogger,bez selected_route/global
application/default data. Jeden handle/session,max64global,TTL30min;GET snapshot
nie przesuwa timeline. POST control przesuwa go według monotonic delta(max30s)
i stosuje play/pause/seek/rate1,2,5. Ciągły player/mapa/SIM i pełny UX etap9.
Nie emituje rad live. Rotacja/logout/revoke/expiry/archive odcinają stare uchwyty.
Brak background replay worker;po odmowie nie może dalej przesuwać stanu.

GPS_QUALITY jest rzeczywistym RunAnalysis na raw.csv,nie placeholder success.
2 workers,queue20,max1actortrip i1000 pamięciowych jobs,TTL30min. Dostęp sprawdzany
przed enqueue,w workerze przed plikami/analizą oraz przed publikacją i na każdym
status/report. Cofnięcie grant podczas CPU obliczenia nie przerywa samego
niekooperującego M8 obliczenia,ale zabrania publikacji wyniku/odczytu. Cancel jest
kooperatywny na granicach,nie zabija wątku. Restart nie wznawia jobs/replays.
Report trwały w owner/trip/derived/{id}/report.json+manifest.json;hash źródła i
raportu sprawdzany na odczycie. Manifest zapisany ostatni;partial bez manifestu
nie jest gotowym raportem. Pełny audyt/recovery DB–raw–manifest nagrania pozostaje6.
Nie obiecujemy recovery nagrywania na podstawie tych adapterów ani intencji.
Logout telefonu/stoplogger po integracji etapy6/9,wymaganie pozostaje.

## Sprawdzenia

Własne wykonanie Windows/Python3.14.4/Node24/Edge headless,bez Linux claim.
Kod odbioru:09646eb735dd8f141de3f89087a644eb875c8a76.

- `python -m unittest discover -s tests -p test_school_resources.py -v`:
  **17/17 PASS,58.404s**. Setki subTest żądań,nie zastępują pomiaru coverage.
- Coverage command z run.md (pełne school_accounts+school_data+school_resources):
  **94 testy,93 PASS,1 skip,117.364s**. Konta/SMTP29,dane48,zasoby17.
- `python -m unittest discover -s tests -v` w świeżym śledzonym eksporcie
  artifacts/stage5-reviewed/source: **320 testów,319 PASS,1 skip,132.336s**.
  Brak błędu Tkinter w tym środowisku. Nie zmieniano testu/rdzenia,by go ukryć.
- Skip obu suite: POSIX symlink na Windows,WinError1314(brak przywileju).
  Istniejący Windows junction i nowy test adaptera junction PASS. Linux/POSIX
  wykonanie nie przeprowadzone;niezależne wyniki poprzednich etapów nie są naszymi.
- `node scripts/check_school_resources.cjs`: desktop1280x900 i phone390x844 PASS,
  każdy driver/analyst/admin,login→own/shared→foreign/admin/export denial→logout401;
  brak overflow/pageerror. Browser wywołuje fetch z prawdziwymi cookies,nie mock API.
- `node scripts/check_school_accounts.cjs`: oba viewport PASS pełnego workflow
  register/mail/verify/login/reauth/logout/reset/change/logoutall,z produkcyjnym KDF.
- `node --test tests/driver_ui.cjs tests/vision_workbench_ui.cjs`: **7/7 PASS**.
  `node tests/mobile_flow.cjs`: PASS.
- Rzeczywisty CLI init/keys/serve na TemporaryDirectory z nową syntetyczną DB:
  login→own200→foreign404→logout→401 PASS,realny KDF. Przy fixture CLI wstrzyknięto
  wyłącznie odpowiedzi getpass testowym adapterem;nie stworzono słabszego hasha.
  Próba piped stdin utknęła na Windows konsolowym getpass;zakończono wyłącznie
  zweryfikowany własny proces fixture. Interaktywny getpass pozostaje ręcznym krokiem.
- Bazowy `python -m greenwave --no-browser --port <wolny>` w świeżym eksporcie:
  HTML200 i /api/state200 PASS;bez telefonu/ADB/kamery/YOLO.

Macierz: wszystkie20 method/path są wykonywane;GETanon401,owner200,foreign404,
shared200 albo404 według zasobu,adminforeign404,expired/revoked401. Mutacje mają
Origin/CSRF odmowy403;DELETE {}zamyka/cancel,unknown fields422. Replay session
substitution/rotation/logout denial;share revoke/role/block/archive/reset i queued
job beforeexecute/afterCPU denial. ADMIN reauth TTL polityki bez wdrożenia panelu.
Eksport rawsha256 unchanged,ZIP3file,corruption409;CVevents bezsource/media_ref,
owner Range206,sharedCV404,invalidRange416;manifest traversal/DBfilename409;
junction Invalid;ścieżki percent../foreign IDs/legacy/runtime404. Błędy DTO bezsekretów.
Nie liczymy404 niepodłączonej funkcji jako wykonanego odbioru jej autoryzacji.

Pierwsze próby ujawniły błędy syntetycznych fixture: operation key za krótki,
SignalAssociation bezstatus/method,account-switch revoke przy współdzielonychcookies.
Poprawione fixture. Test jobstatus skorygowano do owner/requester policy;shared
analityk może czytać reports,ale nie handle joba innego requester. Przegląd zmienił
SQL LIMIT historii korekt i odmowę private storage/credential config payload.
Ponowiono finalne testy na aktualnym kodzie;żadnych bypassów ani omit coverage.

### Coverage branch=True,bez omit/exclude

Lokalne raporty ignorowane artifacts/stage5-final.coverage i stage5-final-coverage.json.

Dokładne komendy i ręczny odbiór: [run.md](run.md), sekcja10.
Zakres końcowy szerokiego backend/M8/CV i osobny JS pomiar pozostaje obowiązkowy;
wynik etapowy trzech pakietów nie zastępuje etapu10.

## Odbiór

- [ ] HEAD/branch/status i literalny zaakceptowany hash etapu4.
- [ ] Syntetyczny nowy root,init,keys,operatorskie fixture,getpass,serve.
- [ ] Dwa konta kierowców: own200,foreign404;anon/logout401.
- [ ] Analityk shared200,private404,export/CV404;ADMIN foreign404.
- [ ] Replay/job/report przed i po revoke/archive/password/role/block.
- [ ] Export manifest/niezmienność raw;CVevents/hash/Range/containment.
- [ ] Tests,permodule branch coverage,browser desktop+phone i niezależny przegląd.
- [ ] Akceptacja etapu5 przed promptem etapu6.

STOP przed6,bezpush/merge/rewrite i bez runtime/DB/mailbox/kluczy w Git.

## Pierwotny raport coverage (0b10d9b)

Linie **2150/2243 = 95.8538%**; gałęzie **594/772 = 76.9430%**; combined **91.0116%**. Wyłączenia:0.

school_resources:linie525/542=96.8635%,gałęzie165/232=71.1207%,combined89.1473%.

school_accounts:linie755/818=92.2983%,gałęzie184/242=76.0331%,combined88.5849%.

school_data:linie870/883=98.5277%,gałęzie245/298=82.2148%,combined94.4115%.

|Moduł|Linie wykonane/wszystkie|Gałęzie wykonane/wszystkie|Combined|
|---|---:|---:|---:|
|school_accounts/__init__.py|0/0|0/0|100.0000%|
|school_accounts/__main__.py|56/67|9/12|82.2785%|
|school_accounts/config.py|51/55|16/20|89.3333%|
|school_accounts/crypto.py|60/62|16/18|95.0000%|
|school_accounts/demo_mail.py|70/80|30/38|84.7458%|
|school_accounts/errors.py|4/4|0/0|100.0000%|
|school_accounts/http.py|212/237|68/98|83.5821%|
|school_accounts/limits.py|28/28|2/2|100.0000%|
|school_accounts/mail.py|57/60|7/8|94.1176%|
|school_accounts/service.py|163/169|25/34|92.6108%|
|school_accounts/sessions.py|54/56|11/12|95.5882%|
|school_data/__init__.py|3/3|0/0|100.0000%|
|school_data/__main__.py|32/33|7/8|95.1220%|
|school_data/accounts.py|50/50|19/20|98.5714%|
|school_data/backup.py|71/74|9/12|93.0233%|
|school_data/configurations.py|38/38|10/16|88.8889%|
|school_data/database.py|59/62|8/8|95.7143%|
|school_data/errors.py|11/11|0/0|100.0000%|
|school_data/locking.py|33/37|5/8|84.4444%|
|school_data/migrations.py|110/111|43/44|98.7097%|
|school_data/observations.py|78/78|26/40|88.1356%|
|school_data/repositories.py|8/8|0/0|100.0000%|
|school_data/repository_base.py|37/37|12/12|100.0000%|
|school_data/security_records.py|94/94|16/22|94.8276%|
|school_data/storage.py|48/49|15/16|96.9231%|
|school_data/time_units.py|26/26|14/14|100.0000%|
|school_data/trips.py|133/133|45/62|91.2821%|
|school_data/validation.py|39/39|16/16|100.0000%|
|school_resources/__init__.py|0/0|0/0|100.0000%|
|school_resources/api.py|61/61|37/42|95.1456%|
|school_resources/contexts.py|160/163|31/46|91.3876%|
|school_resources/files.py|154/161|48/72|86.6953%|
|school_resources/policy.py|37/37|9/10|97.8723%|
|school_resources/reads.py|113/120|40/62|84.0659%|


## Commity tego etapu

1.5ada5e834ac50d4bea07a6d57d7152b78bc6bda9 — wspólna polityka,scoped odczyty,
export/replay/jobs/CV,fixture i integracyjne testy.
2.09646eb735dd8f141de3f89087a644eb875c8a76 — browser smoke na dwóch viewport i harness.
3.Commit dodający stage5.md — run/stages/AI i odbiór,hash w odpowiedzi i
`git log -1 --diff-filter=A --format=%H -- docs/school-app/stage5.md`.
Staging wyłącznie tych źródeł/testów/dokumentów;nieDB/runtime/mailbox/secret.
Main/CV pozostały na wcześniejszych commitach. Nie pushowano ani scalano.


## Ponowny przegląd — konkretne udostępnienie kontekstu

Przegląd dotyczył **0b10d9b39c1f0251c513bcdfdffddffe74318b67**.
Użytkownik przekazał niezależny wynik Linux:17 testów zasobów PASS;pełna regresja
320 testów z jednym błędem importu Tkinter(brak biblioteki środowiska) i jednym
pominiętym testem Windows. To dowód dostarczony przez użytkownika,nie nasze
wykonanie Linux. Nie maskowano Tkinter ani testu rdzenia.

Polecenie poprawek otrzymano urwane na „przed dostępem do”. Poproszono o resztę
przez pytanie w czacie. Poniżej odbiór otrzymanej części;nie deklarujemy wykonania
nieotrzymanych wymagań ani akceptacji etapu5. Etap6 nie rozpoczęty.

### Reprodukcja przed zmianą kodu

Na nowej TemporaryDirectory:share→replay→revoke→nowyshare temu samemuanalyst
→GET starego replay. **Bez żadnego odczytu między revoke i nowym share**.
Test test_exact_reproducer_revoke_regrant_without_intermediate_read przed
poprawką zawiódł: **AssertionError:200 !=404**. Pierwsze wykonanie zebrało także
17 importowanych testów ResourceTests:18 testów,17PASS/1FAIL,67.822s. Następnie
poprawiono import w module testowym,żeby unittest nie zbierał obcej klasy.
Jedyny FAIL był dokładnym reproduktorem;pozostałe istniejące testy nie wykrywały
regrant resurrection. Nie dodano odczytu,który ukrywałby błąd.

### Przyczyna i poprawka

Kontekst pamiętał session/credential/trip,ale każde sprawdzenie wybierało dowolny
aktualny grant. Regrant odtwarzał dostęp do starych uchwytów.
AuthorizationBasis jest frozen dataclass:kind OWN/SHARE,actor_id,trip_id,share_id.
Pochodzi z aktualnej DB i Sessions.lookup,nie z DTO klienta.
Replay i job pamiętają tę podstawę oprócz dotychczasowej sesji/credential.
Policy.check_basis wymaga dokładnego share_id,trip_id,analyst_id,READ_ANALYZE,
revoked_at IS NULL,aktualnej roli ACTIVE ANALYST i COMPLETE nonarchive.
Nie wybiera innego grantu i nie przechodzi automatycznie do OWN.
Publiczne DTO nie ujawniają authorization/share_id/credential.

Replay read/control/close po revoke→regrant404. Stary replay jest usuwany na
pierwszej odmowie;sam zapisany share_id już uniemożliwia jego ożywienie bez
wcześniejszego odczytu. Nowy replay na nowymgrancie200,własnyownerreplay200.
Rotacja/logout/expiry nadal egzekwowane istniejącą regresją etapu5.
Jobs po nieważnym grancie mają trwałą flagę authorization_invalid/cancelled;
read/cancel analityka404. Owner management nie zamienia podstawy wykonania na OWN.
Właściciel zachowuje status/cancel niezależnie od ważności pierwotnej podstawy;
wcześniejszą błędną odmowę właścicielowi skorygowano w następnym przeglądzie. Raport poprawnie opublikowany przed revoke
pozostaje danymi właściciela. Świeży odczyt raportu to osobne O/S;nowy grant może
go dopuścić,bez przywrócenia starego handle joba.

Files.run dla kontekstów sprawdza pinned basis także przy hash/chunk kontroli.
Worker sprawdza ją przed plikami,ponownie przed analizą,po analizie i bezpośrednio
przed publikacją. Sessions.lookup może użyć istniejącego wewnętrznego połączenia,
bez alternatywnej implementacji uwierzytelnienia. Końcowe session/grant check
oraz niewielki zapis report/manifest są w BEGIN IMMEDIATE:revoke/archive/security
writer nie wchodzi pomiędzy kontrolę a publikację. Podczas niekooperującego CPU
M8 revokacja nie zabija wątku,lecz uniemożliwia publikację na cofniętym grancie,
także gdy przed końcem CPU pojawił się nowy share.
Nie deklarujemy transakcyjnego recovery DB–filesystem ani nowej funkcji produktu.

### Nowe testy

8/8 PASS,23.814s:
- dokładny reproduktor bez intermediate read;
- niezależne stare control i close404,nowy replay200,ownerreplay200,safe DTO;
- complete job status/cancel404 bez ożywienia;wcześniejszy owner report nadalread;
- queuedjob revoke→regrant:analyze nie wywołane,bezreport;
- runningjob revoke→regrant:brak publikacji;
- regrant po sprawdzeniu plików przed analizą:analyze nie wywołane;
- regrant po wcześniejszej kontroli przed transakcyjną publikacją:brakmanifestu;
- zgodność grant/recipient/trip i brakfallbackOWN.

Kod: **fdc06bb7efd82455ffbf00deb62a37d80c494e23**.
Końcowe własne wykonanie Windows:102 testy szkolne,101PASS/1skip,138.013s;
pełna regresja w izolowanym eksporcie:328 testów,327PASS/1skip,158.144s.
Eksport:git archive0b10d9b+wyłącznie4zmienione źródła i nowy plik testów;
zgodne z codecommitemfdc06bb. Żadnych prywatnych nagrań/runtime do eksportu.
Skip:Windows symlink WinError1314;Windows junction PASS. Tkinter naWindows
bez błędu;Linux nie uruchamiano. Nowe8testówPASS23.814s.
Browserresource i accountsdesktop1280x900/phone390x844PASS,Node7/7/mobileflowPASS.
Testy sesji obejmują rotację/logout/expiry/status/securityversion jak wcześniej.
Nie zmieniano schematu v2/14 tabel,migracji,solver/logger/livegate ani private roots.

### Aktualny coverage po poprawce,branch=True

Całe school_accounts+school_data+school_resources,bezomit/exclude:
linie **2198/2294=95.8152%**,
gałęzie **614/800=76.7500%**,
combined **90.8856%**,excluded_lines0.

|Moduł|Linie wykonane/wszystkie|Gałęzie wykonane/wszystkie|Combined|
|---|---:|---:|---:|
|school_accounts/__init__.py|0/0|0/0|100.0000%|
|school_accounts/__main__.py|56/67|9/12|82.2785%|
|school_accounts/config.py|51/55|16/20|89.3333%|
|school_accounts/crypto.py|60/62|16/18|95.0000%|
|school_accounts/demo_mail.py|70/80|30/38|84.7458%|
|school_accounts/errors.py|4/4|0/0|100.0000%|
|school_accounts/http.py|212/237|68/98|83.5821%|
|school_accounts/limits.py|28/28|2/2|100.0000%|
|school_accounts/mail.py|57/60|7/8|94.1176%|
|school_accounts/service.py|163/169|25/34|92.6108%|
|school_accounts/sessions.py|58/60|13/14|95.9459%|
|school_data/__init__.py|3/3|0/0|100.0000%|
|school_data/__main__.py|32/33|7/8|95.1220%|
|school_data/accounts.py|50/50|19/20|98.5714%|
|school_data/backup.py|71/74|9/12|93.0233%|
|school_data/configurations.py|38/38|10/16|88.8889%|
|school_data/database.py|59/62|8/8|95.7143%|
|school_data/errors.py|11/11|0/0|100.0000%|
|school_data/locking.py|33/37|5/8|84.4444%|
|school_data/migrations.py|110/111|43/44|98.7097%|
|school_data/observations.py|78/78|26/40|88.1356%|
|school_data/repositories.py|8/8|0/0|100.0000%|
|school_data/repository_base.py|37/37|12/12|100.0000%|
|school_data/security_records.py|94/94|16/22|94.8276%|
|school_data/storage.py|48/49|15/16|96.9231%|
|school_data/time_units.py|26/26|14/14|100.0000%|
|school_data/trips.py|133/133|45/62|91.2821%|
|school_data/validation.py|39/39|16/16|100.0000%|
|school_resources/__init__.py|0/0|0/0|100.0000%|
|school_resources/api.py|61/61|37/42|95.1456%|
|school_resources/contexts.py|178/183|35/54|89.8734%|
|school_resources/files.py|154/161|48/72|86.6953%|
|school_resources/policy.py|63/64|23/28|93.4783%|
|school_resources/reads.py|113/120|40/62|84.0659%|


Raport lokalny ignorowany artifacts/stage5-share-final-coverage.json;
pełne polecenia w run.md. Nadal nie końcowe szerokie pokrycie M8/CV ani JS.
Dokumentacyjny commit poprawki: `git log -1 --format=%H -- docs/school-app/stage5.md`.
Bezpush/merge/rewrite;status po commicie czysty,etap6nierozpoczęty.
Kompletne polecenie kolejnej korekty zastępuje brakującą końcówkę poprzedniego promptu.


## Końcowa korekta — zarządzanie jobem przez właściciela

Przegląd: **20d9be8437be5977d85948cdc456bcfbf430183b**. HEAD zgodny,worktree i
staging czyste. AGENTS przeczytany;nie zmieniono main/CV,schematu,loggera,solvera
ani live gate. Tylko nowe dane syntetyczne;bez prywatnego data/runs/starego runtime.
Nowy prompt jest kompletny;nie ma dalszego pytania o poprzednią końcówkę.

Przed poprawką HTTP reproduktor test_owner_status_reproducer_before_and_after_analyst_denial:
1 test,4 subTest FAIL404!=200,3.255s. Revoke i revoke→regrant,każdy przed i po
odczycie analityka ustawiającym authorization_invalid. Owner status przed revoke
był200;published report owner200. Problem był w kolejności job_authorize:
pierwotny grant blokował również prawo właściciela.
Po poprawce ten sam test PASS3.779s.

Kod rozdziela authorize_job_execution od authorize_job_management.
Execution sprawdza pierwotnego requester/session/credential i dokładny OWN/SHARE
przed plikami,obliczeniem,po obliczeniu i w końcowej transakcji publikacji.
Management najpierw sprawdza aktualną sesję i własność parent w DB. Owner dostaje
status/cancel bez closed=True i bez zależności od authorization_invalid.
Niewłaściciel nadal wymaga pierwotnej sesji i ważnego share;ADMIN foreign404.
Owner management odświeża ważność wykonania bez zmiany jego tożsamości:
actor_id/session_id/credential/authorization pozostają identyczne w testach.
Nieważne queued/running pokazuje CANCELLED;completed zachowuje COMPLETE/report_id.
Cancel204 jest idempotentny,nie usuwa opublikowanego raportu i nie zabija wątku.
Archiwizacja zabrania wykonania/nowego joba,ale nie zarządzania istniejącym handle.

|Po revoke/regrant starego joba analityka|GET status|DELETE cancel|
|---|---:|---:|
|Aktywny owner|200|204|
|Analityk-requester|404|404|
|Drugi kierowca|404|404|
|ADMIN,cudzy trip|404|404|
|Anonymous/expired/revoked session|401|401|
|Owner,błędnyCSRF/Origin|200 dla poprawnegoGET|403|

Nowe testy używają Event do zablokowania kolejki i obliczeń oraz potwierdzenia
zakończenia workera;nie sterują nim przez przypadkowe sleep.
14/14 share/context tests PASS48.536s (8dotychczasowych+6owner regression).
Queued cancel po revoke204,analyze nigdy niewywołane. Running cancel204 bezmanifestu.
Completed status200/cancel204 i report200;stary analyst404,nowy job działa.
Owner ownjob po archive200/204,nowa analiza409;handlepoTTL404.
Session/CSRF/Origin oraz old replay revoke→regrant denial zachowane.

Końcowe własne wyniki Windows/Python3.14.4:
- `python -m unittest discover -s tests -p test_school_share_contexts.py -v`:
  14/14PASS48.536s;17resources wykonane również w pełnym szkolnym suite.
- coverage command z run.md:108tests107PASS1skip195.816s;obejmuje accounts/SMTP/
  passwords/data/resources/share i owner management.
- pełny izolowany eksport20d9be+wyłącznie contexts.py i test_school_share_contexts.py:
  334tests333PASS1skip221.207s;źródła zgodne z5ce716c28c1014e97ec19f058c870fa1c9925984.
- skip w obu suite:Windows symlink WinError1314;Windows junction PASS.
  Tkinter jest dostępny,brak importerror. Linux nie uruchamiano w tej korekcie.
- `node scripts/check_school_resources.cjs` i `node scripts/check_school_accounts.cjs`:
  desktop1280x900 i phone390x844 PASS,prawdziwyHTTP/fetch/sesje i realny KDF.
  Browser obejmuje istniejący UI kont i odczytów;nie deklaruje nieistniejącego UIjobów.
- `node --test tests/driver_ui.cjs tests/vision_workbench_ui.cjs`:7/7PASS;
  `node tests/mobile_flow.cjs`:PASS.
Nie ma blokady środowiska poza jednym jawnie pominiętym symlink testem.
Nie wyłączano Tkinter ani trudnych ścieżek w testach lub coverage.
Etap5 przygotowany do końcowego odbioru;etapy6–12 Do zrobienia.

### Aktualny raport coverage po owner management

Całe trzy szkolne pakiety,branch=True,bezomit/exclude:
linie **2219/2313=95.9360%**,
gałęzie **621/808=76.8564%**,
combined **90.9965%**,excluded_lines0.

|Moduł|Linie wykonane/wszystkie|Gałęzie wykonane/wszystkie|Combined|
|---|---:|---:|---:|
|school_accounts/__init__.py|0/0|0/0|100.0000%|
|school_accounts/__main__.py|56/67|9/12|82.2785%|
|school_accounts/config.py|51/55|16/20|89.3333%|
|school_accounts/crypto.py|60/62|16/18|95.0000%|
|school_accounts/demo_mail.py|70/80|30/38|84.7458%|
|school_accounts/errors.py|4/4|0/0|100.0000%|
|school_accounts/http.py|212/237|68/98|83.5821%|
|school_accounts/limits.py|28/28|2/2|100.0000%|
|school_accounts/mail.py|57/60|6/8|92.6471%|
|school_accounts/service.py|163/169|25/34|92.6108%|
|school_accounts/sessions.py|58/60|13/14|95.9459%|
|school_data/__init__.py|3/3|0/0|100.0000%|
|school_data/__main__.py|32/33|7/8|95.1220%|
|school_data/accounts.py|50/50|19/20|98.5714%|
|school_data/backup.py|71/74|9/12|93.0233%|
|school_data/configurations.py|38/38|10/16|88.8889%|
|school_data/database.py|59/62|8/8|95.7143%|
|school_data/errors.py|11/11|0/0|100.0000%|
|school_data/locking.py|33/37|5/8|84.4444%|
|school_data/migrations.py|110/111|43/44|98.7097%|
|school_data/observations.py|78/78|26/40|88.1356%|
|school_data/repositories.py|8/8|0/0|100.0000%|
|school_data/repository_base.py|37/37|12/12|100.0000%|
|school_data/security_records.py|94/94|16/22|94.8276%|
|school_data/storage.py|48/49|15/16|96.9231%|
|school_data/time_units.py|26/26|14/14|100.0000%|
|school_data/trips.py|133/133|45/62|91.2821%|
|school_data/validation.py|39/39|16/16|100.0000%|
|school_resources/__init__.py|0/0|0/0|100.0000%|
|school_resources/api.py|61/61|37/42|95.1456%|
|school_resources/contexts.py|199/202|43/62|91.6667%|
|school_resources/files.py|154/161|48/72|86.6953%|
|school_resources/policy.py|63/64|23/28|93.4783%|
|school_resources/reads.py|113/120|40/62|84.0659%|


To coverage etapowe,nie końcowy szeroki M8/CV ani pomiar JS. Lokalne raporty
artifacts/stage5-owner* są ignorowane,bez danych użytkownika w commitach.

Commity korekty:
1.5ce716c28c1014e97ec19f058c870fa1c9925984 — execution i management,6newtests,
  aktualizacja testu końcowej publikacji do czytelnej nazwy funkcji.
2.Commit dokumentacji końcowego odbioru: `git log -1 --format=%H -- docs/school-app/stage5.md`.
Przegląd dotyczył20d9be8437be5977d85948cdc456bcfbf430183b;bezpush/merge/rewrite.

Końcowa checklista:
- [ ] Reproduktor owner status:4FAILprzed,wszystkie wariantyPASSpo poprawce.
- [ ] Owner200/204;analyst staryjob404;other/adminforeign404;anon/expired/revoked401.
- [ ] Queued bezexecute,running bezpublication,completed zachowuje report200.
- [ ] Tożsamość joba niezmieniona;archived owner status/cancel doTTL.
- [ ] CSRF/Origin403,nowy grant/newjob działa,stary replay nadal404.
- [ ] Pełna regresja/permodulecoverage i review2commitów.
- [ ] Akceptacja etapu5;dopiero kolejny prompt może rozpocząć6.
