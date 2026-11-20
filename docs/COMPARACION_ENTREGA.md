# Comparación de procedencia y consolidación final

Fecha: 19 de noviembre de 2026. Inspección y pruebas locales; no se publicó ni desplegó nada.

## Dónde se trabajó

- ZIP recibido: `/home/rafael/proyectos/entrega_banamex_final.zip`, raíz interna `banamex/`. Se conserva íntegro. SHA-256: `85bb147f9076e8d92789f73026fa4d7bac3bdb3b8cd71406e3c971c9ea4eb573`.
- Proyecto donde Codex aplicó los cambios de esta conversación: `/home/rafael/proyectos/proyecto_banamex`. No tiene Git; se conservaron los archivos existentes y copias anteriores fuera del proyecto.
- Ollama se instaló fuera del proyecto: `~/.local/opt/ollama`, modelos en `~/.ollama/models`, servicio de usuario `~/.config/systemd/user/ollama.service`. Ese entorno y las descargas no van dentro del ZIP.
- Entrega consolidada: `/home/rafael/proyectos/entrega_banamex_final_validada.zip`. Su fuente es el proyecto de trabajo actualizado, con las incorporaciones del ZIP descritas abajo. El archivo recibido y el ZIP anterior de dist no se sustituyen.

## Hallazgos e integración

La comparación inicial de los 108 archivos del ZIP encontró 72 idénticos al proyecto, 25 diferentes y 11 solo presentes en el ZIP. Las copias duplicadas de datos/interfaz/casos se contaron como archivos de ese ZIP.

| Componente | ZIP recibido | Proyecto de la conversación | Decisión final |
|---|---|---|---|
| CLI y rutas de recursos | Umbrales semánticos, salida configurable y detección más robusta de recursos | CLI más limitado, con restricción E5/Ollama ya eliminada | Integrar el CLI y detección de recursos del ZIP; conservar E5 independiente |
| Clasificador | Soporte adicional de cuentas y lenguaje cotidiano; espera 5 s | CPU, espera 25 s e intención de canal de tarjeta | Combinar capacidades del ZIP con CPU, contexto 2048 y espera 25 s; conservar canal y guardias |
| Canal de Clásica y seguimiento | Evitar sucursal se confundía con requisitos; sin límite específico del trámite remoto | Diferencia ubicación/canal, conserva tarjeta y aclara ambigüedad | Conservar implementación y ocho pruebas de la conversación |
| Interfaz | Identifica E5 y Qwen3 en las rutas | Etiquetas menos completas | Integrar etiquetas del ZIP |
| Pruebas | 61 pruebas; ocho fallos y dos errores al ejecutarlas tal cual | 26 pruebas, incluidas canal y CLI | Combinar en 70 pruebas; actualizar dos fixtures para que realmente alcancen E5/clasificador |
| ES1 de evaluación | Pregunta adecuada para presentación | Texto coloquial histórico | Conservar formulación del ZIP y reevaluar todas las variantes |
| Documentación | Métricas históricas mezcladas y garantías excesivas | Instrucciones ligadas al equipo y resultados parciales recientes | Reescribir documentación y PDF con corrida final y límites explícitos |

Los diez fallos de pruebas del ZIP original provenían de fixtures que ahora resolvían las reglas antes de llegar al componente simulado. Se cambió su formulación para ejercitar el mismo camino esperado; no se cambió el resultado esperado para esconder una regresión. También se cerró automáticamente la conexión SQLite al liberar el corpus para evitar avisos de recursos no cerrados en Python 3.14.

## Verificación

El ZIP recibido se extrajo en una carpeta temporal y se ejecutó sin editar: 61 pruebas, ocho fallos y dos errores; evaluación local 66/75 y Excel 20/20. La consolidación pasa 70/70 pruebas y la evaluación completa real se informa en [RESULTADOS.md](RESULTADOS.md). El modo completo logró 72/75 con dos marcas críticas de rúbrica; no se declara libre de errores. No se atribuyen a Codex los cambios que ya estaban en el ZIP ni los cambios concurrentes preservados del proyecto.

La entrega contiene una sola copia canónica del paquete, fuentes y casos en `asistente_banamex/`; omite duplicados, entornos virtuales, modelos grandes, cachés y reportes históricos. Se documenta la preparación previa necesaria para el modo completo y se conserva `python3 app.py` como arranque básico sin dependencias externas. Los modelos opcionales se descargan solo mediante las instrucciones explícitas de preparación.
