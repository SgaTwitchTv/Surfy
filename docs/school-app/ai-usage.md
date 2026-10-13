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


## Prompt poprawek etapu 3 po niezależnym przeglądzie (2026-10-12)

Pełna treść polecenia; wyłącznie puste linie/formatowanie rozmowy uproszczone.

```text
Nie skończylismy jescze. Etap 3 — poprawki po niezależnym przeglądzie i końcowy odbiór warstwy danych.
Kontynuuj w istniejącym worktree codex/school-app. Nie rozpoczynaj etapu 4. Przeczytaj obowiązujące AGENTS.md oraz contract.md, stage3.md, stages.md, run.md i ai-usage.md w docs/school-app.
Przegląd dotyczył commita:
6c3364997bd26cd8a0a0a67ee7505371bf93feef.
Niezależnie uruchomiono testy na Linuxie:
* 33 testy warstwy danych PASS;
* Windows junction test pominięty, POSIX symlink test PASS;
* pełna regresja: 260 testów, jeden błąd importu Tkinter wynikający z brakującej biblioteki środowiska.
Znaleziono cztery problemy. Napraw je, dodaj testy regresyjne i ponownie sprawdź etap. Nie kończ na propozycji.

ZASADY
* Nie zmieniaj main ani codex/vision-camera.
* Zachowaj niezwiązane zmiany użytkownika.
* Nie czytaj prywatnego data/runs/ ani starego runtime/school/.
* Testy i migracje wykonuj wyłącznie na nowych danych syntetycznych.
* Nie zmieniaj istniejącego loggera GPS, solvera ani warunków rekomendacji live.
* Nie odtwarzaj starego portalu.
* Nie przepisuj opublikowanej historii, nie wykonuj force push ani automatycznego merge.
* Nie edytuj zastosowanej migracji 0001_initial.sql. Jeśli zmienia się schema, dodaj kolejną numerowaną migrację.
* Zachowaj 14 tabel aplikacji.

1. BLOKUJĄCY BŁĄD MIGRACJI
Obecny parser statements() rozpoznaje pierwsze słowo przez split(). Komentarz poprzedzający komendę powoduje ominięcie zakazu COMMIT.
Odtworzony przypadek:
CREATE TABLE schema_migrations(
version INTEGER PRIMARY KEY,
checksum TEXT,
applied_at REAL,
app_version TEXT
);
CREATE TABLE proof_marker(id INTEGER);
-- transaction command hidden behind comment
COMMIT;
THIS IS INVALID;
W tym przypadku migracja kończy się błędem, lecz schema_migrations i proof_marker pozostają w bazie. Złamana zostaje gwarancja atomowości.
Wprowadź skuteczną kontrolę operacji wykonywanych przez migracje. Nie polegaj wyłącznie na pierwszym słowie tekstu SQL. Rozważ sqlite3.set_authorizer jako dodatkową ochronę rzeczywiście wykonywanych komend. Operacje transakcyjne runnera muszą nadal działać, a SQL migracji nie może samodzielnie sterować transakcją.
Uwzględnij:
* komentarze -- i /* ... */, również wieloliniowe;
* białe znaki i wielkość liter;
* COMMIT, END, ROLLBACK, BEGIN, SAVEPOINT i RELEASE;
* ATTACH, DETACH, VACUUM oraz niedozwolone PRAGMA;
* teksty SQL zawierające średniki i słowa COMMIT w literałach;
* legalne CREATE TRIGGER ... BEGIN ... END, których nie można odrzucić jako sterowania transakcją.
Dodaj testy:
* świeża migracja z komentarzem przed COMMIT zostaje odrzucona i nie pozostawia tabel aplikacji;
* nieudany upgrade pozostawia poprzedni schemat, dane i wersję;
* komentarze blokowe i alternatywne komendy nie obchodzą zabezpieczenia;
* legalne triggery nadal działają;
* po błędzie connection nie pozostaje w nieokreślonym stanie transakcji.
Zweryfikuj dokładnie powyższy przypadek, nie tylko nowy uproszczony wariant.

2. JEDNOSTKI CZASU: MILISEKUNDY INTEGER
Zaakceptowany contract.md określa UTC jako integer milisekundy. Obecna schema i repozytoria używają REAL sekund.
Zachowaj kontrakt: trwałe czasy domenowe, sesji, tokenów, limitów i audytu przechowuj jako INTEGER UTC epoch milliseconds.
Zrób to spójnie:
* dodaj migrację kolejnej wersji dla istniejącej szkolnej bazy v1;
* nie zmieniaj checksumu migracji 0001;
* zachowaj identyfikatory, dane, relacje, indeksy, triggery i ograniczenia;
* jawnie określ regułę konwersji sekund REAL do milisekund;
* sprawdź NULL, granice oraz wartości niedopuszczalne;
* dopasuj repozytoria, clock adapter i testy;
* wszystkie TTL, idle, absolute expiry i reauth muszą używać prawidłowych jednostek.
Możesz pozostawić time.time() jako źródło zegara, lecz konwersja na integer ms musi być centralna i jednoznaczna. Nie mieszaj sekund i milisekund w zaufanym Actor ani między modułami.
Backup/restore muszą działać także dla wspieranej starszej wersji:
* backup v1 ma być walidowany według jego historii migracji;
* restore v1 nie może po cichu udawać bieżącej wersji;
* po restore status pokazuje wymagany upgrade, a runtime odmawia startu do migracji;
* nowsza, obca lub uszkodzona baza nadal jest odrzucana.
Testy muszą potwierdzić aktualizację v1→bieżąca wersja z zachowaniem danych, rollback i backup/restore. Testy v1 twórz z historycznej, niezmienionej migracji w TemporaryDirectory. Nie używaj starego lokalnego runtime.

3. ZGODNOŚĆ Z LOGGEREM: RAW.CSV
transition_trip() wymaga teraz ścieżki kończącej się gps.jsonl, lecz istniejący RunLogger zapisuje raw.csv, metadata.json i complete.json.
Napraw nową warstwę danych tak, żeby odpowiadała istniejącemu formatowi:
* prawidłowy raw_ref wskazuje raw.csv we właściwym run-root właściciela i przejazdu;
* nie zmieniaj formatu istniejących nagrań ani RunLogger;
* gps.jsonl nie może być nieudokumentowanym wymaganiem;
* zachowaj kontrolę containment i odrzucanie cudzych ścieżek;
* usuń niespójne przykłady z dokumentacji oraz testów.
Dodaj test:
* syntetyczny run utworzony istniejącym RunLogger w nowym tymczasowym root;
* poprawna ścieżka raw.csv jest akceptowana przez warstwę danych;
* ścieżka do cudzej trasy/przejazdu i obejście przez ../ są odrzucane.
Nie deklaruj pełnego DB–raw–manifest recovery. Weryfikacja plików i koordynacja zapisu nadal należą do integracji etapu 6.

4. ZAKRES DAT: FROM INCLUSIVE, TO EXCLUSIVE
Kontrakt określa przedział [from, to). list_trips() i list_observations() używają teraz <= before.
Popraw obie listy:
* after/from: >=;
* before/to: <;
* from >= to jest błędnym przedziałem;
* odrzuć nieprawidłowe typy, bool jako czas i wartości niefinitywne;
* używaj jednostek zgodnych z poprawioną warstwą danych;
* zachowaj parametryzowane SQL.
Dodaj testy rekordów:
* tuż przed początkiem;
* dokładnie na początku;
* wewnątrz;
* dokładnie na końcu;
* tuż po końcu.
Dla obserwacji sprawdź, że filtrowany czas to server_received_at. Dla przejazdów created_at, zgodnie z kontraktem.
Offset w wewnętrznym repozytorium nie oznacza jeszcze docelowej paginacji HTTP. Zachowaj w dokumentacji informację, że keyset cursor oraz pozostałe filtry UI zostaną domknięte w etapie 6.

5. PONOWNY PRZEGLĄD I TESTY
Po poprawkach:
* uruchom wszystkie testy school_data;
* uruchom pełną regresję Python w izolowanym eksporcie;
* wykonaj odpowiednie testy Node i smoke bazowego GreenWave;
* sprawdź CLI init/status/migrate/backup/restore na świeżej syntetycznej bazie;
* sprawdź v1→bieżąca wersja, no-op, niezgodny checksum i odmowę nowszej wersji;
* ponownie zmierz coverage całej greenwave.school_data z branch=True, bez wyłączania nowych trudnych ścieżek.
Przejrzyj powiązane jednostki czasu, ścieżki i kontrole migracji, aby znaleźć podobne problemy. Nie poszerzaj zakresu o nowe funkcje.
Nie „naprawiaj” brakującego Tkinter przez ukrywanie testu lub zmianę rdzenia. Jeśli zależność środowiska blokuje pełną regresję, podaj dokładny błąd oraz oddziel wyniki wykonanych testów od blokady.
Nie deklaruj wykonania Linux/Windows testów, jeśli pracujesz tylko w jednym środowisku. Zapisz niezależny wynik Linux jako dowód z przeglądu użytkownika/ChatGPT, a własne wyniki jako osobne wykonanie.

6. DOKUMENTACJA I COMMITY
Zaktualizuj:
* stage3.md: problemy, rozwiązania, aktualna wersja schematu, jednostki czasu i wyniki;
* run.md: działające komendy init/upgrade/backup/restore/testów;
* contract.md: doprecyzuj techniczne szczegóły bez zmiany ustalonych ról i zakresu v1;
* stages.md: etap 3 „Przygotowany do ponownego odbioru”, etapy 4–12 nadal „Do zrobienia”;
* ai-usage.md: ten prompt, działania i rzeczywiste wyniki.
Wpisz literalny hash wcześniejszego etapu:
6c3364997bd26cd8a0a0a67ee7505371bf93feef.
Podziel poprawki na małe, sensowne commity. Staging wyłącznie konkretnych plików. Żadnych DB, runtime, nagrań, środowisk ani lokalnych raportów.
Nie pushuj automatycznie i nie scalaj z main.

NA KOŃCU PODAJ
1. Dla każdego z czterech problemów: przyczynę, poprawkę i test regresyjny.
2. Wynik dokładnego reproduktora komentarz + COMMIT + błędny SQL.
3. Aktualną wersję schematu i dowód zachowania danych przy upgrade.
4. Wyniki backup/restore, CLI i testu raw.csv.
5. Wyniki wszystkich uruchomionych testów, pominięcia i blokady.
6. Nowy raport coverage: linie, gałęzie, combined i per moduł.
7. Hashe commitów, końcowy git status oraz komendy ręcznego odbioru.
8. Jawne ograniczenia: brak loginu/SMTP/UI i brak pełnej integracji recovery.
Doprowadź poprawki etapu 3 do sprawdzonego końca i zatrzymaj się przed etapem 4.
```

