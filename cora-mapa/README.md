# Mapa de datasets de la UPC en CORA.RDR

Web con un mapa de los datasets publicados en CORA.RDR (colección `upc`).
Se actualiza sola cada lunes mediante GitHub Actions. No necesita token: solo lee datasets públicos.

## Contenido

```
docs/index.html              La web del mapa (Leaflet)
docs/datos_mapa.json         Datos que lee el mapa (se regenera solo)
docs/pendientes.json         Ciudades que no se han podido situar
scripts/generar_json.py      Descarga los datos de CORA y genera el JSON
scripts/geocache.json        Memoria de ciudades ya geolocalizadas
.github/workflows/actualizar.yml   Tarea semanal automática
```

El `datos_mapa.json` incluido es una **vista previa** hecha con tu Excel. La primera ejecución automática lo sustituye por los datos reales.

## Puesta en marcha (unos 10 minutos)

1. **Crea el repositorio.** En github.com: `+` → *New repository*. Nombre, por ejemplo, `cora-upc-mapa`. Público.
   (Si es un proyecto de la biblioteca, mejor crearlo en una organización de la UPC que en una cuenta personal.)
2. **Sube los archivos.** En el repositorio: *Add file* → *Upload files*, y arrastra el **contenido** de esta carpeta
   (`docs`, `scripts`, `README.md`, `.github`). Pulsa *Commit changes*.
   - Si la carpeta `.github` no se sube (algunos navegadores ignoran las carpetas ocultas), créala a mano:
     *Add file* → *Create new file*, escribe el nombre `.github/workflows/actualizar.yml` (las barras crean las carpetas)
     y pega el contenido del archivo.
3. **Permisos para que la tarea pueda guardar datos.** *Settings* → *Actions* → *General* → *Workflow permissions*
   → **Read and write permissions** → *Save*.
4. **Activa la web.** *Settings* → *Pages* → *Source*: *Deploy from a branch* → rama `main`, carpeta **`/docs`** → *Save*.
5. **Primera ejecución.** Pestaña *Actions* → *Actualizar mapa* → *Run workflow*. Tarda unos minutos.
   Cuando termine en verde, `docs/datos_mapa.json` tendrá los datos reales.
6. **Tu web:** `https://TU-USUARIO.github.io/NOMBRE-DEL-REPO/` (tarda uno o dos minutos en aparecer la primera vez).

A partir de ahí, cada lunes se actualiza sola.

## Mantenimiento

- **Otra colección:** cambia `COLECCION = "upc"` en `scripts/generar_json.py`.
- **Ciudades pendientes:** mira `docs/pendientes.json`. Para añadir una, agrégala a la tabla `CIUDADES` del script
  (nombre en minúsculas y sin acentos, latitud, longitud, país).
- **Si el script falla:** en *Actions* verás la ejecución en rojo; abre el registro para ver el error.
- GitHub puede desactivar las tareas programadas si el repositorio pasa mucho tiempo sin actividad;
  se reactivan con un clic en la pestaña *Actions*.
- **Probarlo en tu ordenador:** desde la carpeta del proyecto, `python -m http.server 8000` y abre
  `http://localhost:8000/docs/`. Abrir `index.html` con doble clic no funciona: el navegador bloquea la lectura del JSON.

## Qué muestra y qué no

- Se sitúan los datasets con coordenadas (punto o área) o con ciudad. Los que solo tienen país o provincia no tienen un punto concreto y no se dibujan.
- Los borradores y los registros que la API no puede leer (por ejemplo, los recolectados de UPCommons) quedan fuera.
- Las ubicaciones fuera de España se ocultan por defecto y se activan con el interruptor.
