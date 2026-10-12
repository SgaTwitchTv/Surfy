# Prompty i wykorzystanie AI — GreenWave School

## Zasady

AI: Codex w aplikacji desktopowej. Zakres, decyzje, zmiany i testy zapisujemy
po każdym etapie. Wyniki testów muszą pochodzić z wykonania, nie z opisu plików.
Nie zapisujemy tu tokenów, haseł prywatnych kont ani treści prywatnych nagrań.

Wcześniej w tym samym czacie użytkownik zlecił całe rozszerzenie, po czym
skorygował tryb pracy: kolejne prompty i akceptacja po każdym etapie, bez nowych
commitów bez polecenia. Zastane commity faa8ca9/f0aff93/6a33be2 oraz późniejsze
zmiany pozostają zachowane jako niezaakceptowany prototyp. Nie są rezultatem
obecnego etapu 1. Starszy zapis: ../ai-usage.md i historia tego czatu.

Uzgodniono 12 etapów zgodnie ze stages.md. Kierunek UI jest inspirowany ReactLY:
ciemny, limonka, mocna typografia. Lokalny DESIGN_SYSTEM.md ReactLY przeczytano
w poprzedniej turze; nie zmieniano tamtego projektu ani UI GreenWave w etapie 1.

## Prompt etapu 1 (2026-10-12)

Poniżej treść otrzymanego polecenia. Zachowano zakres i sformułowania;
znaki formatowania końca linii z interfejsu rozmowy pominięto.

```text
Dobra to lecimy: ETAP 1 — audyt i przygotowanie szkolnego rozszerzenia GreenWave.

Pracujesz lokalnie w repozytorium:
C:\Users\konra\source\repos\SgaTwitchTv\Surfy

Całość będziemy realizować etapami w tym samym wątku. W tym kroku wykonaj tylko audyt i przygotowanie gałęzi. Po przedstawieniu wyników zatrzymaj się i poczekaj na następny prompt.

Zasady:

- Przeczytaj obowiązujące AGENTS.md.
- Sprawdź status repozytorium, istniejące worktree oraz gałęzie. Nie usuwaj ani nie nadpisuj zmian użytkownika.
- Zweryfikuj, że commit 7ece859 istnieje i należy do historii codex/vision-camera. Jeśli baza jest inna niż podana, przedstaw rozbieżność zamiast wybierać inną po cichu.
- Utwórz osobny worktree na gałęzi codex/school-app od dokładnego commita 7ece859. Jeśli taka gałąź lub worktree już istnieje, sprawdź ich stan i nie resetuj ich.
- Nie zmieniaj main ani codex/vision-camera.
- Nie czytaj zawartości prywatnych nagrań w data/runs/, nie modyfikuj ich i nie dodawaj ich do Gita. Do sprawdzeń używaj danych syntetycznych w osobnym katalogu.
- Nie odblokowuj rekomendacji live. Konta użytkowników ani wyniki YOLO nie zastępują zweryfikowanych danych o światłach.

Cel szkolnego rozszerzenia:
GreenWave ma otrzymać prawdziwe konta, role kierowca/analityk/administrator, chronione dane użytkowników, dwie filtrowalne tabele, możliwość zapisu i modyfikacji rekordów, responsywny interfejs, testy z minimum 70% pokrycia, Docker, dokumentację użycia AI i krótki raport. Zachowujemy istniejący GPS Android, symulację, replay i eksperymentalne CV.

Wykonaj:

1. Przeczytaj README.md oraz kod i dokumenty dotyczące M8, nawigacji, danych SQLite, GPS, UI i CV. Nie traktuj opisu w tym prompcie jako dowodu istniejącej funkcjonalności.
2. Ustal aktualną architekturę, zależności, sposób uruchomienia, przechowywanie danych, mechanizm parowania telefonu i zabezpieczenia API.
3. Przygotuj macierz wszystkich 16 wymagań szkolnych:
   - problem domenowy;
   - konta, logowanie i reset hasła;
   - trzy role;
   - ochrona zasobów i własność danych;
   - dwie filtrowalne tabele dostępne kierowcy;
   - estetyka UI;
   - responsywność;
   - walidacja formularzy;
   - zapis i modyfikacja rekordów;
   - AJAX/fetch;
   - dobre praktyki i architektura;
   - historia Git;
   - ujawnienie promptów i pomocy AI;
   - wdrożenie Docker na innym komputerze lub hosting;
   - testy jednostkowe, integracyjne i automatyczne z minimum 70% pokrycia;
   - raport ze screenshotami oraz komplet źródeł i instrukcji.
     Dla każdego wymagania podaj stan: istnieje/częściowo/brak/niezweryfikowane, dowód w kodzie, brakującą pracę i sposób odbioru.
4. Uruchom istniejące testy odpowiednie dla dostępnego środowiska. Zapisz dokładne polecenia, wyniki, pominięcia i blokady. Oddziel błędy kodu od brakujących zależności lub ograniczeń środowiska.
5. Zaproponuj jawny zakres pomiaru pokrycia, obejmujący backend szkolnego rozszerzenia oraz istotną logikę istniejącej aplikacji, którą rozszerzenie wykorzystuje. Uzasadnij każde wyłączenie. Nie deklaruj osiągnięcia 70% bez pomiaru.
6. Zapisz audyt w docs/school-app/audit.md i rozpocznij docs/school-app/ai-usage.md, ujawniając ten prompt, wykonane działania AI oraz sposób ich weryfikacji.
7. Zrób jeden commit z dokumentacją audytu, dodając do stagingu wyłącznie konkretne pliki tego etapu.

Nie implementuj jeszcze kont, migracji ani zmian UI.

Na końcu podaj:

- ścieżkę worktree, nazwę gałęzi i pełny hash bazy;
- macierz wymagań;
- wyniki testów bazowych;
- najważniejsze ryzyka i zależności;
- propozycję kolejności dalszej implementacji;
- hash commita audytu i końcowy git status.

Nie deklaruj funkcjonalności jako sprawdzonej wyłącznie dlatego, że istnieje plik lub opis w README. Poza tym co jeszcze gadaliśmy przed chwilą, pamiętaj żeby Dla każdego etapu zapisać: status, hash commita, dowody
sprawdzenia i blokady. Etap 1 oznacz jako zweryfikowany
tylko po wykonaniu audytu; pozostałe jako „Do zrobienia”.
Uwzględnij ten plik w commicie dokumentacji audytu. Jazda z kurwom
```

## Działania AI i dowody etapu 1