### Działania i weryfikacja AI w tej poprawce

Codex bez subagentów zmienił wyłącznie school_data/testy i dokumentację szkolną.
Naprawa authorizer i rzeczywisty reproduktor:fb80ef609632a78fd268ce864ede713c2b98df71.
Migracja0002,centralny czas,raw.csv,[from,to),legacy backup i regresje:
023198ae149b4953e2311be7c9729ac128d6e405. Zastosowana0001 niezmieniona,checksum
3341933b714ccf9fcd01add836ff395541a5d4e8a99baa39143cccc5c0723156,
porównana z Git6c33649. Etap4 nie rozpoczęty,bez authserver/SMTP/UI/zmian loggera/solvera.

Własne Windows wyniki:48 testów danych OK,1skip,15.752s;pełna regresja274 OK,
1skip,39.289s;7Node PASS,mobile_flow PASS;actualCLI GreenWave HTML/state200 PASS.
Tkinter działał,nie wyłączano testu. Skip Windows symlink WinError1314;junction PASS.
Linux33PASS/POSIXsymlinkPASS/junctionskip i Tkinter import error dotyczą niezależnego
przeglądu6c33649,przekazanego przez użytkownika/ChatGPT;nie własnego wykonania Linux
ani sprawdzenia obecnego kodu. Pełnego tracebacku nie otrzymano.

Dane wyłącznie TemporaryDirectory lub nowe ignorowane runtime/stage3-review i
stage3-legacy GUID roots. Rekordy wszystkich14tabel z v1 zachowane po v2 z konwersją
UTCfloorDecimalms i NULL,FK/indeksy/triggery/auditsequence preserved. Invalid legacy
values/SQL failure rollback. Backup v1 przyWAL/restorependingupgrade/ponownyupgrade PASS.
Dokładny SQLreproduktor kończy się SchemaError przedCOMMIT,zero tabel/user_version0.
Legalne triggery i literalCOMMIT PASS. PrawdziwyRunLogger tworzyraw.csv,hashniezmieniony;
ownref accepted,cudze/../ denied. Pięć granic datefilters i invalidtypes PASS.
Początkowa nowa fixture RunLogger.finish miała brak wymaganych argumentówcontext;
poprawiono sam test zgodnie z istniejącymAPI i ponowiono testy,bez zmianRunLogger.

Coverage całegoschool_data branch=True,bezomit/exclude:linie870/883=98.5277%,
gałęzie245/298=82.2148%,combined94.4115%;time_units100%,migrations98.7097%combined.
Nie zastępuje końcowego szerokiego backend/M8/CV i oddzielnegoJS. Komendy i per-module
raport stage3.md/run.md. Dokumenty sprawdzone pod kątem wersji,jednostek,ACL,linków,
staged paths i braku zmian0001/rdzenia/main/CV. Commity tylko wskazane źródła/testy/docs,
bezDB/nagrań/runtime/coverage. Nie pushowano,nie przepisywano historii,nie mergowano.
PUBLISH-01 pozostaje osobno. Etap3 Przygotowany do ponownego odbioru;4–12 Do zrobienia.


## Prompt etapu 4 (2026-10-12)

Pełna treść polecenia użytkownika, z uproszczonymi pustymi liniami formatowania.

```text
Dobra to lecimy etap 4 — konta, sesje, aktywacja email i bezpieczny reset hasła.
Etap 3 zaakceptowany po niezależnym przeglądzie kodu i testów. Kontynuuj w istniejącym worktree na codex/school-app. IMPLEMENTUJ etap 4 do działającego, sprawdzalnego końca.
Najpierw sprawdź aktualny HEAD i status. Zaakceptowany commit etapu 3 ma skrót 2020b84; ustal i zapisz pełny hash.
Przeczytaj obowiązujące AGENTS.md oraz docs/school-app:
contract.md, stage3.md, stages.md, run.md, ai-usage.md.

ZASADY
* Nie zmieniaj main ani codex/vision-camera.
* Zachowaj niezwiązane zmiany.
* Nie czytaj prywatnego data/runs/ ani starego runtime/school/.
* Nowy portal używa wyłącznie jawnego, nowego runtime root.
* Nie importuj starych kont, baz ani nagrań.
* Nie zmieniaj zastosowanych migracji. Zmiana schematu wymaga następnej migracji.
* Wszystkie trwałe czasy i zaufany Actor używają INTEGER UTC epoch milliseconds.
* Nie zmieniaj solvera, predykcji ani warunków rekomendacji live.
* Nie wystawiaj odziedziczonych endpointów GreenWave przez nowy serwer.
* Nie odtwarzaj usuniętego prototypu jako gotowego rozwiązania.
* Nie przepisuj historii, nie pushuj i nie scalaj automatycznie.

ZAKRES ETAPU
Implementujemy cały przepływ kont i HTTP API uwierzytelniania, transport SMTP, bootstrap administratora oraz minimalny działający interfejs kont.
Nie implementujemy jeszcze tabel przejazdów, nowych widoków analityka/admina, integracji GPS/CV ani pełnej ochrony wszystkich endpointów M8 — to kolejne etapy. Nowy serwer nie może jednak umożliwiać obejścia logowania przez przekazanie żądania do starego Handlera.

1. ARCHITEKTURA I KONFIGURACJA
Zbuduj osobne, czytelne moduły:
* hasła i tokeny;
* usługa kont;
* sesje i preauth/CSRF;
* rate limits;
* SMTP i kolejka dostarczania;
* konfiguracja oraz HTTP adapter.
Wykorzystaj greenwave.school_data. Uzupełnij jego wewnętrzne API tam, gdzie potrzebne, zachowując atomowość i istniejące testy.
Dodaj udokumentowaną komendę uruchomienia serwera kont z:
* jawnym runtime root;
* host/port;
* publicznym base URL i dokładną allowlistą Host/Origin;
* ustawieniami cookie i SMTP;
* sekretami konfiguracji poza Gitem.
Nie uruchamiaj migracji po cichu. Serwer wymaga aktualnej, wcześniej przygotowanej bazy. Import modułów nie wykonuje I/O.
Tryb localhost/demo HTTP musi być jawny. Dla wdrożenia sieciowego z prawdziwymi danymi wymagaj HTTPS oraz Secure cookies. Nie ufaj X-Forwarded-For/Proto bez jawnie skonfigurowanego zaufanego proxy.

2. HASŁA
Implementuj zgodnie z kontraktem:
* 12–128 znaków Unicode, maksymalnie 512 bajtów UTF-8;
* bez trim i normalizacji hasła;
* scrypt z losową solą i wersjonowanym formatem parametrów;
* początkowe parametry kontraktu, jawny pomiar czasu i kosztu na obecnym sprzęcie;
* stałoczasowe porównanie wyniku;
* dummy verification dla nieistniejącego konta;
* rehash obsługiwanej starszej wersji po poprawnym loginie;
* ograniczenie równoległych kosztownych operacji.
Nie stosuj słabszego KDF w działającym demo. Testy jednostkowe mogą używać wstrzykniętego tańszego KDF, ale test integracyjny musi sprawdzić rzeczywistą konfigurację.
Przy odczycie zapisanego formatu ogranicz dopuszczalne parametry, żeby uszkodzony hash nie wymuszał nieograniczonego RAM/CPU.

3. REJESTRACJA I AKTYWACJA
* Rejestracja tworzy wyłącznie DRIVER/PENDING_VERIFICATION.
* Waliduj email, display_name, password i confirmation na kliencie i serwerze.
* Odrzucaj niedozwolone pola role/status/owner/verified.
* Zachowaj normalizację i UNIQUE email.
* Prawidłowe żądanie dla nowego lub istniejącego email ma neutralne 202.
* Dostarcz SMTP jednorazowy token VERIFY_EMAIL, przechowując tylko jego hash.
* Token ma właściwy purpose, TTL i security_version.
* GET linku nie zużywa tokenu.
* POST aktywacji zużywa token i aktywuje konto atomowo.
* Zablokowane konto nie może odzyskać dostępu przez aktywację.
* Ponowienie aktywacji działa według kontraktu bez osobnego rozbudowanego workflow.

4. SESJE, LOGIN I LOGOUT
Implementuj:
* login z jednolitym 401 dla błędnego hasła, braku konta, blokady i braku aktywacji;
* nowy losowy sekret sesji przy loginie;
* przechowywanie wyłącznie hasha sekretu;
* cookie HttpOnly, SameSite=Strict, Path=/, bez Domain, Secure według profilu;
* idle 30 minut i absolute 8 godzin;
* kontrolę statusu konta i security_version przy każdym chronionym żądaniu;
* ograniczenie częstotliwości zapisu last_activity;
* /auth/me z bezpiecznym DTO bez hashów i sekretów;
* logout bieżącej sesji i logout wszystkich sesji;
* reauth z rzeczywistą weryfikacją hasła i rotacją sekretu oraz CSRF;
* odmowę wykorzystania starego sekretu po rotacji;
* zmianę hasła z current password, CSRF i atomową revokacją sesji/tokenów/urządzeń;
* brak auto-login po zmianie lub resecie hasła.
Actor jest konstruowany wyłącznie na podstawie uwierzytelnionej sesji. Timestamp reauth nie może pochodzić z body ani nagłówka użytkownika.
Istniejące repository change_account nie jest automatycznie publicznym endpointem. W tym etapie dodaj tylko operacje konieczne dla własnej zmiany hasła; panel zarządzania rolami pozostaje na etap 8.

5. CSRF, PREAUTH I HTTP
Zaimplementuj endpointy kont zgodnie z contract.md, bez wymyślania konkurencyjnego namespace.
* Preauth cookie i CSRF dla login/register/reset/verify.
* Oddziel preauth od sesji użytkownika.
* CSRF powiązany z aktualnym sekretem cookie; rotacja unieważnia stary token.
* Wszystkie odpowiednie mutacje wymagają CSRF i dokładnego Origin.
* GET nie zmienia haseł, nie aktywuje konta i nie zużywa tokenu.
* Walidacja JSON: object, poprawny Content-Type, limit body, brak duplikowanych i nieznanych pól, NaN/Infinity oraz nieprawidłowych typów.
* Neutralne błędy bez stacktrace, SQL, ścieżek i sekretów.
* no-store, nosniff, Referrer-Policy oraz CSP bez unsafe-inline dla nowego UI.
* Publiczne zasoby ograniczone do jawnej allowlisty shell/static/health/auth.
* Brak dostępu do runtime, DB, backupów i starych endpointów M8.
* Health nie ujawnia konfiguracji poczty, ścieżek ani kont.
Serwer musi umożliwiać postęp niezależnych żądań przy hashowaniu i wysyłce poczty, zgodnie z blokadami warstwy danych. Nie blokuj całej aplikacji synchroniczną wysyłką SMTP.

6. RESET HASŁA I SMTP
Implementuj kompletny przepływ:
* request-reset z neutralnym 202 i limitami niezależnymi od istnienia konta;
* token RESET losowy >=32 bajty, hash w DB, TTL 15 minut;
* cofnięcie poprzednich niewykorzystanych resetów;
* link wyłącznie z zaufanego PUBLIC_BASE_URL;
* token we fragmencie URL, przejęty do pamięci i usunięty z adresu przez klienta;
* brak linku/tokenu w publicznym API, logach i trwałym outboxie;
* POST reset z confirmation i preauth CSRF;
* atomowa zmiana hasła, zużycie tokenu i revokacja credentials;
* równoległe użycie: najwyżej jeden sukces;
* invalid/expired/used token ma neutralny wspólny błąd;
* po sukcesie użytkownik loguje się ponownie.
SMTP:
* ograniczona kolejka w pamięci i worker z timeout;
* walidacja konfiguracji;
* STARTTLS/SMTPS z weryfikacją certyfikatu dla realnego profilu;
* lokalny odbiornik wyłącznie dla danych syntetycznych w profilu demo;
* poprawne delivery_state i zachowanie po błędzie/restart;
* przy pełnej kolejce lub awarii nie twórz fałszywego dowodu wysłania;
* sekret tokenu nie może trafić do wyjątku, logu ani audytu.
Nie wykonuj testowych wysyłek do rzeczywistych osób. Używaj lokalnego SMTP test server oraz example.test.
Docker i pełny Mailpit deployment pozostają na etap 11. Już teraz podaj działającą lokalną instrukcję odbioru poczty demonstracyjnej. Jeśli Docker jest dostępny, można użyć samego Mailpit; jeśli nie, zapewnij jasno oznaczony lokalny odbiornik testowy poza produkcyjnym profilem. Nie zastępuj SMTP publicznym endpointem zwracającym token.

7. RATE LIMITS I BOOTSTRAP
Wykorzystaj trwałe liczniki z warstwy danych:
* poprawne jednostki ms;
* limity kontraktu;
* jednakowe zachowanie dla kont istniejących i nieistniejących;
* limit przed kosztownym KDF;
* brak trwałej blokady konta przez napastnika;
* bezpieczny HMAC kluczy email;
* 429 i Retry-After.
Dodaj CLI pierwszego administratora:
* getpass, bez hasła w argv i bez domyślnego hasła;
* atomowa odmowa, jeśli istnieje aktywny administrator;
* audyt bootstrapu;
* jawny operatorski stan aktywacji;
* brak publicznego bootstrap endpointu.

8. MINIMALNY INTERFEJS KONT
Dodaj prosty, spójny i responsywny interfejs:
* rejestracja;
* login;
* instrukcja sprawdzenia poczty;
* aktywacja;
* prośba o reset i formularz nowego hasła;
* ekran zalogowanego konta;
* zmiana hasła i wylogowanie.
Fetch/AJAX, walidacja klienta, błędy pól, loading i blokada podwójnego submit. Nie zapisuj haseł ani bearer tokens w localStorage. Po 401 usuń prywatny stan.
Zalogowany ekran pokazuje tylko bezpieczne dane bieżącego konta i informację o aktualnie dostępnych funkcjach. Nie prezentuj niezaimplementowanych tabel lub integracji jako działających.
Docelowe tabele, nawigacja i pełny design pozostają na kolejne etapy.

9. TESTY I ODBIÓR
Dodaj testy jednostkowe oraz integracyjne HTTP z prawdziwą tymczasową DB i lokalnym SMTP:
* normalizacja i wyścig rejestracji tego samego email;
* DRIVER niezależnie od prób podania innej roli;
* brak loginu przed aktywacją;
* VERIFY/RESET niezamienne, single-use, expiry i GET bez consume;
* pełny register → mail → verify → login → me → logout;
* pełny request-reset → mail → reset → nowy login;
* równoległy reset i rollback błędu transakcji;
* cookie/CSRF/Origin, fixation, rotacja i stary sekret;
* idle/absolute TTL, block/security_version i revokacja wszystkich credentials;
* rate limits i Retry-After;
* SMTP failure, pełna kolejka i restart z niewysłanym tokenem;
* brak sekretów w odpowiedziach, logach i audycie;
* bootstrap i jego konflikt;
* odmowa dostępu do runtime/backupów/odziedziczonych endpointów.
Dodaj automatyczny scenariusz przeglądarkowy głównych formularzy na desktop i smartfonie. Jeśli środowisko blokuje przeglądarkę, podaj blokadę zamiast deklarować sukces.
Uruchom testy etapu 4, regresję school_data i odpowiednią regresję GreenWave. Zmierz coverage nowych modułów kont oraz warstwy danych z branch=True i raportem per moduł. Wynik etapowy nie zastępuje końcowego szerokiego zakresu aplikacji.

10. DOKUMENTACJA I COMMITY
* Dodaj docs/school-app/stage4.md z implementacją, wynikami i ograniczeniami.
* Aktualizuj run.md oraz README: dokładne polecenia init/migrate, konfiguracji, bootstrapu, SMTP demo, uruchomienia portalu i testów.
* Instrukcja ma umożliwić mi ręczne przejście pełnej rejestracji i resetu bez zgadywania.
* Uzupełnij ai-usage.md.
* Aktualizuj stages.md: etap 3 zaakceptowany z pełnym hashem; etap 4 przygotowany do odbioru; etapy 5–12 nadal Do zrobienia.
* Małe sensowne commity, staging konkretnych plików.
* Żadnych DB, nagrań, mailboxów, sekretów ani środowisk w Git.
* Nie pushuj i nie scalaj automatycznie.

NA KOŃCU PODAJ
1. Działające funkcje oraz granice etapu.
2. Dokładne komendy PowerShell do uruchomienia serwera i poczty demo.
3. Instrukcję ręcznego register/verify/login/logout/reset/change-password.
4. Wyniki testów HTTP, SMTP, przeglądarkowych i regresji.
5. Wynik coverage oraz pomiar kosztu rzeczywistego KDF.
6. Hash końcowego commita, listę commitów i git status.
7. Blokady i ograniczenia.
8. Potwierdzenie, że nowy serwer nie udostępnia prywatnych danych ani legacy API bez ochrony.
Doprowadź etap 4 do sprawdzonego końca i zatrzymaj się przed etapem 5.
```

