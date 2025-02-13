import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import sqlite3
from datetime import datetime
import schedule
import time
import threading
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
REMINDER_CHANNEL_ID = int(os.getenv('REMINDER_CHANNEL_ID'))

intents = discord.Intents.default()
intents.message_content = True

# to run commands with the bot, command prefix is !:
bot = commands.Bot(command_prefix='!', intents=intents)

db = sqlite3.connect('room_requests.db') # title of db
cursor = db.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    location TEXT,
    date TEXT,
    from_time TEXT,
	to_time TEXT,
    status TEXT DEFAULT 'Pending'
)
''')
db.commit()

class RoomRequestModal(Modal):
	def __init__(self):
		super().__init__(title="Room Request from Pookies!")

		self.location = TextInput(label="Preferred Location", placeholder="Enter which library you prefer", min_length=3, max_length=50)
		self.date = TextInput(label="Date", placeholder="Enter the date (MM-DD-YYYY)", min_length=10, max_length=10)
		self.from_time = TextInput(label="From", placeholder="Enter the start time (HH:MM)", min_length=5, max_length=5)
		self.to_time = TextInput(label="To", placeholder="Enter the end time (HH:MM)", min_length=5, max_length=5)

		self.add_item(self.location)
		self.add_item(self.date)
		self.add_item(self.from_time)
		self.add_item(self.to_time)
	
	async def on_submit(self, interaction: discord.Interaction):
		try:
			datetime.strptime(self.date.value, '%m-%d-%Y')
			datetime.strptime(self.from_time.value, '%H:%M')
			datetime.strptime(self.to_time.value, '%H:%M')

			cursor.execute('''
			INSERT INTO requests (user_id, location, date, from_time, to_time)
			VALUES (?, ?, ?, ?, ?)
			''', (interaction.user.id, self.location.value, self.date.value, self.from_time.value, self.to_time.value))

			db.commit()
			await interaction.response.send_message(f"Room request received for **{self.location.value}** on **{self.date.value}** at **{self.from_time.value}-{self.to_time.value}** by {interaction.user.mention}.",
			ephemeral=True)

			channel = interaction.channel

			button = Button(label="Mark as Booked", style=discord.ButtonStyle.green)

			async def button_callback(interaction: discord.Interaction):
				cursor.execute('SELECT user_id, location, date, from_time, to_time FROM requests WHERE id = (SELECT id FROM requests ORDER BY id DESC LIMIT 1)')
				result = cursor.fetchone()

				if result:
					user_id, location, date, from_time, to_time = result
					await channel.send(
						f"✅ **Ew you love your friends?! Room booked ig...**\n"
						f"- **Preferred Location:** {location}\n"
						f"- **Date:** {date}\n"
						f"- **Time:** {from_time}-{to_time}\n"
						f"- **Completed by:** {interaction.user.mention}\n"
						f"- **Requested By:** <@{user_id}>"
					)
				
					cursor.execute('DELETE FROM requests WHERE id = (SELECT id FROM requests ORDER BY id DESC LIMIT 1)')
					db.commit()

					await interaction.response.send_message(
						f"Request has been successfully marked as completed and removed.", ephemeral=True
					)
			
			button.callback = button_callback
			view = View()
			view.add_item(button)

			await channel.send(
				embed=discord.Embed(
					title="Fellow Meow Meow In Need!",
					description=
						f"**Location: **{self.location.value}\n"
						f"**Date: **{self.date.value}\n"
						f"**Time: **{self.from_time.value}-{self.to_time.value}\n"
						f"**Requested By: **{interaction.user.mention}",
					color=discord.Color.blue()
				), view=view
			)

		except ValueError as e:
			print(f"error: {e}")
			await interaction.response.send_message('Can you even read bro? Invalid date or time format. Please use MM-DD-YYYY and HH:MM format. Try again', ephemeral=True)

class RoomRequestButtonView(View):
    def __init__(self):
        super().__init__()
        button = Button(label="Exploit ur gay friends", style=discord.ButtonStyle.primary)
        button.callback = self.button_callback
        self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RoomRequestModal())

# to request room, command is !request location date time:
@bot.command()
async def request(ctx):
	view = RoomRequestButtonView()
	await ctx.send("You need a room!!!!! loser... fill out form below...pls <3", view=view, delete_after=8)
	

# to view all requests, command is !view_requests:
@bot.command()
async def view_requests(ctx):
	cursor.execute('SELECT id, user_id, location, date, from_time, to_time, status FROM requests WHERE status = "Pending"')
	requests = cursor.fetchall()

	if not requests:
		await ctx.send("No pending room requests.")
		return
	
	for request in requests:
		request_id, user_id, location, date, from_time, to_time, status = request
	
	embed = discord.Embed(title=f"Desperate freak alert #{request_id}", color=discord.Color.blue())
	embed.add_field(name="Location", value=location, inline=True)
	embed.add_field(name="Date", value=date, inline=True)
	embed.add_field(name="From", value=from_time, inline=True)
	embed.add_field(name="To", value=to_time, inline=True)
	embed.add_field(name="Requested By", value=f"<@{user_id}>", inline=False)
	embed.add_field(name="Status", value=status, inline=False)

	button = Button(label="Mark as Booked", style=discord.ButtonStyle.green)

	async def button_callback(interaction: discord.Interaction):
		cursor.execute('SELECT location, date, from_time, to_time FROM requests WHERE id = ?', (request_id,))
		result = cursor.fetchone()

		if result:
			location, date, from_time, to_time = result
			await ctx.channel.send(
				f"✅ **Ew you love your friends?! Room booked ig...**\n"
                f"- **Location:** {location}\n"
                f"- **Date:** {date}\n"
                f"- **Time:** {from_time}-{to_time}\n"
                f"- **Completed by:** {interaction.user.mention}"
            )

			cursor.execute('DELETE FROM requests WHERE id = ?', (request_id,))
			db.commit()

			await interaction.response.send_message(
                f"Request ID {request_id} has been successfully marked as completed and removed.", 
                ephemeral=True
            )
	
	button.callback = button_callback

	view = View()
	view.add_item(button)
	await ctx.send(embed=embed, view=view)

async def send_reminders():
	channel = bot.get_channel(REMINDER_CHANNEL_ID)
	if not channel:
		return("Channel not found")
	
	cursor.execute(
		'''SELECT id, user_id, location, date, from_time, to_time FROM requests'''
	)

	requests = cursor.fetchall()

	reminder_messages = []
	tomorrow = datetime.now().date() + timedelta(days=1)

	for request in requests:
		request_id, user_id, location, date, from_time, to_time = request
		request_date = datetime.strptime(date, '%m-%d-%Y').date()

		if request_date == tomorrow:
			reminder_messages.append(
				f"🚨 **Reminder:** Room request still open at **{location}** for tomorrow!!!\n"
				f"- **Time:** {from_time}-{to_time}\n"
				f"- **Requested By:** <@{user_id}>"
			)
	
	if reminder_messages:
		await channel.send("\n\n".join(reminder_messages))

def delete_old_reqs():
	yesterday = (datetime.now() - timedelta(days=1)).strftime('%m-%d-%Y')
	cursor.execute('DELETE FROM requests WHERE date <= ?', (yesterday,))
	db.commit()

def schedule_tasks():
	schedule.every().day.at("10:00").do(lambda: asyncio.run_coroutine_threadsafe(send_reminders(), bot.loop))
	schedule.every().day.at("01:00").do(delete_old_reqs)

	while True:
		schedule.run_pending()
		time.sleep(3600)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    threading.Thread(target=schedule_tasks, daemon=True).start()

bot.run(TOKEN)