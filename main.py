import discord
from discord.ext import tasks, commands
from discord import app_commands
import os
import asyncio
import random
from datetime import datetime, timezone, timedelta
import json
import io
import traceback
from PIL import Image, ImageDraw, ImageFont
import re
import aiohttp
import yaml
import paramiko
import time

# ==================== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ====================
TOKEN = os.getenv("TOKEN")
SFTP_HOST = os.getenv("SFTP_HOST")
SFTP_PORT = int(os.getenv("SFTP_PORT", 7477))
SFTP_USER = os.getenv("SFTP_USER")
SFTP_PASSWORD = os.getenv("SFTP_PASSWORD")
SFTP_REMOTE_PATH = os.getenv("SFTP_REMOTE_PATH")

# ==================== КОНСТАНТЫ ====================
LK_CHANNEL_ID = 1529937315890204836
VERIFY_CHANNEL_ID = 1529538303559205047
VERIFY_ROLE_ID = 1505240271200456864
UNVERIFIED_ROLE_ID = 1529537943663018045
VERIFY_MSG_FILE = "verify_msg.json"
APPLICATIONS_CHANNEL_ID = 1530237443767533748
ROLE_MAPPER = 1525487051544203395
ROLE_MODERATOR = 1505275521825771520
ROLE_CINEMA = 1505250838053126345
HIGHER_ROLES = [1526681612337549343, 1505438802653741096, 1530235500886102216, 1505235504826814535]
MSK = timezone(timedelta(hours=3))
WARNS_FILE = "warns.json"
SUPPORT_CONFIG_FILE = "support_config.json"
BADWORDS_FILE = "badwords.json"
REMINDERS_FILE = "reminders.json"
APPLICATIONS_CONFIG_FILE = "applications_config.json"
CREATOR_AND_ROLE_IDS = [1437779380184158249, 1001913830261129237, 1308313239775608863]
CREATOR_ROLE_ID = 1505438802653741096
FOUNDER_ROLE_ID = 1505235504826814535
MODERATOR_ROLE_ID = 1505275521825771520
COMPLAINTS_DEPT_ROLE_ID = 1527627623428128879
CALM_ROLE_IDS = [1526681612337549343, 1505438802653741096]
IMMUNE_ROLE_IDS = [CREATOR_ROLE_ID, FOUNDER_ROLE_ID]
LOGS_CHANNEL_ID = 1505274763096883230
SUPPORT_CHANNEL_ID = 1526688069464625305
MEDIA_CHANNEL_ID = 1505266075347193976
WELCOME_CHANNEL_ID = 1505280068656824400
EXCLUDED_LOG_CHANNEL = 1505543466426437712
BALKAN_TRIGGERS = ['БАЛКАН', 'балкан', 'balkan', 'BALKAN', 'Balkan', 'Балкан']
SPECIAL_TRIGGERS = ['Вова', 'vovancho', 'вован', 'вова', 'вовчек', 'ВОВА', 'харчек', 'харута', 'ХАРУТА', 'haryta', 'Haryta']
CUSTOM_REACTIONS = [
    discord.PartialEmoji(name="e1", id=1506903029671137390),
    discord.PartialEmoji(name="e2", id=1506902413574012938),
    discord.PartialEmoji(name="e3", id=1506904586655498350)
]
CROWN_EMOJI = discord.PartialEmoji(name="crown", id=1506904987845001236)

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

async def send_log(guild: discord.Guild, title: str, description: str, color: int = 0x7864c8, fields: list = None):
    if not guild:
        return
    log_channel = guild.get_channel(LOGS_CHANNEL_ID)
    if not log_channel:
        try:
            log_channel = await guild.fetch_channel(LOGS_CHANNEL_ID)
        except Exception:
            return
    embed = discord.Embed(
        title=f"🛡️ [LOG] {title}",
        description=description,
        color=color,
        timestamp=datetime.now(MSK)
    )
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
        if time_str.isdigit():
            return timedelta(minutes=int(time_str))
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

def is_high_staff(member: discord.Member) -> bool:
    if not member:
        return False
    return any(r.id in HIGHER_ROLES for r in member.roles) or member.id in CREATOR_AND_ROLE_IDS

uuid_cache = {}

async def get_uuid_by_name(name: str) -> str:
    if name in uuid_cache:
        return uuid_cache[name]
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"https://api.mojang.com/users/profiles/minecraft/{name}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    uuid = data.get("id")
                    if uuid:
                        uuid_cache[name] = uuid
                        return uuid
                elif resp.status == 204:
                    return None
                else:
                    print(f"⚠️ Mojang API вернул {resp.status}")
                    return None
        except Exception as e:
            print(f"❌ Ошибка запроса к Mojang API: {e}")
            return None

def format_time(seconds: int) -> str:
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if days > 0:
        return f"{days}д {hours:02d}ч {minutes:02d}м {secs:02d}с"
    elif hours > 0:
        return f"{hours}ч {minutes:02d}м {secs:02d}с"
    elif minutes > 0:
        return f"{minutes}м {secs:02d}с"
    else:
        return f"{secs}с"

