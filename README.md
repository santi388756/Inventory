# Inventory

Aplicación local de gestión de productos, servicios, ventas, clientes y registros.

## Datos

La base principal es SQLite y se guarda localmente. Inventory no necesita una nube para funcionar.

### Importar / exportar

Formatos compatibles:

- `.inventory` — respaldo completo de Inventory.
- `.xlsx` — Excel. Para importar se usa la hoja `productos` si existe; si no, la primera hoja.
- `.csv` — tabla de productos.
- `.txt` — tabla separada por tabulaciones.
- `.db`, `.sqlite`, `.sqlite3` — lectura de una tabla `productos` compatible.

La exportación a `.inventory` y `.xlsx` conserva todas las tablas. `.csv` y `.txt` exportan la tabla de productos.

Antes de reemplazar la base mediante una importación se crea automáticamente un backup `.inventory`.

## Productos y servicios

Cada registro puede ser `producto` o `servicio`.

- Los productos tienen stock y stock mínimo.
- Los servicios no utilizan stock.
- Ambos pueden venderse desde el mismo flujo de pedidos.

## Build Windows

`build.bat` comprueba Python y, si no existe, descarga e instala Python 3.13.15 para el usuario actual desde python.org. Luego instala únicamente las dependencias faltantes y compila `Inventory.exe` directamente en `%USERPROFILE%\\Downloads`.

> El EXE final no necesita Python ni las librerías para ejecutarse. Python se necesita en la computadora de desarrollo para compilarlo.

## Archivos de prueba

La carpeta `pruebas` incluida en el paquete contiene un Excel y un TXT listos para probar la importación desde **Datos → Importar datos**.
