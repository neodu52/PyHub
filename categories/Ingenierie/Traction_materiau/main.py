"""
INGÉNIERIE — Traction simple : contrainte, allongement, coefficient de sécurité
==================================================================================
Choisissez un matériau dans le menu déroulant (propriétés issues de
data/materiaux.json), donnez une force de traction, une section et une
longueur initiale, et obtenez la contrainte, l'allongement (loi de Hooke),
et le coefficient de sécurité par rapport à la limite élastique du matériau.

⚠️ Valeurs matériaux typiques/indicatives (voir data/materiaux.json) — à
vérifier avec une fiche technique réelle pour un usage critique.
"""

import json
import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QComboBox, QDoubleSpinBox, QPushButton, QTextEdit, QMessageBox
)

DOSSIER_HUB = Path(__file__).resolve().parents[3]  # .../PyHub
CHEMIN_MATERIAUX = DOSSIER_HUB / "data" / "materiaux.json"

TITRE_PROGRAMME = "Traction simple (contrainte, allongement, coefficient de sécurité)"
DESCRIPTION = (
    "Loi de Hooke : contrainte = F/A, déformation = contrainte/E, "
    "allongement = déformation × L0. Propriétés issues de data/materiaux.json."
)


def charger_materiaux():
    if not CHEMIN_MATERIAUX.exists():
        raise FileNotFoundError(f"Base matériaux introuvable : {CHEMIN_MATERIAUX}")
    with open(CHEMIN_MATERIAUX, "r", encoding="utf-8") as f:
        return json.load(f)["materiaux"]


def calculer_traction(materiau, force_N, section_mm2, longueur_mm):
    if section_mm2 <= 0:
        raise ValueError("La section doit être strictement positive.")
    module_young_Pa = materiau["module_young_GPa"] * 1e9
    section_m2 = section_mm2 * 1e-6

    contrainte_MPa = (force_N / section_m2) / 1e6
    deformation = (contrainte_MPa * 1e6) / module_young_Pa
    allongement_mm = deformation * longueur_mm

    coefficient_securite = None
    if materiau.get("limite_elastique_MPa"):
        coefficient_securite = materiau["limite_elastique_MPa"] / contrainte_MPa

    return contrainte_MPa, deformation, allongement_mm, coefficient_securite


class FenetreProgramme(QWidget):
    def __init__(self):
        super().__init__()
        try:
            self.materiaux = charger_materiaux()
            self._erreur_chargement = None
        except FileNotFoundError as e:
            self.materiaux = {}
            self._erreur_chargement = str(e)
        self._construire_ui()

    def _construire_ui(self):
        self.setWindowTitle(TITRE_PROGRAMME)
        self.resize(560, 560)

        layout = QVBoxLayout(self)

        titre = QLabel(TITRE_PROGRAMME)
        titre.setStyleSheet("font-size: 16px; font-weight: bold;")
        titre.setWordWrap(True)
        layout.addWidget(titre)

        desc = QLabel(DESCRIPTION)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)

        if self._erreur_chargement:
            erreur = QLabel(f"⚠️ {self._erreur_chargement}")
            erreur.setStyleSheet("color: #c0392b;")
            erreur.setWordWrap(True)
            layout.addWidget(erreur)

        ligne_materiau = QHBoxLayout()
        ligne_materiau.addWidget(QLabel("Matériau :"))
        self.combo_materiau = QComboBox()
        self.combo_materiau.addItems(sorted(self.materiaux.keys()))
        self.combo_materiau.currentTextChanged.connect(self._afficher_proprietes)
        ligne_materiau.addWidget(self.combo_materiau, stretch=1)
        layout.addLayout(ligne_materiau)

        self.label_proprietes = QLabel("")
        self.label_proprietes.setWordWrap(True)
        self.label_proprietes.setStyleSheet("color: #444; font-family: monospace; font-size: 11px;")
        layout.addWidget(self.label_proprietes)

        formulaire = QFormLayout()
        self.champ_force = QDoubleSpinBox()
        self.champ_force.setRange(0.0, 1e9)
        self.champ_force.setValue(10000.0)
        self.champ_force.setSuffix(" N")
        formulaire.addRow("Force de traction (F) :", self.champ_force)

        self.champ_section = QDoubleSpinBox()
        self.champ_section.setRange(0.001, 1e9)
        self.champ_section.setValue(100.0)
        self.champ_section.setSuffix(" mm²")
        formulaire.addRow("Section (A) :", self.champ_section)

        self.champ_longueur = QDoubleSpinBox()
        self.champ_longueur.setRange(0.001, 1e9)
        self.champ_longueur.setValue(1000.0)
        self.champ_longueur.setSuffix(" mm")
        formulaire.addRow("Longueur initiale (L0) :", self.champ_longueur)

        layout.addLayout(formulaire)

        bouton = QPushButton("Calculer")
        bouton.clicked.connect(self._on_calculer)
        layout.addWidget(bouton)

        self.zone_resultat = QTextEdit()
        self.zone_resultat.setReadOnly(True)
        layout.addWidget(self.zone_resultat)

        if self.materiaux:
            self._afficher_proprietes(self.combo_materiau.currentText())

    def _afficher_proprietes(self, nom_materiau):
        if not nom_materiau or nom_materiau not in self.materiaux:
            self.label_proprietes.setText("")
            return
        m = self.materiaux[nom_materiau]
        re_txt = f"{m['limite_elastique_MPa']} MPa" if m.get("limite_elastique_MPa") else "non applicable / inconnue"
        self.label_proprietes.setText(
            f"E = {m['module_young_GPa']} GPa   ν = {m['coefficient_poisson']}   "
            f"ρ = {m['densite_kg_m3']} kg/m³   Re = {re_txt}   "
            f"Rm = {m.get('resistance_traction_MPa', '?')} MPa"
        )

    def _on_calculer(self):
        if not self.materiaux:
            QMessageBox.critical(self, "Erreur", self._erreur_chargement)
            return

        nom_materiau = self.combo_materiau.currentText()
        materiau = self.materiaux[nom_materiau]
        force = self.champ_force.value()
        section = self.champ_section.value()
        longueur = self.champ_longueur.value()

        try:
            contrainte, deformation, allongement, coefficient_securite = calculer_traction(
                materiau, force, section, longueur
            )
        except ValueError as e:
            QMessageBox.warning(self, "Erreur de calcul", str(e))
            return

        lignes = [
            f"Matériau : {nom_materiau}",
            f"Contrainte (σ = F/A) : {contrainte:.4f} MPa",
            f"Déformation (ε = σ/E) : {deformation:.6e}",
            f"Allongement (ΔL = ε × L0) : {allongement:.4f} mm",
        ]
        if coefficient_securite is not None:
            lignes.append(f"Coefficient de sécurité (Re/σ) : {coefficient_securite:.2f}")
            if coefficient_securite < 1:
                lignes.append("⚠️ La contrainte dépasse la limite élastique (Re) : déformation plastique attendue.")
        else:
            lignes.append(
                "Coefficient de sécurité : non calculable (limite élastique inconnue ou "
                "non applicable pour ce matériau — matériau fragile, voir résistance en flexion/compression)."
            )

        self.zone_resultat.setPlainText("\n".join(lignes))


def main():
    app = QApplication(sys.argv)
    fenetre = FenetreProgramme()
    fenetre.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