### Rzeczywista pomoc AI i jej weryfikacja

Codex napisał moduły school_accounts, samodzielny HTTP adapter, CLI/getpass,
SMTP worker i lokalny syntetyczny odbiornik oraz minimalny UI. Nie delegowano
pracy do innych agentów/czatów. Baza wejściowa i zaakceptowany etap3:
2020b84d68ef3720c1b2d2345cf381c98a2a603b; status/staging czyste. Czytano obowiązujące
AGENTS i dokumenty. Schema2/14tabel i zastosowane migracje niezmienione; brak
czytania prywatnych data/runs/runtime/school, importu starego prototypu czy zmian rdzenia.

Własne Windows wykonanie:29 testów kont PASS; razem77 kont+danych OK,1skip,57.506s.
Pełna regresja syntetycznego eksportu9dcf41e:303 OK,1skip,78.617s. Node7+mobileflowPASS.
Browser Edge headless desktop1280x900 i phone390x844 pełne register/SMTP/verify/login/
reauth/logout/reset/change/logoutall PASS z produkcyjnym KDF,zero pageerrors/overflow/
localStorage. Rzeczywiste subprocess CLI init/migrate/keys/serve/demomail i pełny
register→mail→verify→login→me PASS. BaseCLI HTML/state200 w eksporcie PASS.
Testy nie wysyłały wiadomości do realnych osób; tylko localhost i example.test.

Fixtures używają TemporaryDirectory i wyraźnie tańszego wstrzykniętego KDF;
realny scryptN131072 sprawdzony unit/integracyjnie w browser/CLI, demo nie osłabione.
ActualStartTLSfailure lokalnego odbiornika, mock certverify STARTTLS/SMTPS,
capacity/restart/PENDING recovery,parallelreset/rollback/limits/CSRF/cookies/revoke
sprawdzone testami. Tkinter działał;1skip to Windows symlink1314,junctionPASS.
Nie wykonano Linux ani realnego sieciowego HTTPS/proxy/SMTP-certificate deploymentu;
Docker/Mailpit/hardware to późniejsze etapy,nie ukryte sukcesy.

Początkowe błędy: fixture odczytana cp1252 zamiast UTF8, zły obiekt mockSMTP,
za krótka lista fixturegetpass, brakargtypes dla benchmarku HANDLE Windows,
Windows TCPreset przy early403, brak obsługi same-document hashchange linku.
Naprawiono i ponowiono testy. Przegląd dodał refund wrong-passwordbudget przy503KDF_BUSY
oraz wspólny mailbudget register/reset niezależny od istnienia email.

CoveragebranchTrue całe school_accounts+school_data bezomit/exclude:
1587/1660linie95.6024%,416/524gałęzie79.3893%,combined91.7125%.
Samekonta88.5344%combined,dane94.4115%;permodule stage4.md. Wynik nie zastępuje
końcowego szerokiego backend/M8/CV i osobnego JS. KDF CLIbenchmark:mediana0.5728665s,
PeakWorkingSet175083520B (~167MiB),core128MiB/op,max2;pełne parametry/pomiar stage4.md.

Commity:d0b2ddcbb2aea9c74ff3710a7e341e4997be5462,
90beec7bd5b0abc51548e5c240e9e439708d2f87,4746c9ee5c55806e91e9bb25f7881244958322de,
2b9ed3ddb8e34e316701270e64904c290a73541b,9dcf41e1b3e7140a64b437357f94f9614400eea2;
dokumentacja:commit dodający stage4.md (git log -1 --diff-filter=A --format=%H -- docs/school-app/stage4.md).
Dokumenty/README i dokładne komendy sprawdzone; staging konkretne źródła/testy/docs,
bezDB/raw/mailboxów/kluczy/środowisk/logów/coverage. Main/CV niezmienione,
bezpush/merge/rewrite;PUBLISH-01 osobno. Etap4 przygotowany do odbioru,5–12 Do zrobienia.

## 2026-10-13 — etap 5: uprawnienia i ochrona zasobów

Prompt użytkownika (ujawniony zakres i kluczowe instrukcje;to opis polecenia,
nie deklaracja ukończenia wszystkich przyszłych integracji):

