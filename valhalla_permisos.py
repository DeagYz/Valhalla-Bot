import discord
from discord.ext import commands
import aiohttp
import base64

TOKEN = "PEGA_AQUI_TU_TOKEN"
XAI_API_KEY = "PEGA_AQUI_TU_API_KEY"

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

STAFF = ["Lidel", "Co-Lideres", "👑 Líder", "🔱 Co-Líderes"]
TRIAL = ["Trial", "⚔️ Trial"]
CONTENT = ["Creador de Contenido", "🎥 Creador de Contenido"]

EQUIPOS = {
    "valhalla-elite": "👑 Valhalla Elite",
    "valhalla-v1": "⚔️ V.I",
    "valhalla-v2": "🛡️ V.II",
    "cantera": "🌱 Cantera",
}

VOCES_EQUIPO = ["VALHALLA ELITE", "V.I", "V.II", "Cantera"]
VOCES_SCRIMS = ["Equipo V.1", "Equipo V2"]

SOLO_LECTURA = ["reglamento", "requisitos", "ranking-interno", "anuncios-oficiales", "roles-y-estructura", "bienvenida"]
ABIERTOS = [
    "looking-for-5q", "analisis-y-feedback", "off-topic", "memes",
    "solicitudes", "clips-oficiales",
    "content-creators", "scrims-y-entrenamientos", "casual-community"
]

CANAL_AVISO = "admins-gods"
tickets_abiertos = set()

async def limpiar_y_poner_permisos(canal, target, **permisos):
    try:
        await canal.set_permissions(target, overwrite=None)
    except:
        pass
    await canal.set_permissions(target, **permisos)

async def analizar_captura(image_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as resp:
            image_data = await resp.read()
        image_b64 = base64.b64encode(image_data).decode()
        headers = {
            "Authorization": f"Bearer {XAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "grok-4",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analiza esta captura de Mobile Legends: Bang Bang con precisión. "
                                    "Identifica correctamente cada héroe por su apariencia e ícono (no te equivoques de héroe). "
                                    "Si el usuario menciona un héroe específico (como Alaiza, Ling, etc.), enfócate en ese. "
                                    "Da el KDA, oro, daño, MVP y un feedback claro y útil basado en el meta actual. "
                                    "Sé preciso con los nombres de los héroes y no repitas el mismo héroe si no aparece dos veces."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
                        }
                    ]
                }
            ]
        }
        async with session.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                return "No pude analizar la captura en este momento."

