"""
INGÉNIERIE — Poutre simplement appuyée, charge ponctuelle centrée
====================================================================
Calcule la flèche maximale, le moment fléchissant maximal et la contrainte
maximale d'une poutre à section rectangulaire, et trace le diagramme du
moment fléchissant le long de la poutre.

Cet exemple montre comment intégrer un graphique matplotlib dans le
template : dépendance supplémentaire -> pip install matplotlib numpy
"""

import sys
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QDoubleSpinBox, QPushButton, QTextEdit, QMessageBox
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

TITRE_PROGRAMME = "Poutre simplement appuyée — charge centrée"
DESCRIPTION = "Flèche, contrainte et diagramme du moment fléchissant (section rectangulaire)."

CHAMPS = [
    ("charge",       "Charge ponctuelle centrée (P)", 1000.0, 0.0,    1e9,  "N"),
    ("longueur",     "Longueur de la poutre (L)",         2.0, 0.001, 1e4,  "m"),
    ("module_young", "Module d'Young (E)",              210.0, 0.001, 1e6,  "GPa"),
    ("largeur",      "Largeur de la section (b)",        0.05, 0.0001, 10.0, "m"),
    ("hauteur",      "Hauteur de la section (h)",        0.10, 0.0001, 10.0, "m"),
]


class FenetreProgramme(QWidget):
    def __init__(self):
        super().__init__()
        self.champs_widgets = {}
        self._construire_ui()

    def _construire_ui(self):
        self.setWindowTitle(TITRE_PROGRAMME)
        self.resize(840, 520)

        layout_racine = QHBoxLayout(self)

        # --- colonne de gauche : formulaire + résultats texte ---
        colonne_gauche = QVBoxLayout()

        titre = QLabel(TITRE_PROGRAMME)
        titre.setStyleSheet("font-size: 16px; font-weight: bold;")
        colonne_gauche.addWidget(titre)

        desc = QLabel(DESCRIPTION)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666;")
        colonne_gauche.addWidget(desc)

        formulaire = QFormLayout()
        for nom, label, defaut, mini, maxi, unite in CHAMPS:
            spin = QDoubleSpinBox()
            spin.setDecimals(5)
            spin.setRange(mini, maxi)
            spin.setValue(defaut)
            spin.setSuffix(f" {unite}" if unite else "")
            self.champs_widgets[nom] = spin
            formulaire.addRow(label + " :", spin)
        colonne_gauche.addLayout(formulaire)

        bouton = QPushButton("Calculer")
        bouton.clicked.connect(self._on_calculer)
        colonne_gauche.addWidget(bouton)

        self.zone_resultat = QTextEdit()
        self.zone_resultat.setReadOnly(True)
        self.zone_resultat.setMaximumHeight(170)
        colonne_gauche.addWidget(self.zone_resultat)

        layout_racine.addLayout(colonne_gauche, stretch=1)

        # --- colonne de droite : graphique ---
        self.figure = Figure(figsize=(5, 4))
        self.canvas = FigureCanvas(self.figure)
        layout_racine.addWidget(self.canvas, stretch=1)

    def _on_calculer(self):
        valeurs = {nom: w.value() for nom, w in self.champs_widgets.items()}
        try:
            texte, x, moment = calculer(valeurs)
        except Exception as e:
            QMessageBox.critical(self, "Erreur de calcul", str(e))
            return
        self.zone_resultat.setPlainText(texte)
        self._tracer(x, moment)

    def _tracer(self, x, moment):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.plot(x, moment, color="#3477eb")
        ax.fill_between(x, moment, alpha=0.2, color="#3477eb")
        ax.set_xlabel("Position le long de la poutre (m)")
        ax.set_ylabel("Moment fléchissant (N·m)")
        ax.set_title("Diagramme du moment fléchissant")
        ax.grid(True, alpha=0.3)
        self.figure.tight_layout()
        self.canvas.draw()


def calculer(valeurs):
    p = valeurs["charge"]
    l = valeurs["longueur"]
    e_pa = valeurs["module_young"] * 1e9  # GPa -> Pa
    b = valeurs["largeur"]
    h = valeurs["hauteur"]

    inertie = b * h ** 3 / 12  # moment quadratique de la section, m^4
    v = h / 2                   # distance à la fibre neutre

    m_max = p * l / 4
    sigma_max = m_max * v / inertie
    fleche_max = p * l ** 3 / (48 * e_pa * inertie)

    x = np.linspace(0, l, 200)
    moment = np.where(x <= l / 2, (p / 2) * x, (p / 2) * (l - x))

    texte = (
        f"Moment quadratique (I) : {inertie:.6e} m⁴\n"
        f"Moment fléchissant max : {m_max:.2f} N·m (au centre)\n"
        f"Contrainte normale max : {sigma_max / 1e6:.3f} MPa\n"
        f"Flèche max au centre : {fleche_max * 1000:.4f} mm"
    )
    return texte, x, moment


def main():
    app = QApplication(sys.argv)
    fenetre = FenetreProgramme()
    fenetre.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
