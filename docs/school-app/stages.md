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
2. **77c074cdc24eb14795eb8eb593167945d74eead4** — poprawiony kontrakt, instrukcja, README i rejestry.
   Pełny hash do trwałego odczytu (bez umieszczania przyszłego hasha we własnej treści):

```powershell
git log --diff-filter=A --format=%H -- docs/school-app/run.md
```

Etap 2 został zaakceptowany przez użytkownika w prompcie etapu 3.
PUBLISH-01 nadal otwarty; publikacja runtime nie została usunięta z historii.
Portal HTTP nie jest zaimplementowany; etap 3 dodaje tylko persistence.

| Etap | Zakres | Status | Commit | Dowody sprawdzenia | Blokady / następny krok |
|---|---|---|---|---|---|
|1|Audyt i worktree|Zweryfikowany i zaakceptowany przez użytkownika|bb99de3d808db8898426b42203e6c5e979e527be|Baza/status;226 Python;7 Node+mobile_flow;2 browser E2E;capture smoke;4 Android+APK;bazowe coverage85.9985%;audit.md|Docker CLI brak;YOLO/telefon/droga nieodebrane;wynik tylko bazy|
|2|Kontrakt aplikacji|Zaakceptowany przez użytkownika|77c074cdc24eb14795eb8eb593167945d74eead4; pierwotny 3ff54d9d3c4a7dfb23b53db9095f69f1112427f0; cleanup 7a2899770075cc6ac12c826234f620f1de97a380|14 tabel,37 API+26 adapterów; kontrola dokumentów i syntetyczny smoke opisane w contract/run|PUBLISH-01 osobno; zaakceptowany zakres v1|
|3|Baza danych i migracje|Przygotowany do ponownego odbioru|wcześniejszy 6c3364997bd26cd8a0a0a67ee7505371bf93feef;fb80ef609632a78fd268ce864ede713c2b98df71;023198ae149b4953e2311be7c9729ac128d6e405; dokumentacja: ostatni commit stage3.md|14 tabel/v2;immutable0001;exact COMMIT reproducer rollback;v1 upgrade/legacy restore;raw.csv RunLogger;[from,to);48 testów 1skip;274 regresja 1skip;7Node+mobileflow;CLI/HTTP smoke;coverage94.4115%,linie98.5277%,gałęzie82.2148%|Win symlink1314,junctionPASS;niezależny Linux wynik6c33649 osobno;login/SMTP/UI/recovery nadal później;STOP przed4|
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

Hash dokumentacji etapu 3 do odczytu:
`git log -1 --diff-filter=A --format=%H -- docs/school-app/stage3.md`.
Hash końcowy w odpowiedzi; literalny wpis przy następnej aktualizacji,
żeby commit nie zawierał odwołania do własnego przyszłego hasha.

Ponowny przegląd etapu3: wcześniejszy literalny hash
6c3364997bd26cd8a0a0a67ee7505371bf93feef. Błędy poprzedniej implementacji
naprawione i opisane w stage3.md; nie traktujemy wcześniejszego odbioru jako
potwierdzenia atomowości parsera ani zgodności sekund z kontraktem.
Hash bieżącej dokumentacji: `git log -1 --format=%H -- docs/school-app/stage3.md`.