1. Odczyt AGENTS i instrukcji. Pusty nadrzędny AGENTS nie zawiera dodatkowych
   reguł. Sprawdzenie status/worktree/branches i ancestry bazy przez Git.
2. Reuse istniejącego worktree; bez resetu, przełączania main/CV ani usuwania
   wcześniejszego prototypu. Nie czytano prywatnego data/runs.
3. Odczyt dokumentacji i kodu, macierz wymagań. Wykryto stare opisy M8/UI/CV,
   publiczne odczyty API bazy, brak kont w parowaniu oraz potrzebę pełnej
   izolacji GPS/CV/replay/export. Nie implementowano poprawek.
4. Eksport śledzonej bazy 7ece859 przez git archive do artifacts/school-audit-20261012.
   Testy Python/Node/Playwright/Android i capture na syntetycznych danych.
5. Pomiar coverage.py 7.13.1 szerokiego zakresu bazy, nie zastaną wąską konfiguracją.
   Wynik: 3359/3748 linii, 1180/1530 gałęzi, 85.9985% łącznie. Wyłączenia
   i wyniki słabszych modułów ujawnione w audit.md. Nie jest to wynik końcowy
   szkolnego rozszerzenia.
6. Zapis wyłącznie trzech dokumentów docs/school-app: audit, ai-usage, stages.
   Rejestr oznacza etap 1 jako zweryfikowany przez wykonane sprawdzenia,
   z oczekiwaniem na akceptację. Etapy 2–12 są Do zrobienia.
7. Staging konkretnych dokumentów; sprawdzenie staged diff i pojedynczy commit.
   Hash jest w końcowej odpowiedzi; trwały odczyt wskazany w stages.md.

Weryfikacja: 226 testów Python; 7 Node i mobile_flow; oba bazowe scenariusze
browser PASS (brak pageerror/external requests), 4 JUnit Android + debug APK;
syntetyczny decoder/capture smoke PASS. Szczegóły/polecenia/logi/pominięcia
w audit.md. Nie ma odbioru YOLO, telefonu, kamery, drogi ani Dockera/drugiego hosta.

Rutynowe poprawki podczas audytu dotyczyły tylko komend: rg na Windows wymaga
-g dla globów zamiast wildcardu w ścieżce; skorygowano także odczyt ścieżki logu
Androida. Nie były to błędy aplikacji i nie powodowały edycji jej kodu.

Ograniczenie AI: testy syntetyczne nie dowodzą skuteczności drogowej, autentyczności
faz ani bezpieczeństwa rekomendacji. Estetykę i kolejne kontrakty zatwierdza
użytkownik. Po tym commicie AI zatrzymuje pracę do kolejnego promptu.

## Prompt etapu 2 (2026-10-12)

Poniżej otrzymana treść (formatowanie list/koniec linii ujednolicone).

