# 🤖 Radar CRAI

Bot de Telegram que vigila la disponibilidad de salas de trabajo en grupo del **CRAI Antonio de Ulloa** (Biblioteca de la Universidad de Sevilla) y te avisa automáticamente en cuanto se libera una sala que cumpla el día, la hora y el tamaño que le indiques.

**🔗 Bot en Telegram: [@crainoifierbot](https://t.me/crainoifierbot)**

---

## 📋 ¿Qué hace?

1. El usuario elige, mediante botones interactivos, un **día**, un **bloque horario** y uno o varios **tamaños de sala** (2, 4, 6 u 8 personas).
2. El bot comprueba al instante si ya hay una sala libre con esos criterios.
3. Si no la hay, activa un **radar en segundo plano** que revisa la web del CRAI cada minuto.
4. En cuanto detecta un hueco que cumple los filtros, envía una notificación al chat con la sala, fecha y hora exactas.

---

## 🧰 Tecnologías

- [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) — interacción con la API de Telegram
- `requests` — peticiones HTTP a la web del CRAI
- `BeautifulSoup4` — parseo del HTML de disponibilidad de salas
- `python-dotenv` — gestión de variables de entorno
- Hilo en segundo plano (`threading`) para el escaneo periódico

---

## ⚙️ Requisitos

- Python 3.11+ (o Docker)
- Un token de bot de Telegram, obtenido a través de [@BotFather](https://t.me/BotFather)

---

## 🚀 Instalación

### Opción 1 — Local

```bash
git clone <url-de-tu-repositorio>
cd radar-crai

python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Crea un archivo `.env` en la raíz del proyecto:

```
TELEGRAM_TOKEN=tu_token_de_telegram_aqui
```

Y arranca el bot:

```bash
python bot.py
```

### Opción 2 — Docker / Portainer

El proyecto incluye `Dockerfile` y `docker-compose.yml` listos para desplegar.

1. Sube el proyecto completo (`bot.py`, `requirements.txt`, `Dockerfile`, `docker-compose.yml`) a un repositorio Git (recomendado no incluir el `.env`, usa variables de entorno del stack en su lugar).
2. En Portainer: **Stacks → Add stack**, apunta al repositorio (o sube los archivos manualmente).
3. Define la variable de entorno `TELEGRAM_TOKEN` en la sección **Environment variables** del stack.
4. Pulsa **Deploy the stack**.
5. Revisa los logs del contenedor `radar_crai_bot` para confirmar el arranque correcto (`🤖 Bot en modo DEBUG extremo iniciado.`).

`restart: unless-stopped` está configurado para que el contenedor se reinicie solo si el proceso cae o si se reinicia el host.

---

## 💬 Comandos disponibles

| Comando | Descripción |
|---|---|
| `/start`, `/menu`, `/reservar` | Inicia el asistente para crear una nueva alarma de disponibilidad |
| `/exit` | Cancela la alarma activa del usuario |
| `/help` | Muestra la ayuda básica |

---

## 🔍 Cómo funciona por dentro

- **Extracción de datos**: `buscar_sala_libre()` parsea la tabla HTML (`table_11`) de la web del CRAI, localiza la columna correspondiente al bloque horario elegido y comprueba el estado de cada sala (`Libre` / `Reservada` / `Cerrada`) y su capacidad mediante regex sobre el texto de la celda.
- **Radar en segundo plano**: el hilo `vigilante_crai()` agrupa todas las alarmas activas por fecha para minimizar peticiones a la web (una sola petición HTTP por fecha distinta, aunque haya muchos usuarios esperando el mismo día), y revisa cada 60 segundos.
- **Estado por usuario**: `peticiones_usuarios` y `temp_peticiones` guardan la alarma confirmada y el progreso del asistente de cada `chat_id`, respectivamente.

---

## ⚠️ Limitaciones conocidas

- **Concurrencia**: iterar `peticiones_usuarios.values()` sin copiar el diccionario puede provocar un `RuntimeError` si dos usuarios modifican el estado a la vez, lo que detendría el hilo vigilante silenciosamente. Se recomienda usar `list(peticiones_usuarios.values())` o un `threading.Lock()`.
- **Envío de notificaciones**: un fallo al notificar a un usuario (por ejemplo, si ha bloqueado el bot) puede interrumpir el aviso al resto de usuarios en ese mismo ciclo si no se captura la excepción de forma individual por envío.
- **Formato de fecha**: el valor enviado en `sl_fecha` (`DD-MM-YYYY`) no se ha podido verificar de forma 100% fiable contra el `value` real del desplegable de la web del CRAI; se recomienda confirmarlo inspeccionando `crai_debug.html` para una fecha distinta a la actual.
- El bot depende de que la estructura HTML de la web del CRAI (`biblus.us.es`) no cambie; cualquier rediseño de la página de reservas podría romper el parseo.

---

## 📄 Licencia

Proyecto personal / uso educativo. Ajusta esta sección según corresponda.
