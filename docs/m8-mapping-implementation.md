# M8 — instrukcja implementacji mapowania i odbioru

Status: **implementacja offline ukończona; odbiór telefonu i jazda terenowa oczekują**, 19.09.2026. Kod realizuje MAP-01–05, MAP-06A i bramkę MAP-07. Położenie pilotowej trasy, linii, limitów i faz nie jest oznaczone jako zweryfikowane bez dowodów terenowych.

## 1. Cel i granice

Po wykonaniu MAP-01–05 użytkownik ma móc:

1. Odtworzyć zapisany przejazd w prawdziwych współrzędnych, również poza przygotowanymi trasami.
2. Obserwować telefon na mapie na żywo, z prędkością i jakością danych.
3. Wybrać przygotowaną trasę i zobaczyć dopasowanie do niej, kierunek oraz odległość do właściwej linii zatrzymania.
4. Rozpoznać brak dopasowania, niejednoznaczność, zjazd, przeciwny kierunek i utratę aktualnych danych.
5. Przeprowadzić test tych funkcji bez internetu w komputerze.

MAP-06 to odbiór offline i drogowy. MAP-07 udostępnia rekomendację dopiero po spełnieniu osobnych warunków dotyczących geometrii, pomiaru, ograniczeń i faz. Sama pozycja świateł nie dostarcza ich koloru.

Na tym etapie nie budujemy ogólnomiejskiego routingu, własnego silnika nawigacji ani API aktualnego koloru świateł. Nie trzeba zmieniać natywnego odbiornika Android na inne rozwiązanie. Pierwszy matcher pracuje lokalnie na jawnie wybranej trasie.

Telefon nie jest potrzebny do pierwszych pakietów. Podłączamy go do sprawdzenia integracji live; jazda jest potrzebna dopiero w drogowej części MAP-06.

## 2. Punkt wyjścia i miejsca zmian

Przed kodowaniem sprawdź aktualne pliki i instrukcje repozytorium. Poniższy stan odnosi się do wersji oglądanej przy przygotowaniu planu:

| Obszar | Istniejący kod | Decyzja |
|---|---|---|
| GPS, prędkość, filtr postoju | `greenwave/positioning.py` | Zachować natywną prędkość i jej źródło; dodać kontrolę świeżości i reset historii na granicach strumieni. |
| Orkiestracja | `greenwave/application.py` | Oddzielić kontekst live i mapowania od pozycji symulowanej. |
| Modele symulacji | `greenwave/models.py` | `Corridor` wymaga świateł; nowa geometria nie może od tego zależeć. |
| Replay symulacji | `greenwave/replay.py` | Zachować; odtwarzanie GPS w osobnym module. |
| Niezmienny zapis | `greenwave/telemetry.py` | Nie modyfikować ukończonych nagrań ani ich manifestów. |
| Analiza | `greenwave/analysis.py` | Ponownie wykorzystać walidację integralności; raport mapowania jest osobnym wynikiem. |
| HTTP | `greenwave/server.py` | Zachować walidację hosta, pochodzenia, sesji i autoryzacji właściwą dla danego klienta. |
| Interfejs | `greenwave/web/app.js`, `index.html`, `style.css` | Zachować vanilla JS i istniejący sposób renderowania. |
| Telefon | `android/GreenWaveSensor` | Fused Location już działa; rozszerzyć metadane czasu wysłania. |

Obecna lokalna mapa i trasa demonstracyjna nie wystarczają do pokazania przejazdu na Chomiczówce. Nie przeliczać prawdziwej pozycji GPS na procent długości trasy demonstracyjnej.

Nagranie kontrolne: `5cef7b3e1faa435f9cdb42fa249683a6`, Chomiczówka, 584 próbki ANDROID_FUSED, około 583 s między skrajnymi próbkami. Wybrane podczas nagrywania `corridor_id` nie dowodzi jazdy po tym korytarzu. To regresja sensora i loggera, nie wzorzec rzeczywistej pozycji ani walidacja świateł.

Nie kopiować prywatnego przejazdu do publicznych fixture'ów. Testy w repozytorium mają używać danych syntetycznych. Brak lokalnego nagrania u innego dewelopera może pomijać tylko osobny test integracyjny, nie testy algorytmu.

## 3. Wspólne kontrakty

### Jednostki i tożsamość

- W obliczeniach: metry, sekundy, m/s, stopnie azymutu zgodnie z ruchem wskazówek od północy. km/h wyłącznie w prezentacji.
- Współrzędne API nazwane `latitude`/`longitude`; tablice GeoJSON zawsze `[longitude, latitude]`.
- Brak wartości oznacza `null`, nigdy zero. Odrzucaj NaN, nieskończoności i wartości poza zakresem.
- Tożsamość nowej próbki: `(device_id, stream_id, sample_sequence)`. Dla starych nagrań: `(run_id, numer_wiersza)`; oba odwołania można zachować.
- Numer wiersza to faktyczna sekwencja rekordu w nagraniu, nie indeks po odfiltrowaniu innych eventów.
- Duplikat nie odświeża zegara, nie przesuwa matchera i nie tworzy zdarzenia przejazdu.

### Rozdzielenie kontekstów

Wprowadź `view_mode = SIMULATION | LIVE | GPS_REPLAY`. Zmiana widoku nie uruchamia/zatrzymuje sensora i nie kasuje nagrania.

