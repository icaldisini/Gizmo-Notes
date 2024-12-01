from flask import Flask
from threading import Thread
import discord
from discord.ext import commands
from discord.utils import get
import asyncio
import requests, certifi
from dotenv import load_dotenv
import os
from fpdf import FPDF
import csv
from datetime import datetime

# Load environment variables
load_dotenv()

FLASK_SERVER_URL = os.getenv("FLASK_SERVER_URL")
FLASK_API_URL = os.getenv("FLASK_API_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")
personal_bot = os.getenv("personal_bot_link")

if not BOT_TOKEN:
    raise ValueError("Bot token is missing! Please check your .env file.")

# Flask App
app = Flask(__name__)

@app.route("/")
def home():
    return "Hello from Flask!"

def run_flask():
    app.run(host="0.0.0.0", port=5000)

# Discord Bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Flask thread check
flask_thread_started = False

admins = {}
roles = {}
emails = {}
recording_status = False
recording_channel = None

@app.route('/api/bot_invite', methods=['GET'])
def bot_invite():
    invite_link = personal_bot
    return {"invite_link": invite_link}, 200

@bot.event
async def on_member_update(before, after):
    guild = after.guild
    channel_name = "bot_testing"  # Ganti dengan nama channel yang ingin Anda bersihkan

    # Temukan channel bot_testing
    channel = discord.utils.get(guild.text_channels, name=channel_name)
    if not channel:
        print(f"Channel **{channel_name}** tidak ditemukan!")
        return

    # Bersihkan semua pesan di channel
    try:
        await channel.purge()
        print(f"Pesan di channel **{channel_name}** telah dihapus.")
    except discord.Forbidden:
        print("Bot tidak memiliki izin untuk menghapus pesan.")
    except discord.HTTPException as e:
        print(f"Terjadi kesalahan saat menghapus pesan: {e}")

@bot.command()
async def clear(ctx):
    await ctx.channel.purge()
    await ctx.send("Channel telah dibersihkan!")

@bot.event
async def on_member_join(member):
    guild = member.guild
    channel_name = "bot_testing"  # Ganti dengan nama channel yang ingin Anda bersihkan

    # Temukan channel bot_testing
    channel = discord.utils.get(guild.text_channels, name=channel_name)
    if not channel:
        print(f"Channel **{channel_name}** tidak ditemukan!")
        return

    # Bersihkan semua pesan di channel
    try:
        await channel.purge()
        await channel.send(f"Selamat datang di server, {member.mention}! Channel telah dibersihkan.")
    except discord.Forbidden:
        print("Bot tidak memiliki izin untuk menghapus pesan.")
    except discord.HTTPException as e:
        print(f"Terjadi kesalahan saat menghapus pesan: {e}")

@bot.event
async def on_ready():
    global flask_thread_started
    print(f"Bot {bot.user} is ready!")
    if not flask_thread_started:
        flask_thread_started = True
        thread = Thread(target=run_flask)
        thread.start()

@bot.command()
async def hello(ctx):
    if isinstance(ctx.channel, discord.DMChannel):  # Command issued in DM
        await ctx.send(f"Hello, {ctx.author.display_name}!")
    else:  # Command issued in public channel
        await ctx.send(f"Hello, {ctx.author.display_name}!")
    
@bot.command()
async def ping(ctx):
    await ctx.send(
        "Hello! I am your personal bot. Here are the commands you can use:\n"
        "1. !ping: Test bot\n"
        "2. !create_gp <category_name> : Create default category and channel\n"
        "3. !add_gp <category_name> <channel_name> : Add channel to category\n"
        "4. !role : View role\n"
        "5. !pick_role <role_name> : Select role\n"
        "6. !change_role <@Username> <role_name> : Change role other member if you are Admin\n"
        "7. !add_meet <category _name> <voice_channel_name> : Create voice channel\n"
        "8. !start_record <channel_name> : Record activity in text channel\n"
        "9. !stop_record : Stop recording\n"
        "10. !convert_and_upload <channel_name> : Convert csv files record to pdf and upload to AnonFiles\n"
        "11. !get_record : Request the recording result\n"
        "12. !end_gp : <category_name> : Delete \n"
        "13. !clear : Clear history"
    )
    