> Okej to lecimy etap 5 — uprawnienia i ochrona API zasobów GreenWave School.
> Etap4 zaakceptowany:45eef418efa9ca0afc9af8a6137a286fa990f5a7. Kontynuuj w
> istniejącym worktree codex/school-app. IMPLEMENTUJ do działającego i
> sprawdzalnego końca;przeczytaj AGENTS i docs/school-app contract/audit/stage3/
> stage4/stages/run/ai-usage oraz HEAD/status/staging. Zachowaj niezwiązanezmiany;
> nie czytaj prywatnego data/runs/starego runtime/school,nie importuj kont/nagrań,
> nie zmieniaj migracji/raw.csv/solver/GATE,UTCinteger ms,bezpush/merge/rewrite.

Pozostałe żądania promptu,ujawnione bez zmiany jego intencji:

- Inwentaryzacja każdej metody/ścieżki accounts i trips/observations/corrections/
  shares/export/replay/jobs/results/CVcapture/status/events/preview/frames/media/
  Range/devices/pair/config/admin. Status działa/implementowana/niedostępna,
  polityka,źródło i owner. Nie catch-all Handler ani local token zamiast kont.
- Wspólna polityka:session/active/securityversion,role,ownerparent,READ_ANALYZE,
  adminfreshreauth,defaultdeny. Role wszystkie own;DRIVERown;ANALYSTown+shared
  completed;ADMIN bez globalGPS/filmów. SessionActor/role/owner/reauth wyłącznie
  serwer. Anonymous401,foreign/missing404,explicitrole403,nie blanketDataError503.
- SafeDTO/SQLscope/pagination własnychtrip/obs/history/shared/derived/configs;
  bezhashes/sekretów/paths/audytu. Fullfilters/cursors etap6. Dostęp przedfile/CPU.
- Export ownCOMPLETEsynthetic M8raw.csv/metadata/complete;manifest/hashkontrola,
  controlledrunroot,containment/traversal/symlink/reparse/DB/backup odmowa,
  żadnego globalscan/upload/biblioteki.
- Replayown/shared,handle session+trip,bezglobalnav/radlive;analysisactor/trip,
  access przedexecute/status/result,revokacja share i wynikowner;CVowneronly
  metadane/events/media/Range eachrequest/pertrip,no filenames dlaanalyst,
  nieYOLO/camera tests,niepodłączone funkcje jawnie unavailable.
- Propagacja logout/all/password/reset/block/role/archive/sharerevoke na kolejne
  żądania/jobs;oldcache/handle nie utrzymuje praw. Technicalclose nie read,
  streamingbounded/reauthboundary,nie cofa downloadedbytes. Logger/phone później.
- Zachować Host/Origin/CSRF/JSON duplicate/unknown/NaN/bodylimits/noCORS/headers/
  neutralerrors/requestid/nosecrets. BezmutacjiGET,bezpublic provisioning.
- HTTPmatrix2driver+analyst+admin:own/foreign/shared/unshared/obs/corrections/
  syntheticderived;anon/owner/otherdriver/analystno/yes/adminforeign/expired.
  ID substitutions/spoof/sharedexportCVdeny/revoke/role/block/archive/reset/
  traversal/junction/Range/DB/cache/jobs/CSRF/Origin/DTO/legacy. Disabled nie
  zastępuje testu rzeczywistej integracji. TestauthSMTP/data/coreJS/browser,
  smoke login→own→foreigndenial→logout,branchTrue accounts+data+policy/adapters
  permodulenoomit,wyniketapowy nie szeroki końcowy M8/CV coverage.
- Dokumenty stage5/run manualtwo-users/analyst/AI/stages4acceptedliteralhash,
  5prepared,6–12todo;smallcommits,exactstaging,noruntime/DB/mailbox/secrets,
  finalmatrix/endpoints/testresults/export/replay/analysisCVRange/coverage/
  commands/hashes/status/limitations/future6–9. STOP przed6.

AI wykonała kod policy/reads/files/contexts/API,HTTPmount/neutralDataError mapping,
20działającychresource method/path,syntetyczny CLIfixture(tylkoemptyDB),17testów,
Playwrightfetchsmoke desktopphone. Nie delegowała pracy do innych czatów/agentów.
Nie odtwarzała starego portalu;bezprywatnychdata/staregoruntime/migracjichanges.
Eksport TemporaryFile/64KiB recheck;realM8GPSReplay/RunAnalysisGPS_QUALITY;
CVmanifest/eventsdecode/mediaRange tylkoowner;livepreview/camera/phone/writes/
adminviews pozostają konkretnie niedostępne w inwentaryzacji stage5.md.

Weryfikacja faktyczna:17/17resourcePASS58.404s;94schooltesty93PASS1skip117.364s;
pełna izolowanaPythonregresja320,319PASS1skip132.336s;WindowsjunctionPASS,
POSIXsymlinkskipWinError1314,bezLinuxclaim/Tkintermasking. ObaBrowserresource i
accountsmoke1280x900/390x844PASS zrealKDF,7NodePASS+mobileflowPASS. CLIinit/keys/
serve/loginownforeignlogoutPASS TemporaryDirectory,fixture getpass wejście
wstrzyknięte syntetycznie w unattendedWindows test (pipedstdin utknął na
konsolowymgetpass,własny zweryfikowany proces zakończony). BazowyGreenWave
isolatedexportHTML/state200PASS. Coverage całych3pakietów branchTrue:
2150/2243linie95.8538%,594/772gałęzie76.9430%,combined91.0116%,zeroexclusions;
resourcecombined89.1473%,permodule stage5.md. Wynik nie końcowy backend/M8/CV/JS.

Pierwsze testy wykryły błędyfixture operationkey/SignalAssociation/cookieaccount
switching;poprawionofixtures,niebypass. Przegląd dodał scoped SQLpaginatedhistory
orazfailclosedconfigpayloadcredentials/paths;jobown/requester policyniegrant
cudzychhandles. Codecommits5ada5e834ac50d4bea07a6d57d7152b78bc6bda9 i
09646eb735dd8f141de3f89087a644eb875c8a76;doccommitstage5.md. FinalGitdiffcheck/
stagednames/docslinks/status sprawdzone. Bezpush/merge/rewrite. Etap5 przygotowany
do odbioru;6–12Dozrobienia. PUBLISH-01 nadaloddzielny.


## Etap 5 — poprawka revoke/regrant po niezależnym przeglądzie

Otrzymany prompt użytkownika (wiadomość urwana w punkcie4):

> Poprawimy etap5 — poprawka cofania udostępnień i końcowy odbiór.
> Kontynuuj w istniejącym worktree codex/school-app. Nie rozpoczynaj etapu6.
> Przeczytaj AGENTS.md oraz contract.md,stage5.md,stages.md,run.md,ai-usage.md.
> Przegląd dotyczył0b10d9b39c1f0251c513bcdfdffddffe74318b67.
> Niezależne Linux:17testówzasobówPASS;pełna regresja320,jedenimportTkinter
> (biblioteka środowiska) i jeden pominiętyWindows;dodatkowy reproduktor błąd.
> Zachowaj main/CV i niezwiązane zmiany,bezprivate data/runs/runtime/school,
> tylko nowesyntheticdata,bezsolver/logger/livegate/newproduct/migracjichanges,
> pamięciowe replay/jobs bez nowychtabel;bezrewrite/push/merge.
>
> Odtwórz PRZED poprawką:owner share COMPLETE analyst→replay→revoke→re-share
> tego samego trip temu samemuanalyst→GET staregohandle200. Nie wstawiajread
> między revoke i nowyshare;obecny replay_context usuwa go dopiero po odmowie.
> Przyczyna:session/credential/tripbezkonkretnegograntu. ZapisztestFAILprzedfix.
>
> Jawnywewnętrznykontekst OWN dlaowner lub SHARE zkonkretnymshare_id,odbiorcą
> i trip. ZaktualnejDB/uwierzytelnionejsesji,niebody/query/headers. Przycreate
> replay/job zachowaj dokładnąpodstawę orazsession/credential;przyread/execute
> sprawdzaj tę samąpodstawę. Nie zastępuj share_id i niefallbackinnego dostępu.
> Cofniętygrant nie ożywa przeznewgrant. Nie ujawniajinternalrefs/secretswDTO,
> nieposzerzajadmin/analyst.
>
> Stare replayread/control/close nieodzyskująpraw poreshare;usuń/oznaczpermanent
> invalid;neutral404. Nowy replaynowyshare i ownerreplaydziałają. Rotacja/logout/
> expiry nadalinvalid. Sprawdźaktualnerevoked_at,właściwegoanalyst/trip,nie samID.
>
> Jobs:queued/running/status/cancel/publication. Staryshare niepublikujedzięki
> nowejzgodzie. Ponownie sprawdzajkonkretnąpodstawę:przedwykonaniem;przeddostępemdo

Dalszej części nie otrzymano na moment zapisania tego wpisu. AI zapytała o nią
narzędziem request_user_input_async i wykonywała niezależnie otrzymany zakres.
Nie traktujemy urwanego zdania jako zgody na nieznany zakres kolejnego etapu.

AI:sprawdziła czystyHEAD0b10d9b i pustyAGENTS,rejestry;dodała exactHTTPreproducer.
Przedfix18testów(17importowanychexistingPASS,reproducerFAIL200!=404),67.822s.
Poprawiono import klas testowych,aby nie dublować suite. Następnie frozen
AuthorizationBasis OWN/SHARE,checkdokładnychgrant/actor/trip/role/status/revoked;
pinningreplay/job/Files.runhasher. Przedanalysis i publikacją brakfallback.
PrzedmanifestpublishingBEGINIMMEDIATE zSessionlookup na tym samym connection,
bezduplikowanejlogikiauth i bezmigracji. Stalejob permanentinvalid/cancelled,
DTO bezbasis/credential/share_id. Dodano8regressiontests;PASS23.814s.
Nowyshare dopuszcza nowycontext,freshreportread;nieprzywracastaregojob/replay.

Własne pierwsze pełneWindowswyniki:101school,100PASS1symlinkskip148.422s;
327fullisolatedexport,326PASS1skip166.317s. Po dodaniu ósmego testu finalne
wykonanie i coverage opisane w ostatniej sekcji stage5.md. Browserresource i
accountsdesktop/phonePASS,Node7PASS/mobileflowPASS. NiezależnyLinux wynik
pochodzi od użytkownika;nie nasz. Nie maskowanoTkinter/skipa.

Codecommit:fdc06bb7efd82455ffbf00deb62a37d80c494e23. Dokumenty contract/stage5/
stages/run/AI;concrete staging,noruntime/DB/mediów/sekretów/coverage. Bezagentów/
nowychczatów,push,merge,rewrite. PUBLISH-01 osobno. Etap6nierozpoczęty.

