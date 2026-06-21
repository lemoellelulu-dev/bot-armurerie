# 🔫 Bot Discord Armurerie

Système de gestion des armes complet pour serveur Discord unique.  
Historique permanent · Traçabilité · Export CSV · Gestion des rôles

---

## Structure des fichiers

```
bot-armurerie/
├── main.py          # Point d'entrée – démarrage du bot
├── database.py      # Toutes les opérations SQLite
├── views.py         # Composants UI Discord (boutons, sélecteurs, modals)
├── commands.py      # Commandes slash
├── permissions.py   # Vérification des rôles
├── exports.py       # Génération du fichier CSV
├── config.py        # Constantes et configuration par défaut
├── requirements.txt
└── .env.example
```

---

## Installation

### 1. Prérequis

- Python 3.11 ou supérieur
- Un bot Discord créé sur [discord.com/developers](https://discord.com/developers/applications)

### 2. Permissions requises du bot

Dans le portail développeur Discord, activez :

- **Privileged Gateway Intents** → `Server Members Intent`
- **Bot Permissions** :
  - `Send Messages`
  - `Embed Links`
  - `Attach Files`
  - `Read Message History`
  - `Use Application Commands`

### 3. Installation des dépendances

```bash
pip install -r requirements.txt
```

### 4. Configuration du token

```bash
cp .env.example .env
# Éditez .env et renseignez votre token Discord
```

### 5. Démarrage

```bash
python main.py
```

La base de données `armurerie.db` est créée automatiquement au premier lancement.

---

## Configuration sur le serveur

### Étape 1 – Créer les rôles Discord

Créez ces deux rôles sur votre serveur Discord :

| Rôle | Permissions |
|------|-------------|
| `Armurier` | Gestion complète de l'armurerie |
| `Commandement` | Lecture seule (historique, stats, export) |

> Les noms peuvent être personnalisés avec `/config_roles`.

### Étape 2 – Créer les salons

Créez deux salons textuels :

- `#armurerie` – Panel public avec les boutons
- `#logs-armurerie` – Logs automatiques (réservé à l'équipe)

> Les noms peuvent être personnalisés avec `/config_logs`.

### Étape 3 – Envoyer le panel

```
/envoyer_panel
```

Le bot publie dans `#armurerie` le message permanent avec les 4 boutons.

---

## Commandes disponibles

### Gestion des armes (Armurier)

| Commande | Description |
|----------|-------------|
| `/ajouter_arme` | Ajouter une arme à l'inventaire |
| `/supprimer_arme` | Supprimer une arme |
| `/modifier_arme` | Modifier le nom ou la catégorie |
| `/liste_armes` | Lister toutes les armes |
| `/armes_sorties` | Voir les armes actuellement sorties |

### Recherche (tous)

| Commande | Description |
|----------|-------------|
| `/arme` | Détails d'une arme par son identifiant |
| `/recherche_suivi` | Détails d'un suivi par son numéro |
| `/historique` | Historique filtrable (Armurier/Commandement) |

### Administration (Admin Discord)

| Commande | Description |
|----------|-------------|
| `/config_roles` | Personnaliser les noms des rôles |
| `/config_logs` | Personnaliser les noms des salons |
| `/envoyer_panel` | Publier le panel dans #armurerie |

### Export (Armurier/Commandement)

| Commande | Description |
|----------|-------------|
| `/export_csv` | Télécharger l'historique complet en CSV |

---

## Formats

### Identifiant d'arme

```
HK4-00001   (3 premiers caractères du modèle + numéro auto)
GLO-00001
MP5-00001
```

### Numéro de suivi

```
ARM-000001
ARM-000002
```

### Matricule

```
Format : 3 lettres + 5 chiffres
Exemple : HKA12345
```

---

## Catégories d'armes

- Pistolets
- Pistolets-mitrailleurs
- Fusils d'assaut
- Fusils à pompe
- Fusils de précision
- Armes spéciales
- Équipements

---

## Flux de sortie d'une arme

1. Cliquer sur **🔫 Prendre une arme** dans `#armurerie`
2. Sélectionner une catégorie
3. Sélectionner une arme disponible
4. Saisir son matricule (format `AAA00000`)
5. Confirmer → le numéro de suivi est communiqué

## Flux de retour d'une arme

1. Cliquer sur **✅ Rendre une arme**
2. Sélectionner le suivi à clôturer
3. Sélectionner l'état : `Rendue` / `Endommagée` / `Perdue`
4. Confirmer → l'historique est mis à jour automatiquement

---

## Base de données SQLite

Tables :

| Table | Contenu |
|-------|---------|
| `armes` | Inventaire complet |
| `suivis` | Sorties actives et clôturées |
| `historique` | Historique permanent immuable |
| `configuration` | Paramètres (rôles, salons) |

---

## Sécurité

- Les utilisateurs standards ne voient que leurs propres armes
- L'historique global est réservé aux rôles Armurier / Commandement
- Toutes les actions sont journalisées dans `#logs-armurerie`
- La base de données utilise `WAL mode` pour les accès concurrents
