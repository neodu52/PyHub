"""
TEMPLATE — Nouveau programme pour le PyHub
=============================================
COMMENT UTILISER CE TEMPLATE :

1. Copiez ce fichier dans un nouveau dossier :
       categories/<Categorie>/<NomDuProgramme>/main.py
   (créez <Categorie> si elle n'existe pas encore : elle apparaîtra
   automatiquement comme un nouvel onglet dans le hub)

2. Modifiez les 3 zones marquées "MODIFIEZ ICI" :
   - CHAMPS / TITRE_PROGRAMME / DESCRIPTION : ce que l'utilisateur saisit
   - la fonction calculer() : votre logique de calcul

3. (Optionnel) Ajoutez un fichier hub_info.json à côté de main.py pour
   personnaliser le nom affiché sur le bouton du hub :
       {
         "nom_affiche": "Mon super calcul",
         "description": "Ce que fait ce programme, affiché en info-bulle."
       }

Ce fichier peut être lancé seul (python main.py) pour le tester,
ou automatiquement par le hub.
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QFormLayout, QLabel,
    QDoubleSpinBox, QPushButton, QTextEdit, QMessageBox
)

# ============================================================
# MODIFIEZ ICI : titre et description affichés en haut de la fenêtre
# ============================================================
TITRE_PROGRAMME = "Nom de mon programme"
DESCRIPTION = "Courte description de ce que fait ce programme."

# ============================================================
# MODIFIEZ ICI : décrivez vos champs d'entrée.
# Chaque champ est un tuple :
#   (nom_interne, label_affiché, valeur_par_défaut, min, max, unité)
# Le nom_interne est la clé que vous retrouverez dans le dict `valeurs`
# passé à la fonction calculer() plus bas.
# Ajoutez / retirez des lignes selon vos besoins : le formulaire et le
# reste de l'interface s'adaptent automatiquement.
# ============================================================
CHAMPS = [
    ("masse",   "Masse",                        1.0,  0.0, 1e6, "kg"),
    ("hauteur", "Hauteur de chute",             10.0,  0.0, 1e6, "m"),
    ("cx",      "Coefficient de traînée (Cx)",  0.47,  0.0, 5.0, ""),
]


class FenetreProgramme(QWidget):
    """Interface générique : un formulaire généré depuis CHAMPS,
    un bouton Calculer, une zone de résultat. Vous n'avez normalement
    pas besoin de modifier cette classe : tout se passe dans CHAMPS,
    TITRE_PROGRAMME, DESCRIPTION et calculer()."""

    def __init__(self):
        super().__init__()
        self.champs_widgets = {}
        self._construire_ui()

    def _construire_ui(self):
        self.setWindowTitle(TITRE_PROGRAMME)
        self.resize(480, 420)

        layout_principal = QVBoxLayout(self)

        titre = QLabel(TITRE_PROGRAMME)
        titre.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout_principal.addWidget(titre)

        if DESCRIPTION:
            desc = QLabel(DESCRIPTION)
            desc.setWordWrap(True)
            desc.setStyleSheet("color: #666; margin-bottom: 8px;")
            layout_principal.addWidget(desc)

        # --- formulaire généré automatiquement à partir de CHAMPS ---
        formulaire = QFormLayout()
        for nom, label, defaut, mini, maxi, unite in CHAMPS:
            spin = QDoubleSpinBox()
            spin.setDecimals(6)
            spin.setRange(mini, maxi)
            spin.setValue(defaut)
            spin.setSuffix(f" {unite}" if unite else "")
            self.champs_widgets[nom] = spin
            formulaire.addRow(label + " :", spin)
        layout_principal.addLayout(formulaire)

        bouton_calculer = QPushButton("Calculer")
        bouton_calculer.clicked.connect(self._on_calculer)
        layout_principal.addWidget(bouton_calculer)

        self.zone_resultat = QTextEdit()
        self.zone_resultat.setReadOnly(True)
        self.zone_resultat.setPlaceholderText("Les résultats s'afficheront ici...")
        layout_principal.addWidget(self.zone_resultat)

    def _valeurs(self):
        """Renvoie les valeurs saisies sous forme de dict {nom_interne: valeur}."""
        return {nom: widget.value() for nom, widget in self.champs_widgets.items()}

    def _on_calculer(self):
        valeurs = self._valeurs()
        try:
            resultat_texte = calculer(valeurs)
        except Exception as e:
            # Toute erreur levée dans calculer() (ValueError, etc.) est affichée
            # proprement à l'utilisateur plutôt que de faire planter le programme.
            QMessageBox.critical(self, "Erreur de calcul", str(e))
            return
        self.zone_resultat.setPlainText(resultat_texte)


# ============================================================
# MODIFIEZ ICI : toute votre logique de calcul.
# `valeurs` est un dict contenant les champs définis dans CHAMPS,
# ex : valeurs["masse"], valeurs["hauteur"], valeurs["cx"]
# Levez une ValueError(...) pour signaler une entrée invalide
# (elle sera affichée proprement dans une boîte de dialogue).
# Retournez une chaîne de caractères (peut contenir plusieurs lignes,
# avec \n) qui sera affichée dans la zone de résultat.
# ============================================================
def calculer(valeurs):
    masse = valeurs["masse"]
    hauteur = valeurs["hauteur"]
    cx = valeurs["cx"]

    # --- exemple de calcul à remplacer par le vôtre ---
    g = 9.81
    temps_chute_libre = (2 * hauteur / g) ** 0.5
    vitesse_impact = g * temps_chute_libre

    return (
        f"Temps de chute (sans frottement) : {temps_chute_libre:.3f} s\n"
        f"Vitesse d'impact : {vitesse_impact:.3f} m/s"
    )


def main():
    app = QApplication(sys.argv)
    fenetre = FenetreProgramme()
    fenetre.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
