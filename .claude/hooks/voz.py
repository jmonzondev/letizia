#!/usr/bin/env python3
# copia generada por capa_proyecto.sh desde ~/.claude: edita el original, no esta copia
"""Hook Stop de Claude Code: convierte el último bloque ```voz``` de la respuesta en un audio que Jose escucha cuando
quiere, desde donde quiera. Nada suena solo.

- Audio: ElevenLabs (clave en voz.env); sin clave, la voz de Apple (`say`, Mónica) como respaldo.
- Buzón (CANAL=web): cada ficha (mp3 + texto) va a `~/.claude/voz/`, con una página `index.html` que las lista con su
  reproductor. El propio hook sirve esa carpeta en `127.0.0.1:8765` (`voz.py --servir`, con rangos HTTP, que iOS los exige) y
  Tailscale la publica en su red privada (el hook lanza `tailscale serve --bg 8765` la primera vez). Desde el iPhone, iPad u otro Mac con
  Tailscale: `https://<mac>.<red>.ts.net/`. El aviso «oye, mensaje» es un texto por iMessage a su propio chat con el enlace a la
  ficha (y, si NTFY_TOPIC está puesto, un push por ntfy). Canal cerrado y suyo: sin bots ni terceros.
- Otros canales: `imessage` (texto y audio adjunto; el adjunto no llega al iPhone en el chat con uno mismo), `icloud`
  (carpeta de iCloud Drive), `ninguno` (solo Mac).
- Mac: `.claude/voz/ultima.mp3` del proyecto (y el buzón); `/voz leer` lo reproduce. Solo suena al momento si VOZ_MAC=1.
- Config: `.claude/voz.env` del proyecto; si no existe, `~/.claude/voz.env`. Las variables de entorno mandan sobre el fichero.
- Registro: `.claude/voz.log`. Nunca bloquea la sesión: sale siempre con 0.
- Uso directo: `voz.py --prueba [--mac]` · `voz.py --texto "..." [--mac]` · `voz.py --fichero ruta.txt [--mac]` (la ficha desde
  un fichero; es lo que usa /resolver en modo móvil antes de preguntar) · `voz.py --voces` (voces de la cuenta de ElevenLabs) ·
  `voz.py --url` (enlace del buzón y estado del servidor y de Tailscale) · `voz.py --servir` (el servidor local, en primer plano).
Contrato del bloque voz: docs/VOZ.md. Guardia D3 del cuaderno: la copia global se calla si el repo tiene la suya.
"""
import html
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PRUEBA = ("Prueba de voz del prototipo. Si me oyes con acento de España y sin sonar a robot, vamos bien. "
          "Decisión de ejemplo: el códec con pérdida. Recomiendo AAC. ¿Vale?")

proy = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
carpeta = proy / ".claude" / "voz"
log = proy / ".claude" / "voz.log"
TAILSCALE_RUTAS = ("/Applications/Tailscale.app/Contents/MacOS/Tailscale", "/usr/local/bin/tailscale",
                   "/opt/homebrew/bin/tailscale")


def nota(msg):
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S") + " " + msg + "\n")
    except Exception:
        pass


# ---------- configuración ----------

CLAVES = ("ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID", "ELEVENLABS_MODEL", "CANAL", "IMESSAGE_DESTINO", "ICLOUD_CARPETA",
          "VOZ_MAC", "VOZ_APPLE", "VOZ_BUZON", "VOZ_PUERTO", "VOZ_URL", "NTFY_TOPIC")


def fichero_env():
    for f in (proy / ".claude" / "voz.env", Path.home() / ".claude" / "voz.env"):
        if f.exists():
            return f
    return proy / ".claude" / "voz.env"


def cargar_env():
    cfg = {}
    try:
        for linea in fichero_env().read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, v = linea.split("=", 1)
            cfg[k.strip()] = v.split(" #", 1)[0].strip().strip('"').strip("'")
    except Exception:
        pass
    for k in CLAVES:
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    return cfg