# ==================== СЛЭШ-КОМАНДЫ ====================
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
            embed = discord.Embed(
                title="🔗 Привяжите аккаунт",
                description=(
                    "Вы не привязали Discord к Minecraft.\n\n"
                    "**Как привязать:**\n"
                    "1. Зайдите на сервер Minecraft.\n"
                    "2. Напишите `/setdiscord " + interaction.user.name + " " + discord_id + "`\n"
                    "3. После этого используйте `/lk` снова.\n\n"
                    "Или посмотрите профиль другого игрока:\n"
                    "`/lk <ник>` или `/lk id <ID>`"
                ),
                color=0xe74c3c
            )
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
        if prefix:
            display_name = f"{prefix} {gname}"
        else:
            display_name = gname
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
    embed = discord.Embed(
        title=f"📊 Личный кабинет {nick}",
        color=0x5865F2,
        timestamp=datetime.now(MSK)
    )
    embed.add_field(
        name="👤 Информация",
        value=(
            f"**Ник:** {nick}\n"
            f"**ID:** `{player_id}`\n"
            f"**Тег:** {tag if tag else '—'}\n"
            f"**Discord:** <@{discord_id}>" if discord_id != "Не привязан" else f"**Discord:** {discord_id}"
        ),
        inline=False
    )
    embed.add_field(
        name="⚔️ Статистика",
        value=(
            f"**Время игры:** {format_time(playtime)}\n"
            f"**Убийств:** {kills}\n"
            f"**Смертей:** {deaths}\n"
            f"**K/D:** {(kills / deaths):.2f}" if deaths > 0 else "**K/D:** ∞"
        ),
        inline=True
    )
    embed.add_field(
        name="💰 Экономика",
        value=(
            f"**Баланс:** {balance:.2f} монет\n"
            f"**Реликвии:** {relics} шт."
        ),
        inline=True
    )
    embed.add_field(
        name="👑 Группы",
        value=groups_str[:1024],
        inline=False
    )
    embed.set_footer(
        text="Kingdom of Joy | Личный кабинет",
        icon_url=interaction.guild.icon.url if interaction.guild.icon else None
    )
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
        await interaction.followup.send("❌ Ошибка чтения базы игроков с сервера.")
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
        await interaction.followup.send(
            f"✅ Аккаунт **{nickname}** успешно привязан к Discord!\n"
            f"Теперь вы можете использовать `/lk` для просмотра профиля.",
            ephemeral=True
        )
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
    if interaction.user.id != 1437779380184158249:
        return
    await interaction.response.defer(ephemeral=True)
    banner_file = create_welcome_banner(interaction.user.display_name)
    embed = discord.Embed(
        title="👑 Новый Странник ступил в Kingdom of Joy!",
        description=f"Приветствуем тебя, {interaction.user.mention}!\nЗагляни в <#1520119059566559282> для навигации.",
        color=0x7864c8,
        timestamp=datetime.now(MSK)
    )
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
    if not (interaction.user.id == 1437779380184158249 or any(r.id in [CREATOR_ROLE_ID, FOUNDER_ROLE_ID] for r in interaction.user.roles)):
        return
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
    if not interaction.client.is_allowed_staff(interaction):
        return
    if is_high_staff(user):
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
        except Exception:
            pass
    asyncio.create_task(remove_later())

@app_commands.command(name="warn", description="Выдать варн")
async def warn(interaction: discord.Interaction, user: discord.Member, reason: str = "Нарушение"):
    bot = interaction.client
    if not bot.is_allowed_staff(interaction) or not bot.check_hierarchy(interaction.user, user):
        return
    if is_high_staff(user):
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
    if not interaction.client.is_allowed_staff(interaction):
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
    if not interaction.client.is_allowed_staff(interaction):
        return
    if is_high_staff(user):
        await interaction.response.send_message("❌ Этот пользователь принадлежит к высшему составу и не может быть наказан.", ephemeral=True)
        return
    duration = parse_duration(time)
    await user.timeout(duration, reason=reason)
    await interaction.response.send_message(make_blockquote(f"🔇 {user.mention} отправлен в мут на **{time}**."))
    await send_log(interaction.guild, "🔇 Выдан Мут", f"Модератор: {interaction.user.mention}\nНарушитель: {user.mention}\nСрок: `{time}`\nПричина: *{reason}*", color=0xe74c3c)

@app_commands.command(name="unmute", description="Размут")
async def unmute(interaction: discord.Interaction, user: discord.Member):
    if not interaction.client.is_allowed_staff(interaction):
        return
    await user.timeout(None)
    await interaction.response.send_message(make_blockquote(f"🔊 {user.mention} размучен."))
    await send_log(interaction.guild, "🔊 Размут", f"Модератор {interaction.user.mention} размутил пользователя {user.mention}.", color=0x2ecc71)

@app_commands.command(name="ban", description="Бан")
async def ban(interaction: discord.Interaction, user: discord.Member, reason: str = "Нарушение"):
    if not interaction.client.is_allowed_staff(interaction):
        return
    if is_high_staff(user):
        await interaction.response.send_message("❌ Этот пользователь принадлежит к высшему составу и не может быть наказан.", ephemeral=True)
        return
    await user.ban(reason=reason)
    await interaction.response.send_message(make_blockquote(f"🚫 {user.mention} забанен."))
    await send_log(interaction.guild, "🚫 Бан", f"Модератор {interaction.user.mention} забанил {user.mention}.\nПричина: *{reason}*", color=0x900c3f)

@app_commands.command(name="unban", description="Разбан")
async def unban(interaction: discord.Interaction, user_id: str):
    if not interaction.client.is_allowed_staff(interaction):
        return
    user = await interaction.client.fetch_user(int(user_id))
    await interaction.guild.unban(user)
    await interaction.response.send_message(make_blockquote(f"🔓 Пользователь **{user.name}** разбанен."))
    await send_log(interaction.guild, "🔓 Разбан", f"Модератор {interaction.user.mention} разбанил {user.name} (ID: `{user.id}`).", color=0x2ecc71)

