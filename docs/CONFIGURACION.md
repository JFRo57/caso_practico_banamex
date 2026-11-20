# Configuración de entrega — iniciadores nativos (20 de noviembre de 2026)

La vía principal ya no requiere Docker. Windows usa iniciar.cmd; macOS/Linux usan sh iniciar.sh. macOS también dispone de iniciar.command. Los iniciadores descargan uv 0.13.9 con SHA256 fijado y Python 3.13.18 privado, sin PATH ni registro global, y ejecutan preparar.py. La preparación nativa vive en scripts/native_start.py; Docker sigue disponible como alternativa.

## Modo rápido

Los iniciadores iniciar_rapido.cmd/sh/command activan --quick. Reutilizan Python3.11+ cuando está disponible o utilizan el bootstrap de Python privado. No preparan Ollama, Qwen3, E5, ONNX ni Visual C++. Si falta la base de zonas horarias del sistema, instalan solo tzdata2026.6 en .runtime/quick-venv; el modo completo también declara tzdata en Windows.

El servidor arranca sin --embeddings ni --ollama-model: Engine.model y Engine.semantic quedan en None. No puede hacer fallback al LLM, incluso con Ollama disponible. Las consultas no resueltas se aclaran o se rechazan según las políticas existentes. APIstatus declara routing_mode=local, model=null y embeddings=false; el chat muestra explícitamente ausencia de respaldo LLM. No se alteran los parámetros ni las rutas del modo completo.

## Preparación y comprobaciones

Windows requiere el runtime de Microsoft Visual C++ para ONNX. Si no están disponibles sus DLL, el iniciador descarga el redistribuible oficial, exige firma Authenticode válida de Microsoft y abre su instalador con autorización UAC del usuario. Es una instalación del sistema, a diferencia de Python/Ollama privados; puede necesitar reinicio. Esta rama se probó con simulaciones, no en Windows real. Fuentes: https://onnxruntime.ai/docs/install/ y https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist.

- Dependencias en requirements-native.txt, entorno .runtime/venv. ONNX 1.23.2 solo para Mac Intel; ONNX 1.32 para el resto. Se mantiene el mismo E5 cuantizado y qwen3:4b, CPU, contexto 2048 y timeout 25 s.
- Si no hay Ollama local disponible, se instala un binario privado 0.40.16, descargado con hash SHA256 por plataforma. No se habilitan servicios ni se cambian políticas de ejecución Windows. Los modelos propios quedan en .runtime/ollama-models.
- Se ejecuta E5, se carga Qwen3 en CPU y se exige un plan real válido antes de arrancar el chat. El navegador solo se abre tras confirmar estado adaptativo/E5. Si falla la preparación no se declara éxito ni se abre modo básico como equivalente.
- Al terminar se detienen solo los procesos iniciados por esta ejecución. Ollama preexistente se conserva. Un puerto ocupado provoca un error claro; --port permite elegir otro.

## Evidencia de esta intervención

- Linux/WSL x86_64: uv y Python 3.13.18 descargados y verificados, entorno nativo creado e instalación de dependencias real. Preparación e inferencia real Qwen3 correctas contra Ollama existente.
- También se probó Ollama privado: descarga oficial Linux con SHA256 y extracción real. Tras corregir el selector de ejecutable se reutilizó el archivo oficial idéntico ya verificado para repetir extracción, sin una segunda descarga. El proceso propio se inició en otro puerto loopback con pesos de la prueba aislada anterior; no se repitió su descarga. Arranque de chat, estado adaptativo, E5/Qwen3 CPU y respuesta con citas comprobados por HTTP. Al salir se cerraron ambos puertos de prueba.
- 88 unittest pasan; pruebas de errores, selección de plataforma, integridad de descarga y navegador bloqueado ante modo degradado son simuladas. Los modelos reales se comprueban por separado.
- ONNX 1.23.2 instalado y E5 ejecutado realmente en Linux con Python 3.13, no en macOS. Ruedas de dependencias para Mac Intel/Python 3.13 descargadas y disponibilidad comprobada. ZIP uv Windows verificado por SHA256 y estructura (uv.exe en raíz), sin ejecutarlo en Windows.
- Se preserva la matriz Excel original; no se repitió la evaluación de 300 consultas ni se igualan métricas de backends distintos sin medirlas.