def guardar_env(clave, valor):
    """Fija clave=valor en voz.env sin tocar el resto (rellena la línea o la añade)."""
    f = fichero_env()
    try:
        lineas = f.read_text(encoding="utf-8").splitlines() if f.exists() else []
    except Exception:
        lineas = []
    hecho = False
    for i, linea in enumerate(lineas):
        if re.match(r"\s*" + re.escape(clave) + r"\s*=", linea):
            comentario = " #" + linea.split(" #", 1)[1] if " #" in linea else ""
            lineas[i] = f"{clave}={valor}{comentario}"
            hecho = True
            break
    if not hecho:
        lineas.append(f"{clave}={valor}")
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    except Exception as e:
        nota(f"no pude guardar {clave} en {f}: {e}")


def buzon(cfg):
    return Path(os.path.expanduser(cfg.get("VOZ_BUZON") or "~/.claude/voz"))


def puerto(cfg):
    try:
        return int(cfg.get("VOZ_PUERTO") or 8765)
    except ValueError:
        return 8765


# ---------- HTTP mínimo ----------

def http(url, datos=None, cabeceras=None, timeout=60):
    req = urllib.request.Request(url, data=datos, headers=cabeceras or {}, method="POST" if datos else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def error_http(e):
    if isinstance(e, urllib.error.HTTPError):
        try:
            return f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:200]}"
        except Exception:
            return f"HTTP {e.code}"
    return str(e)[:200]


# ---------- audio ----------

def voces_elevenlabs(cfg):
    _, cuerpo = http("https://api.elevenlabs.io/v1/voices", cabeceras={"xi-api-key": cfg["ELEVENLABS_API_KEY"]},
                     timeout=30)
    return json.loads(cuerpo).get("voices", [])


def es_espanola(v):
    etiquetas = " ".join(str(x) for x in (v.get("labels") or {}).values()).lower()
    return "spanish" in etiquetas or "español" in etiquetas or "castil" in etiquetas or bool(re.search(r"\bes\b", etiquetas))


def elegir_voz(cfg):
    """Sin ELEVENLABS_VOICE_ID: la primera voz en español de la cuenta (si no, la primera); se apunta en voz.env."""
    voces = voces_elevenlabs(cfg)
    if not voces:
        raise RuntimeError("la cuenta de ElevenLabs no tiene voces")
    v = next((x for x in voces if es_espanola(x)), voces[0])
    guardar_env("ELEVENLABS_VOICE_ID", v["voice_id"])
    nota(f"voz de ElevenLabs elegida: {v.get('name')} ({v['voice_id']}); cámbiala con /voz voces")
    return v["voice_id"]


def audio_elevenlabs(texto, cfg, destino):
    voz = cfg.get("ELEVENLABS_VOICE_ID") or elegir_voz(cfg)
    modelo = cfg.get("ELEVENLABS_MODEL") or "eleven_multilingual_v2"
    datos = json.dumps({"text": texto, "model_id": modelo,
                        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.2}}).encode("utf-8")
    _, cuerpo = http(f"https://api.elevenlabs.io/v1/text-to-speech/{voz}?output_format=mp3_44100_128", datos,
                     {"xi-api-key": cfg["ELEVENLABS_API_KEY"], "Content-Type": "application/json",
                      "Accept": "audio/mpeg"}, timeout=90)
    destino.write_bytes(cuerpo)
    return destino


