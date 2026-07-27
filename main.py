"""
PyHub — Point d'entrée
=======================
Lancez ce fichier pour ouvrir le hub :

    python main.py

Le hub scanne automatiquement le dossier "categories/" et affiche
un onglet par catégorie, avec un bouton par programme trouvé.
"""

import sys
from PyQt5.QtWidgets import QApplication

from hub_window import HubWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    fenetre = HubWindow()
    fenetre.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
