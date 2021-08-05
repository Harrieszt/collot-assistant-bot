import discord
from discord.utils import get
from discord import FFmpegPCMAudio
import youtube_dl
import asyncio
from async_timeout import timeout
from functools import partial
from discord.ext import commands
from datetime import datetime, timedelta
import itertools

bot = commands.Bot(command_prefix='c/',help_command=None)

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'nocheckcertificate': True,
    'noplaylist': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn',
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5" ## song will end if no this line
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get('title')
        self.web_url = data.get('webpage_url')

    def __getitem__(self, item: str):
        """Allows us to access attributes similar to a dict.
        This is only useful when you are NOT downloading.
        """
        return self.__getattribute__(item)

    @classmethod
    async def create_source(cls, ctx, search: str, *, loop, download=False):
        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        if 'entries' in data:
            data = data['entries'][0]

        await ctx.send(f'```ini\n[Added {data["title"]} to the Queue.]\n```') 

        if download:
            source = ytdl.prepare_filename(data)
        else:
            return {'webpage_url': data['webpage_url'], 'requester': ctx.author, 'title': data['title']}

        return cls(discord.FFmpegPCMAudio(source, **ffmpeg_options), data=data, requester=ctx.author)

    @classmethod
    async def regather_stream(cls, data, *, loop):
        """Used for preparing a stream, instead of downloading.
        Since Youtube Streaming links expire."""
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url'], **ffmpeg_options), data=data, requester=requester)

class MusicPlayer:
    """A class which is assigned to each guild using the bot for Music.
    This class implements a queue and loop, which allows for different guilds to listen to different playlists
    simultaneously.
    When the bot disconnects from the Voice it's instance will be destroyed.
    """

    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'np', 'volume')

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None
        self.volume = .5
        self.current = None

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        """Our main player loop."""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                async with timeout(300):
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return await self.destroy(self._guild)

            if not isinstance(source, YTDLSource):
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except Exception as e:
                    await self._channel.send(f'There was an error processing your song.\n'
                                             f'```css\n[{e}]\n```')
                    continue

            source.volume = self.volume
            self.current = source

            self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            self.np = await self._channel.send(f'**Now Playing:** `{source.title}` requested by '
                                               f'`{source.requester}`')
            print(' [Collot Bot ] now({0}) playing {1} request by "{2}" at server "{3}"'.format(datetime.now(), source.title, source.requester, self._guild))
            await self.next.wait()

            source.cleanup()
            self.current = None

            try:
                await self.np.delete()
            except discord.HTTPException:
                pass

    async def destroy(self, guild):
        """Disconnect and cleanup the player."""
        del players[self._guild]
        await self._guild.voice_client.disconnect()
        return self.bot.loop.create_task(self._cog.cleanup(guild))

@bot.event
async def on_ready():
    print(f"Logged in as ID {bot.user}")

@bot.command()
async def help(ctx):
    emBed = discord.Embed(title="Collot's Assisstant - Help", description="All available bot commands", color=0x42f5a7)
    emBed.add_field(name="help", value="Get help command", inline=False)
    emBed.add_field(name="test", value="Test bot command", inline=False)
    emBed.add_field(name="type <text>", value="Respond your message that you've send", inline=False)
    emBed.add_field(name="join", value="Bot will join to your channel", inline=False)
    emBed.add_field(name="leave", value="Bot will leave from your channel", inline=False)
    emBed.add_field(name="play", value="Song name or Song link from Youtube", inline=False)
    emBed.add_field(name="queue", value="See queue song", inline=False)
    emBed.add_field(name="stop", value="Stop playing", inline=False)
    emBed.add_field(name="pause", value="Pause the song", inline=False)
    emBed.add_field(name="resume", value="Resume the song", inline=False)
    emBed.add_field(name="skip", value="Play next song in queue", inline=False)
    emBed.set_thumbnail(url='https://static.wikia.nocookie.net/beastars-eng/images/b/bc/Collot_%28Anime%29.png/revision/latest/scale-to-width-down/259?cb=20190806180535')
    emBed.set_footer(text='Collot assistant written by Harrieszt Laboratories', icon_url='https://github.com/account')
    await ctx.channel.send(embed=emBed)
    print(' [Collot Bot ] {0} query "c/ : help" in {1} at {2} in server "{3}"'.format(ctx.author,ctx.channel,datetime.now(),ctx.guild))