def audio_apple(texto, cfg, destino):
    say = shutil.which("say")
    if not say:
        raise RuntimeError("sin `say` (no es macOS)")
    voz = cfg.get("VOZ_APPLE") or "Mónica"
    r = subprocess.run([say, "-v", voz, "-o", str(destino), "--data-format=aac", texto],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if r.returncode != 0:
        subprocess.run([say, "-o", str(destino), "--data-format=aac", texto], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=True)
    return destino


def generar_audio(texto, cfg, nombre, destino_dir=None):
    """Genera el audio en destino_dir (por defecto, .claude/voz/ del proyecto) y deja copia como ultima.<ext> en el proyecto."""
    destino_dir = destino_dir or carpeta
    destino_dir.mkdir(parents=True, exist_ok=True)
    carpeta.mkdir(parents=True, exist_ok=True)
    if cfg.get("ELEVENLABS_API_KEY"):
        try:
            ruta = audio_elevenlabs(texto, cfg, destino_dir / f"{nombre}.mp3")
            nota(f"audio ElevenLabs: {ruta.name} ({ruta.stat().st_size // 1024} KB)")
        except Exception as e:
            nota(f"ElevenLabs falló ({error_http(e)}); uso la voz de Apple")
            ruta = audio_apple(texto, cfg, destino_dir / f"{nombre}.m4a")
    else:
        nota("sin ELEVENLABS_API_KEY en voz.env: voz de Apple")
        ruta = audio_apple(texto, cfg, destino_dir / f"{nombre}.m4a")
    for viejo in carpeta.glob("ultima.*"):  # «ultima» con la extensión que toque
        if viejo.suffix != ruta.suffix:
            viejo.rename(carpeta / f"anterior{viejo.suffix}")
    shutil.copyfile(ruta, carpeta / f"ultima{ruta.suffix}")
    return ruta


# ---------- buzón web ----------

MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
DIAS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")

PAGINA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Voz">
<meta name="theme-color" content="#f6f5f2" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#121212" media="(prefers-color-scheme: dark)">
<title>Buzón de voz</title>
<style>
:root{--fondo:#f6f5f2;--tarjeta:#fff;--texto:#1a1a1a;--suave:#6b6b6b;--acento:#c2410c;--borde:#e6e3dd}
@media(prefers-color-scheme:dark){:root{--fondo:#121212;--tarjeta:#1c1c1e;--texto:#f2f2f2;--suave:#9a9a9a;--acento:#ff8a50;--borde:#2a2a2d}}
*{box-sizing:border-box}
body{margin:0;background:var(--fondo);color:var(--texto);font:17px/1.45 -apple-system,system-ui,sans-serif;padding:max(16px,env(safe-area-inset-top)) 16px 48px;max-width:720px;margin:0 auto}
h1{font-size:22px;margin:4px 0 16px}
h1 small{display:block;color:var(--suave);font-weight:400;font-size:14px;margin-top:2px}
article{background:var(--tarjeta);border:1px solid var(--borde);border-radius:14px;padding:14px 16px;margin-bottom:12px}
article.nueva{border-color:var(--acento);box-shadow:0 0 0 2px var(--acento)}
.meta{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;color:var(--suave);font-size:13px;margin-bottom:6px}
.tipo{color:var(--acento);font-weight:600;font-size:14px}
p{margin:0 0 10px;white-space:pre-wrap}
audio{width:100%;height:40px}
.pie{color:var(--suave);font-size:13px;text-align:center;margin-top:24px}
</style>
</head>
<body>
<h1>Buzón de voz<small>__RESUMEN__</small></h1>
__FICHAS__
<p class="pie">Nada suena solo: pulsa play. Contesta en la app de Claude.</p>
<script>
var h=decodeURIComponent(location.hash.slice(1));if(h){var e=document.getElementById(h);if(e){e.classList.add('nueva');e.scrollIntoView({block:'center'});}}
</script>
</body>
</html>
"""


def titulo_ficha(texto):
    """Lo que va en la cabecera de la tarjeta y en el aviso: «Decisión uno de seis», «Hallazgo», «Terminado», «Prueba de voz»…"""
    m = re.search(r"(Decisi[oó]n \w+ de \w+|Hallazgo|Terminado|Resumen)", texto)
    if m:
        return m.group(1)
    cabeza = texto.split(":", 1)[0].strip() if ":" in texto[:60] else ""
    if cabeza and len(cabeza) <= 40:
        return cabeza
    primera = re.split(r"[.!?¿¡]", texto, 1)[0].strip()
    return primera[:40].rstrip() + ("…" if len(primera) > 40 else "")


def fecha_legible(t):
    e = time.localtime(t)
    return f"{DIAS[e.tm_wday]} {e.tm_mday} {MESES[e.tm_mon - 1]} · {e.tm_hour:02d}:{e.tm_min:02d}"


def tarjeta(f):
    return (f'<article id="{html.escape(f["id"], quote=True)}">'
            f'<div class="meta"><span class="tipo">{html.escape(f["titulo"])}</span>'
            f'<span>{html.escape(fecha_legible(f["t"]))}</span><span>{html.escape(f["proyecto"])}</span>'
            f'<span>{f["segundos"]} s</span></div>'
            f'<p>{html.escape(f["texto"])}</p>'
            f'<audio controls preload="none" src="{html.escape(f["audio"], quote=True)}"></audio></article>')


def escribir_pagina(dir_buzon, fichas):
    recientes = sorted(fichas, key=lambda f: f["t"], reverse=True)[:100]
    resumen = f"{len(fichas)} ficha{'s' if len(fichas) != 1 else ''} · actualizado {fecha_legible(time.time())}"
    cuerpo = "\n".join(tarjeta(f) for f in recientes) if recientes else "<p>Todavía no hay fichas.</p>"
    (dir_buzon / "index.html").write_text(PAGINA.replace("__RESUMEN__", html.escape(resumen)).replace("__FICHAS__", cuerpo),
                                          encoding="utf-8")


def apuntar_en_buzon(texto, audio, cfg, ident):
    """Añade la ficha a fichas.json y regenera index.html. Devuelve la ficha."""
    d = buzon(cfg)
    d.mkdir(parents=True, exist_ok=True)
    indice = d / "fichas.json"
    try:
        fichas = json.loads(indice.read_text(encoding="utf-8")) if indice.exists() else []
    except Exception:
        fichas = []
    ficha = {"id": ident, "t": time.time(), "titulo": titulo_ficha(texto), "proyecto": proy.name, "texto": texto,
             "audio": audio.name, "segundos": max(1, round(len(texto.split()) / 2.8))}
    fichas.append(ficha)
    indice.write_text(json.dumps(fichas, ensure_ascii=False, indent=0), encoding="utf-8")
    escribir_pagina(d, fichas)
    return ficha


# --- servidor local con rangos (iOS no reproduce audio sin Range) ---

class Trozo:
    def __init__(self, f, n):
        self.f, self.n = f, n

    def read(self, k=-1):
        if self.n <= 0:
            return b""
        k = self.n if k is None or k < 0 or k > self.n else k
        datos = self.f.read(k)
        self.n -= len(datos)
        return datos

    def close(self):
        self.f.close()


def manejador(dir_buzon):
    class Manejador(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(dir_buzon), **k)

        def log_message(self, *a):
            pass

        def guess_type(self, ruta):
            r = str(ruta).lower()
            if r.endswith(".mp3"):
                return "audio/mpeg"
            if r.endswith(".m4a"):
                return "audio/mp4"
            return super().guess_type(ruta)

        def end_headers(self):
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "no-cache")
            super().end_headers()

        def send_head(self):
            rango = self.headers.get("Range")
            ruta = self.translate_path(self.path)
            m = re.match(r"bytes=(\d*)-(\d*)$", (rango or "").strip())
            if not m or not os.path.isfile(ruta):
                return super().send_head()
            tam = os.path.getsize(ruta)
            if m.group(1):
                ini = int(m.group(1))
                fin = min(int(m.group(2)), tam - 1) if m.group(2) else tam - 1
            else:
                ini, fin = max(0, tam - int(m.group(2) or 0)), tam - 1
            if ini > fin or ini >= tam:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{tam}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            f = open(ruta, "rb")
            f.seek(ini)
            self.send_response(206)
            self.send_header("Content-Type", self.guess_type(ruta))
            self.send_header("Content-Range", f"bytes {ini}-{fin}/{tam}")
            self.send_header("Content-Length", str(fin - ini + 1))
            self.send_header("Last-Modified", self.date_time_string(os.fstat(f.fileno()).st_mtime))
            self.end_headers()
            return Trozo(f, fin - ini + 1)

    return Manejador


def servir(cfg):
    """Sirve el buzón en 127.0.0.1:VOZ_PUERTO hasta que lo maten. Solo escucha en local; Tailscale lo publica."""
    d = buzon(cfg)
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "index.html").exists():
        escribir_pagina(d, [])
    servidor = ThreadingHTTPServer(("127.0.0.1", puerto(cfg)), manejador(d))
    servidor.daemon_threads = True
    servidor.serve_forever()


def servidor_vivo(p):
    try:
        with socket.create_connection(("127.0.0.1", p), timeout=0.5):
            return True
    except OSError:
        return False


def asegurar_servidor(cfg):
    """Arranca el servidor local si no está (proceso aparte, sobrevive al hook). Devuelve True si responde."""
    p = puerto(cfg)
    if servidor_vivo(p):
        return True
    env = dict(os.environ, VOZ_BUZON=str(buzon(cfg)), VOZ_PUERTO=str(p))
    subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--servir"], stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True, env=env,
                     cwd=str(buzon(cfg)))
    for _ in range(20):
        time.sleep(0.1)
        if servidor_vivo(p):
            nota(f"servidor del buzón arrancado en 127.0.0.1:{p}")
            return True
    nota(f"el servidor del buzón no responde en 127.0.0.1:{p}")
    return False


# --- Tailscale: la dirección pública (privada, de su red) del buzón ---

def tailscale_cli():
    return shutil.which("tailscale") or next((r for r in TAILSCALE_RUTAS if os.path.exists(r)), None)


def tailscale_json(*args):
    cli = tailscale_cli()
    if not cli:
        return None
    r = subprocess.run([cli, *args], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=8)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


def url_publicada(cfg):
    """La dirección con la que `tailscale serve` publica el puerto del buzón, o None si no está publicado."""
    p = str(puerto(cfg))
    estado = tailscale_json("serve", "status", "--json") or {}
    for host_puerto, web in (estado.get("Web") or {}).items():
        for ruta, h in ((web or {}).get("Handlers") or {}).items():
            if p in str((h or {}).get("Proxy", "")):
                host, _, pto = host_puerto.rpartition(":")
                esquema = "https" if pto == "443" else "http"
                extra = "" if pto in ("443", "80") else f":{pto}"
                return f"{esquema}://{host}{extra}{ruta if ruta.endswith('/') else ruta + '/'}"
    return None


def tailscale_estado(cfg):
    """'sin' (no instalado) · 'parado' (instalado pero sin sesión o apagado) · 'conectado'."""
    if not tailscale_cli():
        return "sin"
    st = tailscale_json("status", "--json") or {}
    return "conectado" if st.get("BackendState") == "Running" and (st.get("Self") or {}).get("DNSName") else "parado"


def publicar_tailscale(cfg):
    """Publica el puerto del buzón en la red privada si no lo está: `tailscale serve --bg <puerto>` (https) y, si el tailnet
    no tiene certificados, `--http=80`. Una vez; Tailscale lo recuerda entre reinicios."""
    cli = tailscale_cli()
    p = str(puerto(cfg))
    for args in (["serve", "--bg", p], ["serve", "--bg", "--http=80", p]):
        r = subprocess.run([cli, *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
        if r.returncode == 0:
            nota(f"buzón publicado: tailscale {' '.join(args)}")
            return True
        nota(f"tailscale {' '.join(args)} falló: {' '.join(r.stdout.split())[:160]}")
    return False


def url_buzon(cfg):
    """VOZ_URL si está; si no, lo que publique `tailscale serve` (publicándolo si hace falta); si no, el Mac en local."""
    if cfg.get("VOZ_URL"):
        return cfg["VOZ_URL"].rstrip("/") + "/"
    p = str(puerto(cfg))
    try:
        estado = tailscale_estado(cfg)
        if estado == "conectado":
            url = url_publicada(cfg)
            if not url and publicar_tailscale(cfg):
                url = url_publicada(cfg)
            if url:
                return url
            yo = ((tailscale_json("status", "--json") or {}).get("Self") or {}).get("DNSName", "").rstrip(".")
            nota("no pude publicar el buzón con tailscale serve (mira las líneas de arriba)")
            return f"https://{yo}/"
        if estado == "parado":
            nota("Tailscale está instalado pero no conectado: abre la app de Tailscale en el Mac e inicia sesión")
        else:
            nota("sin Tailscale en el Mac: instálalo (App Store) e inicia sesión; el enlace solo vale en este Mac")
    except Exception as e:
        nota(f"tailscale no responde: {error_http(e)}")
    return f"http://127.0.0.1:{p}/"


# ---------- avisos y canales ----------

def applescript_cadena(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def enviar_imessage(texto, audio, cfg):
    """Manda el texto (y el audio, si se pasa) al chat de Jose consigo mismo (IMESSAGE_DESTINO: número o correo de iMessage)."""
    destino = cfg.get("IMESSAGE_DESTINO")
    if not destino:
        raise RuntimeError("falta IMESSAGE_DESTINO en voz.env (tu número con +34 o tu correo de iMessage)")
    osascript = shutil.which("osascript")
    if not osascript:
        raise RuntimeError("sin osascript (no es macOS)")
    adjunto = f"\n    send POSIX file {applescript_cadena(str(audio))} to quien" if audio else ""
    guion = f'''
tell application "Messages"
    set cuenta to 1st account whose service type = iMessage
    set quien to participant {applescript_cadena(destino)} of cuenta
    send {applescript_cadena(texto)} to quien{adjunto}
end tell'''
    r = subprocess.run([osascript, "-e", guion], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                       timeout=60)
    if r.returncode != 0:
        raise RuntimeError("osascript: " + r.stderr.strip()[:200])
    nota(f"iMessage: {'texto y audio enviados' if audio else 'aviso enviado'} a {destino}")


def enviar_ntfy(titulo, texto, enlace, cfg):
    """Push por ntfy (app ntfy en el iPhone suscrita a NTFY_TOPIC). Opcional: el aviso que suena aunque iMessage calle."""
    tema = cfg.get("NTFY_TOPIC")
    if not tema:
        return
    servidor = tema if tema.startswith("http") else "https://ntfy.sh/" + tema
    cab = {"Title": titulo.encode("utf-8").decode("latin-1", "replace"), "Tags": "studio_microphone",
           "Content-Type": "text/plain; charset=utf-8"}
    if enlace:
        cab["Click"] = enlace
    http(servidor, texto.encode("utf-8"), cab, timeout=20)
    nota("ntfy: aviso enviado")


def enviar_icloud(texto, audio, cfg):
    """Copia el audio (y el texto, en .txt) a una carpeta de iCloud Drive; en el iPhone, Archivos → tocar."""
    base = cfg.get("ICLOUD_CARPETA") or "Claude voz"
    destino = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / base
    destino.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(audio, destino / audio.name)
    (destino / (audio.stem + ".txt")).write_text(texto, encoding="utf-8")
    nota(f"iCloud Drive: {audio.name} copiado a «{base}»")


def canal_web(texto, audio, cfg, ident):
    """Buzón web: apunta la ficha, asegura el servidor, calcula el enlace y avisa por iMessage (y ntfy si está)."""
    ficha = apuntar_en_buzon(texto, audio, cfg, ident)
    asegurar_servidor(cfg)
    enlace = url_buzon(cfg) + "#" + ident
    nota(f"buzón: {enlace}")
    aviso = f"🎙 {ficha['titulo']} · {ficha['proyecto']} ({ficha['segundos']} s)\n{enlace}"
    for nombre, f in (("iMessage", lambda: enviar_imessage(aviso, None, cfg) if cfg.get("IMESSAGE_DESTINO") else None),
                      ("ntfy", lambda: enviar_ntfy(f"{ficha['titulo']} · {ficha['proyecto']}", texto, enlace, cfg))):
        try:
            f()
        except Exception as e:
            nota(f"aviso por {nombre} falló: {error_http(e)}")
    return enlace


# ---------- Mac ----------

def reproducir(audio):
    for p in ("afplay", "say"):
        subprocess.run(["pkill", "-x", p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    afplay = shutil.which("afplay")
    if afplay:
        subprocess.Popen([afplay, str(audio)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---------- texto ----------

def ultimo_mensaje(ruta):
    if not ruta:
        return ""
    try:
        lineas = Path(os.path.expanduser(ruta)).read_text(encoding="utf-8").splitlines()
    except Exception:
        return ""
    for linea in reversed(lineas):
        try:
            e = json.loads(linea)
        except Exception:
            continue
        if e.get("type") != "assistant":
            continue
        c = (e.get("message") or {}).get("content")
        if isinstance(c, str):
            return c
        if isinstance(c, list):
            return "\n".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
    return ""


def limpiar(t):
    t = re.sub(r"`+", "", t)
    t = re.sub(r"^\s{0,3}#{1,6}\s*", "", t, flags=re.M)
    t = re.sub(r"^\s*[-*+]\s+", "", t, flags=re.M)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"[*_>|]", "", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip()


def extraer_bloque(msg):
    bloques = re.findall(r"^[ \t]*```voz[ \t]*\n(.*?)^[ \t]*```[ \t]*$", msg or "", re.M | re.S)
    if len(bloques) > 1:
        nota(f"aviso: {len(bloques)} bloques voz en una respuesta; uso el último")
    return limpiar(bloques[-1]) if bloques else ""


def nombre_fichero(texto):
    """Nombre legible: fecha y hora + las primeras palabras («2026-10-22_091830_decision-uno-de-seis»)."""
    llano = unicodedata.normalize("NFKD", texto.lower()[:40]).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", llano).strip("-")
    return time.strftime("%Y-%m-%d_%H%M%S") + ("_" + base[:30] if base else "")


# ---------- flujo ----------

def procesar(texto, cfg, forzar_mac=False):
    palabras = len(texto.split())
    nota(f"ficha de {palabras} palabras (~{round(palabras / 2.8)} s): {texto[:90].replace(chr(10), ' ')}…")
    if palabras > 70:
        nota("aviso: ficha larga (más de 20 s); el contrato pide 60 palabras como mucho")
    canal = (cfg.get("CANAL") or "ninguno").lower()
    ident = nombre_fichero(texto)
    audio = generar_audio(texto, cfg, ident, buzon(cfg) if canal == "web" else None)
    try:
        if canal == "web":
            canal_web(texto, audio, cfg, ident)
        elif canal == "imessage":
            enviar_imessage(texto, audio, cfg)
        elif canal == "icloud":
            enviar_icloud(texto, audio, cfg)
        else:
            nota("CANAL=ninguno: el audio se queda en el Mac")
    except Exception as e:
        nota(f"canal {canal} falló: {error_http(e)}")
    if forzar_mac or cfg.get("VOZ_MAC", "0") == "1":
        reproducir(audio)
        nota("reproducido en el Mac")
    return audio


def estado_url(cfg):
    p = puerto(cfg)
    vivo = asegurar_servidor(cfg)
    enlace = url_buzon(cfg)  # publica con tailscale serve si hace falta
    estado = tailscale_estado(cfg)
    if estado == "conectado":
        ts = "conectado · buzón " + ("publicado" if url_publicada(cfg) else "NO publicado (mira .claude/voz.log)")
    elif estado == "parado":
        ts = "instalado pero no conectado: abre la app de Tailscale e inicia sesión"
    else:
        ts = "no instalado (App Store, en el Mac y en el iPhone; misma cuenta)"
    print("Buzón:     ", buzon(cfg))
    print("Servidor:  ", f"127.0.0.1:{p} {'responde' if vivo else 'NO responde'}")
    print("Tailscale: ", ts)
    print("Enlace:    ", enlace)


def main(argv):
    cfg = cargar_env()
    if "--servir" in argv:
        servir(cfg)
        return
    if "--url" in argv:
        estado_url(cfg)
        return
    if "--voces" in argv:
        if not cfg.get("ELEVENLABS_API_KEY"):
            print("Falta ELEVENLABS_API_KEY en", fichero_env())
            return
        for v in voces_elevenlabs(cfg):
            etiquetas = ", ".join(f"{k}: {x}" for k, x in (v.get("labels") or {}).items())
            print(f"{'★ ' if es_espanola(v) else '  '}{v.get('name', '?'):<24} {v['voice_id']}  {etiquetas}")
        return
    if "--prueba" in argv:
        procesar(PRUEBA, cfg, forzar_mac="--mac" in argv)
        return
    if "--texto" in argv:
        procesar(argv[argv.index("--texto") + 1], cfg, forzar_mac="--mac" in argv)
        return
    if "--fichero" in argv:
        texto = limpiar(Path(argv[argv.index("--fichero") + 1]).read_text(encoding="utf-8"))
        if texto:
            procesar(texto, cfg, forzar_mac="--mac" in argv)
        return
    try:
        d = json.load(sys.stdin)  # modo hook
    except Exception:
        return
    yo = Path(sys.argv[0]).resolve() if sys.argv and sys.argv[0] else None
    copia = proy / ".claude" / "hooks" / "voz.py"
    if yo and str(yo).startswith(str(Path.home() / ".claude" / "hooks")) and copia.exists() and copia.resolve() != yo:
        return  # D3: la copia global se calla si el repo tiene la suya
    texto = extraer_bloque(d.get("last_assistant_message") or ultimo_mensaje(d.get("transcript_path")))
    if texto:
        procesar(texto, cfg)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        pass
    except Exception as e:
        nota(f"error: {error_http(e)}")
        try:
            sys.stderr.write(f"voz.py: {e}\n")
        except Exception:
            pass
    sys.exit(0)
