# GreenWave (repozytorium Surfy)

Lokalne laboratorium zielonej fali. **Wykonane M1–M7 (do L10) oraz pierwszy etap M8**:
mapa, obserwacje, predykcja, resynchronizacja i planowanie przez wiele świateł
z dynamiką pojazdu, kosztem zatrzymań, hamowania, zmian przyspieszenia, czasu
i ryzyka, trwały logger surowych przejazdów oraz diagnostyczny odbiór GPS z telefonu.

## Uruchomienie

Python 3.11+, bez instalowania zależności pip:

```powershell
python -m greenwave
```

Aplikacja otwiera się w przeglądarce pod adresem `http://127.0.0.1:8765`.
Serwer działa wyłącznie lokalnie. Zatrzymanie: Ctrl+C w terminalu.
Jeśli port jest zajęty, użyj `python -m greenwave --port 8766` lub `--port 0`.
Opcja `--no-browser` uruchamia sam serwer. Mapa, style i skrypty są lokalne;
nie potrzeba internetu ani klucza mapowego.

Starszy panel Tkinter z P02 jest dostępny przez `python -m greenwave --lab`.
Ten panel pozostaje historycznym narzędziem M1/P02; nowa mapa i M2 są w widoku
przeglądarkowym. Tkinter wymaga lokalnej instalacji Tcl/Tk.

## Szybki test M4 na komputerze

Zostaw zaznaczone **Jedź według rekomendacji**, ustaw tempo 5× lub 10× i kliknij
Start. Pojazd rusza od zera, rozpędza się w granicach modelu i podąża za celem.
Duża liczba to prędkość docelowa, a mniejsza to aktualna prędkość pojazdu.
M4 pokazuje pojedynczy cel (np. 34–34 km/h), zweryfikowany dla całej wybranej trajektorii.

Odznacz automatyczne podążanie, aby suwakiem zadawać własny cel prędkości.
Zmiana suwaka nie powoduje natychmiastowego skoku prędkości. Symulowany kierowca
reaguje na niezielony sygnał także w tym trybie.

W sekcji **Plan korytarza — trajektoria i koszt** zobaczysz plan kolejnych punktów,
zatrzymania, składniki kosztu, alternatywy i porównanie z wyborem lokalnym.
Niżej są profil pierwszego polecenia i lista przekroczonych linii. Brak wykonalnego profilu
lub ważnej prognozy usuwa liczbę docelową i pokazuje powód. Niewykonalna sytuacja
przy sygnalizacji przerywa symulację i wymaga nowej sesji, bez przestawiania pojazdu.

Obserwacje i diagnostykę M2 można sprawdzić tak:

1. Zostaw zestaw **S1–S5 · dane syntetyczne**, kliknij Start i następnie Pauza.
2. Wybierz S3 na liście lub mapie. Wybierz „Właśnie zaczęła się faza” i „Zielone teraz”.
   Zmienią się okna S3. Pozostałe modele nie są automatycznie przesuwane.
3. Otwórz „Diagnostyka prognoz i modelu”: porównaj offset, korektę i źródło.
4. Wybierz S1 i zgłoś początek fazy. Konfiguracja demo zawiera jawne relacje S1→S2–S5;
   dalsze prognozy zostaną skorygowane, o ile nowsza obserwacja punktu nie ma pierwszeństwa.
5. „Widzę ten kolor teraz” zapisuje aktualny kolor bez wymyślania początku fazy.
   Sprzeczność z modelem wstrzymuje prognozę do ponownej synchronizacji.
6. W diagnostyce można włączyć jitter i wydłużenia zielonego (nowa sesja).
   Prawda symulatora pozostaje niezależna od prognoz.
7. Wybierz niezweryfikowany zestaw warszawski: fazy pozostają UNKNOWN, pozycja
   i znaczniki są wyłączone. GREEN NOW zapisuje obserwację, ale nie wymyśla cyklu.

Mapa obsługuje przesuwanie, zoom i powrót do całej trasy. Pozycja sondy i kolory
punktów odświeżają się podczas symulacji. M4 analizuje domyślnie do pięciu kolejnych
świateł na danych testowych; ten etap nie jest doradcą jazdy drogowej.

M5 zapisuje przejazd przyciskiem **Rozpocznij nagranie**. Pliki trafiają do
`data/runs/<run_id>/`; sekcja nagrań pozwala pobrać zakończony zapis jako ZIP.
Replay i seek należą do M6.

W sekcji **Replay nagrania** wybierz zakończony przejazd, wczytaj go, ustaw tempo
1×–10×, odtwarzaj, zatrzymuj i przewijaj suwakiem. Replay działa niezależnie od
bieżącej symulacji.