@bot.event
async def on_ready():
    print(f"Conectado como {bot.user}")
    guild = bot.guilds[0]
    roles = {r.name: r for r in guild.roles}
    everyone = guild.default_role

    role_emojis = {
        "Trial": "⚔️ Trial",
        "Cantera": "🌱 Cantera",
        "V.II": "🛡️ V.II",
        "V.I": "⚔️ V.I",
        "Valhalla Elite": "👑 Valhalla Elite",
        "Creador de Contenido": "🎥 Creador de Contenido",
        "Co-Lideres": "🔱 Co-Líderes",
        "Lidel": "👑 Líder",
    }
    for old_name, new_name in role_emojis.items():
        if old_name in roles:
            try:
                await roles[old_name].edit(name=new_name)
                print(f"OK: Rol renombrado -> {new_name}")
            except Exception as e:
                print(f"Error renombrando {old_name}: {e}")

    roles = {r.name: r for r in guild.roles}

    await everyone.edit(permissions=discord.Permissions(
        view_channel=True, read_message_history=True, send_messages=True,
        add_reactions=True, connect=True, speak=True, use_voice_activation=True,
        embed_links=True, attach_files=True, use_external_emojis=True,
        mention_everyone=False, manage_messages=False, manage_channels=False,
        manage_roles=False, kick_members=False, ban_members=False, administrator=False
    ))
    print("OK: @everyone base")

    for nombre in STAFF:
        if nombre in roles:
            await roles[nombre].edit(permissions=discord.Permissions.all())
            print(f"OK: {nombre} -> Admin")

    for nombre in TRIAL:
        if nombre in roles:
            await roles[nombre].edit(permissions=discord.Permissions(
                view_channel=True, read_message_history=True, send_messages=True,
                add_reactions=True, connect=True, speak=True, use_voice_activation=True
            ))
            print(f"OK: {nombre} -> Trial")

    for nombre in CONTENT:
        if nombre in roles:
            await roles[nombre].edit(permissions=discord.Permissions(
                view_channel=True, read_message_history=True, send_messages=True,
                add_reactions=True, connect=True, speak=True, use_voice_activation=True,
                attach_files=True, embed_links=True
            ))
            print(f"OK: {nombre} -> Content")

    for canal_nombre, rol_nombre in EQUIPOS.items():
        canal = discord.utils.get(guild.text_channels, name=canal_nombre)
        if canal and rol_nombre in roles:
            await limpiar_y_poner_permisos(canal, everyone, view_channel=False, send_messages=False, read_message_history=False)
            await limpiar_y_poner_permisos(canal, roles[rol_nombre], view_channel=True, read_message_history=True, send_messages=True, add_reactions=True, embed_links=True, attach_files=True)
            for s in STAFF:
                if s in roles:
                    await limpiar_y_poner_permisos(canal, roles[s], view_channel=True, read_message_history=True, send_messages=True, manage_messages=True)
            print(f"OK: Privado #{canal_nombre}")

    for voz_nombre in VOCES_EQUIPO:
        voz = discord.utils.get(guild.voice_channels, name=voz_nombre)
        if voz:
            rol_voz = {"VALHALLA ELITE": "👑 Valhalla Elite", "V.I": "⚔️ V.I", "V.II": "🛡️ V.II", "Cantera": "🌱 Cantera"}.get(voz_nombre)
            await limpiar_y_poner_permisos(voz, everyone, connect=False, speak=False, use_voice_activation=False)
            if rol_voz and rol_voz in roles:
                await limpiar_y_poner_permisos(voz, roles[rol_voz], connect=True, speak=True, use_voice_activation=True, stream=True)
            for s in STAFF:
                if s in roles:
                    await limpiar_y_poner_permisos(voz, roles[s], connect=True, speak=True, use_voice_activation=True, stream=True, priority_speaker=True)
            print(f"OK: Voz privada {voz_nombre}")

    for voz_nombre in VOCES_SCRIMS:
        voz = discord.utils.get(guild.voice_channels, name=voz_nombre)
        if voz:
            await limpiar_y_poner_permisos(voz, everyone, connect=True, speak=True, use_voice_activation=True, stream=True)
            if "⚔️ Trial" in roles:
                await limpiar_y_poner_permisos(voz, roles["⚔️ Trial"], connect=False, speak=False, use_voice_activation=False)
            print(f"OK: Scrims {voz_nombre}")

    for nombre in SOLO_LECTURA:
        canal = discord.utils.get(guild.text_channels, name=nombre)
        if canal:
            await limpiar_y_poner_permisos(canal, everyone, view_channel=True, read_message_history=True, send_messages=False, add_reactions=True)
            for s in STAFF:
                if s in roles:
                    await limpiar_y_poner_permisos(canal, roles[s], send_messages=True, manage_messages=True)
            print(f"OK: Solo lectura #{nombre}")

    for nombre in ABIERTOS:
        canal = discord.utils.get(guild.text_channels, name=nombre)
        if canal:
            await limpiar_y_poner_permisos(canal, everyone, view_channel=True, read_message_history=True, send_messages=True, add_reactions=True, embed_links=True, attach_files=True, use_external_emojis=True)
            print(f"OK: Abierto #{nombre}")

    reglamento = discord.utils.get(guild.text_channels, name="reglamento")
    if reglamento:
        ya_existe = False
        async for msg in reglamento.history(limit=5):
            if msg.embeds and "REGLAMENTO" in str(msg.embeds[0].title):
                ya_existe = True
                break
        if not ya_existe:
            embed = discord.Embed(
                title="📜 REGLAMENTO DE VALHALLA SPORTS MX",
                description="Lee las reglas con atención.\n\n✅ **Reacciona con ✅ para aceptar el reglamento.**",
                color=discord.Color.gold()
            )
            embed.set_footer(text="Valhalla Sports MX")
            msg = await reglamento.send(embed=embed)
            await msg.add_reaction("✅")

    print("CONFIGURACION COMPLETA")

