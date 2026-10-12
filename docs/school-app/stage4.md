# Etap 4 — konta, sesje, email i reset hasła

Status: **Przygotowany do odbioru**. Etap 3 zaakceptowany przez użytkownika:
**2020b84d68ef3720c1b2d2345cf381c98a2a603b**. HEAD na wejściu równy tej bazie,
status i staging puste. Istniejący worktree C:/Users/konra/.codex/worktrees/school-app/Surfy,
branch codex/school-app. Obowiązujący globalny AGENTS.md pusty; dodatkowego w repo
nie znaleziono. main/codex/vision-camera nie zmieniane; solver,logger,GPS,predykcja i live gate bez zmian.
Nie odczytywano data/runs ani runtime/school; stare konta/nagrania nieimportowane.
Schemat pozostaje w wersji 2 i ma 14 tabel, zastosowane migracje niezmienione.

## Działająca implementacja i granice

Nowy pakiet greenwave.school_accounts:
crypto — scrypt/secrets/hash/HMAC;
service — rejestracja/aktywacja/reset/login/reauth/password change/bootstrap;
sessions — cookie lookup,preauth,CSRF,rotacja,activity;
limits — atomowe trwałe HMAC buckets w auth_rate_limits;
mail — ograniczona ulotna kolejka i background SMTP;
config — jawny profil/base URL/Host/proxy/TLS/SMTP/secrets;
http — samodzielny ThreadingHTTPServer, allowlist i walidacja;
__main__ — serve/secrets/benchmark/bootstrap-admin;
demo_mail — lokalny syntetyczny odbiornik SMTP i operator inbox;
web — minimalne formularze HTML/CSS/fetch JS.

Usługa wykorzystuje Database/Repository school_data i krótkie transakcje BEGIN
IMMEDIATE. Import nie wykonuje I/O; startup wymaga istniejącej aktualnej DB i Lease,
nie wywołuje migrate. KDF oraz SMTP poza transakcjami. Max2 KDF i64 request workers;
health niezależny od hash/wysyłki; pojemność/timeouty nie blokują całej aplikacji.

