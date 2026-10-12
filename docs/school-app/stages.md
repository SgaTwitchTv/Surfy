# Rejestr etapów GreenWave School

Data rozpoczęcia ponownego procesu: 2026-10-12.
„Zweryfikowany” oznacza wykonanie sprawdzeń etapu; osobna akceptacja użytkownika
nadal jest konieczna przed przejściem dalej. Wcześniejszy prototyp nie zatwierdza
etapów 2–12. Nie wykonujemy następnego etapu bez kolejnego promptu.

## Commity i aktualny proces

Etap 1 zaakceptowany przez użytkownika po przeglądzie dokumentacji na GitHubie.
Literalny hash audytu: **bb99de3d808db8898426b42203e6c5e979e527be**.
Po audycie użytkownik utworzył a9f7259; później na jego polecenie kod prototypu
przywrócono lokalnie do 7ece859 bez commita. Te zmiany nie są częścią etapu 2
ani jego commita dokumentacyjnego i pozostają zachowane.

Commit etapu 2 jest pierwszym commitem dodającym contract.md. Pełny trwały hash:

```powershell
git log --diff-filter=A --format=%H -- docs/school-app/contract.md
```

Referencja pozwala wskazać własny commit bez niemożliwego wpisania jego przyszłego
hasha do własnej treści. Pełny hash jest także w końcowej odpowiedzi etapu 2;
przy następnym etapie wpisujemy go literalnie do tego rejestru.

| Etap | Zakres | Status | Commit | Dowody sprawdzenia | Blokady / następny krok |
|---|---|---|---|---|---|
|1|Audyt i worktree|Zweryfikowany i zaakceptowany przez użytkownika|bb99de3d808db8898426b42203e6c5e979e527be|Baza/status;226 Python;7 Node+mobile_flow;2 browser E2E;capture smoke;4 Android+APK;bazowe coverage85.9985%;audit.md|Docker CLI brak;YOLO/telefon/droga nieodebrane;wynik tylko bazy|
|2|Kontrakt aplikacji|Zweryfikowany dokumentacyjnie; oczekuje przeglądu/akceptacji użytkownika|Pierwszy commit contract.md; pełny hash przez polecenie powyżej|Przegląd prototypu z a9f7259;3 niezgodności potwierdzone w syntetycznej DB;74 endpointy/45 mutacji z ochroną;kontrola tabel/scopes/legacy/formularzy;zastany diff identyczny|D1–D7 do przeglądu;SMTP i lease to propozycje, nie gotowe funkcje;STOP przed etapem3|
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

Kontrakt etapu 2: [contract.md](contract.md).

Źródła dowodów oraz rozróżnienie błędów kodu, zależności i pominięć:
[audit.md](audit.md). Jawność promptów: [ai-usage.md](ai-usage.md).
