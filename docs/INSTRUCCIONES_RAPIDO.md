# Ejecución rápida — sin Ollama ni Qwen3

Para probar el chat con **reglas, búsqueda FTS5 y fichas locales**, sin descargar modelos. Este modo tampoco utiliza E5.

1. Descarga y descomprime toda la carpeta del proyecto.
2. Windows: abre `iniciar_rapido.cmd`. macOS/Linux: abre una terminal en esa carpeta y ejecuta:

   ```bash
   sh iniciar_rapido.sh
   ```

3. Abre la URL impresa si el navegador no se abre automáticamente. Mantén la terminal abierta; **Ctrl+C** detiene el chat.

Si ya tienes Python 3.11+ compatible, el iniciador lo reutiliza. Si no lo encuentra, prepara Python privado; esa primera descarga necesita internet. Si faltan las zonas horarias, instala únicamente el pequeño paquete `tzdata` en un entorno privado. No instala Ollama, Qwen3, E5, ONNX ni Microsoft Visual C++.

**No existe respaldo (fallback) hacia un LLM en este modo**, aunque Ollama ya esté instalado en el equipo. Las consultas que no resuelven las reglas y las fichas terminan en una aclaración o abstención; puede reconocer menos formulaciones que el modo completo. Las respuestas admitidas mantienen sus citas. El estado del chat muestra que no hay respaldo LLM.

Para elegir otro puerto:

```bash
# macOS/Linux
sh iniciar_rapido.sh --port 8002
```

```bat
rem Windows
iniciar_rapido.cmd --port 8002
```

Para activar E5 y el respaldo Qwen3, detén el modo rápido y sigue la guía del modo completo de tu plataforma.

[Windows](INSTRUCCIONES_WINDOWS.md) · [macOS](INSTRUCCIONES_MACOS.md) · [Linux](INSTRUCCIONES_LINUX.md) · [Volver al README](../README.md)
