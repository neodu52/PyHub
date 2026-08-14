"""
Fenêtre principale du PyHub.

Logique :
- Le dossier "categories/" (à côté de ce fichier) contient un sous-dossier
  par catégorie (Physique, Chimie, Ingenierie, Aerospatiale, ou toute autre
  catégorie que vous créez).
- Chaque catégorie contient un sous-dossier par programme.
- Chaque dossier de programme contient un fichier main.py (par défaut) OU
  un exécutable natif (.exe, script .sh, binaire compilé en C++...), et
  éventuellement un fichier hub_info.json pour personnaliser l'affichage.
- Cliquer sur le bouton d'un programme le lance dans un processus séparé
  (subprocess), pour que chaque programme ait sa propre fenêtre et son
  propre cycle de vie, indépendant du hub.

Ajouter un nouveau programme = ajouter un dossier + un main.py (ou un
exécutable). Rien à modifier dans ce fichier : cliquez sur "Actualiser"
(ou appuyez sur F5) pour le voir apparaître.

Format de hub_info.json (toutes les clés sont optionnelles) :
    {
        "nom_affiche": "Nom affiché sur le bouton",
        "description": "Info-bulle au survol du bouton",
        "fichier": "main.py",           // ou "simulation.exe", "sim.sh"...
        "type": "python",                // "python" (défaut) ou "executable"
        "arguments": ["--param", "5"]    // arguments passés au programme
    }

Détection automatique du type si "type" n'est pas précisé : un fichier
.py est lancé via l'interpréteur Python ; un fichier .exe/.bat/.sh/.bin/
.app/.out (ou, sur Linux/Mac, tout fichier avec le bit exécutable) est
lancé directement comme un programme natif.
"""

import os
import sys
import json
import platform
import subprocess
from pathlib import Path

from PyQt5.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QFrame, QLayout,
    QVBoxLayout, QLabel, QScrollArea, QMessageBox, QToolBar, QAction
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
LARGEUR_CARTE = 220                          # largeur fixe d'une carte de programme, en pixels

# Extensions reconnues comme "exécutable natif" (lancées directement, sans
# passer par l'interpréteur Python) lors de la détection automatique.
EXTENSIONS_EXECUTABLES = {".exe", ".bat", ".cmd", ".sh", ".bin", ".app", ".out"}


