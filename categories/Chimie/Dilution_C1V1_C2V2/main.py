"""
CHIMIE — Calcul de dilution (C1·V1 = C2·V2)
=============================================
Détermine le volume final et le volume de solvant à ajouter pour diluer
une solution de concentration C1 à une concentration cible C2.
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QFormLayout, QLabel,
    QDoubleSpinBox, QPushButton, QTextEdit, QMessageBox
)

TITRE_PROGRAMME = "Dilution d'une solution (C1V1 = C2V2)"
DESCRIPTION = "Calcule le volume de solvant à ajouter pour obtenir la concentration cible."

CHAMPS = [
    ("c1", "Concentration initiale (C1)", 1.0,   1e-9, 1e6, "mol/L"),
    ("v1", "Volume initial (V1)",       100.0,   1e-6, 1e9, "mL"),
    ("c2", "Concentration cible (C2)",    0.1,   1e-9, 1e6, "mol/L"),
]


class FenetreProgramme(QWidget):
    def __init__(self):
        super().__init__()
        self.champs_widgets = {}
        self._construire_ui()

    def _construire_ui(self):
        self.setWindowTitle(TITRE_PROGRAMME)
        self.resize(460, 380)

        layout = QVBoxLayout(self)
        titre = QLabel(TITRE_PROGRAMME)
        titre.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(titre)

        desc = QLabel(DESCRIPTION)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; margin-bottom: 8px;")
        layout.addWidget(desc)

        formulaire = QFormLayout()
        for nom, label, defaut, mini, maxi, unite in CHAMPS:
            spin = QDoubleSpinBox()
            spin.setDecimals(6)
            spin.setRange(mini, maxi)
            spin.setValue(defaut)
            spin.setSuffix(f" {unite}" if unite else "")
            self.champs_widgets[nom] = spin
            formulaire.addRow(label + " :", spin)
        layout.addLayout(formulaire)

        bouton = QPushButton("Calculer")
        bouton.clicked.connect(self._on_calculer)
        layout.addWidget(bouton)

        self.zone_resultat = QTextEdit()
        self.zone_resultat.setReadOnly(True)
        layout.addWidget(self.zone_resultat)

    def _on_calculer(self):
        valeurs = {nom: w.value() for nom, w in self.champs_widgets.items()}
        try:
            texte = calculer(valeurs)
        except Exception as e:
            QMessageBox.critical(self, "Erreur de calcul", str(e))
            return
        self.zone_resultat.setPlainText(texte)


def calculer(valeurs):
    c1 = valeurs["c1"]
    v1 = valeurs["v1"]
    c2 = valeurs["c2"]

    if c2 > c1:
        raise ValueError(
            "La concentration cible (C2) ne peut pas être supérieure à C1 "
            "(il s'agit d'une dilution, pas d'une concentration)."
        )
    if c2 <= 0:
        raise ValueError("La concentration cible doit être strictement positive.")

    v2 = c1 * v1 / c2
    solvant_a_ajouter = v2 - v1
    facteur_dilution = c1 / c2

    return (
        f"Facteur de dilution : {facteur_dilution:.3f}×\n"
        f"Volume final (V2) : {v2:.3f} mL\n"
        f"Volume de solvant à ajouter : {solvant_a_ajouter:.3f} mL\n\n"
        f"→ Prélevez {v1:.3f} mL de la solution à {c1:g} mol/L,\n"
        f"  complétez avec {solvant_a_ajouter:.3f} mL de solvant,\n"
        f"  pour obtenir {v2:.3f} mL de solution à {c2:g} mol/L."
    )


def main():
    app = QApplication(sys.argv)
    fenetre = FenetreProgramme()
    fenetre.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
