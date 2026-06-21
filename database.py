# database.py – Gestion SQLite de l'armurerie

import sqlite3
import datetime
from pathlib import Path

DB_PATH = Path("armurerie.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Crée toutes les tables si elles n'existent pas."""
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS configuration (
                cle   TEXT PRIMARY KEY,
                valeur TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS armes (
                id            TEXT PRIMARY KEY,          -- ex: HK4-00001
                nom           TEXT NOT NULL,
                categorie     TEXT NOT NULL,
                disponible    INTEGER NOT NULL DEFAULT 1, -- 1=oui, 0=non
                date_ajout    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS suivis (
                numero_suivi  TEXT PRIMARY KEY,           -- ex: ARM-000001
                arme_id       TEXT NOT NULL,
                utilisateur   TEXT NOT NULL,              -- nom#discriminant
                discord_id    TEXT NOT NULL,
                matricule     TEXT NOT NULL,
                date_sortie   TEXT NOT NULL,
                date_retour   TEXT,
                duree_minutes INTEGER,
                etat          TEXT DEFAULT 'En cours',    -- En cours / Rendue / Endommagée / Perdue
                FOREIGN KEY (arme_id) REFERENCES armes(id)
            );

            CREATE TABLE IF NOT EXISTS historique (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_suivi  TEXT NOT NULL,
                arme_id       TEXT NOT NULL,
                nom_arme      TEXT NOT NULL,
                utilisateur   TEXT NOT NULL,
                discord_id    TEXT NOT NULL,
                matricule     TEXT NOT NULL,
                date_sortie   TEXT NOT NULL,
                date_retour   TEXT,
                duree_minutes INTEGER,
                etat          TEXT NOT NULL
            );
            """
        )


# ─────────────────────────────────────────────
#  Armes
# ─────────────────────────────────────────────

def _next_arme_id(conn: sqlite3.Connection, nom: str) -> str:
    prefix = nom[:3].upper().replace(" ", "")[:3]
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM armes WHERE id LIKE ?", (f"{prefix}-%",)
    ).fetchone()
    num = (row["cnt"] or 0) + 1
    return f"{prefix}-{num:05d}"


def ajouter_arme(nom: str, categorie: str) -> str:
    """Ajoute une arme et retourne son identifiant."""
    with get_conn() as conn:
        arme_id = _next_arme_id(conn, nom)
        date_ajout = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
        conn.execute(
            "INSERT INTO armes (id, nom, categorie, disponible, date_ajout) VALUES (?,?,?,1,?)",
            (arme_id, nom, categorie, date_ajout),
        )
    return arme_id


def supprimer_arme(arme_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM armes WHERE id=?", (arme_id,))
        return cur.rowcount > 0


def modifier_arme(arme_id: str, nom: str | None = None, categorie: str | None = None) -> bool:
    sets, vals = [], []
    if nom:
        sets.append("nom=?"); vals.append(nom)
    if categorie:
        sets.append("categorie=?"); vals.append(categorie)
    if not sets:
        return False
    vals.append(arme_id)
    with get_conn() as conn:
        cur = conn.execute(f"UPDATE armes SET {', '.join(sets)} WHERE id=?", vals)
        return cur.rowcount > 0


def liste_armes(categorie: str | None = None, disponible: bool | None = None):
    query = "SELECT * FROM armes WHERE 1=1"
    params = []
    if categorie:
        query += " AND categorie=?"
        params.append(categorie)
    if disponible is not None:
        query += " AND disponible=?"
        params.append(1 if disponible else 0)
    query += " ORDER BY categorie, nom"
    with get_conn() as conn:
        return conn.execute(query, params).fetchall()


def get_arme(arme_id: str):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM armes WHERE id=?", (arme_id,)).fetchone()


# ─────────────────────────────────────────────
#  Suivis
# ─────────────────────────────────────────────

def _next_suivi_id(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT COUNT(*) as cnt FROM suivis").fetchone()
    num = (row["cnt"] or 0) + 1
    return f"ARM-{num:06d}"


def creer_suivi(arme_id: str, utilisateur: str, discord_id: str, matricule: str) -> str:
    now = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
    with get_conn() as conn:
        suivi_id = _next_suivi_id(conn)
        conn.execute(
            """INSERT INTO suivis
               (numero_suivi, arme_id, utilisateur, discord_id, matricule, date_sortie, etat)
               VALUES (?,?,?,?,?,?,'En cours')""",
            (suivi_id, arme_id, utilisateur, discord_id, matricule, now),
        )
        
    return suivi_id


def cloturer_suivi(numero_suivi: str, etat: str) -> dict | None:
    now = datetime.datetime.now()
    now_str = now.isoformat(sep=" ", timespec="seconds")
    with get_conn() as conn:
        suivi = conn.execute(
            "SELECT * FROM suivis WHERE numero_suivi=?", (numero_suivi,)
        ).fetchone()
        if not suivi or suivi["etat"] != "En cours":
            return None

        date_sortie = datetime.datetime.fromisoformat(suivi["date_sortie"])
        duree = int((now - date_sortie).total_seconds() / 60)

        conn.execute(
            """UPDATE suivis SET date_retour=?, duree_minutes=?, etat=?
               WHERE numero_suivi=?""",
            (now_str, duree, etat, numero_suivi),
        )

        # Remettre disponible uniquement si pas perdue
        

        arme = conn.execute("SELECT nom FROM armes WHERE id=?", (suivi["arme_id"],)).fetchone()
        nom_arme = arme["nom"] if arme else suivi["arme_id"]

        conn.execute(
            """INSERT INTO historique
               (numero_suivi, arme_id, nom_arme, utilisateur, discord_id, matricule,
                date_sortie, date_retour, duree_minutes, etat)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                suivi["numero_suivi"], suivi["arme_id"], nom_arme,
                suivi["utilisateur"], suivi["discord_id"], suivi["matricule"],
                suivi["date_sortie"], now_str, duree, etat,
            ),
        )
        return dict(suivi) | {"date_retour": now_str, "duree_minutes": duree, "etat": etat, "nom_arme": nom_arme}


def get_suivi(numero_suivi: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT s.*, a.nom as nom_arme FROM suivis s LEFT JOIN armes a ON s.arme_id=a.id WHERE s.numero_suivi=?",
            (numero_suivi,),
        ).fetchone()


def suivis_utilisateur(discord_id: str):
    with get_conn() as conn:
        return conn.execute(
            """SELECT s.*, a.nom as nom_arme FROM suivis s
               LEFT JOIN armes a ON s.arme_id=a.id
               WHERE s.discord_id=? AND s.etat='En cours'
               ORDER BY s.date_sortie DESC""",
            (discord_id,),
        ).fetchall()


def armes_sorties():
    with get_conn() as conn:
        return conn.execute(
            """SELECT s.*, a.nom as nom_arme FROM suivis s
               LEFT JOIN armes a ON s.arme_id=a.id
               WHERE s.etat='En cours'
               ORDER BY s.date_sortie DESC"""
        ).fetchall()


# ─────────────────────────────────────────────
#  Historique
# ─────────────────────────────────────────────

def get_historique(arme_id: str | None = None, discord_id: str | None = None, limit: int = 20):
    query = "SELECT * FROM historique WHERE 1=1"
    params = []
    if arme_id:
        query += " AND arme_id=?"
        params.append(arme_id)
    if discord_id:
        query += " AND discord_id=?"
        params.append(discord_id)
    query += " ORDER BY date_sortie DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        return conn.execute(query, params).fetchall()


# ─────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────

def set_config(cle: str, valeur: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO configuration (cle, valeur) VALUES (?,?) ON CONFLICT(cle) DO UPDATE SET valeur=excluded.valeur",
            (cle, valeur),
        )


def get_config(cle: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute("SELECT valeur FROM configuration WHERE cle=?", (cle,)).fetchone()
        return row["valeur"] if row else None


# ─────────────────────────────────────────────
#  Export CSV
# ─────────────────────────────────────────────

def export_all_csv() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT h.*, a.categorie FROM historique h
               LEFT JOIN armes a ON h.arme_id=a.id
               ORDER BY h.date_sortie DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
