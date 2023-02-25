import asyncio
import nextcord
from nextcord.ext import commands
from ytwrapper import YTDLException, YTDLSource
from utils import safe_send, get_register_guilds

import playlist


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.server_playlists = {}
        self._now_playing = None

    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def join(self, interaction: nextcord.Interaction):
        """Joins your current voice channel"""
        channel = None
        if interaction.user.voice:
            channel = interaction.user.voice.channel
        if channel:
            await channel.connect()
            await safe_send(interaction, "Joined! :musical_note::notes:")
        else:
            await safe_send(interaction, "You're not in a voice channel!  I don't know what channel to join! :confounded:")

    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def leave(self, interaction: nextcord.Interaction):
        """Stops and disconnects the bot from voice"""
        self._now_playing = None
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
        await safe_send(interaction, ":wave:")

    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def stop(self, interaction: nextcord.Interaction):
        """Stops playing the current playlist or stream without leaving the channel"""
        self._stop(interaction)
        await safe_send(interaction, ":stop_button:")

    def _stop(self, interaction: nextcord.Interaction):
        print("in _stop")
        self._now_playing = None
        data = self._get_data(interaction)
        data.stop()
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()

    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def playlists(self, interaction: nextcord.Interaction):
        """list the existing playlists"""
        data = self._get_data(interaction)
        lists = data.list_playlists()
        output = "Here's the playlists that I currently have:\n"
        if lists:
            lists = "\n".join(lists)
            output = output + lists
        await safe_send(interaction, output, ephemeral=True)

    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def create_playlist(self, interaction: nextcord.Interaction, name: str):
        """(name): create a new playlist by name"""
        data = self._get_data(interaction)
        success = data.add_playlist(name)
        if success:
            await safe_send(interaction, f"Created new playlist with name \"{name}\"", ephemeral=True)
        else:
            await safe_send(interaction, f"Couldn't create playlist with name \"{name}\".  Sorry :sob:", ephemeral=True)

    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def delete_playlist(self, interaction: nextcord.Interaction, name: str):
        """(name): Delete an existing playlist by name"""
        data = self._get_data(interaction)
        if data.current_playlist() == name:
            # this should finish the current song then stop playing.
            await self._stop(interaction)
        success = data.remove_playlist(name)
        if success:
            await safe_send(interaction, f"Removed the playlist called \"{name}\"", ephemeral=True)
        else:
            await safe_send(interaction, f"Something went wrong removing the playlist called \"{name}\".  Sorry :sob:", ephemeral=True)

    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def songs(self, interaction: nextcord.Interaction, name: str, urls: str = None):
        """(playlist name) (opt: print urls?): Get the list of songs in a playlist"""
        data = self._get_data(interaction)
        songurls = data.songs_in_list(name)
        songs = []
        await interaction.response.defer()
        await interaction.followup.send(f"Retrieving the song data for {name}...", ephemeral=True)
        async with interaction.channel.typing():
            for url in songurls:
                song_meta = await YTDLSource.meta_from_url(url)
                if urls:
                    songs.append(f"\t**{song_meta['title']}**  Uploaded by {song_meta['uploader']} ({url})")
                else:
                    songs.append(f"\t**{song_meta['title']}**  Uploaded by {song_meta['uploader']}")
        songs = '\n'.join(songs)
        output = f"Here's what's in {name}:\n{songs}"
        await safe_send(interaction, output, ephemeral=True)

    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def add_song(self, interaction: nextcord.Interaction, playlist_name: str, song_url: str):
        """(playlist) (song url): add a song to a playlist"""
        data = self._get_data(interaction)
        if data.add_to_playlist(playlist_name, song_url):
            await safe_send(interaction, ":thumbsup:", ephemeral=True)
        else:
            await safe_send(interaction, "Something went wrong, sorry!  Does the playlist exist?", ephemeral=True)

    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def add_songs_from_playlist(self, interaction: nextcord.Interaction, playlist_name: str, playlist_url: str):
        """(playlist) (playlist url): add a song to a playlist"""
        data = self._get_data(interaction)
        await interaction.response.defer()
        await interaction.followup.send("One minute while I pull song data from that playlist...", ephemeral=True)
        async with interaction.channel.typing():
            try:
                playlist_songs = await YTDLSource.playlist_from_url(playlist_url)
            except YTDLException:
                await safe_send(interaction, "There was an error extracting one or more songs from this playlist, sorry.")
                return
            all_success = True
            for song in playlist_songs:
                all_success = data.add_to_playlist(playlist_name, song) and all_success
        if all_success:
            await safe_send(interaction, f"Added {len(playlist_songs)} songs to {playlist_name}", ephemeral=True)
        else:
            await safe_send(interaction, "Something went wrong, sorry!  Does the playlist exist?", ephemeral=True)

    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def remove_song(self, interaction: nextcord.Interaction, playlist_name: str, song_url: str):
        """(playlist) (song url): remove a song from a playlist"""
        data = self._get_data(interaction)
        if data.remove_from_playlist(playlist_name, song_url):
            await safe_send(interaction, "Song removed!", ephemeral=True)
        else:
            await safe_send(interaction, "Something went wrong, sorry!  Does the playlist exist?", ephemeral=True)

    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def stream(self, interaction: nextcord.Interaction, url: str):
        """(url): Immediately streams from a url, does not modify playlists."""
        data = self._get_data(interaction)
        old_stream = data.current_stream()
        data.stream(url)
        try:
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
        except YTDLException:
            await safe_send(interaction, "There was an error getting data to stream this, sorry.")
            return
        interaction.guild.voice_client.play(player, after=lambda e: self._stream_over_callback(error=e, interaction=interaction))
        if old_stream != url:
            self._now_playing = f"Now streaming {player.title}"
            await safe_send(interaction, self._now_playing)

    def _stream_over_callback(self, error=None, interaction: nextcord.Interaction = None):
        # check if channel empty, and stop/leave if it is
        print("stream over callback")
        if error:
            print(f"Player Error: {error}")
        else:
            if interaction.guild.voice_client and (len(interaction.guild.voice_client.channel.voice_states) == 1):
                asyncio.run_coroutine_threadsafe(self.leave(interaction), loop=self.bot.loop)
            stream = self._get_data(interaction).current_stream()
            print(f"currently streaming {stream}")
            if stream:
                asyncio.run_coroutine_threadsafe(self.stream(interaction, stream), loop=self.bot.loop)

    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def play(self, interaction: nextcord.Interaction, playlist_name: str):
        print(f"DEBUG: play called, playlist {playlist_name}, interaction {interaction}")
        """(playlist): Play a playlist.  Loops randomly through songs in the list."""
        data = self._get_data(interaction)
        if interaction.guild.voice_client.is_playing():
            self._stop(interaction)
        song = data.play(playlist_name)
        if song:
            try:
                player = await YTDLSource.from_url(song, loop=self.bot.loop, stream=True)
            except YTDLException:
                await safe_send(interaction, "There was an error getting the song to play.")
                return
            interaction.guild.voice_client.play(player, after=lambda e: self._song_over_callback(error=e, interaction=interaction))
            self._now_playing = f"Now playing {player.title} in playlist {data.current_playlist()}"
            await safe_send(interaction, self._now_playing)
        else:
            self._now_playing = None
            await safe_send(interaction, "No more songs to play.  Did the playlist get deleted?")

    def _song_over_callback(self, error=None, interaction: nextcord.Interaction = None):
        if error:
            print(f"Player Error: {error}")
        else:
            if interaction.guild.voice_client and (len(interaction.guild.voice_client.channel.voice_states) == 1):
                asyncio.run_coroutine_threadsafe(self.leave(interaction), loop=self.bot.loop)
            pl = self._get_data(interaction).current_playlist()
            if pl:
                asyncio.run_coroutine_threadsafe(self.play(interaction, pl), loop=self.bot.loop)

    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def nowplaying(self, interaction: nextcord.Interaction):
        """get the currently playing song and playlist"""
        if self._now_playing:
            await safe_send(interaction, self._now_playing)
        else:
            await safe_send(interaction, "Not currently playing!")

    @nextcord.slash_command(guild_ids=get_register_guilds())
    async def next(self, interaction: nextcord.Interaction):
        """Go to the next song in the playlist.  If streaming, restarts the song."""
        print("next called")
        if interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
        await safe_send(interaction, ":track_next:", ephemeral=True)

    def _get_data(self, interaction):
        id = interaction.guild_id
        if id in self.server_playlists:
            return self.server_playlists[id]
        else:
            data = playlist.ServerPlaylist(id)
            self.server_playlists[id] = data
            return data
