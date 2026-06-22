# views.py – Composants UI (Buttons, Selects, Modals) pour le panel Armurerie

import discord
from discord.ui import View, Button, Select, Modal, TextInput
import database as db
import permissions as perms
from config import CATEGORIES, ETATS_RETOUR, MATRICULE_PATTERN


# ──────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────

async def send_log(guild: discord.Guild, embed: discord.Embed, type_log: str = "general") -> None:
    """Envoie un embed dans le salon de logs approprié selon le type."""
    from database import get_config
    if type_log == "sortie":
        log_name = get_config("channel_logs_sortie") or get_config("channel_logs") or "logs-armurerie"
    elif type_log == "retour":
        log_name = get_config("channel_logs_retour") or get_config("channel_logs") or "logs-armurerie"
    else:
        log_name = get_config("channel_logs") or "logs-armurerie"
    channel = discord.utils.get(guild.text_channels, name=log_name)
    if channel:
        await channel.send(embed=embed)


def embed_sortie(suivi_id: str, arme_nom: str, arme_id: str,
                 user: discord.Member, matricule: str) -> discord.Embed:
    e = discord.Embed(title="🔫 Arme sortie", color=0xE74C3C)
    e.add_field(name="Arme", value=arme_nom, inline=True)
    e.add_field(name="Identifiant", value=arme_id, inline=True)
    e.add_field(name="Utilisateur", value=str(user), inline=True)
    e.add_field(name="Matricule", value=matricule, inline=True)
    e.add_field(name="Suivi", value=suivi_id, inline=True)
    e.timestamp = discord.utils.utcnow()
    return e


def embed_retour(data: dict, user: discord.Member) -> discord.Embed:
    e = discord.Embed(title="✅ Arme rendue", color=0x2ECC71)
    e.add_field(name="Arme", value=data.get("nom_arme", data["arme_id"]), inline=True)
    e.add_field(name="Identifiant", value=data["arme_id"], inline=True)
    e.add_field(name="Utilisateur", value=str(user), inline=True)
    e.add_field(name="Matricule", value=data["matricule"], inline=True)
    e.add_field(name="Suivi", value=data["numero_suivi"], inline=True)
    e.add_field(name="État", value=data["etat"], inline=True)
    duree = data.get("duree_minutes", 0)
    e.add_field(name="Durée", value=f"{duree // 60}h{duree % 60:02d}m", inline=True)
    e.timestamp = discord.utils.utcnow()
    return e


# ──────────────────────────────────────────────────────────────
#  Modal : saisie du matricule
# ──────────────────────────────────────────────────────────────

class MatriculeModal(Modal, title="Renseignez votre matricule"):
    matricule = TextInput(
        label="Matricule (ex: HKA12345)",
        placeholder="AAA00000",
        min_length=8,
        max_length=8,
    )

    def __init__(self, arme_id: str, arme_nom: str):
        super().__init__()
        self.arme_id = arme_id
        self.arme_nom = arme_nom

    async def on_submit(self, interaction: discord.Interaction):
        mat = self.matricule.value.strip().upper()
        if not MATRICULE_PATTERN.match(mat):
            await interaction.response.send_message(
                "❌ Format de matricule invalide. Format attendu : 3 lettres + 5 chiffres (ex: HKA12345).",
                ephemeral=True,
            )
            return
        view = ConfirmSortieView(self.arme_id, self.arme_nom, mat)
        await interaction.response.send_message(
            f"Vous êtes sur le point de prendre **{self.arme_nom}** (`{self.arme_id}`).\n"
            f"Matricule : **{mat}**\n\n"
            "En cliquant sur Confirmer, vous attestez avoir reçu cette arme.",
            view=view,
            ephemeral=True,
        )


# ──────────────────────────────────────────────────────────────
#  Vue : confirmation sortie
# ──────────────────────────────────────────────────────────────

