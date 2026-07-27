"""
PHYSIQUE — Chute libre avec frottement de l'air
=================================================
Calcule le temps de chute et la vitesse d'impact d'un objet, avec et sans
frottement de l'air (traînée quadratique), par intégration numérique
(méthode d'Euler).
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QFormLayout, QLabel,
    QDoubleSpinBox, QPushButton, QTextEdit, QMessageBox
)

TITRE_PROGRAMME = "Chute libre avec frottement de l'air"
DESCRIPTION = "Compare la chute libre théorique (sans air) à une chute réaliste avec traînée."

RHO_AIR = 1.225  # kg/m^3, masse volumique de l'air au niveau de la mer
G = 9.81         # m/s^2

CHAMPS = [
    ("masse",   "Masse de l'objet",             1.0,  0.001, 1e5,  "kg"),
    ("hauteur", "Hauteur de chute",             50.0,  0.01,  1e6,  "m"),
    ("cx",      "Coefficient de traînée (Cx)",   0.47, 0.0,   5.0,  ""),
    ("surface", "Surface frontale",              0.05, 0.0001, 1e3, "m²"),
]


class FenetreProgramme(QWidget):
    def __init__(self):
        super().__init__()
        self.champs_widgets = {}
        self._construire_ui()

    def _construire_ui(self):
        self.setWindowTitle(TITRE_PROGRAMME)
        self.resize(500, 440)

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
            spin.setDecimals(5)
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
    m = valeurs["masse"]
    h = valeurs["hauteur"]
    cx = valeurs["cx"]
    a = valeurs["surface"]

    # --- résultat théorique sans frottement ---
    t_sans_frottement = (2 * h / G) ** 0.5
    v_sans_frottement = G * t_sans_frottement

    # --- intégration numérique avec frottement quadratique (méthode d'Euler) ---
    dt = 0.0005
    t, x, v = 0.0, 0.0, 0.0
    t_max = 10 * max(t_sans_frottement, 1.0)  # garde-fou anti-boucle infinie

    while x < h and t < t_max:
        force_trainee = 0.5 * RHO_AIR * cx * a * v ** 2
        acceleration = G - force_trainee / m
        v += acceleration * dt
        x += v * dt
        t += dt

    if t >= t_max:
        raise ValueError("Le calcul n'a pas convergé (paramètres irréalistes ?).")

    if cx > 0 and a > 0:
        v_terminale = (2 * m * G / (RHO_AIR * cx * a)) ** 0.5
    else:
        v_terminale = float("inf")

    ecart_pourcent = (v_sans_frottement - v) / v_sans_frottement * 100

    return (
        f"— Sans frottement (référence théorique) —\n"
        f"Temps de chute : {t_sans_frottement:.3f} s\n"
        f"Vitesse d'impact : {v_sans_frottement:.3f} m/s\n\n"
        f"— Avec frottement de l'air —\n"
        f"Temps de chute : {t:.3f} s\n"
        f"Vitesse d'impact : {v:.3f} m/s\n"
        f"Vitesse terminale théorique : {v_terminale:.3f} m/s\n\n"
        f"Écart sur la vitesse d'impact : {ecart_pourcent:.1f} % plus lent qu'en théorie"
    )


def main():
    app = QApplication(sys.argv)
    fenetre = FenetreProgramme()
    fenetre.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
