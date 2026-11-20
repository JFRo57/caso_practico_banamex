# Iniciar en Linux / WSL

Linux de 64 bits con glibc 2.28 o posterior. Necesitas internet, `tar`, `curl` o `wget`, y una herramienta SHA256 (`sha256sum` o `shasum`). Una instalación mínima puede necesitar las bibliotecas `libgomp` y `libstdc++`.

Para una prueba sin modelos ni respaldo LLM, usa la [opción rápida](INSTRUCCIONES_RAPIDO.md). Esta guía corresponde al **modo completo**.

1. Descarga y descomprime toda la carpeta del proyecto.
2. Abre una terminal en esa carpeta y ejecuta `sh iniciar.sh`.
3. Espera a que termine la preparación y se abra el navegador. Si no abre, usa la dirección que imprime la terminal.

No necesitas instalar Python, Ollama ni Docker previamente. El primer arranque descarga las dependencias y los modelos; los siguientes reutilizan los archivos.

Mantén la terminal abierta. Para detener el chat, pulsa **Ctrl+C**.

Si el puerto está ocupado, ejecuta `sh iniciar.sh --port 8002`.

[Volver al README](../README.md) · [Requisitos y validación](CONFIGURACION.md)
