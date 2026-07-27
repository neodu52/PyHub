"""
CHIMIE — Bilan de réaction : stœchiométrie (avec PubChem)
============================================================
Saisissez une équation bilan avec des NOMS de composés ou des FORMULES,
par exemple :

    1 acetone + 4 O2 = 3 CO2 + 3 H2O

indiquez la quantité connue d'UNE seule espèce (en mol ou en g), et le
programme calcule la quantité (mol + g) de TOUTES les autres espèces à
partir des coefficients de l'équation.

Les propriétés de chaque composé (masse molaire, formule) sont d'abord
cherchées dans le cache local partagé (data/composes_locale.json). Si un
composé est absent du cache, le programme interroge automatiquement
PubChem (https://pubchem.ncbi.nlm.nih.gov, gratuit, sans clé) et enregistre
le résultat dans le cache : la prochaine fois, plus besoin d'Internet pour
ce composé.

Dépendance supplémentaire : requests (pip install requests)
"""

import sys
import re
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QComboBox,
    QDoubleSpinBox, QMessageBox, QHeaderView
)

# Le module partagé data/pubchem_utils.py vit à la racine du hub (PyHub/data/).
# On l'ajoute au chemin de recherche des modules pour pouvoir l'importer,
# même si ce programme est lancé comme un script indépendant (subprocess).
DOSSIER_HUB = Path(__file__).resolve().parents[3]  # .../PyHub
sys.path.insert(0, str(DOSSIER_HUB / "data"))
import pubchem_utils as pc  # noqa: E402

TITRE_PROGRAMME = "Bilan de réaction — stœchiométrie (PubChem)"
DESCRIPTION = (
    "Saisissez une équation bilan (noms ou formules), donnez la quantité "
    "connue d'une espèce, et obtenez la quantité (mol et g) de toutes les autres."
)
EXEMPLE_EQUATION = "1 acetone + 4 O2 = 3 CO2 + 3 H2O"


class FenetreProgramme(QWidget):
    def __init__(self):
        super().__init__()
        self.especes = []  # liste de dicts après analyse + résolution des propriétés
        self._construire_ui()

    def _construire_ui(self):   # fenetre
        self.setWindowTitle(TITRE_PROGRAMME)
        self.resize(780, 580)

        layout = QVBoxLayout(self)

        titre = QLabel(TITRE_PROGRAMME)
        titre.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(titre)

        desc = QLabel(DESCRIPTION)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)

        # --- saisie de l'équation ---
        ligne_equation = QHBoxLayout()
        ligne_equation.addWidget(QLabel("Équation :"))
        self.champ_equation = QLineEdit()
        self.champ_equation.setPlaceholderText(EXEMPLE_EQUATION)
        self.champ_equation.setText(EXEMPLE_EQUATION)
        ligne_equation.addWidget(self.champ_equation, stretch=1)
        self.bouton_analyser = QPushButton("Analyser l'équation")
        self.bouton_analyser.clicked.connect(self._on_analyser)
        ligne_equation.addWidget(self.bouton_analyser)
        layout.addLayout(ligne_equation)

        self.label_statut = QLabel(
            "Astuce : noms anglais ('acetone', 'water') ou formules ('CO2', 'NaCl') "
            "fonctionnent le mieux avec PubChem."
        )
        self.label_statut.setWordWrap(True)
        self.label_statut.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.label_statut)

        # --- tableau des espèces ---
        self.tableau = QTableWidget(0, 6)
        self.tableau.setHorizontalHeaderLabels(
            ["Rôle", "Coeff.", "Composé (saisi)", "Formule", "M (g/mol)", "Quantité calculée"]
        )
        
        self.tableau.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tableau.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tableau, stretch=1)

        # --- espèce de référence + quantité connue ---
        ligne_calcul = QFormLayout()

        self.combo_reference = QComboBox()
        ligne_calcul.addRow("Espèce connue :", self.combo_reference)

        ligne_quantite = QHBoxLayout()
        self.champ_quantite = QDoubleSpinBox()
        self.champ_quantite.setDecimals(4)
        self.champ_quantite.setRange(0.0, 1e9)
        self.champ_quantite.setValue(10.0)
        self.combo_unite = QComboBox()
        self.combo_unite.addItems(["mol", "g"])
        ligne_quantite.addWidget(self.champ_quantite)
        ligne_quantite.addWidget(self.combo_unite)
        ligne_calcul.addRow("Quantité connue :", ligne_quantite)

        layout.addLayout(ligne_calcul)

        self.bouton_calculer = QPushButton("Calculer les quantités")
        self.bouton_calculer.clicked.connect(self._on_calculer)
        self.bouton_calculer.setEnabled(False)
        layout.addWidget(self.bouton_calculer)

    # ------------------------------------------------------------------
    def _on_analyser(self):
        texte = self.champ_equation.text()
        try:
            especes_brutes = analyser_equation(texte)
        except ValueError as e:
            QMessageBox.warning(self, "Équation invalide", str(e))
            return

        self.setCursor(QCursor(Qt.WaitCursor))
        self.bouton_analyser.setEnabled(False)
        QApplication.processEvents()

        especes_resolues = []
        nb_locale = nb_pubchem = 0
        erreurs = []
        for espece in especes_brutes:
            try:
                proprietes = pc.obtenir_proprietes(espece["nom_saisi"])
            except pc.ComposeIntrouvable as e:
                erreurs.append(str(e))
                continue
            especes_resolues.append({**espece, **proprietes})
            if proprietes["source"] == "locale":
                nb_locale += 1
            else:
                nb_pubchem += 1

        self.setCursor(QCursor(Qt.ArrowCursor))
        self.bouton_analyser.setEnabled(True)

        if erreurs:
            QMessageBox.critical(self, "Composé(s) introuvable(s)", "\n\n".join(erreurs))
            return

        self.especes = especes_resolues
        self._remplir_tableau()

        self.combo_reference.clear()
        self.combo_reference.addItems(
            [f"{e['nom_saisi']} ({e['formule']})" for e in self.especes]
        )
        self.bouton_calculer.setEnabled(True)

        statut = (
            f"{len(self.especes)} composé(s) résolu(s) — {nb_locale} depuis le cache local, "
            f"{nb_pubchem} via PubChem (désormais mis en cache pour la prochaine fois)."
        )
        if any(e.get("ambigu") for e in self.especes):
            statut += (
                " ⚠️ Au moins une formule a été résolue de façon ambiguë "
                "(plusieurs composés partagent cette formule) : vérifiez la colonne Formule."
            )
        self.label_statut.setText(statut)

    def _remplir_tableau(self):
        self.tableau.setRowCount(len(self.especes))
        for ligne, espece in enumerate(self.especes):
            role_affiche = "Réactif" if espece["role"] == "reactif" else "Produit"
            valeurs = [
                role_affiche,
                f"{espece['coefficient']:g}",
                espece["nom_saisi"],
                espece["formule"],
                f"{espece['masse_molaire']:.3f}",
                "",
            ]
            for colonne, valeur in enumerate(valeurs):
                item = QTableWidgetItem(valeur)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.tableau.setItem(ligne, colonne, item)

    def _on_calculer(self):
        indice_reference = self.combo_reference.currentIndex()
        if indice_reference < 0 or not self.especes:
            return

        quantite = self.champ_quantite.value()
        unite = self.combo_unite.currentText()

        try:
            resultats = calculer_quantites(self.especes, indice_reference, quantite, unite)
        except ZeroDivisionError:
            QMessageBox.critical(self, "Erreur", "Coefficient nul pour l'espèce de référence.")
            return

        for ligne, resultat in enumerate(resultats):
            texte_quantite = f"{resultat['mol']:.4f} mol   ({resultat['masse_g']:.3f} g)"
            item = QTableWidgetItem(texte_quantite)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.tableau.setItem(ligne, 5, item)


