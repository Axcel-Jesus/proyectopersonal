#!/usr/bin/env python3
"""Servidor HTTP simple para desarrollo.
Sirve la carpeta `frontend/` en `http://127.0.0.1:8000`.
Mapea la raíz `/` a `/html/inicio.html` para ver las páginas existentes.
"""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import pathlib
import os
import re
import json
import mysql.connector
from mysql.connector import errorcode
import hashlib
import binascii

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / 'frontend'
PORT = 8000
HOST = 'localhost'


MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
MYSQL_PASS = os.environ.get('MYSQL_PASS', 'axcelcuno')
MYSQL_DB = os.environ.get('MYSQL_DB', 'tienda')


def get_root_conn(database=None):
    cfg = {
        'host': MYSQL_HOST,
        'port': MYSQL_PORT,
        'user': MYSQL_USER,
        'password': MYSQL_PASS,
        'autocommit': False,
    }
    if database:
        cfg['database'] = database
    return mysql.connector.connect(**cfg)


def init_db():
    # create database and tables if missing
    conn = get_root_conn()
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}` DEFAULT CHARACTER SET 'utf8mb4' COLLATE 'utf8mb4_general_ci';")
    cur.close(); conn.close()

    conn = get_root_conn(MYSQL_DB)
    cur = conn.cursor()
    create_clientes = (
        "CREATE TABLE IF NOT EXISTS clientes ("
        "id INT AUTO_INCREMENT PRIMARY KEY,"
        "nombre VARCHAR(50) NOT NULL,"
        "correo VARCHAR(255) NOT NULL UNIQUE,"
        "contrasena VARCHAR(255) NOT NULL,"
        "pais VARCHAR(50),"
        "edad INT,"
        "foto LONGBLOB,"
        "fecha DATETIME DEFAULT CURRENT_TIMESTAMP,"
        "status TINYINT DEFAULT 1"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
    )
    create_productos = (
        "CREATE TABLE IF NOT EXISTS productos ("
        "id INT AUTO_INCREMENT PRIMARY KEY,"
        "nombre VARCHAR(100) NOT NULL,"
        "descripcion TEXT,"
        "precio DECIMAL(10,2) NOT NULL DEFAULT 0.00,"
        "foto LONGBLOB,"
        "fecha DATETIME DEFAULT CURRENT_TIMESTAMP"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
    )
    cur.execute(create_clientes)
    cur.execute(create_productos)
    conn.commit()
    cur.close(); conn.close()


def hash_password(password: str) -> str:
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + b'$' + pwdhash).decode('ascii')


def verify_password(stored: str, provided: str) -> bool:
    """Verify a stored `salt$hash` password against a provided plaintext password."""
    try:
        salt_hex, hash_hex = stored.split('$', 1)
        salt = salt_hex.encode('ascii')
        new_hash = hashlib.pbkdf2_hmac('sha256', provided.encode('utf-8'), salt, 100000)
        new_hash_hex = binascii.hexlify(new_hash).decode('ascii')
        return new_hash_hex == hash_hex
    except Exception:
        return False


def import_products_from_html():
    # Parse frontend/html/inicio.html for product blocks and insert into DB if missing
    html_file = FRONTEND_DIR / 'html' / 'inicio.html'
    if not html_file.exists():
        return
    text = html_file.read_text(encoding='utf-8')
    # find product blocks: <article class="productos"> ... <header class="producto">NAME</header> ... <img src="../assets/xxx">
    pattern = re.compile(r'<article[^>]*class="productos"[^>]*>.*?<header[^>]*class="producto"[^>]*>(.*?)</header>.*?<img[^>]*src="([^"]+)"', re.S | re.I)
    matches = pattern.findall(text)
    if not matches:
        return
    conn = get_root_conn(MYSQL_DB)
    cur = conn.cursor()
    for name_raw, img_src in matches:
        nombre = re.sub(r'\s+', ' ', re.sub('<[^>]+>', '', name_raw)).strip()
        # check existence
        cur.execute('SELECT id FROM productos WHERE nombre = %s', (nombre,))
        if cur.fetchone():
            continue
        # try to load image bytes
        img_path = img_src.replace('..', '')
        img_file = (FRONTEND_DIR / img_path.lstrip('/')).resolve()
        foto_bytes = None
        try:
            if img_file.exists():
                foto_bytes = img_file.read_bytes()
        except Exception:
            foto_bytes = None
        try:
            cur.execute('INSERT INTO productos (nombre, descripcion, precio, foto) VALUES (%s, %s, %s, %s)',
                        (nombre, '', 0.00, foto_bytes))
        except Exception:
            # ignore individual insert errors
            pass
    conn.commit()
    cur.close(); conn.close()

class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Serve files rooted at FRONTEND_DIR
        # Keep default behaviour but rooted to FRONTEND_DIR
        # Reuse SimpleHTTPRequestHandler's logic by changing cwd in run.
        return super().translate_path(path)

    def do_GET(self):
        # Normalize path (strip query)
        path = self.path.split('?', 1)[0]

        # If root requested, redirect browser to /inicio so URL shows the page name
        if path == '/' or path == '':
            self.send_response(302)
            self.send_header('Location', '/inicio')
            self.end_headers()
            return

        # If someone requests a .html file (e.g. /inicio.html or /html/inicio.html),
        # redirect to the clean URL without extension (/inicio)
        if path.endswith('.html'):
            # remove leading /html/ if present
            p = path
            if p.startswith('/html/'):
                p = p[len('/html/'):]
            # strip extension and ensure leading slash
            name = '/' + p.split('/')[-1].rsplit('.', 1)[0]
            self.send_response(301)
            self.send_header('Location', name)
            self.end_headers()
            return

        # If request is a single segment without extension, map to html/<name>.html
        # e.g. /inicio -> /html/inicio.html, /contacto -> /html/contacto.html
        seg = path.lstrip('/').rstrip('/')
        if seg and '/' not in seg and '.' not in seg:
            # map to html/<seg>.html but keep URL unchanged in browser
            self.path = '/html/' + seg + '.html'
            return super().do_GET()

        return super().do_GET()

    def read_json_body(self):
        length = int(self.headers.get('Content-Length', 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode('utf-8'))

    def do_POST(self):
        path = self.path.split('?', 1)[0]
        if path == '/api/clientes':
            try:
                data = self.read_json_body()
                nombre = data.get('nombre')
                correo = data.get('correo')
                contrasena = data.get('contrasena')
                pais = data.get('pais')
                edad = data.get('edad')
                if not nombre or not correo or not contrasena:
                    self.send_response(400); self.end_headers(); self.wfile.write(b'Missing required fields'); return
                hashed = hash_password(contrasena)
                conn = get_root_conn(MYSQL_DB)
                cur = conn.cursor()
                try:
                    cur.execute('INSERT INTO clientes (nombre, correo, contrasena, pais, edad) VALUES (%s, %s, %s, %s, %s)',
                                (nombre, correo, hashed, pais, edad))
                    conn.commit()
                    self.send_response(201)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'id': cur.lastrowid}).encode('utf-8'))
                except mysql.connector.Error as err:
                    if err.errno == errorcode.ER_DUP_ENTRY:
                        self.send_response(400); self.end_headers(); self.wfile.write(b'Correo ya registrado');
                    else:
                        raise
                finally:
                    cur.close(); conn.close()
            except Exception as e:
                self.send_response(500); self.end_headers(); self.wfile.write(str(e).encode('utf-8'))
            return

        if path == '/api/productos':
            try:
                data = self.read_json_body()
                nombre = data.get('nombre')
                descripcion = data.get('descripcion', '')
                precio = data.get('precio', 0.0)
                if not nombre:
                    self.send_response(400); self.end_headers(); self.wfile.write(b'nombre requerido'); return
                conn = get_root_conn(MYSQL_DB)
                cur = conn.cursor()
                cur.execute('INSERT INTO productos (nombre, descripcion, precio) VALUES (%s, %s, %s)', (nombre, descripcion, precio))
                conn.commit()
                self.send_response(201)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'id': cur.lastrowid}).encode('utf-8'))
                cur.close(); conn.close()
            except Exception as e:
                self.send_response(500); self.end_headers(); self.wfile.write(str(e).encode('utf-8'))
            return

        if path == '/api/login':
            try:
                data = self.read_json_body()
                correo = data.get('correo')
                contrasena = data.get('contrasena')
                if not correo or not contrasena:
                    self.send_response(400); self.end_headers(); self.wfile.write(b'correo y contrasena requeridos'); return
                conn = get_root_conn(MYSQL_DB)
                cur = conn.cursor()
                cur.execute('SELECT nombre, contrasena FROM clientes WHERE correo = %s', (correo,))
                row = cur.fetchone()
                if not row:
                    # account not found
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'Cuenta no existe')
                    cur.close(); conn.close()
                    return
                nombre_db, stored_hash = row[0], row[1]
                if not verify_password(stored_hash, contrasena):
                    self.send_response(401); self.end_headers(); self.wfile.write('Contraseña incorrecta'); cur.close(); conn.close(); return
                # success
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'nombre': nombre_db}).encode('utf-8'))
                cur.close(); conn.close()
            except Exception as e:
                self.send_response(500); self.end_headers(); self.wfile.write(str(e).encode('utf-8'))
            return
        # fallback to default behavior
        self.send_response(404); self.end_headers()

def run():
    if not FRONTEND_DIR.exists():
        print(f"Carpeta frontend no encontrada en: {FRONTEND_DIR}")
        return

    # Initialize DB (MySQL) — will create database and tables if missing
    try:
        init_db()
        import_products_from_html()
    except Exception as e:
        print('Advertencia: fallo al inicializar BD o importar productos:', e)

    # Change working directory to FRONTEND_DIR so static references work
    os.chdir(str(FRONTEND_DIR))
    addr = (HOST, PORT)
    server = ThreadingHTTPServer(addr, Handler)
    print(f"Sirviendo {FRONTEND_DIR} en http://{addr[0]}:{addr[1]}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nDeteniendo servidor...')
        server.server_close()

if __name__ == '__main__':
    run()
