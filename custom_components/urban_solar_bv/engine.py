"""Calcul de la batterie virtuelle, sans dépendance à Home Assistant (testable seul).

Compteurs : "inj" (injection), "hp" et "hc" (soutirage), en kWh.
Capacité infinie : tout le surplus injecté remplit la batterie.
Le soutirage est servi d'abord par la batterie, le reste par le réseau.
data["tarifs"] = {"hp": (prix, taxe), "hc": (prix, taxe)} en €/kWh, fixé par l'intégration.
"""

COUNTERS = ("inj", "hp", "hc")


def new_data(stock):
    return {
        "stock": float(stock),
        "charge": 0.0,
        "decharge_hp": 0.0,
        "decharge_hc": 0.0,
        "reseau_hp": 0.0,
        "reseau_hc": 0.0,
        "cout": 0.0,
        "economies": 0.0,
        "last": {},
    }


def apply(data, key, value, count=True):
    """Applique une nouvelle valeur d'index. count=False : seul le stock bouge (recalibrage)."""
    last = data["last"].get(key)
    data["last"][key] = value
    if last is None or value <= last:  # premier relevé, ou compteur remis à zéro / remplacé
        return
    delta = value - last
    if key == "inj":
        data["stock"] += delta
        if count:
            data["charge"] += delta
        return
    covered = min(delta, data["stock"])
    data["stock"] -= covered
    if count:
        data[f"decharge_{key}"] += covered
        data[f"reseau_{key}"] += delta - covered
        # Tarifs en vigueur au moment de la décharge : un changement de tarif ne réécrit pas le passé
        price, tax = data.get("tarifs", {}).get(key, (0, 0))
        data["cout"] += covered * tax
        data["economies"] += covered * (price - tax)


def replay(data, stock, base, events, count):
    """Repart de `stock` avec les index `base`, puis rejoue les `events` (instant, clé, valeur) dans l'ordre."""
    data["stock"] = float(stock)
    data["last"] = dict(base)
    for _, key, value in sorted(events, key=lambda e: e[0]):
        apply(data, key, value, count)
