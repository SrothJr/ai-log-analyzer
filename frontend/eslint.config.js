import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import react from "eslint-plugin-react";
import reactRefresh from "eslint-plugin-react-refresh";

export default [
  { ignores: ["dist"] },
  js.configs.recommended,
  {
    files: ["**/*.{js,jsx}"],
    languageOptions: { ecmaVersion: 2020, sourceType: "module", parserOptions: { ecmaFeatures: { jsx: true } }, globals: { window: "readonly", document: "readonly", fetch: "readonly", FormData: "readonly", setTimeout: "readonly", clearTimeout: "readonly" } },
    plugins: { react, "react-hooks": reactHooks, "react-refresh": reactRefresh },
    rules: { ...reactHooks.configs.recommended.rules, "react/jsx-uses-vars": "error", "react-refresh/only-export-components": "warn" },
  },
];
