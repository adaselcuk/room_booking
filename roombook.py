import discord
from discord.ext import commands
from discord.ui import Button, View
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
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    location TEXT,
    date TEXT,
    time TEXT,
    status TEXT DEFAULT 'Pending'
)
''')
db.commit()

# to request room, command is !request location date time:
@bot.command()
async def request(ctx, location: str, date: str, time: str):
	try:
		datetime.strptime(date, '%m-%d-%Y')
		datetime.strptime(time, '%H:%M')

		cursor.execute('''
		INSERT INTO requests (user_id, location, date, time)
		VALUES (?, ?, ?, ?)
		''', (ctx.author.id, location, date, time))

		db.commit()
		await ctx.send(f"Room request received for **{location}** on **{date}** at **{time}** by {ctx.author.mention}.")
	except ValueError:
		await ctx.send('Invalid date or time format. Please use DD-MM-YYYY and HH:MM format.')
	except Exception as e:
		await ctx.send(f'An error occurred: {e}')


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