# Urban Solar Virtual Battery Pro

Suivez votre batterie virtuelle Urban Solar comme un pro sur Home Assistant.
Intégration personnalisée pour Home Assistant permettant de suivre le niveau et les économies d'une batterie virtuelle Urban Solar avec un matériel Enphase + ZLinky.

## Entités générées :
1. **Niveau Batterie Virtuelle (kWh)** : Votre solde en temps réel.
2. **Coût Taxes Déstockage (€)** : Ce que vous coûte l'utilisation de votre batterie (TURPE).
3. **Économies Réalisées (€)** : L'argent que vous n'avez pas donné à votre fournisseur d'énergie grâce au stockage.

## Installation
1. Copiez `custom_components/urban_solar_bv` dans votre dossier `config/custom_components`.
2. Redémarrer Home Assistant.
3. Allez dans **Paramètres > Appareils et Services > Ajouter une intégration**.
4. Cherchez **Urban Solar Virtual Battery**.

## Dashboard conseillé
Utilisez la carte `History Graph` pour le niveau (kWh) et `Gauge` pour les économies réalisées.

## Intégration au Dashboard Énergie
1. Dans la section **Consommation**, ajoutez vos capteurs ZLinky.
2. Pour le prix, choisissez **"Utiliser une entité de prix"** et sélectionnez `sensor.prix_kwh_actuel_dynamique`.
3. Dans **Stockage sur batterie**, ajoutez `sensor.niveau_batterie_virtuelle`.