@bot.command()
async def create_gp(ctx, category_name: str, *, default_channel_name: str = None):
    guild = ctx.guild
    author = ctx.author

    # Format nama kategori dan channel default
    formatted_category_name = category_name.strip()
    formatted_channel_name = default_channel_name.lower().replace(" ", "-") if default_channel_name else f"{formatted_category_name.lower().replace(' ', '-')}-projects"

    # Periksa apakah kategori sudah ada
    existing_category = discord.utils.get(guild.categories, name=formatted_category_name)
    if existing_category:
        await ctx.send(f"Category with named **{formatted_category_name}** is already!")
        return

    # Membuat kategori baru
    try:
        new_category = await guild.create_category(formatted_category_name)
        await ctx.send(f"Category with named**{new_category.name}** successfully created!")

        # Mengatur izin khusus untuk channel default
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),  # Semua anggota tidak bisa membaca
            author: discord.PermissionOverwrite(read_messages=True)  # Pembuat kategori bisa membaca
        }

        # Membuat channel default di dalam kategori baru
        new_channel = await guild.create_text_channel(
            formatted_channel_name, category=new_category, overwrites=overwrites
        )
        await ctx.send(
            f"Default Channel with named **{new_channel.name}** created successfully in Category named **{new_category.name}**!\n"
            f"Link: https://discord.com/channels/{guild.id}/{new_channel.id}"
        )
    except discord.Forbidden:
        await ctx.send("I don't have permission to create categories or channels!")
    except discord.HTTPException as e:
        await ctx.send(f"Something error: {e}")
            
@bot.command()
async def add_gp(ctx, category_name: str, *, channel_name: str):
    guild = ctx.guild
    author = ctx.author

    # Format nama kategori dan channel
    formatted_category_name = category_name.strip()
    formatted_channel_name = channel_name.lower().replace(" ", "-")

    # Temukan kategori berdasarkan nama
    category = discord.utils.get(guild.categories, name=formatted_category_name)
    if not category:
        await ctx.send(f"Category with named **{formatted_category_name}** not found!")
        return

    # Tentukan nama channel default (ini bisa disesuaikan dengan nama yang diberikan oleh pengguna)
    default_channel_name = f"{formatted_category_name.lower().replace(' ', '-')}-projects"  # Misalnya: gp-projects

    # Temukan channel default dalam kategori
    default_channel = discord.utils.get(category.text_channels, name=default_channel_name)

    # Pastikan perintah dijalankan di channel default
    if ctx.channel != default_channel:
        await ctx.send(f"This command can only be run on the default channel **{default_channel_name}**!")
        return

    # Cek apakah channel sudah ada dalam kategori
    existing_channel = discord.utils.get(category.channels, name=formatted_channel_name)
    if existing_channel:
        await ctx.send(f"Channel with named **{formatted_channel_name}** is already in Category Named **{category.name}**!")
        return

    # Membuat channel baru di dalam kategori
    try:
        new_channel = await guild.create_text_channel(formatted_channel_name, category=category)
        await ctx.send(f"Channel with named **{new_channel.name}** created successfully in Category named **{category.name}**!")
    except discord.Forbidden:
        await ctx.send("I don't have permission to create channels!")
    except discord.HTTPException as e:
        await ctx.send(f"Something error: {e}")
            
@bot.command()
async def link(ctx, *, category_name: str):
    guild = ctx.guild

    # Temukan kategori berdasarkan nama
    category = discord.utils.get(guild.categories, name=category_name)
    if not category:
        await ctx.send(f"Category with named **{category_name}** not found!")
        return

    # Dapatkan semua channel dalam kategori
    if category.channels:
        channel_links = [
            f"[{channel.name}](https://discord.com/channels/{guild.id}/{channel.id})"
            for channel in category.channels
        ]
        await ctx.send(
            f"Channel in Category **{category.name}**:\n" + "\n".join(channel_links)
        )
    else:
        await ctx.send(f"Category with named **{category.name}** not have channel!")
        
