# Urban Solar Virtual Battery

Intégration Home Assistant qui simule la **batterie virtuelle Urban Solar** à partir des compteurs Linky (ZLinky) et l'affiche dans le **tableau de bord Énergie**.

- Le surplus solaire **injecté** sur le réseau remplit la batterie (capacité **illimitée**).
- La consommation est servie **d'abord par la batterie**, puis par le réseau quand la batterie est vide.
- Le stock se **recale** sur le niveau affiché dans l'espace client Urban Solar, à la date et l'heure du relevé.

## Entités

| Entité | Rôle |
|---|---|
| `sensor.stock_batterie_virtuelle` (kWh) | Niveau actuel de la batterie |
| `sensor.charge_batterie_virtuelle` (kWh) | Énergie entrée dans la batterie (cumul) |
| `sensor.decharge_batterie_virtuelle` (kWh) | Énergie sortie de la batterie (cumul) |
| `sensor.import_reseau_hp` / `sensor.import_reseau_hc` (kWh) | Consommation **réellement achetée** au réseau, une fois la batterie vide |
| `sensor.cout_destockage` (€) | Taxes payées sur l'énergie sortie de la batterie |
| `sensor.economies_batterie_virtuelle` (€) | Gain par rapport à un achat au prix réseau |
| `sensor.independance_reseau` (%) | Part de vos soutirages couverte par la batterie |

Les cumuls démarrent à l'installation de l'intégration. Ils sont conservés au redémarrage, et ce qui s'est passé pendant un arrêt de HA est rattrapé depuis l'historique.

## Installation

1. Copiez `custom_components/urban_solar_bv` dans `config/custom_components` (ou installez via HACS).
2. Redémarrez Home Assistant.
3. **Paramètres > Appareils et services > Ajouter une intégration > Urban Solar Virtual Battery**.
4. Renseignez :
   - les compteurs Linky : injection (EAIT), HCHP, HCHC ;
   - le **niveau relevé** sur l'espace client Urban Solar (kWh) et **la date et l'heure** de ce relevé ;
   - les prix réseau et les taxes de déstockage HP/HC.

> La date du relevé doit rester dans la durée de conservation de l'historique (`recorder`, 10 jours par défaut). Si elle est plus ancienne, le stock part du niveau saisi à l'instant de l'installation. Un avertissement apparaît alors dans le journal.

## Recaler le niveau sur Urban Solar

Le relevé Urban Solar est publié avec du retard. Pour s'y recaler : **Outils de développement > Actions > `urban_solar_bv.calibrer`**.

```yaml
action: urban_solar_bv.calibrer
target:
  entity_id: sensor.stock_batterie_virtuelle
data:
  niveau: 812.5                       # kWh affichés par Urban Solar
  date_releve: "2026-11-05 23:59:00"  # heure locale du relevé ; vide = maintenant
```

Le stock repart du niveau indiqué à cette date, puis l'injection et la consommation enregistrées depuis sont rejouées. Les cumuls (charge, décharge, import réseau) ne sont pas modifiés.

## Tableau de bord Énergie

**Paramètres > Tableaux de bord > Énergie** :

1. **Réseau électrique > Consommation réseau** : ajoutez `sensor.import_reseau_hp` (prix fixe HP) et `sensor.import_reseau_hc` (prix fixe HC).
   N'ajoutez **pas** les compteurs Linky bruts : une partie de ce soutirage vient de la batterie.
2. **Retour au réseau** : rien. Toute l'injection part dans la batterie virtuelle.
3. **Production solaire** : votre capteur de production (Enphase, etc.).
4. **Stockage sur batterie** : *énergie entrant* = `sensor.charge_batterie_virtuelle`, *énergie sortant* = `sensor.decharge_batterie_virtuelle`.

### Voir votre indépendance énergétique

- La jauge **Autosuffisance** du tableau Énergie donne votre indépendance réelle : la part de votre consommation totale (autoconsommation solaire comprise) qui ne vient pas du réseau. Elle n'est juste qu'avec la configuration ci-dessus.
- `sensor.independance_reseau` donne la part de vos soutirages Linky couverte par la batterie virtuelle. Il s'affiche avec une carte *Jauge* ou *Historique*.

Le tableau Énergie ne sait pas mettre un prix sur la décharge d'une batterie. Les taxes de déstockage se suivent donc avec `sensor.cout_destockage`.

## Mise à jour depuis la 1.x

La configuration a changé. Supprimez l'intégration, puis ajoutez-la de nouveau. Les anciennes entités (`niveau_batterie_virtuelle`, `prix_kwh_actuel`, `economies_totales`) disparaissent.

## Tests

```
python tests/test_engine.py
```