Sekcja **Analiza przejazdu i jakości GPS** liczy metryki z zakończonego CSV. Raport
pokazuje częstotliwość i luki pomiarów, dokładność GPS, dostępność oraz źródła
prędkości, a także przejścia postój–ruch. Rozdziela przerwy dostawcy lokalizacji
telefonu od dodatkowych opóźnień transportu. Plik źródłowy pozostaje niezmieniony;
analiza odrzuca zapis z niezgodnym hashem lub przerwaną kolejnością rekordów.

Telefon można podłączyć przez USB i `adb reverse`. Strona mobilna przesyła surową
lokalizację, a serwer ocenia jej jakość, wylicza prędkość zastępczą i filtruje dryf
podczas postoju. Pełna instrukcja uruchomienia i kontrolowanego nagrania znajduje się
w [docs/phone-gps.md](docs/phone-gps.md). Natywny nadajnik Android oraz mapowanie
pozycji na rzeczywisty korytarz pozostają kolejnymi etapami M8.

## Dane i ich znaczenie

- `data/corridors/synthetic_s1_s5.json`: testowe fazy, odległości i limit.
- `data/corridors/zwirki_wigury.json`: niezweryfikowana inwentaryzacja, nieznane parametry null.
- `data/prediction/`: ustawienia horyzontu, marginesów, ważności i jawne relacje.
- `data/maps/warsaw.json`: lokalny wyciąg geometrii OpenStreetMap i odcinek jezdni.
- `data/solver.json`: dynamika pojazdu, minimalna prędkość, marginesy i stabilizacja.
- `data/trajectory.json`: wagi kosztu, horyzont, liczba punktów i szerokość przeszukiwania M4.

**Znaczniki S1–S5 są rozmieszczone testowo na dostępnym odcinku mapy. Nie są
zweryfikowanymi warszawskimi liniami zatrzymania.** Mapa obejmuje fragment ulicy,
nie pełną trasę Wawelska–lotnisko; pozycja demo jest normalizowana na ten fragment.
Geometria mapy nie uzupełnia automatycznie nieznanych danych korytarza.
Źródło, data pobrania i licencja ODbL są w metadanych pliku mapy.
© [OpenStreetMap contributors](https://www.openstreetmap.org/copyright).

Margines czasowy nie jest skalibrowanym przedziałem ufności. Confidence pozostaje
null, gdy nie podano jego podstawy. Przy podanej wartości jest prezentowany wyłącznie
jako malejący indeks modelu, nie prawdopodobieństwo. Domyślny model wygasa po 240 s;
nowa obserwacja początku fazy może go odnowić.

UTC rejestruje czas obsługi obserwacji przez lokalny serwer, a zegar monotoniczny
steruje tempem symulacji. Nie znamy opóźnienia reakcji operatora. W niezweryfikowanym
korytarzu czas modelu oznacza czas UTC od początku sesji, niezależny od pauzy symulacji.

**Historia jest tylko w pamięci serwera.** Reset zachowuje wcześniejsze sesje;
zamknięcie samej karty nie usuwa historii. Zatrzymanie serwera ją usuwa. Trwały logger
jest zakresem M5. UI pokazuje ostatnie 100 obserwacji.

## Testy

```powershell
python -m unittest discover -s tests -v
node tests/mobile_flow.cjs
```

Test Tkinter może zostać pominięty w środowisku bez dostępu do Tcl/Tk; testy HTTP
wymagają dostępu do lokalnych gniazd sieciowych. Scenariusz przeglądarkowy:

```powershell
python -m greenwave --no-browser --port 8766
# W drugim terminalu; Playwright oraz Edge są potrzebne tylko do tego testu:
$env:GW_TEST_URL = 'http://127.0.0.1:8766'
node scripts/check_web.cjs
```

Playwright musi być dostępny jako moduł Node albo wskazany przez
`GW_PLAYWRIGHT_MODULE`. Test zmienia sesję, więc uruchamiaj go na osobnym serwerze.
Zrzuty ekranu trafiają do ignorowanego przez Git katalogu `artifacts/web-check`.

Architektura: [docs/architecture.md](docs/architecture.md).
Kontrakt i odbiór M2: [docs/m2.md](docs/m2.md).
Profile, ograniczenia i testy M3: [docs/m3.md](docs/m3.md).

Szczegóły P07/P08 i ograniczenia przeszukiwania: [docs/m4.md](docs/m4.md).
Logger L09: [docs/m5.md](docs/m5.md).
Replay: [docs/m6.md](docs/m6.md).
Analiza danych M7: [docs/m7.md](docs/m7.md).
