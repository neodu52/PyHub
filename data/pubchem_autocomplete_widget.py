"""
data/pubchem_autocomplete_widget.py — Widget PARTAGÉ (PyQt, réutilisable)
=============================================================================
Un QLineEdit "barre de recherche" qui propose des suggestions de noms de
composés en direct (façon recherche Google), en s'appuyant sur
pubchem_utils.rechercher_suggestions().

Contrairement à pubchem_utils.py (délibérément sans PyQt, pour rester
testable indépendamment), ce module EST spécifique à PyQt : c'est un widget
prêt à l'emploi, à importer et instancier tel quel dans n'importe quel
programme du hub qui a besoin de faire chercher un composé à l'utilisateur.

Usage typique depuis un programme du hub :

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "data"))
    from pubchem_autocomplete_widget import ChampRechercheCompose

    champ = ChampRechercheCompose()
    champ.compose_choisi.connect(lambda nom: print("Choisi :", nom))
"""

from pathlib import Path
import sys

from PyQt5.QtCore import Qt, QTimer, QStringListModel, pyqtSignal
from PyQt5.QtWidgets import QLineEdit, QCompleter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pubchem_utils as pc  # noqa: E402

DELAI_DEBOUNCE_MS = 300      # attente après la dernière frappe avant d'interroger PubChem
LONGUEUR_MIN_RECHERCHE = 2    # nombre de caractères minimum avant de chercher


class ChampRechercheCompose(QLineEdit):
    """QLineEdit avec suggestions de composés en direct, façon barre de
    recherche. Émet `compose_choisi` (str) quand l'utilisateur sélectionne
    une suggestion (clic ou Entrée sur un élément de la liste déroulante)."""

    compose_choisi = pyqtSignal(str)

    def __init__(self, parent=None, placeholder="Rechercher un composé (ex: ace...)"):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)

        self._modele = QStringListModel([])
        self._completer = QCompleter(self._modele, self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self._completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.setCompleter(self._completer)
        self._completer.activated[str].connect(self.compose_choisi.emit)

        self._minuteur = QTimer(self)
        self._minuteur.setSingleShot(True)
        self._minuteur.setInterval(DELAI_DEBOUNCE_MS)
        self._minuteur.timeout.connect(self._rechercher_suggestions)
        self.textEdited.connect(self._programmer_recherche)

    def _programmer_recherche(self, texte):
        self._minuteur.stop()
        if len(texte.strip()) >= LONGUEUR_MIN_RECHERCHE:
            self._minuteur.start()

    def _rechercher_suggestions(self):
        texte = self.text().strip()
        suggestions = pc.rechercher_suggestions(texte, limite=10)
        self._modele.setStringList(suggestions)
        if suggestions:
            self._completer.complete()
