"""
PHYSIQUE — Résolveur d'équations symbolique (LaTeX <-> clavier)
====================================================================
- Saisissez une équation en écriture "clavier" (ex: E=(1/2)*m*v^2) ou en
  LaTeX (ex: E=\\frac{1}{2}mv^{2}, avec ou sans les antislashs) et convertissez
  d'une forme à l'autre.
- Isolez (résolvez) l'équation pour n'importe laquelle de ses variables.
- Donnez une valeur numérique à toutes les autres variables pour calculer
  la variable isolée.

Dépendance supplémentaire : sympy (pip install sympy), et matplotlib
(déjà utilisé ailleurs dans le hub) pour l'aperçu typographié de l'équation.
"""

import re
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QDoubleSpinBox, QMessageBox,
    QScrollArea
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from sympy import Eq, Symbol, solve, latex, log
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, convert_xor
)

TITRE_PROGRAMME = "Résolveur d'équations (LaTeX <-> clavier)"
DESCRIPTION = (
    "Tapez une équation en clavier ou en LaTeX, convertissez d'une forme à "
    "l'autre, isolez n'importe quelle variable, puis calculez sa valeur."
)
EXEMPLE_CLAVIER = "E=(1/2)*m*v^2"

TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application, convert_xor)

# Noms gardés avec leur sens mathématique sympy ; tout le reste dans une
# équation est forcé en simple variable (évite par exemple que "E" soit
# confondu avec le nombre d'Euler, ou "I" avec l'unité imaginaire — E et I
# sont des lettres extrêmement courantes en physique : énergie, courant...).
FONCTIONS_GARDEES = {
    "pi", "sin", "cos", "tan", "sqrt", "exp", "log",
    "asin", "acos", "atan", "sinh", "cosh", "tanh", "Abs",
}

GRECQUES = {
    "alpha": "alpha", "beta": "beta", "gamma": "gamma", "delta": "delta",
    "epsilon": "epsilon", "theta": "theta", "lambda": "lam", "mu": "mu",
    "nu": "nu", "sigma": "sigma", "phi": "phi", "omega": "omega", "pi": "pi",
    "Delta": "Delta", "Omega": "Omega", "Sigma": "Sigma", "Gamma": "Gamma",
}


# ============================================================
# Conversion LaTeX -> clavier (parenthèses/exposants/indices/fractions)
# Prend en charge \frac, \sqrt, \cdot, \times, ^{}, _{}, quelques grecques,
# avec ou sans l'antislash (E=frac{1}{2}... est accepté comme E=\frac{1}{2}...)
# ============================================================
def _trouver_groupe(texte, i):
    """i pointe sur '{' ; renvoie (contenu, index apres la '}' correspondante)."""
    profondeur, debut, j = 0, i + 1, i
    while j < len(texte):
        if texte[j] == "{":
            profondeur += 1
        elif texte[j] == "}":
            profondeur -= 1
            if profondeur == 0:
                return texte[debut:j], j + 1
        j += 1
    raise ValueError("Accolade non fermée dans l'expression LaTeX.")


