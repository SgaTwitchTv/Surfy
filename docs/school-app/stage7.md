# Etap 7 — interfejs użytkownika, tabele i formularze

**Przygotowany do odbioru**, 2026-10-13. Etap 6 zaakceptowany przez użytkownika:
**eb6e61082e84ebf6b5797f02d634f4ec1df96f6e**. Na wejściu HEAD zgodny, status/staging
puste. Worktree: C:/Users/konra/.codex/worktrees/school-app/Surfy, codex/school-app.
Przeczytano obowiązujący pusty AGENTS, contract, stage4–6, stages, run i ai-usage.
Nie czytano data/runs ani starego runtime/school; testy, demo i screenshoty tylko
na nowych syntetycznych bazach. Main/vision-camera, solver, logger, migracje i
warunki rekomendacji live pozostają niezmienione. Nie odtwarzano starego prototypu.

## Działające widoki

- Wspólny ciemny shell z limonkowym akcentem, czytelnym menu własnych danych i konta.
- Moje przejazdy: semantyczna tabela title/created_at/route_version/mode/status/akcje.
- Moje obserwacje: globalna tabela własnych rekordów, efektywny kolor/typ/valid,
  źródło, czas otrzymania, historyczna adnotacja i informacja o korekcie.
- Szczegóły przejazdu: metadane, aktualny status zgody z API, akcje, obserwacje.
- Szczegóły obserwacji: oryginał, wartość efektywna, nieznany measured_at,
  stan zapisu i stronicowana historia before/after/autora/czasu/powodu.
- Konto oraz działające register, verify, login, reset, change-password, reauth,
  logout i logout-all w tej samej stylistyce.
- Minimalny syntetyczny zapis: create SIM → start → status → passenger observation
  → finish. Bez prawdziwego GPS, mapy, symulatora ruchu lub pewnych rekomendacji.

Wszystkie aktywne role mogą korzystać z własnych danych. Nie ma dodatkowych ekranów
analityka/admina ani globalnego dostępu do cudzych danych. Te widoki należą do 8.
Mapa, prędkościomierz, Android/live/kamera należą do 9. Nie pokazano ich przycisków
jako działających. ReactLY nie jest zależnością i nie kopiowano jego kodu.

## Moduły i bezpieczeństwo

Vanilla JS, ES modules, bez bundlera/frameworka/dependency w produkcyjnym UI.
`account.js` jest wejściem shell; `portal/` zawiera 12 mniejszych modułów:
api, state, dates, validation, filters, dom, auth, records, lists, forms, details,
navigation. Warstwy logiki, request lifecycle i widoków mają jawne granice.

