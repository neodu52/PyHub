"""
CHIMIE — Visualiseur de molécules en 3D
====================================================================
Cherchez une molécule (barre de recherche PubChem, comme dans les autres
programmes de Chimie du hub) et affichez sa structure 3D : atomes colorés
selon la convention CPK, liaisons entre atomes, rotation/zoom à la souris.

La structure (coordonnées atomiques) est d'abord cherchée dans le cache
local (data/structures_3d_locale.json) ; si absente, elle est récupérée
depuis PubChem (conformère 3D si disponible, sinon 2D en repli), puis mise
en cache pour ne plus jamais avoir à la re-télécharger.

Rendu réalisé avec matplotlib 3D (déjà une dépendance du hub) : pas de
dépendance supplémentaire lourde (pas de RDKit, pas de moteur 3D dédié).

Dépendances supplémentaires : requests, matplotlib (déjà dans requirements.txt)
"""

import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QMessageBox
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (enregistre la projection '3d')

DOSSIER_HUB = Path(__file__).resolve().parents[3]  # .../PyHub
sys.path.insert(0, str(DOSSIER_HUB / "data"))
import pubchem_utils as pc  # noqa: E402
from sdf_utils import parser_sdf  # noqa: E402
from pubchem_autocomplete_widget import ChampRechercheCompose  # noqa: E402

TITRE_PROGRAMME = "Visualiseur de molécules en 3D"
DESCRIPTION = (
    "Cherchez une molécule (ex: acetone, aspirin, caffeine...) et affichez sa "
    "structure 3D. Clic-glisser pour tourner, molette pour zoomer."
)
EXEMPLE_MOLECULE = "acetone"

# Couleurs CPK usuelles (convention Jmol/RasMol) pour les éléments les plus
# fréquents dans les petites molécules organiques/inorganiques courantes.
COULEURS_CPK = {
    "H": "#FFFFFF", "C": "#404040", "N": "#3050F8", "O": "#FF0D0D",
    "F": "#90E050", "Cl": "#1FF01F", "Br": "#A62929", "I": "#940094",
    "S": "#FFFF30", "P": "#FF8000", "Na": "#AB5CF2", "K": "#8F40D4",
    "Ca": "#3DFF00", "Mg": "#8AFF00", "Fe": "#E06633", "Zn": "#7D80B0",
    "Si": "#F0C8A0", "B": "#FFB5B5", "Al": "#BFA6A6", "Li": "#CC80FF",
}
COULEUR_DEFAUT = "#FF1493"  # élément non répertorié : rose vif (bien visible)

# Rayons covalents approximatifs (Angström) — juste pour la taille relative
# des sphères affichées, pas une donnée physique de précision.
RAYONS_COVALENTS = {
    "H": 0.31, "C": 0.76, "N": 0.71, "O": 0.66, "F": 0.57,
    "Cl": 1.02, "Br": 1.20, "I": 1.39, "S": 1.05, "P": 1.07,
    "Na": 1.66, "K": 2.03, "Ca": 1.76, "Mg": 1.41, "Fe": 1.32,
    "Zn": 1.22, "Si": 1.11, "B": 0.84, "Al": 1.21, "Li": 1.28,
}
RAYON_DEFAUT = 0.75
ECHELLE_TAILLE_SPHERE = 500  # facteur purement esthétique (points^2 par Å de rayon)


