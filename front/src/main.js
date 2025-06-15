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
});
createApp(App).use(vuetify).use(router).mount('#app')
