# GreenWave — audyt rozszerzenia szkolnego

Baza: 7ece859 (codex/vision-camera). Data: 2026-10-12.
Problem: płynny przejazd przez kolejne światła z poszanowaniem limitów wymaga
wiarygodnych faz, linii zatrzymania i pozycji. Nieznane dane oznaczają brak rady.
Kamera jest diagnostyką, a konto użytkownika nie stanowi dowodu jakości faz.

| # | Wymaganie | Stan bazy / luka | Dowód odbioru |
|---|---|---|---|
|1|Problem domenowy|README opisuje laboratorium; dodać opis w portalu|UI i raport|
|2|Konta i reset|brak; token lokalny to nie konto|test sesji, resetu i wylogowania|
|3|Trzy role|brak|test macierzy uprawnień HTTP|
|4|Własność danych|lokalny wspólny storage|próby dostępu do cudzych ID|
|5|Dwie tabele|historia bez właścicieli|filtry przejazdów i obserwacji|
|6|Responsywny UI|eksperymentalna nawigacja i laboratorium|Playwright desktop/mobile, zrzuty|
|7|Walidacja|istniejąca domenowa; brak formularzy kont|granice i błędne payloady|
|8|Rekordy i korekty|surowe logi append-only|oddzielny audyt korekt, niezmienny oryginał|
|9|AJAX|fetch już istnieje|test przepływu bez przeładowania|
|10|Architektura i bezpieczeństwo|lokalny HTTP; brak kont|migracje, CSRF, cookie, hashe|
|11|Commity|baza CV|oddzielna gałąź i commity etapów|
|12|AI|brak dokumentu szkolnego|jawny dziennik promptów i weryfikacji|
|13|Docker demo|brak Docker CLI na komputerze|build/start/smoke w kontenerze wymagany|
|14|Testy i 70%|testy istnieją; brak pomiaru zakresu szkolnego|raport coverage z jawnym zakresem|
|15|Raport i zrzuty|dokumenty M8/CV|raport i obrazy z rzeczywistego UI|
|16|Źródła i instrukcja|README bazy|reprodukowalne polecenia testów i demo|

## Kontrakt kont i danych

SQLite w osobnym katalogu runtime; wersjonowane migracje. Samorejestracja zawsze
nadaje rolę DRIVER. ANALYST czyta przejazdy i obserwacje wszystkich użytkowników
oraz dopisuje korekty. ADMIN dodatkowo zarządza kontami/rolami i ma dostęp do
istniejącego lokalnego laboratorium (wspólny proces badawczy). Kierowca widzi,
tworzy i opisuje wyłącznie swoje przejazdy i obserwacje; korekty własnych obserwacji
są dopisywane. Nikt przez portal nie edytuje raw.csv. Stare nagrania nie są
przypisywane automatycznie, kopiowane ani udostępniane kierowcom.

Sesja: losowy sekret, hash w DB, cookie HttpOnly/SameSite, czas wygaśnięcia,
CSRF przy mutacjach, unieważnienie po resecie hasła. Hasła scrypt z losową solą.
Reset: jednorazowy losowy token z krótkim TTL, hash w DB; odpowiedź nie zdradza
istnienia konta. Dostarczenie linku poza API przez prywatny kanał administracyjny
(CLI), bez wyświetlania tokenu w odpowiedzi HTTP. Ochrona przed próbami logowania.

Demo: syntetyczne dane rozdzielone według użytkowników; brak importu data/runs.
Laboratorium dotychczasowego GreenWave pozostaje osobnym widokiem administratora.
Rekomendacje live zachowują wszystkie bramki M8. Nowe konta i obserwacje portalu
nie potwierdzają automatycznie modelu faz.
