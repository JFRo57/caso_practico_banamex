# Iniciar en Windows

Windows 10 22H2 o posterior, de 64 bits. Necesitas internet para la primera preparación.

1. Descarga y descomprime toda la carpeta del proyecto.
2. Abre `iniciar.cmd`. Si falta Microsoft Visual C++, autoriza su instalador oficial cuando Windows lo solicite; puede requerir reinicio.
3. Espera a que termine la preparación y se abra el navegador. Si no abre, usa la dirección que imprime la terminal.

No necesitas instalar Python, Ollama ni Docker previamente. El primer arranque descarga las dependencias y los modelos; los siguientes reutilizan los archivos.

Mantén la terminal abierta. Para detener el chat, pulsa **Ctrl+C**.

Si el puerto está ocupado, abre una terminal en la carpeta y ejecuta `iniciar.cmd --port 8002`.

[Volver al README](../README.md) · [Requisitos y validación](CONFIGURACION.md)