@bot.command()
async def test(ctx):
    global test
    await ctx.channel.send("Experiment Succesfully!")
    print(' [Collot Bot ] {0} query "c/ : test" in {1} at {2} in server "{3}"'.format(ctx.author,ctx.channel,datetime.now(),ctx.guild))

@bot.command()
async def type(ctx, *, par):
    await ctx.channel.send("Your message is {0}".format(par))
    print(ctx.channel)
    print(' [Collot Bot ] {0} query "c/ : type" in {1} at {2} in server "{3}"'.format(ctx.author,ctx.channel,datetime.now(),ctx.guild))

@bot.command()
async def join(ctx):
    channel = ctx.author.voice.channel
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    await ctx.channel.send("Joined to {0} [{1}]".format(ctx.author.voice.channel, ctx.author.name))
    await channel.connect()
    print(' [Collot Bot ] {0} query "c/ : join" in {1} at {2} in server "{3}"'.format(ctx.author,ctx.channel,datetime.now(),ctx.guild))

@bot.command()
async def leave(ctx):
    await ctx.voice_client.disconnect()
    await ctx.channel.send("Succesfully disconnect from {0} [{1}]".format(ctx.author.voice.channel, ctx.author.name))
    print(' [Collot Bot ] {0} query "c/ : leave" in {1} at {2} in server "{3}"'.format(ctx.author,ctx.channel,datetime.now(),ctx.guild))

@bot.command() 
async def play(ctx,* ,search: str):
    channel = ctx.author.voice.channel
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    
    if voice_client == None:
        await channel.connect()
        voice_client = get(bot.voice_clients, guild=ctx.guild)
        print(' [Collot Bot ] joined to {0} at server "{1}"'.format(ctx.author.voice.channel, ctx.guild))

    await ctx.trigger_typing()

    _player = get_player(ctx)
    source = await YTDLSource.create_source(ctx, search, loop=bot.loop, download=False)

    await _player.queue.put(source)
    print(' [Collot Bot ] {0} query "c/ : play {1}" in {2} at {3} in server "{4}"'.format(ctx.author,search,ctx.channel,datetime.now(),ctx.guild))

@bot.command() 
async def p(ctx,* ,search: str):
    channel = ctx.author.voice.channel
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    
    if voice_client == None:
        await channel.connect()
        voice_client = get(bot.voice_clients, guild=ctx.guild)
        print(' [Collot Bot ] joined to {0} at server "{1}"'.format(ctx.author.voice.channel, ctx.guild))

    await ctx.trigger_typing()

    _player = get_player(ctx)
    source = await YTDLSource.create_source(ctx, search, loop=bot.loop, download=False)

    await _player.queue.put(source)
    print('{0} query "c/ : play {1}" in {2} at {3} in server "{4}"'.format(ctx.author,search,ctx.channel,datetime.now(),ctx.guild))

players = {}
def get_player(ctx):
    try:
        player = players[ctx.guild.id]
    except:
        player = MusicPlayer(ctx)
        players[ctx.guild.id] = player
    
    return player

@bot.command()
async def stop(ctx):
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    print(' [Collot Bot ] {0} query "c/ : stop" in {1} at {2} in server "{3}"'.format(ctx.author,ctx.channel,datetime.now(),ctx.guild))
    if voice_client == None:
        await ctx.channel.send("Bot is not connected to voice cahnnel")
        return

    if voice_client.channel != ctx.author.voice.channel:
        await ctx.channel.send("The bot is currently connected to {0}".format(voice_client.channel))
        return

    voice_client.stop()

@bot.command()
async def pause(ctx):
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    print(' [Collot Bot ] {0} query "c/ : stop" in {1} at {2} in server "{3}"'.format(ctx.author,ctx.channel,datetime.now(),ctx.guild))
    if voice_client == None:
        await ctx.channel.send("Bot is not connected to voice channel")
        return

    if voice_client.channel != ctx.author.voice.channel:
        await ctx.channel.send("The bot is currently connected to {0}".format(voice_client.channel))
        return

    voice_client.pause()

