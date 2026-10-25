import asyncio
import aiohttp
import base64
import os
import discord
from discord.ext import commands

TOKEN = os.getenv("TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Branding
NOMBRE = "⚔️ Mictlán SsG Sports🗡️"
ESLOGAN = "Del inframundo a la gloria"
PIE = f"{NOMBRE} • {ESLOGAN}"
LOGO_URL = "https://raw.githubusercontent.com/DeagYz/Valhalla-Bot/main/assets/mictlan_logo.jpg"

# Rangos (nombres nuevos)
ROL_LIDER = "💀 Mictlantecuhtli"
ROL_COLIDER = "🦉 Señores del Mictlán"
ROL_TRIAL = "🐕 Xoloitzcuintle"
ROL_CANTERA = "🌱 Almas Nuevas"
ROL_CONTENIDO = "🎭 Cronista"
ROL_V1 = "🐆 Guerreros Jaguar"
ROL_V2 = "🦅 Guerreros Águila"
ROL_ELITE = "👑 Mictlán Elite"

# Se aceptan nombres viejos y nuevos para que nada falle durante la migración
STAFF = ["Lidel", "Co-Lideres", "👑 Líder", "🔱 Co-Líderes", ROL_LIDER, ROL_COLIDER]
TRIAL = ["Trial", "⚔️ Trial", ROL_TRIAL]
CONTENT = ["Creador de Contenido", "🎥 Creador de Contenido", ROL_CONTENIDO]

# canal de texto del equipo -> rol del equipo
EQUIPOS = {
    "mictlan-elite": ROL_ELITE,
    "mictlan-v1": ROL_V1,
    "mictlan-v2": ROL_V2,
    "cantera": ROL_CANTERA,
}

# canal de voz del equipo -> rol del equipo
VOCES_EQUIPO = {
    "MICTLÁN ELITE": ROL_ELITE,
    "V.I": ROL_V1,
    "V.II": ROL_V2,
    "Cantera": ROL_CANTERA,
}
VOCES_SCRIMS = ["Equipo V.1", "Equipo V2"]

# Migración de nombres viejos -> nuevos (rebranding Valhalla -> Mictlán)
MIGRACION_CANALES_TEXTO = {
    "valhalla-elite": "mictlan-elite",
    "valhalla-v1": "mictlan-v1",
    "valhalla-v2": "mictlan-v2",
}
MIGRACION_CANALES_VOZ = {
    "VALHALLA ELITE": "MICTLÁN ELITE",
}
MIGRACION_ROLES = {
    "👑 Valhalla Elite": ROL_ELITE,
    "Valhalla Elite": ROL_ELITE,
    "Mictlán Elite": ROL_ELITE,
    "👑 Líder": ROL_LIDER,
    "Lidel": ROL_LIDER,
    "🔱 Co-Líderes": ROL_COLIDER,
    "Co-Lideres": ROL_COLIDER,
    "⚔️ Trial": ROL_TRIAL,
    "Trial": ROL_TRIAL,
    "🌱 Cantera": ROL_CANTERA,
    "Cantera": ROL_CANTERA,
    "🎥 Creador de Contenido": ROL_CONTENIDO,
    "Creador de Contenido": ROL_CONTENIDO,
    "⚔️ V.I": ROL_V1,
    "V.I": ROL_V1,
    "🛡️ V.II": ROL_V2,
    "V.II": ROL_V2,
}

SOLO_LECTURA = ["reglamento", "requisitos", "ranking-interno", "anuncios-oficiales", "roles-y-estructura", "bienvenida"]
ABIERTOS = [
    "looking-for-5q", "analisis-y-feedback", "off-topic", "memes",
    "solicitudes", "clips-oficiales",
    "content-creators", "scrims-y-entrenamientos", "casual-community"
]

CANAL_AVISO = "admins-gods"
CANAL_SOLICITUDES = "solicitudes"
PALABRAS_SOLICITUD = ["unirme", "unirse", "entrar", "solicitud", "reclutamiento", "tryout", "aplicar"]

# user_id -> channel_id del ticket abierto
tickets_abiertos = {}
setup_hecho = False


def es_staff(member):
    if not isinstance(member, discord.Member):
        return False
    return member.guild_permissions.administrator or any(r.name in STAFF for r in member.roles)


def buscar_rol(guild, nombres):
    for n in nombres:
        rol = discord.utils.get(guild.roles, name=n)
        if rol:
            return rol
    return None


def aplicar_marca(embed):
    embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=PIE, icon_url=LOGO_URL)
    return embed