```text
ETAP 2 — kontrakt aplikacji, kont, uprawnień i danych.

Etap 1 zaakceptowany po przeglądzie dokumentacji na GitHubie. Kontynuuj w istniejącym worktree na codex/school-app. Nie zmieniaj main ani codex/vision-camera, nie resetuj gałęzi i nie twórz nowego worktree.

Przeczytaj obowiązujące AGENTS.md oraz:
* docs/school-app/audit.md;
* docs/school-app/stages.md;
* docs/school-app/ai-usage.md;
* aktualny kod szkolnego prototypu, jego testy i integrację z GreenWave.

Historia zawiera wcześniejszy prototyp kont i UI oraz commit a9f7259 po audycie. Traktuj ten kod jako materiał do przeglądu, nie jako zaakceptowaną realizację kolejnych etapów. Sprawdź aktualny HEAD i git status; zachowaj niezwiązane zmiany.

CEL ETAPU
Przygotuj jednoznaczny, implementowalny kontrakt szkolnego rozszerzenia. W tym etapie zmieniaj wyłącznie dokumentację. Nie implementuj jeszcze migracji, kont, API ani UI.

1. GRANICE APLIKACJI
Opisz:
* problem domenowy i główne scenariusze kierowcy;
* podział na Nawigację, Moje przejazdy, Moje obserwacje, Laboratorium i Administrację;
* granice demonstracji syntetycznej oraz działania z prawdziwym telefonem;
* zachowanie istniejącej symulacji, GPS, replay i diagnostycznego CV.
Konta, role i CV nie zmieniają warunków dopuszczenia rekomendacji live. Przy niewiarygodnych lub niepełnych danych nie pokazujemy pewnego zakresu prędkości ani poleceń „Przyspiesz/Zwolnij”.

2. KONTA I SESJE
Zaprojektuj:
* rejestrację tworzącą wyłącznie konto kierowcy;
* bezpieczne utworzenie pierwszego administratora bez publicznych domyślnych haseł;
* login, logout, zmianę hasła i blokadę konta;
* normalizację i unikalność adresu email;
* hashowanie haseł, limity prób logowania i ochronę przed ujawnianiem istnienia kont;
* sesje: przechowywanie, wygasanie, rotację, cookie, CSRF i unieważnienie po zmianie hasła lub blokadzie;
* zachowanie aktywnych sesji po zmianie roli.
Reset hasła ma korzystać z losowego, jednorazowego, wygasającego tokenu przechowywanego w postaci hasha. Zaproponuj dostarczanie przez SMTP; w Docker demo lokalny odbiornik poczty z danymi syntetycznymi. Link ani token nie mogą być zwracane anonimowemu klientowi przez publiczne API. Opisz oddzielnie konfigurację demo i wdrożenia z prawdziwymi danymi.

3. MACIERZ UPRAWNIEŃ
Przygotuj tabelę: zasób/akcja × anonimowy/kierowca/analityk/administrator.
Przyjmij jako propozycję do naszego przeglądu:
* kierowca: własne przejazdy, obserwacje, eksporty, urządzenia i związane z nimi zasoby;
* analityk: wspólne konfiguracje tras i sygnałów oraz analiza przejazdów jawnie udostępnionych mu przez kierowcę;
* administrator: zarządzanie kontami, rolami i konfiguracją; dostęp do prywatnych danych tylko w ramach jawnie opisanej i audytowanej operacji administracyjnej.
Jeżeli ten model wymaga dużej dodatkowej funkcjonalności, przedstaw prostszy wariant z uzasadnieniem. Nie zastępuj go po cichu globalnym dostępem do wszystkich danych.
Uwzględnij odczyt, zapis, korektę, usunięcie, eksport, replay, zadania analizy, media CV, konfigurację i parowanie telefonu. Ukrycie przycisku w UI nie jest zabezpieczeniem.

4. MODEL DANYCH I MIGRACJE
Zaproponuj tabele, relacje, klucze, indeksy i ograniczenia dla:
* kont, sesji i tokenów resetu;
* urządzeń i parowania;
* przejazdów oraz własności danych;
* oryginalnych obserwacji i osobnych korekt;
* audytu istotnych operacji;
* udostępniania danych, jeśli pozostaje w proponowanym modelu.
Opisz powiązania z istniejącą historią SQLite, plikami GPS, replay i CV. Ustal źródło prawdy, granice transakcji oraz zachowanie po awarii lub restarcie.
Surowe logi GPS i oryginalne zdarzenia pozostają niezmienne. Korekta zawiera autora, czas serwera, powód i zmianę wartości. Określ, które metadane przejazdu można edytować.
Stare dane bez właściciela nie mogą automatycznie stać się dostępne nowym użytkownikom. Zaprojektuj kontrolowane przypisanie lub import bez modyfikacji surowych plików. Nie czytaj prywatnych data/runs/.
Opisz wersjonowanie migracji, kopię bezpieczeństwa i odzyskanie po nieudanej migracji.

5. IZOLACJA UŻYTKOWNIKÓW I TELEFONÓW
Rozstrzygnij, jak odseparować współdzielony stan obecnego LocalServer:
* symulację, nagrywanie, replay i analizę;
* tokeny telefonu, użytkownika i sesji przejazdu;
* katalogi runtime, indeksy i media CV.
Telefon nie może wybierać właściciela przez dowolne owner_id. Określ skutki wylogowania, blokady konta, cofnięcia parowania i ponownego uruchomienia serwera.
Jeśli demo dopuszcza tylko jedną aktywną sesję nawigacji lub nagrywania, opisz blokadę i komunikat dla drugiego użytkownika. Nie ukrywaj ograniczenia.

6. KONTRAKT API I FORMULARZY
Dla każdego endpointu szkolnego podaj:
* metodę i ścieżkę;
* wymagane konto, rolę i własność;
* pola żądania i odpowiedzi;
* walidację, limity i kody błędów;
* ochronę CSRF dla operacji zmieniających dane.
Przejrzyj także odziedziczone endpointy GreenWave. Wskaż, które zostają chronione, zastąpione lub niedostępne w portalu. Uwzględnij pliki, eksporty, media, zadania i diagnostykę.
Dwie tabele kierowcy:
* przejazdy: filtry daty, trasy i stanu;
* obserwacje: filtry daty, trasy/sygnalizatora, koloru i rodzaju zdarzenia.
Ustal paginację, sortowanie i limity. Przygotuj listę formularzy z walidacją po stronie klienta i serwera oraz zachowaniem przy błędzie i wygaśnięciu sesji.

7. PRZEGLĄD PROTOTYPU I ODBIÓR
Dla school.py, school_store.py, school.js i powiązanych testów wskaż:
* co zachować;
* co zmienić;
* czego brakuje;
* jakie testy potwierdzą zgodność z kontraktem.
Nie uznawaj deklaracji w dokumentacji za dowód działania. Jeśli przeprowadzasz testy lub małe eksperymenty diagnostyczne, używaj danych syntetycznych i zapisz faktyczne wyniki.
Potwierdź zakres coverage z audytu: nowy backend oraz używany rdzeń, jawne wyłączenia i osobny pomiar istotnej logiki JS. Wąska konfiguracja obejmująca tylko dwa szkolne moduły nie spełnia końcowego odbioru.
Przygotuj scenariusze akceptacyjne dla etapów 3–9, w tym odmowę dostępu anonimowego i do cudzych ID, trwałość danych, reset hasła oraz niezmienność logów.

DOKUMENTACJA I COMMIT
* Zapisz kontrakt w docs/school-app/contract.md.
* Aktualizuj stages.md; nazwij etap 2 „Kontrakt aplikacji”.
* Uzupełnij ai-usage.md o ten prompt, działania i sposób weryfikacji.
* Wpisz literalny hash audytu bb99de3d808db8898426b42203e6c5e979e527be do rejestru.
* Zrób jeden commit dokumentacji, dodając wyłącznie konkretne pliki tego etapu.
* Nie pushuj i nie scalaj automatycznie.

NA KOŃCU PODAJ
1. Krótkie podsumowanie kontraktu.
2. Macierz ról.
3. Model własności i izolacji danych.
4. Proponowany przepływ resetu hasła.
5. Braki wcześniejszego prototypu.
6. Istotne decyzje produktowe wymagające naszego przeglądu.
7. Dowody sprawdzenia dokumentacji i wyniki wykonanych testów.
8. Hash commita i końcowy git status.
Zatrzymaj się po etapie 2. Nie rozpoczynaj implementacji etapu 3.
```

## Działania AI i weryfikacja etapu 2

- Sprawdzono HEAD a9f7259 i status; prototyp jest w historii, lecz lokalnie
  usunięty zgodnie z późniejszym poleceniem użytkownika. Przeczytano go przez
  git show, nie odtworzono. Stare ../ai-usage.md jest obecnie także usunięte
  w worktree; zapis jego treści pozostaje w historii Git.
- Odczytano wymagane dokumenty, pusty nadrzędny AGENTS i kod integracji M8/CV/
  Android. Nie odczytano prywatnego data/runs ani zawartości runtime/.
- Zaproponowano kontrakt z sharing scopes i audytowanym B zamiast globalnego
  read analityka/admina; email verification/SMTP/preauth/sesje, isolated roots,
  lease jednej jazdy, recovery, migracje, API i formularze.
- Mały eksperyment historycznego SchoolStore: compile/exec w pamięci,
  TemporaryDirectory, syntetyczne konta example.test. Wynik faktyczny:
  analyst_reads_unshared_trip=true, admin_reads_private_trip_without_access_operation=true,
  device_token_survives_browser_logout=true, database_user_version=2.
  To potwierdzone braki prototypu, nie testy zaakceptowanego nowego backendu.
- Przegląd spójności doprecyzował CSRF HMAC odtwarzany z cookie, delivery_state
  hash-only resetów, verified_email_at, media_assets i uprawnienia pochodne jobów.
- Kontrola struktur dokumentu w Pythonie: 74 unikalne metody/ścieżki, 74 ID,
  7 kolumn każdej tabeli endpointów, 45 mutacji z jawnym C/P/D, komplet rozdziałów
  API, D1–D7 i scenariuszy etapów3–9. Wynik PASS. Nie jest to test runtime API.
