# Etap 8 — widoki analityka i administratora

**Przygotowany do ponownego odbioru**, 2026-10-14. Zaakceptowany etap 7:
**0499805f282d39944989fb88232fda8cfdb256c9**. HEAD na wejściu zgodny, status i staging
puste, worktree C:/Users/konra/.codex/worktrees/school-app/Surfy, codex/school-app.
Przeczytano pusty obowiązujący AGENTS, contract, stage4–7, stages, run i ai-usage.
Nie czytano prywatnych data/runs ani starego runtime/school. Nie uruchomiono etapu 9.

## Macierz ról

| Działanie | DRIVER | ANALYST | ADMIN |
|---|---|---|---|
| Własne przejazdy, obserwacje i ich mutacje | Tak | Tak | Tak |
| Opublikowane konfiguracje | Tak | Tak | Tak |
| Jawnie udostępnione COMPLETE, niearchiwalne przejazdy | Nie | READ_ANALYZE | Nie |
| Shared obserwacje, historia, GPS replay, GPS_QUALITY, raporty | Nie | Tak, aktualny grant | Nie |
| Zmiana cudzych danych, shared eksport lub CV | Nie | Nie | Nie |
| Drafty wspólnej konfiguracji | Nie | Odczyt; tworzenie i edycja własnych | Odczyt, tworzenie i edycja wszystkich |
| Publish/archive konfiguracji | Nie | Nie | Reauth, CSRF, Origin, powód |
| Lista kont i bezpieczny audyt | Nie | Nie | Tak |
| Role/block/unblock | Nie | Nie | Reauth, revision, powód; ostatni aktywny admin chroniony |

Menu odwzorowuje politykę serwera; nie nadaje praw. Każda rola zachowuje własne dane.
Nie ma globalnej listy przejazdów administratora, break-glass ani nowych zgód na filmy.

## Backend i endpointy

Nowy mały pakiet school_admin: service.py (transakcje i projekcje), validation.py
(ścisłe schematy i adaptery walidatorów domenowych). Schema pozostaje **v3, 14 tabel**;
żadna zastosowana migracja nie została zmieniona. Wspólny Policy używa aktualnej
sesji i DB, a reauth jest serwerowym UTC integer ms. Poprawiono obsługę pustego
reauth oraz zakaz ACTIVE dla niezweryfikowanego konta także w zaufanym repo.

Wszystkie ścieżki poniżej mają prefiks `/school/api/v1`.

| Metoda i ścieżka | Pola / query | Dostęp |
|---|---|---|
| GET /admin/users | email dokładny, role, status, limit, cursor | ADMIN; bezpieczne DTO kont |
| PATCH /admin/users/{id} | expected_revision, role?, status? ACTIVE/BLOCKED, reason | ADMIN + świeży reauth; brak hasła i timestamp klienta |
| GET /admin/audit | actor, action, from/to RFC3339, limit, cursor | ADMIN; SQL allowlista akcji i typów USER/CONFIG |
| GET /config/versions | kind, logical_id, status, limit, cursor; zachowany offset starszego API | DRIVER PUBLISHED; ANALYST/ADMIN także DRAFT/ARCHIVED |
| GET /config/versions/{id} | — | Ta sama polityka stanów |
| POST /config/versions | kind, logical_id, payload, reason, base_version_id? | ANALYST/ADMIN, tworzy DRAFT |
| PATCH /config/versions/{id} | payload, expected_revision, reason | Własny draft ANALYST; dowolny draft ADMIN |
| POST /config/versions/{id}/publish | expected_revision, reason | ADMIN + reauth |
| DELETE /config/versions/{id} | reason | ADMIN + reauth, idempotentna archiwizacja |

Nowych endpointów jest **7**; dwa odczyty konfiguracji były już dostępne i otrzymały
cursor. Listy administracji i konfiguracji używają podpisanego Paging: actor, rodzaj,
filtry, as_of, TTL 15 min, time+id. Audit używa server_at+sequence z reprezentacją
sequence w wewnętrznym cursorze. Default25/max100. Brak pełnego snapshotu rekordów
zmiennych; każda strona ponownie sprawdza bieżącą sesję i rolę. Offset konfiguracji
zachowano wyłącznie dla istniejących klientów; UI używa cursor i nie łączy obu.

