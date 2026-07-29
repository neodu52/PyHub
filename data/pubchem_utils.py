"""
data/pubchem_utils.py — Module PARTAGÉ (pas de fenêtre, pas d'UI)
====================================================================
But : donner à n'importe quel programme du hub une fonction simple,
`obtenir_proprietes(nom_ou_formule)`, qui renvoie la masse molaire (et
d'autres propriétés) d'un composé chimique, en cherchant d'abord dans
une base locale avant d'interroger Internet.

Logique (cache local -> PubChem en secours -> mise en cache) :
    1. On cherche le composé dans data/composes_locale.json.
    2. S'il est absent, on interroge l'API PubChem (PUG REST, gratuite,
       sans clé) :
         a) d'abord par NOM      (marche pour "acetone", "water", "oxygen"...)
         b) sinon par FORMULE    (marche pour "H2O", "CO2", "NaCl"...)
    3. Le résultat obtenu est enregistré dans composes_locale.json :
       la prochaine fois, plus besoin d'Internet pour ce composé.

Ce fichier ne dépend PAS de PyQt : c'est un utilitaire pur, réutilisable
par n'importe quel futur programme de la catégorie Chimie (ou ailleurs).

Comment l'utiliser depuis un programme situé dans
categories/<Categorie>/<Programme>/main.py :

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "data"))
    import pubchem_utils as pc

    infos = pc.obtenir_proprietes("acetone")
    print(infos["masse_molaire"])   # 58.08
"""

import json
import re
import unicodedata
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None  # le mode "cache local uniquement" reste utilisable sans requests

DOSSIER_DATA = Path(__file__).resolve().parent
CHEMIN_CACHE = DOSSIER_DATA / "composes_locale.json"

PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PUBCHEM_AUTOCOMPLETE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/autocomplete/compound"
PROPRIETES_DEMANDEES = "MolecularWeight,MolecularFormula,IUPACName"
DELAI_REQUETE_SECONDES = 10
EN_TETE_HTTP = {"User-Agent": "PyHub-personnel/1.0 (usage non commercial)"}


class ComposeIntrouvable(Exception):
    """Levée quand un composé n'est trouvé ni dans le cache local, ni sur PubChem."""


def normaliser_cle(texte):
    """Normalise un nom/formule pour en faire une clé de cache stable :
    minuscules, sans accents, espaces multiples réduits à un seul."""
    texte = texte.strip().lower()
    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = re.sub(r"\s+", " ", texte)
    return texte


def _charger_cache():
    if not CHEMIN_CACHE.exists():
        return {}
    try:
        with open(CHEMIN_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _sauvegarder_cache(cache):
    CHEMIN_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHEMIN_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)


def _interroger_pubchem_par_nom(nom):
    """Tente /compound/name/... — fonctionne pour les noms communs
    (anglais surtout) et pour pas mal de formules simples (O2, N2...)."""
    url = f"{PUBCHEM_BASE}/compound/name/{nom}/property/{PROPRIETES_DEMANDEES}/JSON"
    reponse = requests.get(url, headers=EN_TETE_HTTP, timeout=DELAI_REQUETE_SECONDES)
    if reponse.status_code != 200:
        return None
    return reponse.json()["PropertyTable"]["Properties"][0], False


def _interroger_pubchem_par_formule(formule):
    """Tente /compound/fastformula/... — utile quand la recherche par nom
    échoue et que l'utilisateur a tapé une formule brute (ex: 'C3H6O').
    Attention : une formule peut correspondre à plusieurs composés
    (isomères) ; on prend le premier résultat et on signale l'ambiguïté."""
    url_cids = f"{PUBCHEM_BASE}/compound/fastformula/{formule}/cids/JSON"
    reponse = requests.get(url_cids, headers=EN_TETE_HTTP, timeout=DELAI_REQUETE_SECONDES)
    if reponse.status_code != 200:
        return None
    cids = reponse.json().get("IdentifierList", {}).get("CID", [])
    if not cids:
        return None

    url_props = f"{PUBCHEM_BASE}/compound/cid/{cids[0]}/property/{PROPRIETES_DEMANDEES}/JSON"
    reponse2 = requests.get(url_props, headers=EN_TETE_HTTP, timeout=DELAI_REQUETE_SECONDES)
    if reponse2.status_code != 200:
        return None
    proprietes = reponse2.json()["PropertyTable"]["Properties"][0]
    return proprietes, len(cids) > 1


