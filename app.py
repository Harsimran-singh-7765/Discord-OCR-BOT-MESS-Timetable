import discord
from discord.ext import commands
import pytesseract
from PIL import Image
import requests
from io import BytesIO
import json
import os
from github import Github

# Load tokens from environment variables for security
TOKEN = "MTM1NTQ0ODgxNTkyNjExNjQxMg.GWoDpa.-2l173_qnlmbyYgMzFmTPwJ7c67xKVCksLQ8dk"
GITHUB_TOKEN = "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"
REPO_NAME = "Harsimran-singh-7765/JIIT-MESS-SCHEDULE"
FILE_PATH = "timetable.ts"

# Discord bot setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user.name} is ready!")

@bot.command()
async def timetable(ctx):
    await ctx.send("📸 Please send an image of the timetable.")

    def check(m):
        return m.author == ctx.author and m.attachments

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)
        image_url = msg.attachments[0].url
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))

        # OCR Processing
        extracted_text = pytesseract.image_to_string(img)
        formatted_timetable = format_timetable(extracted_text)

        # Send extracted text preview
        await ctx.send(f"📝 Extracted Text:\n```\n{extracted_text[:1000]}\n...```")

        # Push to 
        print("🔍 Formatted Timetable Output:\n", formatted_timetable)

        success = push_to_github(formatted_timetable)
        if success:
            await ctx.send("✅ Timetable successfully updated on GitHub!")
        else:
            await ctx.send("❌ Failed to update GitHub. Check logs.")

    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")

def format_timetable(text):
    """
    Converts OCR text into structured timetable format.
    """
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    timetable = {}
    current_day = None

    for line in text.split("\n"):
        line = line.strip()
        if any(day in line for day in days):
            current_day = next(day for day in days if day in line)
            timetable[current_day] = {"breakfast": "", "lunch": "", "dinner": ""}
        elif current_day:
            meal_types = ["breakfast", "lunch", "dinner"]
            for meal in meal_types:
                if meal in line.lower():
                    timetable[current_day][meal] = line.split(":", 1)[-1].strip()

    # Convert to the required format
    timetable_js = f"export const timetableData: WeeklyTimetable = {json.dumps(timetable, indent=2)};"
    return timetable_js

def push_to_github(content):
    """
    Pushes the formatted timetable data to GitHub.
    """
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)

        try:
            # Try to get the file if it exists
            contents = repo.get_contents(FILE_PATH)
            repo.update_file(FILE_PATH, "Updated timetable", content, contents.sha)
        except:
            # If file does not exist, create it
            repo.create_file(FILE_PATH, "Initial timetable upload", content)

        return True
    except Exception as e:
        print(f"GitHub Error: {e}")
        return False

bot.run(TOKEN)
