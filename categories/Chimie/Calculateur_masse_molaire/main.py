"""
CHIMIE — Calculateur de masse molaire (tableau périodique local)
====================================================================
Saisissez une formule chimique — H2O, Ca(OH)2, Fe2O3, C6H12O6,
Al2(SO4)3, K4[Fe(CN)6]... — et obtenez sa masse molaire, calculée à
partir du tableau périodique local (data/tableau_periodique.json).

Contrairement au bilan de réaction (categories/Chimie/Bilan_reaction_stoechiometrie),
ce programme ne se connecte jamais à Internet : le tableau périodique est
complet (118 éléments) et tient facilement dans un seul fichier local, donc
aucune requête réseau n'est nécessaire ici.
"""

import re
import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox
)
from PyQt5.QtCore import Qt

# Le tableau périodique partagé vit dans PyHub/data/tableau_periodique.json.
DOSSIER_HUB = Path(__file__).resolve().parents[3]  # .../PyHub
CHEMIN_TABLEAU = DOSSIER_HUB / "data" / "tableau_periodique.json"

TITRE_PROGRAMME = "Calculateur de masse molaire"
DESCRIPTION = (
    "Formule chimique -> masse molaire, à partir du tableau périodique local "
    "(pas de connexion Internet nécessaire)."
)
EXEMPLE_FORMULE = "Ca(OH)2"


def charger_tableau_periodique():
    import json
    if not CHEMIN_TABLEAU.exists():
        raise FileNotFoundError(f"Tableau périodique introuvable : {CHEMIN_TABLEAU}")
    with open(CHEMIN_TABLEAU, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# Analyse d'une formule chimique (gère les parenthèses/crochets imbriqués)
# ============================================================
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


def calculer_masse_molaire(formule, tableau_periodique):
    comptes = parser_formule(formule)
    total = 0.0
    details = []
    for symbole, compte in sorted(comptes.items()):
        if symbole not in tableau_periodique:
            raise ValueError(
                f"Élément inconnu : « {symbole} ». Vérifiez la casse "
                "(ex: 'Co' = cobalt, 'CO' = carbone + oxygène)."
            )
        masse_atome = tableau_periodique[symbole]["masse_molaire"]
        sous_total = compte * masse_atome
        details.append((symbole, compte, masse_atome, sous_total))
        total += sous_total
    return total, details


class FenetreProgramme(QWidget):
    def __init__(self):
        super().__init__()
        try:
            self.tableau_periodique = charger_tableau_periodique()
        except FileNotFoundError as e:
            self.tableau_periodique = None
            self._erreur_chargement = str(e)
        else:
            self._erreur_chargement = None
        self._construire_ui()

    def _construire_ui(self):
        self.setWindowTitle(TITRE_PROGRAMME)
        self.resize(560, 480)

        layout = QVBoxLayout(self)

        titre = QLabel(TITRE_PROGRAMME)
        titre.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(titre)

        desc = QLabel(DESCRIPTION)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; margin-bottom: 8px;")
        layout.addWidget(desc)

        if self._erreur_chargement:
            erreur = QLabel(f"⚠️ {self._erreur_chargement}")
            erreur.setStyleSheet("color: #c0392b;")
            erreur.setWordWrap(True)
            layout.addWidget(erreur)

        ligne_formule = QHBoxLayout()
        ligne_formule.addWidget(QLabel("Formule :"))
        self.champ_formule = QLineEdit()
        self.champ_formule.setPlaceholderText(EXEMPLE_FORMULE)
        self.champ_formule.setText(EXEMPLE_FORMULE)
        self.champ_formule.returnPressed.connect(self._on_calculer)
        ligne_formule.addWidget(self.champ_formule, stretch=1)
        bouton = QPushButton("Calculer")
        bouton.clicked.connect(self._on_calculer)
        ligne_formule.addWidget(bouton)
        layout.addLayout(ligne_formule)

        self.label_resultat = QLabel("")
        self.label_resultat.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 6px;")
        layout.addWidget(self.label_resultat)

        self.tableau = QTableWidget(0, 4)
        self.tableau.setHorizontalHeaderLabels(
            ["Élément", "Quantité", "M atomique (g/mol)", "Sous-total (g/mol)"]
        )
        self.tableau.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tableau.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tableau, stretch=1)

        exemples = QLabel(
            "Exemples : H2O · CO2 · NaCl · Ca(OH)2 · Fe2O3 · C6H12O6 · "
            "Al2(SO4)3 · K4[Fe(CN)6]"
        )
        exemples.setStyleSheet("color: #666; font-style: italic;")
        exemples.setWordWrap(True)
        layout.addWidget(exemples)

        if self.tableau_periodique is not None:
            self._on_calculer()

    def _on_calculer(self):
        if self.tableau_periodique is None:
            QMessageBox.critical(self, "Erreur", self._erreur_chargement)
            return

        formule = self.champ_formule.text()
        try:
            total, details = calculer_masse_molaire(formule, self.tableau_periodique)
        except ValueError as e:
            QMessageBox.warning(self, "Formule invalide", str(e))
            return

        self.label_resultat.setText(f"M({formule}) = {total:.3f} g/mol")

        self.tableau.setRowCount(len(details))
        for ligne, (symbole, compte, masse_atome, sous_total) in enumerate(details):
            nom = self.tableau_periodique[symbole]["nom"]
            valeurs = [
                f"{symbole} — {nom}",
                str(compte),
                f"{masse_atome:g}",
                f"{sous_total:.3f}",
            ]
            for colonne, valeur in enumerate(valeurs):
                item = QTableWidgetItem(valeur)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.tableau.setItem(ligne, colonne, item)


def main():
    app = QApplication(sys.argv)
    fenetre = FenetreProgramme()
    fenetre.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