Trzy niezależne informacje:

- wybrany dataset symulacji;
- `selected_route_id` oraz wersja geometrii do mapowania, dopuszczalne `null`;
- wynik dopasowania do wybranej trasy, dopuszczalny brak.

Nie deklaruj automatycznego rozpoznania korytarza, jeżeli sprawdzono tylko jedną wybraną trasę. W UI użyj „dopasowanie do wybranej trasy”.

Nowe moduły:

- `greenwave/route_geometry.py`: walidacja i odczyt geometrii, układ metryczny, projekcja na segment, `s`.
- `greenwave/map_matching.py`: stanowy matcher, konfiguracja i wynik, bez HTTP/UI/dostępu do sieci.
- `greenwave/gps_replay.py`: czytanie telemetrii GPS i deterministyczne odtwarzanie.
- `greenwave/route_events.py`: następny punkt i przekroczenia linii.
- `greenwave/mapping_analysis.py`: pochodny raport i zapis wyników.

Nie dokładać frameworka frontendowego, zewnętrznej usługi dopasowania ani ciężkiej biblioteki geograficznej do pierwszej wersji.

## 4. MAP-01 — implementujemy: ślad, swobodny pomiar i replay

### Dane i odtwarzanie

1. Wczytaj nagranie przez istniejącą walidację run ID, kompletności i sum kontrolnych. Wybierz `EXTERNAL_TELEMETRY`; puste rekordy symulacyjnej telemetrii nie mogą zastępować GPS.
2. Zachowaj pozycję surową, prędkość surową/końcową, źródło, dokładność, czas pomiaru, czas odbioru, identyfikatory oraz przyczyny odrzucenia.
3. Kolejność przetwarzania to kolejność odbioru zapisana w logu. Nie sortuj spóźnionych próbek tak, aby ukrywać ich opóźnienie.
4. W ramach strumienia użyj różnic `elapsed_realtime_nanos` do czasu pomiaru. Dla starszych rekordów zastosuj różnice czasu telefonu z flagą fallback. Cofnięcie czasu tworzy granicę ciągłości i jest pokazane w raporcie.
5. Przejście między strumieniami ma oddzielną granicę; nie odejmuj zegarów monotonicznych różnych strumieni/urządzeń. Do umieszczenia granicy na osi replay użyj czasu odbioru i oznacz jego użycie.
6. Odtwarzacz: wybór nagrania, play/pause, prędkość 1×/2×/5×, suwak czasu, reset do początku. Seek odtwarza stan od początku do celu, bez zaglądania w przyszłe próbki. Optymalizację checkpointami dodaj tylko jeżeli rzeczywiście potrzebna.
7. Panel pokazuje czas pomiaru i odbioru oddzielnie. Starsze nagrania bez nowych metadanych czasu nadal można analizować, z informacją o ograniczeniach.

### Mapa

- Rysuj ślad WGS84, początek/koniec, bieżącą próbkę i okrąg deklarowanej dokładności. Próbki odrzucone mają inną prezentację, nie znikają z diagnostyki.
- Dopasuj początkowy widok do bounds nagrania. Zapewnij przesuwanie, zoom i powrót do całego śladu.
- Przygotuj lokalny wektorowy podkład ulic dla bounds testu z marginesem. Zapisz źródło, obszar, datę pobrania i atrybucję OpenStreetMap. Pobranie danych jest krokiem przygotowania, nie częścią obsługi próbki GPS.
- Rozszerz istniejący format podkładu tylko na tyle, ile potrzeba; dodaj wybór obszaru pokrywającego ślad. Nie pobieraj masowo kafelków.
- Bez podkładu nadal pokazuj ślad na pustej mapie z komunikatem „brak lokalnego podkładu”. Brak internetu nie może zatrzymać loggera ani pozycji.
- Ślad nie jest wysyłany do publicznego API dopasowania.

**Odbiór:** Chomiczówka pojawia się we właściwych współrzędnych niezależnie od wybranego datasetu; ten sam punkt replay ma te same dane po seek i po ciągłym odtwarzaniu. Widok bez trasy i bez świateł działa.

## 5. MAP-02 — implementujemy: geometria niezależna od sygnalizacji

Pliki tras: `data/routes/<route_id>.json`, `schema_version: 1`.

Wymagane pola:

| Pole | Znaczenie |
|---|---|
| `route_id`, `geometry_version`, `name` | Stabilny identyfikator i jawna wersja. |
| `direction_description` | Kierunek przejazdu opisany punktami początek → koniec. |
| `coordinates` | Uporządkowana linia `[lon, lat]`, minimum dwa różne punkty. |
| `source` | Rodzaj źródła, identyfikator/URL, data pozyskania, atrybucja. |
| `geometry_verification` | `DRAFT`, `DESK_CHECKED` albo `FIELD_CHECKED`, data i uwagi. |
| `speed_sections` | Opcjonalna lista zakresów `start_s_m`, `end_s_m`, `limit_mps`, źródła i weryfikacji. |
| `stop_lines` | Opcjonalna lista z MAP-04; pusta lista jest poprawna. |

Podczas ładowania wylicz SHA-256 kanonicznego JSON geometrii i konfiguracji trasy. Raporty przechowują wersję i hash. Zmiana punktów bez zmiany nazwy wersji pozostaje wykrywalna.

