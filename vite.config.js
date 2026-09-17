import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const appAccessPin = env.APP_ACCESS_PIN ?? env.VITE_APP_ACCESS_PIN ?? '';

  return {
    plugins: [sveltekit()],
    define: {
      __APP_ACCESS_PIN__: JSON.stringify(appAccessPin),
    },
    server: {
      proxy: {
        '/api': 'http://127.0.0.1:8000',
      },
    },
  };
});
