# Pendientes del dueño — MVD Fútbol

Lo que necesita tu mano. Todo lo demás corre solo.

## 1. Cargar el secret de la línea editorial  ← esto frena las notas

Mientras no esté cargado, **el robot no escribe ninguna nota**. Es a propósito:
preferimos quedarnos sin notas antes que publicar una que no correspondía.

En `https://github.com/yamanducorte/mvdfutbol/settings/secrets/actions` →
*New repository secret*:

- **Name:** `CLUBES_DE_LA_CASA`
- **Secret:** los clubes separados por comas, tal como figuran en tu `.env` local

No va en un archivo del repo porque el repo es público y cualquiera lo leería.
En tu máquina ya está, en `.env`, que git ignora.

## 3. El link de los perfumes árabes

El anuncio ya está cargado en `anuncios.json` pero apagado (`activo: false`),
esperando la URL de la tienda o del catálogo. En cuanto me lo pases, se enciende.

## 4. Decidir qué hacemos con VaposVaper

Está apagado a propósito: hay que chequear si la ley antitabaco uruguaya permite
publicitar vapes en un medio. Si querés lo averiguo y te lo paso por escrito.

## 5. Revisar los colores de los escudos

Están en `escudos.json`. Los puse de memoria y seguro hay alguno mal. Corregís el
color en ese archivo y se arregla en todo el sitio. No son los escudos oficiales:
son monogramas propios, porque los escudos de los clubes son marcas registradas.

## 6. Escribirle a La Movida Online

Las tablas de juveniles, tercera, femenino y ascenso salen de su sitio, con
crédito y link visible en cada tabla. Proponerles un intercambio —vos les mandás
tráfico, ellos te dejan usar los datos tranquilo— es lo correcto y además te
cubre. Te escribo el mensaje cuando quieras, pero lo mandás vos.

Lo que dice su propia página de contacto, verificado el 2026-11-03:

> "Somos un grupo de periodistas y fotógrafos independientes amantes del deporte
> que tratamos de aportar desde hace años nuestro granito de arena para que el
> deporte Uruguayo siga en constante crecimiento. Esta tarea la llevamos adelante
> en nuestros tiempos libres y sin recibir ninguna remuneración."

No publican ningún nombre propio. El correo es **gerencia@lamovidaonline.net**.

(En una versión anterior de este archivo yo había puesto un nombre de persona
como contacto. Era inventado: no figura en ninguna parte del sitio ni en ninguna
fuente. Queda anotado para que nadie lo vuelva a dar por bueno.)

## 7. Cuando quieras: dominio propio

Hoy la dirección es `yamanducorte.github.io/mvdfutbol`, que depende de GitHub y
tiene tu nombre en vez del de la marca. Un `.com` sale unos US$ 12 al año y lo
apuntás a GitHub Pages sin costo extra. El día que lo tengas, en `scripts/sitio.py`
se cambia `DOMINIO` y se deja `BASE = ""`: el sitio queda igual pero en la raíz.
Conviene hacerlo antes de que Google indexe mucho, porque cada mudanza de
dirección cuesta posicionamiento.

## 2. (Resuelto) Los transcriptos los baja tu PC

**Ya está hecho y andando, no requiere nada tuyo.** Hay una tarea programada en
Windows, *"MVD Fútbol - bajar transcriptos"*, que cada hora al minuto 20 baja los
transcriptos nuevos de YouTube y los sube al repo. La nube sigue haciendo todo lo
demás: filtrar, escribir las notas, publicar el sitio y las tablas.

Con la máquina apagada no entran noticias nuevas, pero no se pierde nada: al
prenderla se pone al día hasta 7 días para atrás. Si querés ver qué hizo:

    python scripts/subir_transcriptos.py --ver

El motivo de todo esto: YouTube bloquea a las máquinas de GitHub:
probado el 2026-11-02 con un video nuestro y con uno famoso que nunca habíamos
pedido. Al primero no lo deja ni consultar (*"Iniciá sesión para confirmar que no
sos un robot"*), y del segundo no deja bajar los subtítulos (*429 Too Many
Requests*). Desde tu PC los mismos videos bajan en dos segundos.

Esto afecta **solo a las noticias**. Las tablas salen de La Movida Online y de
Wikipedia, que no bloquean nada, y siguen actualizándose solas en la nube.

Si algún día querés que no dependa de tu PC, la alternativa es pagar un proxy
con IP de casa, unos US$ 5 a 15 por mes. Descartada queda pasarle las cookies de
tu cuenta de YouTube: es tu cuenta de Google expuesta a un repositorio público,
caduca cada pocas semanas y te la pueden bloquear.

---

## Lo que ya está hecho y no requiere nada tuyo

- Sitio online: https://yamanducorte.github.io/mvdfutbol/
- Repo: https://github.com/yamanducorte/mvdfutbol
- **Publicación automática**: los workflows generan y publican en GitHub Pages
  solos. Gratis y sin límite de deploys. Ya no hay que deployar desde tu PC.
- Secrets cargados en GitHub (`ANTHROPIC_API_KEY`, `API_FOOTBALL_KEY`)
- 26 campeonatos con tabla: Primera, juveniles, ascenso y femenino
- Los 25 canales de YouTube cargados y escuchándose
- **Videos sin subtítulos**: se saltean. Son pocos y casi siempre YouTube les
  genera los subtítulos un rato más tarde, y ahí entran solos.
- **Arreglado un error que costaba notas**: cuando YouTube frenaba el pedido por
  abuso, el código lo leía como "este video no tiene subtítulos" y lo tiraba para
  siempre. Ahora distingue las dos cosas y reintenta.
- **Línea editorial**: de los clubes de la casa no se publica nada que los
  perjudique. El filtro no extrae esos hechos, así que el redactor nunca los ve.
  Lo bueno y lo neutro sale normal, y no se maquilla ni se inventa a favor: lo que
  no se puede publicar se omite. La lista está en el secret, no en el repo.

## Por qué nos fuimos de Netlify (2026-11-02)

Netlify cobra **15 créditos por cada deploy de producción** y tu plan Personal
(US$ 9/mes) trae 1.000 créditos mensuales: unos 66 deploys para todos tus sitios
juntos. Este diario se actualiza cada 20 minutos, o sea unos 72 deploys por día.
Era imposible: el mes se agotaba en horas. De hecho el ciclo del 17/10 al 16/11 ya
se consumió entero (1.034 de 1.000) y Netlify pausó los deploys de **todas** tus
páginas hasta el 16 de noviembre.

GitHub Pages no cobra por deploy cuando se publica con un workflow de Actions, y
para un repo público los minutos de Actions también son gratis.

**Tus otros sitios siguen en Netlify** y así tienen que quedarse: parfumarabes y
vaposvaper venden, y los términos de GitHub Pages prohíben usarlo como hosting
gratuito de una tienda; además parfumarabes, vaposvaper y elvideoanalista usan
los formularios de Netlify, que GitHub no tiene. Sacando el diario, los 1.000
créditos mensuales te sobran para esos nueve sitios, que cambian poco.
