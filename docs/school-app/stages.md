# Rejestr etapów GreenWave School

Data rozpoczęcia ponownego procesu: 2026-10-12.
„Zweryfikowany” oznacza wykonanie sprawdzeń etapu; osobna akceptacja użytkownika
nadal jest konieczna przed przejściem dalej. Wcześniejszy prototyp nie zatwierdza
etapów 2–12. Nie wykonujemy następnego etapu bez kolejnego promptu.

## Commity i stan po doprecyzowaniu

Etap 1 zaakceptowany: bb99de3d808db8898426b42203e6c5e979e527be.
Dokumentacyjny etap 2: **3ff54d9d3c4a7dfb23b53db9095f69f1112427f0**.
3476d133006a948887899e8b75dcc210ce084248 zatwierdził usunięcie prototypu
zgodnie z decyzją użytkownika, ale dodał runtime. Nie odtwarzamy prototypu.

Doprecyzowanie etapu 2 obejmuje dwa commity:

1. **7a2899770075cc6ac12c826234f620f1de97a380** — ignore i wycofanie 7 runtime
   paths tylko z indeksu; lokalne pliki zachowane. Stara historia nadal je zawiera.
2. Commit dodający run.md — poprawiony kontrakt, instrukcja, README i rejestry.
   Pełny hash do trwałego odczytu (bez umieszczania przyszłego hasha we własnej treści):

```powershell
git log --diff-filter=A --format=%H -- docs/school-app/run.md
```

Pełny hash podany także w odpowiedzi końcowej; zostanie wpisany literalnie przy
następnej aktualizacji rejestru. PUBLISH-01: wcześniejsza publikacja runtime
pozostaje osobnym otwartym problemem, nie została usunięta przez cleanup.
Decyzje z bieżącego promptu zastępują poprzednie propozycje; nie pytamy o D1–D7.
Portal nie jest zaimplementowany. Po końcowym odbiorze potrzebny nowy prompt
na etap 3; nie przechodzimy do niego automatycznie.

| Etap | Zakres | Status | Commit | Dowody sprawdzenia | Blokady / następny krok |
|---|---|---|---|---|---|
|1|Audyt i worktree|Zweryfikowany i zaakceptowany przez użytkownika|bb99de3d808db8898426b42203e6c5e979e527be|Baza/status;226 Python;7 Node+mobile_flow;2 browser E2E;capture smoke;4 Android+APK;bazowe coverage85.9985%;audit.md|Docker CLI brak;YOLO/telefon/droga nieodebrane;wynik tylko bazy|
|2|Kontrakt aplikacji|Przygotowany do końcowego odbioru|3ff54d9d3c4a7dfb23b53db9095f69f1112427f0; cleanup 7a2899770075cc6ac12c826234f620f1de97a380; doprecyzowanie: commit run.md|14 nowych tabel,37 obowiązkowych API+26 adapterów z scenariuszami;kontrola ACL/DTO/formularzy/legacy;CLI/map/state/synthetic recordingZIP smoke PASS;2Python+7Node+mobileflow;7runtimefiles zachowane,size/mtime,tree0;ignorecheck|PUBLISH-01 otwarte;portal/SMTP/Docker jeszcze niewdrożone;czekamy na końcowy odbiór,STOP przed etapem3|
|3|Baza danych i migracje|Do zrobienia|—|—|Końcowy odbiór kontraktu v1 i osobny prompt;bez importu starego runtime|
|4|Konta i sesje|Do zrobienia|—|—|Implementacja ustalonego SMTP/aktywacji/resetu i session policy|
|5|Uprawnienia i ochrona API|Do zrobienia|—|—|Jawna macierz ról i wszystkie odziedziczone endpointy|
|6|Przejazdy i obserwacje|Do zrobienia|—|—|Niezmienny raw, audyt korekt, spójność i recovery|
|7|Nowoczesny UI użytkownika|Do zrobienia|—|—|Projekt w kierunku ReactLY i odbiór wizualny|
|8|Widoki analityka i administratora|Do zrobienia|—|—|Zatwierdzone role i zakres danych|
|9|Nawigacja i responsywność|Do zrobienia|—|—|Nowy UI, regresja GPS/replay, zachowanie blokad live|
|10|Pełne testy i pokrycie|Do zrobienia|—|—|Pełny uzgodniony mianownik backendu oraz osobny pomiar JS|
|11|Docker i wdrożenie demo|Do zrobienia|—|—|Docker engine/CLI, drugi komputer, syntetyczne dane|
|12|Raport końcowy i odbiór użytkownika|Do zrobienia|—|—|Wyniki wcześniejszych etapów, screenshoty i reprodukcja|

Kontrakt etapu 2: [contract.md](contract.md). Aktualne uruchomienie: [run.md](run.md).

Źródła dowodów oraz rozróżnienie błędów kodu, zależności i pominięć:
[audit.md](audit.md). Jawność promptów: [ai-usage.md](ai-usage.md).