class ConfirmSortieView(View):
    def __init__(self, arme_id: str, arme_nom: str, matricule: str):
        super().__init__(timeout=120)
        self.arme_id = arme_id
        self.arme_nom = arme_nom
        self.matricule = matricule

    @discord.ui.button(label="Confirmer – Je confirme avoir reçu cette arme.", style=discord.ButtonStyle.green)
    async def confirmer(self, interaction: discord.Interaction, button: Button):
        arme = db.get_arme(self.arme_id)
        if not arme or not arme["disponible"]:
            await interaction.response.send_message("❌ Cette arme n'est plus disponible.", ephemeral=True)
            return

        suivi_id = db.creer_suivi(
            self.arme_id,
            str(interaction.user),
            str(interaction.user.id),
            self.matricule,
        )
        e = discord.Embed(
            title="✅ Arme enregistrée",
            description=f"Numéro de suivi : **{suivi_id}**",
            color=0x2ECC71,
        )
        e.add_field(name="Arme", value=self.arme_nom)
        e.add_field(name="Identifiant", value=self.arme_id)
        e.add_field(name="Matricule", value=self.matricule)
        await interaction.response.edit_message(content=None, embed=e, view=None)

        await send_log(
            interaction.guild,
            embed_sortie(suivi_id, self.arme_nom, self.arme_id, interaction.user, self.matricule),
            type_log="sortie",
        )


# ──────────────────────────────────────────────────────────────
#  Vue : choix de l'arme dans une catégorie
# ──────────────────────────────────────────────────────────────

class ArmeSelectView(View):
    def __init__(self, categorie: str):
        super().__init__(timeout=120)
        armes = db.liste_armes(categorie=categorie, disponible=True)
        if not armes:
            return

        options = [
            discord.SelectOption(label=a["nom"], value=a["id"], description=a["id"])
            for a in armes[:25]
        ]

        select = Select(placeholder="Choisissez une arme…", options=options)

        async def callback(inter: discord.Interaction):
            arme_id = select.values[0]
            arme = db.get_arme(arme_id)
            await inter.response.send_modal(MatriculeModal(arme_id, arme["nom"]))

        select.callback = callback
        self.add_item(select)


# ──────────────────────────────────────────────────────────────
#  Vue : choix de la catégorie (prise d'arme)
# ──────────────────────────────────────────────────────────────

class CategorieSelectView(View):
    def __init__(self):
        super().__init__(timeout=120)
        options = [discord.SelectOption(label=c, value=c) for c in CATEGORIES]
        select = Select(placeholder="Choisissez une catégorie…", options=options)

        async def callback(inter: discord.Interaction):
            categorie = select.values[0]
            armes = db.liste_armes(categorie=categorie, disponible=True)
            if not armes:
                await inter.response.send_message(
                    f"❌ Aucune arme disponible dans la catégorie **{categorie}**.", ephemeral=True
                )
                return
            view = ArmeSelectView(categorie)
            await inter.response.send_message(
                f"Catégorie : **{categorie}** — Choisissez une arme :", view=view, ephemeral=True
            )

        select.callback = callback
        self.add_item(select)


# ──────────────────────────────────────────────────────────────
#  Vue : sélection de l'état lors du retour
# ──────────────────────────────────────────────────────────────

class EtatRetourView(View):
    def __init__(self, numero_suivi: str):
        super().__init__(timeout=120)
        self.numero_suivi = numero_suivi
        options = [discord.SelectOption(label=e, value=e) for e in ETATS_RETOUR]
        select = Select(placeholder="État de l'arme…", options=options)

        async def callback(inter: discord.Interaction):
            etat = select.values[0]
            view = ConfirmRetourView(self.numero_suivi, etat)
            await inter.response.send_message(
                f"Vous allez rendre le suivi **{self.numero_suivi}** avec l'état **{etat}**.\n"
                "En cliquant sur Confirmer, vous attestez avoir rendu cette arme.",
                view=view,
                ephemeral=True,
            )

        select.callback = callback
        self.add_item(select)


# ──────────────────────────────────────────────────────────────
#  Vue : confirmation retour
# ──────────────────────────────────────────────────────────────

class ConfirmRetourView(View):
    def __init__(self, numero_suivi: str, etat: str):
        super().__init__(timeout=120)
        self.numero_suivi = numero_suivi
        self.etat = etat

    @discord.ui.button(label="Confirmer – Je confirme avoir rendu cette arme.", style=discord.ButtonStyle.green)
    async def confirmer(self, interaction: discord.Interaction, button: Button):
        data = db.cloturer_suivi(self.numero_suivi, self.etat)
        if not data:
            await interaction.response.send_message(
                "❌ Ce suivi est introuvable ou déjà clôturé.", ephemeral=True
            )
            return
        duree = data["duree_minutes"]
        e = discord.Embed(title="✅ Retour enregistré", color=0x2ECC71)
        e.add_field(name="Suivi", value=self.numero_suivi)
        e.add_field(name="Arme", value=data.get("nom_arme", data["arme_id"]))
        e.add_field(name="État", value=self.etat)
        e.add_field(name="Durée", value=f"{duree // 60}h{duree % 60:02d}m")
        await interaction.response.edit_message(content=None, embed=e, view=None)

        await send_log(interaction.guild, embed_retour(data, interaction.user), type_log="retour")


