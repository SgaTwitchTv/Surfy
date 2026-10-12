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
