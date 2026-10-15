# Análisis técnico del sistema de tickets

Fecha: 13 de octubre de 2026. Revisión del código y del estado local del proyecto.

**Conclusión:** el sistema tiene una base sencilla y útil para administrar tickets de un consultorio, pero necesita reforzar la integridad de las ventas, la validación de importes, la privacidad y la instalación reproducible. Los riesgos más importantes afectan a la contabilidad y a la recuperación de datos; no se resuelven únicamente mejorando la interfaz.

La revisión no modifica el funcionamiento del sistema. No se registraron ventas reales ni se enviaron impresiones. Las comprobaciones de la API utilizaron datos ficticios y sustituyeron la persistencia y la impresora por simulaciones en memoria. Se inspeccionaron encabezados y cantidades de los archivos locales sin reproducir nombres ni DNI de pacientes. No se inspeccionaron los valores de `.env` ni se ejecutó el binario de SumatraPDF.

## 1. Arquitectura y alcance real

El navegador ejecuta una aplicación React con TypeScript. Flask sirve una compilación ubicada en `backend/build` y expone endpoints para catálogos, registro, historial, anulación y reimpresión. Los precios proceden de dos archivos Excel cargados al iniciar el backend. Las ventas se distribuyen entre dos libros contables, un historial JSON, un contador JSON y archivos PDF. La impresión se realiza directamente en Windows mediante ESC/POS.

Es principalmente un sistema administrativo de tickets y cobros. El código revisado no incorpora historia clínica, inventario completo, cuentas por cobrar, conciliación bancaria ni emisión electrónica fiscal. La generación de un ticket PDF por sí sola no demuestra esas capacidades.

Flujo actual: formulario → cálculo del backend → actualización del contador → Excel → JSON → PDF → dos impresiones → respuesta HTTP.

**Ventajas existentes**

- Separación inicial entre interfaz, modelos, persistencia, PDF e impresión. Permite mejorar cada parte sin rehacer todo.
- Python y React son tecnologías conocidas; el volumen de código propio es reducido y comprensible.
- `Decimal` en los modelos ayuda a calcular importes con precisión decimal.
- El backend recupera del catálogo el precio de los servicios normales, en lugar de usar directamente el precio enviado por el navegador.
- Catálogos Excel accesibles para personal que ya utiliza hojas de cálculo.
- Libros diferenciados para General y Dental, útiles para revisar ingresos por área.
- Pagos combinados, descuentos con explicación, conceptos personalizados y reutilización de datos del paciente cubren necesidades operativas concretas.
- Anulación lógica en JSON y conservación del PDF mantienen parte de la evidencia de una operación anulada.
- Bloqueo del botón durante el envío reduce dobles clics accidentales.
- `package-lock.json` y versiones Python fijadas aportan reproducibilidad parcial.
- `.gitignore` excluye actualmente datos operativos, tickets, entorno y compilaciones.

**Limitaciones de esta arquitectura**

La separación modular todavía es parcial: la ruta de registro concentra reglas comerciales, cálculos, escritura de archivos, generación del documento e interacción con hardware. Una avería de cualquiera de estas partes puede afectar al resultado de toda la petición. Excel y JSON son cómodos para intercambiar información, pero su uso simultáneo como almacenamiento principal obliga a mantenerlos sincronizados manualmente.

## 2. Hallazgos por prioridad

| Prioridad | Hallazgo | Consecuencia | Acción recomendada |
|---|---|---|---|
| Muy alta | Ventas y catálogos aparecen en commits anteriores | Datos retirados de la versión actual siguen recuperables desde Git | Revisar exposición y preparar limpieza del historial con respaldo y coordinación |
| Muy alta | Registro sin transacción entre contador, Excel, JSON y PDF | Venta parcialmente guardada y posible duplicación al reintentar | Base transaccional, idempotencia y trabajos posteriores al registro |
| Muy alta | JSON corrupto se trata como historial vacío | La siguiente venta puede sobrescribir el historial anterior | Detener escrituras, informar el error y recuperar desde respaldo |
| Alta | Descuentos, cantidades y pagos sin validación suficiente en servidor | Ventas incoherentes o sin pago validado | Validación de esquema y cálculo íntegro en backend |
| Alta | API sin autenticación; servidor en `0.0.0.0` y modo debug | Acceso a datos y operaciones desde equipos que alcancen el puerto | Limitar interfaz de red, desactivar debug y definir usuarios/permisos |
| Alta | Archivos y contadores sin bloqueo | IDs duplicados o ventas perdidas con solicitudes simultáneas | Secuencias y transacciones en base de datos |
| Alta | Éxito de impresión declarado sin comprobar resultado | Venta o reimpresión anunciada como exitosa aunque no salga papel | Estado separado de impresión y reintentos controlados |
| Alta | Configuración TypeScript incompatible con versión instalada | Comprobación de tipos falla y compromete una compilación limpia | Alinear compilador, configuración y herramienta de build |
| Media | Anulación parcial y búsqueda de ID por subcadena | Descuadre entre archivos o eliminación de otra fila | Comparación exacta y anulación transaccional con auditoría |
| Media | Catálogos, formulario, PDF y vista previa no comparten todas las reglas | Importes o documentos diferentes para la misma venta | Contrato de datos y representación coherente |
| Media | Instalación, respaldo y diagnóstico poco documentados | Dependencia del equipo y de conocimiento informal | Procedimiento reproducible y recuperación verificada |

