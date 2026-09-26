# GreenWave — UI komputera, telefonu i obserwacje z kamery

Status: plan do implementacji, 26.09.2026. Nie wdrożono detektora ani nowych UI.
Rozszerzenie M8 z wcześniejszym prototypem M9. Nie zastępuje weryfikacji faz.

## Cel pierwszej wersji

Kamera USB podłączona do komputera albo plik wideo dostarcza obraz.
Osobny proces wykrywa sygnalizatory, rozpoznaje stan i utrzymuje ich ślady.
GreenWave zestawia obraz z GPS i wybraną trasą. Początkowo pasażer potwierdza
przypisanie śladu do linii. Zdarzenia CV pozostają kandydatami, niezależnymi od
ręcznych obserwacji i aktywnego modelu predykcji.

Możemy zacząć bez samochodu: UI, kontrakty, pliki wideo, testy syntetyczne,
kamera przy komputerze. Ocena dalekiego zasięgu i przypisania w ruchu wymaga
później prawdziwych nagrań drogowych.

## Gałęzie i kolejność integracji

Najpierw sprawdzić stan Git i zapisać obecny ukończony zakres M8 w bazowym
commicie. Obecne niecommitowane zmiany nie przejdą automatycznie do worktree.
Nie resetować ani nie usuwać ich. Planowane gałęzie:

- `codex/ui-vision-contracts`: wspólne DTO, mocki, reguły źródeł i czasu.
- `codex/ui-desktop`: panel laboratoryjny i nawigacyjny komputera.
- `codex/ui-mobile`: widok nawigacyjny telefonu i istniejący odbiornik Android.
- `codex/vision-camera`: odczyt kamery/wideo, detektor, klasyfikator, tracker.
- `codex/vision-association`: GPS, punkty trasy, potwierdzanie przypisania.
- `codex/ui-vision-integration`: integracja i testy całego przepływu.

Używać osobnych worktree do równoległych checkoutów. UI opierać na wspólnym
kontrakcie, nie na strukturach konkretnego YOLO. Pierwsze zmiany scalać małymi
działającymi pakietami; gałęzie rozwijać z aktualizowanej wspólnej bazy.

## UV-01 — kontrakty i scenariusze demonstracyjne

Nowe struktury:

- `CameraFrameRef`: camera/session/frame ID, czas przechwycenia monotoniczny,
  oszacowany UTC, niepewność czasu, rozmiar, referencja pliku/PTS.
- `VisionDetection`: ramka, bbox, stan, typ/piktogram, wynik modelu, hash modelu.
- `VisionTrack`: session/track ID, pierwsza i ostatnia ramka, historia stanów,
  widoczność, jakość, stan utraty śladu.
- `SignalAssociation`: track ID, route ID, geometry hash, line ID, movement,
  metoda, kandydaci, wynik, status UNASSIGNED/CANDIDATE/CONFIRMED/AMBIGUOUS.
- `VisionObservation`: stan, źródło CV, przedział czasu zmiany, dowody ramek,
  przypisanie, przyjęcie/odrzucenie/przegląd oraz wersja algorytmu.

Stany obejmują RED, YELLOW, GREEN, RED_YELLOW, OFF i UNKNOWN; miganie i
piktogramy mają osobne pola. Nie mapować RED_YELLOW na GREEN.
Wynik sieci nie jest skalibrowanym prawdopodobieństwem poprawności systemu.

Mocki: brak kamery, dobre wykrycie, kilka lamp, nieznany kolor, sprzeczne lampy,
utrata obrazu, STALE GPS, przeciwległy kierunek, utrata połączenia telefonu.
Odbiór: serializacja i brak niejawnego przekształcania kandydatów w fazy live.

## UV-02 — wybór modelu i próba na tym komputerze

Porównać mały detektor z rozpoznawaniem stanów oraz wariant detektor +
klasyfikator wycinków. Zwykła klasa traffic light nie wystarcza do koloru.
Sprawdzić kod, dostępność wag, licencję kodu, wag i danych, mapę klas oraz
protokół preprocessingu. Model pobierać z odnotowaną wersją i SHA-256.

Kandydaci badawczy:
- https://github.com/KASTEL-MobilityLab/traffic-light-detection
- https://github.com/Syazvinski/Traffic-Light-Detection-Color-Classification
- https://docs.ultralytics.com/
- https://www.ultralytics.com/license

Pierwszy projekt zawiera również relevance assignment, ale jest prototypem
badawczym. Drugi publikuje modele nano/small/medium i przykłady kamerowe;
nie przyjmować prawa do wykorzystania wag bez sprawdzenia licencji.
Ultralytics i pierwszy projekt mają wariant AGPL; decyzję licencyjną zapisać
przed zależnością produkcyjną. Eksport ONNX nie zmienia licencji modelu.

