import discord
from discord.ext import commands
import pytesseract
import cv2
import requests
import json
import numpy as np
import re
from io import BytesIO
from github import Github
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("REPO_NAME")
FILE_PATH = os.getenv("FILE_PATH")

# Initialize bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def preprocess_image(image):
    """Applies preprocessing techniques to enhance OCR accuracy."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # Convert to grayscale
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)  # Reduce noise
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)  # Adaptive thresholding
    return thresh

def extract_text_from_image(image):
    """Extracts text using Tesseract OCR with optimized settings."""
    processed_image = preprocess_image(image)
    
    # Custom OCR configurations (tuned for tabular text)
    custom_config = r'--oem 3 --psm 6'  # Use OCR Engine 3 and PSM 6 (Assumes uniform text)
    text = pytesseract.image_to_string(processed_image, lang='eng', config=custom_config)
    
    return text

def format_timetable(text):
    """Converts raw OCR text into structured JSON timetable."""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    meals = ["Breakfast", "Lunch", "Dinner"]
    timetable = {}
    
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    current_day = None

    for line in lines:
        for day in days:
            if day in line:
                current_day = day
                timetable[current_day] = {"breakfast": "", "lunch": "", "dinner": ""}
                break

        if current_day:
            meal_match = re.match(r"(Breakfast|Lunch|Dinner)[:-]?\s*(.*)", line, re.IGNORECASE)
            if meal_match:
                meal_type = meal_match.group(1).lower()
                meal_content = meal_match.group(2).strip()
                timetable[current_day][meal_type] = meal_content

    return timetable

def generate_typescript_content(timetable_data):
    """Converts extracted timetable into TypeScript format."""
    ts_object = json.dumps(timetable_data, indent=2)
    ts_content = """export interface WeeklyTimetable {
  [key: string]: {
    breakfast?: string;
    lunch?: string;
    dinner?: string;
  };
}
export const timetableData: WeeklyTimetable = """ + ts_object + ";"
    return ts_content

def push_to_github(content):
    """Pushes updated timetable to GitHub."""
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        try:
            contents = repo.get_contents(FILE_PATH)
            repo.update_file(
                FILE_PATH,
                f"Updated mess schedule - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                content,
                contents.sha
            )
        except Exception:
            repo.create_file(
                FILE_PATH,
                f"Initial mess schedule upload - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                content
            )
        return True
    except Exception as e:
        print(f"GitHub Error: {e}")
        return False

@bot.event
async def on_ready():
    print(f"{bot.user.name} is now online!")

@bot.command()
async def timetable(ctx):
    """Handles timetable extraction when user uploads an image."""
    await ctx.send("📸 Please send an image of the mess schedule.")

    def check(m):
        return m.author == ctx.author and m.attachments

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)
        image_url = msg.attachments[0].url
        response = requests.get(image_url)
        image_bytes = BytesIO(response.content)
        image = cv2.imdecode(np.frombuffer(image_bytes.read(), np.uint8), cv2.IMREAD_COLOR)

        extracted_text = extract_text_from_image(image)
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

if __name__ == "__main__":
    if not TOKEN:
        print("Error: Discord token not found in environment variables!")
    else:
        bot.run(TOKEN)
