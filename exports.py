# exports.py – Génération du fichier CSV d'export

import csv
import io
import datetime
import discord
from database import export_all_csv


HEADERS = [
    "numero_suivi",
    "arme_id",
    "nom_arme",
    "categorie",
    "utilisateur",
    "discord_id",
    "matricule",
    "date_sortie",
    "date_retour",
    "duree_minutes",
    "etat",
]


def generer_csv() -> discord.File:
    """Génère un fichier CSV et le retourne sous forme de discord.File."""
    rows = export_all_csv()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=HEADERS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)

    output.seek(0)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"armurerie_export_{timestamp}.csv"
    return discord.File(io.BytesIO(output.getvalue().encode("utf-8-sig")), filename=filename)
