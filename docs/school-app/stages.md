# Rejestr etapów GreenWave School

Data rozpoczęcia ponownego procesu: 2026-10-12.
„Zweryfikowany” oznacza wykonanie sprawdzeń etapu; osobna akceptacja użytkownika
nadal jest konieczna przed przejściem dalej. Wcześniejszy prototyp nie zatwierdza
etapów 2–12. Nie wykonujemy następnego etapu bez kolejnego promptu.

## Commit dokumentacji etapu 1

Hash commita etapu 1 jest hashem commita, który **po raz pierwszy dodał ten
plik**. Odczyt pełnego, trwałego hasha (także po kolejnych commitach):

```powershell
git log --diff-filter=A --format=%H -- docs/school-app/stages.md
```

Taka referencja unika wpisywania nieznanego jeszcze hasha do treści jego własnego
commita. Pełny hash jest również podany w odpowiedzi końcowej etapu 1.
Dla kolejnych etapów wpisujemy tutaj literalne hashe wcześniejszych commitów.

| Etap | Zakres | Status | Commit | Dowody sprawdzenia | Blokady / następny krok |
|---|---|---|---|---|---|
|1|Audyt i worktree|Zweryfikowany; oczekuje akceptacji użytkownika|Pierwszy commit stages.md; pełny hash przez polecenie powyżej|Baza/ancestry/status; 226 Python; 7 Node + mobile_flow; 2 browser E2E; capture smoke; 4 Android + APK; rzeczywisty coverage bazy 85.9985%; audit.md|Docker CLI brak; YOLO/telefon/droga nieodebrane; zastany prototyp zachowany; STOP do następnego promptu|
|2|Kontrola aplikacji|Do zrobienia|—|—|Prompt i akceptacja etapu 1|
|3|Baza danych i migracje|Do zrobienia|—|—|Kontrakt danych, własność i przegląd zastanego storage|
|4|Konta i sesje|Do zrobienia|—|—|Kontrakt resetu i dostarczania linku|
|5|Uprawnienia i ochrona API|Do zrobienia|—|—|Jawna macierz ról i wszystkie odziedziczone endpointy|
|6|Przejazdy i obserwacje|Do zrobienia|—|—|Niezmienny raw, audyt korekt, spójność i recovery|
|7|Nowoczesny UI użytkownika|Do zrobienia|—|—|Projekt w kierunku ReactLY i odbiór wizualny|
|8|Widoki analityka i administratora|Do zrobienia|—|—|Zatwierdzone role i zakres danych|
|9|Nawigacja i responsywność|Do zrobienia|—|—|Nowy UI, regresja GPS/replay, zachowanie blokad live|
|10|Pełne testy i pokrycie|Do zrobienia|—|—|Pełny uzgodniony mianownik backendu oraz osobny pomiar JS|
|11|Docker i wdrożenie demo|Do zrobienia|—|—|Docker engine/CLI, drugi komputer, syntetyczne dane|
|12|Raport końcowy i odbiór użytkownika|Do zrobienia|—|—|Wyniki wcześniejszych etapów, screenshoty i reprodukcja|

Źródła dowodów oraz rozróżnienie błędów kodu, zależności i pominięć:
[audit.md](audit.md). Jawność promptów: [ai-usage.md](ai-usage.md).
