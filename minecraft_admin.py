import discord
from discord.ext import commands
from discord import app_commands
from config import SFTP_HOST, SFTP_PORT, SFTP_USER, SFTP_PASSWORD, SFTP_REMOTE_PATH, RCON_HOST, RCON_PORT, RCON_PASSWORD
import asyncio
import json
import os
import yaml
import paramiko
import time
import socket
import struct
import aiohttp
from datetime import datetime, timezone, timedelta

# ==================== КОНСТАНТЫ ====================
LK_CHANNEL_ID = 1529937315890204836
HIGHER_ROLES = [1526681612337549343, 1505438802653741096, 1530235500886102216, 1505235504826814535]
CREATOR_AND_ROLE_IDS = [1437779380184158249, 1001913830261129237, 1308313239775608863]
MSK = timezone(timedelta(hours=3))
LOGS_CHANNEL_ID = 1505274763096883230

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def make_blockquote(text: str) -> str:
    lines = text.strip().split('\n')
    return "\n".join([f"> {line}" if line.strip() else ">" for line in lines])

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

def parse_time_duration(time_str: str) -> int:
    if not time_str:
        return -1
    unit = time_str[-1].lower()
    try:
        value = int(time_str[:-1])
    except:
        return -1
    if unit == 'd':
        return value * 86400
    elif unit == 'h':
        return value * 3600
    elif unit == 'm':
        return value * 60
    elif unit == 's':
        return value
    else:
        return -1

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

# ==================== RCON ====================
class RconClient:
    def __init__(self, host, port, password):
        self.host = host
        self.port = port
        self.password = password
        self.sock = None
        self.authenticated = False

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5.0)
            self.sock.connect((self.host, self.port))
            self._send_packet(3, self.password.encode('utf-8'))
            response = self._receive_packet()
            if response['id'] == -1:
                self.authenticated = False
                raise Exception("Неверный пароль RCON")
            self.authenticated = True
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения к RCON: {e}")
            return False

    def _send_packet(self, packet_id, payload):
        packet = struct.pack('<ii', packet_id, 0) + payload + b'\x00\x00'
        packet = struct.pack('<i', len(packet)) + packet
        self.sock.send(packet)

    def _receive_packet(self):
        size_data = self.sock.recv(4)
        if len(size_data) < 4:
            return None
        size = struct.unpack('<i', size_data)[0]
        packet = self.sock.recv(size)
        packet_id, response_id = struct.unpack('<ii', packet[:8])
        payload = packet[8:-2].decode('utf-8')
        return {'id': packet_id, 'response_id': response_id, 'payload': payload}

    def command(self, cmd):
        if not self.authenticated:
            self.connect()
        try:
            self._send_packet(2, cmd.encode('utf-8'))
            response = self._receive_packet()
            return response['payload'] if response else ""
        except Exception as e:
            print(f"❌ Ошибка выполнения RCON команды {cmd}: {e}")
            return ""

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None
            self.authenticated = False

# ==================== MOJANG API ====================
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

async def find_player_in_users(nick: str, users_data: dict) -> tuple:
    if not users_data or "players" not in users_data:
        return None
    uuid = await get_uuid_by_name(nick)
    if not uuid:
        return None
    uuid_clean = uuid.replace("-", "")
    if uuid_clean in users_data["players"]:
        return uuid_clean, users_data["players"][uuid_clean]
    return None

# ==================== ОТПРАВКА ЛОГА ====================
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

# ==================== КОМАНДЫ ====================

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
        found = None
        for uuid, data in users_data["players"].items():
            if data.get("discord-id") == discord_id:
                found = (uuid, data)
                break
        if not found:
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
        uuid, data = found
    else:
        if player.startswith("id "):
            try:
                player_id = int(player.split(" ", 1)[1])
            except:
                await interaction.followup.send("❌ Неверный формат ID. Используйте: `/lk id 123`")
                return
            found = None
            for uuid, data in users_data["players"].items():
                if data.get("player-id") == player_id:
                    found = (uuid, data)
                    break
            if not found:
                await interaction.followup.send(f"❌ Игрок с ID `{player_id}` не найден.")
                return
            uuid, data = found
        else:
            found = await find_player_in_users(player, users_data)
            if not found:
                await interaction.followup.send(f"❌ Игрок `{player}` не найден.")
                return
            uuid, data = found
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
        if expire == -1:
            groups_list.append(f"• {gname} (бессрочно)")
        else:
            expire_date = datetime.fromtimestamp(expire / 1000).strftime("%d.%m.%Y %H:%M")
            groups_list.append(f"• {gname} (до {expire_date})")
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

