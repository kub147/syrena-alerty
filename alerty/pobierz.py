"""Pobiera komunikaty RSO i zapisuje alerty.json dla mapy Syrena (projekt studencki AGH)."""
import html
import json
import re
import sys
import time
import unicodedata
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ADRES = "https://komunikaty.tvp.pl/komunikatyxml/{w}/wszystkie/{s}?_format=json"
WOJEWODZTWA = ("podkarpackie", "lubelskie")
KOLEJNOSC = ("zagrozenie", "gotowosc", "inny")

# „do odwołania” i „czekaj na odwołanie” nie kończą alarmu, dlatego samo słowo liczy się tylko na początku.
ODWOLANIE_NA_POCZATKU = re.compile(r"^\W*(uwaga\W*|alert rcb\W*)*odwolani[ea]\b")
NIE_ZAGROZENIE = re.compile(
    r"\bodwolano\b|\bodwoluj|brak zagrozen|nie ma zagrozen|zagrozeni\w*[^.]{0,40} (minelo|ustalo)\b|koniec (alarmu|zagrozenia)")
CWICZENIA = re.compile(r"cwicze|trening|proba syren|test syren")
NIE_CWICZENIA = re.compile(r"nie (sa|jest) (to )?(cwicze|trening)")
GOTOWOSC = re.compile(r"atak\w* (powietrzn\w*|rakietow\w*|z powietrza) na ukrain|podniesiono gotowosc")
ZAGROZENIE = re.compile(
    r"zagrozeni\w* (atakiem |uderzeniem )?z powietrza|zagrozeni\w* powietrzn|atak\w* z powietrza"
    r"|atak\w* powietrzn|atak\w* (rakietow|dron)|znajdz bezpieczne miejsce")


def uprosc(tekst):
    tekst = html.unescape(re.sub(r"<[^>]+>", " ", tekst or "")).lower().replace("ł", "l")
    tekst = unicodedata.normalize("NFKD", tekst)
    return re.sub(r"\s+", " ", "".join(z for z in tekst if not unicodedata.combining(z)))


def czas(tekst):
    try:
        return datetime.strptime(tekst, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return None


def klasyfikuj(komunikat, teraz):
    od, do = czas(komunikat.get("valid_from")), czas(komunikat.get("valid_to"))
    if (do and do < teraz) or (od and od > teraz):
        return "nieaktualny"
    t = uprosc(" ".join(str(komunikat.get(p) or "") for p in ("title", "shortcut", "content")))
    if CWICZENIA.search(t) and not NIE_CWICZENIA.search(t):
        return "inny"
    if ODWOLANIE_NA_POCZATKU.search(t) or NIE_ZAGROZENIE.search(t):
        return "inny"
    bez_ukrainy = GOTOWOSC.sub(" ", t)
    if ZAGROZENIE.search(bez_ukrainy):
        return "zagrozenie"
    if GOTOWOSC.search(t):
        return "gotowosc"
    return "inny"


def status(komunikaty, teraz):
    if komunikaty is None:
        return "brak_danych"
    klasy = {klasyfikuj(x, teraz) for x in komunikaty}
    return next((s for s in KOLEJNOSC if s in klasy), "brak_komunikatu")


def pobierz(wojewodztwo):
    wszystkie = []
    for strona in range(5):
        adres = ADRES.format(w=wojewodztwo, s=strona)
        prosba = urllib.request.Request(adres, headers={"User-Agent": "syrena-alerty (projekt studencki AGH)"})
        with urllib.request.urlopen(prosba, timeout=30) as odp:
            dane = json.load(odp)
        wszystkie += dane["newses"]
        if len(wszystkie) >= dane["pagination"]["totalitems"] or not dane["newses"]:
            break
    return list({x["id"]: x for x in wszystkie}.values())


def sprobuj(f, ile=3, przerwa=5):
    for proba in range(ile):
        try:
            return f()
        except Exception as blad:
            print(f"próba {proba + 1}: {type(blad).__name__}: {blad}", file=sys.stderr)
            time.sleep(przerwa)
    return None


def geojson(granice, wynik):
    odczyt = int(datetime.fromisoformat(wynik["odczyt"]).timestamp() * 1000)
    cechy = []
    for f in granice["features"]:
        nazwa = f["properties"]["wojewodztwo"]
        w = wynik["wojewodztwa"].get(nazwa, {"status": "brak_danych", "komunikaty": []})
        wazny = next((k["tytul"] for k in w["komunikaty"] if k["klasa"] == w["status"]), "")
        cechy.append({**f, "properties": {"wojewodztwo": nazwa, "status": w["status"], "tytul": wazny,
                                          "liczba": len(w["komunikaty"]), "odczyt": wynik["odczyt"], "odczyt_ms": odczyt}})
    return {"type": "FeatureCollection", "features": cechy}


def main(plik):
    teraz = datetime.now(ZoneInfo("Europe/Warsaw"))
    lokalny = teraz.replace(tzinfo=None)
    wynik = {"odczyt": teraz.isoformat(timespec="seconds"), "zrodlo": "RSO, komunikaty.tvp.pl", "wojewodztwa": {}}
    for w in WOJEWODZTWA:
        lista = sprobuj(lambda: pobierz(w))
        wynik["wojewodztwa"][w] = {
            "status": status(lista, lokalny),
            "komunikaty": [
                {"klasa": klasyfikuj(x, lokalny), "tytul": x.get("title"), "skrot": x.get("shortcut"),
                 "tresc": x.get("content"), "od": x.get("valid_from"), "do": x.get("valid_to")}
                for x in lista or [] if klasyfikuj(x, lokalny) != "nieaktualny"],
        }
    Path(plik).write_text(json.dumps(wynik, ensure_ascii=False, indent=1), encoding="utf-8")
    granice = json.loads((Path(__file__).parent / "wojewodztwa.json").read_text(encoding="utf-8"))
    Path(plik).with_suffix(".geojson").write_text(json.dumps(geojson(granice, wynik), ensure_ascii=False), encoding="utf-8")
    print({w: (d["status"], len(d["komunikaty"])) for w, d in wynik["wojewodztwa"].items()})


if __name__ == "__main__":
    main(sys.argv[1])
