import asyncio
import nextcord
import youtube_dl


# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': './audio/%(title)s-%(id)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(nextcord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def meta_from_url(cls, url, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        except (youtube_dl.utils.DownloadError, youtube_dl.utils.ExtractorError):
            raise YTDLException(url)

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        return data

    @classmethod
    async def playlist_meta_from_url(cls, url, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        except (youtube_dl.utils.DownloadError, youtube_dl.utils.ExtractorError):
            raise YTDLException(url)

        if 'entries' in data:
            # un-nest entries
            data = data['entries']
        return data

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(nextcord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

    @classmethod
    async def playlist_from_url(cls, url, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        except (youtube_dl.utils.DownloadError, youtube_dl.utils.ExtractorError):
            raise YTDLException(url)

        retval = []
        if 'entries' in data:
            # un-nest entries
            data = data['entries']
            for entry in data:
                filename = entry['webpage_url']
                retval.append(filename)
        else:
            filename = data['webpage_url']
            retval.append(filename)
        return retval


class YTDLException(Exception):
    pass