class DispositionFluide(QLayout):
    """Disposition qui aligne les widgets enfants de gauche à droite et les
    fait automatiquement passer à la ligne suivante dès que la largeur
    disponible est dépassée — comme des éléments de page web qui s'enroulent
    (CSS flex-wrap). Remplace une grille à nombre de colonnes fixe, qui ne
    s'adapte pas quand la fenêtre est redimensionnée."""

    def __init__(self, parent=None, marge=0, espacement=14):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(marge, marge, marge, marge)
        self.setSpacing(espacement)
        self._items = []

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, largeur):
        return self._disposer(QRect(0, 0, largeur, 0), test_seulement=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._disposer(rect, test_seulement=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        taille = QSize()
        for item in self._items:
            taille = taille.expandedTo(item.minimumSize())
        marges = self.contentsMargins()
        taille += QSize(marges.left() + marges.right(), marges.top() + marges.bottom())
        return taille

    def _disposer(self, rect, test_seulement):
        x, y = rect.x(), rect.y()
        hauteur_ligne = 0
        espacement = self.spacing()

        for item in self._items:
            largeur_item = item.sizeHint().width()
            hauteur_item = item.sizeHint().height()

            x_suivant = x + largeur_item + espacement
            if x_suivant - espacement > rect.right() and hauteur_ligne > 0:
                x = rect.x()
                y = y + hauteur_ligne + espacement
                x_suivant = x + largeur_item + espacement
                hauteur_ligne = 0

            if not test_seulement:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = x_suivant
            hauteur_ligne = max(hauteur_ligne, hauteur_item)

        return y + hauteur_ligne - rect.y()


class CarteProgramme(QFrame):
    """Carte cliquable représentant un programme : largeur fixe, hauteur
    qui s'adapte au texte (le nom du programme s'enroule sur plusieurs
    lignes plutôt que d'être coupé)."""

    clique = pyqtSignal()

    def __init__(self, texte, info_bulle=""):
        super().__init__()
        self.setFixedWidth(LARGEUR_CARTE)
        self.setMinimumHeight(70)
        self.setCursor(Qt.PointingHandCursor)
        if info_bulle:
            self.setToolTip(info_bulle)

        self.setStyleSheet("""
            CarteProgramme {
                background-color: #2b2b2b;
                border: 1px solid #444;
                border-radius: 10px;
            }
            CarteProgramme:hover {
                background-color: #34363a;
                border: 1px solid #6aa9ff;
            }
        """)

        agencement = QVBoxLayout(self)
        agencement.setContentsMargins(14, 12, 14, 12)

        etiquette = QLabel(texte)
        etiquette.setWordWrap(True)
        etiquette.setFont(QFont("Segoe UI", 10))
        etiquette.setStyleSheet("color: #eee; background: transparent; border: none;")
        etiquette.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        agencement.addWidget(etiquette)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clique.emit()
        super().mousePressEvent(event)


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
        disposition = DispositionFluide(conteneur, marge=16, espacement=14)

        for dossier_programme in dossiers_programmes:
            carte = self._construire_carte_programme(dossier_programme)
            disposition.addWidget(carte)

        zone = QScrollArea()
        zone.setWidgetResizable(True)
        zone.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        zone.setWidget(conteneur)
        return zone

    def _construire_carte_programme(self, dossier_programme):
        info = self._lire_info(dossier_programme)
        nom_affiche = info.get("nom_affiche", dossier_programme.name)
        description = info.get("description", "")

        carte = CarteProgramme(nom_affiche, info_bulle=description)
        carte.clique.connect(
            lambda d=dossier_programme, i=info: self._lancer_programme(d, i)
        )
        return carte

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
    def _resoudre_fichier_a_lancer(self, dossier_programme, info):
        """Détermine quel fichier lancer : le champ "fichier" de hub_info.json
        s'il existe, sinon le premier .py trouvé, sinon le premier exécutable
        connu (.exe, .sh, .bat...) trouvé dans le dossier."""
        nom_fichier = info.get("fichier", NOM_FICHIER_ENTREE_DEFAUT)
        chemin = dossier_programme / nom_fichier
        if chemin.exists():
            return chemin

        fichiers_py = sorted(dossier_programme.glob("*.py"))
        if fichiers_py:
            return fichiers_py[0]

        for extension in EXTENSIONS_EXECUTABLES:
            fichiers_exe = sorted(dossier_programme.glob(f"*{extension}"))
            if fichiers_exe:
                return fichiers_exe[0]

        return None

    def _est_executable(self, chemin, info):
        """Décide si `chemin` doit être lancé directement (exécutable natif :
        .exe, C++ compilé, script shell...) ou via l'interpréteur Python."""
        type_declare = str(info.get("type", "")).strip().lower()
        if type_declare == "executable":
            return True
        if type_declare == "python":
            return False

        # Pas de type déclaré explicitement dans hub_info.json : on déduit
        # à partir de l'extension, puis (sur Linux/Mac) du bit exécutable.
        if chemin.suffix.lower() == ".py":
            return False
        if chemin.suffix.lower() in EXTENSIONS_EXECUTABLES:
            return True
        if platform.system() != "Windows" and os.access(chemin, os.X_OK):
            return True
        return False

    def _lancer_programme(self, dossier_programme, info):
        chemin = self._resoudre_fichier_a_lancer(dossier_programme, info)
        if chemin is None:
            QMessageBox.warning(
                self, "Programme introuvable",
                f"Aucun script Python ni exécutable (.exe, .sh...) trouvé dans :\n{dossier_programme}"
            )
            return

        arguments = info.get("arguments", [])
        if not isinstance(arguments, list):
            arguments = []
        arguments = [str(a) for a in arguments]

        if self._est_executable(chemin, info):
            commande = [str(chemin)] + arguments
        else:
            commande = [sys.executable, str(chemin)] + arguments

        try:
            subprocess.Popen(commande, cwd=str(dossier_programme))
        except PermissionError:
            QMessageBox.critical(
                self, "Permission refusée",
                f"Impossible d'exécuter {chemin.name} : permission refusée.\n\n"
                f"Sur Linux/Mac, rendez le fichier exécutable avec :\n"
                f"chmod +x \"{chemin}\""
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Erreur de lancement",
                f"Impossible de lancer {chemin.name} :\n{e}"
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
