# config.py – Configuration centrale du bot Armurerie

# Noms des rôles par défaut
ROLE_ARMURIER = "Armurier"
ROLE_COMMANDEMENT = "Commandement"

# Noms des salons par défaut
CHANNEL_ARMURERIE = "armurerie"
CHANNEL_LOGS = "logs-armurerie"

# Catégories d'armes disponibles
CATEGORIES = [
    "Pistolets",
    "Pistolets-mitrailleurs",
    "Fusils d'assaut",
    "Fusils à pompe",
    "Fusils de précision",
    "Armes spéciales",
    "Équipements",
]

# États de retour disponibles
ETATS_RETOUR = ["Rendue", "Endommagée", "Perdue"]

# Format du matricule (3 lettres + 5 chiffres)
import re
MATRICULE_PATTERN = re.compile(r"^[A-Za-z]{3}\d{5}$")