Obliczenia metryczne dla lokalnej trasy miejskiej:

- Stały początek układu: pierwszy punkt trasy. `x = R*cos(lat0)*(lon-lon0)`, `y = R*(lat-lat0)`, kąty w radianach, `R = 6371008.8 m`.
- Ogranicz pierwszą wersję do obszaru o rozpiętości do 30 km; większą geometrię odrzuć z czytelną przyczyną zamiast cicho stosować przybliżenie.
- Wylicz długość każdego odcinka i skumulowane `s`. Dla projekcji na odcinek `s = s_start + t*length`, `t` ograniczone do `[0,1]`.
- Każdy odcinek ma `segment_index` oznaczający wystąpienie w trasie. Powtórzony odcinek w pętli ma inny indeks i inne `s`.
- Usuń kolejne identyczne punkty albo odrzuć je z jednoznacznym błędem; wybierz jedno zachowanie, udokumentuj i przetestuj. Nie usuwaj niekolejnych powtórzeń tworzących pętlę.
- Odległości obliczaj w tym samym układzie, nie z pikseli ani długości Web Mercator.
- Brak ograniczenia prędkości pozostaje brakiem. Nie wpisuj automatycznie 50 km/h.

**Odbiór:** testy prostej, zakrętu, projekcji poza końcem odcinka, pętli, błędnych współrzędnych, pustej trasy i odcinka zerowego; niezależny prosty wzorzec długości z tolerancją, nie test powtarzający funkcję produkcyjną.

## 6. MAP-03 — implementujemy: świeżość i dopasowanie

### Najpierw świeżość danych

Obecny wiek odbioru nie wystarcza: telefon może dosłać kolejkę starych pomiarów.

1. Android dodaje `sent_elapsed_realtime_nanos` wyliczone bezpośrednio przed każdą próbą HTTP. Czas pomiaru pozostaje `elapsed_realtime_nanos` z Location. Ponowne wysłanie zachowuje ID próbki, aktualizuje czas wysłania.
2. Backend sprawdza `sent >= capture` i liczy `capture_age_at_send_s`. Wiek rośnie dalej według serwerowego zegara monotonicznego od odebrania próbki.
3. To oszacowanie nie obejmuje nieznanego czasu transportu. Nazwij je `measurement_age_lower_bound_s`, pokaż osobno `receipt_age_s`; nie deklaruj pełnej synchronizacji zegarów. W pierwszym teście live wspieramy lokalne połączenie USB. Transport przez internet wymaga osobnej walidacji opóźnień.
4. Pomiar starszy niż 5 s przy wysłaniu/ocenie nie steruje pozycją live. Historyczny zapis pozostaje dostępny. Brak metadanych wieku oznacza `FRESHNESS_UNKNOWN`; stare logi są odtwarzalne, ale nie dowodzą gotowości live.
5. Próbka poza kolejnością, mock lub niepoprawna jest widoczna w diagnostyce, ale nie przesuwa aktywnego matchera. Nie nadpisuje ostatniej dobrej pozycji jako aktualnej.
6. Na zmianie urządzenia/strumienia, cofnięciu czasu pomiaru lub luce ponad 5 s wyczyść historię ciągłości matchera, wyliczanej prędkości i filtra postoju. Nie zeruj pamięci deduplikacji przy samym zerowaniu historii ruchu.
7. Odpytywanie stanu musi aktualizować STALE także wtedy, gdy nie przychodzi żadna nowa próbka.

Rozszerz istniejący payload kompatybilnie: brak nowego pola nie powoduje HTTP 500. Interfejs ma powiedzieć, dlaczego starego klienta nie dopuszcza do bieżących rekomendacji.

### Wynik matchera

`MapMatchResult` zawiera:

- `sample_ref`, `route_id`, `geometry_version`, `geometry_hash`, `algorithm_version`;
- `status`: `NO_ROUTE | NO_FIX | ACQUIRING | MATCHED | UNCERTAIN | OFF_ROUTE | WRONG_DIRECTION | STALE`;
- `reason_codes`: lista stabilnych kodów, tłumaczonych na tekst w UI;
- `candidate_segment_index`, `candidate_s_m`, `candidate_latitude`, `candidate_longitude`, `cross_track_m` — najlepszy kandydat diagnostyczny, dopuszczalne null;
- `accepted_s_m`, `accepted_latitude`, `accepted_longitude` — wyłącznie dla bieżącego MATCHED, w pozostałych stanach null;
- `direction`: `FORWARD | REVERSE | UNKNOWN`;
- `position_uncertainty_m`: konserwatywna heurystyka, nie skalibrowany przedział ufności;
- parametry świeżości i identyfikator konfiguracji.

Ostatni poprawny wynik można prezentować jako historyczny, z wiekiem i przygaszeniem. Nie wolno przekazywać go solverowi jako aktualnego po utracie dopasowania.

### Algorytm pierwszej wersji

Matcher dostaje kolejne próbki i geometrię; zegar jest wstrzykiwany dla testów. Prędkość końcowa z telefonu pozostaje niezależnym pomiarem. Nie wyliczaj prędkości z przeskoków punktu dopasowanego.

Parametry startowe w jednej dataclass `MatcherConfig`, zapisane także w raportach:

