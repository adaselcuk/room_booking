import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import sqlite3
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

# to run commands with the bot, command prefix is !:
bot = commands.Bot(command_prefix='!', intents=intents)

db = sqlite3.connect('room_requests.db') # title of db
cursor = db.cursor()

cursor.execute('''
DROP TABLE IF EXISTS requests;
''')

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

		self.location = TextInput(label="Location", placeholder="Enter which library you prefer", min_length=3, max_length=50)
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
			await channel.send(
				embed=discord.Embed(
					title="Fellow Homo In Need!",
					description=
						f"**Location: **{self.location.value}\n"
						f"**Date: **{self.date.value}\n"
						f"**Time: **{self.from_time.value}-{self.to_time.value}\n"
						f"**Requested By: **{interaction.user.mention}",
					color=discord.Color.green()
				)
			)

		except ValueError as e:
			print(f"error: {e}")
			await interaction.response.send_message('Invalid date or time format. Please use MM-DD-YYYY and HH:MM format.', ephemeral=True)

class RoomRequestButtonView(View):
    def __init__(self):
        super().__init__()
        button = Button(label="Call ur gay friends to the rescue", style=discord.ButtonStyle.primary)
        button.callback = self.button_callback
        self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RoomRequestModal())

# to request room, command is !request location date time:
@bot.command()
async def request(ctx):
	view = RoomRequestButtonView()
	await ctx.send("You need a room!!!!! loser... fill out form below... freak....", view=view, delete_after=5)
	


# to view all requests, command is !view_requests:
@bot.command()
async def view_requests(ctx):
	cursor.execute('SELECT id, user_id, location, date, time, status FROM requests WHERE status = "Pending"')
	requests = cursor.fetchall()

	if not requests:
		await ctx.send("No pending room requests.")
		return
	
	for request in requests:
		request_id, user_id, location, date, time, status = request
	
	embed = discord.Embed(title=f"Room Request #{request_id}", color=discord.Color.blue())
	embed.add_field(name="Location", value=location, inline=True)
	embed.add_field(name="Date", value=date, inline=True)
	embed.add_field(name="Time", value=time, inline=True)
	embed.add_field(name="Requested By", value=f"<@{user_id}>", inline=False)
	embed.add_field(name="Status", value=status, inline=False)

	button = Button(label="Mark as Completed", style=discord.ButtonStyle.green)

	async def button_callback(interaction: discord.Interaction):
		cursor.execute('SELECT location, date, time FROM requests WHERE id = ?', (request_id,))
		result = cursor.fetchone()

		if result:
			location, date, time = result
			await ctx.channel.send(
				f"✅ **Room request completed!**\n"
                f"- **Location:** {location}\n"
                f"- **Date:** {date}\n"
                f"- **Time:** {time}\n"
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

bot.run(TOKEN)