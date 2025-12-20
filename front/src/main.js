import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import "vuetify/styles";
import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import * as directives from "vuetify/directives";
import "vuetify/dist/vuetify.min.css";
import "@mdi/font/css/materialdesignicons.css";

import router from "@/routers/index.js";
const vuetify = createVuetify({
    components,
    directives,
    theme: {
        defaultTheme: 'light',
        themes: {
            light: {
                dark: false,
                colors: {
                    primary: '#3b82f6',
                    secondary: '#6b7280',
                    success: '#10b981',
                    warning: '#f59e0b',
                    error: '#ef4444',
                    info: '#3b82f6',
                    background: '#ffffff',
                    surface: '#f8fafc',
                },
            },
        },
    },
});
createApp(App).use(vuetify).use(router).mount('#app')