| Parametr | Wartość początkowa |
|---|---:|
| Maksymalna deklarowana dokładność do MATCHED | 25 m |
| Maksymalny wiek/luka ciągłości | 5 s |
| Promień wyszukania kandydatów | `min(50, max(12, 2*accuracy_m))` m |
| Minimalna prędkość dla azymutu urządzenia | 2 m/s |
| Maksymalny błąd azymutu, jeśli podany | 30° |
| Azymut bez informacji o błędzie | diagnostyka, bez rozstrzygania kierunku |
| Potwierdzenie wejścia/powrotu do MATCHED | 2 kolejne zgodne próbki |
| Potwierdzenie OFF_ROUTE | 3 kolejne próbki dobrej jakości bez kandydata |
| Potwierdzenie przeciwnego kierunku | 2 próbki z wiarygodnym kątem >120° |

To progi inżynierskie do zweryfikowania, nie obietnica dokładności GPS. Każda ich zmiana wymaga aktualizacji konfiguracji i testów scenariuszy.

Przetwarzanie:

1. Sprawdź trasę, ważność pozycji, świeżość i ciągłość. Słaba dokładność daje UNCERTAIN, nie OFF_ROUTE.
2. Wyznacz projekcje na wszystkie odcinki w promieniu. Na początek zwykły przegląd odcinków wystarczy; bez sieci i bez pobierania map.
3. Oceniaj odległość poprzeczną względem `max(accuracy_m, 5)`, zgodność wiarygodnego kierunku oraz ciągłość `s`. Wykorzystaj poprzednie hipotezy, nie tylko najbliższy punkt.
4. Utrzymuj do 5 hipotez z poprzedniej próbki. Koszt kroku: `(cross_track/sigma)^2 + (heading_delta/45)^2`, drugi składnik tylko przy wiarygodnym azymucie. Przyciągaj kandydatów zarówno w przód, jak i w tył: do oceny geometrii użyj mniejszego kąta względem osi odcinka; znak kierunku rozstrzygnij oddzielnie. Dzięki temu jazda wstecz nie jest ukrywana jako brak drogi.
5. Dla przejścia użyj różnicy `abs(delta_s)` oraz oczekiwanej drogi `mean(valid_speed)*dt`. Dodaj koszt kwadratu różnicy dzielonej przez `max(10, accuracy_prev + accuracy_now)`. Jeśli brak prędkości, pomiń oczekiwaną drogę; zachowaj konserwatywny limit przemieszczenia.
6. Odrzuć przejście, gdy `abs(delta_s) > vmax_observed*dt + 2*(accuracy_prev+accuracy_now) + 10 m`; `vmax_observed = max(5 m/s, dostępne prędkości + 5 m/s)`. Gdy brak obu prędkości, użyj osobnego technicznego limitu 80 m/s, nie limitu prawnego. Niemożliwe przejście powoduje UNCERTAIN i ponowne nabycie pozycji, nie sztuczne przycięcie `s`.
7. Koszt hipotezy: `0.5*poprzedni_koszt + koszt_kroku + koszt_przejścia`. Po selekcji odejmij najniższy koszt dla stabilności numerycznej. Remisy rozstrzygaj deterministycznie indeksem odcinka, lecz sam remis nie daje MATCHED.
8. Projekcje przy wspólnym wierzchołku o różnicy `s <= 5 m` traktuj jako jedną hipotezę pozycji. Dwa odległe wystąpienia tej samej ulicy w pętli pozostają różnymi hipotezami. Różnica kosztu najlepszych różnych hipotez <2 oznacza UNCERTAIN. Ten margines jest konfigurowalny i nie jest prawdopodobieństwem.
9. Przy starcie/postoju bez wiarygodnego kierunku można uzyskać MATCHED pozycji na jednoznacznym odcinku, ale `direction=UNKNOWN`. Nie wolno z tego potwierdzić przejazdu ani rekomendacji wymagającej kierunku.
10. Kierunek potwierdza wiarygodny azymut albo zgodna zmiana `s` przekraczająca niepewność pozycji w kolejnych próbkach. Sam drgający GPS podczas postoju nie zmienia kierunku. Przeciwny kierunek daje WRONG_DIRECTION; od pierwszego podejrzenia rekomendacja jest niedostępna.
11. Pierwsze próbki po utracie ciągłości mają ACQUIRING. OFF_ROUTE wymaga potwierdzenia, ale już pierwsza próbka bez wiarygodnego dopasowania ma `accepted_s_m=null`.
12. `position_uncertainty_m = max(accuracy_m, cross_track_m, 5 m)` jako początkowa heurystyka. Nie przedstawiaj jej jako gwarantowanego błędu wzdłuż jezdni ani dokładności rozpoznania pasa.

Nie wymuszaj stale rosnącego `s`: zjazd, cofanie i nawrót muszą być widoczne. Jeśli test ujawni sprzeczność powyższych reguł, dodaj minimalny przypadek regresyjny i opisz uzasadnioną korektę w dokumencie; nie ukrywaj błędu pod zmianą progu dla jednego nagrania.

**Odbiór:** deterministyczne testy prostej, skrętu, dwóch jezdni, przecięcia, pętli z powtórzonym odcinkiem, postoju, nawrotu, zjazdu, skoku GPS, luki, kolejki starych danych, duplikatu i restartu strumienia. Przypadek nieodróżnialny na podstawie danych musi dać UNCERTAIN.

## 7. MAP-04 — implementujemy: punkty kontrolne i linie zatrzymania

