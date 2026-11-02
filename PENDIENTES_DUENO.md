# Pendientes del dueño — MVD Fútbol

Lo que necesita tu mano. Todo lo demás corre solo.

## 1. El link de los perfumes árabes

El anuncio ya está cargado en `anuncios.json` pero apagado (`activo: false`),
esperando la URL de la tienda o del catálogo. En cuanto me lo pases, se enciende.

## 2. Decidir qué hacemos con VaposVaper

Está apagado a propósito: hay que chequear si la ley antitabaco uruguaya permite
publicitar vapes en un medio. Si querés lo averiguo y te lo paso por escrito.

## 3. Revisar los colores de los escudos

Están en `escudos.json`. Los puse de memoria y seguro hay alguno mal. Corregís el
color en ese archivo y se arregla en todo el sitio. No son los escudos oficiales:
son monogramas propios, porque los escudos de los clubes son marcas registradas.

## 4. Escribirle a Julio Greño (La Movida Online)

Las tablas de juveniles, ascenso y femenino salen de su sitio, con crédito y link
visible. Es un tipo que lo lleva a pulmón. Proponerle intercambio —vos le mandás
tráfico, él te deja usar los datos tranquilo— es lo correcto y además te cubre.
Te escribo el mensaje cuando quieras, pero lo mandás vos.

## 5. Cuando quieras: dominio propio

Hoy la dirección es `yamanducorte.github.io/mvdfutbol`, que depende de GitHub y
tiene tu nombre en vez del de la marca. Un `.com` sale unos US$ 12 al año y lo
apuntás a GitHub Pages sin costo extra. El día que lo tengas, en `scripts/sitio.py`
se cambia `DOMINIO` y se deja `BASE = ""`: el sitio queda igual pero en la raíz.
Conviene hacerlo antes de que Google indexe mucho, porque cada mudanza de
dirección cuesta posicionamiento.

---

## Lo que ya está hecho y no requiere nada tuyo

- Sitio online: https://yamanducorte.github.io/mvdfutbol/
- Repo: https://github.com/yamanducorte/mvdfutbol
- **Publicación automática**: los workflows generan y publican en GitHub Pages
  solos. Gratis y sin límite de deploys. Ya no hay que deployar desde tu PC.
- Secrets cargados en GitHub (`ANTHROPIC_API_KEY`, `API_FOOTBALL_KEY`)
- 26 campeonatos con tabla: Primera, juveniles, ascenso y femenino
- Los 25 canales de YouTube cargados y escuchándose

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