Las prioridades reflejan impacto técnico. No implican que todos los fallos hayan ocurrido en las ventas reales.

## 3. Integridad de ventas, dinero y anulación

**Registro parcialmente completado.** En `backend/app.py:165` se escribe primero Excel y después JSON. A continuación se genera el PDF. Si falla el PDF, la respuesta es 500 aunque la venta ya se haya guardado. Lo confirmé simulando un fallo de generación: ambas funciones de persistencia se habían ejecutado antes del error. Si el operador reintenta, no existe una clave de idempotencia que reconozca la misma venta.

Además, el contador se incrementa antes de finalizar la operación. Un hueco en numeración no es necesariamente grave; reutilizar o duplicar un ID sí lo es. La actualización de `id_counters.json` no dispone de bloqueo, restricción única ni recuperación coordinada con el historial.

**Pérdida silenciosa por corrupción.** `guardar_historial_json`, en `backend/catalog_manager.py:127`, captura un fallo al leer JSON y continúa con `historial = []`. La siguiente escritura reemplaza el archivo con solo la nueva venta. La lectura del historial también devuelve una lista vacía si el archivo está dañado, confundiendo corrupción con ausencia de ventas. La comprobación en memoria confirmó que una lectura inválida termina abriendo el historial para sobrescribirlo.

**Importes enviados por el cliente.** El backend acepta `descuento_especial_monto_soles` y lo resta aun cuando `descuento_especial_activo` es falso (`backend/app.py:130`). También almacena `pago_con`, `vuelto` y `desglose_pagos` sin verificar que concuerden entre sí y con el total. La API aceptó una venta ficticia con descuento desactivado, descuento monetario suficiente para dejarla en cero y pagos vacíos.

Debe calcularse en el servidor el descuento a partir de su tipo y valor, exigir una razón cuando corresponda, validar permisos y verificar los pagos. Las cantidades deben ser enteros positivos; los importes, finitos y no negativos; los porcentajes deben tener límites explícitos. Hay que definir cuándo se permite un ticket gratuito y cómo se devuelve efectivo en pagos mixtos.

**Cantidades y texto.** Una cantidad `-2` produjo un subtotal negativo y respuesta 200. `int()` también puede truncar cantidades decimales. El servidor acepta el nombre del servicio enviado por el cliente aunque el ID pertenezca a un servicio del catálogo. Debe usar el nombre canónico para servicios normales y reservar texto libre para conceptos autorizados.

`to_decimal()` elimina caracteres y transforma errores en cero. Esto oculta entradas inválidas: por ejemplo, puede perder un signo negativo y confundir formatos con separadores de miles. Es mejor rechazar el dato con un error claro que normalizarlo silenciosamente.

**Reglas distintas en frontend y backend.** El formulario calcula `precio × cantidad`; el backend calcula `(precio − descuento de catálogo) × cantidad`. Con un servicio ficticio de S/100 y descuento de S/20, el backend calculó S/80 mientras el formulario calcularía S/100. Los catálogos locales revisados tienen cero descuentos no nulos, por lo que este fallo es latente en esos archivos. Puede aparecer al activar descuentos de catálogo.

La interfaz usa números de coma flotante para caja y compara `diferenciaCaja > 0`. Esto puede bloquear operaciones por diferencias mínimas de representación. Conviene utilizar céntimos enteros o una estrategia decimal consistente, con redondeo definido y resultado confirmado por el servidor.

**Anulación.** JSON conserva la venta con `habilitado = false`, pero Excel elimina la fila. No se registran usuario real, fecha de anulación ni evento de devolución. La respuesta considera éxito si solo una de las dos modificaciones funciona. Un archivo bloqueado en Excel puede dejar la operación incompleta.