@app_commands.command(name="вход", description="🔗 Привязать Discord к Minecraft аккаунту")
@app_commands.describe(nickname="Ваш ник в Minecraft", password="Пароль от аккаунта (для проверки)")
async def вход(interaction: discord.Interaction, nickname: str, password: str):
    if interaction.channel.id != LK_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Эта команда доступна только в канале <#{LK_CHANNEL_ID}>.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    discord_id = str(interaction.user.id)
    users_data = await get_users_yml_sftp()
    if not users_data or "players" not in users_data:
        await interaction.followup.send("❌ Ошибка чтения базы игроков с сервера.")
        return
    for uuid, data in users_data["players"].items():
        if data.get("discord-id") == discord_id:
            await interaction.followup.send("❌ Этот Discord уже привязан к игроку.", ephemeral=True)
            return
    uuid_clean = await get_uuid_by_name(nickname)
    if not uuid_clean:
        await interaction.followup.send(f"❌ Игрок `{nickname}` не найден в Minecraft.", ephemeral=True)
        return
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
        await send_log(interaction.guild, "🔗 Привязка Discord", f"Пользователь {interaction.user.mention} привязал аккаунт {nickname}", color=0x2ecc71)
    else:
        await interaction.followup.send("❌ Ошибка сохранения данных на сервере. Обратитесь к администрации.", ephemeral=True)

@app_commands.command(name="addgroup", description="👑 Выдать группу игроку")
@app_commands.describe(nickname="Ник игрока", group="Название группы", duration="Время (1d, 2h, 30m, 10s) или оставьте пустым для бессрочной")
async def addgroup(interaction: discord.Interaction, nickname: str, group: str, duration: str = None):
    if interaction.channel.id != LK_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Эта команда доступна только в канале <#{LK_CHANNEL_ID}>.", ephemeral=True)
        return
    if not any(r.id in HIGHER_ROLES for r in interaction.user.roles) and interaction.user.id not in CREATOR_AND_ROLE_IDS:
        await interaction.response.send_message("❌ Доступно только руководству проекта.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    users_data = await get_users_yml_sftp()
    if not users_data or "players" not in users_data:
        await interaction.followup.send("❌ Ошибка чтения базы игроков.")
        return
    found = await find_player_in_users(nickname, users_data)
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
        seconds = parse_time_duration(duration)
        if seconds == -1:
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
    if not any(r.id in HIGHER_ROLES for r in interaction.user.roles) and interaction.user.id not in CREATOR_AND_ROLE_IDS:
        await interaction.response.send_message("❌ Доступно только руководству проекта.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    users_data = await get_users_yml_sftp()
    if not users_data or "players" not in users_data:
        await interaction.followup.send("❌ Ошибка чтения базы игроков.")
        return
    found = await find_player_in_users(nickname, users_data)
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
    if not any(r.id in HIGHER_ROLES for r in interaction.user.roles) and interaction.user.id not in CREATOR_AND_ROLE_IDS:
        await interaction.response.send_message("❌ Доступно только руководству проекта.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    users_data = await get_users_yml_sftp()
    if not users_data or "players" not in users_data:
        await interaction.followup.send("❌ Ошибка чтения базы игроков.")
        return
    found = await find_player_in_users(nickname, users_data)
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
            expire_date = datetime.fromtimestamp(expire / 1000).strftime("%d.%m.%Y %H:%M")
            lines.append(f"• {gname} (до {expire_date})")
    embed = discord.Embed(
        title=f"📋 Группы игрока {nickname}",
        description="\n".join(lines),
        color=0x5865F2,
        timestamp=datetime.now(MSK)
    )
    await interaction.followup.send(embed=embed)

@app_commands.command(name="setbalance", description="💰 Установить баланс игроку")
@app_commands.describe(nickname="Ник игрока", amount="Сумма")
async def setbalance(interaction: discord.Interaction, nickname: str, amount: float):
    if interaction.channel.id != LK_CHANNEL_ID:
        await interaction.response.send_message(f"❌ Эта команда доступна только в канале <#{LK_CHANNEL_ID}>.", ephemeral=True)
        return
    if not any(r.id in HIGHER_ROLES for r in interaction.user.roles) and interaction.user.id not in CREATOR_AND_ROLE_IDS:
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
    found = await find_player_in_users(nickname, users_data)
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
    if not any(r.id in HIGHER_ROLES for r in interaction.user.roles) and interaction.user.id not in CREATOR_AND_ROLE_IDS:
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
    found = await find_player_in_users(nickname, users_data)
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
    if not any(r.id in HIGHER_ROLES for r in interaction.user.roles) and interaction.user.id not in CREATOR_AND_ROLE_IDS:
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
    found = await find_player_in_users(nickname, users_data)
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
    if not any(r.id in HIGHER_ROLES for r in interaction.user.roles) and interaction.user.id not in CREATOR_AND_ROLE_IDS:
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
    found = await find_player_in_users(nickname, users_data)
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
    if not any(r.id in HIGHER_ROLES for r in interaction.user.roles) and interaction.user.id not in CREATOR_AND_ROLE_IDS:
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
    found = await find_player_in_users(nickname, users_data)
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
    if not any(r.id in HIGHER_ROLES for r in interaction.user.roles) and interaction.user.id not in CREATOR_AND_ROLE_IDS:
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
    found = await find_player_in_users(nickname, users_data)
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
    if not any(r.id in HIGHER_ROLES for r in interaction.user.roles) and interaction.user.id not in CREATOR_AND_ROLE_IDS:
        await interaction.response.send_message("❌ Доступно только руководству проекта.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    users_data = await get_users_yml_sftp()
    if not users_data or "players" not in users_data:
        await interaction.followup.send("❌ Ошибка чтения базы игроков.")
        return
    found = await find_player_in_users(nickname, users_data)
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