Przed inwentaryzacją ustal z użytkownikiem dokładny początek, koniec i kierunek pierwszego odcinka przy Arkadii. Wcześniejszy opis „od torów przy Conrada do McDonald's między Klifem i Arkadią” nie wystarcza do automatycznego oznaczenia geometrii jako zweryfikowanej. Rozszerzenie do ONZ jest osobną decyzją. Kod i fixture'y przygotuj przed tym ustaleniem.

Każda linia ma `stop_line_id`, opcjonalne `signal_id`, `segment_index`, geometrię linii `[lon,lat]`, kierunek/manewr, źródło, datę, stan weryfikacji i `position_uncertainty_m`. `s` wylicz z geometrii na przypisanym wystąpieniu odcinka; nie wybieraj innego wystąpienia w pętli przez globalne minimum odległości.

Weryfikuj, czy linia przecina przypisany odcinek lub leży w zadeklarowanej tolerancji. Rozbieżność daje błąd danych, nie ciche przesunięcie. Nie przypisuj pasa, jeśli dostępne dane go nie rozróżniają. Zachowaj osobną weryfikację faz i ograniczeń.

Odległość do linii: `stop_s - accepted_s`. Przedział orientacyjny wykorzystuje sumę niepewności dopasowania i linii. UI może pokazać wartość zaokrągloną; ujemnej odległości nie zamieniaj po cichu na zero w diagnostyce.

Detektor przejazdu:

1. Uzbrój linię dopiero po świeżym MATCHED/FORWARD, gdy cały przedział pozycji jest przed linią.
2. Potwierdź po próbce, której cały przedział jest za linią, pod warunkiem ciągłości i wiarygodnego dopasowania wszystkich próbek między tymi stanami.
3. Luka, niepewność, zjazd lub zmiana kierunku rozbraja potwierdzenie; przejście pozostaje niepotwierdzone.
4. Samo rozpoczęcie pomiaru za linią nie tworzy przejazdu. Nie interpoluj zdarzenia przez lukę.
5. Zdarzenie zawiera przedział czasu pomiaru między ostatnią pewną pozycją przed linią a pierwszą pewną pozycją za nią. Ewentualny czas interpolowany oznacz jako oszacowanie.
6. Deduplikuj po `(traversal_id, stop_line_id)`. Nowy traversal rozpoczyna jawny start przejazdu/reset trasy; ponowne wystąpienia skrzyżowania w pętli mają osobne ID punktów.

Przejazd nie oznacza GREEN. Obserwacja koloru i obserwacja chwili zmiany koloru pozostają osobnymi eventami istniejącego systemu.

**Odbiór:** pojedynczy przejazd, drganie na linii, postój przed nią, start za nią, luka nad linią, zła jezdnia, przeciwny kierunek i dwukrotne wystąpienie punktu w pętli.

## 8. MAP-05 — implementujemy: integracja live i wyniki pochodne

### API i aplikacja

Zachowaj istniejące endpointy i ich odpowiedzi. Dodaj:

- `GET /api/routes`: lista przygotowanych tras i stan weryfikacji, bez ścieżek plikowych od klienta.
- `POST /api/mapping/select` z `{route_id: string|null}`: wybór geometrii i reset historii matchera/detektora; odpowiedź jako snapshot aplikacji.
- `POST /api/view` z `{mode: ...}`: wybór widoku; odpowiedź jako snapshot.
- `GET /api/gps-replay/state` oraz `POST /api/gps-replay` z komendami `load`, `play`, `pause`, `seek`, `rate`. `load` dostaje bezpieczny `run_id`, `seek` sekundy od początku, rate tylko wspierane wartości. Odpowiedź to stan GPS replay.

Snapshot aplikacji rozszerz addytywnie o `view_mode` i `mapping`: wybrana trasa, wynik dopasowania, następny punkt, odległość, status świeżości, przyczyny niedostępności rekomendacji. Pola symulacji nie zmieniają znaczenia.

Nie używaj bezpośrednio istniejącego helpera JS `request()` do odpowiedzi GPS replay, jeśli helper traktuje każdą odpowiedź jako cały stan aplikacji. Dodaj osobną obsługę odpowiedniego kontraktu.

Matcher live przetwarza wyłącznie nową zaakceptowaną próbkę. Snapshot może aktualizować wiek/status, ale nie przetwarza ponownie tej samej próbki. Matcher replay ma oddzielny stan; odtwarzanie starego logu nie przesuwa pozycji live i nie zapisuje fałszywej telemetrii z telefonu.

### UI

- Zakładki/widoki: Symulacja, Telefon na żywo, Nagranie GPS.
- Live działa bez trasy. Pokazuje prędkość z jednostką i źródłem, dokładność, wiek pomiaru/odbioru i stan połączenia.
- Po wybraniu trasy: ślad surowy i dopasowany, kierunek, stan dopasowania z przyczyną, następna linia i dystans. Wyraźnie odróżnij punkt surowy od dopasowanego.
- Nie pokazuj demonstracyjnych kolorów jako aktualnych świateł w live. Brak danych faz ma etykietę „nieznane”.
- Brak świateł/pusta trasa nie może powodować błędów JS; sprawdź użycia `signals[0]`, `.at(-1)` i `.find()`.
- Zachowaj wybrane nagranie przy odświeżaniu listy. Pokaż lokalną datę/godzinę, długość i krótki run ID, aby użytkownik rozpoznawał test.