- Kod roboczy nadal zgodny z 7ece859; SHA256 git diff poza docs/school-app
  przed i po wynosi 80674326e7b927a660e3caecf9d95ba1c7558edc849659da81af0a6c751745e3.
  Zachowano wcześniej istniejące usunięcia/modyfikacje i runtime/.
- Nie zmieniano kodu, migracji, API/UI ani DB aplikacji; nie uruchamiano ponownie
  pełnych testów M8 przy samych dokumentach. Bazowe wyniki/coverage nadal są
  wyłącznie dowodami etapu1. Nie instalowano poczty/Dockera/pakietów, nie użyto
  telefonu/kamery ani nie wdrożono nowego modelu ról.
- Jeden commit: wyłącznie contract.md, stages.md, ai-usage.md; hash końcowy
  w odpowiedzi i resolverze rejestru. Etap2 to propozycja dokumentacyjna do
  akceptacji. Dalsza implementacja zatrzymana do kolejnego promptu.

Techniczna przeszkoda przy zapisie: Windows odrzucił zbyt długą pojedynczą
komendę (os error206). Podzielono zapis dokumentu na krótsze komendy; to nie
błąd kodu aplikacji i nie zmieniło zakresu etapu. Kontrola tabel/diff wykonana
po zakończeniu zapisu i doprecyzowaniu spójności.

## Prompt końcowego doprecyzowania etapu 2 (2026-10-12)

Treść otrzymanego promptu, z ujednoliconym formatowaniem list i końców linii:

