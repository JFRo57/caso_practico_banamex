# Instalación portable y evidencia — 20 de noviembre de 2026

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

La ruta nativa `preparar.py` es una alternativa solo Linux/WSL; no es la instalación portable principal.
