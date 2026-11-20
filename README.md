# Asistente de consulta Banamex — entrega final

Ejercicio de evaluación: no es un canal oficial y no debe publicarse. Atiende Joy y Clásica, apertura y algunos servicios de MiCuenta/Switch, canales oficiales y seguridad. Responde en español e inglés con fichas y fuentes públicas locales; no accede a cuentas ni realiza trámites.

## Arranque nativo con iniciadores — sin Docker

1. Descarga y descomprime **toda** la carpeta del proyecto.
2. Windows: abre `iniciar.cmd` y autoriza el instalador Microsoft si se solicita. macOS/Linux: abre una terminal en la carpeta y ejecuta `sh iniciar.sh` (macOS también incluye `iniciar.command`).
3. Espera la preparación y el navegador automático; si no se abre, usa la URL impresa. Mantén la terminal abierta; Ctrl+C detiene la demo.

Estas son también las tres líneas de [INSTRUCCIONES.txt](INSTRUCCIONES.txt). La primera ejecución necesita internet y puede tardar varios minutos. No exige instalar Python, Ollama o Docker previamente: descarga uv 0.13.9 verificado por SHA256, prepara Python 3.13.18 y el entorno `.runtime/venv`, y descarga Ollama 0.40.16 privado si no encuentra un servicio local disponible. Los archivos pertenecen a esta carpeta: no requiere sudo, no altera PATH ni registra Python en Windows, no habilita servicios ni cambia las políticas de ejecución de Windows.

