import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
from bs4 import BeautifulSoup
import threading
import time
from datetime import datetime, timedelta
import os
import re
from dotenv import load_dotenv

# ================= CONFIGURACIÓN =================
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
URL_CRAI = "https://biblus.us.es/2024/reserva_salas/CRAIU/menu_user.php"

bot = telebot.TeleBot(TOKEN)

peticiones_usuarios = {}
temp_peticiones = {}

def obtener_fecha_siguiente_dia(nombre_dia):
    dias_semana = {"Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4, "Sábado": 5, "Domingo": 6}
    hoy = datetime.now()
    dia_objetivo = dias_semana[nombre_dia]
    
    dias_faltantes = (dia_objetivo - hoy.weekday() + 7) % 7
    if dias_faltantes == 0 and hoy.hour >= 20:
        dias_faltantes = 7
        
    fecha_objetivo = hoy + timedelta(days=dias_faltantes)
    return fecha_objetivo.strftime("%d-%m-%Y")

# ---- COMANDOS BÁSICOS ----

@bot.message_handler(commands=['help'])
def comando_help(message):
    texto_ayuda = "🤖 **Radar CRAI**\n\n🔹 /start - Crear alarma\n🔹 /exit - Cancelar"
    bot.reply_to(message, texto_ayuda, parse_mode="Markdown")

@bot.message_handler(commands=['exit'])
def comando_exit(message):
    chat_id = message.chat.id
    if chat_id in peticiones_usuarios:
        del peticiones_usuarios[chat_id]
        bot.reply_to(message, "✅ **Alarma cancelada.**", parse_mode="Markdown")
    else:
        bot.reply_to(message, "No tenías ninguna alarma activa.")

@bot.message_handler(commands=['start', 'menu', 'reservar'])
def mostrar_menu_dias(message):
    chat_id = message.chat.id
    markup = InlineKeyboardMarkup()
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    
    botones = []
    for dia in dias_semana:
        botones.append(InlineKeyboardButton(f"🗓 {dia}", callback_data=f"d_{dia}"))
    
    for i in range(0, len(botones), 2):
        if i + 1 < len(botones):
            markup.row(botones[i], botones[i+1])
        else:
            markup.row(botones[i])
            
    bot.send_message(chat_id, "Selecciona el **DÍA**:", reply_markup=markup, parse_mode="Markdown")

def generar_teclado_tamanos(chat_id):
    markup = InlineKeyboardMarkup()
    capacidades_disponibles = ["2", "4", "6", "8"]
    seleccionadas = temp_peticiones[chat_id].get("tamanos", [])
    
    for cap in capacidades_disponibles:
        icono = "✅" if cap in seleccionadas else "⬜️"
        btn = InlineKeyboardButton(f"{icono} {cap} personas", callback_data=f"cap_{cap}")
        markup.add(btn)
        
    btn_confirmar = InlineKeyboardButton("🚀 Confirmar y Activar Radar", callback_data="confirmar_alarma")
    markup.add(btn_confirmar)
    return markup

# ---- GESTOR DE BOTONES INTERACTIVOS ----

@bot.callback_query_handler(func=lambda call: True)
def manejar_botones(call):
    chat_id = call.message.chat.id
    datos_boton = call.data 
    
    if datos_boton.startswith("d_"):
        dia_elegido = datos_boton.split("_")[1]
        markup_horas = InlineKeyboardMarkup()
        
        horarios_crai = [
            "08:15 - 10:00", "10:00 - 12:00", "12:00 - 14:30", 
            "14:30 - 16:30", "16:30 - 18:30", "18:30 - 20:45",
            "08:15 - 11:00", "11:00 - 13:00", "13:00 - 15:00", 
            "15:00 - 17:00", "17:00 - 19:00", "19:00 - 20:45"
        ]
        horarios_crai.sort()
        
        botones = []
        for horario in horarios_crai:
            hora_inicio = horario.split(" - ")[0]
            botones.append(InlineKeyboardButton(f"⏰ {horario}", callback_data=f"h_{dia_elegido}_{hora_inicio}"))
        
        for i in range(0, len(botones), 2):
            if i + 1 < len(botones):
                markup_horas.row(botones[i], botones[i+1])
            else:
                markup_horas.row(botones[i])
                
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=f"Día seleccionado: **{dia_elegido}**.\n\nElige el bloque horario:",
            reply_markup=markup_horas,
            parse_mode="Markdown"
        )

    elif datos_boton.startswith("h_"):
        partes = datos_boton.split("_")
        dia_elegido = partes[1]
        hora_elegida = partes[2]
        
        temp_peticiones[chat_id] = {
            "dia": dia_elegido,
            "fecha": obtener_fecha_siguiente_dia(dia_elegido),
            "hora_inicio": hora_elegida,
            "tamanos": [] 
        }
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=f"⏳ Has elegido **{dia_elegido} a las {hora_elegida}**.\n\nSelecciona tamaños:",
            reply_markup=generar_teclado_tamanos(chat_id),
            parse_mode="Markdown"
        )

    elif datos_boton.startswith("cap_"):
        if chat_id not in temp_peticiones: return
        cap_elegida = datos_boton.split("_")[1]
        tamanos_actuales = temp_peticiones[chat_id]["tamanos"]
        
        if cap_elegida in tamanos_actuales:
            tamanos_actuales.remove(cap_elegida)
        else:
            tamanos_actuales.append(cap_elegida)
            
        bot.edit_message_reply_markup(
            chat_id=chat_id, 
            message_id=call.message.message_id, 
            reply_markup=generar_teclado_tamanos(chat_id)
        )

    elif datos_boton == "confirmar_alarma":
        if chat_id not in temp_peticiones: return
        datos_temp = temp_peticiones[chat_id]
        
        if len(datos_temp["tamanos"]) == 0:
            bot.answer_callback_query(call.id, "⚠️ Elige al menos un tamaño.", show_alert=True)
            return

        fecha = datos_temp["fecha"]
        hora = datos_temp["hora_inicio"]
        tamanos = datos_temp["tamanos"]
        
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="⏳ Comprobando web del CRAI...")
            print(f"\n[TEST MANUAL] Solicitando fecha {fecha} a la web...")
            
            cabeceras_falsas = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            respuesta = requests.post(URL_CRAI, data={'sl_fecha': fecha}, headers=cabeceras_falsas, timeout=10)

            # GUARDAR HTML PARA ANALIZAR
            with open("crai_debug.html", "w", encoding="utf-8") as f:
                f.write(respuesta.text)
            print("[LOG] Guardado el HTML en 'crai_debug.html' para inspección.")

            hay_libre, sala_encontrada = buscar_sala_libre(respuesta.text, hora, tamanos)
            
            if hay_libre:
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    text=f"🟢 ¡Sala libre detectada al instante!: **{sala_encontrada}** a las **{hora}**.",
                    parse_mode="Markdown"
                )
            else:
                peticiones_usuarios[chat_id] = datos_temp 
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    text=f"🔴 Ocupado. Radar activo en segundo plano.",
                    parse_mode="Markdown"
                )
            del temp_peticiones[chat_id]
                
        except Exception as e:
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Error. Revisa la consola.")
            print(f"[ERROR]: {e}")