def embed_reglamento():
    embed = discord.Embed(
        title=f"📜 REGLAMENTO DE {NOMBRE}",
        description="Lee las reglas con atención.\n\n✅ **Reacciona con ✅ para aceptar el reglamento.**",
        color=discord.Color.gold()
    )
    return aplicar_marca(embed)


# Reemplazos de textos viejos (de más específico a más general)
REEMPLAZOS_MARCA = [
    ("From the halls of Valhalla to the Land of Glory", ESLOGAN),
    ("VALHALLA SPORTS MX", "MICTLÁN SSG SPORTS"),
    ("Valhalla Sports MX", "Mictlán SsG Sports"),
    ("VALHALLA", "MICTLÁN"),
    ("Valhalla", "Mictlán"),
    ("valhalla", "mictlán"),
]


def reemplazar_marca(valor):
    if isinstance(valor, str):
        for viejo, nuevo in REEMPLAZOS_MARCA:
            valor = valor.replace(viejo, nuevo)
        return valor
    if isinstance(valor, dict):
        return {k: reemplazar_marca(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [reemplazar_marca(v) for v in valor]
    return valor


def menciona_valhalla(msg):
    texto = (msg.content or "") + " ".join(str(e.to_dict()) for e in msg.embeds)
    return "valhalla" in texto.lower()


async def actualizar_mensajes_viejos(guild):
    """Edita (sin borrar ni quitar reacciones) los mensajes del propio bot que aún dicen Valhalla."""
    for nombre in SOLO_LECTURA:
        canal = discord.utils.get(guild.text_channels, name=nombre)
        if not canal:
            continue
        editados = 0
        try:
            async for msg in canal.history(limit=100):
                if msg.author.id != bot.user.id or not menciona_valhalla(msg):
                    continue
                try:
                    if nombre == "reglamento":
                        await msg.edit(content=None, embed=embed_reglamento())
                    else:
                        embeds = [discord.Embed.from_dict(reemplazar_marca(e.to_dict())) for e in msg.embeds]
                        for e in embeds:
                            if e.footer and e.footer.text:
                                e.set_footer(text=PIE, icon_url=LOGO_URL)
                        await msg.edit(content=reemplazar_marca(msg.content) or None, embeds=embeds)
                    editados += 1
                except Exception as e:
                    print(f"AVISO: No se pudo editar un mensaje en #{nombre}: {e}")
        except Exception as e:
            print(f"AVISO: No se pudo leer el historial de #{nombre}: {e}")
        if editados:
            print(f"OK: {editados} mensajes viejos actualizados en #{nombre}")


def dueno_ticket(canal):
    """Devuelve el user_id dueño de un canal de ticket (guardado en el topic), o None."""
    topic = getattr(canal, "topic", None) or ""
    if topic.startswith("ticket:"):
        try:
            return int(topic.split(":", 1)[1].strip())
        except ValueError:
            return None
    return None


async def limpiar_y_poner_permisos(canal, target, **permisos):
    try:
        await canal.set_permissions(target, overwrite=None)
    except Exception as e:
        print(f"AVISO: No se pudo limpiar permisos de {target} en #{canal}: {e}")
    await canal.set_permissions(target, **permisos)


async def migrar_nombres(guild):
    """Renombra canales y roles con nombres viejos a los nuevos (Mictlán)."""
    for viejo, nuevo in MIGRACION_ROLES.items():
        rol = discord.utils.get(guild.roles, name=viejo)
        if not rol:
            continue
        if discord.utils.get(guild.roles, name=nuevo):
            print(f"AVISO: Existen '{viejo}' y '{nuevo}'; se omite renombrar '{viejo}' (revísalo a mano).")
            continue
        try:
            await rol.edit(name=nuevo, reason="Rebranding a Mictlán")
            print(f"OK: Rol migrado {viejo} -> {nuevo}")
        except Exception as e:
            print(f"AVISO: No se pudo migrar el rol {viejo}: {e}")
    for coleccion, mapa in ((guild.text_channels, MIGRACION_CANALES_TEXTO), (guild.voice_channels, MIGRACION_CANALES_VOZ)):
        for viejo, nuevo in mapa.items():
            canal = discord.utils.get(coleccion, name=viejo)
            if not canal:
                continue
            if discord.utils.get(coleccion, name=nuevo):
                print(f"AVISO: Existen #{viejo} y #{nuevo}; se omite renombrar #{viejo}.")
                continue
            try:
                await canal.edit(name=nuevo, reason="Rebranding a Mictlán")
                print(f"OK: Canal migrado {viejo} -> {nuevo}")
            except Exception as e:
                print(f"AVISO: No se pudo migrar el canal {viejo}: {e}")


def reconstruir_tickets():
    tickets_abiertos.clear()
    for guild in bot.guilds:
        for canal in guild.text_channels:
            if canal.name.startswith("ticket-"):
                uid = dueno_ticket(canal)
                if uid:
                    tickets_abiertos[uid] = canal.id
    print(f"OK: {len(tickets_abiertos)} tickets abiertos recuperados")


async def configurar_servidor(guild):
    # Apodo del bot
    try:
        if guild.me.nick != "Mictlán":
            await guild.me.edit(nick="Mictlán")
            print(f"OK: Apodo cambiado a Mictlán en {guild.name}")
    except Exception as e:
        print(f"AVISO: No se pudo cambiar el apodo en {guild.name}: {e}")

    try:
        await migrar_nombres(guild)
    except Exception as e:
        print(f"AVISO: Error en la migración de nombres en {guild.name}: {e}")

    roles = {r.name: r for r in guild.roles}
    everyone = guild.default_role

    try:
        await everyone.edit(permissions=discord.Permissions(
            view_channel=True, read_message_history=True, send_messages=True,
            add_reactions=True, connect=True, speak=True, use_voice_activation=True,
            embed_links=True, attach_files=True, use_external_emojis=True,
            mention_everyone=False, manage_messages=False, manage_channels=False,
            manage_roles=False, kick_members=False, ban_members=False, administrator=False
        ))
        print("OK: @everyone base")
    except Exception as e:
        print(f"AVISO: No se pudo editar @everyone: {e}")

    async def editar_rol(nombre, permisos, etiqueta):
        try:
            await roles[nombre].edit(permissions=permisos)
            print(f"OK: {nombre} -> {etiqueta}")
        except Exception as e:
            print(f"AVISO: No se pudo editar el rol {nombre}: {e}")

    for nombre in STAFF:
        if nombre in roles:
            await editar_rol(nombre, discord.Permissions.all(), "Admin")

    for nombre in TRIAL:
        if nombre in roles:
            await editar_rol(nombre, discord.Permissions(
                view_channel=True, read_message_history=True, send_messages=True,
                add_reactions=True, connect=True, speak=True, use_voice_activation=True
            ), "Trial")

    for nombre in CONTENT:
        if nombre in roles:
            await editar_rol(nombre, discord.Permissions(
                view_channel=True, read_message_history=True, send_messages=True,
                add_reactions=True, connect=True, speak=True, use_voice_activation=True,
                attach_files=True, embed_links=True
            ), "Content")

    staff_roles = [roles[s] for s in STAFF if s in roles]

    for canal_nombre, rol_nombre in EQUIPOS.items():
        canal = discord.utils.get(guild.text_channels, name=canal_nombre)
        if canal and rol_nombre in roles:
            try:
                await limpiar_y_poner_permisos(canal, everyone, view_channel=False, send_messages=False, read_message_history=False)
                await limpiar_y_poner_permisos(canal, roles[rol_nombre], view_channel=True, read_message_history=True, send_messages=True, add_reactions=True, embed_links=True, attach_files=True)
                for r in staff_roles:
                    await limpiar_y_poner_permisos(canal, r, view_channel=True, read_message_history=True, send_messages=True, manage_messages=True)
                print(f"OK: Privado #{canal_nombre}")
            except Exception as e:
                print(f"AVISO: Error en permisos de #{canal_nombre}: {e}")

    for voz_nombre, rol_voz in VOCES_EQUIPO.items():
        voz = discord.utils.get(guild.voice_channels, name=voz_nombre)
        if voz:
            try:
                await limpiar_y_poner_permisos(voz, everyone, connect=False, speak=False, use_voice_activation=False)
                if rol_voz in roles:
                    await limpiar_y_poner_permisos(voz, roles[rol_voz], connect=True, speak=True, use_voice_activation=True, stream=True)
                for r in staff_roles:
                    await limpiar_y_poner_permisos(voz, r, connect=True, speak=True, use_voice_activation=True, stream=True, priority_speaker=True)
                print(f"OK: Voz privada {voz_nombre}")
            except Exception as e:
                print(f"AVISO: Error en permisos de voz {voz_nombre}: {e}")

    for voz_nombre in VOCES_SCRIMS:
        voz = discord.utils.get(guild.voice_channels, name=voz_nombre)
        if voz:
            try:
                await limpiar_y_poner_permisos(voz, everyone, connect=True, speak=True, use_voice_activation=True, stream=True)
                for t in TRIAL:
                    if t in roles:
                        await limpiar_y_poner_permisos(voz, roles[t], connect=False, speak=False, use_voice_activation=False)
                print(f"OK: Scrims {voz_nombre}")
            except Exception as e:
                print(f"AVISO: Error en scrims {voz_nombre}: {e}")

    for nombre in SOLO_LECTURA:
        canal = discord.utils.get(guild.text_channels, name=nombre)
        if canal:
            try:
                await limpiar_y_poner_permisos(canal, everyone, view_channel=True, read_message_history=True, send_messages=False, add_reactions=True)
                for r in staff_roles:
                    await limpiar_y_poner_permisos(canal, r, send_messages=True, manage_messages=True)
                print(f"OK: Solo lectura #{nombre}")
            except Exception as e:
                print(f"AVISO: Error en #{nombre}: {e}")

    for nombre in ABIERTOS:
        canal = discord.utils.get(guild.text_channels, name=nombre)
        if canal:
            try:
                await limpiar_y_poner_permisos(canal, everyone, view_channel=True, read_message_history=True, send_messages=True, add_reactions=True, embed_links=True, attach_files=True, use_external_emojis=True)
                print(f"OK: Abierto #{nombre}")
            except Exception as e:
                print(f"AVISO: Error en #{nombre}: {e}")

    try:
        await actualizar_mensajes_viejos(guild)
    except Exception as e:
        print(f"AVISO: Error actualizando mensajes viejos en {guild.name}: {e}")

    reglamento = discord.utils.get(guild.text_channels, name="reglamento")
    if reglamento:
        try:
            ya_existe = False
            async for msg in reglamento.history(limit=100):
                if msg.author.id == bot.user.id and msg.embeds and "REGLAMENTO" in str(msg.embeds[0].title).upper():
                    ya_existe = True
                    break
            if not ya_existe:
                msg = await reglamento.send(embed=embed_reglamento())
                await msg.add_reaction("✅")
        except Exception as e:
            print(f"AVISO: Error con #reglamento: {e}")

    print(f"CONFIGURACION COMPLETA: {guild.name}")


async def configurar_todo():
    for guild in bot.guilds:
        try:
            await configurar_servidor(guild)
        except Exception as e:
            print(f"AVISO: Error configurando {guild.name}: {e}")


@bot.event
async def on_ready():
    global setup_hecho
    print(f"Conectado como {bot.user}")
    reconstruir_tickets()
    if setup_hecho:
        return
    setup_hecho = True
    await configurar_todo()


async def analizar_captura(image_url):
    if not XAI_API_KEY:
        return "El análisis de capturas no está disponible en este momento."
    try:
        timeout = aiohttp.ClientTimeout(total=90)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(image_url) as resp:
                resp.raise_for_status()
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
                    return data["choices"][0]["message"]["content"] or "No pude analizar la captura en este momento."
                print(f"AVISO: API de análisis respondió {resp.status}")
                return "No pude analizar la captura en este momento."
    except asyncio.TimeoutError:
        return "⏳ El análisis tardó demasiado. Intenta de nuevo en un momento."
    except Exception as e:
        print(f"AVISO: Error analizando captura: {e}")
        return "⚠️ Hubo un problema al analizar la captura. Intenta de nuevo más tarde."


@bot.event
async def on_member_join(member):
    canal = discord.utils.get(member.guild.text_channels, name="bienvenida")
    if canal:
        embed = discord.Embed(
            title=f"BIENVENIDO A {NOMBRE}",
            description=f"{member.mention}\n\n**{ESLOGAN}.**\n\n"
                        "📌 **Antes de nada:**\n"
                        "1. Lee el canal #reglamento\n"
                        "2. Lee #roles-y-estructura\n"
                        "3. Si quieres unirte, ve a #requisitos y #solicitudes\n\n"
                        "Respeto, disciplina y ganas de mejorar.\n\n"
                        "💬 Habla en #casual-community",
            color=discord.Color.gold()
        )
        aplicar_marca(embed)
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
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
async def on_guild_channel_delete(channel):
    for uid, cid in list(tickets_abiertos.items()):
        if cid == channel.id:
            tickets_abiertos.pop(uid, None)


@bot.event
async def on_raw_reaction_add(payload):
    if payload.emoji.name != "✅" or payload.guild_id is None:
        return
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    channel = guild.get_channel(payload.channel_id)
    if channel and channel.name == "reglamento":
        member = guild.get_member(payload.user_id)
        if member and not member.bot:
            aviso = discord.utils.get(guild.text_channels, name=CANAL_AVISO)
            if aviso:
                await aviso.send(f"✅ {member.mention} aceptó el reglamento.")


async def abrir_ticket(message):
    guild = message.guild
    autor = message.author
    cid = tickets_abiertos.get(autor.id)
    if cid:
        if guild.get_channel(cid):
            await message.channel.send(f"{autor.mention} ya tienes un ticket abierto: <#{cid}>")
            return
        tickets_abiertos.pop(autor.id, None)  # el canal ya no existe

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, read_message_history=True, send_messages=True, embed_links=True, manage_channels=True),
        autor: discord.PermissionOverwrite(view_channel=True, read_message_history=True, send_messages=True),
    }
    for nombre in STAFF:
        rol = discord.utils.get(guild.roles, name=nombre)
        if rol:
            overwrites[rol] = discord.PermissionOverwrite(view_channel=True, read_message_history=True, send_messages=True)
    ticket_channel = await guild.create_text_channel(
        name=f"ticket-{autor.name}", overwrites=overwrites,
        topic=f"ticket:{autor.id}", reason="Ticket de solicitud"
    )
    tickets_abiertos[autor.id] = ticket_channel.id
    embed = discord.Embed(
        title="⚔️ Ticket de Solicitud ⚔️",
        description=f"Bienvenido {autor.mention} a **Mictlán SsG Sports**.\n\n"
                    f"Responde estas preguntas para unirte como **{ROL_TRIAL}**:\n\n"
                    "1️⃣ Usuario de MLBB (con ID)\n"
                    "2️⃣ Rango actual y servidor\n"
                    "3️⃣ Rol principal\n"
                    "4️⃣ ¿Cuántas horas juegas a la semana?\n"
                    "5️⃣ ¿Por qué quieres unirte a Mictlán SsG Sports?\n\n"
                    f"Cuando termines, escribe **listo** y recibirás el rol **{ROL_TRIAL}** automáticamente.",
        color=discord.Color.gold()
    )
    aplicar_marca(embed)
    await ticket_channel.send(embed=embed)
    await message.channel.send(f"{autor.mention} tu ticket se creó en {ticket_channel.mention}")