Namespace **/school/api/v1**. Publiczne: root shell,dwa pliki /school/static,
GET /health,GET /auth/preflight i odpowiednie POST auth. Chronione:GET /auth/me,
POST /auth/reauth,/auth/logout,/auth/logout-all,/auth/change-password.
Nowy Handler NIE importuje ani nie deleguje do GreenWave Handler/LocalServer.
/api/*,runtime/backupy,trips/devices/admin/config/media są404, także dla zalogowanego.
POST logout-all dodano jako potrzebną operację własnych sesji, bez panelu innych kont.

Działa register→SMTP→verify→login→me→logout oraz request-reset→SMTP→reset→login,
reauth i własna zmiana hasła. Role/stan/owner/verified z formularza odrzucane.
Register zawszeDRIVER/PENDING_VERIFICATION, poprawne żądanie nowego/istniejącegoemail
neutralne202. Existing PENDING register może ponowić VERIFY; istniejący ACTIVE/BLOCKED
nie jest nadpisywany. request-reset PENDING ponawia VERIFY,ACTIVE wysyła RESET.
Nie zwracamy informacji o istnieniu adresu. Publiczny bootstrap nie istnieje.

## Hasła, tokeny, jednostki

12–128 Unicode code points,<=512 UTF8B,bez trim/normalizacji,confirmation dokładna.
UI liczy Unicode przez Array.from,server przez len. ScryptN131072,r8,p1,dklen32,
losowa sól16B,maxmem256MiB,compare_digest. Format:
`scrypt$v1$131072$8$1$32$<salt hex32>$<digest hex64>`.
Obsługiwany legacyv0/v1 N65536,r8,p1,dk32; poprawny login robi rehash do bieżącego.
Format/parametry/sól/digest są ograniczone przed wykonaniem KDF. Nieistniejące konto
wykonuje dummy verification. Max2 równoległe kosztowne operacje; przeciążenie503.
Test injectionN1024 jest tylko konstruktorem w fixtures: brak CLI/env do osłabienia
produkcji/demo. Browser fixture i rzeczywiste CLI używają produkcyjnegoN131072.

Tokens/session secrets>=32randombytes,hashSHA256 wDB; email HMAC w rate buckets;
CSRF HMAC klucza deploymentu z raw cookie+ID+purpose,hash wDB dla session.
Raw token tylko pamięć/SMTP/mailbox,nie DB/outbox/audit/logi/public API. Link tylko
PUBLIC_BASE_URL /#verify=... lub /#reset=...,client przejmuje i czyści fragment,
także przy same-document hashchange. GET nigdy nie consume. POST atomowo używa
purpose/security_version/single-use i zmienia konto; błędy tokenów jednolite422.
Blokowane konto nie aktywuje/resetuje dostępu; dwa równoległe resetPOST max1 sukces.
Błąd transakcji wycofuje used_at/password/status/revokację. Brak auto-login.

Wszystkie czasy INTEGER UTC ms:verify86400000,reset900000,preauth900000,
idle1800000,absolute28800000,reauth300000. last_activity write max1/min.
Actor tylko z session,reauthenticated_at zDB authenticated_at,nie body/header.
Login ma jednolite401 missing/wrong/pending/blocked. Cookie gw_session/preauth:
HttpOnly,SameSiteStrict,Path/,bez Domain;Secure w real. Reauth rotuje secret+CSRF,
nie przedłuża absolute; stare secret/CSRF nieważne. Key rotation odcina stare sesje.
Logout cofa bieżącą sesję i jej device/pair;logout-all wszystkie;passwordchange/reset
security_version++ i revoke browser/account/device/pair credentials atomowo.
Nie ma jeszcze aktywnego loggera/nav w portalu,więc faktyczne zatrzymanie GPS/CV
contexts po revoke jest integracją przyszłych etapów,nie deklaracją tego odbioru.

## Limity i HTTP

Login:5failures/email/15min,30attempts/IP/15min; sukces czyści emailfailurebudget,
503KDF_BUSY go zwraca,nie jest błędnymhasłem. Register5/IP/h;reset/activation wspólnie3/email/h,
10/IP/h;tokenuse10/IP/15min;reauth5/session/15min. Preflight100/IP/15min,max 1000memory.
429+Retry-After; brak trwałego blokowania users.status przez napastnika. Hashowane
HMAC klucze,bez plaintextemail/IP w licznikach;retencja purge expires_at.

Exact Host i Origin;mutacje wymagają właściwego preauth/session CSRF. Preflight
rotuje/revokuje stary preauth. Brak CORS,JSON object/exact required fields/no duplicates/
noNaN,Infinity/surrogates/wrongtypes,Content-TypeJSON,body8192B. Rejected body jest
bounded discard przed close (Windows TCPreset poprawiony),nie przetwarzany jako dane.
NeutralneJSONerror,bez SQL/stack/path/secrets;no-store,nosniff,ReferrerPolicy no-referrer,
CSP bezunsafe-inline,HSTS real. Public health:{ok,deployment_mode},bezcounts/mailconfig.
Handler nie loguje URL/body/cookie. Nieznane metody/ścieżki nie odsłaniają legacy.

Demo jest jawnie localhostHTTP,tylkoexample.test,SMTP/inboxloopback. Real wymaga
HTTPS/Secure iSTARTTLS/SMTPS z certverify. DirectTLS cert/key lub jawnie trusted
localHTTPSproxy;bezcert real bind tylkoloopback,peer/protozweryfikowane. Forwarded
headers niezaufanego peer ignorowane. Proxy musi nadpisywać/usunąć klientowskie
Forwarded headers. Konfiguracja pozaGit;CLI generuje nowe klucze bez overwrite.

## SMTP i recovery

Smtp timeout5s naoperacje socket;queue max 100 jobs wRAM,worker niezależny odHTTP.
Reservation przed issue zabezpiecza pełną kolejkę: nowe konto może zostaćPENDING,
lecz nie tworzymy niewysłanego tokenu z rzekomymSENT. API zawsze warunkowe202,
nie dowód wysłania. PENDING/SENT/FAILED zapisywane zgodnie z wynikiem. Błąd wysyłki
revoke+FAILED; błądDB poSMTP może pozostawićPENDING,nie fikcyjneSENT;worker nie ginie
ani nie loguje wyjątku. Startup unieważnia utraconePENDING,bez trwałego retry raw.
Crash poSMTPprzedSENT może unieważnić dostarczony link;użytkownik żąda nowego po cooldown.
Dostarczony localdemo_mail to prawdziwySMTPsink+osobny operator inbox127.0.0.1:8771,
RAM100messages,example.test only;nie endpoint portalu. Mailbox znika po restarcie,
nie nadaje się do realnych danych. Docker/Mailpit/drugi komputer etap 11.

Bootstrap:CLI getpass,dwa wpisy hasła,bez argv/defaultpassword. Jawne
--confirm-email-ownership oznacza operatorskieACTIVE+verifiedtime. BEGINIMMEDIATE
sprawdza brak aktywnegoADMIN i istniejącego email,auditBOOTSTRAP_ADMIN. Brak
publicznego tworzeniaADMIN;zarządzanie rolami pozostaje na etap 8,lastadmin policy school_data.

## Wykonane sprawdzenia 2026-10-12

Własne Windows/Python3.14.4/Node24.18/Edgeheadless/coverage7.13.1:

- **29 testów kont i operacji PASS** (14 HTTP/service + 12 operations + 3 crypto/config).
- Konta+dane **77 testów OK,1skip**,57.506s;w tym niezmieniona regresja48school_data.
- Pełny izolowany Git export 9dcf41e: **303 testy OK,1skip**,78.617s.
- Skip znany WinError1314 symlinka;Windowsjunction PASS. Tkinter bez blokady.
- Node7/7+mobileflow PASS. BaseCLI w izolowanym eksporcie HTML/stateHTTP200 PASS.
- Browserdesktop1280x900 i phone390x844: register/clienterror/actualSMTP/verify/
  login/reauth/logout/reset/change-password/logout-all PASS;hash cleared,nooverflow,
  no localStorage,password/bearer notstored,pageerrors0. ProdukcyjnyKDF.
- Rzeczywiste subprocessCLI: init/noop/keys/demomail/serve/register/mail/verify/login/
  me PASS naTemporaryDirectory zdefaultKDF,nie tylko wywołania funkcji.
- UnitCLI bootstrap/getpass/conflict,SMTPfailure/fullqueue/startupPendingRecovery,
  certverify transport mock bezexternal sends;actuallocalSTARTTLSfailure PASS.
- Parallel register uniqueemail/parallelreset/rollbackHTTP i service PASS.
- Fixation,CSRF/Origin,oldcookies,ttl/status/version/allcredentialrevoke,429 i spoofed
  ForwardedIP,slowKDF/SMTPnieblokująhealth,secret-freeDTO/log/audit PASS.
- Początkowe testy ujawniły: fixtureUTF8 czytana jako cp1252;zły mockSMTP.__enter__;
  błędna fixturegetpass
  zbytmało wartości;benchmarkHANDLEctypes bezargtypes. Naprawione testy/benchmark.
  Browser wykrył brakhashchange dla same-document link — poprawiona implementacja.
  Windows early403 wymagał drain rejectedbody dla stabilnej odpowiedzi — poprawione.

Bez prawdziwych wysyłek/osób/prywatnych baz/nagrań. Linux nie uruchamiano w tymetapie.
Nie testowano realnegoSMTPcertificate/networkdeployment/proxy/certifikatuHTTPserwera;
mockTLS potwierdza konfigurację,a nie ukończone wdrożenie. Docker/telefon/ADB/YOLO/
pełneM8browser/Androidbuild niepowtarzane —niezmieniane. PUBLISH-01 nadaloddzielny.

## Rzeczywisty KDF pomiar (osobny CLI proces)

`python -m greenwave.school_accounts benchmark`:
3hashy:0.5736631,0.5716472,0.5728665s;mediana **0.5728665s**.
CPU:0.578125,0.546875,0.5625s. ProcessPeakWorkingSet **175083520B (~167MiB)**,
pomiarGetProcessMemoryInfo Windows. Core estimate128*N*r=134217728B (128MiB)/op;
max 2 daje256MiBcore+overhead,maxmem256MiB/op. Peak obejmujePython/importy/dummyHash,
nie jest samą alokacją KDF. Trzeba zmierzyć ponownie na docelowym sprzęcie;nie osłabiono demo.

## Coverage etapowe,branch=True,bez omit/exclude

Konta:linie717/777=92.2780%,gałęzie171/226=75.6637%,combined**88.5344%**.
Dane:linie870/883=98.5277%,gałęzie245/298=82.2148%,combined**94.4115%**.
Razem:linie1587/1660=95.6024%,gałęzie416/524=79.3893%,combined**91.7125%**.
73 brakujące linie/108gałęzi,zero exclusions. To nie końcowe szerokie backend/M8/CV
coverage i osobny JS pomiar etapu 10. BrowserE2E nie zastępuje pomiaru JS coverage.

|Moduł|Linie wykonane/wszystkie|Gałęzie wykonane/wszystkie|Combined|
|---|---:|---:|---:|
|school_accounts/__init__.py|0/0|0/0|100.0000%|
|school_accounts/__main__.py|56/67|9/12|82.2785%|
|school_accounts/config.py|51/55|16/20|89.3333%|
|school_accounts/crypto.py|60/62|16/18|95.0000%|
|school_accounts/demo_mail.py|70/80|30/38|84.7458%|
|school_accounts/errors.py|4/4|0/0|100.0000%|
|school_accounts/http.py|174/196|56/82|82.7338%|
|school_accounts/limits.py|28/28|2/2|100.0000%|
|school_accounts/mail.py|57/60|6/8|92.6471%|
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

Dokładne polecenia tests/coverage/CLI i ręczny przebieg: [run.md](run.md).
Wyniki lokalnie ignorowane artifacts/stage4*.log/json/coverage i stage4-reviewed.
Screenshots syntetyczne: artifacts/school-accounts/{desktop,phone}-{account,reset}.png
oraz analogiczny folder w eksporcie;nie skrzynka poczty ani prywatne dane.

## Commity i ręczny odbiór

1.d0b2ddcbb2aea9c74ff3710a7e341e4997be5462 — konto/KDF/session/volatileSMTP services.
2.90beec7bd5b0abc51548e5c240e9e439708d2f87 — izolowanyHTTP,CLI,forms,fulltests/browser.
3.4746c9ee5c55806e91e9bb25f7881244958322de — KDF_BUSY nie zużywa budgetwrongpassword.
4.2b9ed3ddb8e34e316701270e64904c290a73541b — czytelność źródeł UI.
5.9dcf41e1b3e7140a64b437357f94f9614400eea2 — wspólny limit wiadomości register/reset,bez enumeration.
6.Commit dodający stage4.md — dokumentacja/odbiór,hash:
`git log -1 --diff-filter=A --format=%H -- docs/school-app/stage4.md`.
Pełny hash w odpowiedzi;literalnie następny rejestr żeby nie tworzyć odwołania do własnego przyszłego hasha.

- [ ] Init jawnegoNOWEGOroot,keys,profildemo,poczta,bootstrapprzedstartem.
- [ ] Register example.test→mailbox→verify→login→me→logout.
- [ ] Requestreset→mail→newpassword→login;change-password→loginponownie.
- [ ] Reauthrotacja i logout-all;legacy/runtime/admin/trips404.
- [ ] Tests/coverage/browser i niezależny przegląd commitów.
- [ ] Akceptacja etapu4 przed promptem etapu5.

STOP przedetapem 5;bez push/merge/rewrite/starychDB i bez sekretów/runtime w stagingu.