Windows puede necesitar [Microsoft Visual C++ Runtime](https://onnxruntime.ai/docs/install/). Si falta, se descarga desde [Microsoft](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist), se verifica su firma Authenticode y se abre el instalador con autorización del usuario mediante Windows. Ese componente sí se instala en el sistema y puede requerir reinicio; no se cambia ninguna política de ejecución ni se oculta una elevación.

### Sistemas y recursos

- Windows 10 22H2 o posterior, de 64 bits x86_64/ARM64, con curl.exe y PowerShell 5 o posterior (incluidos en sistemas compatibles).
- macOS 14 o posterior, Intel o Apple Silicon. Usa `sh iniciar.sh` si Finder no permite abrir `iniciar.command`; no se desactivan controles del sistema.
- Linux/WSL de 64 bits x86_64/ARM64 con glibc 2.28+, shell, tar, curl o wget y sha256sum o shasum. Bibliotecas de CPU como libgomp/libstdc++ deben estar disponibles; una distribución mínima puede requerir instalarlas mediante su administrador. No se promete soporte para Alpine/musl.
- Margen recomendado: 8 GB de RAM y 15 GB libres. Son márgenes de preparación, no mínimos medidos ni garantía de latencia en cualquier equipo. La primera ejecución descarga varios GB. Redes corporativas y políticas de instalación pueden bloquear descargas o ejecutables.

Para Mac Intel se selecciona ONNX Runtime 1.23.2, que ofrece binarios para Python 3.13; los demás usan 1.32.0. `requirements-native.txt` fija las dependencias con marcadores por plataforma. Es el mismo E5 y el mismo Qwen3, pero los resultados de rendimiento/precisión del backend alternativo no deben asumirse idénticos a los de la matriz histórica.

### Qué verifica el iniciador

E5 se descarga con SHA256 y se ejecuta en CPU. Qwen3:4b se descarga, carga en CPU y debe devolver un plan JSON válido antes de abrir el chat. Si falla algún componente, el iniciador termina con error; no presenta el modo básico como si fuera el modo completo. El navegador solo se abre después de comprobar `/api/status` en modo adaptativo con E5 activo.

Qwen3 interpreta consultas no resueltas por las rutas anteriores; las respuestas visibles se construyen con fichas y plantillas. Se conservan modelo, prompts, CPU, contexto 2048 y timeout del chat 25 s. La carga inicial permite 180 s; tras 20 min de inactividad puede activarse respaldo al recargar el modelo.

Si ya hay Ollama en la URL local, se reutiliza y no se detiene al cerrar la demo. Si el iniciador crea Ollama, utiliza `.runtime/ollama-models`, escucha solo en loopback y lo detiene al salir. Log propio: `.runtime/ollama.log`. Los modelos E5 se conservan en `.models`. No hay rutas absolutas del autor en los iniciadores. `.gitattributes` conserva bytes del corpus incluso con Git en Windows.

### Comandos de control

```text
sh iniciar.sh --port 8002
sh iniciar.sh --prepare-only
sh iniciar.sh --no-browser
```

En Windows los mismos argumentos se pasan a `iniciar.cmd`. `--prepare-only` instala y verifica, sin abrir el chat; detiene Ollama si lo inició. Una preparación posterior reutiliza las descargas. `preparar.py --check`, ejecutado con el Python del entorno, comprueba recursos sin descargar/iniciar servicios ni inferir con Qwen3; necesita Ollama activo (por ejemplo, durante la demo). Si el puerto está ocupado, cierra la otra instancia o usa `--port`; no se abre un servidor ajeno como si fuera esta demo.

### Docker opcional

Quien ya utilice Docker compatible puede seguir ejecutando:

```text
docker compose up --build
```

Docker usa su propio Python 3.14.4 y ONNX 1.32; las imágenes están fijadas por digest y las dependencias en `requirements-portable.lock`. Publica solo `127.0.0.1:8000`. `docker compose down` conserva sus volúmenes de modelos; `down --volumes` los elimina.

La evidencia real, simulaciones y plataformas pendientes están en [CONFIGURACION.md](docs/CONFIGURACION.md). La matriz Excel conserva la evaluación del 19 de noviembre y no es una nueva medición de los iniciadores. El workflow incluye pruebas nativas por sistema; su presencia no acredita ejecución satisfactoria.

Para ejecutar sin instalar componentes opcionales:

```bash
python3 app.py
```

Este comando activa solo reglas y fichas locales; sus resultados se informan por separado. E5 sin Qwen3: `./.runtime/venv/bin/python app.py --embeddings`. Los modos usan el mismo código y corpus.

## Evidencia y entregables

- [Instrucciones de tres líneas](INSTRUCCIONES.txt).
- [Nota de diseño de dos páginas](docs/NOTA_DISENO.pdf) y [fuente editable](docs/NOTA_DISENO.md).
- [Resultados actuales y límites](docs/RESULTADOS.md).
- [Comparación del ZIP recibido y la versión preparada](docs/COMPARACION_ENTREGA.md).
- [Bitácora y uso de IA](docs/BITACORA.md).
- [Fuentes, URL y fecha](asistente_banamex/data/facts.json); HTML originales en `asistente_banamex/data/raw/`.
- [Excel del reto](asistente_banamex/evaluation/cases/preguntas_prueba.xlsx).
- [Resumen de evaluación final](evaluation/final_20261119/summary.json) y CSV por variante en esa carpeta.

No se incluyen los reportes históricos mezclados con otras configuraciones ni afirmaciones de ausencia universal de errores. Las fichas son capturas de noviembre de 2026; no se verifican tarifas en vivo. Sobre Clásica sin acudir a una sucursal, el asistente reconoce que las fichas no confirman completar todo el trámite a distancia y enlaza la ficha oficial.

## Verificación

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
./.runtime/venv/bin/python evaluate.py --embeddings --ollama-model qwen3:4b --output evaluation/nueva_corrida
```

La primera orden ejecuta pruebas sin requerir modelos, incluidas simulaciones de rutas y fallos. La segunda ejecuta inferencia real y audita las fuentes antes de comparar cuatro variantes sobre las mismas 75 preguntas. No mezcles una simulación con una medición de Qwen3. El lote contiene preguntas usadas durante el desarrollo; no representa una validación independiente.

El CLI admite `python3 -m asistente_banamex.cli --help`; con el paquete instalado expone `asistente`. Sus subcomandos son `serve`, `chat`, `eval` y `prepare-embeddings`. `eval --output` permite conservar corridas separadas y los parámetros `--semantic-min-score` / `--semantic-min-margin` mantienen el mismo significado que en app.py.

## Código

`app.py` sirve HTTP solo en loopback. `asistente_banamex/engine.py` coordina reglas, recuperación, E5 y clasificador; `routing.py` interpreta alcance e intención; `retrieval.py` maneja SQLite FTS5; `answers.py` construye respuestas citadas; `semantic.py` ejecuta E5; `ollama.py` valida planes de Qwen3. La interfaz está en `asistente_banamex/web/`. La preparación y evaluación viven en `scripts/`, y las pruebas en `tests/`.