def convertir_latex_vers_clavier(texte):
    texte = texte.strip()
    texte = re.sub(r"\\left|\\right", "", texte)
    texte = re.sub(r"\\,|\\;|\\!", " ", texte)

    resultat = []
    i, n = 0, len(texte)
    while i < n:
        c = texte[i]

        if re.match(r"\\?frac\s*\{", texte[i:]):
            i += re.match(r"\\?frac\s*", texte[i:]).end()
            if i >= n or texte[i] != "{":
                raise ValueError("« frac » doit être suivi de deux groupes {...}{...}.")
            num, i = _trouver_groupe(texte, i)
            while i < n and texte[i] == " ":
                i += 1
            if i >= n or texte[i] != "{":
                raise ValueError("« frac » doit être suivi de deux groupes {...}{...}.")
            den, i = _trouver_groupe(texte, i)
            resultat.append(
                f"(({convertir_latex_vers_clavier(num)})/({convertir_latex_vers_clavier(den)}))"
            )
            continue

        if re.match(r"\\?sqrt\s*[\{\[]", texte[i:]):
            i += re.match(r"\\?sqrt\s*", texte[i:]).end()
            indice = None
            if i < n and texte[i] == "[":
                fin = texte.index("]", i)
                indice = texte[i + 1:fin]
                i = fin + 1
            while i < n and texte[i] == " ":
                i += 1
            if i >= n or texte[i] != "{":
                raise ValueError("« sqrt » doit être suivi d'un groupe {...}.")
            contenu, i = _trouver_groupe(texte, i)
            conv = convertir_latex_vers_clavier(contenu)
            resultat.append(f"(({conv})**(1/({indice})))" if indice else f"sqrt({conv})")
            continue

        if re.match(r"\\?cdot\b", texte[i:]):
            resultat.append("*")
            i += re.match(r"\\?cdot\b", texte[i:]).end()
            continue
        if re.match(r"\\?times\b", texte[i:]):
            resultat.append("*")
            i += re.match(r"\\?times\b", texte[i:]).end()
            continue

        m_grec = re.match(r"\\([A-Za-z]+)", texte[i:])
        if m_grec:
            nom = m_grec.group(1)
            resultat.append(GRECQUES.get(nom, ""))
            i += m_grec.end()
            continue

        if c == "^":
            i += 1
            while i < n and texte[i] == " ":
                i += 1
            if i < n and texte[i] == "{":
                exposant, i = _trouver_groupe(texte, i)
                resultat.append(f"**({convertir_latex_vers_clavier(exposant)})")
            elif i < n:
                resultat.append(f"**({texte[i]})")
                i += 1
            continue

        if c == "_":
            i += 1
            while i < n and texte[i] == " ":
                i += 1
            if i < n and texte[i] == "{":
                sub, i = _trouver_groupe(texte, i)
                resultat.append(f"_{sub}")
            elif i < n:
                resultat.append(f"_{texte[i]}")
                i += 1
            continue

        if c == "{":
            contenu, i = _trouver_groupe(texte, i)
            resultat.append(f"({convertir_latex_vers_clavier(contenu)})")
            continue
        if c == "}":
            i += 1
            continue

        resultat.append(c)
        i += 1

    return "".join(resultat)


# ============================================================
# Parsing "clavier" -> sympy, isolement, mise en forme
# ============================================================
def construire_dictionnaire_symboles(texte):
    """Force chaque identifiant de l'équation à être un symbole ordinaire,
    sauf les quelques noms de FONCTIONS_GARDEES (pi, sqrt, sin...)."""
    noms = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", texte))
    dico = {nom: Symbol(nom) for nom in noms if nom not in FONCTIONS_GARDEES}
    if "ln" in noms:
        dico["ln"] = log
    return dico


def parser_expression_clavier(texte):
    texte = texte.strip()
    if not texte:
        raise ValueError("Expression vide.")
    return parse_expr(
        texte, transformations=TRANSFORMATIONS,
        local_dict=construire_dictionnaire_symboles(texte), evaluate=True
    )


def _decouper_equation(texte):
    if "=" not in texte:
        raise ValueError(
            "L'équation doit contenir un signe '=' séparant les deux membres.\n"
            f"Exemple : {EXEMPLE_CLAVIER}"
        )
    gauche, droite = texte.split("=", 1)
    if not gauche.strip() or not droite.strip():
        raise ValueError("Les deux côtés de l'équation doivent être non vides.")
    return gauche, droite


def analyser_equation_clavier(texte):
    gauche, droite = _decouper_equation(texte)
    return Eq(parser_expression_clavier(gauche), parser_expression_clavier(droite))


def analyser_equation_latex(texte):
    gauche, droite = _decouper_equation(texte)
    clavier_gauche = convertir_latex_vers_clavier(gauche)
    clavier_droite = convertir_latex_vers_clavier(droite)
    return Eq(parser_expression_clavier(clavier_gauche), parser_expression_clavier(clavier_droite))


def equation_vers_latex(equation):
    return f"{latex(equation.lhs)} = {latex(equation.rhs)}"


def equation_vers_clavier(equation):
    def cote(e):
        return str(e).replace("**", "^")
    return f"{cote(equation.lhs)} = {cote(equation.rhs)}"


