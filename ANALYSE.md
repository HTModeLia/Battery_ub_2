# Analyse du dépôt `Battery_ub_2` (Urban Solar Virtual Battery)

*Analyse du 06/11/2026 — version 1.2.0 (commit `11aa973`). Les sections 2 à 5 décrivent cette version.*

## 0. Statut après la version 2.0.0 (07/11/2026)

| Point de l'analyse | Statut en 2.0.0 |
|---|---|
| 3.1 Priorité batterie → réseau | **Corrigé** : calcul avec état (`engine.py`), stock jamais négatif, capacité infinie. |
| 3.2 Branchement au tableau Énergie | **Corrigé** : capteurs charge, décharge, import réseau net HP/HC ; procédure dans le README. |
| 3.3 Coûts et économies | **Corrigé** : calculés sur la seule énergie sortie de la batterie. Le capteur de prix dynamique est supprimé. |
| Calibrage | **Ajouté** : niveau relevé chez Urban Solar à une date/heure, à l'installation et via l'action `urban_solar_bv.calibrer`. L'historique depuis le relevé est rejoué. |
| Indépendance énergétique | **Ajouté** : jauge *Autosuffisance* du tableau Énergie et capteur `sensor.independance_reseau`. |
| 3.4 Défauts techniques | **Corrigés** : config flow, classes et unités, gestion de `unavailable`, Wh/kWh, `async_unload_platforms`, manifeste, traductions (`translations/`), README. |
| Options flow (modifier les tarifs) | **Corrigé en 2.1.0** : bouton *Configurer* de l'intégration. |
| Tarifs historisés | **Corrigé en 2.1.0** : coût et économies sont cumulés au tarif en vigueur à chaque décharge. |
| Redémarrage avec un index jamais lu | **Corrigé en 2.1.0** : l'intégration refusait de démarrer ; l'index prend désormais sa première valeur comme référence. |
| Règles Urban Solar (plafond, expiration du stock) | **Non vérifiées** : la batterie est supposée illimitée et sans expiration. |

**Calibrage :** la date du relevé doit rester dans la durée de conservation du recorder (10 jours par défaut).

## 1. Objectif visé

Gérer une **batterie virtuelle** (offre Urban Solar) dans Home Assistant et la **brancher sur le tableau de bord Énergie** :

- la batterie n'est pas physique : elle se **remplit avec le surplus injecté** sur le réseau Enedis/EDF ;
- la consommation est **servie d'abord par la batterie**, puis **par le réseau** quand la batterie est vide.

## 2. Contenu du dépôt

| Fichier | Rôle |
|---|---|
| `hacs.json` | Déclare le dépôt comme intégration HACS. |
| `README.md` | Installation et intégration au tableau Énergie. |
| `custom_components/urban_solar_bv/manifest.json` | Métadonnées HA (`config_flow: true`, `local_polling`, v1.2.0). |
| `__init__.py` | Transmet l'entrée de configuration à la plateforme `sensor`. |
| `const.py` | Clés de configuration : 3 entités Linky, 4 valeurs de calibrage, 4 tarifs. |
| `config_flow.py` | Formulaire de configuration dans l'interface (étape `user`). |
| `strings.json` | Libellés du formulaire. |
| `sensor.py` | Les 3 capteurs, décrits ci-dessous. |

### Entrées (saisies dans le formulaire)
- Compteurs Linky (ZLinky) : **injection** (EAIT), **soutirage HP** (HCHP), **soutirage HC** (HCHC), en **Wh**.
- Index de départ des 3 compteurs + **solde de batterie au départ** (kWh).
- Prix réseau HP/HC et **taxe de déstockage** HP/HC (€/kWh).