Końcowe własne wyniki poprawki:102schooltests101PASS1skip138.013s;328fullPython
isolatedexport327PASS1skip158.144s;8newtestsPASS23.814s. CoveragebranchTrue
2198/2294linie95.8152%,614/800gałęzie76.7500%,combined90.8856%,zeroexclusions,
pełnepermodule wstage5.md. Same3pakietyetapowe,nie końcowyM8/CV/JSzakres.
Dokumenty/spójnośćUTF8/linki/PowerShellsyntax/stagednames/diffcheck sprawdzone.
Main/CVrefsniezmienione;trackedruntime/data/runsbrak. Nadalczekamy na brakującą
końcówkępromptu;odbiórpozostaje dla otrzymanegozakresu,nie nieznanychwymagań.


## Etap 5 — korekta owner management (pełny prompt)

Poniższy kompletny prompt zastępuje brakującą końcówkę poprzedniej wiadomości.

```text
etap 5 — jeszcze jedna korekta uprawnień właściciela do jobów analizy

pracuj dalej w istniejącym worktree na codex/school-app
nie zaczynaj etapu 6

najpierw przeczytaj obowiązujące AGENTS.md oraz docs/school-app/contract.md, stage5.md, stages.md, run.md i ai-usage.md

sprawdź aktualny head, git status i staging
zachowaj wszystkie niezwiązane zmiany użytkownika

przegląd dotyczy commita
20d9be8437be5977d85948cdc456bcfbf430183b

ważne — poprzedni prompt dostałeś urwany
ten prompt jest kompletnym poleceniem dotyczącym pozostałej korekty
nie trzeba ponownie pytać o brakującą część poprzedniego promptu

co już działa i czego nie ruszamy

replay i job analityka są związane z konkretnym share_id

po cofnięciu share i ponownym udostępnieniu temu samemu analitykowi stare uchwyty nie odzyskują dostępu

nowe udostępnienie pozwala tworzyć nowe konteksty, ale nie ożywia starych

job z cofniętym share nie może wykonać analizy ani opublikować wyniku na podstawie nowego share

wcześniej poprawnie opublikowany raport pozostaje danymi właściciela

te zachowania mają zostać zachowane

co jest jeszcze źle

właściciel przejazdu traci dostęp do statusu i anulowania joba utworzonego przez analityka, gdy share użyty przez tego analityka zostaje cofnięty

niezależnie odtworzono taki wynik

właściciel czyta status joba przed cofnięciem share → 200

właściciel cofa share i ponownie udostępnia przejazd analitykowi

analityk czyta stary job → 404, to jest poprawne

właściciel czyta ten sam job → 404, to jest niepoprawne

właściciel czyta wcześniej opublikowany raport → 200, to jest poprawne

przyczyna jest w job_authorize

funkcja najpierw sprawdza authorization_invalid i pierwotną podstawę wykonania joba
dopiero później rozważa dostęp właściciela

przez to nieważny share analityka blokuje również właściciela

musimy rozdzielić prawo wykonania joba od prawa zarządzania jobem

krok 1 — odtwórz problem przed poprawką

dodaj test regresyjny z rzeczywistym http i tymczasową bazą

właściciel udostępnia ukończony przejazd analitykowi

analityk tworzy job

właściciel może odczytać jego status

właściciel cofa share

właściciel nadal powinien dostać 200 przy odczycie statusu

analityk powinien dostać 404

powtórz ten scenariusz także z ponownym udostępnieniem temu samemu analitykowi

nie polegaj na wcześniejszym odczycie analityka, który przypadkowo ustawi authorization_invalid
sprawdź zachowanie zarówno przed takim odczytem, jak i po nim

zapisz wynik testu przed zmianą kodu

krok 2 — rozdziel dwie polityki

pierwsza polityka to uprawnienie wykonania joba

dotyczy workera, odczytu źródła do obliczeń oraz publikacji wyniku

nadal wymaga pierwotnej podstawy OWN albo konkretnego SHARE

dla joba utworzonego przez analityka cofnięcie pierwotnego share unieważnia wykonanie

nowy share nie zastępuje starego

właściciel czytający lub anulujący job nie może zmienić podstawy wykonania na OWN

nie wolno zmieniać actor_id, session_id, credential ani authorization joba na dane właściciela

druga polityka to uprawnienie zarządzania jobem

dotyczy get /analysis-jobs/{job_id} oraz delete /analysis-jobs/{job_id}

aktywny i uwierzytelniony właściciel parent trip może odczytać bezpieczny status oraz anulować job dotyczący jego przejazdu

to prawo nie zależy od ważności share analityka ani od authorization_invalid joba

właściciel nie przejmuje joba, nie wznawia go i nie przywraca analitykowi dostępu

pozostali użytkownicy nadal dostają 404

administrator nie ma wyjątku dla cudzych danych

analityk nadal potrzebuje właściwej sesji i credential oraz pierwotnego, nadal ważnego share

krok 3 — popraw strukturę kodu

przejrzyj job_authorize, job_read, job_cancel i execute w greenwave/school_resources/contexts.py oraz potrzebne funkcje policy.py

możesz rozdzielić obecne job_authorize na osobne funkcje wykonania i zarządzania
nazwy dobierz czytelnie

nie naprawiaj tego przez pomijanie kontroli w workerze

authorization_invalid ma oznaczać nieważność pierwotnego uprawnienia wykonania
nie może oznaczać zakazu wszystkich operacji właściciela

przy zarządzaniu najpierw sprawdź aktualną sesję, aktywny status konta i rzeczywistą własność parent trip

właściciel wynika z db
nie przyjmuj owner_id, role ani actor_id z klienta

nie używaj polityki closed=True jako powodu do odebrania właścicielowi odczytu statusu lub anulowania istniejącego joba po archiwizacji przejazdu

archiwizacja nadal blokuje wykonanie i nowe analizy
właściciel może zobaczyć stan starego joba i go anulować, dopóki jego pamięciowy uchwyt istnieje

dla niewłaściciela zachowaj aktualne ograniczenia complete, nonarchive i share

jeśli job wygasł przez ttl, został usunięty albo serwer uruchomiono ponownie, 404 pozostaje prawidłowe
nie dodawaj trwałej historii jobów ani nowych tabel tylko na potrzeby tej poprawki

krok 4 — zachowanie statusu i anulowania

właściciel powinien widzieć bezpieczne dto statusu joba również po cofnięciu share

jeżeli job był queued albo running i jego pierwotna podstawa została unieważniona, nie pokazuj go jako zdolnego do dalszej publikacji

worker i kontrole uprawnień nadal muszą doprowadzić go do cancelled

wcześniej zakończony job może nadal pokazywać complete oraz report_id, jeśli raport rzeczywiście został poprawnie opublikowany przed cofnięciem

authorization_invalid nie usuwa ani nie fałszuje takiego raportu

delete wykonywany przez właściciela ustawia anulowanie joba oczekującego lub działającego
nie zabija wątku pythona
nie przywraca uprawnienia wykonania
nie usuwa wcześniej opublikowanego raportu

dla joba już zakończonego zachowaj bezpieczne, idempotentne zachowanie anulowania i obecny kontrakt 204
nie udawaj cofnięcia już wykonanej analizy

nie dodawaj endpointu restartowania ani wznawiania starego joba
nowa analiza wymaga nowego joba

krok 5 — zachowaj zabezpieczenia publikacji

nie osłabiaj związania joba z pierwotnym share_id

zachowaj kontrole przed wykonaniem, dostępem do plików, po obliczeniu oraz przed publikacją

zachowaj synchronizację końcowej kontroli i publikacji z revoke, archive oraz zmianami security_version

odczyt statusu przez właściciela nie może wpłynąć na wynik tych kontroli

nie deklaruj transakcyjnego recovery db i filesystem
to nadal osobna integracja kolejnych etapów

krok 6 — testy

dodaj testy na tymczasowej db i syntetycznych danych

właściciel odczytuje status joba analityka po revoke → 200

właściciel odczytuje status po revoke i regrant → 200

właściciel anuluje queued job analityka po revoke → 204 i brak wykonania

właściciel anuluje running job analityka po revoke → 204 i brak publikacji

właściciel zachowuje dostęp niezależnie od tego, czy analityk wcześniej wykonał żądanie ustawiające authorization_invalid

właściciel może zarządzać własnym jobem po archiwizacji trip, dopóki uchwyt istnieje

analityk nie odzyskuje starego joba po regrant → read i cancel 404

nowy job na podstawie nowego share działa

drugi kierowca i administrator wobec cudzego joba → 404

anonimowa, wygasła lub cofnięta sesja → 401

delete bez csrf lub z błędnym origin → 403

wcześniej opublikowany raport pozostaje dostępny właścicielowi

status i anulowanie przez właściciela nie zmieniają pierwotnego actor, credential, session ani authorization joba

stary replay nadal nie odzyskuje dostępu po regrant

do sterowania kolejką i obliczeniem używaj event lub barrier
nie opieraj testów na przypadkowym czasie sleep

krok 7 — regresja

uruchom wszystkie testy school_resources i school_share_contexts

uruchom regresję school_accounts, haseł i school_data

uruchom pełną regresję python w izolowanym eksporcie

ponów odpowiednie testy js oraz smoke rzeczywistego http

jeśli środowisko pozwala, ponów browser smoke desktop i phone
jeśli nie pozwala, jasno podaj blokadę

nie ukrywaj błędu brakującej biblioteki tkinter przez zmianę istniejącego testu

ponownie zmierz coverage trzech szkolnych pakietów z branch=True i raportem per moduł
nie wyłączaj nowych ścieżek

krok 8 — dokumentacja i commit

zaktualizuj stage5.md oraz contract.md

opisz osobno execution authorization i owner management authorization

usuń nieaktualne stwierdzenie, że nieważny share odbiera właścicielowi status i cancel

zaktualizuj run.md o scenariusz właściciel → status → revoke → status → cancel

uzupełnij ai-usage.md o ten pełny prompt i faktycznie wykonane działania

w stages.md wpisz wcześniejszy hash
20d9be8437be5977d85948cdc456bcfbf430183b

etap 5 oznacz jako przygotowany do końcowego odbioru
etapy 6–12 pozostają do zrobienia

zrób małe sensowne commity
staging tylko konkretnych plików

nie dodawaj runtime, db, nagrań, mailboxów, sekretów ani środowisk do gita

nie pushuj automatycznie
nie scalaj z main
nie zaczynaj etapu 6

na końcu podaj

wynik reproduktora przed i po poprawce

tabelę wyników dla owner, analyst, other driver, admin i anonymous

dowód, że owner management nie zmienia uprawnienia wykonania joba

wyniki queued, running i completed jobs

wyniki regresji i coverage oraz ograniczenia środowiska

hashe commitów i git status

krótką checklistę końcowego odbioru etapu 5

to jest całość promptu
wykonaj tę korektę do działającego i sprawdzonego końca, a potem zatrzymaj się
```