Lista kont zwraca id, display_name, email, role, status, revision, daty. Nie ma
password_hash, token_hash, security_version, devices, GPS ani storage paths.
Audit wybiera wyłącznie allowlistę account/auth/admin/config, dodatkowo resource_type
USER/CONFIG, bez dowolnych payloadów. Powód pokazuje tylko dla operacji admin/config;
powody korekt, prywatne notatki i nawet niespójny AUTH_LOGIN/TRIP nie trafiają do DTO.

Mutacje i ich audyt są atomowe przez Repository.atomic/BEGIN IMMEDIATE. Zmiana konta
unieważnia sessions/tokens/devices/pairing, zwiększa revision/security_version i cofa
zgody odbiorcy, który nie jest już aktywnym ANALYST. Unblock nie odtwarza credentials
ani grants. Kontrola ostatniego ACTIVE ADMIN działa pod tą samą blokadą transakcyjną.
Własna degradacja/blokada admina kończy jego sesję. Nie ma ustawiania cudzych haseł.

credentials_changed uruchamia istniejącą techniczną finalizację nagrywania oraz
proaktywne reconcile kontekstów replay/jobs. Job nie zmienia actor/session/credential
ani OWN/konkretnego SHARE. Completed raport pozostaje danymi właściciela; owner
status/cancel zachowuje niezależną politykę zarządzania. Odmowy legacy/runtime nadal
pozostają; nie dodano catch-all ani lokalnego tokenu jako zastępstwa kont.

## Konfiguracje i wiarygodność

ROUTE używa istniejącego load_route (kontrolowany tymczasowy plik walidacyjny,
nie ścieżka klienta), SIGNAL — SignalModel/SignalType/Corridor, MODEL —
PredictionSettings/SignalRelation. Wcześniej sprawdzane są dokładne allowlisty pól,
typy, finitywność, limity i relacje. Geometria 2–10000 współrzędnych, sygnały max1000,
relacje max1000, payload max262144B. HTTP envelope ograniczony do270336B tylko dla
namespace konfiguracji; pozostałe formularze nadal8192B.

Klient nie ustawia flag weryfikacji, także zagnieżdżonych. Serwer nadaje geometrii
`verification: {status: DRAFT}`, a sygnałom/relacjom `verified:false`,
`data_quality:UNVERIFIED`, `last_verified:null` (dla sygnałów). Publish ponownie
waliduje payload, nie nadaje FIELD_CHECKED i nie zmienia solvera lub live gate.
URL http/https bez credentials może być tylko metadanymi `source.url`; nie jest
pobierany ani rozwiązywany. Dowolne URL/path/root są odrzucane. Source ma attribution,
opcjonalnie description/url. SIGNAL source pozostaje tekstem istniejącego modelu.

Published payload i hash pozostają niezmienne; nowa wersja ma nowe ID. Archiwizacja
zachowuje historię i FK trip. Nowe szkolne nagranie kopiuje wersję/payload/hash trasy
do `school_route_snapshot` metadata, nie zmieniając loggera i jego formatu. Test
publikacji następnej wersji i archiwizacji porównuje rekord trip oraz bajty metadata
i raw. Nie przepisuje istniejących nagrań. Brak obietnicy wspólnej transakcji DB/FS.

## Widoki i formularze

- ANALYST: osobne Udostępnione przejazdy (`scope=shared`), istniejące filtry/keyset;
  szczegóły tylko odczyt i historia korekt z jawnym shared także w findObservation.
  Brak edit/archive/correction/share/export/CV. Lista, szczegóły i historia okresowo
  sprawdzają parent access; odmowa usuwa prywatny widok i kończy polling.
- Laboratorium own/shared: GPS replay create/read/play/pause/seek/rate1/2/5/close,
  GPS_QUALITY create/status/cancel, opublikowane raporty i metryki z jednostkami.
  Replay controls są serializowane i zablokowane podczas żądania; nie ma mapy/live.
  Polling ma epoch konta i serial widoku, sprawdzane także po await.
  Po Play jawne POST PLAY (CSRF) przesuwają timeline do końca; GET nadal nie mutuje.
  Automatyczne i ręczne controls są serializowane; starszy status nie cofa nowego sterowania.