@bot.event
async def on_member_join(member):
    canal = discord.utils.get(member.guild.text_channels, name="bienvenida")
    if canal:
        embed = discord.Embed(
            title="⚔️ BIENVENIDO A VALHALLA SPORTS MX ⚔️",
            description=f"{member.mention}\n\nFrom the halls of Valhalla to the Land of Glory.\n\n"
                        "📌 **Antes de nada:**\n"
                        "1. Lee el canal #reglamento\n"
                        "2. Lee #roles-y-estructura\n"
                        "3. Si quieres unirte, ve a #requisitos y #solicitudes\n\n"
                        "Respeto, disciplina y ganas de mejorar.\n\n"
                        "💬 Habla en #casual-community",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Valhalla Sports MX")
        await canal.send(embed=embed)
    aviso = discord.utils.get(member.guild.text_channels, name=CANAL_AVISO)
    if aviso:
        await aviso.send(f"🟢 {member.mention} se unió al servidor.")

@bot.event
async def on_member_remove(member):
    aviso = discord.utils.get(member.guild.text_channels, name=CANAL_AVISO)
    if aviso:
        await aviso.send(f"🔴 {member} salió del servidor.")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.emoji.name != "✅":
        return
    guild = bot.get_guild(payload.guild_id)
    channel = guild.get_channel(payload.channel_id)
    if channel and channel.name == "reglamento":
        member = guild.get_member(payload.user_id)
        if member and not member.bot:
            aviso = discord.utils.get(guild.text_channels, name=CANAL_AVISO)
            if aviso:
                await aviso.send(f"✅ {member.mention} aceptó el reglamento.")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.name == "analisis-y-feedback" and message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image"):
                await message.channel.send("Analizando captura...")
                analisis = await analizar_captura(attachment.url)
                if len(analisis) <= 1900:
                    await message.reply(analisis)
                else:
                    partes = [analisis[i:i+1900] for i in range(0, len(analisis), 1900)]
                    await message.reply(partes[0])
                    for parte in partes[1:]:
                        await message.channel.send(parte)

    if message.channel.name == "solicitudes":
        if message.author.id in tickets_abiertos:
            await message.channel.send(f"{message.author.mention} ya tienes un ticket abierto.")
            return
        guild = message.guild
        staff_roles = [discord.utils.get(guild.roles, name=n) for n in STAFF]
        staff_roles = [r for r in staff_roles if r]
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            message.author: discord.PermissionOverwrite(view_channel=True, read_message_history=True, send_messages=True),
        }
        for role in staff_roles:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, read_message_history=True, send_messages=True)
        ticket_channel = await guild.create_text_channel(name=f"ticket-{message.author.name}", overwrites=overwrites, reason="Ticket de solicitud")
        tickets_abiertos.add(message.author.id)
        embed = discord.Embed(
            title="⚔️ Ticket de Solicitud ⚔️",
            description=f"Bienvenido {message.author.mention} a **Valhalla Sports MX**.\n\n"
                        "Responde estas preguntas para unirte como Trial:\n\n"
                        "1️⃣ Usuario de MLBB (con ID)\n"
                        "2️⃣ Rango actual y servidor\n"
                        "3️⃣ Rol principal\n"
                        "4️⃣ ¿Cuántas horas juegas a la semana?\n"
                        "5️⃣ ¿Por qué quieres unirte a Valhalla?\n\n"
                        "Cuando termines, escribe **listo** y recibirás el rol Trial automáticamente.",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Valhalla Sports MX")
        await ticket_channel.send(embed=embed)
        await message.channel.send(f"{message.author.mention} tu ticket se creó en {ticket_channel.mention}")

    if message.channel.name.startswith("ticket-") and message.content.lower().strip() == "listo":
        trial_role = discord.utils.get(message.guild.roles, name="⚔️ Trial")
        if trial_role and trial_role not in message.author.roles:
            await message.author.add_roles(trial_role)
            embed = discord.Embed(title="🎉 ¡Bienvenido a Valhalla!", description=f"{message.author.mention} ahora tienes el rol **⚔️ Trial**.", color=discord.Color.green())
            await message.channel.send(embed=embed)
            aviso = discord.utils.get(message.guild.text_channels, name=CANAL_AVISO)
            if aviso:
                await aviso.send(f"📥 Nuevo Trial: {message.author.mention}")
            tickets_abiertos.discard(message.author.id)

    await bot.process_commands(message)

@bot.command()
async def anuncio(ctx, *, mensaje: str):
    if not any(role.name in STAFF for role in ctx.author.roles):
        await ctx.send("No tienes permiso.", delete_after=5)
        return
    canal = discord.utils.get(ctx.guild.text_channels, name="anuncios-oficiales")
    if not canal:
        await ctx.send("No encontré #anuncios-oficiales.")
        return
    embed = discord.Embed(title="⚔️ ANUNCIO OFICIAL ⚔️", description=mensaje, color=discord.Color.gold())
    embed.set_footer(text="From the halls of Valhalla to the Land of Glory")
    embed.timestamp = discord.utils.utcnow()
    await canal.send(embed=embed)
    await ctx.message.delete()
    await ctx.send("✅ Anuncio enviado.", delete_after=3)

@bot.command()
async def cerrar(ctx):
    if not ctx.channel.name.startswith("ticket-"):
        await ctx.send("Este comando solo funciona dentro de un ticket.", delete_after=5)
        return
    if not any(role.name in STAFF for role in ctx.author.roles):
        await ctx.send("Solo el staff puede cerrar tickets.", delete_after=5)
        return
    await ctx.send("Cerrando ticket...")
    await ctx.channel.delete(reason=f"Ticket cerrado por {ctx.author}")

@bot.command()
async def permisos(ctx):
    if not any(role.name in STAFF for role in ctx.author.roles):
        await ctx.send("Solo staff.", delete_after=5)
        return
    await ctx.send("Re-aplicando permisos...")
    await bot.dispatch("ready")
    await ctx.send("✅ Permisos re-aplicados.", delete_after=5)

bot.run(TOKEN)