# Sistema de tickets — Consultorio Las Marianas

Aplicación local para Windows, instalada en un solo dispositivo y utilizada por un único operador. React presenta la interfaz y Flask/Waitress atiende exclusivamente en `127.0.0.1:5000`. No necesita cuentas de usuario ni un servidor de base de datos separado.

## Requisitos e instalación

Entorno verificado: Python 3.14 y Node.js 24. Windows debe tener instalada la impresora térmica. Node se requiere para desarrollar/compilar, no para utilizar una instalación ya compilada.

Desde PowerShell en la raíz del proyecto:

```powershell
py -3.14 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
cd frontend
npm.cmd ci
npm.cmd run typecheck
npm.cmd test -- --watchAll=false --runInBand
npm.cmd run build:local
cd ..
```

`build:local` genera directamente `backend/build`, que es la interfaz servida por Flask. `npm run build` también permite verificar la compilación en `frontend/build`. Las carpetas compiladas no se versionan; el paquete que se entregue al cliente debe incluir `backend/build`.

Ejecute `Sistema Consultorio Las Marianas.bat`. Los errores permanecen visibles; use Ctrl+C para apagar. El lanzador verifica el entorno y la interfaz. El servidor comprueba el puerto antes de migrar datos y rechaza una segunda instancia si está ocupado.

## Configuración

Copie `.env.example` a `.env` y ajuste los valores necesarios. No suba `.env` ni los datos del cliente a Git.

- `CONSULTORIO_DATA_DIR`: carpeta local para base de datos, catálogos, exportaciones y respaldos. Predeterminado: `data` dentro del proyecto.
- `CONSULTORIO_TICKETS_DIR`: carpeta de PDF. Predeterminado: `Tickets` dentro del proyecto.
- `PRINTER_NAME`: nombre exacto de la impresora en Windows; predeterminado `MP-POS80`.
- `PRINTER_PROFILE`: perfil ESC/POS; predeterminado `TM-T88V`.
- `CLINIC_NAME`, `CLINIC_ADDRESS`, `CLINIC_WHATSAPP`: datos comunes para documentos e interfaz de historial.
- `PDF_FONT`: fuente TTF opcional. En Windows se utiliza Arial; sin ella se usa Helvetica con sustitución de caracteres no compatibles.

Utilice rutas absolutas, en disco local. Para facilitar actualizaciones, es preferible mantener los datos fuera del directorio del código, por ejemplo `C:/Consultorio/Datos` y `C:/Consultorio/Tickets`. Los directorios deben tener permisos de escritura para el operador. No coloque la base activa en una carpeta compartida o sincronizada en tiempo real.

Los catálogos obligatorios son `Lista de Precios-Las Marianas.xlsx` y `Lista de Precios-Dental.xlsx`. General requiere `ID_General`, `Categoría`, `Nombre Específico`, `Precio Unitario`, `Costo Laboratorio`, `Costo Insumos`; Dental requiere `ID_Dental`, `Categoría`, `Nombre Específico`, `Precio Unitario`, `Costo`. Ambos admiten `Descuento` monetario por unidad. Los identificadores deben ser únicos dentro del catálogo; `OTROS` está reservado.

Los catálogos se validan y vuelven a leer al consultar o registrar una venta. Si un precio cambia después de preparar el carrito, el servidor rechaza un total desactualizado. Actualice el catálogo y vuelva a agregar las líneas afectadas.

Para generar archivos de demostración sin tocar catálogos existentes:

```powershell
.\venv\Scripts\python.exe generar_precios.py --output .test-runtime/demo-nuevo
```

El directorio de destino debe ser nuevo. Esos archivos son ejemplos, no precios comerciales validados.

## Almacenamiento y primera migración

`consultorio.sqlite3` es la fuente principal de ventas. Cada ticket conserva importes, precios, costos y descuentos de sus líneas, además de pagos y eventos. Los IDs, la venta y sus trabajos de documentos se guardan en una sola transacción. Los importes se calculan con Decimal, se conservan como cadenas decimales exactas y la interfaz opera en céntimos.

Al iniciar por primera vez, el sistema importa `ventas.json`, reserva la numeración de `id_counters.json`, libros contables y nombres de PDFs, y crea una copia `backups/pre-migration-*` de JSON y Excel antes de importar. No modifica esos archivos heredados durante la importación. Un JSON corrupto, IDs duplicados o datos incompatibles detienen la migración: restaure o concilie una copia válida; nunca se inicia un historial vacío para reemplazar uno dañado.

También puede ejecutar la migración explícitamente, con la aplicación detenida:

```powershell
.\venv\Scripts\python.exe backend/maintenance.py migrate
.\venv\Scripts\python.exe backend/maintenance.py verify
```

Los libros anteriores se conservan porque pueden incluir operaciones ausentes del JSON o ajustes manuales. Las nuevas ventas se exportan de manera idempotente por ID exacto. No se reconstruye ni se borra todo el libro. Los costos históricos no disponibles no se inventan. Antes de desplegar, concilie las diferencias entre libros, JSON y PDFs sobre una copia de los datos.

Después de migrar, editar `ventas.json` o los contadores anteriores no cambia SQLite. Los archivos heredados se mantienen como evidencia; no son el historial activo. No ejecute scripts antiguos que escribían directamente en Excel, como `prueba_rapida.py`.

## Ventas, documentos e impresión

El servidor valida DNI, cantidades enteras, servicios, importes, descuentos y pagos. Calcula total y vuelto; no acepta como autoridad los importes derivados enviados por el navegador. Los pagos digitales no generan vuelto: cualquier exceso debe estar cubierto por efectivo. Se permite una venta de total cero, por ejemplo un descuento explícito del 100 %, sin pagos ficticios.

