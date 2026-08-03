import { Html, Head, Main, NextScript } from "next/document";

export default function Document() {
  return (
    <Html lang="es">
      <Head>
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="theme-color" content="#F7F8F6" />
        <meta name="description" content="Prospección comercial local: encuentra negocios que podrían necesitar una web nueva o mejorar su presencia digital." />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
