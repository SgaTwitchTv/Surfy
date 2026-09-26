# M8 — plan mapowania GPS na trasę

Status: plan do implementacji. Zakres: odtworzenie dowolnego nagrania GPS, lokalizacja na wybranym korytarzu oraz odległość do właściwych linii zatrzymania. Czasy faz pozostają osobnym źródłem danych.

Szczegółowe kontrakty, algorytm, kryteria odbioru oraz gotowe pakiety pracy dla kolejnego modelu: [instrukcja implementacji](m8-mapping-implementation.md).

## Punkt wyjścia

Nagranie `5cef7b3e1faa435f9cdb42fa249683a6` jest testem sensora i loggera na Chomiczówce: 584 próbki, około 583 s między pierwszą a ostatnią, wszystkie ANDROID_FUSED. Start i koniec dzieli około 29 m. Nie jest walidacją zielonej fali ani geometrii Żwirki i Wigury. Pole corridor_id opisuje wybrany zestaw aplikacji, nie dowodzi przebywania na tym korytarzu. Surowego nagrania nie zmieniamy.

Dokładność zwracana przez telefon jest oszacowaniem urządzenia, nie pomiarem rzeczywistego błędu względem niezależnego wzorca. Podobnie status READY obecnego raportu dotyczy progów jakości telemetrii, nie poprawności przypisania do drogi.

## MAP-01 — rzeczywisty ślad i replay

- Wybór nagrania niezależnie od aktywnego korytarza, początek/koniec, ślad WGS84, prędkość i dokładność próbki.
- Replay według czasu pomiaru, z osobną informacją o czasie odbioru. Tryb diagnostyczny pokazuje także próbki odrzucone.
- Lokalny podkład wektorowy ulic dla obszaru testowego z pochodzeniem, datą danych i atrybucją OSM; po pobraniu działa bez internetu.
- Swobodny pomiar bez korytarza. Wybrany korytarz i rozpoznany korytarz to oddzielne pola.
- Odbiór: zapisany przejazd pokazuje prawdziwe współrzędne i nie trafia na demonstracyjną trasę Żwirki i Wigury.

## MAP-02 — geometria korytarza

- Wersjonowana, uporządkowana linia przejazdu: segmenty, właściwa jezdnia, kierunek i dozwolone połączenia.
- Współrzędne przeliczane do lokalnego układu metrycznego; skumulowana długość s w metrach od początku trasy.
- Oddzielne stany weryfikacji geometrii, linii zatrzymania, ograniczeń prędkości i czasów faz. Brak jednego nie unieważnia pozostałych.
- Pętle i powtórne przejazdy przez to samo miejsce mają odrębne wystąpienia segmentu w trasie.
- Odbiór: długości i kierunki są sprawdzalne, a brak świateł nie uniemożliwia testowania geometrii.

## MAP-03 — dopasowanie na żywo

- Kandydaci na pobliskich segmentach; ocena odległości, dokładności GPS, wiarygodnego kierunku, poprzedniego dopasowania i przemieszczenia możliwego przy zmierzonej prędkości.
- Wynik: segment, pozycja dopasowana, s, odległość poprzeczna, kierunek, status i przyczyna niepewności.
- Statusy: MATCHED, UNCERTAIN, OFF_ROUTE, WRONG_DIRECTION, STALE. Wynik oceny nie jest skalibrowanym prawdopodobieństwem.
- Dwuznaczność między sąsiednimi jezdniami pozostaje widoczna. Brak wymuszania dopasowania przy zjeździe, nawrocie lub dużej luce.
- Przy postoju nie używamy niewiarygodnego azymutu do zmiany kierunku. Po luce ponownie ustalamy położenie; nie zakładamy, że auto nadal stoi.
- Prędkość natywna zachowuje własne źródło i dokładność. Przesunięcia punktu przy dopasowaniu do mapy nie generują sztucznej prędkości.
- Pierwsza wersja działa na wybranej trasie lokalnie. Ogólnomiejski matcher/routing jest rozszerzeniem, nie warunkiem tego etapu.

## MAP-04 — linie zatrzymania i światła