```text
Teraz dokończmy i sprecyzujmy etap 2 — poprawki, doprecyzowanie zakresu i końcowy odbiór kontraktu.
Kontynuuj w istniejącym worktree na codex/school-app. Nie zaczynaj etapu 3. Nie zmieniaj main ani codex/vision-camera. Przeczytaj obowiązujące AGENTS.md, dokumenty docs/school-app oraz aktualny stan Git.

Kontekst przeglądu:
* 3ff54d9d3c4a7dfb23b53db9095f69f1112427f0 zawiera dokumentację kontraktu.
* Późniejszy commit 3476d133006a948887899e8b75dcc210ce084248 usunął wcześniejszy prototyp i część reguł .gitignore oraz dodał runtime/school/school.sqlite3 i pliki nagrań.
* Usunięcie prototypu było moją decyzją. Nie odtwarzaj go automatycznie.
* Zawartość runtime nie jest materiałem do audytu. Nie czytaj bazy, logów, mediów ani prywatnych data/runs/.
* Kontrakt jest dobrym punktem wyjścia, ale wymaga ograniczenia zakresu i usunięcia niezatwierdzonych propozycji.
W tym etapie wolno zmieniać dokumentację, .gitignore i śledzenie wskazanych plików runtime. Nie implementuj backendu, migracji, formularzy ani UI.

A. UPORZĄDKUJ GIT BEZ UTRATY LOKALNYCH DANYCH
1. Sprawdź HEAD, status, staging i listę śledzonych ścieżek. Nie nadpisuj niezwiązanych zmian.
2. Przywróć reguły ignorowania odpowiednie dla projektu:
/runtime/
/artifacts/
.coverage
.coverage.*
/htmlcov/
/.venv-school/
oraz inne rzeczywiście używane katalogi środowiska i raportów.
Zachowaj wszystkie pozostałe istniejące reguły.
3. Usuń runtime/ wyłącznie ze śledzenia Git, zachowując lokalne pliki.
Użyj operacji równoważnej git rm -r --cached -- runtime.
Nie wykonuj usunięcia z dysku, git clean ani reset --hard.
4. Sprawdź pozostałe śledzone ścieżki pod kątem przypadkowego dodania DB, WAL/SHM, nagrań, środowisk i raportów. Korzystaj z nazw i metadanych Git; nie otwieraj danych użytkownika.
5. Wykaż, że wskazane ścieżki runtime pozostają lokalnie, a nie będą obecne w drzewie nowego commita. Sprawdź reguły przez git check-ignore --no-index na konkretnych ścieżkach.
6. Zapisz w dokumentacji, że poprzedni publiczny commit nadal zawiera te pliki. Nie twierdź, że nowy commit usuwa je z historii.
7. Nie przepisuj opublikowanej historii i nie wykonuj force push. Bez czytania danych nie zakładaj, że są syntetyczne. Jeśli kwestia ich wcześniejszej publikacji pozostaje nierozstrzygnięta, zapisz ją jako osobny otwarty problem wraz z opcjami dalszego działania, bez ujawniania zawartości.

B. ZATWIERDZONY ZAKRES PIERWSZEJ WERSJI
Poniższe decyzje zastępują propozycje D1–D7. Zaktualizuj kontrakt, macierz ról, model danych, API, formularze i scenariusze odbioru tak, aby wszystkie były z nimi zgodne.

1. Role
* DRIVER, ANALYST, ADMIN.
* Rejestracja tworzy wyłącznie DRIVER.
* Wszystkie role mogą mieć własne przejazdy i obserwacje.
* DRIVER ma dostęp wyłącznie do własnych danych.
* ANALYST może analizować własne oraz jawnie udostępnione mu ukończone przejazdy. Może tworzyć robocze wersje wspólnych konfiguracji.
* ADMIN zarządza kontami, rolami oraz publikowaniem konfiguracji.
* ADMIN nie otrzymuje automatycznego dostępu do cudzych GPS, filmów ani przejazdów.

2. Proste udostępnianie
* Właściciel udostępnia jeden ukończony przejazd jednemu aktywnemu analitykowi przez dokładny email.
* Jedno uprawnienie READ_ANALYZE: metadane, obserwacje, historia korekt, GPS replay i wynik analizy.
* Formularz jasno informuje, że udostępnia przebieg GPS.
* Analityk nie zmienia oryginałów, korekt ani metadanych właściciela.
* Udostępnienie można cofnąć; dostęp jest sprawdzany także przy kolejnych odczytach i wykonywaniu zadań.
* Eksport i surowe media CV pozostają wyłącznie dla właściciela w v1.
* Nie implementujemy oddzielnych scopes EXPORT/CV_MEDIA, grup, projektów ani wielostopniowych zgód.
* Brak automatycznego dziedziczenia dostępu do nowych przejazdów.

3. Administrator
* Usuń z obowiązkowego v1 mechanizm admin_access, break-glass i związane endpointy, formularze oraz powiadomienia.
* Administrator może zarządzać kontami i unieważniać ich dostęp, bez odczytu prywatnych danych.
* Operacje administracyjne mają audyt i wymagają odpowiedniego ponownego potwierdzenia tożsamości.
* Nie wolno zablokować lub zdegradować ostatniego aktywnego administratora.
* Ewentualne przyszłe awaryjne udostępnianie danych opisz wyłącznie poza zakresem v1.

4. Konta i poczta
* Zachowaj bezpieczny login, logout, zmianę hasła, sesje, CSRF, limity prób i jednorazowy reset.
* Zachowaj aktywację email, korzystając ze wspólnego mechanizmu tokenów i SMTP.
* Docker demo korzysta z Mailpit i syntetycznych adresów; wdrożenie z prawdziwymi danymi z poprawnie skonfigurowanej poczty i HTTPS.
* Tokeny resetu i aktywacji nie są ujawniane przez publiczne API ani logi.
* Bootstrap administratora przez CLI bez stałych publicznych haseł.
* Parametry hashowania opisz jako wymagające pomiaru na docelowym sprzęcie; zachowaj bezpieczne wartości początkowe i limit kosztownych równoległych operacji.

5. Nawigacja i telefon
* Akceptujemy jedną aktywną sesję nawigacji/nagrywania na cały deployment v1.
* Drugi użytkownik może przeglądać swoje dane i replay, lecz start jazdy dostaje jasne 409 bez ujawnienia właściciela aktywnej sesji.
* Token telefonu jest odrębny od sesji przeglądarki i związany z właścicielem oraz sesją parowania.
* Logout sesji nadrzędnej kończy związany z nią dostęp telefonu i nagrywanie.
* Restart wymaga ponownego parowania; zmiana hasła, blokada konta i zmiana roli unieważniają odpowiednie credentials.
* Uwzględnij konieczne późniejsze zmiany Androida.
* Nie zmieniaj warunków dopuszczenia rekomendacji live.

6. Rekordy
* Właściciel może edytować tytuł/notatkę przejazdu i archiwizować zamknięty przejazd.
* Oryginały GPS i obserwacji pozostają niezmienne.
* Korekty obserwacji są osobnymi wpisami z autorem, czasem, powodem i poprzednią/nową wartością.
* Nie realizujemy fizycznego usuwania surowych danych przez API v1.
* Stare nieprzypisane dane nie trafiają automatycznie do nowych kont. Import operatorski jest przyszłym, osobno zlecanym działaniem, a nie warunkiem ukończenia szkolnego demo.

7. CV i konfiguracja
* Zachowaj istniejącą diagnostykę CV oraz ochronę jej zasobów.
* Nie buduj nowych rozbudowanych procesów udostępniania filmów, uploadu czy biblioteki mediów na potrzeby szkolnej wersji.
* Publikacja konfiguracji nie oznacza weryfikacji terenowej. UI kont i role nie nadają wiarygodności fazom, liniom ani wynikom YOLO.
* Demo działa bez telefonu, ADB, kamery i YOLO.

C. UPROŚĆ ARCHITEKTURĘ BEZ UKRYWANIA WYMAGAŃ
1. Przejrzyj dotychczasowe 74 endpointy i model tabel.
2. Usuń elementy wynikające z odrzuconych funkcji. Nie redukuj liczby tabel lub endpointów sztucznie kosztem uprawnień i integralności.
3. Podziel zakres na:
* obowiązkowe v1;
* zachowane funkcje M8/CV wymagające bezpiecznej integracji;
* funkcje poza v1.
4. Każda tabela i endpoint obowiązkowego v1 musi mieć powiązanie z konkretnym scenariuszem.
5. Oddziel trwałe dane domenowe od odtwarzalnego stanu runtime. Uzasadnij, które sesje/replay/jobs wymagają tabel, a które wystarczą w pamięci z poprawnym recovery.
6. Zachowaj wersjonowane migracje, transakcje, audyt, poprawne korzenie storage, recovery i walidację wszystkich formularzy.
7. Sprawdź spójność między modelami, DTO, polityką dostępu, formularzami i scenariuszami. Usuń martwe odwołania do admin_access oraz wycofanych scopes.
8. Wyjaśnij, jak ograniczony namespace szkolny ochroni odziedziczone endpointy, eksporty i media bez przypadkowego publicznego dostępu.
9. Zachowaj ustalony szeroki zakres coverage i osobny pomiar istotnej logiki JS.

D. INSTRUKCJA URUCHOMIENIA I STATUS
1. Utwórz docs/school-app/run.md:
* jak wejść do worktree i sprawdzić gałąź;
* jak uruchomić obecnie działające bazowe GreenWave;
* jak zatrzymać serwer;
* jakie testy są obecnie dostępne;
* wyraźna informacja, że portal szkolny został usunięty i nie jest jeszcze zaimplementowany według nowego kontraktu.
2. Zweryfikuj opisane komendy na bieżącym kodzie. Do smoke testów użyj izolowanego eksportu lub jawnego katalogu danych syntetycznych. Nie uruchamiaj prób zapisujących w prywatnym data/runs/.
3. Nie podawaj przyszłego polecenia python -m greenwave.school jako już działającego.
4. Dodaj w README krótki odnośnik do instrukcji i dokumentacji szkolnego rozszerzenia.
5. Zaktualizuj stages.md:
* wpisz literalny hash dokumentacyjnego etapu 2: 3ff54d9d3c4a7dfb23b53db9095f69f1112427f0;
* etap 2 po tych poprawkach oznacz „Przygotowany do końcowego odbioru”;
* etapy 3–12 pozostają „Do zrobienia”.
6. Zaktualizuj ai-usage.md o ten prompt i faktycznie wykonane działania.
7. Dopisz do kontraktu, że wyżej wymienione decyzje produktowe są ustalone tym promptem. Nie proś ponownie o wybór D1–D7; pytaj tylko o rzeczywistą sprzeczność, której nie można rozwiązać na podstawie polecenia.

E. SPRAWDZENIA I COMMIT
* Wykonaj kontrolę zgodności dokumentacji i staged diff.
* Sprawdź, że staged changes nie zawierają nowych DB, nagrań, sekretów ani niezwiązanych zmian.
* Przy zmianach dokumentacji nie powtarzaj pełnej regresji bez powodu; wykonaj kontrole właściwe dla zakresu.
* Zrób dwa małe commity:
1. reguły ignorowania i usunięcie runtime wyłącznie ze śledzenia;
2. poprawiony kontrakt, instrukcja, README i rejestry.
* Nie pushuj automatycznie, nie przepisuj historii i nie scalaj z main.

Na końcu podaj:
1. Hashe obu commitów i git status.
2. Końcową macierz ról.
3. Zakres v1 oraz funkcje wyłączone z pierwszej wersji.
4. Liczbę i krótkie uzasadnienie obowiązkowych tabel oraz endpointów.
5. Wyniki kontroli dokumentacji i smoke testów.
6. Dowód usunięcia runtime z nowego drzewa Git przy zachowaniu lokalnych plików.
7. Informację o wcześniejszej publikacji runtime i ewentualnym nierozstrzygniętym problemie.
8. Dokładne komendy uruchomienia aktualnej aplikacji.
9. Krótką checklistę pozwalającą nam zatwierdzić etap 2.
Zatrzymaj się po tym etapie. Nie implementuj etapu 3 i nie deklaruj jeszcze spełnienia wymagań przez działający portal.
```