Działania AI:odtworzenie4wariantów HTTP404!=200 przed zmianą kodu;oddzielne
execution i management z aktualnym owner DB,bez zmiany tożsamości joba;
refresh queued/running doCANCELLED,completed/report_id zachowane. Nie zmieniono
pinned share,końcowej transakcji publikacji,migracji,loggera,solvera ani live gate.
Dodano6regressiontests zEvent i snapshotem4niezmiennychpól;14sharetestsPASS48.536s.
Pełna regresja,coverage i browser wyniki są w końcowej sekcji stage5.md.
Nie proszono ponownie o urwaną końcówkę;ten prompt jest kompletny.
Bez innychczatów/agentów,prywatnych danych,push/merge/rewrite. Etap6nierozpoczęty.


Wyniki faktyczne końcowej korekty:reproducer przed1test/4subTestFAIL404!=200,
3.255s;poPASS3.779s. 14sharetestsPASS48.536s;108schooltests107PASS1skip195.816s;
334fullisolatedtests333PASS1skip221.207s. Windows symlinkskipWinError1314,junction
PASS,Tkinterbezbłędu,bezLinuxclaim. Browserresource i accountsdesktop/phonePASS,
Node7PASS/mobileflowPASS. ActualHTTPownerstatus/cancelmatrixprzeszedł.
Coverage3pakietówbranchTrue2219/2313linie95.9360%,621/808gałęzie76.8564%,combined
90.9965%,zeroexclusions;pełnypermodule stage5.md,nie końcowyM8/CV/JSwynik.
Codecommit5ce716c28c1014e97ec19f058c870fa1c9925984;docscommitpodanywodpowiedzi.
Kontrola dokumentów,PowerShellsyntax i stageddiffnames;bezDB/runtime/sekretów,
bezmain/CVchanges/push/merge,rewrite. Etap5przygotowany do końcowego odbioru;
6–12Dozrobienia. Ten kompletnyprompt zamknąłkwestięurwanejwiadomości.

## Etap 6 — 2026-10-13: zapis domeny i recovery

Akceptacja etapu 5 w poleceniu użytkownika:
**13858b06051a4183bfc7e0559962611c8be2eae2**.
Poniżej pełna treść promptu etapu 6 (bez dopisywania niewydanych zgód):

```text
dobra to teraz etap 6 — przejazdy, obserwacje, korekty, udostępnianie i trwały zapis

etap 5 zaakceptowany po niezależnym przeglądzie i testach

zaakceptowany commit
13858b06051a4183bfc7e0559962611c8be2eae2

kontynuuj w istniejącym worktree na codex/school-app
implementuj etap 6 do działającego i sprawdzalnego końca
nie kończ na planie i nie zaczynaj etapu 7

najpierw przeczytaj obowiązujące AGENTS.md oraz docs/school-app/contract.md, stage3.md, stage4.md, stage5.md, stages.md, run.md i ai-usage.md

sprawdź aktualny head, git status i staging
zachowaj niezwiązane zmiany użytkownika

zasady

nie zmieniaj main ani codex/vision-camera

nie czytaj prywatnego data/runs/ ani starego runtime/school/

używaj jawnego nowego runtime root i syntetycznych danych

nie importuj starych nagrań ani kont

nie zmieniaj zastosowanych migracji
jeśli schema wymaga zmiany, dodaj kolejną numerowaną migrację

trwałe czasy i zaufany actor używają integer utc epoch milliseconds
dotychczasowy logger i jego format czasów pozostają zgodne z istniejącym kontraktem raw
konwersję między tymi warstwami rób jawnie na granicy adaptera

nie zmieniaj formatu raw.csv, metadata.json i complete.json

nie zmieniaj solvera, predykcji ani warunków rekomendacji live

nie osłabiaj polityki kont, csrf, własności danych i powiązania kontekstów z konkretnym share

nie przepisuj historii, nie pushuj i nie scalaj automatycznie

krok 1 — ustal dokładny zakres implementacji

porównaj aktualny kod z zaakceptowanym kontraktem

w tym etapie implementujemy

tworzenie przejazdów

edycję dozwolonych metadanych

archiwizację

zapis obserwacji i osobnych korekt

udostępnienie i cofnięcie udostępnienia

pełne filtrowanie i paginację dwóch zbiorów kierowcy

koordynację db, loggera i manifestów oraz recovery

nie implementujemy docelowych tabel ui, administracji, nowej nawigacji, parowania androida ani uruchamiania kamery

dla sprawdzenia zapisu udostępnij minimalny autoryzowany scenariusz nagrywania syntetycznego zgodny z docelowym kontraktem navigation

jeśli wymaga to podłączenia części endpointów planowanych wcześniej na etap 9, opisz dokładnie tę zależność i zrealizuj tylko konieczny zakres simulation start i finish

nie dodawaj publicznego endpointu testowego ani drugiego konkurencyjnego api nagrywania

pełne live, telefon, sterowanie nawigacją i cv pozostają na etap 9

krok 2 — serwis operacji i endpointy

dodaj czytelną warstwę usług zapisujących dane
http adapter ma walidować i mapować odpowiedź, a nie zawierać całą logikę domenową

implementuj endpointy kontraktu dla

create trip

edit title i note z expected_revision

archive zamkniętego trip

create observation

append correction

share complete trip z aktywnym analitykiem

revoke konkretnego share

własność i actor zawsze z aktualnej sesji i db
nie z body, query ani nagłówka klienta

wszystkie browser mutations wymagają csrf i dokładnego origin

waliduj każde pole, typ, długość, enum i revision
odrzucaj nieznane i duplikowane pola, bool zamiast liczby, nan i infinity

brak konta → 401
cudze lub nieistniejące prywatne id → 404
konflikt revision lub stanu → 409
błąd formularza → 422

zachowaj neutralne błędy, request_id i bezpieczne dto

krok 3 — przejazdy

nowy trip ma właściciela, tytuł, notatkę, tryb i dozwoloną wersję trasy zgodnie z kontraktem

edycja zmienia wyłącznie dozwolone metadane
nie pozwala zmienić owner, raw_ref, hashów, czasu przejazdu ani statusu przez dowolny patch

expected_revision obowiązkowe
dwa równoległe zapisy tej samej revision nie mogą oba przejść

archiwizacja tylko stanów dozwolonych kontraktem
nie usuwa raw ani raportów
cofa share i blokuje nowe analizy oraz replay tego przejazdu

właściciel nadal widzi archiwum
zarządzanie istniejącymi jobami przez właściciela działa zgodnie z poprawką etapu 5

nie dodawaj fizycznego delete ani restore archiwum poza ustalonym v1

krok 4 — obserwacje i korekty

obserwacja należy do trip
własność wynika z parent trip

zachowaj rozróżnienie STATE_SEEN i STATE_START
UNKNOWN nie może być STATE_START

czas otrzymania nadaje serwer
czas pomiaru jest osobnym polem i może być null

retrospektywna adnotacja zamkniętego przejazdu ma measured_at=null i jawne oznaczenie historyczne
nie udaje obserwacji wykonanej podczas jazdy
nie dopisuje nic do zakończonego raw

publiczny formularz ręcznej obserwacji nie może podszyć się pod source CV
source CV pozostaje dla zaufanego adaptera przyszłej integracji

korekta jest nowym wpisem
zawiera autora, czas serwera, powód, before, after i revision

zmienia tylko state, event_type i valid zgodnie z kontraktem
nie zmienia gps, źródła, czasów, trip ani raw

lista pokazuje oryginał i efektywną wartość
filtrowanie koloru, typu i valid dotyczy efektywnej wartości

zachowaj triggery niezmienności
techniczna aktualizacja journaling nie może przy okazji zmieniać oryginalnych faktów

krok 5 — udostępnianie

właściciel może udostępnić jeden complete niearchiwalny trip jednemu aktywnemu analitykowi przez dokładny email

jedno uprawnienie READ_ANALYZE
brak eksportu i cv dla analityka
brak globalnego dostępu administratora

odbiorca nie może dostać informacji o innych kontach przez publiczną wyszukiwarkę
stosuj neutralny błąd odbiorcy i limit prób zgodnie z kontraktem

cofnięcie wymaga expected_share_id
powtórzenie cofnięcia tej samej zgody jest bezpieczne
stare żądanie nie może cofnąć nowszego share z innej karty

po revoke lub archive stare replay i job analityka tracą dostęp
regrant nie ożywia starych kontekstów

właściciel zachowuje odczyt statusu i anulowanie istniejących jobów

podłącz zmiany uprawnień do kontekstów
queued i running jobs nie mogą publikować na cofniętej zgodzie
nie opieraj całego mechanizmu tylko na tym, że analityk kiedyś wykona następne żądanie

nie zmieniaj pierwotnej podstawy wykonania joba na OWN przez działanie właściciela

krok 6 — pełne listy i filtry

przejazdy kierowcy

filtry daty utworzenia, trasy, statusu i archived
jawny scope own lub shared
sortowanie zgodne z kontraktem

obserwacje kierowcy

lista ze wszystkich jego przejazdów, bez obowiązkowego trip_id
opcjonalne filtry trip, trasy, sygnalizatora, daty, efektywnego koloru, efektywnego typu zdarzenia, source i valid
scope own lub shared zgodnie z uprawnieniami

nie skanuj globalnych nagrań
listy wynikają z autoryzowanych rekordów db

daty api zgodnie z contract.md — utc RFC3339 z wymaganą strefą
backend przelicza je na integer ms
from inclusive, to exclusive
from < to i maksymalny zakres zgodny z kontraktem

dotychczasowy format query w ms z etapu 5 był rozwiązaniem przejściowym
zaktualizuj klienty testowe i dokumentację
nie utrzymuj dwóch niejednoznacznych formatów tego samego pola

implementuj keyset cursor zgodny z actor, scope, filtrami i sortowaniem
cursor podpisany hmac, z ttl i stabilnym tie-breaker id
limit domyślny 25, maksymalny 100

inny actor, zmieniony filtr, sortowanie, uszkodzony lub wygasły cursor → odmowa
dostęp do share sprawdzaj na każdej stronie

nie zamrażaj uprawnień w cursorze
nie deklaruj pełnego snapshotu wszystkich zmiennych rekordów, jeśli implementacja go nie zapewnia
opisz zachowanie przy korektach lub archiwizacji między stronami

listy nie mogą ucinać całej historii do pierwszych 500 lub 10000 rekordów

krok 7 — idempotency i audyt

zachowaj kontrakt idempotency dla operacji, które go wymagają

ten sam klucz, actor i payload → ten sam wynik bez duplikatu
ten sam klucz z inną treścią → 409

obejmij szczególnie start, finish, zapis obserwacji i korektę
pozostałe mutacje zabezpiecz revision lub identyfikatorem konkretnego zasobu zgodnie z kontraktem

audyt zapisuje actor, action, resource, czas, powód tam gdzie wymagany i request_id

nie zapisuje haseł, raw tokenów, kopii gps ani payloadów poczty

dane i ich audyt zapisuj w jednej transakcji tam, gdzie oba są w sqlite

krok 8 — koordynator nagrywania

wykorzystaj istniejący RunLogger przez adapter z jawnym autoryzowanym root

jedna aktywna sesja nagrywania na deployment
równoległy start drugiego użytkownika daje 409 bez ujawnienia właściciela

start

db intent i rezerwacja
kontrolowany run-root
utworzenie loggera i plików
przejście do recording po poprawnym przygotowaniu

finish

przejście do finalizing
zakończenie raw
istniejący poprawny manifest i hashe
sprawdzenie plików
complete dopiero po rzeczywistym sukcesie

nie fabrykuj complete.json
nie uznawaj trip za complete tylko na podstawie przesłanych hashów

manual observation w aktywnym nagraniu

db event i trwała intencja
journal do raw z kontrolowanym source_event_id
retry i recovery nie tworzą duplikatu

jeśli drugi magazyn zawiedzie, zachowaj zapisany fakt i jawny journaling status
nie odpowiadaj fałszywym sukcesem obu zapisów

do poprawnego flush i finalizacji użyj istniejących interfejsów
jeżeli potrzebujesz małego rozszerzenia loggera, zachowaj format i kompatybilność istniejących nagrań oraz dodaj regresję

krok 9 — recovery i cofnięcie sesji

przy startup nowy boot i recovery tylko nowego szkolnego runtime

nie wznawiaj jazdy ani świeżości ostatniego gps
nie uruchamiaj automatycznie kamery

aktywny trip bez prawidłowego complete manifest → interrupted
prawidłowy manifest po utracie ostatniego db commit → kontrolowane complete i audyt recovery

niedokończone intencje rozstrzygaj idempotentnie
pliki bez zaufanego powiązania nie stają się dostępne kontom

nie zmieniaj zakończonych raw
nie naprawiaj integralności przez przeliczenie hashów uszkodzonego źródła

logout, logout-all, reset i zmiana hasła mają zakończyć podłączone nagrywanie odpowiedniej sesji

przyszła blokada i zmiana roli muszą mieć wspólny punkt integracji
nie dodawaj teraz panelu administracji

techniczna finalizacja po utracie sesji działa jako ograniczona operacja systemowa z audytem
nie wymaga ponownego uzyskania uprawnień użytkownika
nie daje nikomu dodatkowego dostępu do danych

opisz gwarancje przy awarii db, pliku i procesu
nie obiecuj jednej transakcji obejmującej sqlite i filesystem

krok 10 — testy

testy jednostkowe i integracyjne http, prawdziwa tymczasowa sqlite i syntetyczne pliki

create, edit, archive, observations, corrections, share i revoke
restart i trwałość
actor spoofing, cudze id, role i csrf
konkurencyjne revision i idempotency
oryginały raw oraz obserwacji niezmienione po korekcie
historyczna adnotacja nie dopisuje do complete raw
source CV nie może pochodzić z ręcznego formularza

wszystkie filtry obu list
daty na granicach, różne strefy i zmiany czasu Europe/Warsaw
cursor przy jednakowych timestampach, nowych rekordach, zmienionych filtrach, innym actorze, expiry i cofniętym share
paginacja całej historii bez sztucznego ucięcia

start i finish
równoległa rezerwacja
błędy db i filesystem na kolejnych granicach operacji
awaria po utworzeniu manifestu przed db commit
restart z pending intents
brak duplikatu manual event po retry i recovery
logout lub reset podczas aktywnego nagrania
bezpieczna finalizacja po revokacji

revoke → regrant nadal nie ożywia starych replay i jobs
właściciel nadal zarządza jobem
eksport zakończonego przejazdu działa i przechodzi sprawdzenie integralności

steruj wyścigami przez event i barrier
nie opieraj wyniku na przypadkowym sleep

uruchom nową suite oraz regresję kont, danych i zasobów
pełna regresja w izolowanym eksporcie
odpowiednie testy js i smoke prawdziwego http

zmierz coverage szkolnych pakietów z branch=True, per moduł
nie wyłączaj trudnego recovery i io
wynik etapowy nie zastępuje końcowego szerokiego zakresu M8/CV i js

krok 11 — ręczny scenariusz odbioru

zapewnij powtarzalny scenariusz na nowym syntetycznym root

login
create trip
start simulation recording
manual observation
finish
read i export
edit metadata
correction
filters i pagination
share analitykowi
revoke
archive
restart i read

scenariusz może być skryptem używającym rzeczywistego http i sesji
nie musi jeszcze mieć docelowych tabel ui

nie podawaj hasła w argv i nie loguj tokenów
fixtures nie mogą stać się publicznym provisioning api

krok 12 — dokumentacja i commity

dodaj docs/school-app/stage6.md

opisz działające endpointy, jednostki czasu, cursory, idempotency, koordynację zapisu, recovery i ograniczenia

zaktualizuj contract.md tylko o konieczne doprecyzowania
nie zmieniaj ustalonych ról i zakresu v1

zaktualizuj run.md oraz readme, jeśli zmieniły się komendy

uzupełnij ai-usage.md o ten prompt i faktyczne działania

w stages.md oznacz etap 5 jako zaakceptowany z hashem
13858b06051a4183bfc7e0559962611c8be2eae2

etap 6 przygotowany do odbioru po testach
etapy 7–12 nadal do zrobienia

dziel pracę na małe sensowne commity
staging konkretnych plików
żadnych db, runtime, nagrań, mailboxów, sekretów ani środowisk w git

nie pushuj automatycznie
nie scalaj z main

na końcu podaj

co działa i co zostało na etap 7–9

listę endpointów oraz pola formularzy

wyniki zapisu, korekt, filtrów, cursorów i udostępniania

wyniki awarii, restartu i finalizacji po revokacji

wyniki testów, coverage i blokady środowiska

dokładne komendy oraz ręczny scenariusz odbioru

hashe commitów i git status

to jest całość promptu
doprowadź etap 6 do działającego i sprawdzonego końca, potem zatrzymaj się przed etapem 7
```