@app_commands.command(name="delete", description="Очистка чата")
async def delete(interaction: discord.Interaction, amount: str):
    if not interaction.client.is_allowed_staff(interaction):
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
        if FOUNDER_ROLE_ID in rids:
            founders.append(m)
        elif CREATOR_ROLE_ID in rids or m.id == 1437779380184158249:
            creators.append(m)
        elif MODERATOR_ROLE_ID in rids:
            moderators.append(m)
    embed = discord.Embed(title="🛡️ Администрация Kingdom of Joy", color=0x2b2d31, timestamp=datetime.now(MSK))
    embed.add_field(name="👑 1. Основатели", value="\n".join([f"• <@{m.id}>" for m in founders]) if founders else "• *Нет*", inline=False)
    embed.add_field(name="✨ 2. Создатели", value="\n".join([f"• <@{m.id}>" for m in creators]) if creators else "• *Нет*", inline=False)
    embed.add_field(name="🛡️ 3. Модераторы", value="\n".join([f"• <@{m.id}>" for m in moderators]) if moderators else "• *Нет*", inline=False)
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="setup_support", description="Обновить и выставить монументальную панель поддержки")
async def setup_support(interaction: discord.Interaction):
    if interaction.user.id != 1437779380184158249:
        return
    await interaction.response.defer(ephemeral=True)
    channel = interaction.guild.get_channel(SUPPORT_CHANNEL_ID)
    if not channel:
        await interaction.followup.send("❌ Канал поддержки не найден!", ephemeral=True)
        return
    embed = discord.Embed(
        title="✨ **ЦЕНТР ПОДДЕРЖКИ И УПРАВЛЕНИЯ «KINGDOM OF JOY»**",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Приветствуем вас в официальном центре обращений нашего сервера!\n"
            "Здесь вы можете связаться с руководством, заявить о нарушении или предложить идею.\n\n"
            "📌 **ОБЩИЙ СВОД ПРАВИЛ ПОДАЧИ ОБРАЩЕНИЙ:**\n"
            "• **Уважение:** Излагайте суть обращения спокойно и вежливо.\n"
            "• **Доказательства:** В случае жалобы сразу прикрепляйте медиафайлы.\n"
            "• **Терпение:** Ответственные сотрудники отреагируют в ближайшее время.\n"
            "• **Запрещено:** Создавать ложные тикеты, флудить и спамить кнопками.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0x7864c8,
        timestamp=datetime.now(MSK)
    )
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
    embed = discord.Embed(
        title="📩 **Подача заявок на должности**",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Здесь вы можете подать заявку на одну из следующих должностей:\n\n"
            "🗺️ **Маппер** – создание карт и уровней.\n"
            "🛡️ **Модератор чата** – поддержание порядка в общем чате.\n"
            "🎬 **Киноклуб** – организация совместных просмотров фильмов.\n\n"
            "📌 **Инструкция:**\n"
            "1. Выберите тип заявки в меню ниже.\n"
            "2. Заполните анкету (все поля обязательны).\n"
            "3. После отправки ваша заявка будет рассмотрена высшим составом.\n"
            "4. Решение будет принято в течение нескольких дней.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0x5865F2,
        timestamp=datetime.now(MSK)
    )
    embed.set_footer(text="Kingdom of Joy | Applications", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    view = ApplicationView()
    await channel.send(embed=embed, view=view)
    await interaction.followup.send("✅ Сообщение с заявками отправлено в канал!", ephemeral=True)

# ==================== UI КОМПОНЕНТЫ ====================
class WelcomeButtonsView(discord.ui.View):
    def __init__(self, guild_id: int = 0):
        super().__init__(timeout=None)
        g_id = guild_id if guild_id else '@me'
        self.add_item(discord.ui.Button(
            label="📢 Новости",
            style=discord.ButtonStyle.link,
            url=f"https://discord.com/channels/{g_id}/1505126425022300275",
            row=0
        ))
        self.add_item(discord.ui.Button(
            label="💬 Основной Чат",
            style=discord.ButtonStyle.link,
            url=f"https://discord.com/channels/{g_id}/1505239843486306374",
            row=0
        ))
        self.add_item(discord.ui.Button(
            label="🗺️ Навигация",
            style=discord.ButtonStyle.link,
            url=f"https://discord.com/channels/{g_id}/1520119059566559282",
            row=0
        ))

class IdeaModal(discord.ui.Modal, title="💡 Подача предложения"):
    idea_title = discord.ui.TextInput(label="Суть идеи", placeholder="Кратко изложи суть предложения...", max_length=100)
    idea_desc = discord.ui.TextInput(label="Подробные детали", placeholder="Опиши детально, как это улучшит проект...", style=discord.TextStyle.paragraph, max_length=1000)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        thread = await interaction.channel.create_thread(
            name=f"💡-идея-{interaction.user.name}",
            type=discord.ChannelType.private_thread,
            invitable=False
        )
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
        except Exception:
            pass

class SupportHubView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    async def _create_private_ticket(self, interaction: discord.Interaction, prefix: str, title: str, desc: str, ping_roles: list, color: int):
        await interaction.response.defer(ephemeral=True)
        thread = await interaction.channel.create_thread(
            name=f"{prefix}-{interaction.user.name}",
            type=discord.ChannelType.private_thread,
            invitable=False
        )
        await thread.add_user(interaction.user)
        await interaction.followup.send(f"🔒 Личный сектор связи успешно создан: {thread.mention}", ephemeral=True)
        role_pings = " ".join([f"<@&{rid}>" for rid in ping_roles])
        embed = discord.Embed(
            title=f"🛡️ {title}",
            description=(
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Приветствуем тебя, {interaction.user.mention}!\n\n"
                f"{desc}\n\n"
                f"📌 **ПРАВИЛА И РЕКОМЕНДАЦИИ:**\n"
                f"1. **Изложи суть:** Напиши проблему или вопрос одним полным сообщением.\n"
                f"2. **Прикрепи доказательства:** Скриншоты, видео или логи (если есть).\n"
                f"3. **Ожидай ответа:** Ответственные сотрудники уже уведомлены.\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=color,
            timestamp=datetime.now(MSK)
        )
        embed.set_footer(text="Kingdom of Joy | Support Ticket", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        await thread.send(
            content=f"🚪 **Новое обращение!** Участник: {interaction.user.mention} | Доступ: {role_pings}",
            embed=embed,
            view=TicketCloseView(),
            allowed_mentions=discord.AllowedMentions(roles=True, users=True)
        )
        await send_log(interaction.guild, "🎫 Открыт Новый Тикет", f"Пользователь {interaction.user.mention} создал обращение {thread.mention}", color=color, fields=[("Категория", prefix, True)])
    @discord.ui.button(label="Жалоба", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="support_complaint_btn", row=0)
    async def create_complaint(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_private_ticket(
            interaction,
            "⚠️-жалоба",
            "Отдел Рассмотрения Правонарушений",
            "Вы перешли в сектор подачи жалоб. Пожалуйста, опишите причину обращения, укажите никнейм нарушителя и прикрепите прямые доказательства.",
            [CREATOR_ROLE_ID, FOUNDER_ROLE_ID, COMPLAINTS_DEPT_ROLE_ID],
            0xd9534f
        )
    @discord.ui.button(label="Предложить Идею", style=discord.ButtonStyle.primary, emoji="💡", custom_id="support_idea_btn", row=0)
    async def create_idea(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(IdeaModal())
    @discord.ui.button(label="Поддержка / Донат", style=discord.ButtonStyle.success, emoji="💎", custom_id="support_donate_btn", row=0)
    async def create_donation_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_private_ticket(
            interaction,
            "💎-донат",
            "Поддержка и Развитие Проекта",
            "Здесь вы можете обсудить финансовую поддержку сервера, покупку уникальных ролей, спонсорские привилегии и бонусы.",
            [CREATOR_ROLE_ID, FOUNDER_ROLE_ID],
            0x2ecc71
        )
    @discord.ui.button(label="Тех. Разработчик", style=discord.ButtonStyle.primary, emoji="💻", custom_id="support_dev_btn", row=1)
    async def create_dev_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_private_ticket(
            interaction,
            "💻-разраб",
            "Технический Раздел и Баги",
            "Личная линия связи с Техническим Разработчиком. Сообщите о найденных багах, ошибках в ботах или проблемах с игровыми серверами.",
            [CREATOR_ROLE_ID],
            0x7864c8
        )
    @discord.ui.button(label="Высшее Руководство", style=discord.ButtonStyle.secondary, emoji="👑", custom_id="support_management_btn", row=1)
    async def create_management_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_private_ticket(
            interaction,
            "👑-руководство",
            "Приватный Сектор Высшего Совета",
            "Прямой канал связи с Создателем и Основателями проекта для решения конфиденциальных, административных и важных вопросов.",
            [CREATOR_ROLE_ID, FOUNDER_ROLE_ID],
            0xf1c40f
        )

class ApplicationSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Маппер", description="Подать заявку на должность маппера", emoji="🗺️"),
            discord.SelectOption(label="Модератор чата", description="Подать заявку на модератора чата", emoji="🛡️"),
            discord.SelectOption(label="Киноклуб", description="Подать заявку на участие в киноклубе", emoji="🎬")
        ]
        super().__init__(placeholder="Выберите тип заявки", options=options, custom_id="app_select")
    async def callback(self, interaction: discord.Interaction):
        modal = ApplicationModal(self.values[0])
        await interaction.response.send_modal(modal)

class ApplicationModal(discord.ui.Modal, title="📝 Заявка"):
    def __init__(self, app_type: str):
        super().__init__()
        self.app_type = app_type
        self.add_item(discord.ui.TextInput(label="Ваше имя (игровой ник)", placeholder="Напишите ваш никнейм", max_length=50, required=True))
        self.add_item(discord.ui.TextInput(label="Ваш возраст", placeholder="Укажите возраст", max_length=3, required=True))
        self.add_item(discord.ui.TextInput(label="Опыт (если есть)", placeholder="Расскажите о вашем опыте", style=discord.TextStyle.paragraph, max_length=500, required=False))
        self.add_item(discord.ui.TextInput(label="Почему вы хотите стать маппером/модератором?", placeholder="Напишите мотивацию", style=discord.TextStyle.paragraph, max_length=1000, required=True))
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        name = self.children[0].value
        age = self.children[1].value
        experience = self.children[2].value or "Не указан"
        reason = self.children[3].value
        role_map = {"Маппер": ROLE_MAPPER, "Модератор чата": ROLE_MODERATOR, "Киноклуб": ROLE_CINEMA}
        target_role_id = role_map.get(self.app_type)
        if not target_role_id:
            await interaction.followup.send("❌ Ошибка: неизвестный тип заявки.", ephemeral=True)
            return
        channel = interaction.client.get_channel(APPLICATIONS_CHANNEL_ID)
        if not channel:
            await interaction.followup.send("❌ Канал заявок не найден.", ephemeral=True)
            return
        thread_name = f"📩-{self.app_type}-{interaction.user.name}"
        thread = await channel.create_thread(name=thread_name, type=discord.ChannelType.private_thread, invitable=False)
        await thread.add_user(interaction.user)
        for role_id in HIGHER_ROLES:
            role = interaction.guild.get_role(role_id)
            if role:
                try:
                    await thread.send(content=f"<@&{role_id}>", allowed_mentions=discord.AllowedMentions(roles=True))
                except:
                    pass
        embed = discord.Embed(title=f"📋 Заявка на {self.app_type}", color=0x5865F2, timestamp=datetime.now(MSK))
        embed.add_field(name="👤 Игрок", value=interaction.user.mention, inline=False)
        embed.add_field(name="📛 Имя", value=name, inline=True)
        embed.add_field(name="🎂 Возраст", value=age, inline=True)
        embed.add_field(name="📜 Опыт", value=experience, inline=False)
        embed.add_field(name="💬 Мотивация", value=reason[:1024], inline=False)
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
    @discord.ui.button(label="❌ Отказать", style=discord.ButtonStyle.danger, custom_id="app_reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(r.id in HIGHER_ROLES for r in interaction.user.roles) and interaction.user.id not in CREATOR_AND_ROLE_IDS:
            await interaction.response.send_message("❌ У вас нет прав для отклонения заявок.", ephemeral=True)
            return
        await interaction.response.send_message("❌ Заявка отклонена. Ветка будет заархивирована.")
        await interaction.channel.send("🔴 **Заявка отклонена.** Спасибо за проявленный интерес.")
        await interaction.channel.edit(locked=True, archived=True)
        await interaction.message.edit(view=None)
        await send_log(interaction.guild, "❌ Заявка отклонена", f"Заявка на {self.app_type} от пользователя <@{self.applicant_id}> отклонена.", color=0xe74c3c)

class ApplicationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplicationSelect())

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="✅ Верифицироваться", style=discord.ButtonStyle.success, custom_id="verify_btn")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        unverified_role = interaction.guild.get_role(UNVERIFIED_ROLE_ID)
        verified_role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if not unverified_role or not verified_role:
            await interaction.response.send_message("❌ Ошибка конфигурации ролей. Обратитесь к администрации.", ephemeral=True)
            return
        if verified_role in interaction.user.roles:
            await interaction.response.send_message("✅ Вы уже верифицированы!", ephemeral=True)
            return
        if unverified_role not in interaction.user.roles:
            try:
                await interaction.user.add_roles(verified_role)
                await interaction.response.send_message(f"✅ Вам выдана роль {verified_role.mention}. Добро пожаловать!", ephemeral=True)
                await send_log(interaction.guild, "✅ Верификация", f"Пользователь {interaction.user.mention} получил роль участника (был без неверифицированной роли).", color=0x2ecc71)
            except Exception as e:
                await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)
            return
        try:
            await interaction.user.remove_roles(unverified_role)
            await interaction.user.add_roles(verified_role)
            await interaction.response.send_message(f"✅ Поздравляю! Вы успешно верифицированы. Теперь вам доступны все каналы сервера.", ephemeral=True)
            await send_log(interaction.guild, "✅ Верификация", f"Пользователь {interaction.user.mention} успешно верифицирован.", color=0x2ecc71)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка при верификации: {e}", ephemeral=True)

# ==================== КЛАСС БОТА ====================
class KingdomBot(commands.Bot):
    def __init__(self):
        # Оптимизированные интенты
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.reactions = True
        allowed_mentions = discord.AllowedMentions(roles=True, users=True, everyone=False)
        super().__init__(command_prefix="!", intents=intents, allowed_mentions=allowed_mentions)
        self.reacted_messages = set()
        self.user_badword_counts = {}

    async def setup_hook(self):
        self.tree.add_command(lk)
        self.tree.add_command(bind)
        self.tree.add_command(chance)
        self.tree.add_command(sync_cmd)
        self.tree.add_command(test_welcome)
        self.tree.add_command(remind)
        self.tree.add_command(badwords)
        self.tree.add_command(warnlist)
        self.tree.add_command(give_temp_role)
        self.tree.add_command(warn)
        self.tree.add_command(unwarn)
        self.tree.add_command(mute)
        self.tree.add_command(unmute)
        self.tree.add_command(ban)
        self.tree.add_command(unban)
        self.tree.add_command(delete)
        self.tree.add_command(staff)
        self.tree.add_command(setup_support)
        self.tree.add_command(setup_applications)
        try:
            from mc_status import StatusButtonsView
            self.add_view(StatusButtonsView())
        except Exception:
            pass
        self.add_view(VerifyView())
        self.add_view(WelcomeButtonsView())
        self.add_view(SupportHubView())
        self.add_view(TicketCloseView())
        self.add_view(IdeaVotingView())
        self.add_view(ApplicationView())

    async def find_player_by_nick(self, nick: str, users_data: dict):
        if not users_data or "players" not in users_data:
            return None
        uuid = await get_uuid_by_name(nick)
        if not uuid:
            return None
        uuid_clean = uuid.replace("-", "")
        if uuid_clean in users_data["players"]:
            return uuid_clean, users_data["players"][uuid_clean]
        return None

    async def find_player_by_id(self, player_id: int, users_data: dict):
        if not users_data or "players" not in users_data:
            return None
        for uuid, data in users_data["players"].items():
            if data.get("player-id") == player_id:
                return uuid, data
        return None

    async def find_player_by_discord(self, discord_id: str, users_data: dict):
        if not users_data or "players" not in users_data:
            return None
        for uuid, data in users_data["players"].items():
            if data.get("discord-id") == discord_id:
                return uuid, data
        return None

    def get_group_prefix(self, group_name: str, users_data: dict) -> str:
        return ""

    async def on_ready(self):
        print('==================================================')
        print(f'✨ Kingdom of Joy активирован: {self.user}')
        print(f'📍 Часовой пояс установлен: МСК (UTC+3)')
        print('==================================================')
        self.presence_update.start()
        self.reminder_check.start()
        try:
            from mc_status import auto_update_status_task
            if not auto_update_status_task.is_running():
                auto_update_status_task.start(self)
                print("✅ Автообновление мониторинга запущено")
        except Exception as e:
            print(f"⚠️ Ошибка запуска таска мониторинга: {e}")
        verify_channel = self.get_channel(VERIFY_CHANNEL_ID)
        if verify_channel:
            data = load_json(VERIFY_MSG_FILE, {})
            msg_id = data.get("message_id")
            if msg_id:
                try:
                    msg = await verify_channel.fetch_message(msg_id)
                    if msg:
                        print("✅ Сообщение верификации уже существует.")
                        return
                except:
                    pass
            embed = discord.Embed(
                title="🔐 Верификация",
                description=("Для получения доступа ко всем каналам сервера, пожалуйста, нажмите кнопку ниже.\n"
                             "После верификации вы получите основную роль и сможете участвовать в жизни сообщества."),
                color=0x5865F2
            )
            view = VerifyView()
            msg = await verify_channel.send(embed=embed, view=view)
            save_json(VERIFY_MSG_FILE, {"message_id": msg.id})
            print("✅ Сообщение верификации отправлено.")

    @tasks.loop(minutes=5)
    async def presence_update(self):
        statuses = ["Kingdom of Joy | !sync", "Защита Эфира...", "Под управлением Создателя", "Майнкрафт"]
        status = random.choice(statuses)
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status))

    @tasks.loop(minutes=2)  # оптимизация: реже
    async def reminder_check(self):
        reminders = load_json(REMINDERS_FILE, [])
        now = datetime.now(MSK).timestamp()
        updated = []
        for rem in reminders:
            if now >= rem["unix"]:
                try:
                    ch = self.get_channel(rem["channel_id"])
                    if ch:
                        await ch.send(make_blockquote(f"⏰ <@{rem['user_id']}>, **Напоминание:** {rem['text']}"))
                except Exception:
                    pass
            else:
                updated.append(rem)
        if len(updated) != len(reminders):
            save_json(REMINDERS_FILE, updated)

    async def on_member_join(self, member: discord.Member):
        verified_role = member.guild.get_role(VERIFY_ROLE_ID)
        if verified_role and verified_role in member.roles:
            return
        unverified_role = member.guild.get_role(UNVERIFIED_ROLE_ID)
        if unverified_role and unverified_role not in member.roles:
            try:
                await member.add_roles(unverified_role)
                await send_log(member.guild, "📥 Выдана неверифицированная роль", f"Пользователю {member.mention} выдана роль {unverified_role.mention}.", color=0xf1c40f)
            except Exception as e:
                print(f"❌ Не удалось выдать неверифицированную роль: {e}")
        welcome_ch = self.get_channel(WELCOME_CHANNEL_ID)
        if not welcome_ch:
            return
        banner_file = create_welcome_banner(member.display_name)
        embed = discord.Embed(
            title="👑 Новый Странник ступил в Kingdom of Joy!",
            description=f"Приветствуем тебя, {member.mention}!\nЗагляни в <#1520119059566559282> для навигации по серверу.\n\n🔐 Для получения доступа пройди верификацию в канале <#{VERIFY_CHANNEL_ID}>.",
            color=0x7864c8,
            timestamp=datetime.now(MSK)
        )
        embed.set_image(url="attachment://welcome_banner.png")
        await welcome_ch.send(content=f"👋 {member.mention}", embed=embed, file=banner_file, view=WelcomeButtonsView(member.guild.id))
        await send_log(member.guild, "📥 Новый Участник", f"Пользователь {member.mention} (`{member.id}`) присоединился к серверу.", color=0x2ecc71)

    async def on_member_remove(self, member: discord.Member):
        await send_log(member.guild, "📤 Участник Покинул Сервер", f"Пользователь **{member.name}** (`{member.id}`) вышел с сервера.", color=0xe74c3c)

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or after.author.bot:
            return
        if before.content == after.content:
            return
        if not before.guild:
            return
        if before.channel.id == EXCLUDED_LOG_CHANNEL:
            return
        embed = discord.Embed(title="✏️ Сообщение изменено", color=0xf1c40f, timestamp=datetime.now(MSK))
        embed.add_field(name="Автор", value=before.author.mention, inline=True)
        embed.add_field(name="Канал", value=before.channel.mention, inline=True)
        embed.add_field(name="До", value=before.content[:1024] or "*(пусто)*", inline=False)
        embed.add_field(name="После", value=after.content[:1024] or "*(пусто)*", inline=False)
        embed.set_footer(text=f"ID сообщения: {before.id}")
        log_channel = before.guild.get_channel(LOGS_CHANNEL_ID)
        if log_channel:
            try:
                await log_channel.send(embed=embed)
            except Exception as e:
                print(f"❌ Ошибка отправки лога редактирования: {e}")

    async def on_message_delete(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return
        if message.channel.id == EXCLUDED_LOG_CHANNEL:
            return
        embed = discord.Embed(title="🗑️ Сообщение удалено", color=0xe74c3c, timestamp=datetime.now(MSK))
        embed.add_field(name="Автор", value=message.author.mention, inline=True)
        embed.add_field(name="Канал", value=message.channel.mention, inline=True)
        embed.add_field(name="Содержание", value=message.content[:1024] or "*(вложение/пусто)*", inline=False)
        embed.set_footer(text=f"ID сообщения: {message.id}")
        log_channel = message.guild.get_channel(LOGS_CHANNEL_ID)
        if log_channel:
            try:
                await log_channel.send(embed=embed)
            except Exception as e:
                print(f"❌ Ошибка отправки лога удаления: {e}")

    def is_allowed_staff(self, interaction: discord.Interaction) -> bool:
        m = interaction.user
        if m.id in CREATOR_AND_ROLE_IDS:
            return True
        return any(r.id in [CREATOR_ROLE_ID, FOUNDER_ROLE_ID, MODERATOR_ROLE_ID] for r in m.roles)

    def check_hierarchy(self, moderator: discord.Member, target: discord.Member) -> bool:
        if moderator.id in CREATOR_AND_ROLE_IDS:
            return True
        if is_high_staff(target):
            return False
        if target.id in CREATOR_AND_ROLE_IDS or any(r.id in IMMUNE_ROLE_IDS for r in target.roles):
            return False
        return target.top_role.position < moderator.top_role.position

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(make_blockquote("❌ У вас недостаточно прав для выполнения этой команды."))
            return
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send(make_blockquote("❌ У бота нет необходимых прав для выполнения этого действия."))
            return
        print(f"❌ Ошибка в префиксной команде {ctx.command}: {error}")
        traceback.print_exc()

    async def on_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        original_error = getattr(error, 'original', error)
        if isinstance(original_error, (app_commands.MissingPermissions, app_commands.MissingRole)):
            msg = "❌ У вас недостаточно прав для использования этой команды."
        elif isinstance(original_error, app_commands.BotMissingPermissions):
            missing = ", ".join(original_error.missing_permissions)
            msg = f"❌ У бота отсутствуют необходимые права: `{missing}`"
        elif isinstance(original_error, app_commands.CommandOnCooldown):
            msg = f"⏳ Команда на перезарядке. Подождите `{original_error.retry_after:.1f}` сек."
        elif isinstance(original_error, (app_commands.TransformerError, app_commands.BadArgument)):
            msg = "⚠️ Переданы некорректные аргументы для команды."
        else:
            msg = "❌ Произошла внутренняя ошибка при выполнении команды. Информация отправлена в логи."
            print(f"❌ Критическая ошибка в Слэш-команде /{interaction.command.name if interaction.command else 'Unknown'}: {original_error}")
            traceback.print_exc()
            if interaction.guild:
                tb_text = "".join(traceback.format_exception(type(original_error), original_error, original_error.__traceback__))
                if len(tb_text) > 900:
                    tb_text = tb_text[:900] + "\n... [срезано]"
                await send_log(
                    interaction.guild,
                    "💥 Ошибка Слэш-Команды",
                    f"**Команда:** `/{interaction.command.name if interaction.command else 'Unknown'}`\n"
                    f"**Вызвал:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                    f"**Канал:** {interaction.channel.mention}\n\n"
                    f"```python\n{tb_text}\n```",
                    color=0xff0000
                )
        try:
            if interaction.response.is_done():
                await interaction.followup.send(make_blockquote(msg), ephemeral=True)
            else:
                await interaction.response.send_message(make_blockquote(msg), ephemeral=True)
        except Exception as e:
            print(f"❌ Не удалось отправить сообщение об ошибке пользователю: {e}")

    async def on_message(self, message):
        if message.author == self.user:
            return
        lowered_content = message.content.lower().strip()
        if lowered_content.startswith("!sync"):
            if message.author.id != 1437779380184158249:
                return
            parts = message.content.split()
            scope = parts[1].lower() if len(parts) > 1 else "guild"
            status_msg = await message.channel.send("⚡ Синхронизирую слэш-команды...")
            try:
                if scope == "guild":
                    self.tree.copy_global_to(guild=message.guild)
                    synced = await self.tree.sync(guild=message.guild)
                    await status_msg.edit(content=f"✅ **Готово!** Скопировано и синхронизировано: `{len(synced)}` команд.")
                else:
                    synced = await self.tree.sync()
                    await status_msg.edit(content=f"🌐 **Готово!** Глобальная синхронизация завершена: `{len(synced)}` команд.")
                await send_log(message.guild, "⚡ Ручная Синхронизация (!sync)", "Создатель выполнил синхронизацию слэш-команд.", color=0x2ecc71)
            except Exception as e:
                await status_msg.edit(content=f"❌ Ошибка синхронизации: `{e}`")
            return
        if lowered_content.startswith(("!мут", "!бан", "!варн", "!удалить")):
            if not self.is_allowed_staff_sync(message):
                await message.channel.send("❌ У вас недостаточно прав для использования этой команды.", delete_after=5)
                return
            parts = message.content.split()
            cmd = parts[0].lower()
            if len(parts) < 2:
                await message.channel.send("❌ Укажите пользователя (например, `!мут @User 1h`)", delete_after=5)
                return
            target = None
            if len(message.mentions) > 0:
                target = message.mentions[0]
            else:
                try:
                    target_id = int(parts[1])
                    target = await message.guild.fetch_member(target_id)
                except:
                    await message.channel.send("❌ Пользователь не найден. Используйте упоминание (@User).", delete_after=5)
                    return
            if not target:
                await message.channel.send("❌ Пользователь не найден.", delete_after=5)
                return
            if is_high_staff(target):
                await message.channel.send("❌ Этот пользователь принадлежит к высшему составу и не может быть наказан.", delete_after=5)
                return
            if cmd == "!мут":
                time_str = parts[2] if len(parts) > 2 else "10m"
                reason = " ".join(parts[3:]) if len(parts) > 3 else "Нарушение"
                duration = parse_duration(time_str)
                try:
                    await target.timeout(duration, reason=reason)
                    await message.channel.send(make_blockquote(f"🔇 {target.mention} отправлен в мут на **{time_str}**."))
                    await send_log(message.guild, "🔇 Выдан Мут (префикс)", f"Модератор: {message.author.mention}\nНарушитель: {target.mention}\nСрок: `{time_str}`\nПричина: *{reason}*", color=0xe74c3c)
                except Exception as e:
                    await message.channel.send(f"❌ Ошибка: {e}")
            elif cmd == "!бан":
                reason = " ".join(parts[2:]) if len(parts) > 2 else "Нарушение"
                try:
                    await target.ban(reason=reason)
                    await message.channel.send(make_blockquote(f"🚫 {target.mention} забанен."))
                    await send_log(message.guild, "🚫 Бан (префикс)", f"Модератор: {message.author.mention}\nНарушитель: {target.mention}\nПричина: *{reason}*", color=0x900c3f)
                except Exception as e:
                    await message.channel.send(f"❌ Ошибка: {e}")
            elif cmd == "!варн":
                reason = " ".join(parts[2:]) if len(parts) > 2 else "Нарушение"
                warns = load_json(WARNS_FILE, {})
                uid = str(target.id)
                count = warns.get(uid, 0) + 1
                if count >= 3:
                    warns[uid] = 0
                    save_json(WARNS_FILE, warns)
                    await target.timeout(timedelta(days=1), reason="3/3 варна")
                    await message.channel.send(make_blockquote(f"⚡ {target.mention} получил 3/3 варнов и замучен на 1 день!"))
                    await send_log(message.guild, "⛔ Авто-Мут (3/3 Варна)", f"Пользователь {target.mention} набрал 3 варна и отправлен в мут на 24 часа.", color=0xc0392b)
                else:
                    warns[uid] = count
                    save_json(WARNS_FILE, warns)
                    await message.channel.send(make_blockquote(f"⚠️ {target.mention} получил варн **({count}/3)**. Причина: *{reason}*"))
                    await send_log(message.guild, "⚠️ Выдан Варн (префикс)", f"Модератор: {message.author.mention}\nНарушитель: {target.mention}\nВарны: `{count}/3`\nПричина: *{reason}*", color=0xe67e22)
            elif cmd == "!удалить":
                amount_str = parts[1] if len(parts) > 1 else "10"
                try:
                    limit = 1000 if amount_str.lower() == "all" else int(amount_str)
                    deleted = await message.channel.purge(limit=limit + 1)
                    await message.channel.send(make_blockquote(f"🧹 Удалено {len(deleted)-1} сообщений."), delete_after=5)
                    await send_log(message.guild, "🧹 Очистка ЧАТА (префикс)", f"Модератор {message.author.mention} очистил `{len(deleted)-1}` сообщений в канале {message.channel.mention}.", color=0x34495e)
                except Exception as e:
                    await message.channel.send(f"❌ Ошибка: {e}")
            return
        chance_triggers = ("правда ли", "какова вероятность", "инфа что", "шанс что", "инфа ")
        if lowered_content.startswith(chance_triggers):
            val = random.randint(0, 100)
            await message.reply(
                make_blockquote(f"🎲 **Шансометр Kingdom of Joy:**\nВероятность этого составляет: **{val}%**"),
                mention_author=False
            )
            return
        if message.channel.id == MEDIA_CHANNEL_ID and not message.thread:
            try:
                await message.create_thread(name="💬 Комментарии")
            except Exception:
                pass
        if isinstance(message.channel, discord.TextChannel) and message.channel.id == SUPPORT_CHANNEL_ID:
            if message.type == discord.MessageType.thread_created or message.author != self.user:
                try:
                    await message.delete()
                except Exception:
                    pass
                return
        if not isinstance(message.channel, discord.TextChannel):
            return
        badwords_cfg = load_json(BADWORDS_FILE, {})
        words = badwords_cfg.get("words", [])
        if words and any(w in lowered_content for w in words):
            uid = str(message.author.id)
            self.user_badword_counts[uid] = self.user_badword_counts.get(uid, 0) + 1
            try:
                await message.delete()
            except Exception:
                pass
            if self.user_badword_counts[uid] >= 3:
                self.user_badword_counts[uid] = 0
                m_time = badwords_cfg.get("mute_time", "1h")
                await message.author.timeout(parse_duration(m_time), reason="3x Запрещенные слова")
                await message.channel.send(make_blockquote(f"🔇 {message.author.mention} отправлен в мут на **{m_time}**."), delete_after=10)
                await send_log(message.guild, "🔇 Авто-Мут (Слова)", f"Пользователь {message.author.mention} получил авто-мут на `{m_time}` за использование запрещённых слов (3/3).", color=0xc0392b)
            else:
                await message.channel.send(make_blockquote(f"⚠️ {message.author.mention}, запрещенное слово! ({self.user_badword_counts[uid]}/3)"), delete_after=5)
            return
        if message.id not in self.reacted_messages:
            placed = False
            if any(u.id in CREATOR_AND_ROLE_IDS for u in message.mentions) or any(t in message.content for t in SPECIAL_TRIGGERS):
                try:
                    await message.add_reaction(CROWN_EMOJI)
                    placed = True
                except Exception:
                    pass
            if any(t in message.content for t in BALKAN_TRIGGERS) and not placed:
                try:
                    await message.add_reaction(random.choice(CUSTOM_REACTIONS))
                    placed = True
                except Exception:
                    pass
            if placed:
                self.reacted_messages.add(message.id)
        await self.process_commands(message)

    def is_allowed_staff_sync(self, message: discord.Message) -> bool:
        m = message.author
        if m.id in CREATOR_AND_ROLE_IDS:
            return True
        return any(r.id in [CREATOR_ROLE_ID, FOUNDER_ROLE_ID, MODERATOR_ROLE_ID] for r in m.roles)

client = KingdomBot()
client.tree.on_error = client.on_tree_error

if __name__ == "__main__":
    client.run(TOKEN, reconnect=True)