@bot.command()
async def resume(ctx):
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    print(' [Collot Bot ] {0} query "c/ : resume" in {1} at {2} in server "{3}"'.format(ctx.author,ctx.channel,datetime.now(),ctx.guild))
    if voice_client == None:
        await ctx.channel.send("Bot is not connected to voice channel")
        return

    if voice_client.channel != ctx.author.voice.channel:
        await ctx.channel.send("The bot is currently connected to {0}".format(voice_client.channel))
        return

    voice_client.resume()

@bot.command()
async def queue(ctx):
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    print(' [Collot Bot ] {0} query "c/ : queue" in {1} at {2} in server "{3}"'.format(ctx.author,ctx.channel,datetime.now(),ctx.guild))

    if voice_client == None or not voice_client.is_connected():
        await ctx.channel.send("Bot is not connected to voice channel", delete_after=10)
        return
    
    player = get_player(ctx)
    if player.queue.empty():
        return await ctx.send('There are currently no more queued songs')
    
    upcoming = list(itertools.islice(player.queue._queue,0,player.queue.qsize()))
    fmt = '\n'.join(f'**`{_["title"]}`**' for _ in upcoming)
    embed = discord.Embed(title=f'Upcoming - Next {len(upcoming)}', description=fmt)
    await ctx.send(embed=embed)

@bot.command()
async def q(ctx):
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    print(' [Collot Bot ] {0} query "c/ : queue" in {1} at {2} in server "{3}"'.format(ctx.author,ctx.channel,datetime.now(),ctx.guild))

    if voice_client == None or not voice_client.is_connected():
        await ctx.channel.send("Bot is not connected to voice channel", delete_after=10)
        return
    
    player = get_player(ctx)
    if player.queue.empty():
        return await ctx.send('There are currently no more queued songs')
    
    upcoming = list(itertools.islice(player.queue._queue,0,player.queue.qsize()))
    fmt = '\n'.join(f'**`{_["title"]}`**' for _ in upcoming)
    embed = discord.Embed(title=f'Upcoming - Next {len(upcoming)}', description=fmt)
    await ctx.send(embed=embed)

@bot.command()
async def skip(ctx):
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    print(' [Collot Bot ] {0} query "c/ : queue" in {1} at {2} in server "{3}"'.format(ctx.author,ctx.channel,datetime.now(),ctx.guild))
    
    if voice_client == None or not voice_client.is_connected():
        await ctx.channel.send("Bot is not connected to voice channel", delete_after=10)
        return

    if voice_client.is_paused():
        pass
    elif not voice_client.is_playing():
        return

    voice_client.stop()
    await ctx.send(f'**`{ctx.author}`**: Skipped the song!')

@bot.command()
async def s(ctx):
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    print(' [Collot Bot ] {0} query "c/ : queue" in {1} at {2} in server "{3}"'.format(ctx.author,ctx.channel,datetime.now(),ctx.guild))

    if voice_client == None or not voice_client.is_connected():
        await ctx.channel.send("Bot is not connected to voice channel", delete_after=10)
        return

    if voice_client.is_paused():
        pass
    elif not voice_client.is_playing():
        return

    voice_client.stop()
    await ctx.send(f'**`{ctx.author}`**: Skipped the song!')

@bot.event
async def on_message(message):
    if message.content == 'Hi':
        await message.channel.send(' Hello, ' + str(message.author.name))
        print(' [Collot Bot ] {0} query "c! : hi" at {1} and can use this command again in {2}'.format(message.author,datetime.now(),message.guild))
    elif message.content == 'c! admin cmd':
        await message.channel.send('Type "c! admin logout" to shutdown this bot')
        print(' [Collot Bot ] {0} query "c! : admin cmd" in {1} at {2} in server {3}'.format(message.author,message.channel,datetime.now(),message.guild))
    elif message.content == 'c! admin Ex1':
        await message.channel.send('Bot Experiment Succesfully!')
        print(' [Collot Bot ] {0} query "c! : admin Ex1" in {1} at {2} in server {3}'.format(message.author,message.channel,datetime.now(),message.guild))
    elif message.content == 'c! admin logout':
        print(' [Collot Bot ] {0} query "c! : admin logout" in {1} at {2} in server {3}'.format(message.author,message.channel,datetime.now(),message.guild))
        await message.channel.send('Shutdown Bot Succesfully')
        await bot.logout()
    await bot.process_commands(message)

bot.run('Token') 
