"""
data/formule_utils.py — Module PARTAGÉ (pas d'UI, pas de PyQt)
====================================================================
Analyse d'une formule chimique brute ("Ca(OH)2", "Al2(SO4)3"...) en un
dict {symbole_élément: compte}, avec gestion des parenthèses/crochets
imbriqués.

Utilisé par plusieurs programmes de la catégorie Chimie :
- Calculateur_masse_molaire (masse molaire à partir d'une formule)
- Equilibreur_equation (équilibrage automatique d'une équation bilan)

Import depuis un programme du hub :
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "data"))
    import formule_utils
"""

import re


def parser_formule(formule):
    """'Ca(OH)2' -> {'Ca': 1, 'O': 2, 'H': 2}"""
    formule = formule.strip().replace(" ", "")
    if not formule:
        raise ValueError("Formule vide.")

    pile = [{}]
    i = 0
    n = len(formule)
    while i < n:
        c = formule[i]
        if c in "([":
            pile.append({})
            i += 1
        elif c in ")]":
            i += 1
            correspondance = re.match(r"\d+", formule[i:])
            multiplicateur = int(correspondance.group()) if correspondance else 1
            i += len(correspondance.group()) if correspondance else 0
            if len(pile) < 2:
                raise ValueError("Parenthèse fermante sans parenthèse ouvrante correspondante.")
            groupe = pile.pop()
            sommet = pile[-1]
            for symbole, compte in groupe.items():
                sommet[symbole] = sommet.get(symbole, 0) + compte * multiplicateur
        else:
            correspondance = re.match(r"[A-Z][a-z]?", formule[i:])
            if not correspondance:
                raise ValueError(f"Caractère inattendu dans la formule : « {formule[i:]} »")
            symbole = correspondance.group()
            i += len(symbole)
            correspondance_nb = re.match(r"\d+", formule[i:])
            compte = int(correspondance_nb.group()) if correspondance_nb else 1
            i += len(correspondance_nb.group()) if correspondance_nb else 0
            sommet = pile[-1]
            sommet[symbole] = sommet.get(symbole, 0) + compte

    if len(pile) != 1:
        raise ValueError("Parenthèse ouvrante non fermée dans la formule.")
    return pile[0]
