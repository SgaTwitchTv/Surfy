# Telefon → GreenWave przez USB

1. Podłącz telefon z włączonym USB debugging. `adb devices` musi pokazać `device`.
2. Zatrzymaj poprzedni serwer przez Ctrl+C i uruchom w repozytorium:
   `python -m greenwave --no-browser`
3. W drugim terminalu: `adb reverse tcp:8765 tcp:8765`.
4. Na telefonie w Chrome: `http://localhost:8765/mobile?v=14`.
5. Nagłówek musi brzmieć „GreenWave GPS · 14”. Kliknij „Uruchom pomiary” i zezwól na lokalizację.
6. Na komputerze: `http://127.0.0.1:8765`. Panel „Telefon · GPS na żywo” pokazuje współrzędne, prędkość surową i końcową, źródło prędkości, jakość, kierunek, liczbę próbek oraz czas od odbioru.
7. Telefon pokazuje „komputer potwierdził odbiór” dopiero po udanym POST. Po odłączeniu USB panel komputera po 5 sekundach pokaże brak nowych próbek.

Częstotliwość ustala dostawca lokalizacji telefonu; nie gwarantujemy 1 Hz. Strona próbuje utrzymać ekran aktywny i zgłasza przerwę dłuższą niż 5 sekund, ale karta nadal powinna pozostawać na pierwszym planie. Przy zerwanym serwerze UI oznacza dane jako nieaktualne.

Pole prędkości telefonu jest opcjonalne. Gdy go brakuje, serwer wylicza prędkość z ostatnich punktów tylko dla dokładności do 30 m, odstępu 2–12 s i fizycznie wiarygodnego wyniku. Próbka pozycji do 50 m może służyć do dalszych testów; słabsza pozostaje widoczna wyłącznie diagnostycznie. Panel zawsze wskazuje źródło wyniku (`telefon`, `wyliczona z GPS` albo `brak`) i przyczynę odrzucenia.

Przy postoju telefon może nadal raportować około 1–3 km/h. Serwer zeruje taki dryf dopiero po potwierdzeniu przez co najmniej cztery punkty z minimum czterech sekund, że pozycja pozostaje w małym obszarze. Panel oznacza wtedy źródło jako `potwierdzony postój`; surowa wartość telefonu nadal pozostaje widoczna i trafia do nagrania.

To panel rzeczywistych pomiarów, jeszcze bez mapowania GPS na korytarz. Główny solver i sonda mapy nadal pracują na danych symulacji. IMU nie jest obecnie przesyłane przez ten panel: długość wektora przyspieszenia nie jest przyspieszeniem wzdłużnym samochodu.

Testy: `node tests/mobile_flow.cjs` oraz `python -m unittest discover -s tests -q`.

## Kontrolowane nagranie i raport jakości

1. Uruchom GPS na telefonie i poczekaj, aż licznik próbek rośnie.
2. W głównym interfejsie komputera kliknij `Rozpocznij nagranie`.
3. Stój przez 60 sekund, idź normalnym tempem przez 2–3 minuty i ponownie stój przez 60 sekund.
4. Kliknij `Zatrzymaj nagranie` dopiero po ostatniej minucie postoju.
5. Rozwiń `Analiza przejazdu i jakości GPS`, wybierz najnowsze nagranie i kliknij `Policz raport`.

Raport ma status `READY`, gdy zawiera co najmniej 30 próbek i 30 sekund, nie ma przerwy dłuższej niż 5 sekund, co najmniej 90% próbek jest użytecznych, co najmniej 90% ma dokładność do 50 m i prędkość końcowa jest dostępna w co najmniej 90% próbek. Raport pokazuje także medianę i p95 dokładności, częstotliwość próbek, źródła prędkości, cofnięcia czasu telefonu oraz przejścia postój/ruch.
