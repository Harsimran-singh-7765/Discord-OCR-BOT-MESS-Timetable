import discord
from discord.ext import commands
import pytesseract
from PIL import Image
import requests
from io import BytesIO
import json
import os
from github import Github
import re
from datetime import datetime

# Hardcoded tokens (temporary)
TOKEN = "MTM1NTQ0ODgxNTkyNjExNjQxMg.GykAjD.3XHYFFBYaw14753Xzh3A1SpD6cGsdfDvcxKV6k"
GITHUB_TOKEN = "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"
REPO_NAME = "Harsimran-singh-7765/JIIT-MESS-SCHEDULE"
FILE_PATH = "timetable.ts"

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user.name} is ready!")

@bot.command()
async def timetable(ctx):
    await ctx.send("📸 Please send an image of the mess schedule.")

    def check(m):
        return m.author == ctx.author and m.attachments

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)
        image_url = msg.attachments[0].url
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))

        extracted_text = pytesseract.image_to_string(img)
        
        await ctx.send("🔍 Processing the image...")
        
        formatted_timetable = format_timetable(extracted_text)
        
        preview = json.dumps(formatted_timetable, indent=2)[:1500]
        await ctx.send(f"📝 Formatted Data Preview:\n```json\n{preview}\n...```")

        ts_content = generate_typescript_content(formatted_timetable)
        
        success = push_to_github(ts_content)
        if success:
            await ctx.send("✅ Mess schedule successfully updated on GitHub!")
        else:
            await ctx.send("❌ Failed to update GitHub. Please check the logs.")

    except Exception as e:
        await ctx.send(f"⚠️ Error: {str(e)}")

def format_timetable(text):
    """
    Converts OCR text into structured timetable format.
    """
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    meals = ["Breakfast", "Lunch", "Dinner"]
    timetable = {}
    
    # Initialize the structure for all days
    for day in days:
        timetable[day] = {
            "breakfast": "",
            "lunch": "",
            "dinner": ""
        }
    
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    current_day = None
    current_meal = None
    menu_items = []
    
    for line in lines:
        # Skip empty lines and headers
        if not line or "JIIT" in line or "Menu" in line or "Day" in line or "Annapurna" in line:
            continue
            
        # Check for day
        day_found = False
        for day in days:
            if day.lower() in line.lower():
                current_day = day
                day_found = True
                break
        if day_found:
            continue
            
        # Check for meal type
        meal_found = False
        for meal in meals:
            if meal.lower() in line.lower():
                current_meal = meal.lower()
                meal_found = True
                break
        
        # If line contains menu items
        if current_day and current_meal and not meal_found:
            # Clean up the line
            line = re.sub(r'\d{2}\.\d{2}\.\d{2}', '', line)  # Remove dates
            line = re.sub(r'breakfast|lunch|dinner', '', line.lower(), flags=re.IGNORECASE)  # Remove meal names
            line = line.strip(' ,-')  # Remove extra characters
            
            # Split items and clean them
            items = [item.strip() for item in re.split(r'[,.]', line) if item.strip()]
            
            # Only process if we have actual menu items
            if items and not any(day.lower() in line.lower() for day in days):
                current_items = timetable[current_day][current_meal]
                if current_items:
                    # Append new items to existing ones
                    timetable[current_day][current_meal] = current_items + ", " + ", ".join(items)
                else:
                    # Set initial items
                    timetable[current_day][current_meal] = ", ".join(items)

    return timetable

def generate_typescript_content(timetable_data):
    """
    Converts the timetable data into TypeScript format.
    """
    # Clean up empty strings
    for day in timetable_data:
        for meal in timetable_data[day]:
            if not timetable_data[day][meal]:
                timetable_data[day][meal] = "Not specified"
    
    ts_object = json.dumps(timetable_data, indent=2)
    
    ts_content = """export interface WeeklyTimetable {
  [key: string]: {
    breakfast: string;
    lunch: string;
    dinner: string;
  };
}

export const timetableData: WeeklyTimetable = """ + ts_object + ";"
    
    return ts_content

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
            repo.update_file(
                FILE_PATH,
                f"Updated mess schedule - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                content,
                contents.sha
            )
        except Exception as e:
            repo.create_file(
                FILE_PATH,
                f"Initial mess schedule upload - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                content
            )
        return True
    except Exception as e:
        print(f"GitHub Error: {e}")
        return False

if __name__ == "__main__":
    if not TOKEN:
        print("Error: Discord token not found in environment variables!")
    else:
        bot.run("MTM1NTQ0ODgxNTkyNjExNjQxMg.GykAjD.3XHYFFBYaw14753Xzh3A1SpD6cGsdfDvcxKV6k")