- Punkt kontrolny oznacza linię zatrzymania dla konkretnej jezdni, kierunku i manewru, a nie środek skrzyżowania.
- Zapis: współrzędne/geometria linii, s, identyfikator, źródło i data weryfikacji. Nie przypisujemy pasa, jeżeli GPS go nie rozróżnia.
- Odległość do punktu liczona wzdłuż trasy: s_punktu − s_pojazdu, z uwzględnieniem niepewności obu pozycji.
- Przekroczenie wymaga ciągłego, wiarygodnego dopasowania przed i za linią; pojedynczy skok ani luka nie tworzą potwierdzonego przejazdu. Zdarzenie jest deduplikowane w ramach danego przejazdu.
- Położenie świateł nie dostarcza koloru ani harmonogramu. Nieznane fazy pozostają nieznane.

## MAP-05 — widok live i logi pochodne

- Prawdziwa pozycja auta, ślad surowy/dopasowany, aktualny kierunek, jakość dopasowania, kolejny zweryfikowany punkt i dystans.
- Przejazd poza aktywną trasą jest normalnym stanem z dostępnym GPS, ale bez rekomendacji korytarza.
- Nieaktualne lub buforowane próbki zostają w historii; nie sterują bieżącą pozycją. Wiek pomiaru jest rozróżniony od wieku odbioru.
- Log dopasowania jest pochodny i zawiera wersję algorytmu, geometrii oraz odwołanie do surowej próbki. Niezmienny raw.csv pozostaje źródłem.

## MAP-06 — walidacja offline i w terenie

- Testy geometrii: prosta, zakręt, dwie jezdnie, skrzyżowanie, powrót po tej samej ulicy, pętla, zjazd, nawrót, postój, utrata danych i ponowne złapanie pozycji.
- Replay Chomiczówki jako regresja na danych rzeczywistych; przebieg ulic potwierdzamy na mapie. Ten log nie jest centymetrowym wzorcem pozycji.
- Replay online przetwarza próbki kolejno bez podglądu przyszłości. Ewentualne wygładzanie całego nagrania jest osobnym wynikiem analizy.
- Warunki odbioru: brak skoków na odległe segmenty, poprawny kierunek lub jawna niepewność, brak fałszywego przejazdu przez linię, rozpoznany zjazd i odzyskanie dopasowania.
- Po walidacji offline: jeden kontrolowany przejazd docelowym odcinkiem, porównanie kolejności punktów i odległości. Obsługę oraz obserwacje wykonuje pasażer lub użytkownik na postoju.

## MAP-07 — podłączenie rekomendacji

- Oddzielne tryby symulacja/live. Solver dostaje rzeczywistą prędkość i s dopiero po wiarygodnym dopasowaniu.
- Rekomendacja wymaga świeżych pomiarów, zweryfikowanej geometrii, ograniczenia prędkości i wystarczająco wiarygodnych danych faz.
- Bez danych faz panel nadal pokazuje pozycję i dystanse; wynik prędkości docelowej ma jawny powód niedostępności.

## Kolejność pracy

Najpierw MAP-01 i MAP-02, następnie MAP-03 z testami i replayem (część MAP-06). Potem MAP-04 i MAP-05, przejazd weryfikacyjny oraz MAP-07. Do prac na zapisanym nagraniu telefon nie musi być podłączony. Pierwszy pilot ma identyfikator `arkadia_maczka_okopowa_v1`: od świateł przy Reymonta/Maczka (`52.268550, 20.932530`) ulicą Maczka i Powązkowską do świateł Powązkowska/Okopowa (`52.253278, 20.981089`). Pierwsza wersja kończy się przy McDonald’s/Arkadii; rozszerzenie do ronda ONZ będzie osobną geometrią.

Opcja późniejsza: OSRM Match przy dopasowywaniu dowolnych tras do sieci ulic, najlepiej uruchamiany lokalnie. Dokumentacja: https://project-osrm.org/docs/v5.24.0/api/#match-service . Podkład mapy, dopasowanie GPS, routing i dane faz to osobne warstwy.
