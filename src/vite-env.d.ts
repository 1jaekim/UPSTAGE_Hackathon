/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_HARNESS_ENDPOINT: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
