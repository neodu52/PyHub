"""
CHIMIE — Équilibreur automatique d'équation bilan
====================================================================
Saisissez une équation avec des noms de composés ou des formules, SANS
vous soucier des coefficients (ex: "acetone + O2 = CO2 + H2O", ou même
juste "C3H6O + O2 = CO2 + H2O") et le programme calcule automatiquement
les plus petits coefficients entiers qui équilibrent l'équation.

Méthode : chaque composé est résolu en formule brute (cache local puis
PubChem en secours, comme Bilan_reaction_stoechiometrie), puis décomposé
en comptes d'éléments (data/formule_utils.py). Le système d'équations de
conservation des éléments est résolu exactement (noyau de la matrice, via
sympy), puis mis à l'échelle en plus petits entiers positifs.

Dépendances supplémentaires : requests, sympy (déjà dans requirements.txt)
"""

import re
import sys
from math import gcd
from functools import reduce
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox
)
from sympy import Matrix

DOSSIER_HUB = Path(__file__).resolve().parents[3]  # .../PyHub
sys.path.insert(0, str(DOSSIER_HUB / "data"))
import pubchem_utils as pc  # noqa: E402
from formule_utils import parser_formule  # noqa: E402
from pubchem_autocomplete_widget import ChampRechercheCompose  # noqa: E402

TITRE_PROGRAMME = "Équilibreur automatique d'équation bilan"
DESCRIPTION = (
    "Saisissez les réactifs et produits (noms ou formules), sans coefficients : "
    "le programme calcule automatiquement les plus petits entiers qui équilibrent l'équation."
)
EXEMPLE_EQUATION = "acetone + O2 = CO2 + H2O"


# ============================================================
# Découpage de l'équation en noms d'espèces (les coefficients éventuellement
# tapés par l'utilisateur sont ignorés : c'est justement ce qu'on calcule)
# ============================================================
def analyser_especes(texte):
    texte = texte.strip()
    if not texte:
        raise ValueError("L'équation est vide.")

    texte_normalise = re.sub(r"-+>|→|⟶", "=", texte)
    if "=" not in texte_normalise:
        raise ValueError(
            "L'équation doit contenir un séparateur '=' (ou '->') entre réactifs et produits.\n"
            f"Exemple : {EXEMPLE_EQUATION}"
        )
    partie_gauche, partie_droite = texte_normalise.split("=", 1)

    def extraire_noms(partie):
        termes = [t.strip() for t in partie.split("+") if t.strip()]
        noms = []
        for terme in termes:
            correspondance = re.match(r"^[0-9]+(?:[.,][0-9]+)?\s*(.+)$", terme)
            nom = correspondance.group(1).strip() if correspondance else terme
            if not nom:
                raise ValueError(f"Terme illisible dans l'équation : « {terme} »")
            noms.append(nom)
        return noms

    noms_reactifs = extraire_noms(partie_gauche)
    noms_produits = extraire_noms(partie_droite)
    if not noms_reactifs or not noms_produits:
        raise ValueError("Chaque côté de l'équation doit contenir au moins un composé.")
    return noms_reactifs, noms_produits


