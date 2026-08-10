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


def parser_formule_avec_charge(texte):
    """Comme parser_formule, mais reconnaît aussi une notation de charge
    ionique à la fin : 'MnO4-' -> ({'Mn':1,'O':4}, -1), 'Fe3+' -> ({'Fe':1}, 3),
    'Cr2O7^2-' -> ({'Cr':2,'O':7}, -2), 'H2O' -> ({'H':2,'O':1}, 0).

    Notation acceptée : '+', '-', '2+', '2-'... directement à la fin, ou
    précédée d'un accent circonflexe '^' (recommandé pour lever toute
    ambiguïté sur les ions polyatomiques de charge > 1, ex: 'SO4^2-').

    Cas particulier des ions monoatomiques (un seul élément, ex: 'Fe3+',
    'Cu2+', 'Cl-') : le chiffre juste avant le signe est alors interprété
    comme la charge (et non comme un indice), puisqu'un seul atome est en jeu.
    """
    texte_original = texte.strip().replace(" ", "")
    if not texte_original:
        raise ValueError("Formule vide.")

    m_mono = re.fullmatch(r"([A-Z][a-z]?)(\d*)([+\-]+)", texte_original)
    if m_mono:
        symbole, chiffre, signes = m_mono.groups()
        signe = 1 if signes[0] == "+" else -1
        charge = signe * (int(chiffre) if chiffre else len(signes))
        return {symbole: 1}, charge

    pile = [{}]
    i, n = 0, len(texte_original)
    while i < n:
        c = texte_original[i]
        if c in "([":
            pile.append({})
            i += 1
        elif c in ")]":
            i += 1
            correspondance = re.match(r"\d+", texte_original[i:])
            multiplicateur = int(correspondance.group()) if correspondance else 1
            i += len(correspondance.group()) if correspondance else 0
            if len(pile) < 2:
                raise ValueError("Parenthèse fermante sans parenthèse ouvrante correspondante.")
            groupe = pile.pop()
            sommet = pile[-1]
            for symbole, compte in groupe.items():
                sommet[symbole] = sommet.get(symbole, 0) + compte * multiplicateur
        elif c in "+-^":
            if len(pile) != 1:
                raise ValueError("Parenthèse ouverte non fermée avant la notation de charge.")
            break
        else:
            correspondance = re.match(r"[A-Z][a-z]?", texte_original[i:])
            if not correspondance:
                raise ValueError(f"Caractère inattendu dans la formule : « {texte_original[i:]} »")
            symbole = correspondance.group()
            i += len(symbole)
            correspondance_nb = re.match(r"\d+", texte_original[i:])
            compte = int(correspondance_nb.group()) if correspondance_nb else 1
            i += len(correspondance_nb.group()) if correspondance_nb else 0
            sommet = pile[-1]
            sommet[symbole] = sommet.get(symbole, 0) + compte

    if len(pile) != 1:
        raise ValueError("Parenthèse ouvrante non fermée dans la formule.")

    reste = texte_original[i:]
    charge = 0
    if reste:
        m_charge = re.fullmatch(r"\^?\(?\{?(\d+)?([+\-]+)\}?\)?", reste)
        if not m_charge:
            raise ValueError(
                f"Notation de charge invalide : « {reste} ». Pour une charge de "
                "magnitude > 1 sur un ion polyatomique, utilisez un accent "
                "circonflexe, ex: SO4^2-"
            )
        chiffre, signes = m_charge.groups()
        signe = 1 if signes[0] == "+" else -1
        charge = signe * (int(chiffre) if chiffre else len(signes))

    return pile[0], charge
