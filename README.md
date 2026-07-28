# PyHub — Hub personnel de programmes Python scientifiques

Un hub avec une interface PyQt qui centralise tous vos petits programmes
de calcul (physique, chimie, ingénierie, aérospatiale, ou n'importe quelle
autre catégorie). Chaque programme reste un dossier indépendant avec son
propre `main.py` ; le hub se contente de les afficher et de les lancer.

**Principe clé : la modularité vient de la structure des dossiers, pas du
code.** Pour ajouter un programme, vous ajoutez un dossier. Rien à modifier
dans le hub lui-même.

## Installation

```bash
pip install -r requirements.txt
```

`PyQt5` est indispensable. `numpy` et `matplotlib` ne sont utilisés que par
deux programmes d'exemple (Physique et Ingénierie) ; vous pouvez les
ignorer si vous supprimez ces exemples.

## Lancer le hub

```bash
python main.py
```

Une fenêtre s'ouvre avec un onglet par catégorie (dossier dans
`categories/`) et, dans chaque onglet, un bouton par programme trouvé.
Cliquer sur un bouton lance ce programme dans son propre processus Python
(sa propre fenêtre, indépendante du hub).

- `F5` ou le bouton **🔄 Actualiser** : rescanne `categories/` sans
  redémarrer (utile juste après avoir ajouté un dossier).