## Faktyczne działania i dowody końcowego doprecyzowania etapu 2

- Na wejściu HEAD3476d133006a948887899e8b75dcc210ce084248, status i staging
  puste. Odczytano instrukcje, dokumenty szkolne i aktualne źródła uruchomienia;
  prototyp pozostaje usunięty. Nie przywracano żadnej jego funkcji.
- git ls-files wskazał 7 ścieżek runtime (DB i manifesty/CSV). Odczytano jedynie
  nazwy/Git metadata oraz filesystem stat (is_file,size,mtime), nie zawartość.
  Dopisano ignore bez usuwania wcześniejszych reguł;git rm -r --cached -- runtime
  zachował pliki. Pierwszy commit 7a2899770075cc6ac12c826234f620f1de97a380:
  tylko .gitignore i 7 usunięć indeksu. Testy metadata/ignore/tree PASS.
- Kontrola nazw pozostałych śledzonych plików obejmowała DB/WAL/SHM,CSV,
  raw/metadata/complete,filmy/modelweights,env/reportdirs. Brak pozostałych
  podejrzanych ścieżek w sprawdzonym zbiorze nazw;nie jest to badanie zawartości
  ani gwarancja,że historia nie ma wrażliwych danych.
- Lokalny origin/codex/school-app zawiera3476d13. Zachowana historia nadal
  zawiera runtime;użytkownik wskazał publikację. PUBLISH-01 otwarte:charakter
  danych niebadany,bez założenia synthetic;opcje dalszej oceny w contract§1.
  Nie force-pushowano,nie przepisano historii,nie kontaktowano się z hostingiem.
- Przepisano kontrakt według zatwierdzonych decyzji:READ_ANALYZE na jeden trip,
  admin bez prywatnego read,owner-only export/CV,brak nowych mediów/importworkflow,
  Mailpit/SMTP,14 nowych trwałych tabel i37 APIcore+26 adapterówM8/CV. Runtime
  preauth/nav/replay/jobs w pamięci,domain/recordintents/reports trwałe. Decyzje
  nie są ponownie proponowane do wyboru D1–D7. Każdy element ma scenariusz.
- Dodano run.md i krótki READMElink. Baza uruchamia się przez python -m greenwave,
  portal school.py nie istnieje. Polecenia sprawdzono kodem/CLI i izolowanym
  exportem źródeł bez runtime/data/runs/data/derived. Smoke:runs source tylko
  w tym eksporcie;HTTP HTML/map/state PASS,syntheticrecord start/pause/finish/ZIP
  PASS,livebezverifieddata BLOCKED. Token testowy tylko w pamięci,nie w logach.
- Sprawdzenia właściwe zakresowi:python -m greenwave --help OK;
  python -m unittest discover -s tests -p test_live_navigation.py -q:
  2 testy OK;node --check greenwave/web/app.js OK;node --test tests/driver_ui.cjs
  tests/vision_workbench_ui.cjs:7 PASS;node tests/mobile_flow.cjs PASS.
  Nie powtarzano pełnej226regresji/Androidbuild/Playwright/YOLO ani pomiaru coverage.
- Kontrola dokumentacyjna:metody/ścieżki unique,14tabel/37core/26integration,
  scenariusze iCSRF,brak martwych mechanizmów odrzuconych w normatywnym kontrakcie,
  Markdownlinks/fences i statusy3–12. Nie mylić tej kontroli z testami nowego API.
- Drugi commit obejmuje wyłącznie contract.md,run.md,stages.md,ai-usage.md,README.
  Żadnych nowych DB/nagrań/sekretów/backendu;nie ma implementacji migracji/UI.
  Dokładny hash w odpowiedzi końcowej i resolverze rejestru. Etap2 pozostaje
  „Przygotowany do końcowego odbioru”,etapy3–12 „Do zrobienia”. STOP po tym etapie.

Historia wcześniejszych promptów powyżej pozostaje niezmieniona jako zapis
wycofanych propozycji;nie jest aktywnym kontraktem. Bieżące wymagania wyłącznie
w nowej wersji contract.md i niniejszym prompcie.


## Prompt etapu 3 (2026-10-12)

Treść polecenia użytkownika; pominięto wyłącznie puste linie/formatowanie interfejsu.
Ścieżka w prompcie ma konra.codex; użyto istniejącego, zweryfikowanego konra/.codex,
bez tworzenia nowego worktree.

