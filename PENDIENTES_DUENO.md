# Pendientes del dueño — MVD Fútbol

Lo que necesita tu mano. Todo lo demás corre solo.

## 1. Conectar Netlify con el repo (5 minutos, lo único que falta para el 24/7 completo)

Hoy el sitio se publica cuando lo deployo yo desde tu máquina. Para que se publique
solo en cada cambio del cron:

1. Entrá a https://app.netlify.com/projects/mvdfutbol/configuration/deploys
2. **Link repository** → GitHub → autorizá el acceso → elegí `yamanducorte/mvdfutbol`
3. Branch `main`, build command **vacío**, publish directory **`publico`**

No lo hice yo porque autorizar GitHub dentro de Netlify es dar permisos sobre tu
cuenta, y eso no lo toco sin tu OK. Si me decís que sí, lo hago desde tu Chrome.

## 2. El link de los perfumes árabes

El anuncio ya está cargado en `anuncios.json` pero apagado (`activo: false`),
esperando la URL de la tienda o del catálogo. En cuanto me lo pases, se enciende.

## 3. Decidir qué hacemos con VaposVaper

Está apagado a propósito: hay que chequear si la ley antitabaco uruguaya permite
publicitar vapes en un medio. Si querés lo averiguo y te lo paso por escrito.

## 4. Revisar los colores de los escudos

Están en `escudos.json`. Los puse de memoria y seguro hay alguno mal. Corregís el
color en ese archivo y se arregla en todo el sitio. No son los escudos oficiales:
son monogramas propios, porque los escudos de los clubes son marcas registradas.

## 5. Escribirle a Julio Greño (La Movida Online)

Las tablas de juveniles, ascenso y femenino salen de su sitio, con crédito y link
visible. Es un tipo que lo lleva a pulmón. Proponerle intercambio —vos le mandás
tráfico, él te deja usar los datos tranquilo— es lo correcto y además te cubre.
Te escribo el mensaje cuando quieras, pero lo mandás vos.

---

## Lo que ya está hecho y no requiere nada tuyo

- Sitio online: https://mvdfutbol.netlify.app
- Repo: https://github.com/yamanducorte/mvdfutbol
- Google Search Console verificado, con los dos sitemaps enviados
- Secrets cargados en GitHub (`ANTHROPIC_API_KEY`, `API_FOOTBALL_KEY`)
- 26 campeonatos con tabla: Primera, juveniles, ascenso y femenino
- Los 25 canales de YouTube cargados y escuchándose
