# commands.py – Commandes slash de l'armurerie

import discord
from discord import app_commands
from discord.ext import commands
import database as db
import permissions as perms
from config import CATEGORIES, ROLE_ARMURIER, ROLE_COMMANDEMENT
from exports import generer_csv
from views import PanelView, send_log


def setup_commands(bot: commands.Bot) -> None:
    """Enregistre toutes les commandes slash sur le bot."""

    # ─────────────────────────────────────────────
    #  /ajouter_arme
    # ─────────────────────────────────────────────
    @bot.tree.command(name="ajouter_arme", description="[Armurier] Ajouter une arme à l'inventaire.")
    @app_commands.describe(nom="Nom de l'arme", categorie="Catégorie")
    @app_commands.choices(
        categorie=[app_commands.Choice(name=c, value=c) for c in CATEGORIES]
    )
    async def ajouter_arme(interaction: discord.Interaction, nom: str, categorie: str):
        if not perms.peut_gerer_armes(interaction.user):
            await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
            return
        arme_id = db.ajouter_arme(nom, categorie)
        e = discord.Embed(title="✅ Arme ajoutée", color=0x2ECC71)
        e.add_field(name="Identifiant", value=arme_id)
        e.add_field(name="Nom", value=nom)
        e.add_field(name="Catégorie", value=categorie)
        await interaction.response.send_message(embed=e, ephemeral=True)

        log = discord.Embed(title="➕ Arme ajoutée", color=0x2ECC71)
        log.add_field(name="Par", value=str(interaction.user))
        log.add_field(name="Arme", value=f"{nom} ({arme_id})")
        log.timestamp = discord.utils.utcnow()
        await send_log(interaction.guild, log)

    # ─────────────────────────────────────────────
    #  /supprimer_arme
    # ─────────────────────────────────────────────
    @bot.tree.command(name="supprimer_arme", description="[Armurier] Supprimer une arme de l'inventaire.")
    @app_commands.describe(arme_id="Identifiant de l'arme (ex: HK4-00001)")
    async def supprimer_arme(interaction: discord.Interaction, arme_id: str):
        if not perms.peut_gerer_armes(interaction.user):
            await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
            return
        arme = db.get_arme(arme_id)
        if not arme:
            await interaction.response.send_message("❌ Arme introuvable.", ephemeral=True)
            return
        db.supprimer_arme(arme_id)
        await interaction.response.send_message(f"✅ Arme `{arme_id}` supprimée.", ephemeral=True)

        log = discord.Embed(title="🗑️ Arme supprimée", color=0xE74C3C)
        log.add_field(name="Par", value=str(interaction.user))
        log.add_field(name="Arme", value=f"{arme['nom']} ({arme_id})")
        log.timestamp = discord.utils.utcnow()
        await send_log(interaction.guild, log)

    # ─────────────────────────────────────────────
    #  /modifier_arme
    # ─────────────────────────────────────────────
    @bot.tree.command(name="modifier_arme", description="[Armurier] Modifier le nom ou la catégorie d'une arme.")
    @app_commands.describe(arme_id="Identifiant", nom="Nouveau nom (optionnel)", categorie="Nouvelle catégorie (optionnel)")
    @app_commands.choices(
        categorie=[app_commands.Choice(name=c, value=c) for c in CATEGORIES]
    )
    async def modifier_arme(
        interaction: discord.Interaction,
        arme_id: str,
        nom: str | None = None,
        categorie: str | None = None,
    ):
        if not perms.peut_gerer_armes(interaction.user):
            await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
            return
        ok = db.modifier_arme(arme_id, nom=nom, categorie=categorie)
        if not ok:
            await interaction.response.send_message("❌ Arme introuvable ou aucune modification.", ephemeral=True)
            return
        await interaction.response.send_message(f"✅ Arme `{arme_id}` modifiée.", ephemeral=True)

        log = discord.Embed(title="✏️ Arme modifiée", color=0xF39C12)
        log.add_field(name="Par", value=str(interaction.user))
        log.add_field(name="Identifiant", value=arme_id)
        if nom:
            log.add_field(name="Nouveau nom", value=nom)
        if categorie:
            log.add_field(name="Nouvelle catégorie", value=categorie)
        log.timestamp = discord.utils.utcnow()
        await send_log(interaction.guild, log)

    # ─────────────────────────────────────────────
    #  /liste_armes
    # ─────────────────────────────────────────────
    @bot.tree.command(name="liste_armes", description="Lister toutes les armes de l'inventaire.")
    @app_commands.describe(categorie="Filtrer par catégorie (optionnel)")
    @app_commands.choices(
        categorie=[app_commands.Choice(name=c, value=c) for c in CATEGORIES]
    )
    async def liste_armes(interaction: discord.Interaction, categorie: str | None = None):
        armes = db.liste_armes(categorie=categorie)
        if not armes:
            await interaction.response.send_message("Aucune arme dans l'inventaire.", ephemeral=True)
            return
        e = discord.Embed(title="🗃️ Inventaire des armes", color=0x3498DB)
        for arme in armes[:25]:
            dispo = "✅ Disponible" if arme["disponible"] else "🔴 Sortie"
            e.add_field(
                name=f"{arme['id']} – {arme['nom']}",
                value=f"{arme['categorie']} | {dispo}",
                inline=False,
            )
        if len(armes) > 25:
            e.set_footer(text=f"… et {len(armes) - 25} autres armes.")
        await interaction.response.send_message(embed=e, ephemeral=True)

    # ─────────────────────────────────────────────
    #  /armes_sorties
    # ─────────────────────────────────────────────
    @bot.tree.command(name="armes_sorties", description="[Armurier] Voir les armes actuellement sorties.")
    async def armes_sorties(interaction: discord.Interaction):
        if not perms.peut_voir_historique(interaction.user):
            await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
            return
        suivis = db.armes_sorties()
        if not suivis:
            await interaction.response.send_message("Aucune arme en cours de sortie.", ephemeral=True)
            return
        e = discord.Embed(title="🔫 Armes actuellement sorties", color=0xE74C3C)
        for s in suivis[:25]:
            e.add_field(
                name=f"{s['numero_suivi']} – {s.get('nom_arme', s['arme_id'])}",
                value=f"{s['utilisateur']} | Matricule : {s['matricule']} | Depuis : {s['date_sortie']}",
                inline=False,
            )
        await interaction.response.send_message(embed=e, ephemeral=True)

    # ─────────────────────────────────────────────
    #  /recherche_suivi
    # ─────────────────────────────────────────────
    @bot.tree.command(name="recherche_suivi", description="Rechercher un suivi par son numéro.")
    @app_commands.describe(numero="Numéro de suivi (ex: ARM-000001)")
    async def recherche_suivi(interaction: discord.Interaction, numero: str):
        suivi = db.get_suivi(numero.upper())
        if not suivi:
            await interaction.response.send_message("❌ Suivi introuvable.", ephemeral=True)
            return
        e = discord.Embed(title=f"🔎 Suivi {suivi['numero_suivi']}", color=0x9B59B6)
        e.add_field(name="Arme", value=suivi.get("nom_arme", suivi["arme_id"]))
        e.add_field(name="Identifiant", value=suivi["arme_id"])
        e.add_field(name="Utilisateur", value=suivi["utilisateur"])
        e.add_field(name="Matricule", value=suivi["matricule"])
        e.add_field(name="Date sortie", value=suivi["date_sortie"])
        e.add_field(name="État", value=suivi["etat"])
        if suivi["date_retour"]:
            duree = suivi["duree_minutes"] or 0
            e.add_field(name="Date retour", value=suivi["date_retour"])
            e.add_field(name="Durée", value=f"{duree // 60}h{duree % 60:02d}m")
        await interaction.response.send_message(embed=e, ephemeral=True)

    # ─────────────────────────────────────────────
    #  /arme
    # ─────────────────────────────────────────────
    @bot.tree.command(name="arme", description="Consulter les infos d'une arme.")
    @app_commands.describe(arme_id="Identifiant de l'arme")
    async def arme(interaction: discord.Interaction, arme_id: str):
        a = db.get_arme(arme_id)
        if not a:
            await interaction.response.send_message("❌ Arme introuvable.", ephemeral=True)
            return
        e = discord.Embed(title=f"🔫 {a['nom']}", color=0x2C3E50)
        e.add_field(name="Identifiant", value=a["id"])
        e.add_field(name="Catégorie", value=a["categorie"])
        e.add_field(name="Disponibilité", value="✅ Disponible" if a["disponible"] else "🔴 Sortie")
        e.add_field(name="Ajoutée le", value=a["date_ajout"])
        await interaction.response.send_message(embed=e, ephemeral=True)

    # ─────────────────────────────────────────────
    #  /historique
    # ─────────────────────────────────────────────
    @bot.tree.command(name="historique", description="[Armurier/Commandement] Consulter l'historique.")
    @app_commands.describe(arme_id="Filtrer par arme (optionnel)", utilisateur="Filtrer par utilisateur (optionnel)")
    async def historique(
        interaction: discord.Interaction,
        arme_id: str | None = None,
        utilisateur: discord.Member | None = None,
    ):
        if not perms.peut_voir_historique(interaction.user):
            await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
            return
        discord_id = str(utilisateur.id) if utilisateur else None
        rows = db.get_historique(arme_id=arme_id, discord_id=discord_id, limit=20)
        if not rows:
            await interaction.response.send_message("Aucun historique trouvé.", ephemeral=True)
            return
        e = discord.Embed(title="📜 Historique", color=0x8E44AD)
        for r in rows:
            duree = r["duree_minutes"] or 0
            e.add_field(
                name=f"{r['numero_suivi']} – {r['nom_arme']}",
                value=(
                    f"Par : {r['utilisateur']} | Mat : {r['matricule']}\n"
                    f"Sortie : {r['date_sortie']} | Retour : {r['date_retour'] or '—'}\n"
                    f"Durée : {duree // 60}h{duree % 60:02d}m | État : {r['etat']}"
                ),
                inline=False,
            )
        await interaction.response.send_message(embed=e, ephemeral=True)

    # ─────────────────────────────────────────────
    #  /config_roles
    # ─────────────────────────────────────────────
    @bot.tree.command(name="config_roles", description="[Admin] Configurer les noms des rôles.")
    @app_commands.describe(role_armurier="Nom du rôle Armurier", role_commandement="Nom du rôle Commandement")
    async def config_roles(
        interaction: discord.Interaction,
        role_armurier: str | None = None,
        role_commandement: str | None = None,
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Administrateur requis.", ephemeral=True)
            return
        if role_armurier:
            db.set_config("role_armurier", role_armurier)
        if role_commandement:
            db.set_config("role_commandement", role_commandement)
        await interaction.response.send_message("✅ Configuration des rôles mise à jour.", ephemeral=True)

    # ─────────────────────────────────────────────
    #  /config_logs
    # ─────────────────────────────────────────────
    @bot.tree.command(name="config_logs", description="[Admin] Configurer les salons.")
    @app_commands.describe(
        channel_armurerie="Salon panel",
        channel_logs="Salon logs général",
        channel_logs_sortie="Salon logs sorties d'armes",
        channel_logs_retour="Salon logs retours d'armes",
    )
    async def config_logs(
        interaction: discord.Interaction,
        channel_armurerie: str | None = None,
        channel_logs: str | None = None,
        channel_logs_sortie: str | None = None,
        channel_logs_retour: str | None = None,
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Administrateur requis.", ephemeral=True)
            return
        if channel_armurerie:
            db.set_config("channel_armurerie", channel_armurerie)
        if channel_logs:
            db.set_config("channel_logs", channel_logs)
        if channel_logs_sortie:
            db.set_config("channel_logs_sortie", channel_logs_sortie)
        if channel_logs_retour:
            db.set_config("channel_logs_retour", channel_logs_retour)
        await interaction.response.send_message("✅ Configuration des salons mise à jour.", ephemeral=True)

    # ─────────────────────────────────────────────
    #  /envoyer_panel
    # ─────────────────────────────────────────────
    @bot.tree.command(name="envoyer_panel", description="[Armurier] Envoyer le panel dans #armurerie.")
    async def envoyer_panel(interaction: discord.Interaction):
        if not perms.peut_gerer_armes(interaction.user):
            await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
            return
        channel_name = db.get_config("channel_armurerie") or "armurerie"
        channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)
        if not channel:
            await interaction.response.send_message(
                f"❌ Salon `#{channel_name}` introuvable.", ephemeral=True
            )
            return
        e = discord.Embed(
            title="🔫 Armurerie",
            description=(
                "Bienvenue à l'armurerie.\n\n"
                "Utilisez les boutons ci-dessous pour gérer vos armes.\n\n"
                "**🔫 Prendre une arme** – Sortir une arme de l'inventaire\n"
                "**✅ Rendre une arme** – Restituer une arme\n"
                "**📋 Mes armes** – Voir vos armes en cours\n"
                "**🔎 Rechercher un suivi** – Retrouver un suivi par son numéro"
            ),
            color=0x2C3E50,
        )
        e.set_footer(text="Système de gestion des armes")
        await channel.send(embed=e, view=PanelView())
        await interaction.response.send_message(f"✅ Panel envoyé dans {channel.mention}.", ephemeral=True)

    # ─────────────────────────────────────────────
    #  /export_csv
    # ─────────────────────────────────────────────
    @bot.tree.command(name="export_csv", description="[Armurier/Commandement] Exporter l'historique complet en CSV.")
    async def export_csv(interaction: discord.Interaction):
        if not perms.peut_exporter(interaction.user):
            await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        fichier = generer_csv()
        await interaction.followup.send("📊 Export CSV généré :", file=fichier, ephemeral=True)

        log = discord.Embed(title="📊 Export CSV", color=0x1ABC9C)
        log.add_field(name="Par", value=str(interaction.user))
        log.timestamp = discord.utils.utcnow()
        await send_log(interaction.guild, log)