# ============================================================
# Analyse de l'équation : texte -> liste de {role, coefficient, nom_saisi}
# ============================================================
def analyser_equation(texte):
    texte = texte.strip()
    if not texte:
        raise ValueError("L'équation est vide.")

    # accepte "=", "->", "-->", "→", "⟶" comme séparateur réactifs/produits
    texte_normalise = re.sub(r"-+>|→|⟶", "=", texte)
    if "=" not in texte_normalise:
        raise ValueError(
            "L'équation doit contenir un séparateur '=' (ou '->') entre réactifs et produits.\n"
            f"Exemple : {EXEMPLE_EQUATION}"
        )

    partie_gauche, partie_droite = texte_normalise.split("=", 1)

    especes = []
    for role, termes_bruts in (("reactif", partie_gauche), ("produit", partie_droite)):
        termes = [t.strip() for t in termes_bruts.split("+") if t.strip()]
        if not termes:
            raise ValueError("Chaque côté de l'équation doit contenir au moins un composé.")
        for terme in termes:
            correspondance = re.match(r"^([0-9]+(?:[.,][0-9]+)?)?\s*(.+)$", terme)
            coefficient_str = correspondance.group(1)
            nom = correspondance.group(2).strip()
            if not nom:
                raise ValueError(f"Terme illisible dans l'équation : « {terme} »")
            coefficient = float(coefficient_str.replace(",", ".")) if coefficient_str else 1.0
            especes.append({"role": role, "coefficient": coefficient, "nom_saisi": nom})
    return especes


# ============================================================
# Calcul des quantités (mol + g) de toutes les espèces à partir d'une référence
# ============================================================
def calculer_quantites(especes, indice_reference, quantite_reference, unite_reference):
    reference = especes[indice_reference]
    if reference["coefficient"] == 0:
        raise ZeroDivisionError

    if unite_reference == "g":
        n_reference = quantite_reference / reference["masse_molaire"]
    else:
        n_reference = quantite_reference

    resultats = []
    for espece in especes:
        n = n_reference * (espece["coefficient"] / reference["coefficient"])
        masse = n * espece["masse_molaire"]
        resultats.append({**espece, "mol": n, "masse_g": masse})
    return resultats


def main():
    app = QApplication(sys.argv)
    fenetre = FenetreProgramme()
    fenetre.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
