# Asistente de consulta Banamex — entrega final

Ejercicio de evaluación: no es un canal oficial y no debe publicarse. Atiende Joy y Clásica, apertura y algunos servicios de MiCuenta/Switch, canales oficiales y seguridad. Responde en español e inglés con fichas y fuentes públicas locales; no accede a cuentas ni realiza trámites.

## Instalación portable: Windows, macOS y Linux

Las [instrucciones de tres líneas](INSTRUCCIONES.txt) usan **Docker Compose**. Docker instala y ejecuta Python, las dependencias, E5 y Ollama con `qwen3:4b` en contenedores Linux. No requiere Python, Ollama, rutas WSL ni modelos previamente instalados en el equipo anfitrión.

```text
docker compose up --build
```

Espera a que aparezcan `VERIFICADO: E5 ejecutado y Qwen3 respondió con un plan válido en CPU` y `Prototipo local`. Abre http://127.0.0.1:8000. Si falla una descarga o un modelo, el arranque se detiene con error: no presenta el modo básico como si fuera el completo. Si el puerto 8000 está ocupado, cierra la otra instancia antes de iniciar.

### Requisitos del otro equipo

- Windows o macOS compatibles con [Docker Desktop](https://docs.docker.com/compose/install/), o Linux compatible con Docker Engine y Compose v2. Docker debe usar contenedores Linux. Windows puede requerir WSL2/virtualización; Docker informa sus requisitos durante la instalación.
- CPU de 64 bits x86_64 o ARM64 compatible con los motores de inferencia. La presencia de imágenes para ambas arquitecturas no sustituye una prueba de rendimiento en ese hardware.
- Reserva recomendada para la demo: 8 GB de RAM para Docker, 15 GB de disco libre e internet para la primera construcción y descarga. Son márgenes operativos, no un mínimo de hardware medido. La demo puede ser más lenta en equipos modestos y agotar el límite de 25 s.
- No se promete soporte para sistemas de 32 bits, móviles, equipos sin virtualización o sistemas que Docker no soporte. La portabilidad corresponde al entorno común de contenedores, no a cualquier sistema imaginable.

Python y Ollama usan versiones y digests de imágenes fijados en Dockerfile/Compose; `requirements-portable.lock` fija las dependencias del entorno portable. E5 se verifica con SHA256; Qwen3 se descarga desde Ollama al volumen `ollama-models`. El volumen `e5-models` conserva E5. No se copian `.venv`, modelos, claves ni rutas del autor. `.gitattributes` conserva los bytes del corpus incluso al descargar con Git en Windows; `scripts.verify_package` comprueba el manifiesto de integridad. El único puerto publicado es `127.0.0.1:8000`; Ollama permanece en la red interna de Compose. No se publica el prototipo en internet.

Qwen3 interpreta consultas no resueltas por rutas anteriores y devuelve un plan JSON validado. Las respuestas visibles usan fichas y plantillas. Se conserva CPU (`num_gpu: 0`), contexto 2048 y espera de chat de 25 s. La preparación permite hasta 180 s para cargar el modelo y comprueba inferencia real antes de abrir el chat. Una carga tras 20 minutos de inactividad puede activar el respaldo del chat; no se promete disponibilidad universal.

### Comprobar, detener y volver a descargar

```text
docker compose ps
docker compose exec app python -m scripts.container_start --health
docker compose exec app python -m unittest discover -s tests
docker compose exec app python -m scripts.verify_package
docker compose logs app ollama
docker compose down
```

`--health` verifica estado del chat, E5 activo y presencia de Qwen3; no es una nueva prueba de inferencia. `down` conserva modelos. `docker compose down --volumes` elimina **solo los volúmenes de este proyecto** y obliga a descargar de nuevo. Se puede descargar el repositorio en otra carpeta y repetir el arranque; para comprobar instalación inicial debe hacerse sin los volúmenes anteriores.

La matriz Excel conserva los resultados de la corrida del 19 de noviembre; no debe presentarse como una nueva evaluación de contenedores. La evidencia actual de portabilidad y sus límites se documentan en [CONFIGURACION.md](docs/CONFIGURACION.md). El flujo `.github/workflows/portable.yml` permite verificar construcción y descarga desde cero en un runner Linux, además de pruebas del código en Windows/macOS/Linux. Un flujo incluido pero no ejecutado no acredita compatibilidad probada.

### Alternativa nativa en Linux/WSL

El preparador anterior `python3 preparar.py` sigue disponible únicamente para Linux/WSL con Python 3.11+ y venv. `--check` no instala ni descarga. No es la vía portable entre sistemas. Con ese entorno preparado, arranca con `./.venv/bin/python app.py --embeddings --ollama-model qwen3:4b`, sin sudo.

Para ejecutar sin instalar componentes opcionales:

```bash
python3 app.py
```

Este comando activa solo reglas y fichas locales; sus resultados se informan por separado. E5 sin Qwen3: `./.venv/bin/python app.py --embeddings`. Los modos usan el mismo código y corpus.

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
./.venv/bin/python evaluate.py --embeddings --ollama-model qwen3:4b --output evaluation/nueva_corrida
```

La primera orden ejecuta pruebas sin requerir modelos, incluidas simulaciones de rutas y fallos. La segunda ejecuta inferencia real y audita las fuentes antes de comparar cuatro variantes sobre las mismas 75 preguntas. No mezcles una simulación con una medición de Qwen3. El lote contiene preguntas usadas durante el desarrollo; no representa una validación independiente.

El CLI admite `python3 -m asistente_banamex.cli --help`; con el paquete instalado expone `asistente`. Sus subcomandos son `serve`, `chat`, `eval` y `prepare-embeddings`. `eval --output` permite conservar corridas separadas y los parámetros `--semantic-min-score` / `--semantic-min-margin` mantienen el mismo significado que en app.py.

## Código

`app.py` sirve HTTP solo en loopback. `asistente_banamex/engine.py` coordina reglas, recuperación, E5 y clasificador; `routing.py` interpreta alcance e intención; `retrieval.py` maneja SQLite FTS5; `answers.py` construye respuestas citadas; `semantic.py` ejecuta E5; `ollama.py` valida planes de Qwen3. La interfaz está en `asistente_banamex/web/`. La preparación y evaluación viven en `scripts/`, y las pruebas en `tests/`.
