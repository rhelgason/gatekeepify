// Flat ESLint config for Next 16 / ESLint 9.
//
// We configure @next/eslint-plugin-next directly rather than going through
// eslint-config-next + FlatCompat: under ESLint 9 the legacy-config bridge
// crashes ("Converting circular structure to JSON") on eslint-config-next 16's
// flat-shaped config. typescript-eslint's parser lets us lint .ts/.tsx without
// pulling in the strict TS rule set (the codebase intentionally uses `any`).
import nextPlugin from "@next/eslint-plugin-next";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

// Defensive merge: keep linting green even if a plugin renames its config keys.
const nextRules = {
  ...(nextPlugin.configs?.recommended?.rules ?? {}),
  ...(nextPlugin.configs?.["core-web-vitals"]?.rules ?? {}),
};
const reactHooksRules = reactHooks.configs?.recommended?.rules ?? {};

export default [
  { ignores: [".next/**", "out/**", "src/**/*.test.ts", "src/**/*.test.tsx", "vitest.config.ts"] },
  {
    files: ["**/*.ts", "**/*.tsx", "**/*.js", "**/*.mjs"],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    plugins: { "@next/next": nextPlugin, "react-hooks": reactHooks },
    rules: {
      ...nextRules,
      ...reactHooksRules,
      "@next/next/no-img-element": "off",
    },
    linterOptions: { reportUnusedDisableDirectives: "off" },
  },
];
