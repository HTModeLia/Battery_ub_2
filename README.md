# Urban Solar Virtual Battery Pro

Suivez votre batterie virtuelle Urban Solar comme un pro sur Home Assistant.

## Entités générées :
1. **Niveau Batterie Virtuelle (kWh)** : Votre solde en temps réel.
2. **Coût Taxes Déstockage (€)** : Ce que vous coûte l'utilisation de votre batterie (TURPE).
3. **Économies Réalisées (€)** : L'argent que vous n'avez pas donné à votre fournisseur d'énergie grâce au stockage.

## Installation
1. Copier le dossier `urban_solar_bv` dans `custom_components`.
2. Redémarrer Home Assistant.
3. Ajouter l'intégration via l'UI.
4. Renseigner vos tarifs HP/HC et les taxes de déstockage (environ 0.05€/kWh).

## Dashboard conseillé
Utilisez la carte `History Graph` pour le niveau (kWh) et `Gauge` pour les économies réalisées.