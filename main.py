import discord
from discord.ext import tasks, commands
from discord import app_commands
from config import TOKEN, SFTP_HOST, SFTP_PORT, SFTP_USER, SFTP_PASSWORD, SFTP_REMOTE_PATH
import asyncio
import random
from datetime import datetime, timezone, timedelta, time
import json
import os
import io
import traceback
from PIL import Image, ImageDraw, ImageFont
import re
import aiohttp
import yaml
import paramiko
import time
import socket
from mcstatus import JavaServer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

# ==================== КОНСТАНТЫ ====================
LK_CHANNEL_ID = 1529937315890204836
VERIFY_CHANNEL_ID = 1529538303559205047
VERIFY_ROLE_ID = 1505240271200456864
UNVERIFIED_ROLE_ID = 1529537943663018045
VERIFY_MSG_FILE = "verify_msg.json"
APPLICATIONS_CHANNEL_ID = 1530237443767533748
ROLE_MAPPER = 1525487051544203395
ROLE_MODERATOR = 1505275521825771520
CHAT_MODERATOR_ROLE_ID = 1536729603522170961
ROLE_CINEMA = 1505250838053126345
ROLE_GIRL = 1505251541039321290
HIGHER_ROLES = [1526681612337549343, 1505438802653741096, 1530235500886102216, 1505235504826814535]
MSK = timezone(timedelta(hours=3))
WARNS_FILE = "warns.json"
SUPPORT_CONFIG_FILE = "support_config.json"
BADWORDS_FILE = "badwords.json"
REMINDERS_FILE = "reminders.json"
APPLICATIONS_CONFIG_FILE = "applications_config.json"
MARRIAGES_FILE = "marriages.json"
BIRTHDAYS_FILE = "birthdays.json"
CREATOR_AND_ROLE_IDS = [1437779380184158249, 1001913830261129237, 1308313239775608863]
CREATOR_USER_ID = 1437779380184158249
CREATOR_ROLE_ID = 1505438802653741096
FOUNDER_ROLE_ID = 1505235504826814535
MODERATOR_ROLE_ID = 1505275521825771520
COMPLAINTS_DEPT_ROLE_ID = 1527627623428128879
CALM_ROLE_IDS = [1526681612337549343, 1505438802653741096]
IMMUNE_ROLE_IDS = [CREATOR_ROLE_ID, FOUNDER_ROLE_ID]
LOGS_CHANNEL_ID = 1505274763096883230
SUPPORT_CHANNEL_ID = 1526688069464625305
MEDIA_CHANNEL_ID = 1505266075347193976
COMMUNICATION_CHANNEL_ID = 1505239843486306374
WELCOME_CHANNEL_ID = 1505280068656824400
MONITORING_CHANNEL_ID = 1526686756580229200
EXCLUDED_LOG_CHANNEL = 1505543466426437712
BOT_ID = 1521131389229994165

# ==================== КОНСТАНТЫ МОНИТОРИНГА MINECRAFT ====================
SERVER_IP = "45.152.160.92:25727"
DISPLAY_DOMAINS = ["balkangrief.burmalda.me:25727", "kingdomofjoy.gamepvp.ru:25727"]

# ==================== ФАЙЛЫ ДЛЯ ГИФОК ====================
GIF_STORAGE_FILE = "gif_storage.json"

# Файлы для мониторинга МЦ
MSG_ID_FILE = "mc_status_msg_id.txt"
HISTORY_FILE = "online_history.json"
online_history = []

CUSTOM_REACTIONS = [
    discord.PartialEmoji(name="e1", id=1506903029671137390),
    discord.PartialEmoji(name="e2", id=1506902413574012938),
    discord.PartialEmoji(name="e3", id=1506904586655498350)
]
CROWN_EMOJI = discord.PartialEmoji(name="crown", id=1506904987845001236)

# ==================== КОНСТАНТЫ УРОВНЕЙ ====================
ROLE_1 = 1505457314751320064
ROLE_5 = 1505457763894165595
ROLE_10 = 1505479667954487398
ROLE_15 = 1530587772132528353
ROLE_20 = 1505480198580080650

COUNT_CHANNELS = [1505239843486306374, 1505266075347193976, 1505822985309917274, 1525488573950853342]
UNVERIFIED_ALLOWED_CATEGORY = 1505265810015523016
BOT_CHANNEL = 1505591602360615015

LEVEL_THRESHOLDS = {1: 0, 2: 10, 3: 25, 4: 50, 5: 100, 6: 200, 7: 350, 8: 500, 9: 700, 10: 1000, 11: 1300, 12: 1700, 13: 2100, 14: 2600, 15: 3100, 16: 3700, 17: 4400, 18: 5200, 19: 6100, 20: 10000}
LEVEL_ROLE_MAP = {1: ROLE_1, 5: ROLE_5, 10: ROLE_10, 15: ROLE_15, 20: ROLE_20}

MESSAGE_COUNTS_FILE = "message_counts.json"

def get_level(count: int) -> int:
    lvl = 1
    for level, threshold in LEVEL_THRESHOLDS.items():
        if count >= threshold:
            lvl = level
    return lvl

def get_role_for_level(level: int) -> int:
    return LEVEL_ROLE_MAP.get(level)

# ==================== JSON-ФУНКЦИИ ====================
def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Ошибка чтения {filepath}: {e}")
            return default
    return default

def save_json(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Ошибка сохранения {filepath}: {e}")

# ==================== СЧЁТЧИКИ СООБЩЕНИЙ, БРАКОВ И ДНИ РОЖДЕНИЯ ====================
def load_message_counts(): return load_json(MESSAGE_COUNTS_FILE, {})
def save_message_counts(data): save_json(MESSAGE_COUNTS_FILE, data)
def load_marriages(): return load_json(MARRIAGES_FILE, {})
def save_marriages(data): save_json(MARRIAGES_FILE, data)
def load_birthdays(): return load_json(BIRTHDAYS_FILE, {})
def save_birthdays(data): save_json(BIRTHDAYS_FILE, data)

# ==================== SFTP ====================
sftp_cache = {"data": None, "timestamp": 0}

async def get_users_yml_sftp() -> dict:
    now = time.time()
    if sftp_cache["data"] is not None and (now - sftp_cache["timestamp"]) < 10:
        return sftp_cache["data"]
    try:
        transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)
        with sftp.open(SFTP_REMOTE_PATH, 'r') as f:
            content = f.read().decode('utf-8')
        sftp.close()
        transport.close()
        data = yaml.safe_load(content)
        sftp_cache["data"] = data
        sftp_cache["timestamp"] = now
        return data
    except Exception as e:
        print(f"❌ Ошибка SFTP при чтении: {e}")
        return None

async def put_users_yml_sftp(data: dict) -> bool:
    try:
        content = yaml.dump(data, allow_unicode=True, default_flow_style=False)
        transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)
        with sftp.open(SFTP_REMOTE_PATH, 'w') as f:
            f.write(content.encode('utf-8'))
        sftp.close()
        transport.close()
        sftp_cache["data"] = data
        sftp_cache["timestamp"] = time.time()
        return True
    except Exception as e:
        print(f"❌ Ошибка SFTP при записи: {e}")
        return False

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def make_blockquote(text: str) -> str:
    lines = text.strip().split('\n')
    return "\n".join([f"> {line}" if line.strip() else ">" for line in lines])

def is_calm_member(member) -> bool:
    if not isinstance(member, discord.Member):
        return False
    if member.id in CREATOR_AND_ROLE_IDS:
        return True
    return any(r.id in CALM_ROLE_IDS for r in member.roles)

def is_creator_or_founder(user: discord.Member) -> bool:
    if not isinstance(user, discord.Member):
        return False
    return user.id in CREATOR_AND_ROLE_IDS or any(r.id in [CREATOR_ROLE_ID, FOUNDER_ROLE_ID] for r in user.roles)

def is_high_staff(member: discord.Member) -> bool:
    if not member:
        return False
    return any(r.id in HIGHER_ROLES for r in member.roles) or member.id in CREATOR_AND_ROLE_IDS

def is_staff(member: discord.Member) -> bool:
    if not member:
        return False
    return is_high_staff(member) or any(r.id == CHAT_MODERATOR_ROLE_ID for r in member.roles)

async def send_log(guild: discord.Guild, title: str, description: str, color: int = 0x7864c8, fields: list = None):
    if not guild: return
    log_channel = guild.get_channel(LOGS_CHANNEL_ID)
    if not log_channel:
        try:
            log_channel = await guild.fetch_channel(LOGS_CHANNEL_ID)
        except Exception:
            return
    embed = discord.Embed(title=f"🛡️ [LOG] {title}", description=description, color=color, timestamp=datetime.now(MSK))
    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
    embed.set_footer(text="Kingdom of Joy | Audit System", icon_url=guild.icon.url if guild.icon else None)
    try:
        await log_channel.send(embed=embed)
    except Exception as e:
        print(f"❌ Ошибка отправки лога: {e}")