### Logi pochodne

- Nie zmieniaj istniejących `raw.csv`, `metadata.json` ani `complete.json`. Zapisuj do `data/derived/mapping/<run_id>/<analysis_id>/`; upewnij się, że katalog jest ignorowany przez Git.
- `manifest.json`: hash źródłowego nagrania, geometria/hash, wersja algorytmu, pełna konfiguracja, czas wykonania, metoda zegara, ukończenie i sumy kontrolne wyników.
- `matches.jsonl`: wynik dla każdej próbki z `sample_ref`; `events.jsonl`: przekroczenia i utraty/odzyskania dopasowania; `report.json`: podsumowanie.
- Do wyświetlenia live nie trzeba ponownie czytać plików. Analizę pełnego logu uruchamiaj poza obsługą pojedynczej próbki; nie blokuj przyjmowania GPS długą analizą w serwerze HTTP.
- Raport: liczba/czas statusów, deklarowana dokładność, rozkład odległości poprzecznej, luki, zmiany kierunku, zdarzenia potwierdzone/niepotwierdzone i przyczyny. Wynik kosztu matchera nie jest procentem pewności.
- Nowe nagrania zapisują wybrany kontekst i wersję trasy jawnie. Swobodny pomiar nie musi udawać nagrania na korytarzu symulacyjnym.

**Odbiór:** telefon → API → live → logger → replay daje spójne identyfikatory i wartości; restart, utrata USB, dosłanie kolejki i praca offline nie produkują aktualnej pozycji ze starej próbki. Tryb symulacji nadal działa.

## 9. MAP-06A — implementujemy: odbiór przy komputerze

Wymagane grupy testów:

| Grupa | Co wykrywa |
|---|---|
| Geometria | Zamianę lat/lon, błędne długości, pętle, zły segment linii. |
| Matcher | Niejednoznaczne jezdnie, skoki między odległymi `s`, błędny kierunek, sztuczny ruch na postoju. |
| Czas | Duplikaty, opóźnione bufory, cofnięcie zegara, nowy strumień, STALE bez nowych danych. |
| Detektor | Fałszywe przekroczenia przez szum/lukę, podwójne zdarzenia, start za linią. |
| Replay | Identyczny wynik seek/ciągłe odtwarzanie, brak wpływu przyszłych próbek i brak ingerencji w live. |
| HTTP/UI | Niepoprawne ID i komendy, izolacja sesji, brak trasy/świateł, poprawna prezentacja null i stale. |
| Regresja | Istniejąca symulacja, obserwacje, prędkość/postój, nagrywanie i niezmienność źródłowych plików. |

Polecenie podstawowe: `python -m unittest discover -s tests -v`. Sprawdź składnię JS przez `node --check greenwave/web/app.js`; istniejące testy JS uruchom według poleceń w repozytorium. Po zmianie Androida wykonaj testy modułu i build APK przy użyciu działającego lokalnego zestawu JDK/Gradle; nie zakładaj, że wrapper ma tę samą wersję co lokalnie używany Gradle. Zanotuj dokładne polecenia i wersje, bez instalowania nowego toolchainu bez potrzeby.

Testy muszą zawierać oczekiwane stany/zdarzenia, nie tylko sprawdzenie, że funkcja się uruchamia. Bez rzeczywistego Androida stosuj syntetyczne payloady odtwarzające kolejkę i restart.

Na lokalnym nagraniu Chomiczówki:

- potwierdź liczbę próbek i integralność źródła przed/po analizie;
- obejrzyj surowy ślad i porównaj z ulicami; nie nazywaj tego pomiarem absolutnego błędu GPS;
- bez przypisanej geometrii oczekuj swobodnego replay;
- z celowo niepasującą trasą oczekuj braku dopasowania, nigdy przeniesienia auta na tę trasę;
- nie wymagaj poprawnych zdarzeń świateł z logu, w którym nie prowadzono ich inwentaryzacji.

Następnie krótki test telefonu na postoju: połączenie, kilka świeżych próbek, odłączenie, STALE, ponowne podłączenie, obsługa ewentualnej kolejki i odzyskanie pozycji. Nie wymaga samochodu.

**Warunek dopuszczenia do jazdy:** testy automatyczne przechodzą, lokalny replay działa offline, znana jest geometria odcinka i wybrane punkty kontrolne, UI rozróżnia aktualny pomiar od historycznego. Nie trzeba jeszcze mieć danych faz.

## 10. MAP-06B — w samochodzie: jeden przejazd walidacyjny

To pierwszy wymagany wyjazd w tym planie. Celem jest mapowanie, nie jazda według rekomendacji.