class FenetreProgramme(QWidget):
    def __init__(self):
        super().__init__()
        self._construire_ui()

    def _construire_ui(self):
        self.setWindowTitle(TITRE_PROGRAMME)
        self.resize(760, 700)

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
        ligne_recherche.addWidget(QLabel("🔍 Molécule :"))
        self.champ_recherche = ChampRechercheCompose(
            placeholder=f"ex: {EXEMPLE_MOLECULE}, aspirin, caffeine..."
        )
        self.champ_recherche.setText(EXEMPLE_MOLECULE)
        self.champ_recherche.compose_choisi.connect(self._on_compose_choisi)
        self.champ_recherche.returnPressed.connect(self._on_afficher)
        ligne_recherche.addWidget(self.champ_recherche, stretch=1)
        self.bouton_afficher = QPushButton("Afficher")
        self.bouton_afficher.clicked.connect(self._on_afficher)
        ligne_recherche.addWidget(self.bouton_afficher)
        layout.addLayout(ligne_recherche)

        self.label_statut = QLabel("")
        self.label_statut.setWordWrap(True)
        self.label_statut.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.label_statut)

        # --- zone 3D (matplotlib) ---
        self.figure = Figure(figsize=(6, 6))
        self.axes = self.figure.add_subplot(111, projection="3d")
        self.canvas = FigureCanvas(self.figure)
        self.barre_outils = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.barre_outils)
        layout.addWidget(self.canvas, stretch=1)

        # affiche l'exemple par défaut au démarrage (depuis le cache local, sans réseau)
        self._on_afficher()

    # ------------------------------------------------------------------
    def _on_compose_choisi(self, nom):
        self.champ_recherche.setText(nom)
        self._charger_et_afficher(nom)

    def _on_afficher(self):
        nom = self.champ_recherche.text().strip()
        if nom:
            self._charger_et_afficher(nom)

    def _charger_et_afficher(self, nom):
        self.setCursor(QCursor(Qt.WaitCursor))
        self.bouton_afficher.setEnabled(False)
        QApplication.processEvents()

        try:
            proprietes = pc.obtenir_proprietes(nom)
            cid = proprietes.get("cid_pubchem")
            if not cid:
                raise pc.ComposeIntrouvable(
                    f"« {nom} » n'a pas d'identifiant PubChem (CID) connu, "
                    "impossible de récupérer sa structure 3D."
                )
            sdf, dimension, source_structure = pc.obtenir_structure_3d(cid)
            atomes, liaisons = parser_sdf(sdf)
        except (pc.ComposeIntrouvable, ValueError) as e:
            self.setCursor(QCursor(Qt.ArrowCursor))
            self.bouton_afficher.setEnabled(True)
            QMessageBox.warning(self, "Structure introuvable", str(e))
            return

        self.setCursor(QCursor(Qt.ArrowCursor))
        self.bouton_afficher.setEnabled(True)

        self._dessiner_molecule(atomes, liaisons)

        note_dimension = (
            "structure 3D" if dimension == "3d"
            else "⚠️ pas de conformère 3D disponible — structure 2D affichée à plat"
        )
        self.label_statut.setText(
            f"{proprietes['nom_pubchem'] or nom} ({proprietes['formule']}) — "
            f"{len(atomes)} atomes, {len(liaisons)} liaisons — {note_dimension} "
            f"[composé: {proprietes['source']}, structure: {source_structure}]"
        )

    def _dessiner_molecule(self, atomes, liaisons):
        self.axes.clear()
        self.axes.set_axis_off()

        if not atomes:
            self.canvas.draw()
            return

        xs = [a.x for a in atomes]
        ys = [a.y for a in atomes]
        zs = [a.z for a in atomes]

        for liaison in liaisons:
            if liaison.i1 >= len(atomes) or liaison.i2 >= len(atomes):
                continue
            a1, a2 = atomes[liaison.i1], atomes[liaison.i2]
            milieu = ((a1.x + a2.x) / 2, (a1.y + a2.y) / 2, (a1.z + a2.z) / 2)
            epaisseur = 2.0 + (max(liaison.ordre, 1) - 1) * 1.5
            couleur1 = COULEURS_CPK.get(a1.element, COULEUR_DEFAUT)
            couleur2 = COULEURS_CPK.get(a2.element, COULEUR_DEFAUT)
            self.axes.plot(
                [a1.x, milieu[0]], [a1.y, milieu[1]], [a1.z, milieu[2]],
                color=couleur1, linewidth=epaisseur
            )
            self.axes.plot(
                [milieu[0], a2.x], [milieu[1], a2.y], [milieu[2], a2.z],
                color=couleur2, linewidth=epaisseur
            )

        couleurs = [COULEURS_CPK.get(a.element, COULEUR_DEFAUT) for a in atomes]
        tailles = [RAYONS_COVALENTS.get(a.element, RAYON_DEFAUT) * ECHELLE_TAILLE_SPHERE for a in atomes]
        self.axes.scatter(
            xs, ys, zs, s=tailles, c=couleurs,
            edgecolors="black", linewidths=0.6, depthshade=True
        )

        for a in atomes:
            self.axes.text(a.x, a.y, a.z, a.element, fontsize=8, ha="center", va="center")

        # repère cubique centré, pour une échelle identique sur les 3 axes
        # (sinon la molécule apparaît déformée)
        portee = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 1.0) / 2 + 0.6
        cx, cy, cz = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, (max(zs) + min(zs)) / 2
        self.axes.set_xlim(cx - portee, cx + portee)
        self.axes.set_ylim(cy - portee, cy + portee)
        self.axes.set_zlim(cz - portee, cz + portee)
        try:
            self.axes.set_box_aspect((1, 1, 1))
        except AttributeError:
            pass  # versions de matplotlib antérieures à 3.3, sans set_box_aspect

        self.canvas.draw()


def main():
    app = QApplication(sys.argv)
    fenetre = FenetreProgramme()
    fenetre.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