Każdy plik jest osobno wpisany do STATIC. Nie ma serwowania katalogu, DB, sekretów,
runtime lub legacy /api/*. CSP pozostaje bez unsafe-inline; nie ma inline onclick,
eval, innerHTML ani HTML z użytkownika. Dane renderowane textContent/TextNode.
Nie używa się localStorage/sessionStorage do haseł, tokenów lub prywatnych danych.

401 unieważnia lokalną epokę konta, abortuje zależne fetch, zamyka dialogi,
czyści filtry/cursory/klucze/uchwyty oraz zatrzymuje polling, po czym pokazuje login.
Zmiana konta nie przywraca starej mutacji. Epoch sprawdzany jest także przed
interpretacją spóźnionego HEAD 401, aby stare konto nie wylogowało nowego.
Polling sprawdza epokę i generację widoku również po await, nie tylko przed nim.

## Formularze, filtry i konflikty

| Formularz | Pola i sprawdzenia |
|---|---|
| Nowy przejazd | title 1–120, note 0–1000, SIMULATION, opcjonalna opublikowana wersja ROUTE |
| Edycja | title/note, expected_revision z rekordu; konflikt pokazuje aktualny rekord i wymaga jawnej nowej revision |
| Archiwizacja | konkretny trip, reason 3–500, expected_revision; bez fizycznego delete; konflikt wymaga potwierdzenia aktualnej revision |
| Obserwacja pasażera/historyczna | signal_id 1–120, state, event_type; UNKNOWN nie STATE_START; source MANUAL na serwerze |
| Korekta | state/event_type/valid, reason, expected_revision, stabilny client_operation_id; oryginał i raw niezmienne |
| Share | dokładny email analityka, informacja o GPS/obserwacjach/historii/raportach, bez EXPORT/CV scopes |
| Revoke | expected_share_id z aktualnego API; stare okno nie cofa nowszej zgody |
| START/FINISH | stabilny Idempotency-Key przy identycznym retry, właściwy trip/context/revision |
| Konto | walidacja email/nazwy/Unicode hasła/confirmation, bez trim/normalizacji hasła |

Pola mają etykiety, powiązane komunikaty i aria-invalid/aria-describedby. Komunikaty
są aria-live. Submit jest blokowany w trakcie mutacji; formularz nie jest czyszczony
po walidacji/sieci. Dialog native modal wspiera Escape, focus i jego przywrócenie.
Statusy mają tekst; nie polegają wyłącznie na kolorze. Trasa/sygnalizator mogą być
identyfikatorami zgodnie z obecnymi DTO. Nie ma publicznej wyszukiwarki kont.

Filtry trips: dzień od/do, route_id, status, archived, sort. Observations: dzień,
trip_id (opcjonalny), route_id, signal_id, efektywne state/type/valid, source, sort.
Każde zapytanie ma scope=own i limit=25; next_cursor przechodzi na kolejną stronę,
zmiana filtrów/sortowania resetuje cursor. Nie pobiera się całej historii do filtrowania.
Zmiana pola podczas GET abortuje stare żądanie; serial ignoruje także odpowiedź,
która dotarłaby pomimo abortu. Loading/empty/error/retry/end mają osobne stany.

Dni oznaczają **Europe/Warsaw**, nie strefę przeglądarki. Intl/IANA wyznacza UTC
RFC3339: początek wybranego dnia, koniec jako początek następnego. Bez +01/+02
w kodzie. DST: 23 i 25 godzin. W UI wyraźnie wskazano strefę i znaczenie czasu
otrzymania, measured_at NULL pokazuje Nieznany. Zakres maksymalnie 366 dni.

Błąd sieci/timeout nie dowodzi braku commit. Klucze zachowują się w pamięci dla
retry tej samej operacji, zmiana payload tworzy nową świadomą operację. FAILED
journaling oznacza trwały fakt DB, nie fałszywy sukces raw. START nie jest wznawiany
po INTERRUPTED/utracie uchwytu; należy utworzyć nowy PLANNED trip. Znany FINISH409
po zmianie metadanych wymaga odczytu stanu i jawnego potwierdzenia nowej rewizji.
Po pełnym reload znikają pamięciowe uchwyty; backend nie dostarcza endpointu
odtwarzania aktualnego navigation. Wylogowanie kończy jego zapis po stronie serwera.

## Jedyna korekta API: HEAD eksportu

Wstępny GET anulowanego ZIP kolidował z właściwym natywnym pobraniem (E2E: canceled).
Zamiast zmieniać kontrakt zapisów dodano **HEAD /school/api/v1/trips/{id}/export**
na tej samej ścieżce co GET. Tylko ten HEAD jest dostępny; inne pozostają 404.

HEAD sprawdza aktualną sesję, właściciela, COMPLETE/nonarchive, containment i
integralność tak jak GET, przez Files.run. Nie tworzy ZIP ani Transfer, nie wysyła
body. Błąd ma status i bezpieczny enum X-School-Error, bez SQL/ścieżek/sekretów.
200 ma application/zip, bez nieprawdziwej długości przyszłego ZIP. GET i jego
uprawnienia są niezmienione; razem 31 kombinacji metoda/ścieżka zasobów.

Frontend HEAD obsługuje odmowę, expiry i integrity; następnie przeglądarka pobiera
GET z autoryzowanym cookie. Nie buduje wielkiego Blob. GET ponownie sprawdza prawa;
HEAD nie jest gwarancją dostępu później, nie cofamy pobranych już bajtów. Przy
zmianie uprawnień między HEAD/GET natywne pobranie może zostać przerwane przez serwer.
Test HTTP obejmuje anon401, owner200, other/analyst shared/admin foreign404,
logout401, Host403, corrupted raw409, brak body i brak wywołania generatora ZIP.

## Wykonane sprawdzenia

Własne środowisko: Windows, Python 3.14.4, Node 24, Playwright + headless Edge.
Browser fixture używa produkcyjnego scrypt N131072 i nowej TemporaryDirectory
SQLite/SMTP. Dodatkowe seeds mają tylko example.test i syntetyczne pliki.
Nie dodano publicznego test/provisioning HTTP.

| Sprawdzenie | Wynik |
|---|---|
| Node istotna logika nowego UI | 16/16 PASS, 199.9334 ms |
| HTTP allowlist/HEAD/security | 4/4 PASS, 7.708 s |
| Backend kont | 26/26 PASS, 35.663 s |
| Backend zasobów | 17/17 PASS, 54.061 s |
| Istniejące Node driver/CV UI | 7/7 PASS, mobile_flow PASS |
| Browser kont, SMTP, verify/reset/change/reauth/logout-all | desktop i phone PASS |
| Browser macierzy zasobów | desktop i phone PASS |
| Nowy pełny browser UI | 1360×900, 390×844, 320×844 PASS |

Nowy E2E: login, obie tabele, create, start/observe/finish, edycja, korekta/historia,
filtry, następna strona, share/revoke/regrant/stare okno, rzeczywisty ZIP (PK), archive,
server logout bez zmiany DOM → 401 → login drugiego konta bez przecieku. Dodatkowo
puste/błędne pola, UNKNOWN+START, XSS jako tekst, maksymalne 120/1000/120 znaków,
spóźniony filtr, keyboard Tab/Shift+Tab/Escape, focus restoration, scroll tabeli,
response loss po realnym commit START/FINISH/PATCH, stabilne klucze i znany FINISH409
wymagający świadomego nowego revision. Wyścigi sterowane bramkami Promise/Event,
bez sleep jako podstawy poprawności. Browser timezone America/New_York, UI Warsaw.

Nie powtarzano pełnej kosztownej regresji M8/SQLite po każdej zmianie CSS. Zmiany
backendu są ograniczone do static allowlist/MIME/HEAD; wykonano właściwe 47 testów
HTTP/kont/zasobów oraz browser regresję. Solver/logger/migracje nie zmieniły się.
Nie deklarujemy aktualnego wykonania pełnych 369 testów z etapu 6. Brak blokady
przeglądarki; Linux, Docker, telefon, Tkinter i YOLO nie były tym odbiorem.

## Pomiar Node/V8

Polecenie w run.md sekcja 13: --experimental-test-coverage i jawne include dla
CAŁYCH api/state/dates/filters/validation.mjs, bez ignorowania trudnych branchy.
Zakres to logika API/expiry/races, sesji, stable keys, walidacji, filtrów/keyset i
IANA dat. DOM/auth/views/forms/navigation są adapterami browser-only sprawdzanymi
E2E, nie są zaliczane do tego mianownika. To **nie pokrycie całego frontendu**
i nie końcowy szeroki pomiar JS/M8/CV z etapu 10. E2E nie jest pomiarem coverage.

| Moduł | Linie | Gałęzie | Funkcje |
|---|---|---|---|
| api.mjs | 100.00% | 94.12% | 87.50% |
| dates.mjs | 94.74% | 96.43% | 100.00% |
| filters.mjs | 100.00% | 90.91% | 100.00% |
| state.mjs | 100.00% | 100.00% | 100.00% |
| validation.mjs | 100.00% | 87.50% | 100.00% |
| Łącznie | **99.22%** | **93.24%** | **98.11%** |

Node/V8 raportuje te metryki, nie mieszamy ich z Python combined. Lokalny raport
artifacts/stage7-js.log, browser artifacts/stage7-browser*.json/log; nie w Git.

## Ocena wizualna i screenshoty

Oglądano rzeczywiste PNG poprzez view_image, nie generowano makiet. Po oględzinach
poprawiono nagłówek telefonu, zwijane filtry, wskazówkę poziomego scroll i łamanie
przycisków tabel. Nagłówki, limonkowy wybór menu, pola, spacing i kontrast spójne;
telefon ma pionowe formularze, dotykowe 44px przyciski, tabele tylko w lokalnym scroll.
Długie dane łamią się bez page overflow. Widoczny focus sprawdzony też klawiaturą.
Nie jest to pełny audyt WCAG lub odbiór sprzętowego smartfona.

Wszystkie screenshoty mają wyłącznie syntetyczne dane, bez mailboxa, haseł, linków,
tokenów i prywatnych nagrań. Konto/table/trip/corrections pochodzą z realnego backendu:

| Widok | Desktop | Telefon |
|---|---|---|
| Konto | [PNG](screenshots/desktop-account.png) | [PNG](screenshots/phone-account.png) |
| Przejazdy | [PNG](screenshots/desktop-trips.png) | [PNG](screenshots/phone-trips.png) |
| Szczegóły | [PNG](screenshots/desktop-trip.png) | [PNG](screenshots/phone-trip.png) |
| Obserwacje | [PNG](screenshots/desktop-observations.png) | [PNG](screenshots/phone-observations.png) |
| Korekty | [PNG](screenshots/desktop-corrections.png) | [PNG](screenshots/phone-corrections.png) |

## Ograniczenia i odbiór

Historia korekt zachowuje starsze API offset z limitem 10000 i pokazuje ten limit;
nie jest to ograniczenie dwóch głównych list next_cursor. Lista wersji trasy przy
create pokazuje pierwsze 100 opublikowanych konfiguracji, jawnie opisana. Wyszukiwanie
konkretnej obserwacji czyta ograniczone strony do znalezienia ID, nie trzyma całości
w pamięci ani nie filtruje całej historii klientem. Autor korekty to ID z bezpiecznego
DTO, nie dodano publicznego lookup kont. Teksty odpowiadają walidacji serwera
(bez skrajnych spacji/znaków sterujących); hasła nigdy nie są normalizowane.

Etap 8: dodatkowe widoki ANALYST/ADMIN. Etap 9: pełna nawigacja/prędkościomierz,
telefon/live/kamera i pełny responsive odbiór jazdy. Nie ma gwarancji DB–filesystem
transaction ani auto-resume, nadal obowiązują granice etapu 6/PUBLISH-01.

- [ ] Nowy root i syntetyczne konta według run.md, sekcja 13.
- [ ] UI login → trip → start → observation → finish → edit/correction → share/revoke → archive.
- [ ] Filtry, cursor, DST, konflikt rewizji i błąd sieci bez automatycznego nowego zapisu.
- [ ] Logout/login drugiego konta, brak starego stanu.
- [ ] Screenshoty oraz wyniki Node/V8/HTTP/browser i code review.
- [ ] Akceptacja etapu 7; dopiero kolejny prompt może rozpocząć 8.

Commity kodu:
8ce6d513a2fbae420b51aead71b9b44231741c9b,
d8e4e25599f8081a7a08e5bb105cfdc873d591e6,
75e25b48c7b94641c573763a161c56e0f2ccbe88,
a18fef0cbd8344b20b9bf40014dfe0e50d4088eb.
Hash dokumentacji: `git log -1 --diff-filter=A --format=%H -- docs/school-app/stage7.md`.
Bez push/merge/rewrite. STOP przed 8.


Końcowy E2E i 10 screenshotów ponowiono na dokładnym commicie kodu
**a18fef0cbd8344b20b9bf40014dfe0e50d4088eb**: wszystkie trzy rozmiary PASS.
Sprawdzono UTF-8, code fences, względne linki, PNG dimensions i 43 bloki PowerShell
w run.md; PASS. CLI serve --help potwierdza root/host/port. Node v24.18.0,
Python 3.14.4. Main/vision-camera niezmienione; diff logger/migracji/solver/GATE pusty.
Staging wyłącznie wskazanych dokumentów i 10 syntetycznych PNG, bez runtime,
DB/mailboxów/sekretów/środowisk/lokalnych raportów. Git diff --cached --check PASS.