def create_support_banner():
    width, height = 800, 240
    img = Image.new('RGB', (width, height), color=(15, 15, 20))
    draw = ImageDraw.Draw(img)
    for i in range(height):
        r = int(15 + (i / height) * 12)
        g = int(15 + (i / height) * 10)
        b = int(25 + (i / height) * 35)
        draw.line([(0, i), (width, i)], fill=(r, g, b))
    draw.rectangle([10, 10, width - 10, height - 10], outline=(80, 80, 120), width=2)
    try:
        font_main = ImageFont.truetype("arial.ttf", 42)
        font_sub = ImageFont.truetype("arial.ttf", 20)
    except Exception:
        font_main = font_sub = ImageFont.load_default()
    draw.text((width // 2, 80), "KINGDOM OF JOY", fill=(235, 235, 245), font=font_main, anchor="mm")
    draw.text((width // 2, 130), "SUPPORT & MANAGEMENT HUB", fill=(140, 140, 180), font=font_sub, anchor="mm")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return discord.File(fp=buffer, filename="support_banner.png")

def create_welcome_banner(display_name: str):
    width, height = 800, 250
    img = Image.new('RGB', (width, height), color=(12, 10, 18))
    draw = ImageDraw.Draw(img)
    for i in range(height):
        r = int(12 + (i / height) * 20)
        g = int(10 + (i / height) * 15)
        b = int(18 + (i / height) * 45)
        draw.line([(0, i), (width, i)], fill=(r, g, b))
    draw.rectangle([10, 10, width - 10, height - 10], outline=(120, 100, 200), width=2)
    try:
        font_title = ImageFont.truetype("arial.ttf", 34)
        font_welcome = ImageFont.truetype("arial.ttf", 24)
    except Exception:
        font_title = font_welcome = ImageFont.load_default()
    draw.text((width // 2, 75), "KINGDOM OF JOY", fill=(180, 160, 255), font=font_title, anchor="mm")
    draw.text((width // 2, 150), f"ДОБРО ПОЖАЛОВАТЬ, {display_name.upper()}!", fill=(240, 240, 250), font=font_welcome, anchor="mm")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return discord.File(fp=buffer, filename="welcome_banner.png")

def parse_duration(time_str: str) -> timedelta:
    try:
        if time_str.isdigit(): return timedelta(minutes=int(time_str))
        unit = time_str[-1].lower()
        value = int(time_str[:-1])
        if unit == 's': return timedelta(seconds=value)
        elif unit == 'm': return timedelta(minutes=value)
        elif unit == 'h': return timedelta(hours=value)
        elif unit == 'd': return timedelta(days=value)
    except Exception:
        pass
    return timedelta(minutes=10)

def parse_time_or_unix(time_input: str) -> int:
    time_input = time_input.strip()
    now_ts = int(datetime.now(MSK).timestamp())
    if time_input.isdigit():
        val = int(time_input)
        return val if val > 1500000000 else now_ts + (val * 60)
    delta = parse_duration(time_input)
    return now_ts + int(delta.total_seconds())

def format_time(seconds: int) -> str:
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if days > 0: return f"{days}д {hours:02d}ч {minutes:02d}м {secs:02d}с"
    elif hours > 0: return f"{hours}ч {minutes:02d}м {secs:02d}с"
    elif minutes > 0: return f"{minutes}м {secs:02d}с"
    return f"{secs}с"

# ==================== ОБНОВЛЕНИЕ УРОВНЯ ====================
async def update_user_level(bot: commands.Bot, member: discord.Member, new_count: int, channel: discord.TextChannel = None):
    new_level = get_level(new_count)
    old_level = bot.user_level_cache.get(member.id, 1)
    if new_level == old_level: return
    old_role_id = get_role_for_level(old_level)
    if old_role_id:
        old_role = member.guild.get_role(old_role_id)
        if old_role and old_role in member.roles: await member.remove_roles(old_role, reason=f"Уровень повысился до {new_level}")
    new_role_id = get_role_for_level(new_level)
    if new_role_id:
        new_role = member.guild.get_role(new_role_id)
        if new_role and new_role not in member.roles: await member.add_roles(new_role, reason=f"Достигнут уровень {new_level}")
    bot.user_level_cache[member.id] = new_level
    if new_level > old_level and channel:
        try:
            await channel.send(make_blockquote(f"🎉 **Поздравляю, {member.mention}!**\nТы достиг **{new_level} уровня**!\n📊 Сообщений: `{new_count}`\n🏆 Новый уровень: `{new_level}` из 20"))
        except Exception as e:
            print(f"Ошибка отправки поздравления: {e}")

# ==================== ИСТОРИЯ И ГРАФИКИ (ИЗ MC_STATUS) ====================
def save_history():
    try:
        data = [{"t": item[0].isoformat(), "o": item[1]} for item in online_history]
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"⚠️ Ошибка сохранения истории: {e}")

def load_history():
    global online_history
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                online_history = [(datetime.fromisoformat(item["t"]), item["o"]) for item in data]
                print(f"✅ Загружена история онлайна: {len(online_history)} записей.")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки истории: {e}")
            online_history = []

load_history()

def parse_address(addr: str):
    addr = addr.strip()
    if ":" in addr:
        host, port_str = addr.split(":", 1)
        try:
            return host.strip(), int(port_str.strip())
        except ValueError:
            return host.strip(), 25727
    return addr, 25727

async def check_mc_server():
    targets = [SERVER_IP] if SERVER_IP and "xxx" not in SERVER_IP else []
    targets.extend(DISPLAY_DOMAINS)
    for addr in targets:
        host, port = parse_address(addr)
        is_port_open = False
        try:
            loop = asyncio.get_event_loop()
            def ping_socket():
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3.0)
                res = s.connect_ex((host, port))
                s.close()
                return res == 0
            is_port_open = await loop.run_in_executor(None, ping_socket)
        except Exception as e:
            print(f"⚠️ Ошибка сокета {host}:{port} -> {e}")
        if is_port_open:
            try:
                server = JavaServer(host, port)
                status = await server.async_status()
                players_sample = status.players.sample if status.players.sample else []
                player_names = [p.name for p in players_sample]
                return True, status.players.online, status.players.max, player_names
            except Exception as e:
                print(f"⚠️ Порт открыт, сбой mcstatus ({host}:{port}): {e}")
                return True, 0, 100, []
    return False, 0, 100, []

def generate_double_graph(history_data, max_slots=100):
    fig, (ax24, ax1h) = plt.subplots(2, 1, figsize=(8, 6), facecolor='#1e1f22')
    now_msk = datetime.now(MSK)
    ax24.set_facecolor('#1e1f22')
    cutoff_24h = now_msk - timedelta(hours=24)
    data_24h = [item for item in history_data if item[0] >= cutoff_24h]
    if not data_24h:
        data_24h = [(now_msk, 0)]
    times_24 = [item[0].strftime("%H:%M") for item in data_24h]
    players_24 = [item[1] for item in data_24h]
    ax24.plot(times_24, players_24, color='#7864c8', linewidth=2)
    ax24.fill_between(times_24, players_24, color='#7864c8', alpha=0.25)
    ax24.set_title("ИСТОРИЯ ОНЛАЙНА ЗА 24 ЧАСА (ИНТЕРВАЛ 2 МИНУТЫ)", fontsize=9, color='#808080', pad=8)
    ax24.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax24.set_ylim(0, max(max_slots, max(players_24) + 2))
    step_24 = max(1, len(times_24) // 12)
    ax24.set_xticks(range(0, len(times_24), step_24))
    ax24.set_xticklabels([times_24[i] for i in range(0, len(times_24), step_24)], rotation=0)
    ax24.tick_params(colors='#808080', labelsize=8)
    for spine in ax24.spines.values():
        spine.set_color('#2b2d31')
    ax24.grid(True, color='#2b2d31', linestyle='--', linewidth=0.5)
    
    ax1h.set_facecolor('#1e1f22')
    cutoff_1h = now_msk - timedelta(hours=1)
    data_1h = [item for item in history_data if item[0] >= cutoff_1h]
    if not data_1h:
        data_1h = [(now_msk, 0)]
    times_1h = [item[0].strftime("%H:%M") for item in data_1h]
    players_1h = [item[1] for item in data_1h]
    ax1h.plot(times_1h, players_1h, color='#2ecc71', marker='o', linewidth=2, markersize=4)
    ax1h.fill_between(times_1h, players_1h, color='#2ecc71', alpha=0.25)
    ax1h.set_title("ДЕТАЛИЗАЦИЯ ЗА ПОСЛЕДНИЙ 1 ЧАС", fontsize=9, color='#808080', pad=8)
    ax1h.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax1h.set_ylim(0, max(max_slots, max(players_1h) + 2))
    step_1h = max(1, len(times_1h) // 4)
    ax1h.set_xticks(range(0, len(times_1h), step_1h))
    ax1h.set_xticklabels([times_1h[i] for i in range(0, len(times_1h), step_1h)], rotation=0)
    ax1h.tick_params(colors='#808080', labelsize=8)
    for spine in ax1h.spines.values():
        spine.set_color('#2b2d31')
    ax1h.grid(True, color='#2b2d31', linestyle='--', linewidth=0.5)
    plt.tight_layout()
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', facecolor='#1e1f22', edgecolor='none', dpi=120)
    buffer.seek(0)
    plt.close()
    return discord.File(fp=buffer, filename="online_graph.png")

def save_msg_id(msg_id: int):
    with open(MSG_ID_FILE, "w", encoding="utf-8") as f:
        f.write(str(msg_id))

def load_msg_id() -> int:
    if os.path.exists(MSG_ID_FILE):
        try:
            with open(MSG_ID_FILE, "r", encoding="utf-8") as f:
                return int(f.read().strip())
        except Exception:
            return None
    return None

class StatusButtonsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Обновить сейчас", style=discord.ButtonStyle.primary, emoji="🔄", custom_id="mc_refresh_status_btn")
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await update_status_message(interaction.client)
        await interaction.followup.send("✅ Данные мониторинга обновлены!", ephemeral=True)

async def update_status_message(bot: commands.Bot):
    try:
        channel = bot.get_channel(MONITORING_CHANNEL_ID)
        if not channel:
            try:
                channel = await bot.fetch_channel(MONITORING_CHANNEL_ID)
            except Exception as e:
                print(f"❌ Канал мониторинга {MONITORING_CHANNEL_ID} не найден: {e}")
                return
        is_online, current_players, max_players, player_names = await check_mc_server()
        print(f"🔄 Статус: {'онлайн' if is_online else 'офлайн'}, игроков: {current_players}/{max_players}")
        now_msk = datetime.now(MSK)
        time_str = now_msk.strftime("%H:%M")
        online_history.append((now_msk, current_players if is_online else 0))
        if len(online_history) > 720:
            online_history.pop(0)
        save_history()
        main_public_domain = DISPLAY_DOMAINS[0] if DISPLAY_DOMAINS else "Оф. Сервер"
        if is_online:
            embed = discord.Embed(title="🎮 Мониторинг Minecraft Сервера", color=0x2ecc71, timestamp=now_msk)
            embed.add_field(name="🟢 Статус", value="**Сервер онлайн!**", inline=False)
            embed.add_field(name="👥 Онлайн", value=f"`{current_players} / {max_players}`", inline=True)
            embed.add_field(name="⚡ Работающий адрес", value=f"`{main_public_domain}`", inline=True)
            if player_names:
                players_list = "\n".join([f"• {name}" for name in player_names])
                embed.add_field(name="👤 Игроки онлайн", value=players_list, inline=False)
        else:
            embed = discord.Embed(title="🎮 Мониторинг Minecraft Сервера", color=0xe74c3c, timestamp=now_msk)
            embed.add_field(name="🔴 Статус", value="**Сервер недоступен или выключен.**", inline=False)
            embed.add_field(name="⚠️ Ошибка подключения", value="`Сервер не отвечает по указанным адресам`", inline=False)
        domains_text = "\n".join([f"• `{d}`" for d in DISPLAY_DOMAINS])
        embed.add_field(name="🌐 Домены для подключения", value=domains_text, inline=False)
        embed.set_footer(text=f"Авто-обновление раз в 2 минуты • Сегодня, в {time_str}")
        max_slots = max_players if max_players > 0 else 100
        graph_file = generate_double_graph(online_history, max_slots=max_slots)
        embed.set_image(url="attachment://online_graph.png")
        msg_id = load_msg_id()
        msg = None
        if msg_id:
            try:
                msg = await channel.fetch_message(msg_id)
            except Exception as e:
                print(f"⚠️ Не удалось найти сообщение {msg_id}: {e}")
                msg = None
        try:
            if msg:
                await msg.edit(embed=embed, attachments=[graph_file], view=StatusButtonsView())
                print(f"✅ Обновлено сообщение {msg.id} в канале {channel.id}")
            else:
                new_msg = await channel.send(embed=embed, file=graph_file, view=StatusButtonsView())
                save_msg_id(new_msg.id)
                print(f"✅ Создано новое сообщение мониторинга с ID: {new_msg.id}")
        except discord.Forbidden:
            print(f"❌ Нет прав на редактирование/отправку в канале {channel.id}")
        except Exception as e:
            print(f"❌ Ошибка отправки/обновления мониторинга: {e}")
    except Exception as e:
        print(f"❌ Критическая ошибка в update_status_message: {e}")
        traceback.print_exc()

# ==================== СИСТЕМА ВЕРИФИКАЦИИ ====================
class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Верифицироваться", style=discord.ButtonStyle.success)
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        guild = interaction.guild

        if VERIFY_ROLE_ID in [r.id for r in member.roles]:
            await interaction.response.send_message("⚠️ Вы уже верифицированы!", ephemeral=True)
            return

        verify_role = guild.get_role(VERIFY_ROLE_ID)
        unverified_role = guild.get_role(UNVERIFIED_ROLE_ID)

        try:
            if verify_role:
                await member.add_roles(verify_role)
            if unverified_role and unverified_role in member.roles:
                await member.remove_roles(unverified_role)
            await interaction.response.send_message("✅ Поздравляю! Вы успешно прошли верификацию и получили доступ к серверу!", ephemeral=True)
            await send_log(guild, "✅ Верификация", f"Пользователь {member.mention} успешно верифицировался.", color=0x2ecc71)
        except Exception as e:
            await interaction.response.send_message(f"❌ Произошла ошибка: {e}", ephemeral=True)

@app_commands.command(name="setup_verify", description="⚙️ Отправить сообщение с кнопкой верификации (Основатели)")
async def setup_verify(interaction: discord.Interaction):
    if not is_creator_or_founder(interaction.user):
        await interaction.response.send_message("❌ Доступно только Основателям.", ephemeral=True)
        return

    if interaction.channel.id != VERIFY_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Эта команда используется только в канале <#{VERIFY_CHANNEL_ID}>.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🔒 Верификация",
        description=(
            "Для получения доступа ко всем каналам сервера, пожалуйста, нажмите кнопку ниже.\n"
            "После верификации вы получите основную роль и сможете участвовать в жизни сообщества."
        ),
        color=0x2ecc71
    )
    view = VerifyView()
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send(embed=embed, view=view)

# ==================== ИНТЕРАКТИВНЫЙ БРАК ====================
class MarriageProposalView(discord.ui.View):
    def __init__(self, author: discord.Member, target: discord.Member):
        super().__init__(timeout=120)
        self.author = author
        self.target = target

    @discord.ui.button(label="Принять 💕", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("❌ Это предложение адресовано не вам!", ephemeral=True)
            return
        marriages = load_marriages()
        if str(self.author.id) in marriages or str(self.target.id) in marriages:
            await interaction.response.send_message("❌ Один из участников уже состоит в браке!", ephemeral=True)
            return
        now_ts = int(datetime.now(MSK).timestamp())
        marriages[str(self.author.id)] = {"partner": self.target.id, "date": now_ts}
        marriages[str(self.target.id)] = {"partner": self.author.id, "date": now_ts}
        save_marriages(marriages)
        self.stop()
        embed = discord.Embed(title="💍 Священный Союз Заключён!", description=f"🎉 {self.author.mention} и {self.target.mention} теперь официально в браке!\nПоздравляем новобрачных! 💕", color=0xff69b4, timestamp=datetime.now(MSK))
        await interaction.response.edit_message(content=None, embed=embed, view=None)
        await send_log(interaction.guild, "💍 Заключен Брак", f"{self.author.mention} и {self.target.mention} вступили в брак.", color=0xff69b4)

    @discord.ui.button(label="Отклонить 💔", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("❌ Это предложение адресовано не вам!", ephemeral=True)
            return
        self.stop()
        await interaction.response.edit_message(content=make_blockquote(f"💔 {self.target.mention} отклонил(а) предложение руки и сердца от {self.author.mention}."), embed=None, view=None)

# ==================== СЛЭШ-КОМАНДЫ БРАКОВ И ДНЕЙ РОЖДЕНИЯ ====================
@app_commands.command(name="брак", description="💍 Сделать предложение руки и сердца игроку")
@app_commands.describe(user="Пользователь, которому вы предлагаете брак")
async def marriage_propose(interaction: discord.Interaction, user: discord.Member):
    if user.id == interaction.user.id:
        await interaction.response.send_message("❌ Вы не можете заключить брак с самим собой!", ephemeral=True)
        return
    if user.bot:
        await interaction.response.send_message("❌ Нельзя вступать в брак с ботами!", ephemeral=True)
        return
    marriages = load_marriages()
    if str(interaction.user.id) in marriages:
        await interaction.response.send_message("❌ Вы уже состоите в браке! Сначала разведитесь командой `/развод`.", ephemeral=True)
        return
    if str(user.id) in marriages:
        await interaction.response.send_message(f"❌ Пользователь {user.mention} уже состоит в браке!", ephemeral=True)
        return
    view = MarriageProposalView(interaction.user, user)
    embed = discord.Embed(title="💍 Предложение руки и сердца!", description=f"💖 {user.mention}, пользователь {interaction.user.mention} предлагает вам вступить в брак!\nВы принимаете предложение?", color=0xff69b4)
    await interaction.response.send_message(content=f"{user.mention}", embed=embed, view=view)

@app_commands.command(name="развод", description="💔 Расторгнуть ваш текущий брак")
async def marriage_divorce(interaction: discord.Interaction):
    marriages = load_marriages()
    uid = str(interaction.user.id)
    if uid not in marriages:
        await interaction.response.send_message("❌ Вы не состоите в браке.", ephemeral=True)
        return
    partner_id = marriages[uid]["partner"]
    del marriages[uid]
    if str(partner_id) in marriages:
        del marriages[str(partner_id)]
    save_marriages(marriages)
    partner = interaction.guild.get_member(partner_id)
    partner_str = partner.mention if partner else f"<@{partner_id}>"
    await interaction.response.send_message(make_blockquote(f"💔 Брак между {interaction.user.mention} и {partner_str} был расторгнут."))
    await send_log(interaction.guild, "💔 Брак Расторгнут", f"Пользователь {interaction.user.mention} развёлся с {partner_str}.", color=0xe74c3c)

@app_commands.command(name="профиль_брака", description="💕 Посмотреть статус брака")
@app_commands.describe(user="Пользователь (оставьте пустым для себя)")
async def marriage_profile(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    marriages = load_marriages()
    uid = str(target.id)
    if uid not in marriages:
        await interaction.response.send_message(make_blockquote(f"💔 {target.mention} не состоит в браке."), ephemeral=True)
        return
    p_info = marriages[uid]
    partner = interaction.guild.get_member(p_info["partner"])
    partner_str = partner.mention if partner else f"<@{p_info['partner']}>"
    date_str = f"<t:{p_info['date']}:D> (<t:{p_info['date']}:R>)"
    embed = discord.Embed(title=f"💕 Профиль брака — {target.display_name}", color=0xff69b4, timestamp=datetime.now(MSK))
    embed.add_field(name="💍 Супруг(а)", value=partner_str, inline=True)
    embed.add_field(name="📅 Дата свадьбы", value=date_str, inline=True)
    embed.set_footer(text="Kingdom of Joy | Браки", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="все_браки", description="💕 Показать список всех браков на сервере")
async def all_marriages(interaction: discord.Interaction):
    marriages = load_marriages()
    if not marriages:
        await interaction.response.send_message("💔 На сервере пока нет ни одного брака.", ephemeral=True)
        return
    embed = discord.Embed(title="💕 Список браков", color=0xff69b4, timestamp=datetime.now(MSK))
    processed = set()
    desc = []
    for uid_str, data in marriages.items():
        uid = int(uid_str)
        partner_id = data["partner"]
        if uid in processed or partner_id in processed:
            continue
        processed.add(uid)
        processed.add(partner_id)
        p1 = interaction.guild.get_member(uid)
        p2 = interaction.guild.get_member(partner_id)
        p1_str = p1.mention if p1 else f"<@{uid}>"
        p2_str = p2.mention if p2 else f"<@{partner_id}>"
        date_ts = data["date"]
        date_str = f"<t:{date_ts}:D>"
        desc.append(f"{p1_str} 💞 {p2_str}\n📅 {date_str}")
    if not desc:
        embed.description = "Не удалось отобразить браки (возможно, участники покинули сервер)."
    else:
        embed.description = "\n\n".join(desc)
    embed.set_footer(text="Kingdom of Joy | Браки", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="setdr", description="🎂 Установить дату своего рождения (ДД.ММ или ДД.ММ.ГГГГ)")
@app_commands.describe(date="Дата рождения в формате ДД.ММ (например, 15.08) или ДД.ММ.ГГГГ (15.08.2005)")
async def set_dr(interaction: discord.Interaction, date: str):
    if not re.match(r"^\d{2}\.\d{2}(\.\d{4})?$", date):
        await interaction.response.send_message("❌ Неверный формат! Используйте `ДД.ММ` (например, `15.08`) или `ДД.ММ.ГГГГ` (например, `15.08.2005`).", ephemeral=True)
        return
    birthdays = load_birthdays()
    birthdays[str(interaction.user.id)] = date
    save_birthdays(birthdays)
    await interaction.response.send_message(make_blockquote(f"🎂 Дата рождения успешно установлена на `{date}`!"), ephemeral=True)

@app_commands.command(name="др", description="🎂 Посмотреть дату рождения игрока")
@app_commands.describe(user="Пользователь (оставьте пустым для себя)")
async def get_dr(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    birthdays = load_birthdays()
    bdate = birthdays.get(str(target.id))
    if not bdate:
        await interaction.response.send_message(make_blockquote(f"🎂 У пользователя {target.mention} не указана дата рождения."), ephemeral=True)
        return
    await interaction.response.send_message(make_blockquote(f"🎂 День рождения {target.mention}: **{bdate}**"))

@app_commands.command(name="все_др", description="🎂 Показать список всех дней рождения на сервере")
async def all_birthdays(interaction: discord.Interaction):
    birthdays = load_birthdays()
    if not birthdays:
        await interaction.response.send_message("🎂 На сервере пока нет сохранённых дней рождения.", ephemeral=True)
        return
    embed = discord.Embed(title="🎂 Список дней рождения", color=0x5865F2, timestamp=datetime.now(MSK))
    today = datetime.now(MSK).strftime("%d.%m")
    fields_added = 0
    for uid_str, date in birthdays.items():
        uid = int(uid_str)
        member = interaction.guild.get_member(uid)
        if not member:
            continue
        avatar_url = member.display_avatar.url
        date_parts = date.split(".")
        is_today = date.startswith(today)
        if len(date_parts) == 3: # DD.MM.YYYY
            day, month, year = date_parts
            display_date = f"{day}.{month}"
            try:
                current_year = datetime.now(MSK).year
                age = current_year - int(year)
                age_str = f"{age} лет"
                if is_today:
                    age_str += " 🎂 (Сегодня!)"
            except:
                age_str = "Неизвестно"
        else: # DD.MM
            display_date = date
            age_str = "Не указан"
        today_str = " 🎉 СЕГОДНЯ! 🎉" if is_today else ""
        embed.add_field(
            name=member.display_name,
            value=f"📅 {display_date}{today_str}\n🎂 Возраст: {age_str}\n👤 [Аватар]({avatar_url})",
            inline=True
        )
        fields_added += 1
        if fields_added % 9 == 0:
            pass
    if fields_added == 0:
        embed.description = "Не удалось найти участников с указанными днями рождения (возможно, они покинули сервер)."
    embed.set_footer(text="Kingdom of Joy | Дни рождения", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await interaction.response.send_message(embed=embed)

# ==================== СИСТЕМА МАФИИ ====================
mafia_configs = {}

class MafiaGame:
    def __init__(self, bot, channel, starter):
        self.bot = bot
        self.channel = channel
        self.starter = starter
        self.participants = []
        self.alive = []
        self.roles = {}
        self.choices = {}
        self.actions_done = {"don_investigate": False}
        self.message = None
        self.game_over = False
        self.night_phase = False
        self.votes = {}
        self.registration_active = True
        self.registration_time_left = 90

    async def send_creator_log(self, embed: discord.Embed):
        try:
            creator = await self.bot.fetch_user(CREATOR_USER_ID)
            await creator.send(embed=embed)
        except Exception as e:
            print(f"❌ Ошибка отправки лога создателю: {e}")

    def get_alive_players_list(self):
        return [p for p in self.alive if p in self.participants]

    def check_win(self):
        mafia = [p for p in self.alive if self.roles.get(p.id) in ["Мафия", "Дон"]]
        town = [p for p in self.alive if self.roles.get(p.id) not in ["Мафия", "Дон"]]
        if len(mafia) >= len(town): return "Мафия"
        if len(mafia) == 0: return "Город"
        return None

    async def start_night(self):
        self.night_phase = True
        self.choices = {}
        alive = self.get_alive_players_list()
        alive_ids = [p.id for p in alive]
        await self.channel.send("🌙 **Наступила ночь.**")
        log_embed = discord.Embed(title="🌙 Начало ночи", color=0x222222)
        log_embed.add_field(name="Живые игроки", value=", ".join([p.mention for p in alive]))
        await self.send_creator_log(log_embed)
        for p in alive:
            role = self.roles.get(p.id)
            if role in ["Мафия", "Дон", "Доктор", "Детектив", "Бармен", "Путана"]:
                try:
                    await p.send(f"🕵️ **Ночь началась!** Твоя роль: **{role}**", view=self.get_role_view(p, alive_ids))
                except: pass
        start_time = datetime.now(MSK)
        needed_roles = [p for p in alive if self.roles.get(p.id) in ["Мафия", "Дон", "Доктор", "Детектив", "Бармен", "Путана"]]
        while datetime.now(MSK) - start_time < timedelta(seconds=60):
            if len(self.choices) >= len(needed_roles): break
            await asyncio.sleep(1)
        self.night_phase = False
        await self.resolve_night()

    def get_role_view(self, player, alive_ids):
        role = self.roles.get(player.id)
        alive_members = [p for p in self.participants if p.id in alive_ids and p.id != player.id]
        if role == "Мафия": return MafiaActionView(self, player, alive_members)
        elif role == "Дон": return DonActionView(self, player, alive_members)
        elif role == "Доктор": return DoctorActionView(self, player, alive_members)
        elif role == "Детектив": return DetectiveActionView(self, player, alive_members)
        elif role == "Бармен": return BarmanActionView(self, player, alive_members)
        elif role == "Путана": return HarlotActionView(self, player, alive_members)
        return None

    async def resolve_night(self):
        mafia_target = self.choices.get("mafia")
        doctor_target = self.choices.get("doctor")
        barman_target = self.choices.get("barman")
        detective_invest = self.choices.get("detective_invest")
        detective_shoot = self.choices.get("detective_shoot")
        harlot_target = self.choices.get("harlot")
        dead_players = []
        message_lines = []
        night_silent = False
        harlot_blocked = None
        log_embed = discord.Embed(title="🔍 Ночные выборы", color=0xffaa00)
        if mafia_target: log_embed.add_field(name="Мафия/Дон", value=f"Убить <@{mafia_target}>", inline=False)
        if doctor_target: log_embed.add_field(name="Доктор", value=f"Спасти <@{doctor_target}>", inline=False)
        if harlot_target: log_embed.add_field(name="Путана", value=f"Соблазнить <@{harlot_target}>", inline=False)
        if detective_invest: log_embed.add_field(name="Детектив", value=f"Проверить <@{detective_invest}>", inline=False)
        if detective_shoot: log_embed.add_field(name="Детектив", value=f"Застрелить <@{detective_shoot}>", inline=False)
        if barman_target: log_embed.add_field(name="Бармен", value=f"Напоить <@{barman_target}>", inline=False)
        if harlot_target:
            harlot_victim = discord.utils.get(self.participants, id=harlot_target)
            if harlot_victim:
                blocked_role = self.roles.get(harlot_victim.id)
                harlot_blocked = harlot_victim
                if blocked_role in ["Мафия", "Дон"]:
                    night_silent = True
                    message_lines.append(f"🥂 **Путана** соблазнила мафию! Убийство сорвано!")
                elif blocked_role == "Доктор":
                    doctor_target = None
                    message_lines.append(f"🥂 **Путана** соблазнила доктора! Он никого не спас.")
                elif blocked_role == "Детектив":
                    detective_shoot = None; detective_invest = None
                    message_lines.append(f"🥂 **Путана** соблазнила детектива! Он потерял бдительность.")
                elif blocked_role == "Бармен":
                    barman_target = None
                    message_lines.append(f"🥂 **Путана** соблазнила бармена! Он забыл про напитки.")
        detective_player = None
        for p in self.participants:
            if self.roles.get(p.id) == "Детектив": detective_player = p; break
        if detective_shoot and not harlot_blocked == detective_player:
            target_p = discord.utils.get(self.participants, id=int(detective_shoot))
            if target_p and self.roles.get(target_p.id) in ["Мафия", "Дон"]:
                dead_players.append(target_p)
                message_lines.append(f"🔫 **Детектив** застрелил мафию: {target_p.mention}!")
            elif target_p:
                dead_players.append(detective_player)
                message_lines.append(f"💔 **Детектив** застрелил мирного {target_p.mention} и выбывает сам!")
        elif detective_invest and not harlot_blocked == detective_player:
            target_p = discord.utils.get(self.participants, id=int(detective_invest))
            if target_p and detective_player:
                role_info = self.roles.get(target_p.id, "Неизвестно")
                await detective_player.send(f"🔍 **Результат проверки:** Игрок {target_p.display_name} — роль **{role_info}**")
        if mafia_target and not night_silent:
            victim = discord.utils.get(self.participants, id=mafia_target)
            if victim and victim not in dead_players:
                saved = False
                if doctor_target == mafia_target:
                    saved = True
                    message_lines.append(f"🏥 **Доктор** спас {victim.mention} от смерти!")
                if barman_target == mafia_target:
                    saved = True
                    message_lines.append(f"🍺 **Бармен** напоил {victim.mention} и тот выжил!")
                if not saved:
                    dead_players.append(victim)
                    message_lines.append(f"🔪 **Мафия** жестоко убила {victim.mention}!")
                else:
                    message_lines.append(f"🌙 Покушение на {victim.mention} провалилось!")
        if not dead_players and not message_lines: message_lines.append("Ночь прошла тихо, все живы.")
        for p in dead_players:
            if p in self.alive: self.alive.remove(p)
        log_embed.add_field(name="📌 Итог ночи", value="\n".join(message_lines), inline=False)
        await self.send_creator_log(log_embed)
        winner = self.check_win()
        if winner:
            embed = discord.Embed(title="🏆 Игра окончена!", description=f"Победила фракция: **{winner}**", color=0xffd700)
            await self.channel.send(embed=embed)
            self.game_over = True
            return
        public_desc = "\n".join([l for l in message_lines if "кто-то" not in l])
        embed = discord.Embed(title="🌅 Утро", description=public_desc, color=0x7864c8)
        embed.set_footer(text="Обсуждение 60 сек!")
        await self.channel.send(embed=embed)
        await asyncio.sleep(60)
        embed = discord.Embed(title="🗳️ Начинается голосование!", description="Введите `!голос @Игрок`.\nГолосование завершится **моментально** по общему согласию, либо через 40 секунд.", color=0x2ecc71)
        await self.channel.send(embed=embed)
        self.votes = {}
        start_time = datetime.now(MSK)
        total_alive = len(self.alive)
        while datetime.now(MSK) - start_time < timedelta(seconds=40):
            if len(self.votes) >= total_alive: break
            await asyncio.sleep(1)
        most_voted = None
        max_votes = 0
        for target_id, voters in self.votes.items():
            if len(voters) > max_votes:
                max_votes = len(voters)
                most_voted = target_id
        vote_embed = discord.Embed(title="🗳️ Итоги дневного голосования", color=0xf1c40f)
        if self.votes:
            for target_id, voters in self.votes.items():
                target_p = discord.utils.get(self.participants, id=target_id)
                vote_embed.add_field(name=f"{target_p.mention if target_p else 'Unknown'}", value=f"Голосов: {len(voters)} ({', '.join([v.mention for v in voters])})", inline=False)
        else:
            vote_embed.description = "Никто не проголосовал."
        await self.send_creator_log(vote_embed)
        if most_voted:
            banished = discord.utils.get(self.participants, id=most_voted)
            if banished and banished in self.alive:
                self.alive.remove(banished)
                await self.channel.send(f"💀 По результатам голосования игрок {banished.mention} был изгнан!")
        else:
            await self.channel.send("🗳️ Никто не набрал голосов, сегодня никто не вылетает.")
        winner = self.check_win()
        if winner:
            embed = discord.Embed(title="🏆 Игра окончена!", description=f"Победила фракция: **{winner}**", color=0xffd700)
            await self.channel.send(embed=embed)
            self.game_over = True
            return
        if not self.game_over: await self.start_night()

# ==================== VIEWS ДЛЯ МАФИИ (Меню в ЛС) ====================
class BaseActionView(discord.ui.View):
    def __init__(self, game, player, alive_members, timeout=60):
        super().__init__(timeout=timeout)
        self.game = game
        self.player = player
        self.alive_members = alive_members
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.player.id

class MafiaActionView(BaseActionView):
    @discord.ui.select(placeholder="Выберите жертву для убийства 👇", custom_id="mafia_target")
    async def select_target(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.game.choices["mafia"] = int(select.values[0])
        await interaction.response.send_message(f"✅ Выбрано.", ephemeral=True)
        self.stop()

class DonActionView(BaseActionView):
    def __init__(self, game, player, alive_members):
        super().__init__(game, player, alive_members)
        if not self.game.actions_done["don_investigate"]:
            self.add_item(DonInvestigateButton())
    @discord.ui.select(placeholder="Выберите жертву для убийства 👇", custom_id="don_target")
    async def select_target(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.game.choices["mafia"] = int(select.values[0])
        await interaction.response.send_message(f"✅ Дон выбрал.", ephemeral=True)
        self.stop()

class DonInvestigateButton(discord.ui.Button):
    def __init__(self): super().__init__(label="🔍 Прошмонать (1 раз)", style=discord.ButtonStyle.primary)
    async def callback(self, interaction: discord.Interaction):
        view = DonInvestView(interaction.client.mafia_game, interaction.user, interaction.client.mafia_game.get_alive_players_list())
        await interaction.response.send_message("Выберите игрока:", view=view, ephemeral=True)

class DonInvestView(BaseActionView):
    @discord.ui.select(placeholder="Кого проверить?", custom_id="don_invest_select")
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.game.actions_done["don_investigate"] = True
        self.game.choices["don_investigate"] = int(select.values[0])
        await interaction.response.send_message("✅ Запрос отправлен!", ephemeral=True)
        self.stop()

class DoctorActionView(BaseActionView):
    @discord.ui.select(placeholder="Выберите, кого спасти 👇", custom_id="doctor_target")
    async def select_target(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.game.choices["doctor"] = int(select.values[0])
        await interaction.response.send_message(f"✅ Выбрано.", ephemeral=True)
        self.stop()

class BarmanActionView(BaseActionView):
    @discord.ui.select(placeholder="Кого напоить (усыпить) 👇", custom_id="barman_target")
    async def select_target(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.game.choices["barman"] = int(select.values[0])
        await interaction.response.send_message(f"✅ Выбрано.", ephemeral=True)
        self.stop()

class HarlotActionView(BaseActionView):
    @discord.ui.select(placeholder="Кого соблазнить этой ночью? 👇", custom_id="harlot_target")
    async def select_target(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.game.choices["harlot"] = int(select.values[0])
        await interaction.response.send_message(f"✅ Выбрано.", ephemeral=True)
        self.stop()

class DetectiveActionView(BaseActionView):
    def __init__(self, game, player, alive_members):
        super().__init__(game, player, alive_members)
        self.add_item(DetectiveInvestigateButton())
        self.add_item(DetectiveShootButton())

class DetectiveInvestigateButton(discord.ui.Button):
    def __init__(self): super().__init__(label="🔍 Проверить", style=discord.ButtonStyle.primary, custom_id="det_invest")
    async def callback(self, interaction: discord.Interaction):
        view = DetectiveInvestView(interaction.client.mafia_game, interaction.user, interaction.client.mafia_game.get_alive_players_list())
        await interaction.response.send_message("Выберите игрока:", view=view, ephemeral=True)

class DetectiveShootButton(discord.ui.Button):
    def __init__(self): super().__init__(label="🔫 Выстрелить", style=discord.ButtonStyle.danger, custom_id="det_shoot")
    async def callback(self, interaction: discord.Interaction):
        view = DetectiveShootView(interaction.client.mafia_game, interaction.user, interaction.client.mafia_game.get_alive_players_list())
        await interaction.response.send_message("Выберите цель:", view=view, ephemeral=True)

class DetectiveInvestView(BaseActionView):
    @discord.ui.select(placeholder="Кого проверить?", custom_id="det_invest_select")
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.game.choices["detective_invest"] = int(select.values[0])
        await interaction.response.send_message(f"✅ Выбрано.", ephemeral=True)
        self.stop()

class DetectiveShootView(BaseActionView):
    @discord.ui.select(placeholder="В кого стрелять?", custom_id="det_shoot_select")
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.game.choices["detective_shoot"] = int(select.values[0])
        await interaction.response.send_message(f"✅ Выбрано.", ephemeral=True)
        self.stop()

# ==================== КОМАНДА ЗАПУСКА МАФИИ И ГОЛОСОВАНИЕ ====================
@app_commands.command(name="mafia", description="🕶️ Запустить новую игру в Мафию")
async def mafia_cmd(interaction: discord.Interaction):
    if not is_creator_or_founder(interaction.user) and not any(r.id in HIGHER_ROLES for r in interaction.user.roles):
        await interaction.response.send_message("❌ Запускать игру могут только модераторы и руководство.", ephemeral=True)
        return
    await interaction.response.defer()
    config = mafia_configs.get(interaction.guild_id, {})
    game = MafiaGame(interaction.client, interaction.channel, interaction.user)
    interaction.client.mafia_game = game
    embed = discord.Embed(title="🕶️ Регистрация на игру в Мафию", color=0x7864c8)
    view = MafiaRegistrationView(game, interaction.client)
    await interaction.followup.send(embed=embed, view=view)
    msg = await interaction.original_response()
    game.message = msg
    await view.update_embed()
    async def registration_timer():
        while game.registration_active and game.registration_time_left > 0:
            await asyncio.sleep(1)
            game.registration_time_left -= 1
            if game.registration_time_left % 3 == 0 or game.registration_time_left <= 0:
                await view.update_embed()
            if game.registration_time_left <= 0:
                game.registration_active = False
                break
        if game.registration_active and len(game.participants) < 4:
            await interaction.channel.send("❌ Меньше 4 игроков. Игра отменена.")
            game.registration_active = False
            return
        if len(game.participants) >= 4:
            await interaction.channel.send("⏰ Время регистрации истекло! Начинаем игру!")
            await view.start_game()
    view.timer_task = asyncio.create_task(registration_timer())

class MafiaRegistrationView(discord.ui.View):
    def __init__(self, game: MafiaGame, bot):
        super().__init__(timeout=None)
        self.game = game
        self.bot = bot
        self.timer_task = None

    async def update_embed(self):
        players_list = "\n".join([f"{i+1}. {p.mention}" for i, p in enumerate(self.game.participants)]) if self.game.participants else "Пока никого..."
        embed = discord.Embed(title="🕶️ Регистрация на игру в Мафию", description=(f"**Игру создал:** {self.game.starter.mention}\n" f"**⏱️ Осталось:** `{self.game.registration_time_left}` сек.\n" f"**👥 Участников:** `{len(self.game.participants)} / 30`\n\n" f"**📋 Список игроков:**\n{players_list}"), color=0x7864c8)
        try:
            await self.game.message.edit(embed=embed, view=self)
        except: pass

    @discord.ui.button(label="Участвовать в Мафии 🕶️", style=discord.ButtonStyle.primary, row=0)
    async def join_mafia(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.game.registration_active:
            await interaction.response.send_message("❌ Регистрация уже завершена!", ephemeral=True)
            return
        if interaction.user in self.game.participants:
            await interaction.response.send_message("⚠️ Вы уже зарегистрированы!", ephemeral=True)
            return
        if len(self.game.participants) >= 30:
            await interaction.response.send_message("❌ Лимит 30 человек.", ephemeral=True)
            return
        try:
            test_msg = await interaction.user.send("🛡️ Проверка ЛС успешна. Вы допущены.")
            await test_msg.delete()
        except discord.Forbidden:
            await interaction.response.send_message("❌ У вас закрыты ЛС! Откройте их в настройках.", ephemeral=True)
            return
        self.game.participants.append(interaction.user)
        await interaction.response.send_message(f"✅ {interaction.user.mention} зарегистрирован!", ephemeral=True)
        await self.update_embed()

    @discord.ui.button(label="⏱️ +30 сек", style=discord.ButtonStyle.secondary, row=0)
    async def extend_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_creator_or_founder(interaction.user) and not is_high_staff(interaction.user):
            await interaction.response.send_message("❌ Доступно только руководству.", ephemeral=True)
            return
        if not self.game.registration_active:
            await interaction.response.send_message("❌ Регистрация завершена.", ephemeral=True)
            return
        self.game.registration_time_left += 30
        await interaction.response.send_message(f"⏱️ Регистрация продлена на 30 сек! Осталось: {self.game.registration_time_left} сек.", ephemeral=False)
        await self.update_embed()

    @discord.ui.button(label="▶️ Начать игру", style=discord.ButtonStyle.success, row=1)
    async def start_game_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_creator_or_founder(interaction.user) and not is_high_staff(interaction.user):
            await interaction.response.send_message("❌ Доступно только руководству.", ephemeral=True)
            return
        if not self.game.registration_active:
            await interaction.response.send_message("❌ Игра уже начата.", ephemeral=True)
            return
        if len(self.game.participants) < 4:
            await interaction.response.send_message("❌ Минимум 4 игрока.", ephemeral=True)
            return
        self.game.registration_active = False
        if self.timer_task:
            self.timer_task.cancel()
        await self.start_game()
        await interaction.response.send_message("🚀 Игра запущена принудительно!", ephemeral=True)

    async def start_game(self):
        config = mafia_configs.get(self.game.channel.guild.id, {})
        participants = self.game.participants
        random.shuffle(participants)
        self.game.alive = participants[:]
        mafia_count = config.get("mafia", 1)
        doctor_count = config.get("doctor", 1)
        detective_count = config.get("detective", 0)
        barman_count = config.get("barman", 0)
        harlot_count = config.get("harlot", 0)
        if len(participants) >= 6:
            if detective_count == 0: detective_count = 1
            if harlot_count == 0: harlot_count = 1
        if len(participants) >= 8:
            if barman_count == 0: barman_count = 1
        if len(participants) >= 10:
            if mafia_count == 1: mafia_count = 2
        roles_to_assign = []
        for _ in range(mafia_count): roles_to_assign.append("Мафия")
        if mafia_count >= 1: roles_to_assign.append("Дон")
        for _ in range(doctor_count): roles_to_assign.append("Доктор")
        for _ in range(detective_count): roles_to_assign.append("Детектив")
        for _ in range(barman_count): roles_to_assign.append("Бармен")
        for _ in range(harlot_count): roles_to_assign.append("Путана")
        for i, p in enumerate(participants):
            if i < len(roles_to_assign):
                self.game.roles[p.id] = roles_to_assign[i]
            else:
                self.game.roles[p.id] = "Мирный житель"
        for p in participants:
            role = self.game.roles[p.id]
            try:
                await p.send(f"🎮 **Игра началась!**\nВаша роль: **{role}**\nСкоро наступит ночь.")
            except: pass
        embed = discord.Embed(title="🎬 Игра в Мафию Началась!", description=f"**Участников:** {len(participants)}\n🌙 Наступает ночь...", color=0x2ecc71)
        embed.set_footer(text="Роли разосланы в ЛС.")
        await self.game.channel.send(embed=embed)
        log_embed = discord.Embed(title="📋 Роли в игре", color=0x2ecc71)
        for p in participants:
            log_embed.add_field(name=p.display_name, value=self.game.roles[p.id], inline=True)
        await self.game.send_creator_log(log_embed)
        await self.game.start_night()

    @discord.ui.button(label="❌ Отменить игру", style=discord.ButtonStyle.danger, row=1)
    async def cancel_game_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_creator_or_founder(interaction.user) and not is_high_staff(interaction.user):
            await interaction.response.send_message("❌ Доступно только руководству.", ephemeral=True)
            return
        self.game.registration_active = False
        if self.timer_task:
            self.timer_task.cancel()
        for child in self.children:
            child.disabled = True
        await self.game.message.edit(view=self)
        await interaction.response.send_message(f"🛑 Игра отменена {interaction.user.mention}.")

@commands.command(name="голос")
async def vote(ctx, member: discord.Member):
    game = ctx.bot.mafia_game if hasattr(ctx.bot, 'mafia_game') else None
    if not game or game.game_over or game.night_phase: return
    if member == ctx.author:
        await ctx.send("❌ За себя нельзя!", delete_after=5)
        return
    if member not in game.alive:
        await ctx.send("❌ Этот игрок мёртв!", delete_after=5)
        return
    if ctx.author.id in game.votes:
        await ctx.send("❌ Вы уже проголосовали!", delete_after=5)
        return
    if member.id not in game.votes:
        game.votes[member.id] = []
    game.votes[member.id].append(ctx.author.id)
    await ctx.send(f"✅ Ваш голос учтен за {member.mention}!")

@app_commands.command(name="mafia_config", description="⚙️ Настроить количество ролей (Основатели)")
async def mafia_config(interaction: discord.Interaction, mafia: int = 1, doctor: int = 1, detective: int = 0, barman: int = 0, harlot: int = 0):
    if not is_creator_or_founder(interaction.user):
        await interaction.response.send_message("❌ Доступно только Основателям.", ephemeral=True)
        return
    mafia_configs[interaction.guild_id] = {"mafia": mafia, "doctor": doctor, "detective": detective, "barman": barman, "harlot": harlot}
    await interaction.response.send_message(f"✅ Настройки обновлены!\nМафия: {mafia}, Доктор: {doctor}, Детектив: {detective}, Бармен: {barman}, Путана: {harlot}", ephemeral=True)

# ==================== ОСТАЛЬНЫЕ СЛЭШ-КОМАНДЫ ====================
@app_commands.command(name="mcstatus", description="Показать статус и график онлайна Minecraft")
async def mcstatus_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await update_status_message(interaction.client)
    await interaction.followup.send("📊 Данные мониторинга в канале успешно обновлены!", ephemeral=True)

@app_commands.command(name="lk", description="📊 Показать личный кабинет (свой или другого игрока)")
@app_commands.describe(player="Никнейм или ID игрока (оставьте пустым для своего профиля)")
async def lk(interaction: discord.Interaction, player: str = None):
    if interaction.channel.id != LK_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Эта команда доступна только в канале <#{LK_CHANNEL_ID}>.", ephemeral=True)
        return
    await interaction.response.defer()
    users_data = await get_users_yml_sftp()
    if not users_data or "players" not in users_data:
        await interaction.followup.send("❌ Не удалось получить данные игроков с сервера.")
        return
    if not player:
        discord_id = str(interaction.user.id)
        result = await interaction.client.find_player_by_discord(discord_id, users_data)
        if not result:
            embed = discord.Embed(title="🔗 Привяжите аккаунт", description=("Вы не привязали Discord к Minecraft.\n\n" "**Как привязать:**\n" "1. Зайдите на сервер Minecraft.\n" "2. Напишите `/setdiscord " + interaction.user.name + " " + discord_id + "`\n" "3. После этого используйте `/lk` снова.\n\n" "Или посмотрите профиль другого игрока:\n" "`/lk <ник>` или `/lk id <ID>`"), color=0xe74c3c)
            await interaction.followup.send(embed=embed)
            return
        uuid, data = result
    else:
        if player.lower().startswith("id "):
            try:
                player_id = int(player.split(" ", 1)[1])
            except:
                await interaction.followup.send("❌ Неверный формат ID. Используйте: `/lk id 123`")
                return
            result = await interaction.client.find_player_by_id(player_id, users_data)
            if not result:
                await interaction.followup.send(f"❌ Игрок с ID `{player_id}` не найден.")
                return
            uuid, data = result
        else:
            result = await interaction.client.find_player_by_nick(player, users_data)
            if not result:
                await interaction.followup.send(f"❌ Игрок `{player}` не найден.")
                return
            uuid, data = result
    player_id = data.get("player-id", "—")
    discord_id = data.get("discord-id", "Не привязан")
    tag = data.get("tag", "")
    playtime = data.get("stats", {}).get("playtime", 0)
    deaths = data.get("stats", {}).get("deaths", 0)
    kills = data.get("stats", {}).get("killis", 0)
    balance = data.get("balance", 0.0)
    relics = data.get("relics", 0)
    groups_data = data.get("groups", [])
    groups_list = []
    for g in groups_data:
        gname = g.get("name", "unknown")
        expire = g.get("expire", -1)
        prefix = interaction.client.get_group_prefix(gname, users_data)
        display_name = f"{prefix} {gname}" if prefix else gname
        if expire == -1:
            groups_list.append(f"• {display_name} (бессрочно)")
        else:
            expire_date = datetime.fromtimestamp(expire / 1000).strftime("%d.%m.%Y %H:%M")
            groups_list.append(f"• {display_name} (до {expire_date})")
    groups_str = "\n".join(groups_list) if groups_list else "Нет групп"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.mojang.com/user/profile/{uuid}") as resp:
                if resp.status == 200:
                    profile_data = await resp.json()
                    nick = profile_data.get("name", "Неизвестно")
                else:
                    nick = "Неизвестно"
    except:
        nick = "Неизвестно"
    embed = discord.Embed(title=f"📊 Личный кабинет {nick}", color=0x5865F2, timestamp=datetime.now(MSK))
    embed.add_field(name="👤 Информация", value=(f"**Ник:** {nick}\n" f"**ID:** `{player_id}`\n" f"**Тег:** {tag if tag else '—'}\n" f"**Discord:** <@{discord_id}>" if discord_id != "Не привязан" else f"**Discord:** {discord_id}"), inline=False)
    embed.add_field(name="⚔️ Статистика", value=(f"**Время игры:** {format_time(playtime)}\n" f"**Убийств:** {kills}\n" f"**Смертей:** {deaths}\n" f"**K/D:** {(kills / deaths):.2f}" if deaths > 0 else "**K/D:** ∞"), inline=True)
    embed.add_field(name="💰 Экономика", value=(f"**Баланс:** {balance:.2f} монет\n" f"**Реликвии:** {relics} шт."), inline=True)
    embed.add_field(name="👑 Группы", value=groups_str[:1024], inline=False)
    embed.set_footer(text="Kingdom of Joy | Личный кабинет", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await interaction.followup.send(embed=embed)

@app_commands.command(name="bind", description="🔗 Привязать Discord к Minecraft аккаунту")
@app_commands.describe(nickname="Ваш ник в Minecraft", password="Пароль от аккаунта (для проверки)")
async def bind(interaction: discord.Interaction, nickname: str, password: str):
    if interaction.channel.id != LK_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Эта команда доступна только в канале <#{LK_CHANNEL_ID}>.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    discord_id = str(interaction.user.id)
    users_data = await get_users_yml_sftp()
    if not users_data or "players" not in users_data:
        await interaction.followup.send("❌ Ошибка чтения базы игроков с сервера.", ephemeral=True)
        return
    existing = await interaction.client.find_player_by_discord(discord_id, users_data)
    if existing:
        await interaction.followup.send("❌ Этот Discord уже привязан к игроку.", ephemeral=True)
        return
    uuid = await get_uuid_by_name(nickname)
    if not uuid:
        await interaction.followup.send(f"❌ Игрок `{nickname}` не найден в Minecraft.", ephemeral=True)
        return
    uuid_clean = uuid.replace("-", "")
    if uuid_clean not in users_data["players"]:
        await interaction.followup.send(f"❌ Игрок `{nickname}` не зарегистрирован на сервере.", ephemeral=True)
        return
    saved_password = users_data["players"][uuid_clean].get("password")
    if saved_password != password:
        await interaction.followup.send("❌ Неверный пароль!", ephemeral=True)
        return
    users_data["players"][uuid_clean]["discord-id"] = discord_id
    if await put_users_yml_sftp(users_data):
        await interaction.followup.send(f"✅ Аккаунт **{nickname}** успешно привязан к Discord!\nТеперь вы можете использовать `/lk` для просмотра профиля.", ephemeral=True)
        await send_log(interaction.guild, "🔗 Привязка Discord", f"Пользователь {interaction.user.mention} привязал аккаунт {nickname} (UUID: {uuid_clean})", color=0x2ecc71)
    else:
        await interaction.followup.send("❌ Ошибка сохранения данных на сервере. Обратитесь к администрации.", ephemeral=True)

@app_commands.command(name="chance", description="🎲 Узнать вероятность события (0% - 100%)")
async def chance(interaction: discord.Interaction, question: str):
    percentage = random.randint(0, 100)
    await interaction.response.send_message(make_blockquote(f"🎲 **Вопрос:** *{question}*\n📊 **Вероятность:** `{percentage}%`"))

@app_commands.command(name="sync", description="Синхронизировать слэш-команды бота (guild или global)")
async def sync_cmd(interaction: discord.Interaction, scope: str = "guild"):
    if interaction.user.id != 1437779380184158249:
        await interaction.response.send_message("❌ Доступно только Создателю.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        if scope.lower() == "guild":
            interaction.client.tree.copy_global_to(guild=interaction.guild)
            synced = await interaction.client.tree.sync(guild=interaction.guild)
            await interaction.followup.send(f"⚡ Слэш-команды гильдии синхронизированы! Загружено: `{len(synced)}`", ephemeral=True)
        else:
            synced = await interaction.client.tree.sync()
            await interaction.followup.send(f"🌐 Глобальная синхронизация запущена! Загружено: `{len(synced)}`.", ephemeral=True)
        await send_log(interaction.guild, "⚡ Выполнена Синхронизация", f"Создатель {interaction.user.mention} выполнил `/sync` (Режим: `{scope}`).", color=0x2ecc71)
    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: `{e}`", ephemeral=True)

@app_commands.command(name="test_welcome", description="Протестировать баннер приветствия в канале")
async def test_welcome(interaction: discord.Interaction):
    if interaction.user.id != 1437779380184158249: return
    await interaction.response.defer(ephemeral=True)
    banner_file = create_welcome_banner(interaction.user.display_name)
    embed = discord.Embed(title="👑 Новый Странник ступил в Kingdom of Joy!", description=f"Приветствуем тебя, {interaction.user.mention}!\nЗагляни в <#1520119059566559282> для навигации.", color=0x7864c8, timestamp=datetime.now(MSK))
    embed.set_image(url="attachment://welcome_banner.png")
    view = WelcomeButtonsView(interaction.guild_id)
    await interaction.channel.send(content=f"👋 {interaction.user.mention}", embed=embed, file=banner_file, view=view)
    await interaction.followup.send("✅ Приветствие отправлено!", ephemeral=True)

@app_commands.command(name="remind", description="Установить напоминание (Время в формате МСК)")
async def remind(interaction: discord.Interaction, time: str, text: str):
    unix_time = parse_time_or_unix(time)
    reminders = load_json(REMINDERS_FILE, [])
    reminders.append({"user_id": interaction.user.id, "channel_id": interaction.channel_id, "unix": unix_time, "text": text})
    save_json(REMINDERS_FILE, reminders)
    await interaction.response.send_message(make_blockquote(f"⏰ Напоминание записано на <t:{unix_time}:R>!"), ephemeral=True)

@app_commands.command(name="badwords", description="Настройка фильтра слов")
async def badwords(interaction: discord.Interaction, words: str, mute_time: str = "1h"):
    if not (interaction.user.id == 1437779380184158249 or any(r.id in [CREATOR_ROLE_ID, FOUNDER_ROLE_ID] for r in interaction.user.roles)): return
    word_list = [w.strip().lower() for w in words.split(",") if w.strip()]
    save_json(BADWORDS_FILE, {"words": word_list, "mute_time": mute_time})
    await interaction.response.send_message(f"✅ Фильтр обновлен: `{', '.join(word_list)}` | Мут: **{mute_time}**", ephemeral=True)
    await send_log(interaction.guild, "⚙️ Фильтр Слов Обновлен", f"Модератор {interaction.user.mention} установил фильтр: `{', '.join(word_list)}`", color=0x34495e)

@app_commands.command(name="warnlist", description="Список предупреждений")
async def warnlist(interaction: discord.Interaction):
    warns = load_json(WARNS_FILE, {})
    lines = [f"• <@{uid}>: **{count}/3** варнов" for uid, count in warns.items() if count > 0]
    await interaction.response.send_message(embed=discord.Embed(title="📜 Предупреждения", description="\n".join(lines) if lines else "Нет активных варнов.", color=0xe74c3c), ephemeral=True)

@app_commands.command(name="role", description="Выдать временную роль (например 10m, 2h)")
async def give_temp_role(interaction: discord.Interaction, user: discord.Member, role: discord.Role, duration: str):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ У вас нет прав для выполнения этой команды.", ephemeral=True)
        return
    if interaction.user.id != 1437779380184158249 and is_high_staff(user):
        await interaction.response.send_message("❌ Этот пользователь принадлежит к высшему составу и не может быть наказан.", ephemeral=True)
        return
    await user.add_roles(role)
    delta = parse_duration(duration)
    await interaction.response.send_message(make_blockquote(f"✅ Роль {role.mention} выдана {user.mention} на **{duration}**."))
    await send_log(interaction.guild, "🎭 Выдана Временная Роль", f"Модератор: {interaction.user.mention}\nЦель: {user.mention}\nРоль: {role.mention}\nСрок: `{duration}`", color=0x9b59b6)
    async def remove_later():
        await asyncio.sleep(delta.total_seconds())
        try:
            await user.remove_roles(role)
            await send_log(interaction.guild, "🎭 Снята Временная Роль", f"Роль {role.mention} у {user.mention} истекла и была снята.", color=0x95a5a6)
        except Exception: pass
    asyncio.create_task(remove_later())

@app_commands.command(name="warn", description="Выдать варн")
async def warn(interaction: discord.Interaction, user: discord.Member, reason: str = "Нарушение"):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ У вас нет прав для выполнения этой команды.", ephemeral=True)
        return
    if interaction.user.id != 1437779380184158249 and is_high_staff(user):
        await interaction.response.send_message("❌ Этот пользователь принадлежит к высшему составу и не может быть наказан.", ephemeral=True)
        return
    warns = load_json(WARNS_FILE, {})
    uid = str(user.id)
    count = warns.get(uid, 0) + 1
    if count >= 3:
        warns[uid] = 0
        save_json(WARNS_FILE, warns)
        await user.timeout(timedelta(days=1), reason="3/3 варна")
        await interaction.response.send_message(make_blockquote(f"⚡ {user.mention} получил 3/3 варнов и замучен на 1 день!"))
        await send_log(interaction.guild, "⛔ Авто-Мут (3/3 Варна)", f"Пользователь {user.mention} набрал 3 варна и отправлен в мут на 24 часа.", color=0xc0392b)
    else:
        warns[uid] = count
        save_json(WARNS_FILE, warns)
        await interaction.response.send_message(make_blockquote(f"⚠️ {user.mention} получил варн **({count}/3)**. Причина: *{reason}*"))
        await send_log(interaction.guild, "⚠️ Выдан Варн", f"Модератор: {interaction.user.mention}\nНарушитель: {user.mention}\nВарны: `{count}/3`\nПричина: *{reason}*", color=0xe67e22)

@app_commands.command(name="unwarn", description="Снять варн")
async def unwarn(interaction: discord.Interaction, user: discord.Member):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ У вас нет прав для выполнения этой команды.", ephemeral=True)
        return
    warns = load_json(WARNS_FILE, {})
    uid = str(user.id)
    if warns.get(uid, 0) > 0:
        warns[uid] -= 1
        save_json(WARNS_FILE, warns)
        await interaction.response.send_message(make_blockquote(f"✅ Варн снят с {user.mention}. Осталось: **{warns[uid]}/3**"))
        await send_log(interaction.guild, "🟢 Снят Варн", f"Модератор {interaction.user.mention} снял варн с {user.mention}. Остаток: `{warns[uid]}/3`", color=0x2ecc71)

@app_commands.command(name="mute", description="Мут")
async def mute(interaction: discord.Interaction, user: discord.Member, time: str, reason: str = "Нарушение"):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ У вас нет прав для выполнения этой команды.", ephemeral=True)
        return
    if interaction.user.id != 1437779380184158249 and is_high_staff(user):
        await interaction.response.send_message("❌ Этот пользователь принадлежит к высшему составу и не может быть наказан.", ephemeral=True)
        return
    duration = parse_duration(time)
    await user.timeout(duration, reason=reason)
    await interaction.response.send_message(make_blockquote(f"🔇 {user.mention} отправлен в мут на **{time}**."))
    await send_log(interaction.guild, "🔇 Выдан Мут", f"Модератор: {interaction.user.mention}\nНарушитель: {user.mention}\nСрок: `{time}`\nПричина: *{reason}*", color=0xe74c3c)

@app_commands.command(name="unmute", description="Размут")
async def unmute(interaction: discord.Interaction, user: discord.Member):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ У вас нет прав для выполнения этой команды.", ephemeral=True)
        return
    await user.timeout(None)
    await interaction.response.send_message(make_blockquote(f"🔊 {user.mention} размучен."))
    await send_log(interaction.guild, "🔊 Размут", f"Модератор {interaction.user.mention} размутил пользователя {user.mention}.", color=0x2ecc71)

@app_commands.command(name="ban", description="Бан")
async def ban(interaction: discord.Interaction, user: discord.Member, reason: str = "Нарушение"):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ У вас нет прав для выполнения этой команды.", ephemeral=True)
        return
    if interaction.user.id != 1437779380184158249 and is_high_staff(user):
        await interaction.response.send_message("❌ Этот пользователь принадлежит к высшему составу и не может быть наказан.", ephemeral=True)
        return
    await user.ban(reason=reason)
    await interaction.response.send_message(make_blockquote(f"🚫 {user.mention} забанен."))
    await send_log(interaction.guild, "🚫 Бан", f"Модератор {interaction.user.mention} забанил {user.mention}.\nПричина: *{reason}*", color=0x900c3f)

@app_commands.command(name="unban", description="Разбан")
async def unban(interaction: discord.Interaction, user_id: str):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ У вас нет прав для выполнения этой команды.", ephemeral=True)
        return
    user = await interaction.client.fetch_user(int(user_id))
    await interaction.guild.unban(user)
    await interaction.response.send_message(make_blockquote(f"🔓 Пользователь **{user.name}** разбанен."))
    await send_log(interaction.guild, "🔓 Разбан", f"Модератор {interaction.user.mention} разбанил {user.name} (ID: `{user.id}`).", color=0x2ecc71)

@app_commands.command(name="kick", description="👢 Кикнуть пользователя")
@app_commands.describe(user="Пользователь для кика", reason="Причина кика")
async def kick_cmd(interaction: discord.Interaction, user: discord.Member, reason: str = "Нарушение"):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ У вас нет прав для выполнения этой команды.", ephemeral=True)
        return
    if interaction.user.id != 1437779380184158249 and is_high_staff(user):
        await interaction.response.send_message("❌ Этот пользователь принадлежит к высшему составу и не может быть наказан.", ephemeral=True)
        return
    try:
        await user.kick(reason=reason)
        await interaction.response.send_message(make_blockquote(f"👢 {user.mention} был кикнут. Причина: *{reason}*"))
        await send_log(interaction.guild, "👢 Кик", f"Модератор {interaction.user.mention} кикнул {user.mention}.\nПричина: *{reason}*", color=0xecf0f1)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка при кике: {e}", ephemeral=True)

@app_commands.command(name="delete", description="Очистка чата")
async def delete(interaction: discord.Interaction, amount: str):
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ У вас нет прав для выполнения этой команды.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    limit = 1000 if amount.lower() == "all" else int(amount)
    deleted = await interaction.channel.purge(limit=limit)
    await interaction.followup.send(make_blockquote(f"🧹 Удалено {len(deleted)} сообщений."), ephemeral=True)
    await send_log(interaction.guild, "🧹 Очистка ЧАТА", f"Модератор {interaction.user.mention} очистил `{len(deleted)}` сообщений в канале {interaction.channel.mention}.", color=0x34495e)

@app_commands.command(name="staff", description="Состав Администрации")
async def staff(interaction: discord.Interaction):
    guild = interaction.guild
    await guild.chunk()
    founders, creators, moderators = [], [], []
    for m in guild.members:
        rids = [r.id for r in m.roles]
        if FOUNDER_ROLE_ID in rids: founders.append(m)
        elif CREATOR_ROLE_ID in rids or m.id == 1437779380184158249: creators.append(m)
        elif MODERATOR_ROLE_ID in rids or CHAT_MODERATOR_ROLE_ID in rids: moderators.append(m)
    embed = discord.Embed(title="🛡️ Администрация Kingdom of Joy", color=0x2b2d31, timestamp=datetime.now(MSK))
    embed.add_field(name="👑 1. Основатели", value="\n".join([f"• <@{m.id}>" for m in founders]) if founders else "• *Нет*", inline=False)
    embed.add_field(name="✨ 2. Создатели", value="\n".join([f"• <@{m.id}>" for m in creators]) if creators else "• *Нет*", inline=False)
    embed.add_field(name="🛡️ 3. Модераторы", value="\n".join([f"• <@{m.id}>" for m in moderators]) if moderators else "• *Нет*", inline=False)
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="setup_support", description="Обновить и выставить монументальную панель поддержки")
async def setup_support(interaction: discord.Interaction):
    if interaction.user.id != 1437779380184158249: return
    await interaction.response.defer(ephemeral=True)
    channel = interaction.guild.get_channel(SUPPORT_CHANNEL_ID)
    if not channel:
        await interaction.followup.send("❌ Канал поддержки не найден!", ephemeral=True)
        return
    embed = discord.Embed(title="✨ **ЦЕНТР ПОДДЕРЖКИ И УПРАВЛЕНИЯ «KINGDOM OF JOY»**", description=("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nПриветствуем вас в официальном центре обращений нашего сервера!\nЗдесь вы можете связаться с руководством, заявить о нарушении или предложить идею.\n\n📌 **ОБЩИЙ СВОД ПРАВИЛ ПОДАЧИ ОБРАЩЕНИЙ:**\n• **Уважение:** Излагайте суть обращения спокойно и вежливо.\n• **Доказательства:** В случае жалобы сразу прикрепляйте медиафайлы.\n• **Терпение:** Ответственные сотрудники отреагируют в ближайшее время.\n• **Запрещено:** Создавать ложные тикеты, флудить и спамить кнопками.\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"), color=0x7864c8, timestamp=datetime.now(MSK))
    embed.add_field(name="⚠️ **1. Отдел Жалоб**", value="Подача претензий на игроков или членов администрации. Обязательны прямые доказательства.", inline=False)
    embed.add_field(name="💡 **2. Предложить Идею**", value="Отправка ваших уникальных идей по улучшению дискорда, ивентов и игровых серверов.", inline=False)
    embed.add_field(name="💎 **3. Поддержка и Донат**", value="Вопросы по покупке привилегий, подпискам, спонсорству и развитию проекта.", inline=False)
    embed.add_field(name="💻 **4. Технический Разработчик**", value="Прямая связь с разработчиком бота и технической части серверов для багрепортов.", inline=False)
    embed.add_field(name="👑 **5. Высшее Руководство**", value="Приватный сектор общения лично с Создателем и Основателями проекта.", inline=False)
    embed.set_image(url="attachment://support_banner.png")
    embed.set_footer(text="Kingdom of Joy | Support System", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    banner_file = create_support_banner()
    msg = await channel.send(embed=embed, file=banner_file, view=SupportHubView())
    save_json(SUPPORT_CONFIG_FILE, {"support_message_id": msg.id})
    await interaction.followup.send("✅ Монументальная панель поддержки успешно отправлена и настроена!", ephemeral=True)

@app_commands.command(name="setup_applications", description="Настроить канал заявок (отправить сообщение с кнопками)")
async def setup_applications(interaction: discord.Interaction):
    if interaction.user.id != 1437779380184158249:
        await interaction.response.send_message("❌ Доступно только Создателю.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    channel = interaction.guild.get_channel(APPLICATIONS_CHANNEL_ID)
    if not channel:
        await interaction.followup.send("❌ Канал заявок не найден!", ephemeral=True)
        return
    embed = discord.Embed(title="📩 **Подача заявок на должности**", description=("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nЗдесь вы можете подать заявку на одну из следующих должностей:\n\n🗺️ **Маппер** – создание карт и уровней.\n🛡️ **Модератор чата** – поддержание порядка в общем чате.\n🎬 **Киноклуб** – организация совместных просмотров фильмов.\n👩 **Девушка** – получение специального статуса.\n\n📌 **Инструкция:**\n1. Выберите тип заявки в меню ниже.\n2. Заполните анкету (все поля обязательны).\n3. После отправки ваша заявка будет рассмотрена высшим составом.\n4. Решение будет принято в течение нескольких дней.\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"), color=0x5865F2, timestamp=datetime.now(MSK))
    embed.set_footer(text="Kingdom of Joy | Applications", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    view = ApplicationView()
    await channel.send(embed=embed, view=view)
    await interaction.followup.send("✅ Сообщение с заявками отправлено в канал!", ephemeral=True)

@app_commands.command(name="messages", description="📊 Показать количество сообщений и уровень")
@app_commands.describe(user="Пользователь (оставьте пустым для себя)")
async def messages(interaction: discord.Interaction, user: discord.Member = None):
    if interaction.channel.id != BOT_CHANNEL:
        await interaction.response.send_message(f"❌ Эта команда доступна только в канале <#{BOT_CHANNEL}>.", ephemeral=True)
        return
    target = user or interaction.user
    counts = load_message_counts()
    count = counts.get(str(target.id), 0)
    level = get_level(count)
    embed = discord.Embed(title=f"📊 Статистика сообщений", color=0x5865F2, timestamp=datetime.now(MSK))
    embed.add_field(name="👤 Пользователь", value=target.mention, inline=False)
    embed.add_field(name="✉️ Сообщений", value=f"`{count}`", inline=True)
    embed.add_field(name="🏆 Уровень", value=f"`{level}` из 20", inline=True)
    embed.set_footer(text="Kingdom of Joy | Статистика", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="top", description="🏆 Топ-10 по сообщениям")
async def top(interaction: discord.Interaction):
    if interaction.channel.id != BOT_CHANNEL:
        await interaction.response.send_message(f"❌ Эта команда доступна только в канале <#{BOT_CHANNEL}>.", ephemeral=True)
        return
    counts = load_message_counts()
    if not counts:
        await interaction.response.send_message("❌ Нет данных.")
        return
    sorted_users = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="🏆 Топ-10 по сообщениям", color=0xf1c40f, timestamp=datetime.now(MSK))
    medals = ["🥇", "🥈", "🥉"]
    description = ""
    for i, (user_id, count) in enumerate(sorted_users):
        try:
            user = await interaction.client.fetch_user(int(user_id))
            name = user.display_name
        except:
            name = f"Неизвестный ({user_id})"
        medal = medals[i] if i < 3 else f"`#{i+1}`"
        description += f"{medal} **{name}** — `{count}` сообщений\n"
    embed.description = description
    embed.set_footer(text="Kingdom of Joy | Топ", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="setmessages", description="⚙️ Установить точное количество сообщений пользователю")
@app_commands.describe(user="Пользователь", count="Новое количество")
async def setmessages(interaction: discord.Interaction, user: discord.Member, count: int):
    await interaction.response.defer(ephemeral=True)
    try:
        if not any(r.id == 1526681612337549343 for r in interaction.user.roles) and interaction.user.id not in CREATOR_AND_ROLE_IDS:
            await interaction.followup.send("❌ Доступно только руководству проекта.", ephemeral=True)
            return
        if count < 0:
            await interaction.followup.send("❌ Количество не может быть отрицательным.", ephemeral=True)
            return
        counts = load_message_counts()
        counts[str(user.id)] = count
        save_message_counts(counts)
        await update_user_level(interaction.client, user, count, interaction.channel)
        await interaction.followup.send(f"✅ Пользователю {user.mention} установлено `{count}` сообщений.", ephemeral=True)
        await send_log(interaction.guild, "⚙️ Установлено сообщений", f"Руководство {interaction.user.mention} установило {user.mention} сообщений = {count}", color=0x3498db)
    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)

@app_commands.command(name="addmessages", description="➕ Добавить сообщения пользователю")
@app_commands.describe(user="Пользователь", amount="Количество для добавления")
async def addmessages(interaction: discord.Interaction, user: discord.Member, amount: int):
    await interaction.response.defer(ephemeral=True)
    try:
        if not any(r.id == 1526681612337549343 for r in interaction.user.roles) and interaction.user.id not in CREATOR_AND_ROLE_IDS:
            await interaction.followup.send("❌ Доступно только руководству проекта.", ephemeral=True)
            return
        if amount < 0:
            await interaction.followup.send("❌ Количество не может быть отрицательным.", ephemeral=True)
            return
        counts = load_message_counts()
        current = counts.get(str(user.id), 0)
        new_count = current + amount
        counts[str(user.id)] = new_count
        save_message_counts(counts)
        await update_user_level(interaction.client, user, new_count, interaction.channel)
        await interaction.followup.send(f"✅ Пользователю {user.mention} добавлено `{amount}` сообщений. Теперь: `{new_count}`.", ephemeral=True)
        await send_log(interaction.guild, "➕ Добавлены сообщения", f"Руководство {interaction.user.mention} добавил {user.mention} +{amount} сообщений (теперь {new_count})", color=0x2ecc71)
    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)

@app_commands.command(name="resetmessages", description="🔄 Обнулить счётчики всем авторизованным пользователям (дать 1 уровень)")
async def resetmessages(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        if not any(r.id == 1526681612337549343 for r in interaction.user.roles) and interaction.user.id not in CREATOR_AND_ROLE_IDS:
            await interaction.followup.send("❌ Доступно только руководству проекта.", ephemeral=True)
            return
        await interaction.followup.send("⚠️ Вы уверены, что хотите обнулить счётчики ВСЕМ авторизованным пользователям? Напишите `подтвердить` в течение 30 секунд.", ephemeral=True)
        def check(msg): return msg.author == interaction.user and msg.content.lower() == "подтвердить" and msg.channel == interaction.channel
        try:
            await interaction.client.wait_for("message", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("❌ Операция отменена (таймаут).", ephemeral=True)
            return
        counts = load_message_counts()
        guild = interaction.guild
        role_1 = guild.get_role(ROLE_1)
        role_5 = guild.get_role(ROLE_5)
        role_10 = guild.get_role(ROLE_10)
        role_15 = guild.get_role(ROLE_15)
        role_20 = guild.get_role(ROLE_20)
        for user_id in list(counts.keys()):
            member = guild.get_member(int(user_id))
            if member and VERIFY_ROLE_ID in [r.id for r in member.roles]:
                counts[user_id] = 0
                await member.remove_roles(role_1, role_5, role_10, role_15, role_20, reason="Обнуление счётчика сообщений")
                if role_1: await member.add_roles(role_1, reason="Обнуление счётчика сообщений (уровень 1)")
                interaction.client.user_level_cache[member.id] = 1
        save_message_counts(counts)
        await interaction.followup.send("✅ Счётчики всех авторизованных пользователей обнулены, выдана роль 1 уровня.", ephemeral=True)
        await send_log(interaction.guild, "🔄 Обнуление счётчиков", f"Руководство {interaction.user.mention} обнулило счётчики всех авторизованных.", color=0xe67e22)
    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)

@app_commands.command(name="send", description="📨 Отправить объявление/сообщение в канал (только для руководства)")
@app_commands.describe(text="Текст сообщения", color="Цвет в HEX (например #ff0000 или ff0000)")
async def send_cmd(interaction: discord.Interaction, text: str, color: str = None):
    if not any(r.id == 1526681612337549343 for r in interaction.user.roles) and interaction.user.id not in CREATOR_AND_ROLE_IDS:
        await interaction.response.send_message("❌ У вас нет прав на использование этой команды.", ephemeral=True)
        return
    embed_color = 0x5865F2
    if color:
        clean_hex = color.lstrip('#')
        try:
            embed_color = int(clean_hex, 16)
        except ValueError:
            embed_color = 0x5865F2
    embed = discord.Embed(description=text, color=embed_color, timestamp=datetime.now(MSK))
    embed.set_footer(text="Kingdom of Joy | Объявление", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await interaction.response.send_message(embed=embed)
    await send_log(interaction.guild, "📨 Отправлено объявление", f"Руководство {interaction.user.mention} отправил объявление в канале {interaction.channel.mention}", color=embed_color)

# ==================== ИГРОВЫЕ ДАННЫЕ (MINECRAFT SFTP) ====================
@app_commands.command(name="addgroup", description="👑 Выдать группу игроку")
@app_commands.describe(nickname="Ник игрока", group="Название группы", duration="Время (1d, 2h, 30m, 10s) или оставьте пустым для бессрочной")
async def addgroup(interaction: discord.Interaction, nickname: str, group: str, duration: str = None):
    if interaction.channel.id != LK_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Эта команда доступна только в канале <#{LK_CHANNEL_ID}>.", ephemeral=True)
        return
    if not is_high_staff(interaction.user):
        await interaction.response.send_message("❌ Доступно только руководству проекта.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    users_data = await get_users_yml_sftp()
    if not users_data or "players" not in users_data:
        await interaction.followup.send("❌ Ошибка чтения базы игроков.")
        return
    found = await interaction.client.find_player_by_nick(nickname, users_data)
    if not found:
        await interaction.followup.send(f"❌ Игрок `{nickname}` не найден.")
        return
    uuid, data = found
    groups = data.get("groups", [])
    for g in groups:
        if g.get("name") == group:
            await interaction.followup.send(f"❌ У игрока уже есть группа `{group}`. Сначала удалите её.")
            return
    expire = -1
    duration_str = "бессрочно"
    if duration:
        seconds = int(parse_duration(duration).total_seconds())
        if seconds <= 0:
            await interaction.followup.send("❌ Неверный формат времени. Используйте: 1d, 2h, 30m, 10s")
            return
        expire = int((datetime.now(MSK) + timedelta(seconds=seconds)).timestamp() * 1000)
        duration_str = duration
    groups.append({"name": group, "expire": expire})
    users_data["players"][uuid]["groups"] = groups
    if await put_users_yml_sftp(users_data):
        await interaction.followup.send(f"✅ Группа `{group}` выдана игроку **{nickname}** (срок: {duration_str})")
        await send_log(interaction.guild, "👑 Выдана группа", f"Руководство {interaction.user.mention} выдал группу `{group}` игроку **{nickname}** (срок: {duration_str})", color=0xf1c40f)
    else:
        await interaction.followup.send("❌ Ошибка сохранения данных.")

@app_commands.command(name="removegroup", description="🗑️ Удалить группу у игрока")
@app_commands.describe(nickname="Ник игрока", group="Название группы")
async def removegroup(interaction: discord.Interaction, nickname: str, group: str):
    if interaction.channel.id != LK_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Эта команда доступна только в канале <#{LK_CHANNEL_ID}>.", ephemeral=True)
        return
    if not is_high_staff(interaction.user):
        await interaction.response.send_message("❌ Доступно только руководству проекта.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    users_data = await get_users_yml_sftp()
    if not users_data or "players" not in users_data:
        await interaction.followup.send("❌ Ошибка чтения базы игроков.")
        return
    found = await interaction.client.find_player_by_nick(nickname, users_data)
    if not found:
        await interaction.followup.send(f"❌ Игрок `{nickname}` не найден.")
        return
    uuid, data = found
    groups = data.get("groups", [])
    original_len = len(groups)
    groups = [g for g in groups if g.get("name") != group]
    if len(groups) == original_len:
        await interaction.followup.send(f"❌ У игрока нет группы `{group}`.")
        return
    users_data["players"][uuid]["groups"] = groups
    if await put_users_yml_sftp(users_data):
        await interaction.followup.send(f"✅ Группа `{group}` удалена у игрока **{nickname}**")
        await send_log(interaction.guild, "🗑️ Удалена группа", f"Руководство {interaction.user.mention} удалил группу `{group}` у игрока **{nickname}**", color=0xe74c3c)
    else:
        await interaction.followup.send("❌ Ошибка сохранения данных.")

@app_commands.command(name="listgroups", description="📋 Показать все группы игрока")
@app_commands.describe(nickname="Ник игрока")
async def listgroups(interaction: discord.Interaction, nickname: str):
    if interaction.channel.id != LK_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Эта команда доступна только в канале <#{LK_CHANNEL_ID}>.", ephemeral=True)
        return
    if not is_high_staff(interaction.user):
        await interaction.response.send_message("❌ Доступно только руководству проекта.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    users_data = await get_users_yml_sftp()
    if not users_data or "players" not in users_data:
        await interaction.followup.send("❌ Ошибка чтения базы игроков.")
        return
    found = await interaction.client.find_player_by_nick(nickname, users_data)
    if not found:
        await interaction.followup.send(f"❌ Игрок `{nickname}` не найден.")
        return
    uuid, data = found
    groups = data.get("groups", [])
    if not groups:
        await interaction.followup.send(f"У игрока **{nickname}** нет групп.")
        return
    lines = []
    for g in groups:
        gname = g.get("name", "unknown")
        expire = g.get("expire", -1)
        if expire == -1:
            lines.append(f"• {gname} (бессрочно)")
        else:
            remaining = (expire // 1000) - int(datetime.now(MSK).timestamp())
            if remaining > 0:
                lines.append(f"• {gname} (осталось {format_time(remaining)})")
            else:
                lines.append(f"• {gname} (истекла)")
    embed = discord.Embed(title=f"📋 Группы игрока {nickname}", description="\n".join(lines), color=0x5865F2, timestamp=datetime.now(MSK))
    await interaction.followup.send(embed=embed)

@app_commands.command(name="setbalance", description="💰 Установить баланс игроку")
@app_commands.describe(nickname="Ник игрока", amount="Сумма")
async def setbalance(interaction: discord.Interaction, nickname: str, amount: float):
    if interaction.channel.id != LK_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Эта команда доступна только в канале <#{LK_CHANNEL_ID}>.", ephemeral=True)
        return
    if not is_high_staff(interaction.user):
        await interaction.response.send_message("❌ Доступно только руководству проекта.", ephemeral=True)
        return
    if amount < 0:
        await interaction.response.send_message("❌ Сумма не может быть отрицательной.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    users_data = await get_users_yml_sftp()
    if not users_data or "players" not in users_data:
        await interaction.followup.send("❌ Ошибка чтения базы игроков.")
        return
    found = await interaction.client.find_player_by_nick(nickname, users_data)
    if not found:
        await interaction.followup.send(f"❌ Игрок `{nickname}` не найден.")
        return
    uuid, data = found
    users_data["players"][uuid]["balance"] = amount
    if await put_users_yml_sftp(users_data):
        await interaction.followup.send(f"✅ Баланс игрока **{nickname}** установлен на `{amount:.2f}` монет")
        await send_log(interaction.guild, "💰 Установлен баланс", f"Руководство {interaction.user.mention} установил баланс игрока **{nickname}** = {amount:.2f}", color=0x2ecc71)
    else:
        await interaction.followup.send("❌ Ошибка сохранения данных.")

@app_commands.command(name="addbalance", description="➕ Добавить монеты игроку")
@app_commands.describe(nickname="Ник игрока", amount="Сумма")
async def addbalance(interaction: discord.Interaction, nickname: str, amount: float):
    if interaction.channel.id != LK_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Эта команда доступна только в канале <#{LK_CHANNEL_ID}>.", ephemeral=True)
        return
    if not is_high_staff(interaction.user):
        await interaction.response.send_message("❌ Доступно только руководству проекта.", ephemeral=True)
        return
    if amount <= 0:
        await interaction.response.send_message("❌ Сумма должна быть больше 0.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    users_data = await get_users_yml_sftp()
    if not users_data or "players" not in users_data:
        await interaction.followup.send("❌ Ошибка чтения базы игроков.")
        return
    found = await interaction.client.find_player_by_nick(nickname, users_data)
    if not found:
        await interaction.followup.send(f"❌ Игрок `{nickname}` не найден.")
        return
    uuid, data = found
    current = data.get("balance", 0.0)
    users_data["players"][uuid]["balance"] = current + amount
    if await put_users_yml_sftp(users_data):
        await interaction.followup.send(f"✅ Добавлено `{amount:.2f}` монет игроку **{nickname}** (теперь: {current + amount:.2f})")
        await send_log(interaction.guild, "➕ Добавлены монеты", f"Руководство {interaction.user.mention} добавил {amount:.2f} монет игроку **{nickname}**", color=0x2ecc71)
    else:
        await interaction.followup.send("❌ Ошибка сохранения данных.")

@app_commands.command(name="takebalance", description="➖ Снять монеты у игрока")
@app_commands.describe(nickname="Ник игрока", amount="Сумма")
async def takebalance(interaction: discord.Interaction, nickname: str, amount: float):
    if interaction.channel.id != LK_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Эта команда доступна только в канале <#{LK_CHANNEL_ID}>.", ephemeral=True)
        return
    if not is_high_staff(interaction.user):
        await interaction.response.send_message("❌ Доступно только руководству проекта.", ephemeral=True)
        return
    if amount <= 0:
        await interaction.response.send_message("❌ Сумма должна быть больше 0.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    users_data = await get_users_yml_sftp()
    if not users_data or "players" not in users_data:
        await interaction.followup.send("❌ Ошибка чтения базы игроков.")
        return
    found = await interaction.client.find_player_by_nick(nickname, users_data)
    if not found:
        await interaction.followup.send(f"❌ Игрок `{nickname}` не найден.")
        return
    uuid, data = found
    current = data.get("balance", 0.0)
    if current < amount:
        await interaction.followup.send(f"❌ У игрока **{nickname}** недостаточно монет (есть: {current:.2f})")
        return
    users_data["players"][uuid]["balance"] = current - amount
    if await put_users_yml_sftp(users_data):
        await interaction.followup.send(f"✅ Снято `{amount:.2f}` монет у игрока **{nickname}** (осталось: {current - amount:.2f})")
        await send_log(interaction.guild, "➖ Сняты монеты", f"Руководство {interaction.user.mention} снял {amount:.2f} монет у игрока **{nickname}**", color=0xe74c3c)
    else:
        await interaction.followup.send("❌ Ошибка сохранения данных.")

@app_commands.command(name="setrelic", description="💎 Установить реликвии игроку")
@app_commands.describe(nickname="Ник игрока", amount="Количество")
async def setrelic(interaction: discord.Interaction, nickname: str, amount: int):
    if interaction.channel.id != LK_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Эта команда доступна только в канале <#{LK_CHANNEL_ID}>.", ephemeral=True)
        return
    if not is_high_staff(interaction.user):
        await interaction.response.send_message("❌ Доступно только руководству проекта.", ephemeral=True)
        return
    if amount < 0:
        await interaction.response.send_message("❌ Количество не может быть отрицательным.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    users_data = await get_users_yml_sftp()
    if not users_data or "players" not in users_data:
        await interaction.followup.send("❌ Ошибка чтения базы игроков.")
        return
    found = await interaction.client.find_player_by_nick(nickname, users_data)
    if not found:
        await interaction.followup.send(f"❌ Игрок `{nickname}` не найден.")
        return
    uuid, data = found
    users_data["players"][uuid]["relics"] = amount
    if await put_users_yml_sftp(users_data):
        await interaction.followup.send(f"✅ Реликвии игрока **{nickname}** установлены на `{amount}` шт.")
        await send_log(interaction.guild, "💎 Установлены реликвии", f"Руководство {interaction.user.mention} установил реликвии игрока **{nickname}** = {amount}", color=0x9b59b6)
    else:
        await interaction.followup.send("❌ Ошибка сохранения данных.")

@app_commands.command(name="addrelic", description="➕ Добавить реликвии игроку")
@app_commands.describe(nickname="Ник игрока", amount="Количество")
async def addrelic(interaction: discord.Interaction, nickname: str, amount: int):
    if interaction.channel.id != LK_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Эта команда доступна только в канале <#{LK_CHANNEL_ID}>.", ephemeral=True)
        return
    if not is_high_staff(interaction.user):
        await interaction.response.send_message("❌ Доступно только руководству проекта.", ephemeral=True)
        return
    if amount <= 0:
        await interaction.response.send_message("❌ Количество должно быть больше 0.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    users_data = await get_users_yml_sftp()
    if not users_data or "players" not in users_data:
        await interaction.followup.send("❌ Ошибка чтения базы игроков.")
        return
    found = await interaction.client.find_player_by_nick(nickname, users_data)
    if not found:
        await interaction.followup.send(f"❌ Игрок `{nickname}` не найден.")
        return
    uuid, data = found
    current = data.get("relics", 0)
    users_data["players"][uuid]["relics"] = current + amount
    if await put_users_yml_sftp(users_data):
        await interaction.followup.send(f"✅ Добавлено `{amount}` реликвий игроку **{nickname}** (теперь: {current + amount})")
        await send_log(interaction.guild, "➕ Добавлены реликвии", f"Руководство {interaction.user.mention} добавил {amount} реликвий игроку **{nickname}**", color=0x9b59b6)
    else:
        await interaction.followup.send("❌ Ошибка сохранения данных.")

@app_commands.command(name="takerelic", description="➖ Снять реликвии у игрока")
@app_commands.describe(nickname="Ник игрока", amount="Количество")
async def takerelic(interaction: discord.Interaction, nickname: str, amount: int):
    if interaction.channel.id != LK_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Эта команда доступна только в канале <#{LK_CHANNEL_ID}>.", ephemeral=True)
        return
    if not is_high_staff(interaction.user):
        await interaction.response.send_message("❌ Доступно только руководству проекта.", ephemeral=True)
        return
    if amount <= 0:
        await interaction.response.send_message("❌ Количество должно быть больше 0.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    users_data = await get_users_yml_sftp()
    if not users_data or "players" not in users_data:
        await interaction.followup.send("❌ Ошибка чтения базы игроков.")
        return
    found = await interaction.client.find_player_by_nick(nickname, users_data)
    if not found:
        await interaction.followup.send(f"❌ Игрок `{nickname}` не найден.")
        return
    uuid, data = found
    current = data.get("relics", 0)
    if current < amount:
        await interaction.followup.send(f"❌ У игрока **{nickname}** недостаточно реликвий (есть: {current})")
        return
    users_data["players"][uuid]["relics"] = current - amount
    if await put_users_yml_sftp(users_data):
        await interaction.followup.send(f"✅ Снято `{amount}` реликвий у игрока **{nickname}** (осталось: {current - amount})")
        await send_log(interaction.guild, "➖ Сняты реликвии", f"Руководство {interaction.user.mention} снял {amount} реликвий у игрока **{nickname}**", color=0xe74c3c)
    else:
        await interaction.followup.send("❌ Ошибка сохранения данных.")

@app_commands.command(name="resetplayer", description="🔄 Сбросить все данные игрока (группы, баланс, реликвии)")
@app_commands.describe(nickname="Ник игрока")
async def resetplayer(interaction: discord.Interaction, nickname: str):
    if interaction.channel.id != LK_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Эта команда доступна только в канале <#{LK_CHANNEL_ID}>.", ephemeral=True)
        return
    if not is_high_staff(interaction.user):
        await interaction.response.send_message("❌ Доступно только руководству проекта.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    users_data = await get_users_yml_sftp()
    if not users_data or "players" not in users_data:
        await interaction.followup.send("❌ Ошибка чтения базы игроков.")
        return
    found = await interaction.client.find_player_by_nick(nickname, users_data)
    if not found:
        await interaction.followup.send(f"❌ Игрок `{nickname}` не найден.")
        return
    uuid, data = found
    users_data["players"][uuid]["groups"] = []
    users_data["players"][uuid]["balance"] = 0.0
    users_data["players"][uuid]["relics"] = 0
    if await put_users_yml_sftp(users_data):
        await interaction.followup.send(f"✅ Данные игрока **{nickname}** сброшены (группы, баланс, реликвии обнулены)")
        await send_log(interaction.guild, "🔄 Сброс игрока", f"Руководство {interaction.user.mention} сбросил данные игрока **{nickname}**", color=0xe67e22)
    else:
        await interaction.followup.send("❌ Ошибка сохранения данных.")

# ==================== НОВЫЕ КОМАНДЫ ДЛЯ ГИФОК ПО ССЫЛКАМ ====================
GIF_STORAGE_FILE = "gif_storage.json"

def load_gifs():
    return load_json(GIF_STORAGE_FILE, {"morning": [], "night": []})

def save_gifs(data):
    save_json(GIF_STORAGE_FILE, data)

@app_commands.command(name="add_gif_url", description="Добавить URL гифки в хранилище (Только для руководства)")
@app_commands.describe(thread_type="В какую категорию добавить", gif_url="Прямая ссылка на гифку")
@app_commands.choices(thread_type=[
    app_commands.Choice(name="Доброе утро", value="morning"),
    app_commands.Choice(name="Доброй ночи", value="night")
])
async def add_gif_url(interaction: discord.Interaction, thread_type: str, gif_url: str):
    if not is_creator_or_founder(interaction.user) and not is_high_staff(interaction.user):
        await interaction.response.send_message("❌ Только руководство может добавлять гифки.", ephemeral=True)
        return

    gifs = load_gifs()
    if gif_url in gifs[thread_type]:
        await interaction.response.send_message("❌ Эта ссылка уже существует в данной категории.", ephemeral=True)
        return

    gifs[thread_type].append(gif_url)
    save_gifs(gifs)
    await interaction.response.send_message(f"✅ URL гифки успешно добавлен в категорию '{'доброе утро' if thread_type == 'morning' else 'доброй ночи'}'!", ephemeral=True)

@app_commands.command(name="remove_gif_url", description="Удалить URL гифки из хранилища (Только для руководства)")
@app_commands.describe(thread_type="Из какой категории удалить", gif_url="Прямая ссылка на гифку для удаления")
@app_commands.choices(thread_type=[
    app_commands.Choice(name="Доброе утро", value="morning"),
    app_commands.Choice(name="Доброй ночи", value="night")
])
async def remove_gif_url(interaction: discord.Interaction, thread_type: str, gif_url: str):
    if not is_creator_or_founder(interaction.user) and not is_high_staff(interaction.user):
        await interaction.response.send_message("❌ Только руководство может удалять гифки.", ephemeral=True)
        return

    gifs = load_gifs()
    if gif_url not in gifs[thread_type]:
        await interaction.response.send_message("❌ Данная ссылка не найдена в указанной категории.", ephemeral=True)
        return

    gifs[thread_type].remove(gif_url)
    save_gifs(gifs)
    await interaction.response.send_message(f"✅ URL гифки успешно удалён из категории.", ephemeral=True)

@app_commands.command(name="list_gif_urls", description="Показать все сохранённые URL гифок в категории")
@app_commands.describe(thread_type="Выберите категорию")
@app_commands.choices(thread_type=[
    app_commands.Choice(name="Доброе утро", value="morning"),
    app_commands.Choice(name="Доброй ночи", value="night")
])
async def list_gif_urls(interaction: discord.Interaction, thread_type: str):
    gifs = load_gifs()
    data = gifs[thread_type]
    if not data:
        await interaction.response.send_message(f"📭 В категории '{'доброе утро' if thread_type == 'morning' else 'доброй ночи'}' пока нет сохранённых гифок.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"📋 Список URL гифок: {'Утро' if thread_type == 'morning' else 'Ночь'}",
        description="\n".join([f"`{i+1}.` {url}" for i, url in enumerate(data)]),
        color=0x5865F2
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== UI КОМПОНЕНТЫ И АНКЕТЫ ====================
class WelcomeButtonsView(discord.ui.View):
    def __init__(self, guild_id: int = 0):
        super().__init__(timeout=None)
        g_id = guild_id if guild_id else '@me'
        self.add_item(discord.ui.Button(label="📢 Новости", style=discord.ButtonStyle.link, url=f"https://discord.com/channels/{g_id}/1505126425022300275", row=0))
        self.add_item(discord.ui.Button(label="💬 Основной Чат", style=discord.ButtonStyle.link, url=f"https://discord.com/channels/{g_id}/1505239843486306374", row=0))
        self.add_item(discord.ui.Button(label="📜 Законы сервера", style=discord.ButtonStyle.link, url=f"https://discord.com/channels/{g_id}/1523064602080841728", row=1))
        self.add_item(discord.ui.Button(label="📚 Информация", style=discord.ButtonStyle.link, url=f"https://discord.com/channels/{g_id}/1519998391390834698", row=1))
        self.add_item(discord.ui.Button(label="🛠️ Тех. Поддержка", style=discord.ButtonStyle.link, url=f"https://discord.com/channels/{g_id}/1526688069464625305", row=2))

class IdeaModal(discord.ui.Modal, title="💡 Подача предложения"):
    idea_title = discord.ui.TextInput(label="Суть идеи", placeholder="Кратко изложи суть предложения...", max_length=100)
    idea_desc = discord.ui.TextInput(label="Подробные детали", placeholder="Опиши детально, как это улучшит проект...", style=discord.TextStyle.paragraph, max_length=1000)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        thread = await interaction.channel.create_thread(name=f"💡-идея-{interaction.user.name}", type=discord.ChannelType.private_thread, invitable=False)
        await thread.add_user(interaction.user)
        await interaction.followup.send(f"✨ Твоё предложение успешно отправлено в личный сектор: {thread.mention}", ephemeral=True)
        embed = discord.Embed(title=f"💡 Идея от {interaction.user.display_name}", color=0x7864c8, timestamp=datetime.now(MSK))
        embed.add_field(name="📌 Заголовок", value=self.idea_title.value, inline=False)
        embed.add_field(name="📝 Детали предложения", value=self.idea_desc.value, inline=False)
        embed.set_footer(text="Kingdom of Joy | Idea Center", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        pings = f"<@&{CREATOR_ROLE_ID}> <@&{FOUNDER_ROLE_ID}>"
        await thread.send(content=f"⚙️ Уведомление Высшему Совету: {pings}", embed=embed, view=IdeaVotingView(), allowed_mentions=discord.AllowedMentions(roles=True, users=True))
        await send_log(interaction.guild, "💡 Создано Предложение", f"Пользователь {interaction.user.mention} предложил идею в ветке {thread.mention}", color=0x3498db, fields=[("Заголовок", self.idea_title.value, False)])

class IdeaVotingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.approvals, self.rejections = set(), set()
    def is_management(self, user: discord.Member) -> bool:
        return user.id == 1437779380184158249 or any(r.id in [CREATOR_ROLE_ID, FOUNDER_ROLE_ID] for r in user.roles)
    @discord.ui.button(label="Принять", style=discord.ButtonStyle.success, emoji="✅", custom_id="idea_approve_btn")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_management(interaction.user):
            await interaction.response.send_message("❌ Доступно только Руководству Kingdom of Joy.", ephemeral=True)
            return
        self.approvals.add(interaction.user.id)
        await interaction.response.send_message("✅ Голос за принятие записан.", ephemeral=True)
        if len(self.approvals) >= 2 or interaction.user.id == 1437779380184158249:
            self.stop()
            await interaction.channel.send(make_blockquote("🟢 **Вердикт Руководства:** Идея официально одобрена и принята в разработку!"))
            await interaction.channel.edit(locked=True, archived=True)
            await send_log(interaction.guild, "🟢 Идея Одобрена", f"Идея в канале {interaction.channel.mention} была официально принята.", color=0x2ecc71)
    @discord.ui.button(label="Отказ", style=discord.ButtonStyle.danger, emoji="❌", custom_id="idea_reject_btn")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_management(interaction.user):
            await interaction.response.send_message("❌ Доступно только Руководству Kingdom of Joy.", ephemeral=True)
            return
        self.rejections.add(interaction.user.id)
        await interaction.response.send_message("❌ Голос за отклонение записан.", ephemeral=True)
        if len(self.rejections) >= 2 or interaction.user.id == 1437779380184158249:
            self.stop()
            await interaction.channel.send(make_blockquote("🔴 **Вердикт Руководства:** Идея отклонена."))
            await interaction.channel.edit(locked=True, archived=True)
            await send_log(interaction.guild, "🔴 Идея Отклонена", f"Идея в канале {interaction.channel.mention} была отклонена.", color=0xe74c3c)

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Запечатать тикет", style=discord.ButtonStyle.secondary, emoji="🔒", custom_id="ticket_close_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Сессия завершается... Канал будет запечатан.")
        await send_log(interaction.guild, "🔒 Тикет Закрыт", f"Тикет {interaction.channel.mention} запечатан {interaction.user.mention}.", color=0x95a5a6)
        await asyncio.sleep(2)
        try:
            await interaction.channel.edit(locked=True, archived=True)
        except Exception: pass

class SupportHubView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    async def _create_private_ticket(self, interaction: discord.Interaction, prefix: str, title: str, desc: str, ping_roles: list, color: int):
        await interaction.response.defer(ephemeral=True)
        thread = await interaction.channel.create_thread(name=f"{prefix}-{interaction.user.name}", type=discord.ChannelType.private_thread, invitable=False)
        await thread.add_user(interaction.user)
        await interaction.followup.send(f"🔒 Личный сектор связи успешно создан: {thread.mention}", ephemeral=True)
        role_pings = " ".join([f"<@&{rid}>" for rid in ping_roles])
        embed = discord.Embed(title=f"🛡️ {title}", description=(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nПриветствуем тебя, {interaction.user.mention}!\n\n{desc}\n\n📌 **ПРАВИЛА И РЕКОМЕНДАЦИИ:**\n1. **Изложи суть:** Напиши проблему или вопрос одним полным сообщением.\n2. **Прикрепи доказательства:** Скриншоты, видео или логи (если есть).\n3. **Ожидай ответа:** Ответственные сотрудники уже уведомлены.\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"), color=color, timestamp=datetime.now(MSK))
        embed.set_footer(text="Kingdom of Joy | Support Ticket", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        await thread.send(content=f"🚪 **Новое обращение!** Участник: {interaction.user.mention} | Доступ: {role_pings}", embed=embed, view=TicketCloseView(), allowed_mentions=discord.AllowedMentions(roles=True, users=True))
        await send_log(interaction.guild, "🎫 Открыт Новый Тикет", f"Пользователь {interaction.user.mention} создал обращение {thread.mention}", color=color, fields=[("Категория", prefix, True)])
    @discord.ui.button(label="Жалоба", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="support_complaint_btn", row=0)
    async def create_complaint(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_private_ticket(interaction, "⚠️-жалоба", "Отдел Рассмотрения Правонарушений", "Вы перешли в сектор подачи жалоб. Пожалуйста, опишите причину обращения, укажите никнейм нарушителя и прикрепите прямые доказательства.", [CREATOR_ROLE_ID, FOUNDER_ROLE_ID, COMPLAINTS_DEPT_ROLE_ID], 0xd9534f)
    @discord.ui.button(label="Предложить Идею", style=discord.ButtonStyle.primary, emoji="💡", custom_id="support_idea_btn", row=0)
    async def create_idea(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(IdeaModal())
    @discord.ui.button(label="Поддержка / Донат", style=discord.ButtonStyle.success, emoji="💎", custom_id="support_donate_btn", row=0)
    async def create_donation_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_private_ticket(interaction, "💎-донат", "Поддержка и Развитие Проекта", "Здесь вы можете обсудить финансовую поддержку сервера, покупку уникальных ролей, спонсорские привилегии и бонусы.", [CREATOR_ROLE_ID, FOUNDER_ROLE_ID], 0x2ecc71)
    @discord.ui.button(label="Тех. Разработчик", style=discord.ButtonStyle.primary, emoji="💻", custom_id="support_dev_btn", row=1)
    async def create_dev_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_private_ticket(interaction, "💻-разраб", "Технический Раздел и Баги", "Личная линия связи с Техническим Разработчиком. Сообщите о найденных багах, ошибках в ботах или проблемах с игровыми серверами.", [CREATOR_ROLE_ID], 0x7864c8)
    @discord.ui.button(label="Высшее Руководство", style=discord.ButtonStyle.secondary, emoji="👑", custom_id="support_management_btn", row=1)
    async def create_management_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_private_ticket(interaction, "👑-руководство", "Приватный Сектор Высшего Совета", "Прямой канал связи с Создателем и Основателями проекта для решения конфиденциальных, административных и важных вопросов.", [1526681612337549343, FOUNDER_ROLE_ID], 0xf1c40f)

class ApplicationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplicationSelect())

class ApplicationSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label="Маппер", description="Подать заявку на маппера", emoji="🗺️"), discord.SelectOption(label="Модератор чата", description="Подать заявку на модератора", emoji="🛡️"), discord.SelectOption(label="Киноклуб", description="Подать заявку в киноклуб", emoji="🎬"), discord.SelectOption(label="Девушка", description="Получить статус девушки", emoji="👩")]
        super().__init__(placeholder="Выберите тип заявки", options=options, custom_id="app_select")
    async def callback(self, interaction: discord.Interaction):
        modal = ApplicationModal(self.values[0])
        await interaction.response.send_modal(modal)

class ApplicationModal(discord.ui.Modal):
    def __init__(self, app_type: str):
        super().__init__(title=f"📝 Заявка: {app_type[:20]}")
        self.app_type = app_type
        if app_type == "Модератор чата":
            self.add_item(discord.ui.TextInput(label="Ваш никнейм", placeholder="Напишите ник", max_length=50, required=True))
            self.add_item(discord.ui.TextInput(label="Ваш возраст", placeholder="Укажите возраст", max_length=3, required=True))
            self.add_item(discord.ui.TextInput(label="Опыт (если есть)", placeholder="Расскажите о вашем опыте", style=discord.TextStyle.paragraph, max_length=500, required=False))
            self.add_item(discord.ui.TextInput(label="Причина стать модератором", placeholder="Напишите мотивацию", style=discord.TextStyle.paragraph, max_length=1000, required=True))
        elif app_type == "Маппер":
            self.add_item(discord.ui.TextInput(label="Ваш никнейм", placeholder="Напишите ник", max_length=50, required=True))
            self.add_item(discord.ui.TextInput(label="Ваш возраст", placeholder="Укажите возраст", max_length=3, required=True))
            self.add_item(discord.ui.TextInput(label="Опыт мапперства", placeholder="Опишите ваш опыт", style=discord.TextStyle.paragraph, max_length=500, required=False))
            self.add_item(discord.ui.TextInput(label="Ваша специализация", placeholder="Например: строительство, редстоун...", max_length=100, required=True))
        elif app_type == "Киноклуб":
            self.add_item(discord.ui.TextInput(label="Ваш никнейм", placeholder="Напишите ник", max_length=50, required=True))
            self.add_item(discord.ui.TextInput(label="Ваш возраст", placeholder="Укажите возраст", max_length=3, required=True))
            self.add_item(discord.ui.TextInput(label="Время на сервере", placeholder="Например: 2 месяца", max_length=50, required=True))
            self.add_item(discord.ui.TextInput(label="Причина вступления в киноклуб", placeholder="Напишите вашу мотивацию...", style=discord.TextStyle.paragraph, max_length=1000, required=True))
        elif app_type == "Девушка":
            self.add_item(discord.ui.TextInput(label="Как вас зовут?", placeholder="Ваше имя", max_length=50, required=True))
            self.add_item(discord.ui.TextInput(label="Сколько вам лет?", placeholder="Возраст", max_length=3, required=True))
            self.add_item(discord.ui.TextInput(label="Расскажите о себе", placeholder="Немного о себе...", style=discord.TextStyle.paragraph, max_length=1000, required=True))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        answers = [child.value for child in self.children]
        role_map = {"Маппер": ROLE_MAPPER, "Модератор чата": ROLE_MODERATOR, "Киноклуб": ROLE_CINEMA, "Девушка": ROLE_GIRL}
        target_role_id = role_map.get(self.app_type)
        if not target_role_id:
            await interaction.followup.send("❌ Ошибка: неизвестный тип заявки.", ephemeral=True)
            return
        channel = interaction.client.get_channel(APPLICATIONS_CHANNEL_ID)
        if not channel:
            await interaction.followup.send("❌ Канал заявок не найден.", ephemeral=True)
            return
        thread_name = f"📩-{self.app_type}-{interaction.user.name}"
        try:
            thread = await channel.create_thread(name=thread_name, type=discord.ChannelType.private_thread, invitable=False)
        except Exception:
            thread = await channel.create_thread(name=thread_name, type=discord.ChannelType.public_thread)
        await thread.add_user(interaction.user)
        for role_id in HIGHER_ROLES:
            role = interaction.guild.get_role(role_id)
            if role:
                try:
                    await thread.send(content=f"<@&{role_id}>", allowed_mentions=discord.AllowedMentions(roles=True))
                except: pass
        embed = discord.Embed(title=f"📋 Заявка на {self.app_type}", color=0x5865F2, timestamp=datetime.now(MSK))
        embed.add_field(name="👤 Игрок", value=interaction.user.mention, inline=False)
        if self.app_type == "Модератор чата":
            embed.add_field(name="📛 Никнейм", value=answers[0], inline=True)
            embed.add_field(name="🎂 Возраст", value=answers[1], inline=True)
            embed.add_field(name="📜 Опыт", value=answers[2] or "Не указан", inline=False)
            embed.add_field(name="💬 Причина", value=answers[3], inline=False)
        elif self.app_type == "Маппер":
            embed.add_field(name="📛 Никнейм", value=answers[0], inline=True)
            embed.add_field(name="🎂 Возраст", value=answers[1], inline=True)
            embed.add_field(name="📜 Опыт мапперства", value=answers[2] or "Не указан", inline=False)
            embed.add_field(name="🔧 Специализация", value=answers[3], inline=False)
        elif self.app_type == "Киноклуб":
            embed.add_field(name="📛 Никнейм", value=answers[0], inline=True)
            embed.add_field(name="🎂 Возраст", value=answers[1], inline=True)
            embed.add_field(name="⏳ Время на сервере", value=answers[2], inline=False)
            embed.add_field(name="🎬 Причина вступать в киноклуб", value=answers[3], inline=False)
        elif self.app_type == "Девушка":
            embed.add_field(name="👩 Имя", value=answers[0], inline=True)
            embed.add_field(name="🎂 Возраст", value=answers[1], inline=True)
            embed.add_field(name="📝 О себе", value=answers[2], inline=False)
        embed.set_footer(text=f"ID заявки: {thread.id}")
        view = ApplicationVerdictView(interaction.user.id, target_role_id, self.app_type)
        await thread.send(content=f"🔔 **Новая заявка от {interaction.user.mention}**", embed=embed, view=view)
        await interaction.followup.send(f"✅ Ваша заявка отправлена! Ожидайте решения в ветке {thread.mention}", ephemeral=True)
        await send_log(interaction.guild, "📩 Создана заявка", f"Пользователь {interaction.user.mention} подал заявку на {self.app_type} (ветка {thread.mention})", color=0x3498db)

class ApplicationVerdictView(discord.ui.View):
    def __init__(self, applicant_id: int, role_id: int, app_type: str):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.role_id = role_id
        self.app_type = app_type
    @discord.ui.button(label="✅ Принять", style=discord.ButtonStyle.success, custom_id="app_accept")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(r.id in HIGHER_ROLES for r in interaction.user.roles) and interaction.user.id not in CREATOR_AND_ROLE_IDS:
            await interaction.response.send_message("❌ У вас нет прав для принятия заявок.", ephemeral=True)
            return
        guild = interaction.guild
        member = guild.get_member(self.applicant_id)
        if not member:
            await interaction.response.send_message("❌ Пользователь не найден на сервере.", ephemeral=True)
            return
        role = guild.get_role(self.role_id)
        if not role:
            await interaction.response.send_message("❌ Роль для выдачи не найдена.", ephemeral=True)
            return
        try:
            await member.add_roles(role)
            await interaction.response.send_message(f"✅ Заявка принята! Пользователю {member.mention} выдана роль {role.mention}.")
            await send_log(guild, "✅ Заявка принята", f"Пользователь {member.mention} получил роль {role.mention} (заявка на {self.app_type})", color=0x2ecc71)
            await interaction.channel.edit(locked=True, archived=True)
            await interaction.channel.send(f"🎉 Заявка принята! {member.mention}, поздравляем!")
            await interaction.message.edit(view=None)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)
    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger, custom_id="app_reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(r.id in HIGHER_ROLES for r in interaction.user.roles) and interaction.user.id not in CREATOR_AND_ROLE_IDS:
            await interaction.response.send_message("❌ У вас нет прав для отклонения заявок.", ephemeral=True)
            return
        guild = interaction.guild
        member = guild.get_member(self.applicant_id)
        try:
            await interaction.response.send_message("❌ Заявка отклонена.")
            await send_log(guild, "❌ Заявка отклонена", f"Заявка пользователя <@{self.applicant_id}> на {self.app_type} была отклонена модератором {interaction.user.mention}.", color=0xe74c3c)
            await interaction.channel.edit(locked=True, archived=True)
            if member:
                try:
                    await member.send(f"❌ Ваша заявка на должность **{self.app_type}** была отклонена.")
                except: pass
            await interaction.message.edit(view=None)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

# ==================== ИНИЦИАЛИЗАЦИЯ БОТА ====================
class KingdomBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.user_level_cache = {}
        self.mafia_game = None

    async def setup_hook(self):
        commands_list = [
            setup_verify, mcstatus_cmd, marriage_propose, marriage_divorce, marriage_profile, set_dr, get_dr,
            mafia_cmd, mafia_config, lk, bind, chance, sync_cmd, test_welcome, remind, badwords,
            warnlist, give_temp_role, warn, unwarn, mute, unmute, ban, unban, kick_cmd,
            delete, staff, setup_support, setup_applications, messages, top,
            setmessages, addmessages, resetmessages, send_cmd, addgroup,
            removegroup, listgroups, setbalance, addbalance, takebalance,
            setrelic, addrelic, takerelic, resetplayer,
            add_gif_url, remove_gif_url, list_gif_urls,
            all_marriages, all_birthdays
        ]
        for cmd in commands_list:
            self.tree.add_command(cmd)

        self.add_view(SupportHubView())
        self.add_view(ApplicationView())
        self.add_view(IdeaVotingView())

    async def on_ready(self):
        print(f"✅ Бот {self.user} успешно запущен и готов к работе!")
        counts = load_message_counts()
        for uid, count in counts.items():
            self.user_level_cache[int(uid)] = get_level(count)

    async def on_member_join(self, member):
        # Выдача роли
        role = member.guild.get_role(UNVERIFIED_ROLE_ID)
        if role:
            await member.add_roles(role)
        
        # Приветствие
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            banner_file = create_welcome_banner(member.display_name)
            embed = discord.Embed(
                title="👑 Новый Странник ступил в Kingdom of Joy!",
                description=f"Приветствуем тебя, {member.mention}!\nЗагляни в <#1520119059566559282> для навигации.",
                color=0x7864c8,
                timestamp=datetime.now(MSK)
            )
            embed.set_image(url="attachment://welcome_banner.png")
            view = WelcomeButtonsView(member.guild.id)
            await channel.send(content=f"👋 {member.mention}", embed=embed, file=banner_file, view=view)

    async def on_message(self, message):
        if message.author.bot: return
        
        # 1. Автоматическое создание ветки
        if message.channel.id == MEDIA_CHANNEL_ID and message.author.id != self.user.id:
            try:
                await message.create_thread(name="Комментарии", auto_archive_duration=1440)
            except:
                pass

        # 2. Ответ гифками (НОВАЯ ЛОГИКА ПО URL)
        content_lower = message.content.lower()
        gifs = load_gifs()
        if "доброе утро" in content_lower:
            if gifs["morning"]:
                await message.channel.send(random.choice(gifs["morning"]))
        if "доброй ночи" in content_lower or "спокойной ночи" in content_lower:
            if gifs["night"]:
                await message.channel.send(random.choice(gifs["night"]))

        badwords_data = load_json(BADWORDS_FILE, {})
        words = badwords_data.get("words", [])
        mute_time_str = badwords_data.get("mute_time", "1h")

        if words and not is_high_staff(message.author):
            content_lower = message.content.lower()
            if any(w in content_lower for w in words):
                try:
                    await message.delete()
                    duration = parse_duration(mute_time_str)
                    await message.author.timeout(duration, reason="Нарушение фильтра нецензурных слов")
                    await message.channel.send(make_blockquote(f"⚠️ {message.author.mention}, ваше сообщение содержало запрещенные слова и было удалено. Вы получили мут на **{mute_time_str}**."))
                    await send_log(message.guild, "🚫 Фильтр Слов", f"Сообщение от {message.author.mention} удалено. Выдан мут на `{mute_time_str}`.", color=0xe74c3c)
                except Exception as e:
                    print(f"❌ Ошибка фильтра слов: {e}")
                return

        if message.channel.id in COUNT_CHANNELS:
            counts = load_message_counts()
            uid = str(message.author.id)
            current = counts.get(uid, 0) + 1
            counts[uid] = current
            save_message_counts(counts)
            await update_user_level(self, message.author, current, message.channel)

        await self.process_commands(message)

    async def find_player_by_discord(self, discord_id: str, users_data: dict):
        players = users_data.get("players", {})
        for uuid, data in players.items():
            if str(data.get("discord-id")) == str(discord_id):
                return uuid, data
        return None

    async def find_player_by_id(self, player_id: int, users_data: dict):
        players = users_data.get("players", {})
        for uuid, data in players.items():
            if data.get("player-id") == player_id:
                return uuid, data
        return None

    async def find_player_by_nick(self, nick: str, users_data: dict):
        uuid = await get_uuid_by_name(nick)
        if not uuid: return None
        uuid_clean = uuid.replace("-", "")
        players = users_data.get("players", {})
        if uuid_clean in players:
            return uuid_clean, players[uuid_clean]
        return None

    def get_group_prefix(self, group_name: str, users_data: dict) -> str:
        return ""

bot = KingdomBot()

# ==================== ТАСКИ ПО РАСПИСАНИЮ ====================
@tasks.loop(minutes=2)
async def auto_update_status_task():
    try:
        await update_status_message(bot)
    except Exception as e:
        print(f"⚠️ Ошибка в автообновлении мониторинга: {e}")
        traceback.print_exc()

@auto_update_status_task.before_loop
async def before_auto_update():
    await asyncio.sleep(5)

@tasks.loop(minutes=1)
async def status_scheduler():
    now = datetime.now(MSK)
    if now.hour >= 21 or now.hour < 8:
        if bot.status != discord.Status.idle:
            await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name="Неактивен"))
    else:
        if bot.status != discord.Status.online:
            await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="Kingdom of Joy"))

@status_scheduler.before_loop
async def before_status_scheduler():
    await bot.wait_until_ready()

@tasks.loop(minutes=1)
async def reminders_loop():
    reminders = load_json(REMINDERS_FILE, [])
    if not reminders: return
    now_ts = int(datetime.now(MSK).timestamp())
    remaining = []
    for r in reminders:
        if r["unix"] <= now_ts:
            try:
                channel = bot.get_channel(r["channel_id"])
                user = await bot.fetch_user(r["user_id"])
                if channel: await channel.send(make_blockquote(f"⏰ {user.mention}, напоминание: **{r['text']}**"))
                elif user: await user.send(make_blockquote(f"⏰ Напоминание: **{r['text']}**"))
            except Exception as e: print(f"❌ Ошибка отправки напоминания: {e}")
        else:
            remaining.append(r)
    save_json(REMINDERS_FILE, remaining)

@reminders_loop.before_loop
async def before_reminders():
    await bot.wait_until_ready()

@tasks.loop(time=time(hour=0, minute=1, tzinfo=MSK))
async def birthday_checker():
    birthdays = load_birthdays()
    now = datetime.now(MSK)
    today_str = now.strftime("%d.%m")
    channel = bot.get_channel(COMMUNICATION_CHANNEL_ID)
    if not channel:
        return
    
    for uid_str, date in birthdays.items():
        if date.startswith(today_str):
            try:
                user = await bot.fetch_user(int(uid_str))
                if user:
                    embed = discord.Embed(
                        title="🎂 С днём рождения! 🎂",
                        description=f"Поздравляем {user.mention} с днём рождения!\nЖелаем счастья, здоровья и удачи! 🥳",
                        color=0xffd700,
                        timestamp=now
                    )
                    embed.set_thumbnail(url=user.display_avatar.url)
                    await channel.send(content=user.mention, embed=embed)
            except:
                pass

@birthday_checker.before_loop
async def before_birthday_checker():
    await bot.wait_until_ready()

async def main():
    async with bot:
        auto_update_status_task.start()
        status_scheduler.start()
        reminders_loop.start()
        birthday_checker.start()
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
