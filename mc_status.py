import matplotlib
matplotlib.use('Agg')

import discord
from discord.ext import tasks, commands
from discord import app_commands
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import io
import os
import json
import asyncio
import socket
from datetime import datetime, timezone, timedelta
from mcstatus import JavaServer
import traceback

MSK_TZ = timezone(timedelta(hours=3))
SERVER_IP = "45.152.160.92:25727"
DISPLAY_DOMAINS = ["balkangrief.burmalda.me:25727", "kingdomofjoy.gamepvp.ru:25727"]
MONITORING_CHANNEL_ID = 1526686756580229200
MSG_ID_FILE = "mc_status_msg_id.txt"
HISTORY_FILE = "online_history.json"
online_history = []

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
    targets = []
    if SERVER_IP and "xxx" not in SERVER_IP:
        targets.append(SERVER_IP)
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
                return True, status.players.online, status.players.max
            except Exception as e:
                print(f"⚠️ Порт открыт, сбой mcstatus ({host}:{port}): {e}")
                return True, 0, 100
    return False, 0, 100

def generate_double_graph(history_data, max_slots=100):
    fig, (ax24, ax30) = plt.subplots(2, 1, figsize=(8, 6), facecolor='#1e1f22')
    now_msk = datetime.now(MSK_TZ)
    ax24.set_facecolor('#1e1f22')
    cutoff_24h = now_msk - timedelta(hours=24)
    data_24h = [item for item in history_data if item[0] >= cutoff_24h]
    if not data_24h:
        data_24h = [(now_msk, 0)]
    times_24 = [item[0].strftime("%H:%M") for item in data_24h]
    players_24 = [item[1] for item in data_24h]
    ax24.plot(times_24, players_24, color='#7864c8', linewidth=2)
    ax24.fill_between(times_24, players_24, color='#7864c8', alpha=0.25)
    ax24.set_title("📊 ИСТОРИЯ ОНЛАЙНА ЗА 24 ЧАСА (ИНТЕРВАЛ 1 ЧАС)", fontsize=9, color='#808080', pad=8)
    ax24.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax24.set_ylim(0, max(max_slots, max(players_24) + 2))
    step_24 = max(1, len(times_24) // 12)
    ax24.set_xticks(range(0, len(times_24), step_24))
    ax24.set_xticklabels([times_24[i] for i in range(0, len(times_24), step_24)], rotation=0)
    ax24.tick_params(colors='#808080', labelsize=8)
    for spine in ax24.spines.values():
        spine.set_color('#2b2d31')
    ax24.grid(True, color='#2b2d31', linestyle='--', linewidth=0.5)
    ax30.set_facecolor('#1e1f22')
    cutoff_30m = now_msk - timedelta(minutes=30)
    data_30m = [item for item in history_data if item[0] >= cutoff_30m]
    if not data_30m:
        data_30m = [(now_msk, 0)]
    times_30 = [item[0].strftime("%H:%M") for item in data_30m]
    players_30 = [item[1] for item in data_30m]
    ax30.plot(times_30, players_30, color='#2ecc71', marker='o', linewidth=2, markersize=4)
    ax30.fill_between(times_30, players_30, color='#2ecc71', alpha=0.25)
    ax30.set_title("⚡ ДЕТАЛИЗАЦИЯ ЗА ПОСЛЕДНИЕ 30 МИНУТ", fontsize=9, color='#808080', pad=8)
    ax30.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax30.set_ylim(0, max(max_slots, max(players_30) + 2))
    step_30 = max(1, len(times_30) // 3)
    ax30.set_xticks(range(0, len(times_30), step_30))
    ax30.set_xticklabels([times_30[i] for i in range(0, len(times_30), step_30)], rotation=0)
    ax30.tick_params(colors='#808080', labelsize=8)
    for spine in ax30.spines.values():
        spine.set_color('#2b2d31')
    ax30.grid(True, color='#2b2d31', linestyle='--', linewidth=0.5)
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
        is_online, current_players, max_players = await check_mc_server()
        print(f"🔄 Статус: {'онлайн' if is_online else 'офлайн'}, игроков: {current_players}/{max_players}")
        now_msk = datetime.now(MSK_TZ)
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
        else:
            embed = discord.Embed(title="🎮 Мониторинг Minecraft Сервера", color=0xe74c3c, timestamp=now_msk)
            embed.add_field(name="🔴 Статус", value="**Сервер недоступен или выключен.**", inline=False)
            embed.add_field(name="⚠️ Ошибка подключения", value="`Сервер не отвечает по указанным адресам`", inline=False)
        domains_text = "\n".join([f"• `{d}`" for d in DISPLAY_DOMAINS])
        embed.add_field(name="🌐 Домены для подключения", value=domains_text, inline=False)
        embed.set_footer(text=f"Авто-обновление раз в 3 минуты • Сегодня, в {time_str}")
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

@app_commands.command(name="mcstatus", description="Показать статус и график онлайна Minecraft")
async def mcstatus_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await update_status_message(interaction.client)
    await interaction.followup.send("📊 Данные мониторинга в канале успешно обновлены!", ephemeral=True)

@tasks.loop(minutes=3)
async def auto_update_status_task(bot: commands.Bot):
    try:
        await update_status_message(bot)
    except Exception as e:
        print(f"⚠️ Ошибка в автообновлении: {e}")
        traceback.print_exc()

@auto_update_status_task.before_loop
async def before_auto_update():
    await asyncio.sleep(5)