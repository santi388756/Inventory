import sqlite3
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from config import DB_FILENAME, DATA_DIR_NAME

ESQUEMA = """
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    telefono TEXT,
    email TEXT,
    direccion TEXT,
    fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    categoria TEXT,
    tipo TEXT NOT NULL DEFAULT 'producto',
    codigo_barra TEXT,
    precio REAL NOT NULL DEFAULT 0,
    costo REAL NOT NULL DEFAULT 0,
    stock_actual INTEGER NOT NULL DEFAULT 0,
    stock_minimo INTEGER NOT NULL DEFAULT 5,
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER,
    fecha TEXT DEFAULT CURRENT_TIMESTAMP,
    estado TEXT DEFAULT 'completado',
    total REAL NOT NULL DEFAULT 0,
    descripcion TEXT,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS detalle_pedido (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_unitario REAL NOT NULL,
    subtotal REAL NOT NULL,
    FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

CREATE TABLE IF NOT EXISTS pagos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER NOT NULL,
    monto REAL NOT NULL,
    fecha TEXT DEFAULT CURRENT_TIMESTAMP,
    metodo TEXT DEFAULT 'efectivo',
    FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_detalle_producto ON detalle_pedido(producto_id);
CREATE INDEX IF NOT EXISTS idx_pedido_fecha ON pedidos(fecha);
"""


class DatabaseError(Exception):
    pass


def ruta_base_datos():
    carpeta = Path.home() / DATA_DIR_NAME
    carpeta.mkdir(parents=True, exist_ok=True)
    return str(carpeta / DB_FILENAME)


