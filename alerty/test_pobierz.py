import unittest
from datetime import datetime
from pobierz import geojson, klasyfikuj, sprobuj, status

TERAZ = datetime(2026, 11, 24, 12, 0)


def k(tytul, tresc="", od="2026-11-24 11:00:00", do="2026-11-24 23:00:00"):
    return {"title": tytul, "shortcut": "", "content": tresc, "valid_from": od, "valid_to": do}


class Klasyfikacja(unittest.TestCase):
    def test_snieg(self):
        self.assertEqual(klasyfikuj(k("Intensywne opady śniegu"), TERAZ), "inny")

    def test_zagrozenie_bez_polskich_znakow(self):
        tresc = "UWAGA! Zagrozenie atakiem z powietrza. Znajdz bezpieczne miejsce."
        self.assertEqual(klasyfikuj(k("Alert RCB", tresc), TERAZ), "zagrozenie")

    def test_zagrozenie_z_polskimi_znakami(self):
        self.assertEqual(klasyfikuj(k("Zagrożenie atakiem z powietrza"), TERAZ), "zagrozenie")

    def test_podniesiona_gotowosc(self):
        tresc = "Rosyjski atak powietrzny na Ukrainie. Sytuacja jest monitorowana. Podniesiono gotowosc Systemu Obrony Powietrznej RP."
        self.assertEqual(klasyfikuj(k("Alert RCB", tresc), TERAZ), "gotowosc")

    def test_po_terminie(self):
        self.assertEqual(klasyfikuj(k("Zagrozenie atakiem z powietrza", do="2026-11-24 11:30:00"), TERAZ), "nieaktualny")

    def test_odwolanie_nie_zapala_czerwonego(self):
        self.assertEqual(klasyfikuj(k("Odwołanie: zagrożenie atakiem z powietrza"), TERAZ), "inny")

    def test_do_odwolania_to_nadal_zagrozenie(self):
        self.assertEqual(klasyfikuj(k("Zagrożenie atakiem z powietrza do odwołania"), TERAZ), "zagrozenie")

    def test_trening_syren(self):
        self.assertEqual(klasyfikuj(k("Trening syren", "Ćwiczenia: sygnał zagrożenie atakiem z powietrza"), TERAZ), "inny")

    def test_to_nie_sa_cwiczenia(self):
        self.assertEqual(klasyfikuj(k("Zagrożenie atakiem z powietrza", "To nie są ćwiczenia."), TERAZ), "zagrozenie")

    def test_czekaj_na_odwolanie_to_nadal_zagrozenie(self):
        self.assertEqual(klasyfikuj(k("Alert RCB", "Zagrożenie atakiem z powietrza. Czekaj na odwołanie alarmu."), TERAZ), "zagrozenie")

    def test_ustalono_nie_gasi_zagrozenia(self):
        self.assertEqual(klasyfikuj(k("Alert RCB", "Zagrożenie atakiem z powietrza. Ustalono miejsca schronienia."), TERAZ), "zagrozenie")

    def test_odwolano_w_tresci(self):
        self.assertEqual(klasyfikuj(k("Alert RCB", "Odwołano alarm: zagrożenie atakiem z powietrza."), TERAZ), "inny")

    def test_zagrozenie_minelo(self):
        self.assertEqual(klasyfikuj(k("Alert RCB", "Zagrożenie atakiem z powietrza minęło."), TERAZ), "inny")

    def test_zla_data_nie_ukrywa_zagrozenia(self):
        self.assertEqual(klasyfikuj(k("Zagrożenie atakiem z powietrza", do=None), TERAZ), "zagrozenie")


class Status(unittest.TestCase):
    def test_blad_odczytu(self):
        self.assertEqual(status(None, TERAZ), "brak_danych")

    def test_pusto(self):
        self.assertEqual(status([], TERAZ), "brak_komunikatu")

    def test_najwazniejszy_wygrywa(self):
        self.assertEqual(status([k("Śnieg"), k("Zagrożenie atakiem z powietrza")], TERAZ), "zagrozenie")

    def test_same_nieaktualne(self):
        self.assertEqual(status([k("Zagrożenie atakiem z powietrza", do="2026-11-24 11:30:00")], TERAZ), "brak_komunikatu")


class Ponawianie(unittest.TestCase):
    def test_drugi_raz_sie_udaje(self):
        wyniki = iter([OSError("sieć"), [1]])

        def f():
            w = next(wyniki)
            if isinstance(w, Exception):
                raise w
            return w
        self.assertEqual(sprobuj(f, przerwa=0), [1])

    def test_po_trzech_bledach_brak_danych(self):
        def f():
            raise OSError("sieć")
        self.assertIsNone(sprobuj(f, przerwa=0))


class Mapa(unittest.TestCase):
    def test_status_i_czas_na_poligonie(self):
        granice = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {"wojewodztwo": "lubelskie"}, "geometry": None},
            {"type": "Feature", "properties": {"wojewodztwo": "podkarpackie"}, "geometry": None}]}
        wynik = {"odczyt": "2026-11-24T12:00:00+01:00", "wojewodztwa": {
            "lubelskie": {"status": "zagrozenie", "komunikaty": [
                {"klasa": "inny", "tytul": "Śnieg"}, {"klasa": "zagrozenie", "tytul": "Alarm"}]}}}
        a, b = (f["properties"] for f in geojson(granice, wynik)["features"])
        self.assertEqual((a["status"], a["tytul"], a["liczba"]), ("zagrozenie", "Alarm", 2))
        self.assertEqual(a["odczyt_ms"], 1795518000000)
        self.assertEqual((b["status"], b["tytul"]), ("brak_danych", ""))


if __name__ == "__main__":
    unittest.main()