## Límites pendientes

Windows y macOS, tanto Intel como Apple Silicon, necesitan ejecución real en esos sistemas; ARM64 tampoco se ejecutó aquí. El workflow incluye preparación nativa desde cero para Linux, Windows, Mac ARM y Mac Intel, pero solo sus resultados reales acreditan esas plataformas. Docker completo tampoco se ejecutó localmente.

Requisitos: Windows 10 22H2+, macOS 14+ o Linux/WSL glibc 2.28+ de 64 bits, herramientas de descarga indicadas en README, internet y recursos suficientes. Una distribución Linux mínima puede necesitar bibliotecas del sistema. No se garantiza instalación en cualquier OS/hardware ni sobre restricciones corporativas.

## Evidencia previa de la vía Docker (histórica)

### Instalación portable y evidencia — 20 de noviembre de 2026

## Ruta de instalación

El arranque común es `docker compose up --build` después de instalar/iniciar Docker compatible y descargar esta carpeta. Las instrucciones completas de uso ocupan tres líneas en INSTRUCCIONES.txt. No requieren Python, E5 ni Ollama del anfitrión. Docker Desktop y Docker Engine tienen requisitos propios: no se promete compatibilidad con sistemas de 32 bits, móviles, sistemas obsoletos o cualquier CPU arbitraria.

Las imágenes Python 3.14.4 y Ollama 0.40.16 están fijadas por digest de índice multi-arquitectura. Se comprobó en el registro oficial que ambas ofrecen Linux amd64 y Linux arm64. Se descargaron todas las ruedas del lock para ARM64/Python3.14, sin inferencia real en ARM. El contenedor Linux evita la ausencia de distribución ONNX 1.32 para macOS Intel nativo.

## Verificaciones realizadas

- `docker compose config --quiet`: configuración válida con Compose oficial 5.8.0, cuyo SHA256 se verificó.
- Sistema de archivos Linux Debian Trixie/Python 3.14.4 extraído de la misma imagen oficial y ejecutado en namespace de usuario con Bubblewrap: instalación real de libgomp1, certificados y dependencias sin usar .venv del autor.
- E5 descargado desde cero en la copia de prueba, hashes correctos y embeddings ejecutados en CPU.
- Qwen3 descargado desde cero en un almacén aislado vacío. Para esta prueba se utilizó el binario Ollama 0.40.16 previamente instalado, con otro proceso y puerto loopback; no el Ollama ni los modelos de la demo. La precarga y clasificación real devolvieron un plan válido; API ps confirmó size_vram=0.
- Tres consultas HTTP reales en español/inglés verificaron estado adaptativo, citas y la respuesta prudente sobre solicitud remota de Clásica.
- 79 unittest pasan en el entorno limpio. Los controles de fallos de preparación son simulados y no sustituyen las comprobaciones anteriores.
- `.gitattributes` conserva bytes del corpus en Git, incluido Windows con autocrlf; `python -m scripts.verify_package` permite verificar todos los hashes de entrega.

## Límites

No se ejecutó Docker Engine/Compose completo en esta máquina, que no tiene Docker. La prueba de filesystem Linux no acredita redes, volúmenes ni empaquetado final del motor Docker. Windows/macOS y ARM64 no fueron ejecutados localmente. El workflow incluido permite pruebas de código en Windows/macOS/Linux y una instalación Docker limpia en Linux al subir el commit; sus resultados deben comprobarse después, no inferirse por la presencia del archivo.

La matriz Excel conserva la corrida del 19 de noviembre; no se repitieron las 300 consultas. CPU, qwen3:4b, prompts, corpus, contexto 2048 y timeout de chat 25 s se preservan. La preparación permite 180 s de carga previa; el chat mantiene respaldo ante fallos y no promete tiempos de respuesta en cualquier equipo.

Esta limitación correspondía al preparador anterior; la sección vigente de iniciadores nativos al inicio sustituye esa restricción.