Przetwarzanie w osobnym środowisku CV. Nie wymuszać zależności ML w istniejącym
Pythonie 3.14 bez sprawdzenia dostępnych pakietów. Runtime zgłasza AMD64;
sprawdzić rzeczywisty OS/CPU i możliwość emulacji na Surface przed wyborem
akceleratora. Nie zakładać obsługi CUDA ani wykorzystania NPU.

Benchmark na rzeczywistym sprzęcie: czas inferencji p50/p95, wiek ramki,
RAM, stabilność, jakość małych obiektów, dzienne/nocne materiały. CPU najpierw;
ONNX Runtime lub inne przyspieszenie dopiero po sprawdzeniu obsługi urządzenia.
Odbiór: reprodukowalny raport i przynajmniej jeden działający backend.

## UV-03 — wspólny design UI

Pozostać przy obecnym backendzie i web UI. Utworzyć wspólne kolory, komponenty
stanu, oznaczenia źródeł, czytelne liczby i scenariusze demonstracyjne.
Rozdzielić ekran nawigacyjny od laboratorium, wykorzystując te same dane.
Rozmiar, układ i interakcje sprawdzić osobno dla komputera oraz telefonu.
Prędkość zalecana nadal niewidoczna jako aktywna, gdy warunki M8 nie są spełnione.

## UV-04 — UI komputera

Widok nawigacji: mapa, bieżąca prędkość, rekomendacja/jej brak, najbliższe punkty,
dystans, stan obserwowany versus przewidywany, wiek danych i ich źródło.
Laboratorium: kamera z bbox i track ID, przypisania, konflikty, ręczne przyciski,
replay, wspólna historia i raport kompletności. Pokazać powód UNKNOWN/STALE.
Wideo nie może blokować GPS, HTTP ani loggera. Zamknięcie panelu nie zmienia faz.
Odbiór: istniejące działania nadal działają, mocki pokazują wszystkie stany.

## UV-05 — UI telefonu

Pierwszy zakres to responsywny ekran nawigacyjny istniejącej aplikacji webowej;
natywna aplikacja Android nadal dostarcza GPS. Nie zastępować jej geolokalizacją
w przeglądarce. W obecnym setupie dostęp przez USB/ADB localhost.

Ekran: mapa, duże liczby, najbliższe punkty, połączenie, świeżość i przyciski
pasażera. Laboratorium i podgląd kamery opcjonalne. Sprawdzić pion/poziom,
czytelność, uprawnienia, pracę odbiornika po przełączeniu do przeglądarki,
rozłączenie i wznowienie. Kamerę nadal obsługuje komputer.
Samodzielny telefon z własną kamerą/inferencją to późniejszy oddzielny pakiet.

## UV-06 — źródło obrazu i zsynchronizowany zapis

Obsłużyć kamerę USB i plik wideo; konfiguracja urządzenia, rozdzielczość,
FPS, rozłączenie i ponowna inicjalizacja. Worker z ograniczoną kolejką:
live analizuje najnowsze ramki zamiast narastającego opóźnienia; raportuje straty.
Tryb offline może analizować każdą ramkę niezależnie od tempa odtwarzania.

Oryginalne wideo i manifest przechowywać lokalnie poza Git. Oddzielić je od
niezmiennych istniejących raw.csv; zapisać hashe, powiązanie z run ID, PTS,
mapowanie czasu na UTC/monotoniczny i niepewność synchronizacji. Nie przypisywać
czasów historycznego GPS do niesynchronizowanego filmu jako faktów.
Odbiór: odłączenie kamery nie zatrzymuje aplikacji; replay czasu jest powtarzalny.

## UV-07 — wykrywanie i rozpoznawanie stanu

Adapter modelu -> bbox -> wycinek/klasyfikacja -> wynik jakości. Zachować
koordynaty po resize/letterbox/crop. Przetestować czerwonożółte, strzałki,
sygnalizatory pieszych, odbicia, tylne lampy aut, małe obiekty i prześwietlenie.
Gdy wycinek ma za mało informacji, zwracać UNKNOWN. Zasięg mierzyć na danych;
nie deklarować 100/200 m na podstawie samego FPS lub rozdzielczości kamery.
Odbiór: oznaczony zestaw klipów, błędy koloru i false GREEN mierzone osobno.

## UV-08 — śledzenie i momenty zmian

