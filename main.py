import discord
import discord.utils
from discord.ext import tasks, commands
import datetime

import os

from dotenv import load_dotenv
load_dotenv()

# Your bot token
TOKEN = os.getenv("DISCORD_TOKEN")

# Channel ID where you want the message to be posted
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Intents allow your bot to access specific information and events
intents = discord.Intents.default()
intents.message_content = True  # Needed to access the message content
intents.reactions = True  # Needed to handle reactions

# Bot instance
bot = commands.Bot(command_prefix='!', intents=intents)


# React emoji for attendance
ATTENDANCE_EMOJI = '✅'

WEDNESDAY = 2
SUNDAY = 6

def get_day_message():
    today = datetime.datetime.now()
    current_day = today.weekday()

    if current_day <= WEDNESDAY:
        game_day = today + datetime.timedelta(days = WEDNESDAY - current_day)
        formatted_date = game_day.strftime('%d-%m-%Y')

        return f"Ketä tulossa peli-iltaan Lategameen {formatted_date}? ✅"
    elif current_day <= SUNDAY:
        game_day = today + datetime.timedelta(days = SUNDAY - current_day)
        formatted_date = game_day.strftime('%d-%m-%Y')

        return f"Ketä tulossa peli-iltaan Konttoriin {formatted_date}? ✅"

    return ""


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    schedule_meeting_message.start()  # Starts the recurring task when the bot is ready

async def send_message(channel):
    msg_content = get_day_message()

    msg = await channel.send(msg_content)
    await msg.add_reaction(ATTENDANCE_EMOJI)

    schedule_meeting_message.msg_id = msg.id


@tasks.loop(hours=24)  # This checks every 24 hours
async def schedule_meeting_message():
    # Get current day of the week (0 = Monday, 1 = Tuesday, ..., 6 = Sunday)
    current_day = datetime.datetime.now().weekday()
    channel = bot.get_channel(CHANNEL_ID)

    if channel is None:
        channel = await bot.fetch_channel(CHANNEL_ID)

    if channel is None:
        print("No channel found!")
        return

    # Post only on tuesdays and saturdays
    if current_day == WEDNESDAY - 1 or current_day == SUNDAY - 1:
        await send_message(channel)
    else:
        print("Wrong day to post!")

@bot.command(name='meeting')
async def manual_meeting_message(ctx):
    await send_message(ctx.channel)


async def fetch_members(channel, id_list):
    members = channel.guild.members
    found_members = list(filter(lambda x: x.id in id_list, members))

    if len(found_members) == len(id_list):
        return found_members

    await channel.guild.query_members(user_ids=id_list, cache=True)

    return list(filter(lambda x: x.id in id_list, channel.guild.members))

async def update_attendee_list(channel):
    msg = await channel.fetch_message(schedule_meeting_message.msg_id)

    reaction = next(x for x in msg.reactions if x.emoji == ATTENDANCE_EMOJI)
    users = [user async for user in reaction.users() if user.id != bot.user.id]
    members = await fetch_members(channel, list(map(lambda x: x.id, users)))
    attendees = list(map(lambda x: x.nick if x.nick is not None else x.display_name, members))

    msg_content = get_day_message()

    if len(attendees) > 0:
        msg_content += "\n\nTulijat:\n"
        msg_content += "\n".join(attendees)

    await msg.edit(content=msg_content)

@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user:  # Ignore the bot's own reactions
        return

    if str(reaction.emoji) != ATTENDANCE_EMOJI:
        return

    if reaction.message.id != schedule_meeting_message.msg_id:
        return

    await update_attendee_list(reaction.message.channel)

@bot.event
async def on_raw_reaction_remove(payload):
    if str(payload.emoji) != ATTENDANCE_EMOJI:
        return

    if payload.message_id != schedule_meeting_message.msg_id:
        return

    channel = bot.get_channel(payload.channel_id)
    await update_attendee_list(channel)


# Run the bot with the token
bot.run(TOKEN)
