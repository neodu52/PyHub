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

## Structure du projet

```
PyHub/
├── main.py                     # point d'entrée : lance la fenêtre du hub
├── hub_window.py                # logique du hub (scan, onglets, boutons, exécution)
├── requirements.txt
├── templates/
│   └── template_programme.py    # à copier pour créer un nouveau programme
└── categories/
    ├── Physique/
    │   └── Chute_libre_avec_frottement/
    │       ├── main.py
    │       └── hub_info.json
    ├── Chimie/
    │   └── Dilution_C1V1_C2V2/
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
