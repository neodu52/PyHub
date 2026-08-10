"""
CHIMIE — Demi-équations rédox (équilibrage automatique)
====================================================================
Donnez la forme oxydée (Ox) et la forme réduite (Red) d'un couple
rédox — avec la charge ionique explicite, ex: "MnO4-", "Fe3+",
"Cr2O7^2-" — et le programme équilibre automatiquement la demi-équation
électronique, en milieu acide (H+) ET en milieu basique (OH-).

Méthode (celle enseignée au lycée/prépa) :
1. équilibrer l'élément "squelette" (autre que O, H) entre Ox et Red ;
   à défaut (aucun autre élément, ex: O2/H2O), utiliser O, puis H ;
2. équilibrer l'oxygène en ajoutant des H2O ;
3. équilibrer l'hydrogène en ajoutant des H+ ;
4. équilibrer la charge en ajoutant des électrons e- ;
5. (bonus) conversion en milieu basique : ajout de autant de OH- que de
   H+ des deux côtés, combinaison H+ + OH- -> H2O, simplification.

Notation de charge acceptée : 'Fe3+', 'Cl-', 'MnO4-', 'MnO4^-',
'Cr2O7^2-'... Pour un ion polyatomique de charge de magnitude > 1,
utilisez de préférence l'accent circonflexe ('SO4^2-') pour lever toute
ambiguïté avec un indice de formule.
"""

import re
import sys
from fractions import Fraction
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox
)

DOSSIER_HUB = Path(__file__).resolve().parents[3]  # .../PyHub
sys.path.insert(0, str(DOSSIER_HUB / "data"))
from formule_utils import parser_formule_avec_charge  # noqa: E402

TITRE_PROGRAMME = "Demi-équations rédox (équilibrage automatique)"
DESCRIPTION = (
    "Donnez la forme oxydée (Ox) et la forme réduite (Red) d'un couple, avec "
    "la charge (ex: MnO4-, Fe3+, Cr2O7^2-) : la demi-équation est équilibrée "
    "automatiquement, en milieu acide et en milieu basique."
)
EXEMPLE_OX = "MnO4-"
EXEMPLE_RED = "Mn2+"


# ============================================================
# Détermination du ratio "squelette" (a, b) tel que a·Ox = b·Red pour un
# élément conservé — d'abord un élément autre que O/H, sinon O, sinon H.
# ============================================================
def determiner_ratio_squelette(elements_ox, elements_red):
    def essayer(elements_a_tester):
        ratio = None
        for el in elements_a_tester:
            na = elements_ox.get(el, 0)
            nb = elements_red.get(el, 0)
            if na == 0 or nb == 0:
                continue
            fraction = Fraction(nb, na)
            if ratio is None:
                ratio = fraction
            elif ratio != fraction:
                return None
        return ratio

    squelette = sorted((set(elements_ox) | set(elements_red)) - {"O", "H"})
    ratio = essayer(squelette) if squelette else None
    source = ", ".join(squelette) if ratio is not None else None
    if ratio is None:
        ratio = essayer(["O"])
        source = "l'oxygène" if ratio is not None else None
    if ratio is None:
        ratio = essayer(["H"])
        source = "l'hydrogène" if ratio is not None else None
    if ratio is None:
        raise ValueError(
            "Impossible de déterminer les coefficients de base : aucun élément "
            "commun cohérent entre les deux formes du couple. Vérifiez les formules."
        )
    return ratio.numerator, ratio.denominator, source


# ============================================================
# Équilibrage complet : O (via H2O), H (via H+), charge (via e-)
# ============================================================
def equilibrer_demi_equation(elements_ox, charge_ox, elements_red, charge_red):
    a, b, source = determiner_ratio_squelette(elements_ox, elements_red)

    o_ox, o_red = elements_ox.get("O", 0), elements_red.get("O", 0)
    h_ox, h_red = elements_ox.get("H", 0), elements_red.get("H", 0)

    h2o = b * o_red - a * o_ox         # >0 : côté Ox (gauche) ; <0 : côté Red (droite)
    hplus = -(a * h_ox - b * h_red + h2o * 2)
    n_e = a * charge_ox - b * charge_red + hplus

    if n_e == 0:
        raise ValueError(
            "Aucun échange d'électrons trouvé entre ces deux espèces : ce n'est "
            "pas une transformation rédox (ou Ox et Red sont identiques)."
        )

    return {"a": a, "b": b, "h2o": h2o, "hplus": hplus, "n_e": n_e, "source_squelette": source}


def _ajouter(cote, espece, quantite, avant_electrons=False):
    for i, (c, e) in enumerate(cote):
        if e == espece:
            cote[i] = (c + quantite, e)
            return
    if avant_electrons:
        indice_e = next((i for i, (c, e) in enumerate(cote) if e == "e-"), len(cote))
        cote.insert(indice_e, (quantite, espece))
    else:
        cote.append((quantite, espece))


def construire_presentation(resultat, texte_ox, texte_red):
    gauche, droite = [], []
    gauche.append((resultat["a"], texte_ox))
    droite.append((resultat["b"], texte_red))

    if resultat["h2o"] > 0:
        _ajouter(gauche, "H2O", resultat["h2o"])
    elif resultat["h2o"] < 0:
        _ajouter(droite, "H2O", -resultat["h2o"])

    if resultat["hplus"] > 0:
        _ajouter(gauche, "H+", resultat["hplus"])
    elif resultat["hplus"] < 0:
        _ajouter(droite, "H+", -resultat["hplus"])

    if resultat["n_e"] > 0:
        _ajouter(gauche, "e-", resultat["n_e"])
        type_reaction = "réduction (l'espèce de gauche GAGNE des électrons)"
    else:
        _ajouter(droite, "e-", -resultat["n_e"])
        type_reaction = "oxydation (l'espèce de gauche PERD des électrons)"

    return gauche, droite, type_reaction