@bot.event
async def on_message(message):
    if message.author.bot or message.guild is None:
        return

    contenido = message.content.lower().strip()

    if message.channel.name == "analisis-y-feedback" and message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image"):
                await message.channel.send("Analizando captura...")
                analisis = await analizar_captura(attachment.url)
                partes = [analisis[i:i+1900] for i in range(0, len(analisis), 1900)] or ["No pude analizar la captura en este momento."]
                await message.reply(partes[0])
                for parte in partes[1:]:
                    await message.channel.send(parte)

    if message.channel.name == CANAL_SOLICITUDES and not contenido.startswith(bot.command_prefix) and not es_staff(message.author):
        if any(p in contenido for p in PALABRAS_SOLICITUD):
            await abrir_ticket(message)
        else:
            await message.channel.send(
                f"{message.author.mention} para solicitar unirte escribe **!solicitud** "
                "(o un mensaje como \"quiero unirme\").",
                delete_after=15
            )

    if message.channel.name.startswith("ticket-") and contenido == "listo":
        dueno = dueno_ticket(message.channel)
        es_dueno = dueno == message.author.id if dueno else not es_staff(message.author)
        trial_role = buscar_rol(message.guild, [ROL_TRIAL] + TRIAL)
        if es_dueno and trial_role and trial_role not in message.author.roles:
            await message.author.add_roles(trial_role)
            embed = discord.Embed(title="🎉 ¡Bienvenido al Mictlán!", description=f"{message.author.mention} ahora tienes el rol **{trial_role.name}**.", color=discord.Color.green())
            aplicar_marca(embed)
            await message.channel.send(embed=embed)
            aviso = discord.utils.get(message.guild.text_channels, name=CANAL_AVISO)
            if aviso:
                await aviso.send(f"📥 Nuevo {trial_role.name}: {message.author.mention}")
            tickets_abiertos.pop(message.author.id, None)

    await bot.process_commands(message)


