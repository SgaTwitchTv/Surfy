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