# ---- EXTRACTOR HTML CON LOGS EXTREMOS ----

def buscar_sala_libre(html_web, hora_inicio_buscada, tamanos_aceptados):
    print(f"\n--- INICIO DE BÚSQUEDA --- (Hora inicio: '{hora_inicio_buscada}' | Tamaños admitidos: {tamanos_aceptados})")
    soup = BeautifulSoup(html_web, 'html.parser')
    
    # Buscamos todas las tablas legítimas
    tablas = soup.find_all('table', id='table_11')
    print(f"[LOG] Tablas válidas encontradas: {len(tablas)}")
    
    for num_tabla, tabla in enumerate(tablas):
        thead = tabla.find('thead')
        if not thead: 
            continue
            
        cabeceras = thead.find_all('th')
        indice_columna = -1
        
        # Iteramos las columnas para encontrar la que EMPIEZA por la hora indicada
        for i, cabecera in enumerate(cabeceras):
            texto_cabecera = cabecera.text.strip() # Ej: "14:30 - 16:30"
            if not texto_cabecera: 
                continue
                
            # Extraemos la hora de inicio del bloque (lo que está antes del guion)
            hora_inicio_bloque = texto_cabecera.split('-')[0].strip()
            
            if hora_inicio_bloque == hora_inicio_buscada.strip():
                indice_columna = i
                print(f"  -> [OK] Tabla #{num_tabla}: El bloque '{texto_cabecera}' empieza a las {hora_inicio_buscada}. Columna [{i}]")
                break
                
        if indice_columna == -1:
            print(f"  -> [X] Tabla #{num_tabla}: Ningún bloque horario empieza a las {hora_inicio_buscada}.")
            continue
            
        tbody = tabla.find('tbody')
        if not tbody: 
            continue
            
        filas = tbody.find_all('tr')
        for num_fila, fila in enumerate(filas):
            celdas = fila.find_all('td')
            if len(celdas) <= indice_columna: 
                continue
                
            # Primera celda: Contiene nombre y capacidad (div interno)
            celda_nombre = celdas[0]
            texto_sala_completo = celda_nombre.get_text(separator=" ", strip=True) # une nombre y div interno
            
            celda_objetivo = celdas[indice_columna]
            clases_celda = celda_objetivo.get('class', [])
            texto_estado = celda_objetivo.text.strip().upper()
            
            # Condición robusta para comprobar si está LIBRE
            es_libre = 'usrSalaLIBRE' in clases_celda or 'LIBRE' in texto_estado
            
            if es_libre:
                print(f"     [HUECO DETECTADO] -> Sala: {texto_sala_completo} está LIBRE.")
                
                # Buscamos la capacidad con una regex flexible en todo el bloque de texto
                match = re.search(r'Capacidad\s*(\d+)', texto_sala_completo, re.IGNORECASE)
                capacidad_sala = match.group(1) if match else None
                
                # Backup manual si falla la regex
                if not capacidad_sala:
                    for cap in ["2", "4", "6", "8"]:
                        if f"{cap} personas" in texto_sala_completo.lower():
                            capacidad_sala = cap
                            break
                
                print(f"     [CONTROL] Capacidad de la sala: {capacidad_sala} personas.")
                
                if capacidad_sala in tamanos_aceptados:
                    # Limpiamos el nombre para que quede bonito sacando solo lo anterior a la barra "/"
                    nombre_bonito = texto_sala_completo.split('/')[0].strip()
                    print(f"     [APROBADO] ¡Sala idónea encontrada! Notificando...")
                    return True, f"{nombre_bonito} ({capacidad_sala} personas)"
                else:
                    print(f"     [OMITIDO] No coincide con el tamaño que pide el usuario.")
                    
    print("--- FIN DE BÚSQUEDA --- (No se han encontrado salas libres que cumplan los filtros)")
    return False, None