El carrito bloquea el cambio de área mientras contiene servicios; quitar una línea no elimina las demás del mismo servicio. El borrador permanece en la sesión del navegador al cambiar de pestaña interna o recargar. No es un respaldo permanente y puede perderse al cerrar la sesión del navegador.

Cada registro utiliza una clave de operación única y conserva la solicitud exacta antes de enviarla. Ante una desconexión, utilice «Reintentar operación pendiente». El servidor devuelve el mismo ticket sin repetir el cobro, los documentos ni las dos copias iniciales. No borre el almacenamiento del navegador mientras haya una operación sin confirmar; consulte primero el historial.

Excel, PDF e impresión se procesan mediante una cola persistente con un solo trabajador. Sus fallos no deshacen una venta confirmada. Consulte «Documentos e impresión» desde el ticket del historial. Si Excel está abierto y bloquea la escritura, ciérrelo y reintente Excel/PDF desde allí.

«Enviado» para impresión significa que el sistema de impresión aceptó la tarea; no prueba la salida física de papel. Una impresión fallida o interrumpida no se repite automáticamente. Verifique el papel antes de solicitar nuevas copias. La reimpresión admite entre una y cinco copias y rechaza solicitudes mientras haya copias pendientes.

Anular requiere un motivo y registra fecha y evento, conservando la venta y su PDF. La actualización del libro contable se encola; mientras esté pendiente o fallida, Excel todavía puede mostrar la fila anterior. Una anulación no ejecuta devoluciones bancarias ni de efectivo: el operador debe completar y conciliar la devolución correspondiente.

## Respaldos, restauración y actualizaciones

En cada arranque se crea, si falta, un respaldo de la fecha local en `data/backups/daily-AAAAmmdd`. Incluye una instantánea SQLite consistente, libros, catálogos y PDFs. Un respaldo incompleto no se considera válido. Estos respaldos locales no protegen frente a pérdida del disco: copie respaldos completos a otra unidad protegida. La retención es manual para no borrar evidencia automáticamente; controle el espacio disponible.

Respaldo manual, preferentemente con la aplicación detenida:

```powershell
.\venv\Scripts\python.exe backend/maintenance.py backup --output D:/Respaldos/consultorio-2026-10-14
```

El destino debe ser nuevo. Se verifica integridad SQLite y solo al finalizar se escribe `BACKUP_COMPLETE`. Para comprobar el respaldo:

```powershell
.\venv\Scripts\python.exe backend/maintenance.py --data-dir D:/Respaldos/consultorio-2026-10-14 verify
```

Para restaurar sin sobrescribir el estado actual:

```powershell
.\venv\Scripts\python.exe backend/maintenance.py restore --source D:/Respaldos/consultorio-2026-10-14 --output C:/Consultorio/Restaurado
```

La restauración exige un respaldo completo, comprueba integridad, crea una carpeta nueva y marca las impresiones pendientes como «Verificar papel» para evitar duplicarlas. Configure `CONSULTORIO_DATA_DIR=C:/Consultorio/Restaurado` y `CONSULTORIO_TICKETS_DIR=C:/Consultorio/Restaurado/Tickets`; verifique totales e historial antes de continuar. No pruebe una restauración enviando impresiones reales.

Antes de actualizar: detenga el sistema, cree un respaldo externo verificado, conserve el paquete de la versión anterior y compile/verifique la nueva versión. Mantenga los directorios operativos fuera del reemplazo de código. Esta versión utiliza esquema SQLite 1 y rechaza versiones desconocidas. Para volver al sistema anterior a SQLite, restaure conjuntamente su paquete y su respaldo previo: los JSON antiguos no contienen las ventas nuevas.

## Desarrollo y comprobaciones

```powershell
.\venv\Scripts\python.exe -B -m unittest discover -s backend/tests -v
cd frontend
npm.cmd run typecheck
npm.cmd test -- --watchAll=false --runInBand
npm.cmd run build
npm.cmd audit --omit=dev
```

Las pruebas Python crean datos ficticios dentro de `.test-runtime` y simulan la impresora. Cubren concurrencia, reintentos, rollback, migración, corrupción, respaldo, anulaciones, Excel bloqueado, documentos y reglas monetarias. Las pruebas React verifican líneas OTROS independientes, conservación del borrador, redondeo y recuperación de una venta interrumpida. GitHub Actions ejecuta las comprobaciones sobre Windows.

Para desarrollar con el servidor de React en el puerto 3000, configure temporalmente `CONSULTORIO_DEV_ORIGIN=http://localhost:3000` en la terminal del backend y ejecute `npm start` desde frontend. La configuración proxy dirige `/api` a `127.0.0.1:5000`. Retire ese permiso al distribuir la aplicación. La configuración de producción no habilita CORS ni debug.

## Privacidad y límites

Los datos se mantienen en el equipo. El backend no incorpora cuentas, porque hay un único operador; esto presupone que las personas con acceso a la sesión Windows están autorizadas. Proteja esa sesión y sus respaldos. La API rechaza hosts/orígenes ajenos y requiere una cabecera local para operaciones de escritura; el servidor escucha únicamente en la interfaz local.

`.gitignore` evita nuevas incorporaciones de datos, SQLite y PDFs, pero no elimina datos ya publicados en el historial de Git. La limpieza de commits antiguos requiere una actuación coordinada sobre el remoto y sus clones; no se realiza automáticamente al instalar o actualizar.

El sistema administra tickets y cobros; no constituye emisión fiscal electrónica, historia clínica ni conciliación bancaria. Debe completarse la prueba física de la impresora configurada en cada instalación.