@bot.command()
async def solicitud(ctx):
    if ctx.guild is None or ctx.channel.name != CANAL_SOLICITUDES:
        await ctx.send(f"Usa este comando en #{CANAL_SOLICITUDES}.", delete_after=10)
        return
    await abrir_ticket(ctx.message)


@bot.command()
async def anuncio(ctx, *, mensaje: str):
    if not es_staff(ctx.author):
        await ctx.send("No tienes permiso.", delete_after=5)
        return
    canal = discord.utils.get(ctx.guild.text_channels, name="anuncios-oficiales")
    if not canal:
        await ctx.send("No encontré #anuncios-oficiales.")
        return
    embed = discord.Embed(title="⚔️ ANUNCIO OFICIAL ⚔️", description=mensaje, color=discord.Color.gold())
    aplicar_marca(embed)
    embed.timestamp = discord.utils.utcnow()
    await canal.send(embed=embed)
    await ctx.message.delete()
    await ctx.send("✅ Anuncio enviado.", delete_after=3)


@bot.command()
async def cerrar(ctx):
    if ctx.guild is None or not ctx.channel.name.startswith("ticket-"):
        await ctx.send("Este comando solo funciona dentro de un ticket.", delete_after=5)
        return
    if not es_staff(ctx.author):
        await ctx.send("Solo el staff puede cerrar tickets.", delete_after=5)
        return
    for uid, cid in list(tickets_abiertos.items()):
        if cid == ctx.channel.id:
            tickets_abiertos.pop(uid, None)
    dueno = dueno_ticket(ctx.channel)
    if dueno:
        tickets_abiertos.pop(dueno, None)
    await ctx.send("Cerrando ticket...")
    await ctx.channel.delete(reason=f"Ticket cerrado por {ctx.author}")


@bot.command()
async def permisos(ctx):
    if not es_staff(ctx.author):
        await ctx.send("Solo staff.", delete_after=5)
        return
    await ctx.send("Re-aplicando permisos...")
    await configurar_servidor(ctx.guild)
    await ctx.send("✅ Permisos re-aplicados.", delete_after=5)


bot.run(TOKEN)
