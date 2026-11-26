# Nadia Fitness Dance Studio — propuesta v5

La v5 toma la **estructura de página de una web clásica de actividades locales** (la referencia es [blackfrogdivers.com](https://www.blackfrogdivers.com/), también en Torrox Costa) y la monta sobre todo lo aprendido en las versiones anteriores ([v1](https://negimaru.github.io/nadia-fitness/) · [v2](https://negimaru.github.io/nadia-fitness-alt/) · [v3](https://negimaru.github.io/nadia-fitness-v3/) · [v4](https://negimaru.github.io/nadia-fitness-v4/)). Cada regla de diseño de [`DESIGN.md`](DESIGN.md) lleva al lado el motivo por el que existe.

## Qué toma de cada sitio

| De | Qué |
|---|---|
| **Black Frog Divers** | Barra superior con redes, logo grande centrado y menú fijo debajo; foto a todo lo ancho como portada; «elige tu clase» con 4 tarjetas cuadradas; títulos centrados en mayúsculas; banda de cifras; páginas interiores con barra de título y migas de pan; pie oscuro con columnas de contacto y horarios |
| **v4** | Un solo archivo de datos y páginas generadas, el panel «Hoy en el estudio», el horario con filtros y pestañas, el bloque rosa del teléfono, el formulario a WhatsApp y las 15 reglas de diseño |
| **v1–v3 y feedback** | Energía de la marca (rosa, cursiva de acento, fotos en color), sin brillos ni etiquetas sobre títulos, sin menores en fotos, accesibilidad WCAG 2.2 AA, horario imprimible |

Lo que **no** se ha copiado: cifras inventadas (la banda de números solo muestra datos reales: clases, sesiones, grupos y la valoración de Google), el formulario en la portada, sliders y tienda.

## Cómo se edita

Todo el contenido que se repite o cambia está en **`data/site.json`**: clases, grupos de la portada, horario, teléfono, WhatsApp, dirección, horario de llamadas, valoración, redes, curso, datos de la titular y fotos. Después de editarlo:

```
python3 tools/build.py
```

El script regenera todas las páginas, el sitemap, el manifest, la imagen para compartir el Horario, las imágenes de muestra de las clases y las 4 tarjetas de grupo (necesita Pillow). El HTML generado no se edita a mano.

### Desde la hoja de Google de Nadia

El horario, las horas de llamadas, los textos de las clases y los datos de contacto los edita Nadia en una hoja de Google. La Action `.github/workflows/sheets.yml` la lee cada hora, o cuando se lanza a mano:

1. `tools/sheets.py sync` descarga los CSV de cada pestaña, los valida y los vuelca a `site.json`.
2. Si algo ha cambiado, ejecuta `build.py` y hace commit.

Con una sola fila mal no se escribe nada: la web se queda como estaba y la Action falla, con el motivo en el log.

- **Plantilla** para importar en la hoja: `python3 tools/sheets.py template web-nadia.xlsx`. Se genera desde el `site.json` actual (necesita openpyxl).
- **Enlaces:** `data/sheets.json` con `{"tabs": {"Clases": "…", "Horario": "…", "Llamadas": "…", "Estudio": "…"}}`. Cada valor es el enlace de *Archivo → Compartir → Publicar en la web → pestaña → CSV*. Sin ese archivo, la Action no hace nada.
- **Probar sin Google:** `python3 tools/sheets.py sync --csv carpeta/`, con `Clases.csv`, `Horario.csv`, etc.

Las clases nuevas o eliminadas no se hacen desde la hoja, porque necesitan foto y grupo. Se añaden aquí y después en la hoja de Nadia, en una fila con su `Código`. Mientras falte esa fila, la sincronización se para.

**Fotos de las tarjetas:** en `groups` de `site.json`, pon en `photo` el archivo de `assets/img/` (`src`), el punto de encuadre (`focus`, de 0 a 1) y el `alt`. Con `photo: null` se genera una tarjeta oscura con el número. Peques y Fitness esperan fotos sin menores.

## Comprobado

- **axe-core:** 0 infracciones en las 8 páginas, escritorio y móvil, modo claro y oscuro (y 320 px).
- **Móvil:** sin scroll horizontal a 320 px; ningún elemento con foco tapado por las barras fijas.
- **Sin JavaScript:** funciona completa (menú visible, horario por días).

Lleva `noindex` mientras sea una propuesta: hay que quitar esa línea en `tools/build.py` cuando sustituya a la web actual.