@bot.command()
async def role(ctx):
    guild = ctx.guild

    # Daftar role yang akan ditampilkan
    role_names = ["Admin", "Member", "Guest"]

    # Periksa apakah role-role tersebut ada di server
    available_roles = [role.name for role in guild.roles if role.name in role_names]
    if not available_roles:
        await ctx.send("Tidak ada role yang tersedia di server ini!")
        return

    # Kirim daftar role ke user
    await ctx.send(f"Role yang tersedia: {', '.join(available_roles)}")


@bot.command()
async def pick_role(ctx, *, role_name: str):
    guild = ctx.guild
    member = ctx.author

    # Periksa apakah role ada di server
    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        await ctx.send(f"Role **{role_name}** tidak ditemukan! Gunakan `!role` untuk melihat daftar role yang tersedia.")
        return

    # Periksa apakah user sudah memiliki role tersebut
    if role in member.roles:
        await ctx.send(f"Anda sudah memiliki role **{role_name}**!")
        return

    # Hapus role lain sebelum menambahkan role baru
    role_names = ["Admin", "Member", "Guest"]
    roles_to_remove = [r for r in member.roles if r.name in role_names]

    try:
        # Hapus role-role lama
        for old_role in roles_to_remove:
            await member.remove_roles(old_role)

        # Tambahkan role baru
        await member.add_roles(role)
        await ctx.send(f"Role Anda telah diperbarui menjadi **{role_name}**!")
    except discord.Forbidden:
        await ctx.send("Saya tidak memiliki izin untuk mengubah role Anda!")
    except discord.HTTPException as e:
        await ctx.send(f"Terjadi kesalahan: {e}")

@bot.command()
@commands.has_role("Admin")  # Hanya bisa dijalankan oleh user dengan role "Admin"
async def change_role(ctx, member: discord.Member, *, role_name: str):
    """Mengubah role anggota lain. Hanya untuk Admin."""
    guild = ctx.guild

    # Daftar role yang diizinkan
    allowed_roles = ["Admin", "Member", "Guest"]

    # Validasi role
    role = discord.utils.get(guild.roles, name=role_name)
    if not role or role_name not in allowed_roles:
        await ctx.send(f"Role **{role_name}** tidak valid! Role yang tersedia: {', '.join(allowed_roles)}")
        return

    # Periksa apakah member sudah memiliki role tersebut
    if role in member.roles:
        await ctx.send(f"Anggota **{member.display_name}** sudah memiliki role **{role_name}**!")
        return

    # Hapus role lama (jika ada) sebelum menambahkan role baru
    roles_to_remove = [r for r in member.roles if r.name in allowed_roles]

    try:
        # Hapus role lama
        for old_role in roles_to_remove:
            await member.remove_roles(old_role)

        # Tambahkan role baru
        await member.add_roles(role)
        await ctx.send(f"Role anggota **{member.display_name}** telah diubah menjadi **{role_name}** oleh **{ctx.author.display_name}**.")
    except discord.Forbidden:
        await ctx.send("Saya tidak memiliki izin untuk mengubah role anggota ini!")
    except discord.HTTPException as e:
        await ctx.send(f"Terjadi kesalahan: {e}")
        
