
import discord
from discord import voice_client
from discord import guild
from discord import channel

from discord.utils import get
from discord import FFmpegPCMAudio
from youtube_dl import YoutubeDL

from discord import client
from discord import embeds
from discord.ext import commands
from datetime import date, datetime, timedelta

from discord import message

# wrapper / decorator

hi = datetime.now()
s1 = datetime.now()
test = datetime.now()

bot = commands.Bot(command_prefix='c!',help_command=None)

@bot.event
async def on_ready():
    print(f"Logged in as ID {bot.user}")

@bot.command()
async def help(ctx):
    emBed = discord.Embed(title="Collot's Assisstant - Help", description="All available bot commands", color=0x42f5a7)
    emBed.add_field(name="help", value="Get help command", inline=False)
    emBed.add_field(name="test", value="Test bot command", inline=False)
    emBed.add_field(name="type <text>", value="Respond your message that you've send", inline=False)
    emBed.set_thumbnail(url='https://static.wikia.nocookie.net/beastars-eng/images/b/bc/Collot_%28Anime%29.png/revision/latest/scale-to-width-down/259?cb=20190806180535')
    emBed.set_footer(text='Collot assistant written by Harrieszt Laboratories', icon_url='https://lh3.googleusercontent.com/yrGY7kZHEl14w44X_J1qXa1gSE9PstWggz7bEy6jdi9wNd5XQd2xMXHjNJ4I9Qe5_9Ae0k3oQbhaaqpQ1CJX-OgU6yB4YJlIOjVdYw2jpEX5BxQ4JwVwi3h0t3iONBQo4dOdC-sUgMdiiVP2Q2y_YdTYrmVw06GVqdpNvWGxQuKxikZyb9ZAgQbTB4CmfANR_wUGGqHdica0G2aCLbAFdsr-J0NGeA1PPgQkxT-Zian6x-RjKhiJ1DnKW46F1fY522tobOf3wWmsjQks797cuLb-K0SSsKJ7XYMXxlIjkdUazaIiW2WwKyU-AXXDhOMdh5xSUS1dXV7CdHUPtxpqDRn7kDeA362F4SEzkmGGTViMoKtFpwTFiQrp5gpoN8GUS0Ub42UTH3u6KDzoDDef49qzLEIuUnngtYom6XarI-yP2IRqkjRiM149RzpDWALg3IEVk4ygYRC8CPdYxMNfJUjb_1ePshJDF_XxoHvXLeuqO0FRz9PgRxBv-1SMgZ-aD1YtMrlSQ9uIsxVxHrIHxHNJA3Q7RdQA19_fAv7H2KvOHyu9munirm-Jnb5padRjROVj4tEF00SwVcpWBd_RFb5bFn-W5KjhWwOGYzz6cBpn7tgyYOFbbiLv5yB20IaMsAWLCHDo2fU2ZHFpXYQdcxwQKEALDEWv1ZrKgHrifIgWp7eOmEasiyStIJsFNkAXYs0AGCVNIQ8WzMAbzwO9ZIjwsA=s490-no?authuser=0')
    await ctx.channel.send(embed=emBed)
    print(ctx.channel)

@bot.command()
async def test(ctx):
    global test
    test = datetime.now() + timedelta(seconds=2)
    await ctx.channel.send("Experiment Succesfully!")
    print('{0} query "c! : test" in {1} at {2} in server {3}'.format(ctx.author,ctx.channel,datetime.now(),ctx.guild))

@bot.command()
async def type(ctx, *, par):
    await ctx.channel.send("Your message is {0}".format(par))
    print(ctx.channel)
    print('{0} query "c! : type" in {1} at {2} in server {3}'.format(ctx.author,ctx.channel,datetime.now(),ctx.guild))

@bot.command()
async def join(ctx):
    channel = ctx.author.voice.channel
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    await channel.connect()
    print('{0} query "c! : join" in {1} at {2} in server {3}'.format(ctx.author,ctx.channel,datetime.now(),ctx.guild))

@bot.command()
async def leave(ctx):
    await ctx.voice_client.disconnect()
    print('{0} query "c! : leave" in {1} at {2} in server {3}'.format(ctx.author,ctx.channel,datetime.now(),ctx.guild))

@bot.command()
async def play(ctx, url):
    channel = ctx.author.voice.channel
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    await channel.connect()
    if voice_client == None :
        ctx.channel.send("Joined")
        await channel.connect()
        voice_client = get(bot.voice_clients, guild=ctx.guild)
        

    YDL_OPTIONS = {'format' : 'bestaudio', 'noplaylist' : 'True'}
    FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

    if not voice_client.is_playing() :
        with YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
        URL = info['formats'][0]['url']
        voice_client.play(discord.FFmpegPCMAudio(URL, **FFMPEG_OPTIONS))
        voice_client.is_playing()
    else :
        await ctx.channel.send("Already playing song")
        return
    print('{0} query "c! : play" in {1} at {2} in server {3}'.format(ctx.author,ctx.channel,datetime.now(),ctx.guild))



@bot.event
async def on_message(message):
    global hi
    if message.content == 'Hi' and datetime.now() >= hi:
        hi = datetime.now() + timedelta(seconds=2)
        await message.channel.send(' Hello, ' + str(message.author.name))
        print('{0} query "c! : hi" at {1} and can use this command again in {2}'.format(message.author,datetime.now(),hi))
    elif message.content == 'c! admin cmd':
        await message.channel.send('Type "c! admin logout" to shutdown this bot')
        print('{0} query "c! : admin cmd" in {1} at {2} in server {3}'.format(message.author,message.channel,datetime.now(),message.guild))
    elif message.content == 'c! admin Ex1':
        await message.channel.send('Bot Experiment Succesfully!')
        print('{0} query "c! : admin Ex1" in {1} at {2} in server {3}'.format(message.author,message.channel,datetime.now(),message.guild))
    elif message.content == 'c! admin logout':
        print('{0} query "c! : admin logout" in {1} at {2} in server {3}'.format(message.author,message.channel,datetime.now(),message.guild))
        await message.channel.send('Shutdown Bot Succesfully')
        await bot.logout()
    await bot.process_commands(message)

bot.run('token') 