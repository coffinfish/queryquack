# discord modules
from discord.ext import commands
from discord import app_commands
import discord
import os
from dotenv import load_dotenv
import pdfreaderclass as pr

load_dotenv()

# discord bot
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

# changing the headline in the help command
help_command = commands.DefaultHelpCommand(
    no_category = 'Commands'
)

bot = commands.Bot(intents = intents, command_prefix = "!", help_command=help_command)

# instantiating the pdfreaderclass
queryquack = pr.pdfreaderclass("cohere-pinecone")

@bot.command(name="load", help = "!load [namespace] - Will load the PDF file that is attached to be queried in a namespace. QueryQuack will query PDFs in the same namespace, if no namespace is given, a new namespace will be generated or the latest namespace will be used.")
async def getPDF(ctx, arg1 = "default"):
    attachments = ctx.message.attachments
    message = await ctx.send("Loading File. Please wait a moment!")
    if (len(attachments) == 0):
        await message.edit(content = "No File Attached! Please attach a pdf file")
    elif (attachments[0].content_type != "application/pdf"):
        await message.edit(content = "Unknown File Type! Please attach a pdf file")
    else:
        await attachments[0].save(fp = f"./data/{attachments[0].filename}")
        queryquack.loadPDF(attachments[0].filename, arg1)
        await message.edit(content = "Successfully loaded!")

@bot.command(name="ask", help = "!ask [prompt]- Requires a pdf to be loaded beforehand.")
async def askPDF(ctx, *, args):
    message = await ctx.send("Fetching answer. Please wait a moment!")
    answer = queryquack.ask(args)
    await message.edit(content = answer["output_text"])

@bot.command(name="clearPDFs", help = "!clearPDF - Will clear all the pdfs in storage. Warning! It will not clear the Namespace.")
async def clearPDF(ctx):
    message = await ctx.send("Clearing PDF files. Please wait a moment!")
    await message.edit(content = queryquack.clearPDFs())

@bot.command(name="clearNamespace", help = "!clearNamespace [namespace*] - Deletes and clears out the given namespace name")
async def clearNamespace(ctx, arg):
    message = await ctx.send("Clearing Namespace. Please wait a moment!")
    await message.edit(content = queryquack.clearNamespace(arg))

@bot.command(name="listNamespaces", help = "!listNamespaces - Will list all namespaces")
async def listNamespaces(ctx):
    await ctx.send("**List Of Namespaces:\n**" +"\n".join(list(queryquack.namespaceDict.keys())) if (len(queryquack.namespaceDict) != 0 ) else "No Namespaces to list!")

@bot.command(name="listPDFs", help = "!listPDFs - Will list pdfs currently saved in the data folder")
async def listPDFs(ctx):
    await ctx.send("**List of PDFs:**\n" + "\n".join(os.listdir("data/")) if (len(os.listdir("data/")) != 0) else "No PDFs to list!")

@bot.command(name="setNamespace", help = "!setNamespace [namespace] - Set the namespace to query from")
async def setNamespace(ctx,arg1):
    queryquack.setCurrentNamespace(arg1)
    await ctx.send("Successfully set current Namespace to "+ arg1)

@bot.command(name="quit", help = "!quit - Closes the bot")
async def quit(ctx):
    await ctx.send("Quack! Goodbye!")
    await bot.close()

@bot.command(name="about", help = "!about - Learn how to get started.")
async def about(ctx):
    await ctx.send(
"""**I'm QueryQuack!**

__About Me:__
Upload a PDF document then ask me anything about it! I'll do my best to answer. 
I was created by Nina and Cindy using CoHere, LangChain, Pinecone, and discord.py for 
2023 MetHacks!

__How To Use:__
In your message, type "!load" and attach a pdf file. If you want to keep your pdf files
in separate Namespaces (think of Namespaces as folders), you can specify it by "!load [name of Namespace]".
If there is no name, the Namespace will be called 'default'

Then, after it has finished loading, you can type "!ask [prompt]" and I will respond! I will always refer to
latest namespace that was referenced.

!help for more available commands.""")

@bot.event
async def on_command_error(ctx, error, **kwargs):
    if isinstance(error, commands.errors.CommandNotFound):
        await ctx.reply("Command not found! Do !help to see a list of commands")
    elif isinstance(error, commands.errors.UserInputError):
        await ctx.reply("Invalid arguments: Please check !help to see the available arguments")
    else:
        await ctx.reply(error)

@bot.event
async def on_disconnect():
    queryquack.clearPDFs()
    for k in list(queryquack.namespaceDict.keys()):
        queryquack.clearNamespace(k)

@bot.event
async def on_connect():
    queryquack.loadPDFs()


bot.run(TOKEN)
