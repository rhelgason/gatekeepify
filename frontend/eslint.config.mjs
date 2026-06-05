import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({ baseDirectory: __dirname });

const eslintConfig = [
  ...compat.extends("next/core-web-vitals"),
  {
    rules: {
      "@next/next/no-img-element": "off",
    },
  },
  {
    ignores: [
      ".next/**",
      "out/**",
      "src/**/*.test.ts",
      "src/**/*.test.tsx",
      "vitest.config.ts",
    ],
  },
];

export default eslintConfig;
