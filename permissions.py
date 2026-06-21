# permissions.py – Vérification des rôles Discord

import discord
from config import ROLE_ARMURIER, ROLE_COMMANDEMENT
from database import get_config


def _role_name(key: str, default: str) -> str:
    return get_config(key) or default


def has_role_armurier(member: discord.Member) -> bool:
    name = _role_name("role_armurier", ROLE_ARMURIER)
    return any(r.name == name for r in member.roles)


def has_role_commandement(member: discord.Member) -> bool:
    name = _role_name("role_commandement", ROLE_COMMANDEMENT)
    return any(r.name == name for r in member.roles)


def peut_gerer_armes(member: discord.Member) -> bool:
    """Armurier ou administrateur Discord."""
    return member.guild_permissions.administrator or has_role_armurier(member)


def peut_voir_historique(member: discord.Member) -> bool:
    return (
        member.guild_permissions.administrator
        or has_role_armurier(member)
        or has_role_commandement(member)
    )


def peut_exporter(member: discord.Member) -> bool:
    return (
        member.guild_permissions.administrator
        or has_role_armurier(member)
        or has_role_commandement(member)
    )
