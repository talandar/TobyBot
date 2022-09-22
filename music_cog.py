import asyncio
import discord
from discord.ext import commands, tasks
from youtube_dl import YoutubeDL
from ytwrapper import *
from utils import send

import playlist

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.server_playlists = {}
        self._now_playing = None

    @commands.command()
    async def join(self, ctx):
        """Joins your current voice channel"""
        channel = None
        if ctx.author.voice:
            channel = ctx.author.voice.channel
        if channel:
            if ctx.voice_client is not None:
                return await ctx.voice_client.move_to(channel)
            await channel.connect()
        else:
            await send(ctx, "You're not in a voice channel!  I don't know what channel to join! :confounded:")

    @commands.command()
    async def volume(self, ctx, volume: int):
        """(volume [0-100]): Changes the player's volume"""
        if ctx.voice_client is None:
            return await send(ctx, "Not connected to a voice channel.")
        volume = max(0, min(volume, 100))
        ctx.voice_client.source.volume = volume / 100
        await send(ctx, f"Changed volume to {volume}%")

    @commands.command()
    async def leave(self, ctx):
        """Stops and disconnects the bot from voice"""
        self._now_playing = None
        await ctx.voice_client.disconnect()

    @commands.command()
    async def stop(self, ctx):
        """Stops playing the current playlist or stream without leaving the channel"""
        self._now_playing = None
        data = self._get_data(ctx)
        data.stop()
        ctx.voice_client.stop()

    @commands.command(aliases=['playlists'])
    async def listplaylists(self, ctx):
        """list the existing playlists"""
        data = self._get_data(ctx)
        lists = data.list_playlists()
        output = "Here's the playlists that I currently have:\n"
        if lists:
            lists = "\n".join(lists)
            output = output + lists
        await send(ctx, output)

    @commands.command()
    async def createplaylist(self, ctx, name:str):
        """(name): create a new playlist by name"""
        data = self._get_data(ctx)
        success = data.add_playlist(name)
        if success:
            await send(ctx, f"Created new playlist with name \"{name}\"")
        else:
            await send(ctx, f"Couldn't create playlist with name \"{name}\".  Sorry :sob:")

    @commands.command()
    async def deleteplaylist(self, ctx, name:str):
        """(name): Delete an existing playlist by name"""
        data = self._get_data(ctx)
        if data.current_playlist() == name:
            #this should finish the current song then stop playing.
            data.stop()
        success = data.remove_playlist(name)
        if success:
            await send(ctx, f"Removed the playlist called \"{name}\"")
        else:
            await send(ctx, f"Something went wrong removing the playlist called \"{name}\".  Sorry :sob:")

    @commands.command()
    async def songs(self, ctx, name:str, urls:str=None):
        """(playlist name) (opt: print urls?): Get the list of songs in a playlist"""
        data = self._get_data(ctx)
        songurls = data.songs_in_list(name)
        songs = []
        await send(ctx, "One second while I retrieve the song data...")
        async with ctx.typing():
            for url in songurls:
                song_meta = await YTDLSource.meta_from_url(url)
                if urls:
                    songs.append(f"\t**{song_meta['title']}**  Uploaded by {song_meta['uploader']} ({url})")
                else:
                    songs.append(f"\t**{song_meta['title']}**  Uploaded by {song_meta['uploader']}")
            songs = '\n'.join(songs)
        output = f"Here's what's in {name}:\n{songs}"
        await send(ctx, output)

    @commands.command()
    async def addsong(self, ctx, playlist_name:str, song_url:str):
        """(playlist) (song url): add a song to a playlist"""
        data = self._get_data(ctx)
        if data.add_to_playlist(playlist_name,song_url):
            await ctx.message.add_reaction("\N{THUMBS UP SIGN}")
        else:
            await send(ctx, "Something went wrong, sorry!  Does the playlist exist?")

    @commands.command(name='addPlaylistToPlaylist')
    async def add_songs_from_playlist(self, ctx, playlist_name:str, playlist_url:str):
        """(playlist) (playlist url): add a song to a playlist"""
        data = self._get_data(ctx)
        await send(ctx, "One minute while I pull song data from that playlist...")
        async with ctx.typing():
            playlist_songs = await YTDLSource.playlist_from_url(playlist_url)
            all_success=True
            for song in playlist_songs:
                all_success = all_success and data.add_to_playlist(playlist_name, song)
        if all_success:
            await ctx.message.add_reaction("\N{THUMBS UP SIGN}")
            await send(ctx, f"Added {len(playlist_songs)} songs to {playlist_name}")
        else:
            await send(ctx, "Something went wrong, sorry!  Does the playlist exist?")


    @commands.command()
    async def removesong(self, ctx, playlist_name:str, song_url:str):
        """(playlist) (song url): remove a song from a playlist"""
        data = self._get_data(ctx)
        if data.remove_from_playlist(playlist_name,song_url):
            await ctx.message.add_reaction("\N{THUMBS UP SIGN}")
        else:
            await send(ctx, "Something went wrong, sorry!  Does the playlist exist?")

    @commands.command()
    async def stream(self, ctx, url:str):
        """(url): Immediately streams from a url, does not modify playlists."""
        data = self._get_data(ctx)
        old_stream = data.current_stream()
        data.stream(url)
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else self._stream_over_callback(ctx))
            if old_stream != url:
                self._now_playing = f"Now streaming {player.title}"
                await send(ctx, self._now_playing)

    def _stream_over_callback(self, ctx):
        #check if channel empty, and stop/leave if it is
        if ctx.voice_client and (len(ctx.voice_client.channel.voice_states) == 1):
            asyncio.run_coroutine_threadsafe(self.leave(ctx), loop=self.bot.loop)
        stream = self._get_data(ctx).current_stream()
        if stream:
            asyncio.run_coroutine_threadsafe(self.stream(ctx, stream), loop=self.bot.loop)

    @commands.command()
    async def play(self, ctx, playlist_name:str):
        """(playlist): Play a playlist.  Loops randomly through songs in the list."""
        data = self._get_data(ctx)
        async with ctx.typing():
            song = data.play(playlist_name)
            if song: 
                player = await YTDLSource.from_url(song, loop=self.bot.loop, stream=True)
                ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else self._song_over_callback(ctx))
                self._now_playing = f"Now playing {player.title} in playlist {data.current_playlist()}"
                await send(ctx, self._now_playing)
            else:
                self._now_playing = None
                await send(ctx, "No more songs to play.  Did the playlist get deleted?")

    def _song_over_callback(self, ctx):
        #check if channel empty, and stop/leave if it is
        if ctx.voice_client and (len(ctx.voice_client.channel.voice_states) == 1):
            asyncio.run_coroutine_threadsafe(self.leave(ctx), loop=self.bot.loop)
        pl = self._get_data(ctx).current_playlist()
        if pl:
            asyncio.run_coroutine_threadsafe(self.play(ctx, pl), loop=self.bot.loop)

    @commands.command(aliases=["currentsong"])
    async def nowplaying(self, ctx):
        """get the currently playing song and playlist"""
        if self._now_playing:
            await send(ctx, self._now_playing)
        else:
            await send(ctx, "Not currently playing!")

    @commands.command(aliases=["skip"])
    async def next(self, ctx):
        """Go to the next song in the playlist.  If streaming, ends the song."""
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()

    def _get_data(self, context):
        id = context.guild.id
        if id in self.server_playlists:
            return self.server_playlists[id]
        else:
            data = playlist.ServerPlaylist(id)
            self.server_playlists[id] = data
            return data

    #Disable this - it was for playing downloaded files
    #@commands.command()
    async def play_downloaded(self, ctx, *, query):
        """Plays a file from the local filesystem"""

        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
        ctx.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)

        await send(ctx, f'Now playing: {query}')

    #Disable this - it downloads the file
    #@commands.command()
    async def download(self, ctx, *, url):
        """Plays from a url (almost anything youtube_dl supports)"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

        await send(ctx, f'Now playing: {player.title}')

    @play.before_invoke
    @stream.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await send(ctx, "You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()