Działania AI: przegląd kontraktu i kodu przy zgodnym, czystym HEAD etapu 5;
nowa migracja 0003 bez zmian zastosowanych 0001/0002; atomowe jednostki danych/audytu;
warstwa writes/lists/paging/raw/recording; jawne trasy HTTP i minimalny SIM start/finish;
kontrolowany RunLogger run_id i close_unfinished z zachowaniem formatu; callbacks
credentials i watchdog; proaktywne cofanie kontekstów; skrypt rzeczywistego HTTP;
25 testów etapu 6 i adaptacja regresji do aktualnej schema/API.
Nie odtwarzano portalu z historii. Nie delegowano pracy do agentów/innych czatów.

Weryfikacja AI: nowe syntetyczne TemporaryDirectory i izolowane eksporty; HTTP z
cookies/CSRF i realną SQLite; Event/Barrier dla wyścigów; celowe błędy DB/filesystem,
manifestów i restart; kontrola oryginałów raw oraz immutable triggerów. Test paginacji
odczytał 10007 rekordów. Rzeczywisty CLI świeżej bazy/upgrade v2/backup/restore,
serwer z produkcyjnym scrypt oraz ręczny skrypt i restart/read PASS. Getpass przy
unattended teście Windows wstrzyknięty ze stdin tylko w procesie testowym, bez hasła
w argv, logach ani osłabienia KDF. Nie wysyłano maili do prawdziwych osób.

Końcowy kod bf6af53f72365cdb95523db40f9fb48b0d0a1fe1:
133 szkolne testy (132 PASS, 1 skip), 309.084 s; pełny izolowany Python zestaw
359 testów (358 PASS, 1 skip), 329.174 s. Skip POSIX symlink WinError 1314;
Windows junction PASS. Tkinter dostępny, bez ukrywania błędu. Node 7/7 i mobile_flow
PASS; browser resources i pełny accounts SMTP flow desktop/phone PASS z realnym KDF.
Bazowy GreenWave smoke HTML/state 200 w osobnym eksporcie. Linux, Docker, telefon,
ADB, prawdziwa kamera i YOLO nie były wykonywane jako dowód tego etapu.

Coverage branch=True: cztery całe szkolne pakiety 2701/2837 linii, 765/1030 gałęzi,
combined 89.6302%. Dodatkowo cały zmieniony telemetry: 2784/2970 linii,
771/1060 gałęzi, combined 88.2134%. Zero excluded lines. Pełny per-module raport
w stage6.md, lokalny JSON ignorowany. Nie jest to końcowy szeroki pomiar M8/CV/JS.
Pierwsze nieudane próby i ich poprawki ujawniono w stage6.md, nie przemilczano ich.

AI zmieniło kod i dokumentację; wynik wymaga końcowego przeglądu użytkownika.
Dowody, gwarancje i granice (bez jednej transakcji DB–filesystem, bez wznowienia
jazdy/GPS po restart) są w stage6.md; dokładne komendy w run.md sekcja 11.
Staging wyłącznie konkretnych plików, bez danych/runtime/sekretów, bez zmian
main/vision-camera, push, merge lub rewrite. PUBLISH-01 pozostaje otwarty.
Etap 6 przygotowany do odbioru; 7–12 Do zrobienia i nie rozpoczęte.

Kontrola końcowych dokumentów: UTF-8/fences/odnośniki oraz 35 bloków PowerShell PASS.
Zastosowane migracje bez diff, niezmienione refs main/vision-camera, brak śledzonych
runtime/data-runs. Przejrzano konkretne nazwy staged plików oraz git diff --cached
--check przed commitem dokumentacji. Hash tego commita w końcowej odpowiedzi.

## Etap 6 — poprawka nieudanego startu, 2026-10-13

Przegląd dotyczył **4d30c8bec1586604313a838413e6fc64818f7ae7**.
Pełny prompt użytkownika (zachowano treść, pominięto końcowe spacje w wierszach):

