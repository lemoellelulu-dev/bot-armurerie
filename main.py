import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

import database as db
from commands import setup_commands
from views import PanelView

TOKEN = "MTUxODM1NjE0NjA2MTE4MTEwMA.G27sSy.Sgo9kn6RJ6iUQ_C_OA7KAvkWAX4LKpkKenlq7Q"
if not TOKEN:
    raise RuntimeError("Variable d'environnement DISCORD_TOKEN manquante.")

# ─────────────────────────────────────────────
#  Intents
# ─────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True
intents.message_content = False  # non nécessaire pour les slash commands


class ArmurierBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Initialise la base de données
        db.init_db()

        # Enregistre les commandes slash
        setup_commands(self)

        # Enregistre la vue persistante (survit aux redémarrages)
        self.add_view(PanelView())

        # Synchronise les commandes sur tous les guilds
        guild = discord.Object(id=1518299343621460068)  # ton ID de serveur
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        print(f"[Armurerie] {len(synced)} commande(s) synchronisée(s).")

    async def on_ready(self):
        print(f"[Armurerie] Connecté en tant que {self.user} (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="l'armurerie 🔫",
            )
        )


bot = ArmurierBot()


@bot.event
async def on_guild_join(guild: discord.Guild):
    """Synchronise les commandes sur le nouveau serveur."""
    await bot.tree.sync(guild=guild)
    print(f"[Armurerie] Rejoint le serveur : {guild.name}")


if __name__ == "__main__":
    bot.run(TOKEN)