- ADMIN: filtrowalna lista kont, modal role/status/reason, bezpieczny audit.
  Przy REAUTH_REQUIRED modal zostaje zamknięty, a draft w pamięci wraca po
  potwierdzeniu hasła wyłącznie temu samemu użytkownikowi, po odczycie zasobu i praw.
  Każda mutacja nadal wymaga świadomego submit; szczegóły poprawki niżej.
- Konfiguracje: lista stanów/rodzajów/ID, szczegóły, create/edit draft, nowa wersja,
  publish/archive. Pola kind/logical_id/reason są nazwane; złożona geometria/fazy
  używają jawnego zaawansowanego JSON z szablonami ROUTE/SIGNAL/MODEL i walidacją
  klienta oraz niezależną pełną domenową walidacją serwera. Edycja nie zmienia kind/ID.
- Konflikt409 pobiera aktualny rekord/payload/revision; przycisk świadomego przyjęcia
  rewizji nie wykonuje mutacji. Form busy, etykiety/błędy/aria-live, native modal
  Escape/focus restore. Dane tylko textContent; bez unsafe-inline/localStorage.

## Sprawdzenia

Końcowe wykonanie Windows, Python3.14.4, coverage7.13.1, Node24.18.0, Edge/Playwright:

| Sprawdzenie | Wynik |
|---|---|
| `python -m unittest discover -s tests -p test_school_admin.py -v` |10 PASS,34.572s; SQLite/HTTP real,synthetic|
| `coverage run --branch --source=greenwave.school_admin,greenwave.school_accounts,greenwave.school_data,greenwave.school_resources,greenwave.school_records,greenwave.telemetry -m unittest discover -s tests -p 'test_school*.py' -v` |157 testów,333.206s,OK(skipped1)|
| Pełna `python -m unittest discover -s tests -p 'test_*.py' -v` w nowym izolowanym eksporcie aktualnego kodu bez runtime/data/runs |383 testy,341.814s,OK(skipped1)|
| Node `--test tests/school_roles.cjs tests/school_portal.cjs`, z V8 coverage sześciu modułów |25 PASS|
| `node --test tests/driver_ui.cjs tests/vision_workbench_ui.cjs` |7 PASS|
| `node tests/mobile_flow.cjs` |PASS|
| `node scripts/check_school_roles.cjs` |desktop1360×900,phone390×844,narrow320×844 PASS; rzeczywisty HTTP i produkcyjny scrypt|
| `node scripts/check_school_ui.cjs` |3 rozmiary PASS; pełna regresja formularzy etapu7, screenshoty do artifacts|
| `node scripts/check_school_accounts.cjs` |desktop/phone PASS; register/mail/verify/login/reauth/logout/reset/change/logout-all|
| `node scripts/check_school_resources.cjs` |desktop/phone PASS; own/shared/foreign/admin/export/logout|
| CLI serve/GreenWave --help, diff check, UTF8/link/fence/PowerShell checks |PASS (kontrola dokumentacji po dopisaniu wyników)|

Jedno pominięcie w każdej regresji to Windows symlink, WinError1314 (brak privilege).
Nie jest to błąd kodu; Windows junction test PASS. Nie deklarujemy wykonania POSIX/Linux.
Tkinter jest dostępny tutaj; nie zmieniono/ukryto jego testu. Backend testy obejmują
role/reauth/CSRF/spoof/revision, atomową ochronę ostatniego admina także przez równoległe
HTTP, pending verification, block/unblock/session invalidation, finalizację nagrywania,
Event-sterowany running job bez publikacji i zachowane owner management/identity,
audyt bez private resource/reason, wszystkie rodzaje config, immutability, snapshot,
nested verification i brak pobierania źródłowego URL. Dotychczasowe testy pinned share,
replay/jobs, Range/eksport i recovery pozostają w szkolnej regresji.

