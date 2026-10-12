# Udział AI

2026-10-12: użytkownik zlecił rozszerzenie szkolne GreenWave w jednym czacie:
UI, konta, trzy role, własność danych, tabele, walidacja, korekty, AJAX, migracje,
commity, Docker demo, pomiar coverage >=70%, raport i instrukcję. Baza 7ece859,
gałąź codex/school-app, osobny worktree; zakaz zmiany main i prywatnych nagrań.
Wymagana kolejność: audyt → kontrakt → backend → UI → testy → Docker → raport.
To streszczenie promptu; pełny prompt pozostaje w historii tego czatu.

AI (Codex) czyta kod, proponuje kontrakty, implementuje i uruchamia weryfikację.
Wyniki są sprawdzane rzeczywistymi testami, pomiarem pokrycia i scenariuszami
przeglądarkowymi. Testy syntetyczne nie potwierdzają bezpieczeństwa drogowego CV.
Nie wykonano weryfikacji terenowej faz, linii, limitów ani skuteczności YOLO.
Dalsze prompty i dowody weryfikacji należy dopisywać w kolejnych etapach.

Etap backend: test_school_store (7) oraz test_school_http (5) przechodzą.
Test HTTP obejmuje zapis prawdziwego syntetycznego raw.csv i eksport ZIP,
izolację kont, parowanie Android z właścicielem i brak rekomendacji live.
Jedna poprawka po teście: odczyt ciała odrzucanego POST przed odpowiedzią,
aby Windows nie zrywał połączenia przy nieodczytanych bajtach.