@bot.command()
async def add_meet(ctx, category_name: str, *, voice_channel_name: str):
    guild = ctx.guild
    author = ctx.author

    # Format nama kategori dan voice channel
    formatted_category_name = category_name.strip()
    formatted_voice_channel_name = voice_channel_name.lower().replace(" ", "-")

    # Temukan kategori berdasarkan nama
    category = discord.utils.get(guild.categories, name=formatted_category_name)
    if not category:
        await ctx.send(f"Category with named **{formatted_category_name}** not found!")
        return

    # Tentukan nama channel default
    default_channel_name = f"{formatted_category_name.lower().replace(' ', '-')}-projects"  # Misalnya: gp-projects

    # Temukan channel default dalam kategori
    default_channel = discord.utils.get(category.text_channels, name=default_channel_name)

    # Pastikan perintah dijalankan di channel default
    if ctx.channel != default_channel:
        await ctx.send(f"This command can only be run on the default channel **{default_channel_name}**!")
        return

    # Cek apakah voice channel sudah ada dalam kategori
    existing_channel = discord.utils.get(category.voice_channels, name=formatted_voice_channel_name)
    if existing_channel:
        await ctx.send(f"Voice channel **{formatted_voice_channel_name}** is already in Category **{category.name}**!")
        return

    # Membuat voice channel baru di dalam kategori
    try:
        new_voice_channel = await guild.create_voice_channel(formatted_voice_channel_name, category=category)
        await ctx.send(f"Voice channel **{new_voice_channel.name}** created successfully in Category named **{category.name}**!")
    except discord.Forbidden:
        await ctx.send("I don't have permission to create voice channels!")
    except discord.HTTPException as e:
        await ctx.send(f"Something error: {e}")

@bot.command()
async def start_record(ctx, category_name: str, *, channel_name: str):
    guild = ctx.guild

    # Format nama kategori dan channel
    formatted_category_name = category_name.strip()
    formatted_channel_name = channel_name.lower().replace(" ", "-")

    # Temukan kategori berdasarkan nama
    category = discord.utils.get(guild.categories, name=formatted_category_name)
    if not category:
        await ctx.send(f"Category with named **{formatted_category_name}** not found!")
        return

    # Tentukan nama channel default
    default_channel_name = f"{formatted_category_name.lower().replace(' ', '-')}-projects"

    # Temukan channel default dalam kategori
    default_channel = discord.utils.get(category.text_channels, name=default_channel_name)

    # Validasi: Perintah hanya dijalankan di channel default
    if ctx.channel != default_channel:
        await ctx.send(f"This command can only be run on the default channel **{default_channel_name}**!")
        return

    # Simpan status perekaman
    global recording_status, recording_channel
    recording_status = True
    recording_channel = formatted_channel_name
    await ctx.send(f"Recording started for channel **{formatted_channel_name}** in category **{formatted_category_name}**.")

@bot.command()
async def stop_record(ctx, category_name: str, *, channel_name: str):
    guild = ctx.guild

    # Format nama kategori dan channel
    formatted_category_name = category_name.strip()
    formatted_channel_name = channel_name.lower().replace(" ", "-")

    # Temukan kategori berdasarkan nama
    category = discord.utils.get(guild.categories, name=formatted_category_name)
    if not category:
        await ctx.send(f"Category with named **{formatted_category_name}** not found!")
        return

    # Tentukan nama channel default
    default_channel_name = f"{formatted_category_name.lower().replace(' ', '-')}-projects"

    # Temukan channel default dalam kategori
    default_channel = discord.utils.get(category.text_channels, name=default_channel_name)

    # Validasi: Perintah hanya dijalankan di channel default
    if ctx.channel != default_channel:
        await ctx.send(f"This command can only be run on the default channel **{default_channel_name}**!")
        return

    # Hentikan perekaman
    global recording_status, recording_channel
    if recording_status and recording_channel == formatted_channel_name:
        recording_status = False
        recording_channel = None
        await ctx.send(f"Recording stopped for channel **{formatted_channel_name}** in category **{formatted_category_name}**.")
    else:
        await ctx.send("No recording is currently active.")