def obtenir_proprietes(nom_ou_formule):
    """
    Renvoie un dict :
        {
            "nom_saisi":     ...,   # tel que fourni en argument
            "nom_pubchem":   ...,   # nom IUPAC renvoyé par PubChem
            "formule":       ...,   # formule brute
            "masse_molaire": ...,   # g/mol (float)
            "cid_pubchem":   ...,   # identifiant PubChem (utile pour vérifier à la main)
            "source":        "locale" | "pubchem_nom" | "pubchem_formule",
            "ambigu":        bool,  # True si trouvé par formule et plusieurs composés possibles
        }

    Lève ComposeIntrouvable si le composé n'est trouvé nulle part, ou si
    `requests` n'est pas installé et que le composé n'est pas déjà en cache.
    """
    cle = normaliser_cle(nom_ou_formule)
    cache = _charger_cache()

    if cle in cache:
        resultat = dict(cache[cle])
        resultat["source"] = "locale"
        return resultat

    if requests is None:
        raise ComposeIntrouvable(
            f"« {nom_ou_formule} » n'est pas dans la base locale, et le module "
            "'requests' n'est pas installé pour interroger PubChem "
            "(installez-le avec : pip install requests)."
        )

    proprietes, ambigu, source = None, False, None
    try:
        reponse_nom = _interroger_pubchem_par_nom(nom_ou_formule.strip())
        if reponse_nom is not None:
            proprietes, ambigu = reponse_nom
            source = "pubchem_nom"
        else:
            reponse_formule = _interroger_pubchem_par_formule(nom_ou_formule.strip())
            if reponse_formule is not None:
                proprietes, ambigu = reponse_formule
                source = "pubchem_formule"
    except requests.exceptions.RequestException as e:
        raise ComposeIntrouvable(
            f"Impossible de contacter PubChem pour « {nom_ou_formule} » "
            f"(vérifiez votre connexion Internet). Détail : {e}"
        )

    if proprietes is None:
        raise ComposeIntrouvable(
            f"« {nom_ou_formule} » est introuvable, ni dans la base locale, ni sur PubChem.\n"
            "Vérifiez l'orthographe, ou essayez le nom anglais du composé, ou sa formule brute."
        )

    resultat = {
        "nom_saisi": nom_ou_formule.strip(),
        "nom_pubchem": proprietes.get("IUPACName") or "",
        "formule": proprietes.get("MolecularFormula") or "",
        "masse_molaire": float(proprietes.get("MolecularWeight", 0.0)),
        "cid_pubchem": proprietes.get("CID"),
        "source": source,
        "ambigu": ambigu,
    }

    # Mise en cache locale (on ne stocke pas "source", qui est recalculée à chaque lecture)
    cache[cle] = {k: v for k, v in resultat.items() if k != "source"}
    _sauvegarder_cache(cache)

    return resultat


def rechercher_suggestions(texte_partiel, limite=10):
    """Auto-complétion façon barre de recherche : renvoie une liste de noms
    de composés suggérés par PubChem à partir d'un texte partiel (ex: "ace"
    -> ["Acetone", "Acetic Acid", "Acetaminophen", ...]).

    Utilise le service officiel d'auto-complétion de PubChem :
    https://pubchem.ncbi.nlm.nih.gov/docs/autocomplete

    Ne lève JAMAIS d'exception : en cas d'échec réseau, de réponse
    inattendue, ou si `requests` n'est pas installé, renvoie simplement une
    liste vide. C'est une fonctionnalité de confort (suggestions), pas une
    donnée critique — un échec silencieux (pas de suggestions) est
    préférable à une erreur qui interromprait la saisie de l'utilisateur.
    """
    texte_partiel = texte_partiel.strip()
    if len(texte_partiel) < 2 or requests is None:
        return []
    url = f"{PUBCHEM_AUTOCOMPLETE_URL}/{texte_partiel}/json"
    try:
        reponse = requests.get(
            url, params={"limit": limite}, headers=EN_TETE_HTTP,
            timeout=DELAI_REQUETE_SECONDES
        )
        if reponse.status_code != 200:
            return []
        donnees = reponse.json()
        termes = donnees.get("dictionary_terms", {}).get("compound", [])
        return list(termes[:limite])
    except Exception:
        return []