Stabilne ID lamp w kolejnych ramkach, histereza/dowody czasowe, obsługa zasłonięć,
braku widoczności, migania i track switch. Parametry dobrać na walidacji.
Pierwsze zobaczenie zielonego oznacza STATE_SEEN. STATE_START tworzyć wyłącznie
przy rzeczywiście zaobserwowanej zmianie w ciągłym śladzie; czas zmiany to
przedział między ostatnią ramką starego i pierwszą nowego stanu. Utrata śladu
przerywa ten dowód. Nie utożsamiać czasu zakończenia inferencji ze zmianą lampy.
Odbiór: testy resetów i brak fałszywych początków faz po odzyskaniu obrazu.

## UV-09 — przypisanie lamp do punktów trasy

Najpierw pasażer wybiera track i line ID; przypisanie ma zasięg sesji/odcinka i
wygasa przy utracie śladu lub geometrii. Następnie GPS/matcher, kierunek i manewr
zawężają kandydatów. Najbliższa linia nie oznacza automatycznie właściwej lampy.

Posiadamy linie zatrzymania, nie pełną mapę położeń lamp. Do projekcji na obraz
potrzebna będzie inwentaryzacja sygnalizatorów, orientacja, kalibracja obiektywu,
mocowania i pozy pojazdu z uwzględnieniem ich błędów. Monokular nie zapewnia
pewnego dystansu do każdej lampy. Nie sortować lamp po samym rozmiarze bbox.
Rozpoznawanie pasów/strzałek może pomagać, ale jest osobnym źródłem dowodów.

Kilka lamp dla jednej linii grupować tylko przy zgodności przypisania i stanu.
Sprzeczność daje CONFLICT/UNKNOWN. Kilka skrzyżowań śledzić niezależnie;
nieprzypisane lampy pozostają widoczne w laboratorium, bez wpływu na solver.
Odbiór: przypadki skrętu, ruchu poprzecznego, pieszych i dwóch skrzyżowań.

## UV-10 — integracja z historią, przegląd i replay

Zdarzenia CV mają własne źródło, ramki, model/wersję, track i przypisanie.
Kandydaci nie zwiększają liczby potwierdzonych początków faz w raporcie.
Potwierdzenie/odrzucenie użytkownika to osobny zapis, nie nadpisanie detekcji.
Konflikt MANUAL/CV jest widoczny; nie rozstrzygać go ostatnim timestampem.
Pozwolić obejrzeć klip i GPS przy danym zdarzeniu. Import/replay idempotentny.
Odbiór: bezpieczne uruchomienie bez kamery/modelu oraz niezmienność starych logów.

## UV-11 — walidacja offline i stacjonarna

Oddzielić zbiór do doboru parametrów od klipów odbiorowych; nie dzielić sąsiednich
ramek tego samego filmu pomiędzy trening i test. Ręczne etykiety: lampa, stan,
czas/przedział zmiany, kierunek/manewr i właściwa linia.
Mierzyć kolor, false GREEN, przypisanie do złej linii, błędy czasu zmiany,
track switches, UNKNOWN, zasięg, opóźnienie i zużycie zasobów.
Klipy nocne/dzienne oraz odbicia i zasłonięcia osobno. Kamera przy biurku
potwierdza integrację, nie dokładność drogową. Kiedy samochodu brak, można
zbierać pełne cykle z bezpiecznego miejsca stacjonarnie.

## UV-12 — przejazd odbiorowy i powrót do M8

Po odzyskaniu auta: zamocowana kamera, GPS, nagranie, pasażer oznaczający prawdę
referencyjną. CV najpierw tylko w tle, bez sterowania rekomendacją. Porównać
obserwacje manualne/CV i ocenić przypisania oraz opóźnienia.

Dopiero zaakceptowane obserwacje trafiają do uczenia modelu faz. Przewidywanie
niewidocznych świateł nadal wymaga zweryfikowanego modelu lub źródła aktualnego
stanu. Kamera może go aktualizować, ale nie widzi przez zakręt ani przeszkody.
Rekomendacje live zachowują istniejące warunki GPS/geometrii/limitów/faz.

## Kolejność do rozpoczęcia teraz

1. Bazowy commit aktualnego M8 i UV-01.
2. UV-02 jako mały eksperyment wykonalności na Surface.
3. UV-03–05 na mockach; UV-06 bez samochodu.
4. UV-07–08 na nagraniach i kamerze.
5. UV-09 z ręcznym przypisaniem, następnie UV-10–11.
6. UV-12 po dostępności auta; dalsza predykcja i rekomendacje w M8.

Pierwszy osiągalny odbiór: nowy ekran PC/telefon, obraz USB, kolor i track ID,
ręczne przypisanie do linii, zapis i replay — bez automatycznego odblokowania
rekomendacji prędkości.