def isoler_variable(equation, variable):
    solutions = solve(equation, variable)
    if not solutions:
        raise ValueError(
            f"Aucune solution trouvée pour « {variable} » "
            "(l'équation ne dépend peut-être pas de cette variable, ou est trop complexe)."
        )
    return solutions


def evaluer_numeriquement(solution, valeurs):
    substitution = {Symbol(nom): val for nom, val in valeurs.items()}
    return solution.subs(substitution).evalf()


def vider_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        else:
            sous_layout = item.layout()
            if sous_layout is not None:
                vider_layout(sous_layout)


class FenetreProgramme(QWidget):
    def __init__(self):
        super().__init__()
        self.equation = None
        self.solutions = []
        self.spinboxes_valeurs = {}
        self._construire_ui()
        self._on_clavier_vers_latex()

    def _construire_ui(self):
        self.setWindowTitle(TITRE_PROGRAMME)
        self.resize(720, 700)

        layout = QVBoxLayout(self)

        titre = QLabel(TITRE_PROGRAMME)
        titre.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(titre)

        desc = QLabel(DESCRIPTION)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)

        # --- forme clavier ---
        ligne_clavier = QHBoxLayout()
        ligne_clavier.addWidget(QLabel("Clavier :"))
        self.champ_clavier = QLineEdit(EXEMPLE_CLAVIER)
        ligne_clavier.addWidget(self.champ_clavier, stretch=1)
        bouton_vers_latex = QPushButton("Clavier → LaTeX")
        bouton_vers_latex.clicked.connect(self._on_clavier_vers_latex)
        ligne_clavier.addWidget(bouton_vers_latex)
        layout.addLayout(ligne_clavier)

        # --- forme LaTeX ---
        ligne_latex = QHBoxLayout()
        ligne_latex.addWidget(QLabel("LaTeX :"))
        self.champ_latex = QLineEdit()
        ligne_latex.addWidget(self.champ_latex, stretch=1)
        bouton_vers_clavier = QPushButton("LaTeX → Clavier")
        bouton_vers_clavier.clicked.connect(self._on_latex_vers_clavier)
        ligne_latex.addWidget(bouton_vers_clavier)
        layout.addLayout(ligne_latex)

        # --- aperçu typographié ---
        self.figure = Figure(figsize=(6, 1.2))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFixedHeight(90)
        layout.addWidget(self.canvas)

        # --- isolement de variable ---
        ligne_isoler = QHBoxLayout()
        ligne_isoler.addWidget(QLabel("Isoler :"))
        self.combo_variable = QComboBox()
        ligne_isoler.addWidget(self.combo_variable, stretch=1)
        bouton_isoler = QPushButton("Isoler cette variable")
        bouton_isoler.clicked.connect(self._on_isoler)
        ligne_isoler.addWidget(bouton_isoler)
        layout.addLayout(ligne_isoler)

        self.label_solutions = QLabel("")
        self.label_solutions.setWordWrap(True)
        self.label_solutions.setStyleSheet("font-family: monospace;")
        self.label_solutions.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.label_solutions.setCursor(QCursor(Qt.IBeamCursor))
        layout.addWidget(self.label_solutions)

        # --- zone dynamique de saisie des valeurs numériques ---
        layout.addWidget(QLabel("Valeurs numériques des autres variables :"))
        self.zone_valeurs_widget = QWidget()
        self.layout_valeurs = QFormLayout(self.zone_valeurs_widget)
        zone_defilement = QScrollArea()
        zone_defilement.setWidgetResizable(True)
        zone_defilement.setWidget(self.zone_valeurs_widget)
        zone_defilement.setMaximumHeight(180)
        layout.addWidget(zone_defilement)

        self.bouton_calculer = QPushButton("Calculer")
        self.bouton_calculer.clicked.connect(self._on_calculer)
        self.bouton_calculer.setEnabled(False)
        layout.addWidget(self.bouton_calculer)

        self.label_resultat = QLabel("")
        self.label_resultat.setWordWrap(True)
        self.label_resultat.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.label_resultat.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.label_resultat.setCursor(QCursor(Qt.IBeamCursor))
        layout.addWidget(self.label_resultat)

    # ------------------------------------------------------------------
    def _mettre_a_jour_apercu(self, texte_latex):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.axis("off")
        try:
            ax.text(0.5, 0.5, f"${texte_latex}$", fontsize=18, ha="center", va="center")
        except Exception:
            ax.text(0.5, 0.5, texte_latex, fontsize=12, ha="center", va="center")
        self.canvas.draw()

    def _on_clavier_vers_latex(self):
        try:
            equation = analyser_equation_clavier(self.champ_clavier.text())
        except Exception as e:
            QMessageBox.warning(self, "Équation invalide", str(e))
            return
        texte_latex = equation_vers_latex(equation)
        self.champ_latex.setText(texte_latex)
        self._mettre_a_jour_apercu(texte_latex)
        self._charger_equation(equation)

    def _on_latex_vers_clavier(self):
        try:
            equation = analyser_equation_latex(self.champ_latex.text())
        except Exception as e:
            QMessageBox.warning(self, "Équation LaTeX invalide", str(e))
            return
        self.champ_clavier.setText(equation_vers_clavier(equation))
        self._mettre_a_jour_apercu(equation_vers_latex(equation))
        self._charger_equation(equation)

    def _charger_equation(self, equation):
        self.equation = equation
        self.solutions = []
        self.label_solutions.setText("")
        self.label_resultat.setText("")
        self.bouton_calculer.setEnabled(False)
        vider_layout(self.layout_valeurs)

        variables = sorted(equation.free_symbols, key=lambda s: s.name)
        self.combo_variable.clear()
        self.combo_variable.addItems([v.name for v in variables])

    def _on_isoler(self):
        if self.equation is None:
            return
        nom_variable = self.combo_variable.currentText()
        if not nom_variable:
            return
        try:
            self.solutions = isoler_variable(self.equation, Symbol(nom_variable))
        except Exception as e:
            QMessageBox.warning(self, "Impossible d'isoler", str(e))
            return

        lignes = []
        for indice, solution in enumerate(self.solutions, start=1):
            prefixe = f"Solution {indice}" if len(self.solutions) > 1 else nom_variable
            lignes.append(f"{prefixe} = {str(solution).replace('**', '^')}")
        self.label_solutions.setText("\n".join(lignes))

        if len(self.solutions) == 1:
            self._mettre_a_jour_apercu(f"{nom_variable} = {latex(self.solutions[0])}")

        # reconstruit dynamiquement les champs de saisie pour les AUTRES variables
        vider_layout(self.layout_valeurs)
        self.spinboxes_valeurs = {}
        autres_variables = sorted(
            (s.name for s in self.equation.free_symbols if s.name != nom_variable)
        )
        for nom in autres_variables:
            spin = QDoubleSpinBox()
            spin.setDecimals(6)
            spin.setRange(-1e12, 1e12)
            spin.setValue(1.0)
            self.spinboxes_valeurs[nom] = spin
            self.layout_valeurs.addRow(f"{nom} :", spin)

        self.bouton_calculer.setEnabled(True)
        self.label_resultat.setText("")

    def _on_calculer(self):
        if not self.solutions:
            return
        valeurs = {nom: spin.value() for nom, spin in self.spinboxes_valeurs.items()}

        nom_variable = self.combo_variable.currentText()
        lignes = []
        for indice, solution in enumerate(self.solutions, start=1):
            prefixe = f"Solution {indice}" if len(self.solutions) > 1 else nom_variable
            try:
                resultat = evaluer_numeriquement(solution, valeurs)
            except Exception as e:
                lignes.append(f"{prefixe} : erreur ({e})")
                continue
            try:
                valeur_flottante = float(resultat)
                lignes.append(f"{prefixe} : {nom_variable} = {valeur_flottante:.6g}")
            except TypeError:
                lignes.append(f"{prefixe} : pas de solution réelle ({resultat})")

        self.label_resultat.setText("\n".join(lignes))


def main():
    app = QApplication(sys.argv)
    fenetre = FenetreProgramme()
    fenetre.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