# ---- CEREBRO EN SEGUNDO PLANO ----

def vigilante_crai():
    while True:
        if len(peticiones_usuarios) > 0:
            print(f"\n--- [CRON] EJECUTANDO ESCANEO AUTOMÁTICO ---")
            usuarios_avisados = []
            fechas_a_revisar = set(p['fecha'] for p in list(peticiones_usuarios.values()))
            
            for fecha in fechas_a_revisar:
                try:
                    cabeceras_falsas = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    respuesta = requests.post(URL_CRAI, data={'sl_fecha': fecha}, headers=cabeceras_falsas, timeout=15)
                    
                    for chat_id, peticion in list(peticiones_usuarios.items()):
                        if peticion["fecha"] == fecha:
                            hay_libre, sala = buscar_sala_libre(respuesta.text, peticion["hora_inicio"], peticion["tamanos"])
                            if hay_libre:
                                mensaje_alerta = (
                                    f"🚨 **¡HUECO ENCONTRADO EN EL CRAI!** 🚨\n\n"
                                    f"Sala: **{sala}**\nFecha: **{peticion['fecha']}**\nHora: **{peticion['hora_inicio']}**\n\n"
                                    f"👉 {URL_CRAI}"
                                )
                                try:
                                    bot.send_message(chat_id, mensaje_alerta, parse_mode="Markdown")
                                    usuarios_avisados.append(chat_id)
                                except Exception as e_envio:
                                    print(f"[ERROR ENVÍO a {chat_id}]: {e_envio}")
                except Exception as e:
                    print(f"[ERROR CRON]: {e}")
            
            for uid in usuarios_avisados:
                if uid in peticiones_usuarios:
                    del peticiones_usuarios[uid]
                    
        time.sleep(60) # Bajado a 1 minuto para pruebas de depuración rápidas

# ================= ARRANQUE =================
hilo = threading.Thread(target=vigilante_crai)
hilo.daemon = True
hilo.start()

print("🤖 Bot en modo DEBUG extremo iniciado.")
while True:
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        print(f"Error polling: {e}")
        time.sleep(5)
