"""
AÉROSPATIALE — Équation de la fusée de Tsiolkovsky
======================================================
Calcule le delta-v disponible d'une fusée (ou étage) à partir de son
impulsion spécifique et de ses masses initiale/finale, ainsi que la
masse d'ergols nécessaire.
"""

import math
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QFormLayout, QLabel,
    QDoubleSpinBox, QPushButton, QTextEdit, QMessageBox
)

TITRE_PROGRAMME = "Équation de Tsiolkovsky (delta-v d'une fusée)"
DESCRIPTION = "Delta-v disponible, ratio de masse et fraction d'ergols nécessaire."

G0 = 9.80665  # m/s^2, accélération de référence utilisée pour l'Isp

CHAMPS = [
    ("masse_initiale", "Masse initiale (m0, avec ergols)", 50000.0, 0.001, 1e9, "kg"),
    ("masse_finale",   "Masse finale (mf, à sec)",          8000.0, 0.001, 1e9, "kg"),
    ("isp",             "Impulsion spécifique (Isp)",        311.0, 1.0,   1e5, "s"),
]


class FenetreProgramme(QWidget):
    def __init__(self):
        super().__init__()
        self.champs_widgets = {}
        self._construire_ui()

    def _construire_ui(self):
        self.setWindowTitle(TITRE_PROGRAMME)
        self.resize(480, 400)

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
            spin.setDecimals(3)
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
    m0 = valeurs["masse_initiale"]
    mf = valeurs["masse_finale"]
    isp = valeurs["isp"]

    if mf > m0:
        raise ValueError("La masse finale ne peut pas être supérieure à la masse initiale.")
    if mf <= 0:
        raise ValueError("La masse finale doit être strictement positive.")

    ratio_masse = m0 / mf
    vitesse_ejection = isp * G0
    delta_v = vitesse_ejection * math.log(ratio_masse)
    masse_ergols = m0 - mf
    fraction_ergols = masse_ergols / m0

    return (
        f"Vitesse d'éjection effective (Isp·g0) : {vitesse_ejection:.1f} m/s\n"
        f"Ratio de masse (m0/mf) : {ratio_masse:.3f}\n"
        f"Delta-v disponible : {delta_v:.1f} m/s  ({delta_v / 1000:.3f} km/s)\n"
        f"Masse d'ergols consommée : {masse_ergols:.1f} kg\n"
        f"Fraction de masse en ergols : {fraction_ergols * 100:.1f} %"
    )


def main():
    app = QApplication(sys.argv)
    fenetre = FenetreProgramme()
    fenetre.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