La búsqueda utiliza `id_global in texto`: `TK-1000` coincide con `TK-10000`. El defecto está confirmado por la condición del código; no se ejecutó una eliminación sobre los libros reales. Debe extraerse y compararse el identificador completo. Una anulación debería mantener la venta original, registrar su motivo, autor y momento, y reflejar el efecto económico con un estado o movimiento de reversión.

## 4. Almacenamiento y recuperación

| Medio | Ventajas | Desventajas como almacenamiento principal |
|---|---|---|
| Excel | Familiar, portable, útil para revisión y reportes | Bloqueos al abrirlo, edición manual, dependencia de columnas y fórmulas, sin transacción conjunta con JSON |
| JSON | Fácil de inspeccionar y transportar; admite detalles de venta | Reescritura completa, carreras entre solicitudes, sin índices ni restricciones; daño del archivo afecta todo el historial |
| PDF | Documento legible y conservable | No permite reconstruir fielmente todas las reglas, costos y pagos; es una salida documental |
| SQLite | Archivo local, transacciones, consultas, restricciones e índices | Requiere esquema, migración y respaldo consistente; tiene límites para escrituras concurrentes |

**Propuesta proporcionada al proyecto:** usar SQLite en disco local como fuente principal y producir Excel y PDF como salidas regenerables. Para una instalación pequeña atendida por un único backend es una opción razonable; si aparecen varios servidores o una concurrencia de escritura elevada, evaluar una base cliente/servidor. La documentación de SQLite explica estos criterios en [Appropriate Uses For SQLite](https://www.sqlite.org/whentouse.html).

El esquema debería incluir tickets, líneas de servicio, pagos, catálogos, usuarios y eventos de auditoría. Las líneas deben conservar el precio, costo y descuento aplicados al vender, aunque cambie el catálogo. Guardar importes en céntimos, fechas con año completo y zona horaria definida, e IDs sujetos a unicidad. El historial actual no conserva los IDs de servicio ni sus costos: reconstruir ganancias pasadas desde él puede resultar imposible si cambian los catálogos.

Separar el directorio del código del directorio de datos operativos. Configurar las rutas y la impresora mediante opciones explícitas. Los datos deben tener permisos de acceso apropiados y respaldos fuera del mismo disco, con versiones y protección de acceso. Una copia guardada en el mismo equipo no cubre la pérdida de ese equipo.

El respaldo debe abarcar la base o, durante la transición, JSON, contadores, catálogos y libros como un conjunto coherente. Guardar PDFs si tienen valor documental propio. Verificar periódicamente una restauración en otra ubicación: existencia de una copia no demuestra que se pueda recuperar el sistema.

La migración debe hacerse sobre copias: importar, detectar IDs repetidos, conciliar importes, conservar anulaciones y comprobar conteos antes de sustituir el almacenamiento. En el estado local hay 6 registros JSON, 14 filas entre ambos libros y 38 PDFs. Son conjuntos con distinta cantidad; esto justifica una conciliación, pero por sí solo no prueba pérdida de datos porque pueden incluir pruebas, anulaciones o documentos de otros momentos.

## 5. Seguridad y privacidad

`app.run(host='0.0.0.0', debug=True)`, en `backend/app.py:243`, escucha en todas las interfaces y activa el modo de desarrollo. La exposición efectiva depende de firewall y red; no se comprobó desde otro equipo. Los endpoints no implementan autenticación ni autorización. CORS está habilitado sin restricción de orígenes y no sustituye un control de acceso.

Para uso exclusivamente local, escuchar en `127.0.0.1`. Para acceso desde la red, utilizar un servidor de producción, autenticación, permisos para descuentos/anulaciones y transporte protegido según el despliegue. Flask desaconseja expresamente el servidor de desarrollo y el debugger en producción en su [documentación de despliegue](https://flask.palletsprojects.com/en/stable/deploying/).

El historial devuelve en una petición todas las ventas, nombres, DNI y servicios, incluidos registros anulados. Limitar datos por función, paginar consultas y registrar accesos y acciones relevantes. El campo `atendido_por` está fijado a una persona en el código; no demuestra quién realizó la operación.

Los errores devuelven `str(e)` al navegador, que puede revelar rutas o detalles internos. Sustituirlo por mensajes adecuados y registrar el diagnóstico técnico con un identificador de operación, evitando incluir innecesariamente datos personales.

Hay un riesgo de fórmulas en Excel al escribir texto controlado por el usuario que comience por `=`. Debe verificarse y forzarse el almacenamiento como texto para campos libres. Este riesgo se identificó por lectura del flujo, sin una prueba de apertura del archivo ni explotación.

**Datos en el historial de Git.** El árbol actual no rastrea `data/`, pero existen versiones anteriores de `data/ventas.json` y ambos catálogos. Los commits `1ddb688` y `5a507d1` contienen JSON con campos de paciente; se verificó únicamente su estructura y cantidad de registros. No se determinó si todos esos registros eran reales o de prueba, ni quién tiene acceso al remoto.

`.gitignore` no borra versiones anteriores. Revisar visibilidad y copias existentes, identificar qué información quedó almacenada y preparar una limpieza del historial si corresponde. Reescribir y publicar ese historial exige coordinación porque cambia referencias y afecta clones; no se realizó durante esta revisión. Eliminar un archivo de Git tampoco lo retira de copias ya descargadas.

## 6. Código, interfaz y documentos

**Backend.** Extraer las reglas de venta a un servicio independiente de Flask y del hardware. Validar entradas antes de obtener IDs o escribir archivos. Utilizar un esquema explícito para API y modelos. Los atributos `costo_lab` y `costo_insumo` se añaden dinámicamente a la dataclass: deben declararse para que los tipos y las reglas sean visibles. Los errores de entrada deberían devolver respuestas 400/422, no 500 genéricos.

Los catálogos se cargan una vez al importar la aplicación. Editar Excel no actualiza el catálogo activo hasta reiniciar. Si faltan archivos, el arranque falla. Validar columnas, tipos, duplicados y precios; ofrecer recarga controlada o administración del catálogo. `generar_precios.py` sobrescribe los archivos de precios existentes y genera General con una columna `Costo` que el código actual no usa para sus costos separados: puede producir ganancias incorrectas. Debe limitarse a datos de demostración y bloquear sobrescrituras accidentales.

**Formulario.** `handleRemoveItem` elimina todas las líneas con un mismo ID. Como todos los conceptos OTROS comparten ID, borrar uno borra también los demás. Cada línea necesita un identificador propio, distinto del ID de catálogo. Cambiar de General a Dental conserva el carrito anterior; el backend intenta resolver todas las líneas contra el nuevo catálogo. Bloquear el cambio o pedir una decisión explícita sobre el carrito.

Los campos siguen editables durante el envío; cambiar pestañas desmonta el formulario y pierde el borrador. Conviene bloquear los campos mientras se registra y mantener o advertir sobre borradores. Las solicitudes usan `http://localhost:5000`: en otro equipo `localhost` se refiere a ese equipo. Preferir rutas `/api/...` cuando Flask sirve la interfaz y una configuración explícita en desarrollo.

**Historial y experiencia de uso.** Incorporar búsqueda por ticket/paciente, filtros por fecha y área, ordenamiento y paginación. Distinguir carga, lista vacía y fallo de conexión: actualmente un fallo puede parecer ausencia de datos. Revisar accesibilidad de modales, foco de teclado, etiquetas de botones y adaptación móvil; el HTML declara idioma inglés pese a que la interfaz es española. Reducir estilos en línea y dividir los componentes grandes para facilitar mantenimiento.

**Impresión.** `imprimir_ticket_escpos()` devuelve falso si falla, pero registro y reimpresión no comprueban ese valor. La prueba confirmó respuesta 200 con impresora simulada fallida. Reimprimir con cantidad cero también devuelve éxito; el límite 1–5 existe en la interfaz pero no se valida en el servidor.

Guardar la venta y tratar la impresión como una tarea con estados pendiente/enviada/fallida. Permitir reintentar sin duplicar el cobro. Separar el registro de las dos copias obligatorias y del `sleep(2.5)`, que prolonga cada petición. No confundir aceptación por la cola de impresión con confirmación física de papel. Cerrar el recurso de impresora también ante excepciones.

**PDF y vista previa.** El PDF recorta servicios a 24 caracteres y no incluye observaciones; la impresora y la vista previa sí pueden mostrarlas. PDF, impresión y modal tienen diseños independientes. Nombres largos, métodos de pago extensos y caracteres no soportados por Helvetica requieren pruebas. La altura estimada no garantiza una única página para cualquier contenido. Usar ajuste por ancho real, fuentes con cobertura adecuada y datos comunes para las tres representaciones. La función llamada `total_a_letras` imprime números, no su conversión a palabras.

## 7. Repositorio, dependencias y ejecución

**Compilación comprobada.** El lockfile y el entorno local contienen TypeScript 4.9.5, pero `frontend/tsconfig.json:17` declara `moduleResolution: bundler`. La comprobación `tsc --noEmit -p frontend/tsconfig.json` falla con TS6046 y TS5070. La estrategia `bundler` se incorporó en TypeScript 5.0, según sus [notas oficiales](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-0.html).

Resolver la incompatibilidad como conjunto: configuración, TypeScript y `react-scripts`. No basta con actualizar una dependencia sin comprobar el resto. La existencia local de `backend/build` permite que haya una versión ejecutable antigua aunque el código fuente actual no pase esta comprobación. No se verificó que ese build corresponda exactamente al código revisado.

Existen dos `requirements.txt` diferentes. El de `docs` omite dependencias usadas por la impresión. Mantener una fuente de dependencias y separar ejecución de desarrollo/ empaquetado; fijar versiones de Python y Node. El entorno disponible utiliza Python 3.14. No se ejecutó una auditoría de vulnerabilidades de dependencias, por lo que este informe no afirma presencia ni ausencia de CVE.

`SumatraPDF.exe` ocupa aproximadamente 20,3 MB y no se referencia desde el código revisado. Evitar binarios ajenos innecesarios dentro de Git; si se necesitan, documentar origen, versión, licencia y método de verificación. El historial de Git conserva también versiones eliminadas de binarios, por lo que borrarlos del árbol actual no reduce automáticamente todo el repositorio.

El lanzador oculta los errores, espera un tiempo fijo y abre el navegador sin comprobar que el servicio esté listo. Puede ejecutar otra instancia si el puerto ya está ocupado. El mensaje sobre cerrar la ventana no sustituye una gestión explícita del proceso. Añadir diagnóstico visible, comprobación de salud y procedimiento claro de apagado.

El README describe extracción por Regex que no aparece en el flujo actual y no explica instalación, configuración, build, datos iniciales, respaldo ni recuperación. Actualizarlo al comportamiento real. No se encontraron pruebas automatizadas versionadas ni una configuración CI. Existe un `prueba_rapida.py` local ignorado que escribe en el Excel operativo: no se ejecutó y debería trasladarse a un entorno de pruebas aislado.

## 8. Plan de mejora

**Primero: evitar daños y corregir inconsistencias.** Respaldar y conciliar los archivos actuales; revisar datos presentes en Git; desactivar debug y definir alcance de red; rechazar entradas inválidas; calcular descuento, pago y vuelto en servidor; impedir sobrescritura tras corrupción; comprobar estados de impresión; corregir IDs por subcadena, líneas repetidas y cambio de destino; alinear TypeScript con la configuración.

**Después: consolidar el núcleo.** Migrar a SQLite con transacciones, restricciones y clave de idempotencia. Conservar una instantánea de precios y costos por venta. Separar tareas de PDF/impresión y exportaciones. Registrar usuarios, permisos y eventos de anulación. Mantener Excel como reporte y verificar una restauración completa.

**Luego: facilitar operación y mantenimiento.** Documentar instalación y publicación del build; configurar rutas e impresora; incorporar logs y comprobación de salud; filtros y paginación; accesibilidad y borradores; unificar contenido de documentos; actualizar dependencias con verificación de compatibilidad.

Pruebas de mayor valor: dos registros simultáneos; reintento de la misma venta; corte o error durante persistencia; JSON dañado durante transición; Excel bloqueado; cantidades inválidas; descuentos límite; pagos mixtos y redondeo; anulación con devolución; impresora desconectada; documentos largos; instalación limpia y restauración del respaldo. Son escenarios de negocio y recuperación, no pruebas que solo repiten la implementación.

## 9. Evidencia y límites

- Lectura de todos los módulos propios versionados y del script local de prueba; revisión de estructura, dependencias, lanzador y Git.
- Compilación sintáctica de los archivos Python satisfactoria. Esto no verifica las reglas de negocio ni el hardware.
- Comprobación TypeScript fallida por incompatibilidad de configuración/versiones.
- API simulada: cantidades negativas, descuento inactivo y pagos vacíos aceptados; fallo de impresora ignorado; PDF fallido después de ambas escrituras; reimpresión con cero copias aceptada.
- Persistencia simulada: JSON corrupto conduce a apertura para sobrescritura. Comparación textual confirma la colisión entre prefijos de IDs.
- Revisión estructural de catálogos, historial, libros y cantidades de PDFs; detección de datos históricos en Git sin incluir identidades en el informe.
- No se ejecutó una venta real, borrado real, impresión física, instalación limpia, build completo, prueba de concurrencia ni restauración. Los riesgos de concurrencia, bloqueo de Excel y formato de documentos se deducen del flujo y requieren esas pruebas para medir su manifestación real.

La base existente puede conservarse. El mayor retorno está en convertir la venta en una operación consistente y verificable, separar sus documentos del almacenamiento principal y hacer recuperable el sistema ante fallos.
