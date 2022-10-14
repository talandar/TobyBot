import os

import nextcord
from xcard_cog import XCardHandler
from music_cog import Music
from dice_cog import Dice
from dotenv import load_dotenv
from utils import send, get_version, safe_send, get_register_guilds


class TobyTrack(nextcord.ext.commands.Bot):

    prefix_map = {}
    default_prefix = '+'

    def __init__(self):
        intents = nextcord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, case_insensitive=True)
        self.add_cog(Music(self))
        self.add_cog(XCardHandler(self))
        self.add_cog(Dice(self))
        self.add_general_commands()

    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        print(f'running code built on {get_version()}')

    def add_general_commands(self):
        @self.slash_command(guild_ids=get_register_guilds())
        async def cleanup(interaction: nextcord.Interaction):
            """Clean up commands sent by Toby, as well as any commands sent by players to Toby"""
            await safe_send(interaction, "Cleaning up old messages...")
            async for message in interaction.channel.history(limit=200):
                if message.author == self.user:
                    try:
                        await message.delete()
                    except nextcord.HTTPException:
                        pass

        @self.slash_command(guild_ids=get_register_guilds())
        async def version(interaction: nextcord.Interaction):
            """Get Toby's build version."""
            await safe_send(interaction, f"Version: {get_version()}")

        @self.event
        async def on_command_error(ctx, error):
            if isinstance(error, nextcord.ext.commands.CommandNotFound):
                await send(ctx, "I don't know that command, sorry :(")
            raise error


def main():
    """run the toby tracker.  This Method blocks"""
    load_dotenv()
    client = TobyTrack()
    TOKEN = os.getenv('DISCORD_TOKEN')
    client.run(TOKEN)


if __name__ == "__main__":
    main()