1. Przed wyjazdem: telefon w uchwycie, działające USB/ADB i GPS, sprawdzony lokalny podkład, wybrana właściwa trasa/kierunek. Uruchom nowe nagranie i zapisz jego ID oraz wersję trasy.
2. Postój 30–60 s przed początkiem odcinka. Sprawdź, czy pozycja jest świeża i aplikacja nie przenosi jej na inną jezdnię. Niewiarygodny pomiar nie jest powodem do wymuszenia MATCHED.
3. Przejedź raz przygotowany odcinek normalnie, zgodnie z ruchem. Pasażer obserwuje kolejność punktów, malejący dystans i moment mijania linii; kierowca nie obsługuje aplikacji.
4. Pasażer zapisuje czas/ID punktu, gdy dystans lub przypisanie wyglądają źle. Jeśli rejestruje kolor, odróżnia „widzę czerwone” od „właśnie zmieniło się na czerwone”. Nagranie wideo jest opcjonalne, nie warunek testu.
5. Jeżeli naturalny i legalny przebieg trasy na to pozwala, obejmij zjazd poza korytarz; brak takiego przypadku uzupełnia test syntetyczny albo osobny przejazd. Nie trzeba wykonywać specjalnego manewru.
6. Po odcinku: postój 30–60 s, zakończ nagranie, sprawdź kompletność. Zachowaj uwagi pasażera i run ID.

Po powrocie porównaj replay z notatkami: właściwa jezdnia/kierunek lub jawna niepewność, kolejność linii, brak fałszywych zdarzeń, poprawne zachowanie przy zatrzymaniu/zjeździe. Bez niezależnego wzorca nie deklaruj dokładności „do 5 m”.

Wynik odbioru: `PASS`, `FAIL` lub `INCONCLUSIVE`, z listą sprawdzonych przypadków i pozostałych niewiadomych. Jedna udana jazda nie weryfikuje całego miasta ani wszystkich warunków GPS.

## 11. MAP-07 — implementujemy: kontrolowane podłączenie rekomendacji

Szkielet bramki i jej testy można przygotować wcześniej. Włączenie rekomendacji live dla trasy następuje po odbiorze mapowania i sprawdzeniu pozostałych danych.

`LiveRecommendationEligibility` zwraca `allowed` i wszystkie `reason_codes`. Wymagania łączne:

- świeża próbka z wiarygodnie określonym wiekiem w obsługiwanym setupie;
- MATCHED, potwierdzony kierunek FORWARD, dostępna wiarygodna prędkość;
- geometria i używane linie po weryfikacji terenowej;
- zweryfikowane ograniczenie dla właściwego odcinka;
- wystarczająco wiarygodne dane faz według istniejących zasad predykcji, powiązane z właściwymi sygnałami;
- poprawne przeliczenie czasu pomiaru na dziedzinę zegara predykcji, bez użycia zegara symulacji jako UTC.

Brak warunku daje brak prędkości docelowej i czytelny powód. Nie blokuje samego GPS, mapy, nagrywania ani odległości. Dane syntetyczne nie mogą odblokować rekomendacji w live.

Solver otrzymuje zaakceptowane `s`, rzeczywistą prędkość i właściwy czas przez jawny adapter wejścia live. Nie podmieniaj po cichu `self.position` symulacji. Testuj rozdzielenie trybów i natychmiastowe wycofanie rekomendacji po utracie warunku.

## 12. Pakiety pracy dla kolejnego modelu

W każdym pakiecie: przeczytaj zmieniany kod, wykonaj zakres, uruchom adekwatne testy, zaktualizuj poniższą checklistę i zapisz krótkie podsumowanie. Nie rozpoczynaj automatycznie testu drogowego. Nie przepisuj całego planu w odpowiedziach.

### Pakiet A — implementujemy: MAP-01 i MAP-02

- [x] Swobodny GPS replay i rzeczywisty ślad.
- [x] Lokalny podkład oraz działanie bez internetu.
- [x] Oddzielny model geometrii, `s`, wersja/hash i testy.
- [x] Obsługa braku trasy/świateł; bez zmiany zachowania solvera symulacji.

Prompt: „Wykonaj pakiet A z docs/m8-mapping-implementation.md. Zachowaj istniejący GPS, logger i symulację. Użyj lokalnego nagrania Chomiczówki do odbioru, jeżeli jest dostępne. Zakończ testami i aktualizacją checklisty; nie przechodź do następnego pakietu.”

### Pakiet B — implementujemy: MAP-03

- [x] Metadane wieku próbki w Androidzie/backendzie, kolejka i reset ciągłości.
- [x] Matcher i kontrakt wyniku.
- [x] Syntetyczne scenariusze geometrii, dwuznaczności, czasu, kierunku, skoku, postoju i luki.
- [x] Podłączenie matchera do GPS replay bez ingerencji w pozycję symulacji.

Prompt: „Wykonaj pakiet B z docs/m8-mapping-implementation.md. Najpierw świeżość i granice strumieni, następnie matcher i replay. Nie zmieniaj prędkości na podstawie punktów dopasowanych. Zakończ testami, informacją o wymaganym APK i aktualizacją checklisty.”

### Pakiet C — implementujemy: MAP-04 i MAP-05

- [x] Model linii, wybór kolejnego punktu i detektor przekroczeń.
- [x] Ustalone z użytkownikiem granice/kierunek pilotowego odcinka.
- [x] Inwentaryzacja z jawnym stanem weryfikacji; nie oznaczać desk check jako field check.
- [x] Integracja live/API/UI i osobne logi pochodne.
- [x] Test telefonu na postoju oraz utraty/odzyskania połączenia.

Prompt: „Wykonaj pakiet C z docs/m8-mapping-implementation.md. Przygotuj kod i testy niezależnie od ustalenia granic trasy. Nie zgaduj lokalizacji linii ani faz. Po integracji przeprowadź ze mną krótki odbiór telefonu na postoju.”

### Pakiet D — implementujemy: MAP-06A i przygotowanie MAP-07

