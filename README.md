# Syrena – alerty RSO

Moduł projektu studenckiego WebGIS (AGH, GO_26, Jakub Wilk). Co kilka minut odczytuje publiczne komunikaty
Regionalnego Systemu Ostrzegania dla woj. podkarpackiego i lubelskiego i publikuje je jako stronę.

**Nie zastępuje komunikatów służb.** Odczyt starszy niż 15 minut jest pokazywany jako „brak danych”.
Tryb pokazowy: `?cwiczenie=1` (wyraźnie oznaczony).

## Dane
- `dane/Syrena_Punkty_PSP_JW.csv` – punkty schronienia, Komenda Główna PSP, gdziesieukryc.pl / dane.gov.pl nr 28058, CC BY 4.0, stan na 24.11.2026. Wycięto dwa województwa; pominięto 1 punkt z błędnymi współrzędnymi.
- `dane/Syrena_Zgloszenia_JW.csv` – **DANE PRZYKŁADOWE**, obiekty wymyślone.
- `alerty/wojewodztwa.json` – granice województw, PRG (GUGiK), uproszczone.
- `dane/Syrena_Powiaty_JW.geojson` – granice PRG (GUGiK, uproszczone), ludność GUS 31.12.2025 (tabl. III), liczba punktów KG PSP policzona po współrzędnych.
- `dane/Syrena_Straze_JW.csv` – komendy PSP, dane.gov.pl nr 1050 (2022), współrzędne z usługi adresowej GUGiK. Brakuje KM PSP Krosno.