Browser role suite sprawdza także 401 po realnej zmianie roli oraz po block świeżej
sesji, brak powrotu credentials po unblock, utratę shared widoku, stare handles404
po regrant, poprawne rate2, JSON validation, edit draft, publish, driver visibility,
Escape/Tab/focus i overflow wszystkich3rozmiarów. Nie użyto sleep do sterowania wyścigami.

### Coverage Python

Pomiar całych pięciu szkolnych pakietów oraz telemetry, branch=True, bez omit/exclude
nowych trudnych I/O lub odmów. Nie jest to końcowy uzgodniony szeroki mianownik M8/CV.
Telemetry wynik niższy, ponieważ pomiar wykonuje suite szkolną, a nie wszystkie
niezależne testy loggera. Reads zawiera również stare niewykorzystywane ścieżki,
które pozostają w mianowniku; nie usunięto ich, aby zawyżyć liczbę.

- Cały mierzony zakres: 3058/3239 lines (94.4119%), 898/1220 branches (73.6066%), combined 88.7194%.
- Pięć szkolnych pakietów: 2967/3106 lines (95.5248%), 890/1190 branches (74.7899%), combined 89.7812%.
- Nowy school_admin: 184/191 lines (96.3351%), 90/126 branches (71.4286%), combined 86.4353%.

| Moduł | Linie pokryte / wszystkie | Gałęzie pokryte / wszystkie | Combined |
|---|---:|---:|---:|
|greenwave/school_accounts/__init__.py|0/0|0/0|100.00%|
|greenwave/school_accounts/__main__.py|56/67|9/12|82.28%|
|greenwave/school_accounts/config.py|51/55|16/20|89.33%|
|greenwave/school_accounts/crypto.py|60/62|16/18|95.00%|
|greenwave/school_accounts/demo_mail.py|70/80|30/38|84.75%|
|greenwave/school_accounts/errors.py|4/4|0/0|100.00%|
|greenwave/school_accounts/http.py|224/247|74/104|84.90%|
|greenwave/school_accounts/limits.py|28/28|2/2|100.00%|
|greenwave/school_accounts/mail.py|57/60|6/8|92.65%|
|greenwave/school_accounts/service.py|170/177|27/36|92.49%|
|greenwave/school_accounts/sessions.py|58/60|13/14|95.95%|
|greenwave/school_admin/__init__.py|0/0|0/0|100.00%|
|greenwave/school_admin/service.py|83/85|23/34|89.08%|
|greenwave/school_admin/validation.py|101/106|67/92|84.85%|
|greenwave/school_data/__init__.py|3/3|0/0|100.00%|
|greenwave/school_data/__main__.py|32/33|7/8|95.12%|
|greenwave/school_data/accounts.py|52/52|22/22|100.00%|
|greenwave/school_data/backup.py|71/74|9/12|93.02%|
|greenwave/school_data/configurations.py|38/38|10/16|88.89%|
|greenwave/school_data/database.py|59/62|8/8|95.71%|
|greenwave/school_data/errors.py|11/11|0/0|100.00%|
|greenwave/school_data/locking.py|33/37|5/8|84.44%|
|greenwave/school_data/migrations.py|110/111|43/44|98.71%|
|greenwave/school_data/observations.py|80/80|27/42|87.70%|
|greenwave/school_data/repositories.py|8/8|0/0|100.00%|
|greenwave/school_data/repository_base.py|51/51|14/16|97.01%|
|greenwave/school_data/security_records.py|94/94|16/22|94.83%|
|greenwave/school_data/storage.py|48/49|15/16|96.92%|
|greenwave/school_data/time_units.py|26/26|14/14|100.00%|
|greenwave/school_data/trips.py|133/133|45/62|91.28%|
|greenwave/school_data/validation.py|39/39|16/16|100.00%|
|greenwave/school_records/__init__.py|0/0|0/0|100.00%|
|greenwave/school_records/lists.py|62/62|33/38|95.00%|
|greenwave/school_records/paging.py|56/58|16/24|87.80%|
|greenwave/school_records/raw.py|54/56|27/44|81.00%|
|greenwave/school_records/recording.py|223/230|47/70|90.00%|
|greenwave/school_records/writes.py|114/115|24/38|90.20%|
|greenwave/school_resources/__init__.py|0/0|0/0|100.00%|
|greenwave/school_resources/api.py|88/88|56/62|96.00%|
|greenwave/school_resources/contexts.py|212/215|48/68|91.87%|
|greenwave/school_resources/files.py|154/161|48/72|86.70%|
|greenwave/school_resources/policy.py|63/64|23/28|93.48%|
|greenwave/school_resources/reads.py|91/125|34/62|66.84%|
|greenwave/telemetry.py|91/133|8/30|60.74%|

