# Iniciar en macOS

macOS 14 o posterior, Intel o Apple Silicon. Necesitas internet para la primera preparación.

Para una prueba sin modelos ni respaldo LLM, usa la [opción rápida](INSTRUCCIONES_RAPIDO.md). Esta guía corresponde al **modo completo**.

1. Descarga y descomprime toda la carpeta del proyecto.
2. Abre Terminal en esa carpeta y ejecuta `sh iniciar.sh`. También se incluye `iniciar.command` para abrirlo desde Finder si el sistema lo permite.
3. Espera a que termine la preparación y se abra el navegador. Si no abre, usa la dirección que imprime la terminal.

No necesitas instalar Python, Ollama ni Docker previamente. El primer arranque descarga las dependencias y los modelos; los siguientes reutilizan los archivos.

Mantén la terminal abierta. Para detener el chat, pulsa **Ctrl+C**.

Si el puerto está ocupado, ejecuta `sh iniciar.sh --port 8002`.

[Volver al README](../README.md) · [Requisitos y validación](CONFIGURACION.md)
