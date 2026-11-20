# Iniciar con Docker — opcional

Esta opción ejecuta el **modo completo con modelos**. Para una prueba sin modelos ni respaldo LLM, usa el [modo rápido](INSTRUCCIONES_RAPIDO.md).

Usa esta opción si prefieres Docker. Necesitas Docker Desktop iniciado, o Docker Engine con Compose v2 en Linux, e internet para la primera preparación. Docker debe usar contenedores Linux.

1. Descarga y descomprime toda la carpeta del proyecto.
2. Abre una terminal en esa carpeta y ejecuta `docker compose up`.
3. Espera los mensajes `VERIFICADO` y `Prototipo local`; abre http://127.0.0.1:8000.

La primera ejecución construye la imagen de la aplicación y descarga los modelos automáticamente. No necesitas instalar Python ni Ollama en el equipo.

Para detenerlo, pulsa **Ctrl+C** y ejecuta `docker compose down`. Los modelos quedan guardados para el siguiente arranque.

Si el puerto 8000 está ocupado, cierra la otra instancia antes de iniciar.

[Volver al README](../README.md) · [Requisitos y validación](CONFIGURACION.md)
