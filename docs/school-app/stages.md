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
|6|Przejazdy i obserwacje|Zaakceptowany przez użytkownika|bc459fb628861bd40b26404805840c66f45f0850;1e3ae7126fa5d6d5dac0aa38be42cb3cf9565f7b;9b0d0e5d18031c0d027ba63a5ceb421b4a5e3e83;bf6af53f72365cdb95523db40f9fb48b0d0a1fe1;eb6e61082e84ebf6b5797f02d634f4ec1df96f6e;1827dd8dfdf2d930bf610c84786c1ddded5553dc;przegląd 4d30c8bec1586604313a838413e6fc64818f7ae7;dokumentacja stage6.md|Poprawka: 35 records PASS; 143 szkolne / 369 pełna regresja (po 1 skip); browser/JS/HTTP PASS; coverage z telemetry 88.5812%; końcowa sekcja stage6.md|UI/pełne nav/Android/CV później;STOP przed 7|
|7|Interfejs użytkownika, tabele i formularze|Zaakceptowany przez użytkownika|0499805f282d39944989fb88232fda8cfdb256c9;8ce6d513a2fbae420b51aead71b9b44231741c9b;d8e4e25599f8081a7a08e5bb105cfdc873d591e6;75e25b48c7b94641c573763a161c56e0f2ccbe88;a18fef0cbd8344b20b9bf40014dfe0e50d4088eb;dokumentacja stage7.md|16 Node/V8, 47 Python, browser 3 rozmiary, 10 screenshotów; stage7.md|Dodatkowe role i pełna nawigacja: 8–9; STOP przed 8|
|8|Widoki analityka i administratora|Zaakceptowany przez użytkownika|7927fc233f48a90ee238fc2ecacf1566b9a0a6fa;cc7637334da78d470e674bf2a62f11ecec00d10e;d9c281a186f657048bbba72ec749fea075c1033c;781f8bc1a45c892ee4c5de55e14316255406f625;0a738140000a78da401df99115d42f4fb989f568;f7df99da6cf4f8752d51d922101245e79aa6d372;dokumentacja stage8.md|10 admin HTTP;157 szkolnych/383 pełna regresja (1 skip),25 Node/V8,3 rozmiary browser,8 PNG;stage8.md|Nawigacja/Android/CV etap9;pełny mianownik coverage etap10;STOP przed9|
|9|Nawigacja, Android GPS, CV i responsywność|Zaakceptowany przez użytkownika|dabe41356c6028b855506ffd8e93aa3a844ad126;92c07c80fd6658c5464c7de5e232e2e6529f16c1;77798fd202728f76df7c9b28008b129bb2899810;844e633c48e56ac6c8adb72e183e9598a9bdba5e;546c37241843c6f4de5db8215b61494ee4379f1b;c23e8b8698064a39a880d0e74784a5af5e59c819;dokumentacja stage9.md|400 Python OK/1skip;17 new HTTP;35 Node/V8;Edge4 viewport, role3 i reauth2;JUnit7/APK;coverage87.2919% etapowego zakresu;stage9.md|Akceptacja w prompcie10;sprzęt/YOLO/field ride niewykonane|
|10|Pełne testy i pokrycie|Przygotowany do odbioru|6a4e02cb1a2bb85e0cb574d307da1ddc67c2b1b9;40f98642a32d05b074e92931442c65fb27e159b8;dokumentacja stage10.md|412Python:411PASS/1skip;42Node;6browser/16rozmiarów;JUnit7/APK;Python87.2846%combined/92.1971%lines/75.0973%branches;JS76.10%lines/98.84%V8branches;stage10.md|Brak lokalnych blokerów;CI skonfigurowane,nieuruchomione zdalnie;sprzęt niewykonany;STOP przed11|
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


Ponowny przegląd etapu 6: **4d30c8bec1586604313a838413e6fc64818f7ae7**.
Poprawka nieudanego startu i retry cleanup niezależnego od aktywnego kontekstu:
końcowa sekcja [stage6.md](stage6.md), reproduktor [run.md, sekcja 12](run.md).
Bieżący status: **Przygotowany do ponownego odbioru**. Etapy 7–12 Do zrobienia.
Hash dokumentacji poprawki: `git log -1 --format=%H -- docs/school-app/stage6.md`.


Etap 6 zaakceptowany w prompcie 7: **eb6e61082e84ebf6b5797f02d634f4ec1df96f6e**.
Etap 7 przygotowany do odbioru: [stage7.md](stage7.md). Poprzednie wpisy są historią,
bieżący status jest w tabeli i tym wpisie. Etapy 8–12 Do zrobienia.


Etap7 zaakceptowany w prompcie8: **0499805f282d39944989fb88232fda8cfdb256c9**.
Etap8 przygotowany do odbioru: stage8.md. Bieżąca tabela zastępuje historyczne statusy
z wcześniejszych wpisów. Etapy9–12 Do zrobienia, etap9 nie rozpoczęty.
Hash dokumentacji: `git log -1 --format=%H -- docs/school-app/stage8.md`.


Poprawka reauth etapu8,2026-10-14: przegląd d9c281a186f657048bbba72ec749fea075c1033c.
Status: **Przygotowany do ponownego odbioru**. Draft pamięciowy, ten sam użytkownik,
fresh GET zasobu/uprawnień, świadomy submit i revision; pełne czyszczenie na401/logout/
zmianie konta/cancel. Dowody:40Python,29Node/V8, real403 browser desktop/phone i regresja
UI/roles w3rozmiarach; końcowa sekcja stage8.md. Etapy9–12 Do zrobienia.
Hash poprawki: `git log -1 --format=%H -- docs/school-app/stage8.md`.


Etap9 zaakceptowany w prompcie10: **dabe41356c6028b855506ffd8e93aa3a844ad126**.
Etap10 kryteria lokalne spełnione, przygotowany do odbioru: stage10.md.
Aktualna tabela zastępuje historyczne statusy w starszych wpisach.
412 testów Python (411PASS/1symlink skip),42JS,6browser suites/16viewport runs,
7JUnit/debugAPK. Szeroki Python87.2846%combined, osobny JS76.10%lines/98.84%V8branches.
CI Windows/Linux/browser/Android istnieje, zdalnego run/pushu brak.
Etap11 Docker/drugi komputer i etap12 raport/końcowy odbiór nadal Do zrobienia.
