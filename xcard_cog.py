from nextcord.ext import commands
import nextcord
from utils import safe_send, get_register_guilds


class XCardHandler(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def xcard(self, interaction: nextcord.Interaction):
        """Call for an X card, to stop the current action in case the current action is uncomfortable."""
        await safe_send(interaction, "X-Card - Let's change things up...", file=nextcord.File('./images/xcard.png'))

    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def ocard(self, interaction: nextcord.Interaction):
        """Call for the O card - indicating that what is going on is super cool."""
        await safe_send(interaction, "This scene is great, keep going! :sunglasses:")

    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def fadecard(self, interaction: nextcord.Interaction):
        """Call for a fade to black.  This scene can happen, but lets do that offscreen."""
        await safe_send(interaction, "Fade-Card Called.  Lets fade this scene to black...")