```text
Etap 2 został zaakceptowany dokumentacyjnie. Teraz IMPLEMENTUJ etap 3, nie kończ na planie: Etap 3 — baza danych, migracje i warstwa dostępu do danych GreenWave School.
Pracuj w istniejącym worktree na codex/school-app:
C:\Users\konra.codex\worktrees\school-app\Surfy
Przeczytaj obowiązujące AGENTS.md oraz:
* docs/school-app/contract.md;
* docs/school-app/audit.md;
* docs/school-app/stages.md;
* docs/school-app/run.md;
* docs/school-app/ai-usage.md.
Zaakceptowany kontrakt znajduje się w commicie:
77c074cdc24eb14795eb8eb593167945d74eead4.

ZASADY
* Nie zmieniaj main ani codex/vision-camera.
* Sprawdź HEAD, git status i staging. Zachowaj niezwiązane zmiany.
* Nie odtwarzaj automatycznie usuniętego prototypu. Możesz korzystać z jego historii jako materiału, ale implementacja musi odpowiadać aktualnemu kontraktowi.
* Nie czytaj ani nie modyfikuj prywatnego data/runs/ i starego runtime/school/.
* Wszystkie testy wykonuj na nowych danych syntetycznych w TemporaryDirectory lub osobnym ignorowanym katalogu.
* Nie importuj starej bazy ani nie przypisuj starych nagrań nowym kontom.
* Nie zmieniaj solvera, predykcji ani warunków dopuszczenia rekomendacji live.
* PUBLISH-01 pozostaje osobnym problemem. Nie przepisuj historii ani nie wykonuj force push.
* Nie implementuj jeszcze serwera kont, SMTP, UI ani integracji telefonu z nowymi kontami.

CEL
Działająca warstwa persistence zgodna z kontraktem v1:
14 tabel, wersjonowane migracje, integralność danych, transakcje, backup/restore, jawny runtime root oraz testy.

1. ARCHITEKTURA WARSTWY DANYCH
Podziel kod na czytelne moduły: połączenie i transakcje, migracje, repozytoria oraz konfiguracja storage. Dobierz prostą strukturę do istniejącego projektu; unikaj jednego ogromnego modułu.
Ustal:
* jawny katalog danych szkolnego portalu;
* lokalizację school.sqlite3;
* brak automatycznego fallbacku do DATA/runs, DATA/derived lub starego runtime;
* konfigurację SQLite: foreign_keys, busy_timeout, WAL i synchronous zgodnie z kontraktem;
* poprawne zamykanie połączeń, rollback i obsługę błędów;
* wstrzykiwany zegar oraz generator ID, jeśli ułatwiają rzeczywiste testy.
Zachowaj działanie bazowego python -m greenwave. Nowa warstwa nie może uruchamiać migracji ani tworzyć kont przy samym imporcie modułu.

2. SCHEMAT I MIGRACJE
Implementuj 14 tabel z zaakceptowanego contract.md:
* schema_migrations;
* users;
* browser_sessions;
* account_tokens;
* auth_rate_limits;
* devices;
* pairing_challenges;
* trips;
* observations;
* observation_corrections;
* trip_shares;
* audit_events;
* config_versions;
* recording_operations.
Doprecyzuj SQL typy, nullability, klucze obce, CHECK, UNIQUE i indeksy. Odzwierciedl wszystkie istotne ograniczenia kontraktu. Nie twórz tabel odrzuconych w etapie 2.
Ograniczenia zależne od wielu rekordów lub aktualnego czasu egzekwuj atomowo w warstwie danych; opisz, czego nie da się wyrazić samym CHECK.
Migracje:
* numerowane pliki SQL/Python oraz stabilne checksumy;
* schema_migrations jest źródłem wersji, PRAGMA user_version jej zgodnym odzwierciedleniem;
* brak zmian checksumów już zastosowanych migracji;
* transakcyjne wykonanie bez niejawnych commitów rozrywających migrację;
* kontrola foreign_key_check i integrity_check;
* ponowne uruchomienie bez zmian jest bezpieczne;
* nowsza baza, niespójne wersje i niezgodny checksum powodują odmowę;
* awaria pozostawia bazę w określonym, sprawdzonym stanie.
Nie rozbijaj arbitralnie tabel na wiele migracji tylko po to, aby stworzyć historię. Test aktualizacji może wykorzystywać kontrolowaną syntetyczną migrację kolejnej wersji.

3. BACKUP, RESTORE I BLOKADA
Dodaj udokumentowane narzędzie CLI do:
* inicjalizacji/migracji nowej szkolnej bazy;
* odczytu statusu schematu;
* utworzenia backupu przez SQLite backup API;
* kontrolowanego odtworzenia backupu.
CLI nie służy jeszcze do logowania ani tworzenia rzeczywistych kont.
Zapewnij wyłączność operacji maintenance i odmowę konfliktującego dostępu zgodnie z architekturą v1. Rozróżnij blokadę procesu/runtime od transakcyjnej blokady SQLite. Rozwiązanie ma działać na Windows oraz w przyszłym kontenerze Linux.
Przed zmianą istniejącej bazy przygotuj backup. Restore:
* waliduje backup i zgodność schematu;
* nie nadpisuje aktywnie używanej bazy;
* zachowuje możliwość odzyskania poprzedniego stanu;
* nie udaje backupu surowych GPS i mediów.
Nie stosuj zwykłego kopiowania aktywnego pliku DB jako backupu przy WAL. Nie dodawaj backupów do Gita.

4. REPOZYTORIA I INTEGRALNOŚĆ DOMENOWA
Implementuj operacje warstwy danych potrzebne kolejnym etapom. To wewnętrzne API, nie publiczne endpointy.
Uwzględnij:
* tworzenie i odczyt kont z unikalnym znormalizowanym emailem;
* przechowywanie wyłącznie hashów sekretów sesji, tokenów kont i urządzeń;
* relacje sesji/urządzenia/kodu parowania z właścicielem;
* tworzenie przejazdu z właścicielem dostarczonym przez przyszły zaufany kontekst serwera;
* odczyty przejazdów i obserwacji ograniczone do właściciela;
* osobną ścieżkę odczytu jawnie udostępnionego przejazdu dla aktywnego ANALYST;
* brak globalnego odczytu prywatnych danych przez ADMIN;
* jedno aktywne udostępnienie ukończonego niearchiwalnego przejazdu;
* cofnięcie udostępnienia;
* modyfikację dozwolonych metadanych z expected_revision;
* oryginalne obserwacje i osobne korekty z autorem, czasem, powodem oraz before/after;
* append-only audyt;
* wersje konfiguracji;
* trwałe intencje operacji nagrywania.
Nie implementuj jeszcze pełnego workflow nagrywania, SMTP ani kryptografii logowania. Jeśli test potrzebuje password_hash lub token_hash, użyj jawnych fikstur, które nie udają gotowego mechanizmu uwierzytelniania.
Wewnętrzne API musi jasno rozróżniać zaufany actor/context od danych formularza. Testy repozytorium nie zastępują późniejszych testów autoryzacji HTTP.
Zapewnij ochronę niezmiennych pól i atomowe korekty:
* zwykły UPDATE/DELETE nie zmienia oryginałów obserwacji, korekt ani audytu;
* techniczna aktualizacja journaling_state/raw_sequence nie może przy okazji zmienić faktów obserwacji;
* dwie korekty z tą samą revision nie mogą obie przejść;
* powtórzenie tej samej operacji nie tworzy duplikatu;
* niezgodna treść pod tym samym kluczem operacji jest konfliktem.

5. STORAGE I GRANICE IMPLEMENTACJI
Dodaj resolver ścieżek szkolnego runtime zgodny z układem kontraktu. Ścieżki wynikają z kontrolowanych identyfikatorów i kontekstu, nie dowolnego path użytkownika.
Sprawdź containment i ucieczki przez symlinki lub Windows reparse points odpowiednio do dostępnego środowiska. Obsłuż przypadek braku możliwości wykonania takiego testu jawnie.
Nie podłączaj jeszcze istniejących loggerów, CV i replay do nowych kont. Przygotuj jawny interfejs oraz testy ścieżek, żeby integracja w kolejnych etapach nie dziedziczyła globalnych katalogów.
Nie deklaruj pełnego recovery nagrywania na podstawie samej tabeli recording_operations. W tym etapie sprawdzamy trwałość intencji; integracja DB–raw–manifest zostaje na etap 6.

6. TESTY
Dodaj znaczące testy jednostkowe i integracyjne na prawdziwej tymczasowej SQLite:
* fresh init, status i ponowna migracja bez zmian;
* aktualizacja syntetycznej starszej wersji;
* błąd w środku migracji i rollback;
* niezgodny checksum, nowsza wersja i rozbieżny user_version;
* backup oraz restore, również przy istniejącym WAL;
* konflikt maintenance/runtime lock;
* FK, CHECK, UNIQUE i indeksy potrzebne dla filtrów;
* dwa konta i odmowa odczytu cudzych rekordów;
* ADMIN bez automatycznego dostępu do cudzych danych;
* ANALYST przed udostępnieniem, po nim i po cofnięciu;
* udostępnienie niewłaściwemu odbiorcy lub nieukończonego przejazdu;
* trwałość rekordów po zamknięciu i ponownym otwarciu bazy;
* niezmienność oryginałów, korekt i audytu;
* konkurencyjne revision oraz idempotency;
* bezpieczne ścieżki i odrzucenie prób wyjścia z runtime root.
Uruchom nowe testy oraz odpowiednią regresję istniejącego GreenWave. Raportuj dokładne polecenia, wyniki i pominięcia.
Zmierz coverage nowej warstwy danych z branch=True i pokaż raport per moduł, linii oraz gałęzi. To wynik etapu 3, nie końcowe pokrycie aplikacji. Nie wprowadzaj wąskiej konfiguracji jako zastępstwa zaakceptowanego szerokiego zakresu końcowego.

7. DOKUMENTACJA I COMMITY
* Dodaj docs/school-app/stage3.md: implementacja, granice, schema, migracje, backup/restore i wyniki sprawdzeń.
* Aktualizuj run.md o dokładne komendy CLI bazy oraz testów. Wyraźnie zaznacz, że nowa baza nie oznacza jeszcze działającego loginu.
* Uzupełnij ai-usage.md o prompt, działania i weryfikację.
* Aktualizuj stages.md: etap 2 zaakceptowany, literalny hash 77c074cdc24eb14795eb8eb593167945d74eead4; etap 3 przygotowany do odbioru po wykonaniu sprawdzeń.
* Etapy 4–12 pozostają Do zrobienia.
* Dziel implementację na małe sensowne commity, np. migracje/backup, repozytoria/integralność, dokumentacja i odbiór. Nie wymuszaj liczby commitów kosztem spójności.
* Staging wyłącznie konkretnych plików. Żadnych DB, runtime, nagrań, środowisk ani raportów zawierających lokalne dane.
* Nie pushuj automatycznie i nie scalaj z main.

NA KOŃCU PODAJ
1. Podsumowanie zaimplementowanych funkcji i granic etapu.
2. Listę 14 tabel oraz wersję schematu.
3. Wyniki migracji, backup/restore i testów izolacji.
4. Dokładne wyniki testów i pomiar coverage.
5. Komendy PowerShell do stworzenia świeżej bazy testowej, sprawdzenia schematu, backupu, restore i testów.
6. Komendę uruchomienia aktualnego bazowego GreenWave.
7. Hash końcowego commita, listę commitów tego etapu i git status.
8. Checklistę ręcznego odbioru oraz ewentualne blokady.
Doprowadź etap 3 do działającego i sprawdzonego końca. Nie zaczynaj etapu 4.
```