class Database:
    def __init__(self):
        self.ruta = ruta_base_datos()
        self.conn = None
        self._inicializar_esquema()

    def connect(self):
        try:
            if self.conn is None:
                self.conn = sqlite3.connect(self.ruta)
                self.conn.row_factory = sqlite3.Row
                self.conn.execute("PRAGMA foreign_keys = ON")
            return self.conn
        except sqlite3.Error as e:
            raise DatabaseError(f"No se pudo abrir la base de datos: {e}")

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def _inicializar_esquema(self):
        conn = self.connect()
        conn.executescript(ESQUEMA)
        columnas = {row[1] for row in conn.execute("PRAGMA table_info(productos)").fetchall()}
        if "tipo" not in columnas:
            conn.execute("ALTER TABLE productos ADD COLUMN tipo TEXT NOT NULL DEFAULT 'producto'")
        if "codigo_barra" not in columnas:
            conn.execute("ALTER TABLE productos ADD COLUMN codigo_barra TEXT")
        columnas_pedidos = {row[1] for row in conn.execute("PRAGMA table_info(pedidos)").fetchall()}
        if "descripcion" not in columnas_pedidos:
            conn.execute("ALTER TABLE pedidos ADD COLUMN descripcion TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_productos_codigo_barra ON productos(codigo_barra)")
        conn.commit()

    def get_clientes(self):
        cur = self.connect().execute("SELECT * FROM clientes ORDER BY nombre")
        return [dict(row) for row in cur.fetchall()]

    def add_cliente(self, nombre, telefono, email, direccion):
        self.connect().execute(
            "INSERT INTO clientes (nombre, telefono, email, direccion) VALUES (?,?,?,?)",
            (nombre, telefono, email, direccion),
        )
        self.connect().commit()

    def update_cliente(self, cliente_id, nombre, telefono, email, direccion):
        self.connect().execute(
            "UPDATE clientes SET nombre=?, telefono=?, email=?, direccion=? WHERE id=?",
            (nombre, telefono, email, direccion, cliente_id),
        )
        self.connect().commit()

    def delete_cliente(self, cliente_id):
        self.connect().execute("DELETE FROM clientes WHERE id=?", (cliente_id,))
        self.connect().commit()

    def get_productos(self):
        cur = self.connect().execute("SELECT * FROM productos ORDER BY nombre")
        return [dict(row) for row in cur.fetchall()]

    def add_producto(self, nombre, categoria, precio, costo, stock_actual, stock_minimo, tipo="producto", codigo_barra=""):
        tipo = "servicio" if str(tipo).strip().lower() in {"servicio", "service"} else "producto"
        if tipo == "servicio":
            stock_actual, stock_minimo = 0, 0
            codigo_barra = None
        self.connect().execute(
            """INSERT INTO productos (nombre, categoria, tipo, codigo_barra, precio, costo, stock_actual, stock_minimo)
               VALUES (?,?,?,?,?,?,?,?)""",
            (nombre, categoria, tipo, codigo_barra or None, precio, costo, stock_actual, stock_minimo),
        )
        self.connect().commit()

    def update_producto(self, producto_id, nombre, categoria, precio, costo, stock_actual, stock_minimo, tipo="producto", codigo_barra=""):
        tipo = "servicio" if str(tipo).strip().lower() in {"servicio", "service"} else "producto"
        if tipo == "servicio":
            stock_actual, stock_minimo = 0, 0
            codigo_barra = None
        self.connect().execute(
            """UPDATE productos SET nombre=?, categoria=?, tipo=?, codigo_barra=?, precio=?, costo=?,
               stock_actual=?, stock_minimo=? WHERE id=?""",
            (nombre, categoria, tipo, codigo_barra or None, precio, costo, stock_actual, stock_minimo, producto_id),
        )
        self.connect().commit()

    def delete_producto(self, producto_id):
        self.connect().execute("DELETE FROM productos WHERE id=?", (producto_id,))
        self.connect().commit()

    def crear_pedido(self, cliente_id, items):
        conn = self.connect()
        try:
            # Validación defensiva: el stock se vuelve a comprobar al confirmar.
            for it in items:
                cur = conn.execute("SELECT stock_actual, tipo FROM productos WHERE id=?", (it["producto_id"],))
                row = cur.fetchone()
                if row is None:
                    raise DatabaseError("Uno de los elementos del pedido ya no existe.")
                if row["tipo"] != "servicio" and int(row["stock_actual"]) < int(it["cantidad"]):
                    raise DatabaseError("El stock cambió mientras preparabas el pedido. Revisá el carrito.")

            total = sum(it["cantidad"] * float(it["precio_unitario"]) for it in items)
            cur = conn.execute(
                "INSERT INTO pedidos (cliente_id, total) VALUES (?, ?)",
                (cliente_id, total),
            )
            pedido_id = cur.lastrowid

            for it in items:
                subtotal = it["cantidad"] * float(it["precio_unitario"])
                conn.execute(
                    """INSERT INTO detalle_pedido
                       (pedido_id, producto_id, cantidad, precio_unitario, subtotal)
                       VALUES (?,?,?,?,?)""",
                    (pedido_id, it["producto_id"], it["cantidad"], it["precio_unitario"], subtotal),
                )
                conn.execute(
                    "UPDATE productos SET stock_actual = CASE WHEN tipo = 'servicio' THEN 0 ELSE stock_actual - ? END WHERE id=?",
                    (it["cantidad"], it["producto_id"]),
                )

            conn.commit()
            return pedido_id
        except DatabaseError:
            conn.rollback()
            raise
        except sqlite3.Error as e:
            conn.rollback()
            raise DatabaseError(f"No se pudo registrar el pedido: {e}")

    def registrar_pago(self, pedido_id, monto, metodo):
        self.connect().execute(
            "INSERT INTO pagos (pedido_id, monto, metodo) VALUES (?,?,?)",
            (pedido_id, monto, metodo),
        )
        self.connect().commit()

    def registrar_venta_rapida(self, total, metodo="efectivo", descripcion=""):
        """Registra una venta rápida con monto y una descripción opcional."""
        try:
            conn = self.connect()
            cur = conn.execute(
                "INSERT INTO pedidos (cliente_id, total, descripcion) VALUES (NULL, ?, ?)",
                (float(total), descripcion.strip() or None),
            )
            pedido_id = cur.lastrowid
            conn.execute(
                "INSERT INTO pagos (pedido_id, monto, metodo) VALUES (?,?,?)",
                (pedido_id, float(total), metodo),
            )
            conn.commit()
            return pedido_id
        except sqlite3.Error as e:
            self.connect().rollback()
            raise DatabaseError(f"No se pudo registrar la venta rápida: {e}")

    def get_resumen_ventas(self):
        cur = self.connect().execute(
            """SELECT COUNT(*) AS cantidad, COALESCE(SUM(total), 0) AS total
               FROM pedidos WHERE date(fecha, 'localtime') = date('now', 'localtime')"""
        )
        return dict(cur.fetchone())

    def delete_pedido(self, pedido_id):
        """Elimina una venta y devuelve al stock los productos que contenía."""
        conn = self.connect()
        try:
            detalles = conn.execute(
                "SELECT producto_id, cantidad FROM detalle_pedido WHERE pedido_id=?",
                (pedido_id,),
            ).fetchall()
            for detalle in detalles:
                conn.execute(
                    "UPDATE productos SET stock_actual = stock_actual + ? WHERE id=?",
                    (int(detalle["cantidad"]), int(detalle["producto_id"])),
                )
            conn.execute("DELETE FROM pagos WHERE pedido_id=?", (pedido_id,))
            conn.execute("DELETE FROM detalle_pedido WHERE pedido_id=?", (pedido_id,))
            cur = conn.execute("DELETE FROM pedidos WHERE id=?", (pedido_id,))
            if cur.rowcount == 0:
                raise DatabaseError("La venta seleccionada ya no existe.")
            conn.commit()
        except DatabaseError:
            conn.rollback()
            raise
        except sqlite3.Error as e:
            conn.rollback()
            raise DatabaseError(f"No se pudo eliminar la venta: {e}")

    def _exportar_payload(self):
        tablas = {}
        for tabla in ("clientes", "productos", "pedidos", "detalle_pedido", "pagos"):
            rows = self.connect().execute(f"SELECT * FROM {tabla} ORDER BY id").fetchall()
            tablas[tabla] = [dict(row) for row in rows]
        return {
            "format": "inventory",
            "version": 2,
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "tables": tablas,
        }

    def exportar_datos(self, ruta):
        """Exporta la base en .inventory, .xlsx, .csv o .txt."""
        extension = Path(ruta).suffix.lower()
        try:
            payload = self._exportar_payload()
            if extension in (".inventory", ".json"):
                Path(ruta).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            elif extension == ".xlsx":
                with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
                    for tabla, rows in payload["tables"].items():
                        pd.DataFrame(rows).to_excel(writer, sheet_name=tabla[:31], index=False)
            elif extension in (".txt", ".csv"):
                rows = payload["tables"]["productos"]
                pd.DataFrame(rows).to_csv(ruta, sep="\t" if extension == ".txt" else ",", index=False, encoding="utf-8-sig")
            else:
                raise DatabaseError("Formato de exportación no compatible.")
        except (OSError, ValueError, ImportError) as e:
            raise DatabaseError(f"No se pudo exportar la información: {e}")

    @staticmethod
    def _normalizar_columna(valor):
        import unicodedata
        texto = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode().strip().lower()
        return "".join(ch if ch.isalnum() else "_" for ch in texto).strip("_")

    def _fila_producto(self, row):
        normal = {self._normalizar_columna(k): v for k, v in row.items()}
        def val(*keys, default=""):
            for key in keys:
                if key in normal and pd.notna(normal[key]):
                    return normal[key]
            return default
        nombre = str(val("nombre", "producto", "descripcion", default="")).strip()
        if not nombre:
            return None
        tipo = str(val("tipo", "tipo_producto", default="producto")).strip().lower()
        tipo = "servicio" if tipo in {"servicio", "service"} else "producto"
        def num(*keys, default=0.0):
            raw = val(*keys, default=default)
            try:
                return float(str(raw).replace("$", "").replace(" ", "").replace(".", "").replace(",", "."))
            except (ValueError, TypeError):
                return default
        def integer(*keys, default=0):
            raw = val(*keys, default=default)
            try:
                return int(float(str(raw).replace(",", ".")))
            except (ValueError, TypeError):
                return default
        stock = 0 if tipo == "servicio" else integer("stock_actual", "stock", "existencia")
        minimo = 0 if tipo == "servicio" else integer("stock_minimo", "minimo", "stock_min")
        codigo_raw = val("codigo_barra", "codigo_de_barras", "codigo", "ean", "barcode", default="")
        if isinstance(codigo_raw, float) and codigo_raw.is_integer():
            codigo_raw = int(codigo_raw)
        return {
            "nombre": nombre,
            "categoria": str(val("categoria", "rubro", default="")).strip(),
            "tipo": tipo,
            "codigo_barra": str(codigo_raw).strip(),
            "precio": num("precio", "precio_venta", "venta", "valor"),
            "costo": num("costo", "coste"),
            "stock_actual": stock,
            "stock_minimo": minimo,
        }

    def _importar_tabla_productos(self, rows):
        imported = 0
        for row in rows:
            data = self._fila_producto(row)
            if not data:
                continue
            self.add_producto(**data)
            imported += 1
        return imported

    def _importar_dataframe(self, frame):
        if frame is None or frame.empty:
            return {"productos": 0}
        frame = frame.dropna(how="all").fillna("")
        return {"productos": self._importar_tabla_productos(frame.to_dict(orient="records"))}

    def _importar_sqlite(self, ruta):
        source = sqlite3.connect(ruta)
        source.row_factory = sqlite3.Row
        try:
            tablas = {r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "productos" not in tablas:
                raise DatabaseError("La base SQLite no contiene una tabla 'productos'.")
            rows = [dict(r) for r in source.execute("SELECT * FROM productos")]
            return self._importar_tabla_productos(rows)
        finally:
            source.close()

    def importar_archivo(self, ruta):
        """Importa .inventory, .xlsx, .csv, .txt, .db, .sqlite o .sqlite3."""
        extension = Path(ruta).suffix.lower()
        try:
            if extension in (".inventory", ".json"):
                payload = json.loads(Path(ruta).read_text(encoding="utf-8"))
                return self._importar_payload(payload)
            if extension == ".xlsx":
                hojas = pd.read_excel(ruta, sheet_name=None)
                resumen = {"productos": 0, "clientes": 0}
                productos = next((v for k, v in hojas.items() if self._normalizar_columna(k) in {"productos", "producto", "services", "servicios"}), None)
                if productos is None and hojas:
                    productos = next(iter(hojas.values()))
                if productos is not None:
                    resumen["productos"] = self._importar_dataframe(productos).get("productos", 0)
                clientes = next((v for k, v in hojas.items() if self._normalizar_columna(k) in {"clientes", "cliente", "customers", "customer"}), None)
                if clientes is not None and not clientes.empty:
                    for row in clientes.fillna("").to_dict(orient="records"):
                        normal = {self._normalizar_columna(k): v for k, v in row.items()}
                        nombre = str(normal.get("nombre", normal.get("cliente", ""))).strip()
                        if nombre:
                            self.add_cliente(nombre, str(normal.get("telefono", "")).strip(), str(normal.get("email", "")).strip(), str(normal.get("direccion", "")).strip())
                            resumen["clientes"] += 1
                return resumen
            if extension in (".txt", ".csv"):
                sep = "\t" if extension == ".txt" else ","
                frame = pd.read_csv(ruta, sep=sep, encoding="utf-8-sig")
                return self._importar_dataframe(frame)
            if extension in (".db", ".sqlite", ".sqlite3"):
                return {"productos": self._importar_sqlite(ruta)}
            raise DatabaseError("Formato no compatible. Usá .inventory, .xlsx, .csv, .txt, .db, .sqlite o .sqlite3.")
        except DatabaseError:
            raise
        except (OSError, ValueError, pd.errors.ParserError, ImportError) as e:
            raise DatabaseError(f"No se pudo importar el archivo: {e}")

    def _importar_payload(self, payload):
        if payload.get("format") != "inventory" or payload.get("version") not in (1, 2):
            raise DatabaseError("El archivo no es un respaldo válido de Inventory.")
        tables = payload.get("tables")
        required = ("clientes", "productos", "pedidos", "detalle_pedido", "pagos")
        if not isinstance(tables, dict) or any(not isinstance(tables.get(t), list) for t in required):
            raise DatabaseError("El archivo está incompleto o tiene un formato incorrecto.")
        conn = self.connect()
        try:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("BEGIN")
            for tabla in ("pagos", "detalle_pedido", "pedidos", "productos", "clientes"):
                conn.execute(f"DELETE FROM {tabla}")
            columnas = {
                "clientes": ("id", "nombre", "telefono", "email", "direccion", "fecha_registro"),
                "productos": ("id", "nombre", "categoria", "tipo", "codigo_barra", "precio", "costo", "stock_actual", "stock_minimo", "fecha_creacion"),
                "pedidos": ("id", "cliente_id", "fecha", "estado", "total"),
                "detalle_pedido": ("id", "pedido_id", "producto_id", "cantidad", "precio_unitario", "subtotal"),
                "pagos": ("id", "pedido_id", "monto", "fecha", "metodo"),
            }
            for tabla in required:
                cols = columnas[tabla]
                placeholders = ",".join("?" for _ in cols)
                sql = f"INSERT INTO {tabla} ({','.join(cols)}) VALUES ({placeholders})"
                for row in tables[tabla]:
                    if not isinstance(row, dict):
                        raise DatabaseError(f"Registro inválido en {tabla}.")
                    values = []
                    for c in cols:
                        if c == "tipo":
                            values.append(row.get(c, "producto"))
                        elif c == "codigo_barra":
                            values.append(row.get(c))
                        else:
                            values.append(row.get(c))
                    conn.execute(sql, tuple(values))
            conn.execute("PRAGMA foreign_keys = ON")
            conn.commit()
            return {"productos": len(tables["productos"]), "clientes": len(tables["clientes"]), "ventas": len(tables["pedidos"])}
        except DatabaseError:
            conn.rollback(); conn.execute("PRAGMA foreign_keys = ON"); raise
        except sqlite3.Error as e:
            conn.rollback(); conn.execute("PRAGMA foreign_keys = ON")
            raise DatabaseError(f"No se pudo importar la información: {e}")

    def importar_datos(self, ruta):
        return self.importar_archivo(ruta)

    def borrar_todos_los_datos(self):
        """Borra todos los registros de la aplicación, conservando el esquema."""
        conn = self.connect()
        try:
            conn.execute("DELETE FROM pagos")
            conn.execute("DELETE FROM detalle_pedido")
            conn.execute("DELETE FROM pedidos")
            conn.execute("DELETE FROM productos")
            conn.execute("DELETE FROM clientes")
            conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('pagos','detalle_pedido','pedidos','productos','clientes')")
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise DatabaseError(f"No se pudieron borrar los datos: {e}")

    def get_pedidos(self):
        cur = self.connect().execute(
            """SELECT pe.id, COALESCE(c.nombre, 'Sin cliente') AS cliente,
                      pe.fecha, pe.estado, pe.total, COALESCE(pe.descripcion, '') AS descripcion
               FROM pedidos pe
               LEFT JOIN clientes c ON pe.cliente_id = c.id
               ORDER BY pe.fecha DESC"""
        )
        return [dict(row) for row in cur.fetchall()]

    def get_ventas_historicas(self):
        cur = self.connect().execute(
            """SELECT dp.producto_id, pe.fecha, dp.cantidad
               FROM detalle_pedido dp
               JOIN pedidos pe ON dp.pedido_id = pe.id"""
        )
        return cur.fetchall()


    def get_ventas_diarias(self, dias=14):
        """Ventas por día, separando ventas rápidas de ventas con productos/servicios."""
        try:
            rows = self.connect().execute(
                """SELECT date(pe.fecha, 'localtime') AS dia,
                          SUM(pe.total) AS total,
                          SUM(CASE WHEN NOT EXISTS (SELECT 1 FROM detalle_pedido dp WHERE dp.pedido_id = pe.id) THEN pe.total ELSE 0 END) AS rapidas,
                          SUM(CASE WHEN EXISTS (SELECT 1 FROM detalle_pedido dp WHERE dp.pedido_id = pe.id) THEN pe.total ELSE 0 END) AS catalogo,
                          COUNT(*) AS ventas
                   FROM pedidos pe
                   WHERE date(pe.fecha, 'localtime') >= date('now', 'localtime', ?)
                   GROUP BY date(pe.fecha, 'localtime')
                   ORDER BY dia ASC""",
                (f"-{int(dias)-1} days",),
            ).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            raise DatabaseError(f"No se pudieron obtener las ventas diarias: {e}")

    def get_estadisticas(self, dias=30):
        """Calcula estadísticas comerciales reales para el período seleccionado."""
        dias = max(1, int(dias))
        conn = self.connect()
        try:
            end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)
            start = end.replace(hour=0, minute=0, second=0, microsecond=0)
            start_text = (start - timedelta(days=dias-1)).strftime('%Y-%m-%d %H:%M:%S')
            previous_start = (start - timedelta(days=dias)).strftime('%Y-%m-%d %H:%M:%S')
            previous_end = (start - timedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S')

            k = conn.execute("""
                SELECT COUNT(*) ventas, COALESCE(SUM(total),0) facturacion,
                       COALESCE(AVG(total),0) ticket_promedio,
                       COUNT(DISTINCT CASE WHEN cliente_id IS NOT NULL THEN cliente_id END) clientes_activos,
                       SUM(CASE WHEN NOT EXISTS (SELECT 1 FROM detalle_pedido d WHERE d.pedido_id=p.id) THEN 1 ELSE 0 END) ventas_rapidas,
                       COALESCE(SUM(CASE WHEN NOT EXISTS (SELECT 1 FROM detalle_pedido d WHERE d.pedido_id=p.id) THEN p.total ELSE 0 END),0) facturacion_rapida
                FROM pedidos p WHERE datetime(p.fecha) >= datetime(?)
            """, (start_text,)).fetchone()
            prev = conn.execute("""SELECT COALESCE(SUM(total),0) total FROM pedidos
                WHERE datetime(fecha) >= datetime(?) AND datetime(fecha) <= datetime(?)""", (previous_start, previous_end)).fetchone()[0] or 0

            units = conn.execute("""SELECT COALESCE(SUM(d.cantidad),0) FROM detalle_pedido d
                JOIN pedidos p ON p.id=d.pedido_id WHERE datetime(p.fecha) >= datetime(?)""", (start_text,)).fetchone()[0] or 0
            services = conn.execute("""SELECT COUNT(DISTINCT p.id), COALESCE(SUM(d.subtotal),0)
                FROM detalle_pedido d JOIN pedidos p ON p.id=d.pedido_id
                JOIN productos pr ON pr.id=d.producto_id
                WHERE pr.tipo='servicio' AND datetime(p.fecha) >= datetime(?)""", (start_text,)).fetchone()
            stock = conn.execute("""SELECT COUNT(*), COALESCE(SUM(stock_actual * costo),0),
                COALESCE(SUM(stock_actual * precio),0) FROM productos WHERE tipo!='servicio'""").fetchone()
            low = conn.execute("""SELECT id,nombre,stock_actual,stock_minimo FROM productos
                WHERE tipo!='servicio' AND stock_actual <= stock_minimo ORDER BY (stock_minimo-stock_actual) DESC,nombre LIMIT 10""").fetchall()
            top = conn.execute("""SELECT pr.nombre, SUM(d.cantidad) unidades, COALESCE(SUM(d.subtotal),0) facturacion
                FROM detalle_pedido d JOIN pedidos p ON p.id=d.pedido_id JOIN productos pr ON pr.id=d.producto_id
                WHERE datetime(p.fecha) >= datetime(?) GROUP BY pr.id,pr.nombre ORDER BY unidades DESC, facturacion DESC LIMIT 8""", (start_text,)).fetchall()
            cats = conn.execute("""SELECT COALESCE(NULLIF(pr.categoria,''),'Sin categoría') categoria,
                SUM(d.cantidad) unidades, COALESCE(SUM(d.subtotal),0) facturacion
                FROM detalle_pedido d JOIN pedidos p ON p.id=d.pedido_id JOIN productos pr ON pr.id=d.producto_id
                WHERE datetime(p.fecha) >= datetime(?) GROUP BY categoria ORDER BY facturacion DESC LIMIT 8""", (start_text,)).fetchall()
            payments = conn.execute("""SELECT LOWER(COALESCE(pg.metodo,'sin método')) metodo, COUNT(*) operaciones, COALESCE(SUM(pg.monto),0) monto
                FROM pagos pg JOIN pedidos p ON p.id=pg.pedido_id WHERE datetime(pg.fecha) >= datetime(?)
                GROUP BY metodo ORDER BY monto DESC""", (start_text,)).fetchall()
            daily = conn.execute("""SELECT date(p.fecha,'localtime') dia, COUNT(*) ventas, COALESCE(SUM(p.total),0) total,
                COALESCE(SUM(CASE WHEN NOT EXISTS (SELECT 1 FROM detalle_pedido d WHERE d.pedido_id=p.id) THEN p.total ELSE 0 END),0) rapidas
                FROM pedidos p WHERE date(p.fecha,'localtime') >= date('now','localtime',?)
                GROUP BY date(p.fecha,'localtime') ORDER BY dia""", (f'-{dias-1} days',)).fetchall()
            margin = conn.execute("""SELECT COALESCE(SUM(d.subtotal - (d.cantidad * pr.costo)),0)
                FROM detalle_pedido d JOIN pedidos p ON p.id=d.pedido_id JOIN productos pr ON pr.id=d.producto_id
                WHERE datetime(p.fecha) >= datetime(?) AND pr.tipo!='servicio'""", (start_text,)).fetchone()[0] or 0
            return {
                'kpis': {**dict(k), 'unidades': int(units), 'servicios': int(services[0] or 0), 'facturacion_servicios': float(services[1] or 0),
                         'stock_productos': int(stock[0] or 0), 'valor_stock_costo': float(stock[1] or 0), 'valor_stock_venta': float(stock[2] or 0),
                         'margen_estimado': float(margin), 'periodo_anterior': float(prev)},
                'top_productos':[dict(x) for x in top], 'categorias':[dict(x) for x in cats],
                'pagos':[dict(x) for x in payments], 'diarias':[dict(x) for x in daily], 'stock_bajo':[dict(x) for x in low]
            }
        except sqlite3.Error as e:
            raise DatabaseError(f"No se pudieron calcular las estadísticas: {e}")

    def get_ventas_por_tipo(self):
        try:
            row = self.connect().execute(
                """SELECT
                    COALESCE(SUM(CASE WHEN NOT EXISTS (SELECT 1 FROM detalle_pedido dp WHERE dp.pedido_id=pe.id) THEN pe.total ELSE 0 END),0) AS rapidas,
                    COALESCE(SUM(CASE WHEN EXISTS (SELECT 1 FROM detalle_pedido dp WHERE dp.pedido_id=pe.id) THEN pe.total ELSE 0 END),0) AS catalogo,
                    SUM(CASE WHEN NOT EXISTS (SELECT 1 FROM detalle_pedido dp WHERE dp.pedido_id=pe.id) THEN 1 ELSE 0 END) AS cantidad_rapidas,
                    SUM(CASE WHEN EXISTS (SELECT 1 FROM detalle_pedido dp WHERE dp.pedido_id=pe.id) THEN 1 ELSE 0 END) AS cantidad_catalogo
                   FROM pedidos pe"""
            ).fetchone()
            return dict(row)
        except sqlite3.Error as e:
            raise DatabaseError(f"No se pudo calcular el resumen por tipo: {e}")
