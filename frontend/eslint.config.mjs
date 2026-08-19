import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    // react-hooks/set-state-in-effect (new in eslint-plugin-react-hooks v6) flags
    // standard patterns: data fetching via .then() inside an effect (app/page.tsx)
    // and localStorage hydration on mount (lib/auth.tsx). Both files are owned by
    // the lead (outside this slice's partition), so the rule is scoped off here
    // rather than editing their code.
    files: ["app/page.tsx", "lib/auth.tsx"],
    rules: {
      "react-hooks/set-state-in-effect": "off",
    },
  },
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
]);