### Faktycznie wykonana pomoc AI

Codex samodzielnie napisał pakiet school_data, SQL v1, repozytoria, CLI i trzy
moduły testowe. Nie delegowano pracy do innych agentów/czatów. Przeczytano AGENTS
(pusty), dokumenty szkolne i aktualne punkty integracji; stan wejściowy Git był
czysty, HEAD77c074c. Nie czytano danych starego runtime/private runs ani nie
importowano kont/nagrań. Nie odtworzono starego prototypu, nie zmieniono rdzenia/UI.
Zegar/ID są wstrzykiwane; wszystkie fixtures są nowe i syntetyczne.

Weryfikacja: wykonane testy prawdziwej SQLite TemporaryDirectory, subprocess lease,
WAL backup, restore previous snapshot, SQL trigger odmowy, stale revision i dwie
równoległe korekty, idempotency, role/share revoke, hash-only i token callback rollback.
Windows junction test PASS; zwykły symlink skip WinError1314 jawnie opisany.
Kod POSIX flock istnieje, lecz rzeczywisty Linux/Docker nie był tu uruchamiany.
Przegląd znalazł błąd zakazu COMMIT; poprawiono parser i test przeszedł. Przegląd
containment znalazł akceptację ../ między tripami; poprawiono resolved containment,
dodano odrzucenie i ponowiono wszystkie 34 testy danych.

34 testy: OK,1skip,7.822s. Izolowany eksport c6fd304:260 testów OK,1skip,31.127s;
po ostatniej poprawce ścieżki ponowiono 34 testy danych, bez zmian rdzenia.
7Node PASS,mobile_flow PASS; rzeczywiste CLI GreenWave +HTML/state200 PASS.
PowerShell school_data init/status/migrate/backup/restore/status na nowym
runtime/stage3-cli-<GUID> PASS. Nie testowano loginu/SMTP/telefonu, bo są poza etapem3.
Coverage7.13.1 branch=True:807/821linie98.2948%,218/274gałęzie79.5620%,combined93.6073%.
Per-module raport i dokładne komendy w stage3.md/run.md. Wynik nie zastępuje
szerokiego backend/M8/CV i osobnego JS pomiaru końcowego. Nie dodano wąskiej .coveragerc.

Commity implementacji:2af534f84fe766dd982d6d69beeafb9eb660fe85,
37de1cd491650aed75e3c593c4e0cfccfb8fce7f,c6fd304dc4e6965da19dd431773b3dfb8e8dc691,
a64adff4c14d1475422f1abd4270df14472b34ec; dokumentacja: commit dodający stage3.md
(`git log -1 --diff-filter=A --format=%H -- docs/school-app/stage3.md`).
Staging konkretnych źródeł/testów/dokumentów, bez DB/runtime/coverage/logów.
PUBLISH-01 nadal osobny; nie zmieniono historii, nie pushowano/mergowano.
Etap3 przygotowany do ręcznego odbioru; etap4 nie rozpoczęty.