- **📂 Ouvrir le dossier categories/** : ouvre l'explorateur de fichiers
  sur ce dossier, si vous préférez naviguer manuellement.

## Exécutables natifs (C++, .exe, scripts...)

Un dossier de programme n'est plus obligé de contenir un `main.py` : il
peut contenir directement un exécutable natif (un `.exe` Windows, un
binaire C++ compilé, un script `.sh`...). Le hub le détecte et le lance
directement (sans passer par l'interpréteur Python), soit automatiquement
d'après l'extension (`.exe`, `.bat`, `.cmd`, `.sh`, `.bin`, `.app`, `.out`),
soit explicitement via `hub_info.json` :

```json
{
  "nom_affiche": "Simulation de trajectoire (C++)",
  "fichier": "simulation.exe",
  "type": "executable",
  "arguments": ["--vitesse", "300", "--angle", "45"]
}
```

- `"type"` : `"executable"` force un lancement direct ; `"python"` force
  un lancement via l'interpréteur Python ; si absent, le hub déduit le
  type à partir de l'extension du fichier.
- `"arguments"` (optionnel) : liste de chaînes passées en ligne de
  commande à l'exécutable.
- Sur Linux/Mac, si le fichier n'a pas le bit exécutable, le hub affiche
  un message clair vous invitant à faire `chmod +x` dessus.

Pour vos simulations C++ : compilez-les normalement sur votre machine
(ex: avec `g++` ou Visual Studio), placez l'exécutable résultant dans
un dossier sous `categories/<Categorie>/`, ajoutez le `hub_info.json`
ci-dessus (en adaptant `"fichier"` au nom réel de votre binaire), et le
bouton apparaîtra comme n'importe quel autre programme.

## Structure du projet

```
PyHub/
├── main.py                     # point d'entrée : lance la fenêtre du hub
├── hub_window.py                # logique du hub (scan, onglets, boutons, exécution)
├── requirements.txt
├── templates/
│   └── template_programme.py    # à copier pour créer un nouveau programme
├── data/                         # dossier PARTAGÉ, ignoré par le hub (voir plus bas)
│   ├── pubchem_utils.py           # module utilitaire : masse molaire d'un composé (PubChem)
│   ├── composes_locale.json       # cache local des composés déjà résolus par PubChem
│   └── tableau_periodique.json    # les 118 éléments, complet, 100% hors-ligne
└── categories/
    ├── Physique/
    │   ├── Chute_libre_avec_frottement/
    │   │   ├── main.py
    │   │   └── hub_info.json
    │   └── Resolveur_equations/
    │       ├── main.py
    │       └── hub_info.json
    ├── Chimie/
    │   ├── Dilution_C1V1_C2V2/
    │   │   ├── main.py
    │   │   └── hub_info.json
    │   ├── Quantite_reactif/
    │   │   ├── main.py
    │   │   └── hub_info.json
    │   ├── Calculateur_masse_molaire/
    │   │   ├── main.py
    │   │   └── hub_info.json
    │   └── Bilan_reaction_stoechiometrie/
    │       ├── main.py
    │       └── hub_info.json
    ├── Ingenierie/
    │   └── Poutre_flexion_simple/
    │       ├── main.py
    │       └── hub_info.json
    └── Aerospatiale/
        └── Equation_fusee_Tsiolkovsky/
            ├── main.py
            └── hub_info.json
```

## Le dossier `data/` — ressources partagées entre programmes

`data/` est volontairement **à la racine du hub, en dehors de `categories/`** :
le hub ne scanne que `categories/`, donc rien dans `data/` n'apparaît jamais
comme catégorie ou comme bouton. Ce dossier n'est utilisé que par vos
`main.py`, qui vont y piocher des données ou des fonctions communes.

Il contient aujourd'hui :

- **`composes_locale.json`** — un cache de propriétés de composés chimiques
  (masse molaire, formule, nom PubChem, CID). Il est pré-rempli avec
  `acetone`, `O2`, `CO2`, `H2O` (et quelques synonymes) pour que l'exemple
  ci-dessous fonctionne sans connexion.
- **`pubchem_utils.py`** — un module Python *sans PyQt* qui expose une seule
  fonction utile : `obtenir_proprietes(nom_ou_formule)`. Elle cherche
  d'abord dans `composes_locale.json` ; si le composé est absent, elle
  interroge automatiquement l'API PubChem (gratuite, sans clé), puis
  **enregistre le résultat dans le cache** pour ne plus jamais avoir à
  refaire la requête réseau pour ce composé.

Pour utiliser ce module depuis un nouveau programme (où qu'il soit dans
`categories/`), le pattern est toujours le même :

```python
import sys
from pathlib import Path
# remonte de main.py jusqu'à la racine PyHub/, puis descend dans data/
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "data"))
import pubchem_utils as pc

infos = pc.obtenir_proprietes("acetone")
print(infos["masse_molaire"])   # 58.08
print(infos["source"])          # "locale" ou "pubchem_nom" ou "pubchem_formule"
```

Ce même pattern (dossier `data/` + `sys.path.insert`) fonctionne pour
n'importe quel autre fichier JSON ou module Python que vous voudriez
partager entre plusieurs programmes (un futur `tableau_periodique.json`,
une table de constantes physiques, etc.) : il suffit de l'ajouter dans
`data/` et de l'importer/charger de la même façon depuis n'importe quel
`main.py`.

### Exemple : Bilan de réaction (stœchiométrie + PubChem)

`categories/Chimie/Bilan_reaction_stoechiometrie/` illustre ce pattern.
On y saisit une équation bilan avec des noms ou formules, par exemple :

```
1 acetone + 4 O2 = 3 CO2 + 3 H2O
```

On choisit ensuite une espèce dont on connaît la quantité (en mol ou en g),
et le programme calcule automatiquement la quantité (mol + g) de toutes
les autres espèces, à partir des coefficients réels de l'équation — y
compris quand le coefficient du produit choisi n'est pas 1.

Pour chaque composé de l'équation, le programme :
1. regarde d'abord dans `data/composes_locale.json` ;
2. si absent, interroge PubChem par nom, puis par formule brute en secours ;
3. enregistre le résultat dans le cache local.

Astuce : les noms anglais (`acetone`, `water`, `oxygen`) et les formules
brutes (`CO2`, `NaCl`, `H2O`) sont les mieux reconnus par PubChem. Les noms
français ne fonctionnent que s'ils font partie des synonymes connus de
PubChem pour ce composé — sinon, préférez la formule ou le nom anglais.

Dépendance supplémentaire pour ce programme : `requests`
(déjà dans `requirements.txt`).

### `Quantite_reactif` — votre propre calculateur

`categories/Chimie/Quantite_reactif/` est le programme que vous avez
écrit à partir du template : à partir d'une masse de produit visée, il
calcule la masse et le volume de deux réactifs. Une seule précision a été
ajoutée en commentaire dans `calculer()` : le calcul suppose que le
**produit** a un coefficient de 1 dans l'équation bilan (les coefficients
des réactifs que vous saisissez doivent alors être exprimés "par mol de
produit"). Si ce n'est pas le cas dans votre réaction, `Bilan_reaction_stoechiometrie`
(ci-dessus) gère lui n'importe quels coefficients directement depuis
l'équation complète.

## Le tableau périodique local (`data/tableau_periodique.json`)

Contrairement aux composés chimiques (trop nombreux pour être stockés à
l'avance), le tableau périodique est complet et minuscule : 118 éléments
qui ne changent jamais. Il est donc fourni **entièrement en local**, sans
connexion Internet ni cache à remplir — pas besoin du pattern PubChem ici.

Pour chaque élément (clé = symbole, ex `"Fe"`) :

```json
{
  "numero_atomique": 26,
  "symbole": "Fe",
  "nom": "Fer",
  "masse_molaire": 55.845,
  "masse_volumique_g_cm3": 7.874,
  "nombre_protons": 26,
  "nombre_electrons": 26,
  "configuration_electronique": {"K": 2, "L": 8, "M": 14, "N": 2},
  "configuration_electronique_detaillee": "[Ar] 3d6 4s2",
  "categorie": "métal de transition",
  "etat_standard": "solide",
  "point_fusion_C": 1537.85,
  "point_ebullition_C": 2860.85
}
```

Données factuelles publiques (IUPAC / PeriodicTableOfElements.org).

### Exemple : `Calculateur_masse_molaire`

`categories/Chimie/Calculateur_masse_molaire/` illustre l'usage de ce
fichier : tapez une formule (`H2O`, `Ca(OH)2`, `Fe2O3`, `C6H12O6`,
`Al2(SO4)3`, `K4[Fe(CN)6]`...), et le programme décompose la formule
(parenthèses/crochets imbriqués gérés), regarde la masse molaire de
chaque élément dans `data/tableau_periodique.json`, et affiche le détail
du calcul par élément ainsi que le total. Aucune requête réseau — même
principe de partage de données que PubChem, mais 100% hors-ligne car le
jeu de données est petit et complet.

## Résolveur d'équations symbolique (`categories/Physique/Resolveur_equations`)

Tapez une équation en écriture "clavier" (`E=(1/2)*m*v^2`) ou en LaTeX
(`E=\frac{1}{2}mv^{2}`, avec ou sans les antislashs — les deux marchent),
et :

1. **Convertissez** d'une forme à l'autre avec les boutons "Clavier → LaTeX"
   / "LaTeX → Clavier". Un aperçu typographié (rendu via matplotlib)
   s'affiche automatiquement.
2. **Isolez** n'importe quelle variable de l'équation (pas seulement celle
   du membre de gauche) : choisissez-la dans le menu déroulant et cliquez
   sur "Isoler cette variable". S'il y a plusieurs solutions (ex : une
   racine carrée donnant ± une valeur), toutes sont affichées.
3. **Calculez** : des champs numériques apparaissent automatiquement pour
   toutes les autres variables de l'équation ; entrez leurs valeurs et
   cliquez sur "Calculer" pour obtenir la variable isolée.

Prend en charge `\frac{}{}`, `\sqrt{}` (et `\sqrt[n]{}`), les exposants
`^{}`, les indices `_{}` (ex: `v_0`), `\cdot`/`\times`, et les lettres
grecques courantes. Utilise sympy pour le calcul symbolique — y compris
un correctif pour les lettres piégeuses comme `E` (confondue par défaut
avec le nombre d'Euler) ou `I` (confondue avec l'unité imaginaire), très
courantes en physique (énergie, intensité) mais toujours traitées ici
comme de simples variables.

Dépendance supplémentaire : `sympy` (déjà dans `requirements.txt`).

## Simulation de gravité (c++)

Ceci est une simulationd de la gravité utilisant les lois de la gravité de Newton.
Elle vous permet de crée des corps celestes représenté par des disques et de voire comment la gravité influ sur eux.
En cliquant d'abord sur espace pour mettre la simulation en pose puis clique droit sur corp vous pourrez modifier
ses parametres (taille, masse, couleur, véloicité, position)
Vous pourrer aussi crée vos propres corps avec clique molette.
Ce programme est directement tiré d'un autre de mes project intituler "2D-newtonian-gravity-sim"
que vous pourrez retrouver [ici](https://github.com/neodu52/2D-newtonian-gravity-sim)

## Ajouter un nouveau programme

1. Choisissez (ou créez) une catégorie : un dossier dans `categories/`,
   par exemple `categories/Mathematiques/`. **Aucune catégorie n'est
   codée en dur** : un nouveau dossier ici devient un nouvel onglet
   automatiquement.
2. Créez un sous-dossier pour votre programme, par exemple
   `categories/Mathematiques/Racines_polynome/`.
3. Copiez `templates/template_programme.py` dedans, en le renommant
   `main.py`.
4. Adaptez les 3 zones marquées `MODIFIEZ ICI` dans le fichier :
   - `CHAMPS` : la liste des champs de saisie (nom interne, label,
     valeur par défaut, min, max, unité)
   - `TITRE_PROGRAMME` / `DESCRIPTION`
   - la fonction `calculer(valeurs)` : votre logique, qui reçoit un
     dict `{nom_interne: valeur}` et renvoie une chaîne de résultat
5. (Optionnel) Ajoutez un fichier `hub_info.json` à côté de `main.py` :

```json
{
  "nom_affiche": "Racines d'un polynôme",
  "description": "Affiché en info-bulle au survol du bouton.",
  "fichier": "main.py"
}
```

Sans ce fichier, le bouton affiche simplement le nom du dossier.

6. Appuyez sur `F5` dans le hub : le nouveau bouton apparaît.

Vous pouvez aussi tester un programme seul, sans passer par le hub :

```bash
python categories/Mathematiques/Racines_polynome/main.py
```

## Ajouter un programme qui n'est pas basé sur le template

Le template n'est qu'un point de départ pratique. Le hub n'exige rien
d'autre qu'un dossier contenant un `main.py` exécutable (avec un
`if __name__ == "__main__":` qui lance sa propre fenêtre). Vous pouvez
donc écrire une UI PyQt entièrement différente, avec des graphiques
(comme l'exemple Ingénierie qui intègre matplotlib), plusieurs onglets
internes, des fichiers de données à côté du script, etc. — tant que le
dossier a un `main.py` lançable, le hub saura l'exécuter.

## Notes techniques

- Chaque programme est lancé via `subprocess.Popen([sys.executable, ...])`,
  c'est-à-dire un **nouveau processus Python indépendant**. C'est
  volontaire : PyQt n'autorise qu'une seule `QApplication` par processus,
  donc lancer les programmes dans des processus séparés évite tout conflit
  avec la fenêtre du hub, et une erreur dans un programme ne fait jamais
  planter le hub.
- Le dossier `categories/` est repéré par rapport à l'emplacement de
  `hub_window.py` (pas par rapport au dossier depuis lequel vous lancez
  la commande), donc vous pouvez lancer `python main.py` depuis n'importe
  où.
