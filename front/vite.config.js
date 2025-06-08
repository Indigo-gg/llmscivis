import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import ViteMonacoPlugin from 'vite-plugin-monaco-editor';
import path from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue(),  ViteMonacoPlugin.default({})],
  server: {
    host: '0.0.0.0',
    port: 5174
  },
  resolve:{
    alias: {
      '@': path.resolve(__dirname, './src/'),
    }
  }
})
