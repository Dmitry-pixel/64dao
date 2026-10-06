import nextVitals from "eslint-config-next/core-web-vitals";

const config = [
  ...nextVitals,
  {
    rules: {
      "react/no-unescaped-entities": "off",
      // С eslint-config-next 15 правило проверяет каталог app/: обычные <a>
      // на внутренние страницы раньше проходили. Поведение не меняется.
      "@next/next/no-html-link-for-pages": "off",
      // next/image не используется, оптимизатор выключен (аудит 2026-10-06, R001).
      "@next/next/no-img-element": "off",
      // Правило для pages/_document; в App Router шрифт подключается в layout.
      "@next/next/no-page-custom-font": "off",
      // Новые правила React Compiler (eslint-plugin-react-hooks 7): 62 замечания
      // в существующем коде. Это стиль, не поломки; пока предупреждения.
      "react-hooks/refs": "warn",
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/static-components": "warn",
      "react-hooks/purity": "warn",
      "react-hooks/immutability": "warn",
    },
  },
  { ignores: [".next/**", "node_modules/**", "next-env.d.ts"] },
];

export default config;