- [x] Pełna regresja offline oraz raport gotowości do jazdy.
- [x] Bramka rekomendacji z testami i adapter wejścia live.
- [x] Instrukcja konkretnego przejazdu z ustalonymi granicami i punktami w `m8-field-test.md`.
- [x] Rekomendacje live pozostają niedostępne bez kompletu warunków.

Prompt: „Wykonaj pakiet D z docs/m8-mapping-implementation.md. Zweryfikuj całość offline, przygotuj i przetestuj bramkę rekomendacji oraz zapisz konkretną instrukcję testu drogowego. Nie przedstawiaj niewykonanego testu terenowego jako zaliczonego.”

### Pakiet E — w samochodzie: MAP-06B

- [ ] Kontrolowany przejazd i notatki pasażera.
- [ ] Kompletny log i identyfikacja wersji.
- [ ] Analiza po jeździe: PASS/FAIL/INCONCLUSIVE i regresje dla wykrytych błędów.

### Pakiet F — implementujemy: zakończenie MAP-07

- [ ] Poprawki wynikające z jazdy, bez dopasowywania progów wyłącznie do jednego śladu.
- [ ] Aktualizacja stanu weryfikacji geometrii/linii na podstawie dowodów.
- [ ] Uruchomienie rekomendacji tylko jeżeli dostępne są również zweryfikowane ograniczenia i odpowiednie dane faz; w przeciwnym razie poprawnym wynikiem pozostaje pozycja i dystanse z jawnym brakiem rekomendacji.

## 13. Zasady przekazania i oszczędzania pracy

- Nie odtwarzaj architektury z historii rozmowy: ten dokument i aktualny kod są punktem startowym. High-level cel pozostaje w `m8-mapping-plan.md`.
- Każdy pakiet zostawia działającą aplikację. Nie łącz wszystkich etapów w jedną trudną do sprawdzenia zmianę.
- Dopisz pod checklistą faktyczne zmienione pliki, wykonane polecenia testów, wynik i ograniczenia. Odhaczaj tylko ukończone elementy.
- Nie poprawiaj przy okazji całej aplikacji ani wyglądu nawigacji. Dostosuj UI tylko do diagnostyki i czytelnego rozdzielenia trybów.
- Rutynowe decyzje implementacyjne podejmuj samodzielnie. Pytaj o fakty terenowe, których nie da się ustalić z danych, szczególnie granice i kierunek trasy.
- Gdy kontrakt wymaga zmiany, uzasadnij ją konkretnym przypadkiem i testem; zaktualizuj specyfikację, aby następny pakiet nie korzystał z nieaktualnych założeń.
- Zmiana modelu nie gwarantuje poprawności. Kontrolę zapewniają jawne kontrakty, testy regresyjne, odtwarzalne logi i odbiór terenowy.

## 14. Stan odbioru z 19.09.2026

Zmieniono backend świeżości, matcher, replay, zdarzenia linii, analizę pochodną,
API, trzy tryby UI oraz natywny payload Androida. Analiza pełnego logu działa jako
autoryzowane zadanie w tle. Dodano jawny, fail-closed adapter wejścia live do
solvera; nie modyfikuje pozycji symulacji.

Wykonane kontrole:

- `python -m unittest discover -s tests -v`: 165 testów, wynik OK; jeden historyczny
  test Tk pominięty z powodu braku Tcl/Tk;
- `node --check greenwave/web/app.js`: OK;
- `node tests/mobile_flow.cjs`: PASS;
- `gradlew.bat testDebugUnitTest assembleDebug`: BUILD SUCCESSFUL, cztery testy
  Androida, APK debug zbudowane;
- lokalny replay `5cef7b3e1faa435f9cdb42fa249683a6`: 584 próbki i 582,99 s;
  bez trasy wszystkie wyniki `NO_ROUTE`, z celowo niepasującą trasą Żwirki i
  Wigury 582/584 próbek `OFF_ROUTE`; SHA-256 `raw.csv` bez zmian;
- odbiór telefonu `6bad97111dbc4422afaf2beb256509ef`: 54 próbki Android Fused,
  kontrolowana przerwa odbioru 32,55 s, 28 próbek kolejki oznaczonych
  `MEASUREMENT_STALE` i niedopuszczonych do sterowania live, następnie odzyskanie
  `FRESH`; kolejka telefonu wróciła do zera;
- pilot Arkadia `arkadia_maczka_okopowa_v1`: start 52.268550, 20.932530,
  koniec 52.253278, 20.981089, 3,76 km, geometria `DESK_CHECKED`, limit 50 km/h
  `DESK_CHECKED` i dziesięć roboczych linii `DRAFT`; pierwszy przejazd kończy się
  przy Powązkowskiej/Okopowej bez przedłużenia do ronda ONZ;
- ręczny odbiór przeglądarki: tryb live bez telefonu, wybór trasy DRAFT, swobodny
  replay Chomiczówki, opis czasu pomiaru/odbioru i filtrowanie listy do nagrań GPS.

`scripts/check_web.cjs` nie został uruchomiony, ponieważ lokalne środowisko nie ma
modułu Playwright. Ten sam przepływ sprawdzono w przeglądarce aplikacji. Do
zamknięcia pozostają tylko pozycje checklisty wymagające telefonu po instalacji
nowego APK albo faktów i dowodów z terenu.
