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
Etap 3 dodał persistence, etap 4 portal kont, etap 5 ochronę zasobów.
Etap 6 implementuje zapis domeny; bieżące dowody i status są w tabeli poniżej.
Niższe wpisy zachowują historię wcześniejszych odbiorów, nie zastępują bieżącej tabeli.

| Etap | Zakres | Status | Commit | Dowody sprawdzenia | Blokady / następny krok |
|---|---|---|---|---|---|
|1|Audyt i worktree|Zweryfikowany i zaakceptowany przez użytkownika|bb99de3d808db8898426b42203e6c5e979e527be|Baza/status;226 Python;7 Node+mobile_flow;2 browser E2E;capture smoke;4 Android+APK;bazowe coverage85.9985%;audit.md|Docker CLI brak;YOLO/telefon/droga nieodebrane;wynik tylko bazy|
|2|Kontrakt aplikacji|Zaakceptowany przez użytkownika|77c074cdc24eb14795eb8eb593167945d74eead4; pierwotny 3ff54d9d3c4a7dfb23b53db9095f69f1112427f0; cleanup 7a2899770075cc6ac12c826234f620f1de97a380|14 tabel,37 API+26 adapterów; kontrola dokumentów i syntetyczny smoke opisane w contract/run|PUBLISH-01 osobno; zaakceptowany zakres v1|
|3|Baza danych i migracje|Zaakceptowany przez użytkownika|2020b84d68ef3720c1b2d2345cf381c98a2a603b|Niezależny przegląd i wyniki opisane w stage3.md; v2/14 tabel/immutable migrations/rollback/backup/isolacja|Akceptacja w prompcie etapu4; PUBLISH-01 nadal osobno|
|4|Konta i sesje|Zaakceptowany przez użytkownika|45eef418efa9ca0afc9af8a6137a286fa990f5a7;d0b2ddcbb2aea9c74ff3710a7e341e4997be5462;90beec7bd5b0abc51548e5c240e9e439708d2f87;4746c9ee5c55806e91e9bb25f7881244958322de;2b9ed3ddb8e34e316701270e64904c290a73541b;9dcf41e1b3e7140a64b437357f94f9614400eea2;dokumentacja: commit stage4.md|Register/SMTP/verify/login/session/CSRF/reset/change/reauth/bootstrap; testy i per-module coverage w stage4.md; desktop i phone browser PASS z realnym KDF; brak legacy passthrough|Akceptacja w prompcie5;domena/role panel/telefon/Docker odbierane oddzielnie|
|5|Uprawnienia i ochrona API|Zaakceptowany przez użytkownika|13858b06051a4183bfc7e0559962611c8be2eae2;5ce716c28c1014e97ec19f058c870fa1c9925984;fdc06bb7efd82455ffbf00deb62a37d80c494e23;5ada5e834ac50d4bea07a6d57d7152b78bc6bda9;09646eb735dd8f141de3f89087a644eb875c8a76;dokumentacja stage5.md|Macierz HTTP,scoped export/replay/GPS_QUALITY/CVmedia/Range,revokacja;stage5.md|Wcześniejsze granice etapu 5 w stage5.md; zapis odebrany osobno w etapie 6|
|6|Przejazdy i obserwacje|Przygotowany do odbioru|bc459fb628861bd40b26404805840c66f45f0850;1e3ae7126fa5d6d5dac0aa38be42cb3cf9565f7b;9b0d0e5d18031c0d027ba63a5ceb421b4a5e3e83;bf6af53f72365cdb95523db40f9fb48b0d0a1fe1;dokumentacja stage6.md|133 testy szkolne / 359 pełna regresja, po 1 skip; HTTP/CLI/browser/Node PASS; coverage szkolne combined 89.6302%; stage6.md|UI/pełne nav/Android/CV później;STOP przed 7|
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

Etap3 zaakceptowany: literalny hash2020b84d68ef3720c1b2d2345cf381c98a2a603b.
Hash dokumentacji etapu4: `git log -1 --diff-filter=A --format=%H -- docs/school-app/stage4.md`.
Wyniki i blokady etapu4 w stage4.md;stan etapu5 według aktualnej tabeli,6–12 Do zrobienia.

Etap4 zaakceptowany w prompcie etapu5: **45eef418efa9ca0afc9af8a6137a286fa990f5a7**.
Etap5 dowody/status/granice: [stage5.md](stage5.md). Hash końcowej dokumentacji:
`git log -1 --diff-filter=A --format=%H -- docs/school-app/stage5.md`.
Etapy6–12 nadal Do zrobienia;bez automatycznego startu6.

Przegląd etapu5 dotyczył **0b10d9b39c1f0251c513bcdfdffddffe74318b67**.
Poprawka konkretnego share_id i dowody w końcowej sekcji stage5.md.
Poprzednie polecenie było urwane;kompletny prompt korekty owner management
zastępuje jego brakującą część. Bez ponownego pytania. Etapy6–12 Do zrobienia.

Korekta owner management:przegląd **20d9be8437be5977d85948cdc456bcfbf430183b**.
Właściciel status/cancel niezależnie od share;execution nadal przypięte do pierwotnego grantu.
Dowody i per-module coverage w końcowej sekcji stage5.md.

Korekta końcowa:własne108tests/334fulltesty,1jawnyWindows symlinkskip;
branch coverage90.9965%combined,permodulewstage5.md. Execution i owner management
odebrane oddzielnymi testami;etapy6–12nadal Do zrobienia.

Etap5 zaakceptowany:**13858b06051a4183bfc7e0559962611c8be2eae2**.
Etap6 implementacja,dowody i granice:[stage6.md](stage6.md);etapy7–12 Do zrobienia.
Hash dokumentacji etapu6:`git log -1 --diff-filter=A --format=%H -- docs/school-app/stage6.md`.