### Capteurs produits (`sensor.py`)
| Capteur | Calcul | Classe HA |
|---|---|---|
| Niveau Batterie Virtuelle (kWh) | `solde_départ + (Δinjection − ΔHP − ΔHC) / 1000` | `energy` / `total` |
| Prix kWh Actuel (€/kWh) | `taxe_HP` si niveau > 0, sinon `prix_HP` | `monetary` |
| Économies Totales (€) | `ΔHP × (prix_HP − taxe_HP) + ΔHC × (prix_HC − taxe_HC)`, borné à ≥ 0 | `monetary` / `total_increasing` |

Les calculs sont **sans état** : chaque valeur est recalculée à partir des index actuels moins les index de départ, à chaque interrogation (toutes les 30 s).

## 3. Écart avec l'objectif

**Verdict : partiellement en phase.** Le principe (« ce que j'injecte remplit, ce que je soutire vide ») est juste. En revanche, la **priorité batterie puis réseau n'est pas implémentée**, et l'intégration ne fournit **pas les capteurs attendus par le tableau Énergie**.

### 3.1 La priorité batterie → réseau n'existe pas (bloquant)
Le niveau est un simple bilan `injecté − soutiré`. Il **devient négatif** quand la consommation dépasse le stock, au lieu de rester à 0 avec bascule sur le réseau.

Exemple : stock 0 kWh, on consomme 10 kWh, puis on injecte 5 kWh.
- **Attendu** : 10 kWh pris au réseau, puis batterie à **5 kWh**.
- **Calculé** : niveau à −10, puis à **−5 kWh**. L'injection rembourse une « dette » qui n'existe pas.

Un calcul sans état ne peut pas faire mieux : savoir quelle part d'un kWh soutiré était couverte par le stock **au moment où il a été consommé** suppose de **suivre les variations dans le temps** et de mémoriser le stock.

### 3.2 Pas de branchement correct au tableau Énergie (bloquant)
Le tableau Énergie de HA, section *Stockage sur batterie*, attend **deux compteurs cumulatifs** : « énergie entrant dans la batterie » et « énergie sortant de la batterie » (kWh, `total_increasing`). Il **n'accepte pas un niveau de charge**. Le README demande d'y mettre `sensor.niveau_batterie_virtuelle`, ce qui est faux.

De plus, si les compteurs Linky bruts sont déclarés en *Consommation réseau* et *Retour au réseau*, le tableau compte deux fois :
- l'injection apparaît comme vendue au réseau, alors qu'elle part dans la batterie ;
- tout le soutirage apparaît comme acheté au réseau, alors qu'une partie sort de la batterie.

**Capteurs manquants** : charge cumulée, décharge cumulée, et **import réseau net** HP/HC (la part du soutirage non couverte par la batterie).

### 3.3 Coûts et économies approximatifs
- **Prix** : le capteur ne connaît que HP, il ignore la période HC. C'est aussi un contournement : appliquer un prix « taxe » à tout le soutirage Linky n'est juste que si le stock ne s'épuise jamais en cours d'intervalle.
- **Économies** : le calcul suppose que **toute** la consommation sort de la batterie, même quand elle est vide. Il **surestime** donc les gains.

### 3.4 Défauts techniques
| Problème | Où | Effet |
|---|---|---|
| `config_flow.py` avait été écrasé par une copie de `sensor.py` (commit `11aa973`) | `config_flow.py` | Intégration impossible à ajouter depuis l'interface. **Corrigé** (non committé). |
| Aucun formulaire de modification (options flow) | `config_flow.py` | Changer les tarifs impose de supprimer puis recréer l'intégration. |
| `float(state)` hors de tout `try` | `UrbanSolarSavings` | Exception à chaque interrogation quand le Linky est `unavailable`. |
| `except:` nu | `UrbanSolarBatteryLevel` | Masque toutes les erreurs. |
| Entité `sensor.niveau_batterie_virtuelle` codée en dur | `UrbanSolarCurrentPrice` | Si l'entité est renommée ou si plusieurs instances existent, le prix retombe silencieusement sur le prix plein. |
| `monetary` avec l'unité `€/kWh` ; `monetary` + `total_increasing` ; unité `€` au lieu de `EUR` | `sensor.py` | Combinaisons refusées par HA (avertissements). Un prix doit être sans `device_class`, en `EUR/kWh`. |
| Niveau en `energy` / `total` | `UrbanSolarBatteryLevel` | Pour un stock, la bonne classe est `energy_storage` / `measurement`. |
| Index supposés en Wh (division par 1000) | `sensor.py` | Faux si le ZLinky publie en kWh. L'unité devrait être lue depuis l'entité. |
| `async_forward_entry_unload` | `__init__.py` | Fonction dépréciée ; à remplacer par `async_unload_platforms`. |
| `issue_tracker` et `requirements` absents | `manifest.json` | Signalés par la validation HACS et hassfest. |
| `configuration_url` vaut `github.com/votre_pseudo/...` | `sensor.py` | URL d'exemple jamais remplacée. |
| Le README cite « Coût Taxes Déstockage » et `sensor.prix_kwh_actuel_dynamique` | `README.md` | Entités inexistantes : l'entité actuelle est `sensor.prix_kwh_actuel`. |

## 4. Conception cible proposée

### Moteur (avec état, persistant au redémarrage via `RestoreEntity`)
On écoute les changements d'état des 3 compteurs Linky. À chaque variation :

```
Δinj > 0  :  stock += Δinj ; charge_totale += Δinj
Δsout > 0 (HP ou HC) :
    couvert   = min(Δsout, stock)
    stock    -= couvert
    decharge_totale       += couvert
    import_reseau_HP/HC   += Δsout − couvert
```

Les variations négatives (remise à zéro ou remplacement du compteur) et les états `unknown`/`unavailable` sont ignorés.

### Capteurs à exposer
| Capteur | Classe | Usage dans le tableau Énergie |
|---|---|---|
| Stock batterie virtuelle | `energy_storage` / `measurement`, kWh | Affichage (jauge, historique) |
| Charge cumulée | `energy` / `total_increasing`, kWh | Batterie → *énergie entrant* |
| Décharge cumulée | `energy` / `total_increasing`, kWh | Batterie → *énergie sortant* |
| Import réseau net HP | `energy` / `total_increasing`, kWh | Consommation réseau, prix fixe HP |
| Import réseau net HC | `energy` / `total_increasing`, kWh | Consommation réseau, prix fixe HC |
| Coût de déstockage (optionnel) | `monetary` / `total`, EUR | Suivi des taxes payées sur la décharge |

Dans le tableau Énergie : **ne pas** déclarer l'injection Linky en *Retour au réseau*, puisqu'elle est déjà comptée en charge de la batterie. La production solaire (Enphase) se déclare normalement.

**Limite de HA à arbitrer** : le tableau Énergie n'associe **aucun coût** à la décharge d'une batterie. Deux options :
1. garder la décharge en *Batterie* (flux justes, taxes de déstockage suivies par un capteur à part) ;
2. déclarer la décharge comme une 2ᵉ source de *Consommation réseau* au prix « taxe » (coût total juste, mais la batterie n'apparaît plus comme telle).

### Points à confirmer côté offre Urban Solar
- capacité maximale ou plafond éventuel de la batterie virtuelle, avec ce que devient l'injection au-delà ;
- taxe de déstockage différente en HP et en HC, et dates de révision des tarifs (pour l'options flow).

## 5. Priorités
1. Moteur avec état et capteurs charge / décharge / import net : c'est le cœur de l'objectif.
2. Corriger les classes et unités des capteurs, puis mettre à jour le README (procédure du tableau Énergie).
3. Ajouter un options flow pour les tarifs, compléter le manifeste, remplacer `async_forward_entry_unload`.
4. Ajouter un test du moteur : séquence injection / soutirage, vérification du stock borné à 0 et du partage batterie / réseau.
