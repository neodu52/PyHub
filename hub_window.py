"""
Fenêtre principale du PyHub.

Logique :
- Le dossier "categories/" (à côté de ce fichier) contient un sous-dossier
  par catégorie (Physique, Chimie, Ingenierie, Aerospatiale, ou toute autre
  catégorie que vous créez).
- Chaque catégorie contient un sous-dossier par programme.
- Chaque dossier de programme contient un fichier main.py (par défaut),
  et éventuellement un fichier hub_info.json pour personnaliser l'affichage.
- Cliquer sur le bouton d'un programme le lance dans un processus Python
  séparé (subprocess), pour que chaque programme ait sa propre fenêtre
  et son propre cycle de vie, indépendant du hub.

Ajouter un nouveau programme = ajouter un dossier + un main.py. Rien à
modifier dans ce fichier : cliquez sur "Actualiser" (ou appuyez sur F5)
pour le voir apparaître.
"""

import os
import sys
import json
import platform
import subprocess
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QGridLayout, QPushButton,
    QVBoxLayout, QLabel, QScrollArea, QMessageBox, QToolBar, QAction,
    QSizePolicy
)

# Dossier contenant les catégories, situé à côté de ce fichier
DOSSIER_CATEGORIES = Path(__file__).resolve().parent / "categories"

# Icônes facultatives affichées devant le nom de chaque catégorie
# (vous pouvez en ajouter d'autres, ou laisser le hub utiliser 📁 par défaut)
ICONES_CATEGORIES = {
    "physique": "⚛️",
    "chimie": "🧪",
    "ingenierie": "⚙️",
    "ingénierie": "⚙️",
    "aerospatiale": "🚀",
    "aérospatiale": "🚀",
    "informatique": "💻",
    "mathematiques": "📐",
    "mathématiques": "📐",
}

NOM_FICHIER_INFO = "hub_info.json"          # métadonnées optionnelles d'un programme
NOM_FICHIER_ENTREE_DEFAUT = "main.py"        # fichier lancé par défaut
NB_COLONNES_GRILLE = 3


class HubWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyHub — Mes programmes scientifiques")
        self.resize(950, 650)

        self._appliquer_theme()
        self._creer_barre_outils()

        self.onglets = QTabWidget()
        self.setCentralWidget(self.onglets)

        self.actualiser()

    # ------------------------------------------------------------------
    # Apparence
    # ------------------------------------------------------------------
    def _appliquer_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #202124; }
            QTabWidget::pane { border: none; background-color: #202124; }
            QTabBar::tab {
                background: #2b2c2e;
                color: #ddd;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected { background: #3a3b3d; color: #fff; }
            QToolBar { background: #2b2c2e; border: none; spacing: 8px; padding: 4px; }
            QLabel { color: #ddd; }
        """)

    def _creer_barre_outils(self):
        barre = QToolBar("Actions")
        barre.setMovable(False)
        self.addToolBar(barre)

        action_actualiser = QAction("🔄 Actualiser (F5)", self)
        action_actualiser.setShortcut("F5")
        action_actualiser.triggered.connect(self.actualiser)
        barre.addAction(action_actualiser)

        action_ouvrir_dossier = QAction("📂 Ouvrir le dossier categories/", self)
        action_ouvrir_dossier.triggered.connect(self._ouvrir_dossier_categories)
        barre.addAction(action_ouvrir_dossier)

    # ------------------------------------------------------------------
    # Scan et construction de l'interface
    # ------------------------------------------------------------------
    def actualiser(self):
        """Rescanne le dossier categories/ et reconstruit tous les onglets."""
        self.onglets.clear()

        if not DOSSIER_CATEGORIES.exists():
            DOSSIER_CATEGORIES.mkdir(parents=True, exist_ok=True)

        dossiers_categories = sorted(
            (d for d in DOSSIER_CATEGORIES.iterdir() if d.is_dir()),
            key=lambda d: d.name.lower()
        )

        if not dossiers_categories:
            self.onglets.addTab(
                self._page_message(
                    "Aucune catégorie trouvée.\n\n"
                    f"Créez un dossier ici :\n{DOSSIER_CATEGORIES}"
                ),
                "Vide"
            )
            return

        for dossier_categorie in dossiers_categories:
            self.onglets.addTab(
                self._construire_page_categorie(dossier_categorie),
                self._label_categorie(dossier_categorie.name)
            )

    def _label_categorie(self, nom_dossier):
        icone = ICONES_CATEGORIES.get(nom_dossier.lower(), "📁")
        return f"{icone}  {nom_dossier}"

    def _page_message(self, message):
        page = QWidget()
        layout = QVBoxLayout(page)
        label = QLabel(message)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #888; font-size: 13px;")
        layout.addWidget(label)
        return page

    def _construire_page_categorie(self, dossier_categorie):
        dossiers_programmes = sorted(
            (d for d in dossier_categorie.iterdir() if d.is_dir()),
            key=lambda d: d.name.lower()
        )

        if not dossiers_programmes:
            zone = QScrollArea()
            zone.setWidgetResizable(True)
            zone.setWidget(self._page_message(
                f"Aucun programme dans « {dossier_categorie.name} ».\n\n"
                f"Ajoutez un dossier contenant un fichier {NOM_FICHIER_ENTREE_DEFAUT} ici :\n"
                f"{dossier_categorie}"
            ))
            return zone

        conteneur = QWidget()
        grille = QGridLayout(conteneur)
        grille.setSpacing(14)
        grille.setContentsMargins(16, 16, 16, 16)
        grille.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        for index, dossier_programme in enumerate(dossiers_programmes):
            bouton = self._construire_bouton_programme(dossier_programme)
            ligne, colonne = divmod(index, NB_COLONNES_GRILLE)
            grille.addWidget(bouton, ligne, colonne)

        zone = QScrollArea()
        zone.setWidgetResizable(True)
        zone.setWidget(conteneur)
        return zone

    def _construire_bouton_programme(self, dossier_programme):
        info = self._lire_info(dossier_programme)
        nom_affiche = info.get("nom_affiche", dossier_programme.name)
        description = info.get("description", "")

        bouton = QPushButton(nom_affiche)
        bouton.setMinimumSize(220, 90)
        bouton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bouton.setFont(QFont("Segoe UI", 10))
        bouton.setCursor(Qt.PointingHandCursor)
        bouton.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 12px;
                border-radius: 10px;
                border: 1px solid #444;
                background-color: #2b2b2b;
                color: #eee;
            }
            QPushButton:hover {
                background-color: #34363a;
                border: 1px solid #6aa9ff;
            }
            QPushButton:pressed { background-color: #1f1f1f; }
        """)
        if description:
            bouton.setToolTip(description)

        bouton.clicked.connect(
            lambda _checked=False, d=dossier_programme, i=info: self._lancer_programme(d, i)
        )
        return bouton

    def _lire_info(self, dossier_programme):
        chemin_info = dossier_programme / NOM_FICHIER_INFO
        if chemin_info.exists():
            try:
                with open(chemin_info, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    # ------------------------------------------------------------------
    # Exécution des programmes
    # ------------------------------------------------------------------
    def _lancer_programme(self, dossier_programme, info):
        nom_fichier = info.get("fichier", NOM_FICHIER_ENTREE_DEFAUT)
        chemin_script = dossier_programme / nom_fichier

        if not chemin_script.exists():
            fichiers_py = sorted(dossier_programme.glob("*.py"))
            if fichiers_py:
                chemin_script = fichiers_py[0]
            else:
                QMessageBox.warning(
                    self, "Programme introuvable",
                    f"Aucun fichier {nom_fichier} (ni aucun .py) trouvé dans :\n{dossier_programme}"
                )
                return

        try:
            subprocess.Popen(
                [sys.executable, str(chemin_script)],
                cwd=str(dossier_programme),
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Erreur de lancement",
                f"Impossible de lancer {chemin_script.name} :\n{e}"
            )

    def _ouvrir_dossier_categories(self):
        chemin = str(DOSSIER_CATEGORIES)
        systeme = platform.system()
        try:
            if systeme == "Windows":
                os.startfile(chemin)  # type: ignore[attr-defined]
            elif systeme == "Darwin":
                subprocess.Popen(["open", chemin])
            else:
                subprocess.Popen(["xdg-open", chemin])
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Impossible d'ouvrir le dossier :\n{e}")
