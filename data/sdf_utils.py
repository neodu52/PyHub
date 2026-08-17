"""
data/sdf_utils.py — Module PARTAGÉ (pas d'UI, pas de PyQt)
====================================================================
Parsing minimal du format SDF / MDL Molfile (V2000) : extrait la liste des
atomes (élément + coordonnées x, y, z) et des liaisons (indices des deux
atomes + ordre de liaison) du premier enregistrement d'un bloc SDF texte.

C'est le format renvoyé par PubChem pour les structures 3D (et 2D) des
composés — voir pubchem_utils.obtenir_structure_3d().

Ne gère que le format V2000 (de très loin le plus courant ; c'est ce que
PubChem renvoie). Le format V3000 (rare, réservé aux très grosses
molécules) n'est pas pris en charge et lève une ValueError claire.
"""


class Atome:
    """Un atome : symbole de l'élément + coordonnées 3D (en Angström)."""
    __slots__ = ("element", "x", "y", "z")

    def __init__(self, element, x, y, z):
        self.element = element
        self.x, self.y, self.z = x, y, z

    def __repr__(self):
        return f"Atome({self.element!r}, {self.x}, {self.y}, {self.z})"


class Liaison:
    """Une liaison entre deux atomes (indices 0-based dans la liste
    d'atomes) et son ordre (1=simple, 2=double, 3=triple, 4=aromatique)."""
    __slots__ = ("i1", "i2", "ordre")

    def __init__(self, i1, i2, ordre):
        self.i1, self.i2, self.ordre = i1, i2, ordre

    def __repr__(self):
        return f"Liaison({self.i1}, {self.i2}, ordre={self.ordre})"


def parser_sdf(texte_sdf):
    """Parse le premier enregistrement d'un bloc SDF (V2000).
    Renvoie (liste_atomes, liste_liaisons).
    Lève ValueError si le format n'est pas reconnu ou si le bloc est vide
    (ex: molécule sans conformère disponible sur PubChem)."""
    lignes = texte_sdf.splitlines()
    if len(lignes) < 4:
        raise ValueError("Bloc SDF vide ou trop court.")

    ligne_compteurs = lignes[3]
    try:
        nb_atomes = int(ligne_compteurs[0:3])
        nb_liaisons = int(ligne_compteurs[3:6])
    except (ValueError, IndexError):
        parties = ligne_compteurs.split()
        if len(parties) < 2:
            raise ValueError("Ligne de comptage SDF illisible.")
        nb_atomes, nb_liaisons = int(parties[0]), int(parties[1])

    if "V3000" in ligne_compteurs:
        raise ValueError("Format V3000 non pris en charge par ce visualiseur (molécule trop volumineuse).")
    if nb_atomes == 0:
        raise ValueError("Structure vide : aucun conformère disponible pour ce composé.")

    debut_atomes = 4
    if len(lignes) < debut_atomes + nb_atomes:
        raise ValueError("Bloc SDF tronqué (moins de lignes que d'atomes annoncés).")

    atomes = []
    for i in range(nb_atomes):
        parties = lignes[debut_atomes + i].split()
        if len(parties) < 4:
            raise ValueError(f"Ligne d'atome SDF illisible : « {lignes[debut_atomes + i]} »")
        x, y, z = float(parties[0]), float(parties[1]), float(parties[2])
        element = parties[3]
        atomes.append(Atome(element, x, y, z))

    debut_liaisons = debut_atomes + nb_atomes
    liaisons = []
    for i in range(nb_liaisons):
        if debut_liaisons + i >= len(lignes):
            break  # certains exports omettent le bloc de liaisons ; on ignore alors
        parties = lignes[debut_liaisons + i].split()
        if len(parties) < 3:
            continue
        i1, i2, ordre = int(parties[0]), int(parties[1]), int(parties[2])
        liaisons.append(Liaison(i1 - 1, i2 - 1, ordre))  # SDF indexe à partir de 1

    return atomes, liaisons