# ============================================================
# Équilibrage : résout le système de conservation des éléments (noyau de
# la matrice), puis met à l'échelle en plus petits entiers positifs.
# ============================================================
def equilibrer_equation(noms_reactifs, noms_produits, formules_par_nom):
    especes = noms_reactifs + noms_produits
    signes = [1] * len(noms_reactifs) + [-1] * len(noms_produits)
    elements = sorted({el for nom in especes for el in formules_par_nom[nom]})

    if not elements:
        raise ValueError("Aucun élément trouvé dans les composés fournis.")

    lignes = []
    for element in elements:
        ligne = [signes[i] * formules_par_nom[especes[i]].get(element, 0) for i in range(len(especes))]
        lignes.append(ligne)

    noyau = Matrix(lignes).nullspace()
    if not noyau:
        raise ValueError(
            "Impossible d'équilibrer cette équation : vérifiez que tous les éléments "
            "présents à gauche se retrouvent à droite (et inversement), et qu'aucun "
            "composé n'est manquant."
        )

    vecteur = noyau[0]
    ppcm = 1
    for terme in vecteur:
        ppcm = ppcm * terme.q // gcd(ppcm, terme.q)
    entiers = [int(terme * ppcm) for terme in vecteur]

    if all(c <= 0 for c in entiers):
        entiers = [-c for c in entiers]
    if any(c <= 0 for c in entiers):
        raise ValueError(
            "Cette équation ne peut pas être équilibrée avec des coefficients tous "
            "positifs : vérifiez que les réactifs et produits sont dans le bon sens "
            "et qu'aucune espèce n'est manquante."
        )

    pgcd_commun = reduce(gcd, entiers)
    entiers = [c // pgcd_commun for c in entiers]

    return dict(zip(especes, entiers))


def formater_equation(noms_reactifs, noms_produits, coefficients, utiliser_formules=False, formules_par_nom=None):
    def cote(noms):
        termes = []
        for nom in noms:
            affichage = formules_par_nom[nom]["formule"] if utiliser_formules else nom
            coefficient = coefficients[nom]
            termes.append(affichage if coefficient == 1 else f"{coefficient} {affichage}")
        return " + ".join(termes)
    return f"{cote(noms_reactifs)} = {cote(noms_produits)}"


class FenetreProgramme(QWidget):
    def __init__(self):
        super().__init__()
        self._construire_ui()

    def _construire_ui(self):
        self.setWindowTitle(TITRE_PROGRAMME)
        self.resize(700, 460)

        layout = QVBoxLayout(self)

        titre = QLabel(TITRE_PROGRAMME)
        titre.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(titre)

        desc = QLabel(DESCRIPTION)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)

        # --- barre de recherche PubChem ---
        ligne_recherche = QHBoxLayout()
        ligne_recherche.addWidget(QLabel("🔍 Rechercher un composé :"))
        self.champ_recherche = ChampRechercheCompose(
            placeholder="Tapez ex: ace... puis choisissez dans la liste"
        )
        self.champ_recherche.compose_choisi.connect(self._on_compose_choisi)
        ligne_recherche.addWidget(self.champ_recherche, stretch=1)
        layout.addLayout(ligne_recherche)

        # --- équation (sans coefficients) ---
        ligne_equation = QHBoxLayout()
        ligne_equation.addWidget(QLabel("Équation :"))
        self.champ_equation = QLineEdit(EXEMPLE_EQUATION)
        self.champ_equation.setPlaceholderText(EXEMPLE_EQUATION)
        ligne_equation.addWidget(self.champ_equation, stretch=1)
        layout.addLayout(ligne_equation)

        bouton = QPushButton("Équilibrer l'équation")
        bouton.clicked.connect(self._on_equilibrer)
        layout.addWidget(bouton)

        self.label_statut = QLabel("")
        self.label_statut.setWordWrap(True)
        self.label_statut.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.label_statut)

        layout.addWidget(QLabel("Équation équilibrée :"))
        self.label_resultat_formules = QLabel("")
        self.label_resultat_formules.setWordWrap(True)
        self.label_resultat_formules.setStyleSheet("font-size: 15px; font-weight: bold; font-family: monospace;")
        self.label_resultat_formules.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.label_resultat_formules.setCursor(QCursor(Qt.IBeamCursor))
        layout.addWidget(self.label_resultat_formules)

        self.label_resultat_noms = QLabel("")
        self.label_resultat_noms.setWordWrap(True)
        self.label_resultat_noms.setStyleSheet("font-size: 13px; color: #333;")
        self.label_resultat_noms.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.label_resultat_noms.setCursor(QCursor(Qt.IBeamCursor))
        layout.addWidget(self.label_resultat_noms)

        layout.addStretch(1)

    # ------------------------------------------------------------------
    def _on_compose_choisi(self, nom):
        texte_actuel = self.champ_equation.text().rstrip()
        if not texte_actuel:
            nouveau_texte = nom
        elif texte_actuel.endswith(("+", "=")):
            nouveau_texte = f"{texte_actuel} {nom}"
        else:
            nouveau_texte = f"{texte_actuel} + {nom}"
        self.champ_equation.setText(nouveau_texte)
        self.champ_recherche.clear()
        self.champ_recherche.setFocus()

    def _on_equilibrer(self):
        try:
            noms_reactifs, noms_produits = analyser_especes(self.champ_equation.text())
        except ValueError as e:
            QMessageBox.warning(self, "Équation invalide", str(e))
            return

        self.setCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()

        formules_par_nom = {}
        elements_par_nom = {}
        erreurs = []
        nb_locale = nb_pubchem = 0
        for nom in noms_reactifs + noms_produits:
            if nom in formules_par_nom:
                continue
            try:
                proprietes = pc.obtenir_proprietes(nom)
            except pc.ComposeIntrouvable as e:
                erreurs.append(str(e))
                continue
            formules_par_nom[nom] = proprietes
            try:
                elements_par_nom[nom] = parser_formule(proprietes["formule"])
            except ValueError as e:
                erreurs.append(f"Formule illisible pour « {nom} » ({proprietes['formule']}) : {e}")
                continue
            if proprietes["source"] == "locale":
                nb_locale += 1
            else:
                nb_pubchem += 1

        self.setCursor(QCursor(Qt.ArrowCursor))

        if erreurs:
            QMessageBox.critical(self, "Composé(s) introuvable(s)", "\n\n".join(erreurs))
            return

        try:
            coefficients = equilibrer_equation(noms_reactifs, noms_produits, elements_par_nom)
        except ValueError as e:
            QMessageBox.warning(self, "Équilibrage impossible", str(e))
            return

        equation_formules = formater_equation(
            noms_reactifs, noms_produits, coefficients,
            utiliser_formules=True, formules_par_nom=formules_par_nom
        )
        equation_noms = formater_equation(noms_reactifs, noms_produits, coefficients)

        self.label_resultat_formules.setText(equation_formules)
        self.label_resultat_noms.setText(f"(soit : {equation_noms})")
        self.label_statut.setText(
            f"{len(formules_par_nom)} composé(s) résolu(s) — {nb_locale} depuis le cache local, "
            f"{nb_pubchem} via PubChem (désormais mis en cache)."
        )


def main():
    app = QApplication(sys.argv)
    fenetre = FenetreProgramme()
    fenetre.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
