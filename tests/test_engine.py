"""Lancer : python tests/test_engine.py (aucune dépendance)."""
import importlib.util
import pathlib

_path = pathlib.Path(__file__).parents[1] / "custom_components" / "urban_solar_bv" / "engine.py"
_spec = importlib.util.spec_from_file_location("engine", _path)
engine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(engine)


def test_batterie_vide_bascule_reseau_puis_recharge():
    d = engine.new_data(0)
    for k in engine.COUNTERS:
        engine.apply(d, k, 100.0)  # index de référence
    engine.apply(d, "hp", 110.0)   # 10 kWh consommés, batterie vide
    assert d["stock"] == 0 and d["reseau_hp"] == 10 and d["decharge_hp"] == 0
    engine.apply(d, "inj", 105.0)  # 5 kWh injectés
    assert d["stock"] == 5 and d["charge"] == 5


def test_batterie_partiellement_couverte():
    d = engine.new_data(3)
    d["last"] = {"inj": 0.0, "hp": 0.0, "hc": 0.0}
    engine.apply(d, "hc", 5.0)
    assert d["stock"] == 0 and d["decharge_hc"] == 3 and d["reseau_hc"] == 2


def test_capacite_infinie():
    d = engine.new_data(0)
    d["last"] = {"inj": 0.0}
    engine.apply(d, "inj", 100000.0)
    assert d["stock"] == 100000


def test_remise_a_zero_compteur_ignoree():
    d = engine.new_data(10)
    d["last"] = {"hp": 500.0}
    engine.apply(d, "hp", 2.0)  # compteur remplacé
    assert d["stock"] == 10 and d["last"]["hp"] == 2.0
    engine.apply(d, "hp", 3.0)
    assert d["stock"] == 9


def test_recalibrage_ne_touche_que_le_stock():
    d = engine.new_data(0)
    d["charge"] = 42.0
    base = {"inj": 0.0, "hp": 0.0, "hc": 0.0}
    events = [(2, "hp", 8.0), (1, "inj", 5.0), (3, "inj", 6.0)]  # désordonnés exprès
    engine.replay(d, 4, base, events, count=False)
    # 4 + 5 injectés = 9, -8 consommés = 1, +1 injecté = 2
    assert d["stock"] == 2 and d["charge"] == 42 and d["reseau_hp"] == 0


def test_changement_de_tarif_ne_reecrit_pas_le_passe():
    d = engine.new_data(10)
    d["last"] = {"hp": 0.0, "hc": 0.0}
    d["tarifs"] = {"hp": (0.25, 0.05), "hc": (0.20, 0.04)}
    engine.apply(d, "hp", 4.0)   # 4 kWh déstockés : taxe 0,20 €, gain 0,80 €
    d["tarifs"]["hp"] = (0.30, 0.10)
    engine.apply(d, "hp", 6.0)   # 2 kWh : taxe 0,20 €, gain 0,40 €
    engine.apply(d, "hc", 10.0)  # 4 kWh restants en batterie, 6 au réseau : taxe 0,16 €, gain 0,64 €
    assert round(d["cout"], 6) == 0.56 and round(d["economies"], 6) == 1.84
    assert d["reseau_hc"] == 6


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("OK")