### Coverage JS

V8 `--experimental-test-coverage`, jawne include roles,state,api,dates,filters,validation.
25 testów, linie99.39%, gałęzie95.38%, funkcje98.55%. Nowe roles100/100/100.
UI DOM adapters laboratory/role_views/lists/details/auth oraz shell sprawdzono przez
E2E, ale nie włączono ich do tego pomiaru Node. Nie jest to coverage całego frontendu
ani zamiennik etapu10. Dokładna komenda i narzędzia w run.md, sekcja14.

| Moduł JS | Linie | Gałęzie | Funkcje |
|---|---:|---:|---:|
|roles.mjs|100.00%|100.00%|100.00%|
|state.mjs|100.00%|100.00%|100.00%|
|api.mjs|100.00%|92.45%|87.50%|
|dates.mjs|94.74%|96.43%|100.00%|
|filters.mjs|100.00%|88.89%|100.00%|
|validation.mjs|100.00%|87.50%|100.00%|

### Screenshoty i ocena wizualna

Rzeczywisty backend, nowa DB, wyłącznie syntetyczne dane, bez mailboxa/tokenu/hasła.
Obejrzano wszystkie8PNG. Spójne ciemne tło, limonkowy akcent, widoczny focus,
pionowe mobile filtry, kontrolowany scroll tabel. Test także320px. Długie nazwisko80,
email i powód do500znaków. Po przeglądzie poprawiono napis zgody shared, precyzję seek,
wyświetlanie metryk/jednostek, footer, czytelne nazwy zdarzeń audytu i rozwijany pełny
powód zamiast wysokich pustych wierszy. Screenshoty nie są makietami.

| Widok | Desktop | Telefon |
|---|---|---|
|Analyst shared + GPS/reports|[PNG](screenshots/stage8-desktop-analyst.png)|[PNG](screenshots/stage8-phone-analyst.png)|
|Admin accounts|[PNG](screenshots/stage8-desktop-admin.png)|[PNG](screenshots/stage8-phone-admin.png)|
|Configurations|[PNG](screenshots/stage8-desktop-configs.png)|[PNG](screenshots/stage8-phone-configs.png)|
|Safe admin audit|[PNG](screenshots/stage8-desktop-audit.png)|[PNG](screenshots/stage8-phone-audit.png)|


Pierwsze przebiegi wykryły błędne fixtures revision0, zły kształt verification,
przekroczenie reauth limitu w teście, niedozwolony zbyt krótki Idempotency-Key,
nieidempotentne usunięcie callbacku podczas restartu i wyścig replay Play/Pause/rate.
Poprawiono kod albo fixtures i powtórzono odpowiednie testy. Starsze oczekiwanie
404 dla nieistniejącego admin API zastąpiono401 anonim/403 DRIVER, ponieważ API już
istnieje; legacy/storage nadal404. Nie ukryto testu Tkinter.

## Ograniczenia i odbiór

Raporty używają istniejącego bounded API25 na widok (repo max100, offset do10000,
limit indeksu1000 raportów); nie zbudowano trwałej historii jobów lub raportowego
indeksu. Replay/jobs są pamięciowe, związane z sesją, credential, TTL i konkretną
zgodą. Regrant wymaga nowych kontekstów. Nie da się cofnąć już pobranych bajtów.
Przerwanie polling jest obserwowane najpóźniej przy następnym sprawdzeniu; nie ma
push/WebSocket. Nie wznawia się starych mutacji lub jazdy.