@bot.event
async def on_message(message):
    """Record messages if recording is active."""
    global recording_status, recording_channel

    # Abaikan pesan dari bot itu sendiri
    if message.author.bot:
        return

    # Rekam pesan jika perekaman aktif dan channel sesuai
    if recording_status and message.channel.name == recording_channel:
        filename = f"{recording_channel}_record.csv"
        with open(filename, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([message.author.name, message.content, message.created_at])

    await bot.process_commands(message)

@bot.command()
async def convert_and_upload(ctx, category_name: str, *, channel_name: str):
    guild = ctx.guild

    # Format nama kategori dan channel
    formatted_category_name = category_name.strip()
    formatted_channel_name = channel_name.lower().replace(" ", "-")

    # Temukan kategori berdasarkan nama
    category = discord.utils.get(guild.categories, name=formatted_category_name)
    if not category:
        await ctx.send(f"Category with named **{formatted_category_name}** not found!")
        return

    # Tentukan nama channel default
    default_channel_name = f"{formatted_category_name.lower().replace(' ', '-')}-projects"

    # Temukan channel default dalam kategori
    default_channel = discord.utils.get(category.text_channels, name=default_channel_name)

    # Validasi: Perintah hanya dijalankan di channel default
    if ctx.channel != default_channel:
        await ctx.send(f"This command can only be run on the default channel **{default_channel_name}**!")
        return

    # Konversi CSV ke PDF
    csv_filename = f"{formatted_channel_name}_record.csv"
    pdf_filename = f"{formatted_channel_name}_record.pdf"

    try:
        csv_to_pdf(csv_filename, pdf_filename)
    except FileNotFoundError:
        await ctx.send(f"CSV file `{csv_filename}` not found. Ensure recording was started for this channel.")
        return

    # Upload file PDF to AnonFiles
    result = upload_to_gofiles(pdf_filename)
    await ctx.send(result)

def csv_to_pdf(csv_filename, pdf_filename):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    #Set Title Column
    pdf.set_font("Arial", "B" ,size=12)
    pdf.cell(40, 10, "Author", border=1, align="C")
    pdf.cell(100, 10, "Content", border=1, align="C")
    pdf.cell(40, 10, "Timestamp", border=1, align="C")
    pdf.ln()
    
    #Set font
    pdf.set_font("Arial", "", 10)

    with open(csv_filename, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            author, content, timestamp = row
            
            try:
                timestamp_obj = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f+00:00")
                timestamp = timestamp_obj.strftime("%Y-%m-%d %H:%M:%S")  # Format yang lebih bersih
            except ValueError:
                pass
            
            content = content[:150] + '...' if len(content) > 150 else content  # Truncate jika terlalu panjang

            pdf.cell(40, 10, author, border=1, align="C")
            pdf.cell(100, 10, content, border=1, align="C")
            pdf.cell(40, 10, timestamp, border=1, align="C")
            pdf.ln()

    pdf.output(pdf_filename)

def upload_to_gofiles(filename):
    """Upload file to AnonFiles and return the link."""
    try:
        with open(filename, "rb") as f:
            response = requests.post("https://store1.gofile.io/uploadFile", files={"file": f}, verify=False)
            if response.status_code != 200:
                return f"Failed to upload. HTTP Status Code: {response.status_code}"
            
            data = response.json()
            if data["status"] == "ok":
                file_url = data["data"]["downloadPage"]
                return f"File uploaded successfully to GoFiles!\nLink: {file_url}"
            else:
                return f"Failed to upload file: {data.get('error', {}).get('message', 'Unknown error')}"
    except FileNotFoundError:
        return f"File `{filename}` not found!"
    except Exception as e:
        return f"An error occurred: {e}"
        
@bot.command()
async def end_gp(ctx, *, category_name: str):
    guild = ctx.guild
    category = discord.utils.get(guild.categories, name=category_name)
    if not category:
        await ctx.send(f"Category with named **{category_name}** not found!")
        return

    try:
        for channel in category.channels:
            await channel.delete()
        await category.delete()
        await ctx.send(f"Category **{category_name}** successfully deleted along with all channels in it!")
    except discord.Forbidden:
        await ctx.send("I don't have permission to delete categories or channels!")
    except discord.HTTPException as e:
        await ctx.send(f"Something error: {e}")

@bot.command()
async def get_invite(ctx):
    try:
        response = requests.get(f"{FLASK_SERVER_URL}/invite-bot")
        if response.status_code == 200:
            invite = response.json()
            await ctx.send(f"Here is your invite link: {invite['invite_link']}")
        else:
            await ctx.send("Failed to get invite link.")
    except Exception as e:
        await ctx.send(f"Error: {e}")

# Run the bot
bot.run(BOT_TOKEN)