```text
poprawa etapu 6 — naprawa nieudanego startu nagrywania i końcowy odbiór

kontynuuj w istniejącym worktree codex/school-app
nie zaczynaj etapu 7

przeczytaj obowiązujące AGENTS.md oraz docs/school-app/contract.md, stage6.md, stages.md, run.md i ai-usage.md

przegląd dotyczył commita
4d30c8bec1586604313a838413e6fc64818f7ae7

sprawdź aktualny head, status i staging
zachowaj niezwiązane zmiany użytkownika

nie zmieniaj main ani codex/vision-camera
nie czytaj prywatnego data/runs/ ani starego runtime/school/
wszystkie próby na nowych syntetycznych danych
nie zmieniaj solvera, formatu loggera ani warunków rekomendacji live
nie przepisuj historii, nie pushuj i nie scalaj automatycznie

co zostało znalezione

Recording.start najpierw zapisuje w db przejazd STARTING oraz PENDING START

potem przygotowuje ścieżkę przez storage.run i tworzy RunLogger

ten fragment jest przed try obsługującym nieudany start

jeśli przygotowanie ścieżki lub loggera zgłosi wyjątek, request kończy się błędem, ale przejazd pozostaje STARTING

globalna rezerwacja pozostaje zajęta mimo braku nagrywania

dokładny niezależny reproduktor

utwórz nowy trip SIMULATION

na czas POST /school/api/v1/navigation wstrzyknij OSError z storage.run
błąd ma wystąpić po zatwierdzeniu intencji START w db

wynik obecnego kodu

start → 503
trip → STARTING
po usunięciu wstrzykniętej awarii start drugiego trip → 409

restart może odzyskać stan, ale zwykły błąd startu nie powinien wymagać restartowania całego serwera

krok 1 — test przed poprawką

dodaj test integracyjny rzeczywistego http z tymczasową db

odtwórz dokładnie powyższy przypadek

potwierdź, że błąd występuje po zapisaniu intencji, a nie przed rezerwacją

test oczekuje docelowo

pierwszy start → neutralny błąd 503
pierwszy trip → INTERRUPTED
jego pending START → FAILED
brak aktywnego kontekstu i otwartego loggera
start drugiego trip po ustąpieniu awarii → 201 bez restartu serwera

zapisz wynik testu przed poprawką

krok 2 — obejmij cały start obsługą błędów

przejrzyj Recording.start w greenwave/school_records/recording.py

obsługa nieudanego startu ma obejmować cały fragment po zatwierdzeniu db intent

przygotowanie bezpiecznej ścieżki

konstrukcję loggera

utworzenie i rejestrację kontekstu

utworzenie plików

pierwsze append i flush

przejście db do RECORDING oraz START APPLIED

nie zakładaj, że logger lub ctx już istnieje
inicjalizuj je jawnie albo zastosuj równoważną czytelną strukturę

cleanup nie może zgłosić błędu przez odwołanie do nieutworzonego loggera

zachowaj kontrolę sesji przed przejściem STARTING → RECORDING

błąd przed zatwierdzeniem rezerwacji nie może tworzyć plików ani fałszywego audytu przerwanego nagrania

krok 3 — cleanup po nieudanym starcie

jeżeli logger powstał, zamknij go bez fabrykowania complete.json

usuń lub unieważnij częściowo zarejestrowany kontekst
nie usuwaj dowodów zapisu ani nie nadpisuj plików

jeżeli db działa

atomowo ustaw właściwy trip na INTERRUPTED

oznacz jego niezakończoną intencję START jako FAILED

zapisz audyt systemowy nieudanego startu

zwolnij globalną rezerwację przez poprawny stan db

nie oznaczaj innych przejazdów ani operacji jako failed

nie pozostawiaj loggera otwartego, nawet jeśli zapis stanu błędu w db zgłosi wyjątek

cleanup powinien zachować diagnostykę przyczyny bez ujawniania ścieżek, sekretów lub treści danych w publicznej odpowiedzi

krok 4 — gdy db zawiedzie również podczas cleanup

nie udawaj, że globalna rezerwacja została zwolniona, jeśli nie zapisano tego w db

zachowaj trwałą intencję oraz informację potrzebną do ponowienia cleanup

zapewnij kontrolowane ponowienie w działającym procesie po ustąpieniu awarii db
nie opieraj go wyłącznie na obecności aktywnego ctx, bo błąd mógł wystąpić przed jego utworzeniem

dopiero po poprawnym cleanup kolejny start może dostać 201

zachowaj startup recovery jako zabezpieczenie po awarii procesu

nie wznawiaj automatycznie nieudanego nagrania
retry tego samego nieudanego START nie tworzy kolejnego runu ani nie udaje sukcesu
nowy start odbywa się na nowym PLANNED trip zgodnie z dotychczasowym kontraktem

ponowienie cleanup ma być idempotentne
nie dopisuj tego samego audytu przy każdym przebiegu watchdog

jeśli potrzebna jest niewielka zmiana architektury cleanup, opisz ją
nie dodawaj publicznego endpointu naprawczego

krok 5 — testy granic awarii

dodaj testy dla

storage.run zgłasza OSError po commit intencji

konstrukcja RunLogger zgłasza wyjątek

błąd po rejestracji ctx, przed utworzeniem plików

błąd po częściowym utworzeniu plików

błąd podczas przejścia do RECORDING

błąd podczas zamykania częściowego loggera

db cleanup zawodzi, następnie db odzyskuje sprawność i cleanup zostaje ponowiony bez restartu

restart po nieudanym cleanup rozstrzyga pozostałą intencję

kolejny użytkownik może wystartować po poprawnym cleanup

równoległe poprawne starty nadal dopuszczają tylko jedną aktywną sesję

retry tego samego nieudanego startu nie tworzy duplikatu

brak fałszywego complete.json oraz brak utraty zapisanych plików

sesja cofnięta podczas startu nie może przejść do RECORDING

do sterowania wyścigami używaj event lub barrier
nie uzależniaj poprawności testu od przypadkowego sleep

nie osłabiaj containment, blokady procesu, polityki sesji ani rezerwacji sqlite

krok 6 — regresja

uruchom wszystkie test_school_records.py

uruchom całą szkolną suite

uruchom pełną regresję python w izolowanym eksporcie

ponów testy js i rzeczywisty http scenariusz zapisu

ponownie zmierz coverage szkolnych pakietów oraz telemetry tak jak w etapie 6
branch=True, per moduł, bez wyłączania nowych ścieżek błędów

brak tkinter albo przeglądarki raportuj jako ograniczenie środowiska
nie ukrywaj testów i nie deklaruj sprawdzeń, których nie wykonano

krok 7 — dokumentacja i commity

zaktualizuj stage6.md

opisz przyczynę, rozwiązanie oraz zachowanie przy działającej i niedostępnej db

doprecyzuj run.md o ręczny odbiór nieudanego startu, jeśli jest potrzebny

uzupełnij ai-usage.md o ten pełny prompt i faktyczne wyniki

w stages.md wpisz wcześniejszy hash
4d30c8bec1586604313a838413e6fc64818f7ae7

etap 6 oznacz jako przygotowany do ponownego odbioru
etapy 7–12 nadal do zrobienia

małe sensowne commity
staging konkretnych plików

żadnych runtime, db, nagrań, mailboxów, sekretów i środowisk w git

nie pushuj automatycznie
nie scalaj z main
nie zaczynaj etapu 7

na końcu podaj

wynik dokładnego reproduktora przed i po poprawce

stany trip i START intent po każdej granicy awarii

dowód, że kolejny trip startuje bez restartu po ustąpieniu błędu

dowód zamknięcia loggera i braku osieroconego aktywnego kontekstu

wynik cleanup retry oraz startup recovery

wyniki regresji i coverage

hashe commitów, git status i ograniczenia

to jest całość promptu
doprowadź poprawkę do działającego i sprawdzonego końca, potem zatrzymaj się przed etapem 7
```

Działania AI: potwierdzono czysty HEAD i staging zgodny z przeglądem. Przeczytano
obowiązujący pusty AGENTS oraz dokumentację. Dodano dokładny reproduktor HTTP
storage.run po commit intencji; przed zmianą FAIL (503, STARTING, PENDING, 409)
zamiast oczekiwanego (503, INTERRUPTED, FAILED, 201), 1 test, 3.231 s.
Po zmianie dokładny test PASS, 3.176 s. Nie dodano odczytu/poprzedniego recovery
mogącego ukryć błąd. Baza i pliki tylko z nowego TemporaryDirectory.

Przeniesiono przygotowanie ścieżki/loggera/kontekstu do obsługi błędów po intent.
Dodano oddzielne failed_starts i idempotentny cleanup z watchdog/start/shutdown.
Logger zamykany przed transakcją cleanup, z fallback do uchwyconego stream;
kontekst natychmiast usuwany. Trip, konkretna START i audyt systemowy aktualizowane
atomowo; niedostępna DB zachowuje rezerwację i retry niezależnie od aktywnego ctx.
Diagnostyka tylko klas wyjątków, bez ścieżek/sekretów/payloadów. Zachowano startup
recovery i kontrolę sesji przed RECORDING. Wrapped OSError RunLoggera mapowany na
neutralne 503 bez zmiany loggera/formatu. Nie zmieniono schematu ani migracji.

Dodano 10 testów (część z wieloma subTest) rzeczywistego HTTP dla granic filesystem,
loggera, transakcji, cleanup DB, zamykania stream, watchdog, restart, retry i
revokacji podczas startu. Wyścigi Event/Barrier, nie sleep. Sprawdzane są stany,
zamknięte stream, brak active context, zachowanie plików i pojedynczy audyt.
Wstępny zestaw 9 testów PASS 35.141 s, po nim dodano realne częściowe I/O/append.
Wyniki: 35 records PASS 140.332 s, 143 szkolne (142 PASS, 1 skip) 360.229 s.
Coverage branch=True/zero exclusions: cztery pakiety 2740/2876 linii, 776/1042 gałęzi,
combined 89.7397%; z telemetry 2831/3009 linii, 784/1072 gałęzi, combined 88.5812%.
Pełny per-module raport w końcowej sekcji stage6.md. Node 7/7 i mobile_flow PASS,
browser accounts/resources desktop i phone PASS. Rzeczywisty HTTP scenariusz
zapisu/restart z test_school_records PASS. Pełna regresja w izolowanym eksporcie commita kodu: 369 testów (368 PASS, 1 skip),
393.470 s.
Kod: 1827dd8dfdf2d930bf610c84786c1ddded5553dc.
Bez subagentów/innych czatów, prywatnych danych, push/merge/rewrite lub etapu 7.

Końcowe kontrole: kod eksportu zgodny bajtowo z poprawionymi plikami, UTF-8/fences/
odnośniki oraz 38 bloków PowerShell PASS, migracje bez zmian, main/vision-camera
niezmienione, staged wyłącznie cztery konkretne dokumenty. Jedyny skip Windows
symlink WinError 1314, junction PASS; Tkinter i browser działały. Linux, Docker i
sprzęt nie były wykonane. Bez runtime/DB/mailboxów/sekretów w Git, push/merge/rewrite.
Etap 6 przygotowany do ponownego odbioru; nie rozpoczęto etapu 7.