Etap9: pełna nawigacja, Android/live, kamera i integracja CV. Etap10: uzgodnione szerokie
backend/M8/CV coverage i JS. Etap11: Docker i drugi komputer. Etap12: raport końcowy.
Nie wykonano Linux/hardware/Docker w tym etapie; PUBLISH-01 nadal osobno.

Ręczny odbiór: run.md, sekcja14. Akceptacja użytkownika po przeglądzie, nie automatyczne
przejście do etapu9. Bez push/merge/rewrite i bez prywatnych danych w Git.


Commity implementacji: 781f8bc1a45c892ee4c5de55e14316255406f625,
0a738140000a78da401df99115d42f4fb989f568 oraz doprecyzowanie postępu replay f7df99da6cf4f8752d51d922101245e79aa6d372.
Dokumentacja/screenshoty w oddzielnym commicie, hash w odpowiedzi i przez
`git log -1 --format=%H -- docs/school-app/stage8.md`. Nie pushowano ani scalano.

Checklista akceptacji:
- [ ] DRIVER own/published; ANALYST own/shared/own draft; ADMIN konta/audit/config bez prywatnych przejazdów.
- [ ] Reauth i revision/powód; ostatni admin chroniony także współbieżnie.
- [ ] Block/role change unieważnia credentials; unblock ich nie odtwarza; recording kończone.
- [ ] Revoke/regrant nie ożywia replay/jobs, owner management zachowane; raport właściciela bez zmian.
- [ ] ROUTE/SIGNAL/MODEL walidowane; flags/read-only/published immutable/snapshot bez zmiany live gate.
- [ ] Testy/coverage/screenshoty i samodzielny odbiór sekcji14 run.md.
- [ ] Akceptacja użytkownika przed etapem9.


## Poprawka reauth z dialogu administracyjnego — 2026-10-14

Przegląd dotyczył **d9c281a186f657048bbba72ec749fea075c1033c**. HEAD zgodny,
status/staging puste; obowiązujący AGENTS pusty, dodatkowych instrukcji repo brak.
Wyłącznie frontend, wewnętrzna syntetyczna fixture i testy oraz dokumentacja.
Produkcyjny backend, CSRF, Origin, cookie/rotacja, reauth TTL, SQL i polityki niezmienione.

### Reproduktor przed / po

Nowa tymczasowa baza, realny HTTP i produkcyjny scrypt. Fixture ma wstrzyknięty zegar
integer UTC ms; operator steruje nim wyłącznie przez stdin. Po otwarciu dialogu
czas zwiększono o300001ms i PATCH zwrócił rzeczywiste403 REAUTH_REQUIRED.
Przed poprawką: przycisk tworzył formularz hasła w tle, `open modal=1`, password form=1;
regresyjna asercja `open modal=0` FAIL. Po: modal=0, password form=1, focus na haśle,
reauth dostępny z klawiatury; ten sam test PASS. Nie mockowano odpowiedzi403 i nie
czekano pięciu minut. Nie dodano publicznego endpointu zegara/provisioningu.

### Jednorazowy powrót

AdministrativeDraft w state.mjs przechowuje tylko userId, operation account/publish/archive,
resourceID, expected_revision/status i dozwolone pola formularza. Dla konta email jest
potrzebny do istniejącego dokładnego odczytu listy; wynik jest dodatkowo porównywany poID.
Pola konta: role/status/reason; konfiguracji: reason. Bez password/token/CSRF/cookie,
bez localStorage/sessionStorage. Snapshot powstaje dopiero przy kliknięciu przejścia do
reauth, obejmuje też zmiany wpisane po403; tylko w pamięci, nie w URL lub logach.

Accounts pobiera return tylko po udanym reauth z tym samym userID, przed state.set.
state.set nadal bez wyjątku abortuje requests, czyści wszystkie prywatne widoki,
uchwyty i globalny draft oraz zamyka dialogi. Jednorazowy lokalny snapshot tego samego
użytkownika jest następnie rewalidowany przez GET auth/me, odpowiedni zasób i aktualny
uprawniony widok. Epoch konta chroni także await. Zwykły login nie konsumuje ani nie
przywraca return. Brak zasobu/operacji/ADMIN lub401 nie otwiera formularza zapisu.