def _simplifier_espece_commune(gauche, droite, espece):
    gauche, droite = list(gauche), list(droite)
    ig = next((i for i, (c, e) in enumerate(gauche) if e == espece), None)
    idr = next((i for i, (c, e) in enumerate(droite) if e == espece), None)
    if ig is None or idr is None:
        return gauche, droite
    cg, cd = gauche[ig][0], droite[idr][0]
    minimum = min(cg, cd)
    if cg == minimum:
        del gauche[ig]
    else:
        gauche[ig] = (cg - minimum, espece)
    if cd == minimum:
        del droite[idr]
    else:
        droite[idr] = (cd - minimum, espece)
    return gauche, droite


def convertir_milieu_basique(gauche, droite):
    """Ajoute autant de OH- que de H+ des deux côtés, combine H+ + OH- en
    H2O du côté qui avait les H+, puis simplifie le H2O commun aux 2 côtés."""
    ig = next((i for i, (c, e) in enumerate(gauche) if e == "H+"), None)
    idr = next((i for i, (c, e) in enumerate(droite) if e == "H+"), None)
    if ig is None and idr is None:
        return gauche, droite  # pas de H+ : rien à convertir

    gauche, droite = list(gauche), list(droite)
    if ig is not None:
        n_h = gauche[ig][0]
        del gauche[ig]
        _ajouter(gauche, "H2O", n_h, avant_electrons=True)
        _ajouter(droite, "OH-", n_h, avant_electrons=True)
    else:
        n_h = droite[idr][0]
        del droite[idr]
        _ajouter(droite, "H2O", n_h, avant_electrons=True)
        _ajouter(gauche, "OH-", n_h, avant_electrons=True)

    return _simplifier_espece_commune(gauche, droite, "H2O")


def formater_cote(cote):
    return " + ".join(f"{c} {e}" if c != 1 else e for c, e in cote)


def formater_equation(gauche, droite):
    return f"{formater_cote(gauche)} = {formater_cote(droite)}"


class FenetreProgramme(QWidget):
    def __init__(self):
        super().__init__()
        self._construire_ui()

    def _construire_ui(self):
        self.setWindowTitle(TITRE_PROGRAMME)
        self.resize(660, 420)

        layout = QVBoxLayout(self)

        titre = QLabel(TITRE_PROGRAMME)
        titre.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(titre)

        desc = QLabel(DESCRIPTION)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)

        formulaire = QFormLayout()
        self.champ_ox = QLineEdit(EXEMPLE_OX)
        self.champ_ox.setPlaceholderText(f"ex: {EXEMPLE_OX}")
        formulaire.addRow("Forme oxydée (Ox) :", self.champ_ox)

        self.champ_red = QLineEdit(EXEMPLE_RED)
        self.champ_red.setPlaceholderText(f"ex: {EXEMPLE_RED}")
        formulaire.addRow("Forme réduite (Red) :", self.champ_red)
        layout.addLayout(formulaire)

        astuce = QLabel(
            "Astuce : pour un ion polyatomique de charge > 1, utilisez '^' "
            "pour éviter toute ambiguïté avec un indice — ex: SO4^2-, Cr2O7^2-"
        )
        astuce.setWordWrap(True)
        astuce.setStyleSheet("color: #888; font-style: italic; font-size: 11px;")
        layout.addWidget(astuce)

        bouton = QPushButton("Équilibrer la demi-équation")
        bouton.clicked.connect(self._on_equilibrer)
        layout.addWidget(bouton)

        self.label_type = QLabel("")
        self.label_type.setStyleSheet("color: #444; font-style: italic;")
        layout.addWidget(self.label_type)

        layout.addWidget(QLabel("Milieu acide :"))
        self.label_acide = self._creer_label_resultat()
        layout.addWidget(self.label_acide)

        layout.addWidget(QLabel("Milieu basique :"))
        self.label_basique = self._creer_label_resultat()
        layout.addWidget(self.label_basique)

        layout.addStretch(1)

    def _creer_label_resultat(self):
        label = QLabel("")
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 15px; font-weight: bold; font-family: monospace;")
        label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        label.setCursor(QCursor(Qt.IBeamCursor))
        return label

    def _on_equilibrer(self):
        texte_ox = self.champ_ox.text().strip()
        texte_red = self.champ_red.text().strip()

        try:
            elements_ox, charge_ox = parser_formule_avec_charge(texte_ox)
        except ValueError as e:
            QMessageBox.warning(self, "Forme oxydée invalide", str(e))
            return
        try:
            elements_red, charge_red = parser_formule_avec_charge(texte_red)
        except ValueError as e:
            QMessageBox.warning(self, "Forme réduite invalide", str(e))
            return

        try:
            resultat = equilibrer_demi_equation(elements_ox, charge_ox, elements_red, charge_red)
        except ValueError as e:
            QMessageBox.warning(self, "Équilibrage impossible", str(e))
            return

        gauche, droite, type_reaction = construire_presentation(resultat, texte_ox, texte_red)
        equation_acide = formater_equation(gauche, droite)
        gauche_b, droite_b = convertir_milieu_basique(gauche, droite)
        equation_basique = formater_equation(gauche_b, droite_b)

        self.label_type.setText(
            f"Type : {type_reaction} — élément de référence : {resultat['source_squelette']}"
        )
        self.label_acide.setText(equation_acide)
        self.label_basique.setText(equation_basique)


def main():
    app = QApplication(sys.argv)
    fenetre = FenetreProgramme()
    fenetre.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