# ──────────────────────────────────────────────────────────────
#  Vue : sélection du suivi à rendre
# ──────────────────────────────────────────────────────────────

class SuiviRetourSelectView(View):
    def __init__(self, discord_id: str):
        super().__init__(timeout=120)
        suivis = db.suivis_utilisateur(discord_id)
        if not suivis:
            return

        options = [
            discord.SelectOption(
                label=s["numero_suivi"],
                value=s["numero_suivi"],
                description=(s["nom_arme"] or s["arme_id"])[:50],
            )
            for s in suivis[:25]
        ]
        select = Select(placeholder="Choisissez le suivi à clôturer…", options=options)

        async def callback(inter: discord.Interaction):
            suivi_id = select.values[0]
            view = EtatRetourView(suivi_id)
            await inter.response.send_message(
                f"Suivi **{suivi_id}** – Sélectionnez l'état de l'arme :", view=view, ephemeral=True
            )

        select.callback = callback
        self.add_item(select)


# ──────────────────────────────────────────────────────────────
#  Panel principal (message permanent)
# ──────────────────────────────────────────────────────────────

class PanelView(View):
    """Vue persistante (timeout=None) publiée dans #armurerie."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔫 Prendre une arme", style=discord.ButtonStyle.danger, custom_id="panel:prendre")
    async def prendre(self, interaction: discord.Interaction, button: Button):
        view = CategorieSelectView()
        await interaction.response.send_message(
            "Choisissez une catégorie d'arme :", view=view, ephemeral=True
        )

    @discord.ui.button(label="✅ Rendre une arme", style=discord.ButtonStyle.success, custom_id="panel:rendre")
    async def rendre(self, interaction: discord.Interaction, button: Button):
        suivis = db.suivis_utilisateur(str(interaction.user.id))
        if not suivis:
            await interaction.response.send_message(
                "❌ Vous n'avez aucune arme en cours.", ephemeral=True
            )
            return
        view = SuiviRetourSelectView(str(interaction.user.id))
        await interaction.response.send_message(
            "Choisissez le suivi à clôturer :", view=view, ephemeral=True
        )

    @discord.ui.button(label="📋 Mes armes", style=discord.ButtonStyle.primary, custom_id="panel:mes_armes")
    async def mes_armes(self, interaction: discord.Interaction, button: Button):
        suivis = db.suivis_utilisateur(str(interaction.user.id))
        if not suivis:
            await interaction.response.send_message(
                "Vous n'avez aucune arme en cours.", ephemeral=True
            )
            return
        e = discord.Embed(title="📋 Vos armes en cours", color=0x3498DB)
        for s in suivis:
            e.add_field(
                name=f"{s['numero_suivi']} – {s['nom_arme'] or s['arme_id']}",
                value=f"Sorti le {s['date_sortie']}",
                inline=False,
            )
        await interaction.response.send_message(embed=e, ephemeral=True)

    @discord.ui.button(label="🔎 Rechercher un suivi", style=discord.ButtonStyle.secondary, custom_id="panel:recherche")
    async def recherche(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(RechercheModal())


class RechercheModal(Modal, title="Rechercher un suivi"):
    numero = TextInput(label="Numéro de suivi (ex: ARM-000001)", placeholder="ARM-000001")

    async def on_submit(self, interaction: discord.Interaction):
        suivi = db.get_suivi(self.numero.value.strip().upper())
        if not suivi:
            await interaction.response.send_message("❌ Suivi introuvable.", ephemeral=True)
            return
        e = discord.Embed(title=f"🔎 Suivi {suivi['numero_suivi']}", color=0x9B59B6)
        e.add_field(name="Arme", value=suivi["nom_arme"] or suivi["arme_id"], inline=True)
        e.add_field(name="Identifiant", value=suivi["arme_id"], inline=True)
        e.add_field(name="Utilisateur", value=suivi["utilisateur"], inline=True)
        e.add_field(name="Matricule", value=suivi["matricule"], inline=True)
        e.add_field(name="Sortie", value=suivi["date_sortie"], inline=True)
        e.add_field(name="État", value=suivi["etat"], inline=True)
        if suivi["date_retour"]:
            e.add_field(name="Retour", value=suivi["date_retour"], inline=True)
        await interaction.response.send_message(embed=e, ephemeral=True)