Przywrócony modal zawiera draft do przeglądu, nie wykonuje mutacji. Gdy revision/status
są inne, pokazuje aktualne DTO i wymaga przycisku Użyj aktualnej rewizji; submit przed
przyjęciem nie wysyła żądania. Nie zmienia revision po cichu. Account/PUBLISH zachowują
serwerowe expected_revision. ARCHIVE zgodnie z niezmienionym kontraktem API wysyła reason;
revision służy dodatkowej jawnej kontroli powrotu UI, nie nowej gwarancji CAS dla DELETE.

Escape, Zrezygnuj z powrotu, istniejący Powrót do konta, inna pozycja menu, logout,
401 i zmiana konta usuwają draft. Złe hasło daje401 i pełne czyszczenie, więc draft nie
wraca po późniejszym loginie. Escape w przywróconym modalu zwraca focus do users/configs;
Escape w formularzu reauth wraca do Konto. Nie wyłączono pełnego czyszczenia tożsamości.

### Wyniki wykonania

| Sprawdzenie | Wynik |
|---|---|
| Nowy browser `scripts/check_school_reauth.cjs` |PASS desktop1360×900 i phone390×844: real403, focus, drugi submit, account/publish/archive, revision/status gate, bad password401,3 cancel paths, utrata zasobu/roli, logout/login other, Escape/focus; brak błędów strony/storage/overflow|
| `tests/school_reauth.cjs` + roles + portal |29 PASS,177.239ms;4 nowe jednostkowe|
| Konta/hasła/SMTP `test_school_accounts*.py` |26 PASS,34.108s|
| `test_school_admin.py` |10 PASS,31.420s|
| `test_school_ui_static.py` |4 PASS,8.301s|
| Browser accounts |PASS desktop/phone, cały register/mail/verify/login/reauth/logout/reset/change/logout-all|
| Browser UI etapu7 |PASS desktop/phone/320px, formularze/konflikty/network/identity/focus|
| Browser roles etapu8 |PASS desktop/phone/320px, shared/replay/analysis/revoke/config/admin|

Browser zlicza PATCH, publish POST i archive DELETE: po reauth licznik jest bez zmian,
dopiero kolejny świadomy submit zwiększa go o1. W przypadku innej revision submit przed
przyjęciem również nie zwiększa licznika. Sprawdza dokładnie zapisany role/status/reason,
w tym reason zmieniony po403. Eventy i odpowiedzi kontrolują postęp; bez sleep.

V8 coverage sześciu dotychczasowych modułów logiki:99.46%linii,95.72%gałęzi,98.68%funkcji;
state.mjs (wraz z AdministrativeDraft)100/100/100. Pozostałe per-module: roles100/100/100,
api100/92.45/87.50,dates94.74/96.43/100,filters100/88.89/100,validation100/87.50/100.
DOM auth/role_views sprawdzono E2E, nie zaliczono do liczbowego pomiaru Node.
Nie powtarzano pełnej regresji383 ani backend coverage bez potrzeby: backend nie zmieniony;
powyżej właściwa regresja40Python i29JS oraz rzeczywista przeglądarka. Historyczne wyniki
pełnej regresji etapu8 pozostają we wcześniejszej sekcji. Własne wykonanie tylko Windows,
bez deklaracji Linux/Docker. Nie było blokady przeglądarkowej w tym wykonaniu.

Screenshoty zaakceptowanego etapu8 zachowano: podczas regresji GW_SCREENSHOT_ROOT wskazuje
ignorowany artifacts. Nie dodano DB/runtime/mailboxów/sekretów/prywatnych danych do Git.
Instrukcja odbioru: run.md,sekcja15. Etap8 Przygotowany do ponownego odbioru;
etap9 i pozostałe etapy Do zrobienia. Bez push/merge/rewrite.

Commit poprawki kodu/testów: **cc7637334da78d470e674bf2a62f11ecec00d10e**. Commit tej dokumentacji w odpowiedzi
i przez `git log -1 --format=%H -- docs/school-app/stage8.md`.
