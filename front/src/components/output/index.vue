<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-row>
          <v-col cols="6">
            <v-card variant="tonal">
              <v-card-title class="d-flex align-center">
                Console Output
                <v-spacer></v-spacer>
                <v-btn-group variant="outlined" class="ml-1" density="compact">
                  <v-btn :color="selectedLogLevel === 'all' ? 'primary' : undefined" @click="selectedLogLevel = 'all'"
                    size="x-small">All</v-btn>
                  <v-btn :color="selectedLogLevel === 'error' ? 'error' : undefined" @click="selectedLogLevel = 'error'"
                    size="x-small">Error</v-btn>
                  <v-btn :color="selectedLogLevel === 'warn' ? 'warning' : undefined" @click="selectedLogLevel = 'warn'"
                    size="x-small">Warn</v-btn>
                  <v-btn :color="selectedLogLevel === 'info' ? 'info' : undefined" @click="selectedLogLevel = 'info'"
                    size="x-small">Info</v-btn>
                  <v-btn :color="selectedLogLevel === 'log' ? 'success' : undefined" @click="selectedLogLevel = 'log'"
                    size="x-small">Log</v-btn>
                </v-btn-group>
              </v-card-title>
              <v-card-text>
                <div class="console-container" ref="consoleContainer">
                  <div v-for="(log, index) in filteredLogs" :key="index" class="log-entry" :class="log.type">
                    <v-icon :color="getLogColor(log.type)" size="small" class="mr-2">{{ getLogIcon(log.type) }}</v-icon>
                    <span class="log-timestamp">{{ formatTimestamp(log.timestamp) }}</span>
                    <span class="log-message">{{ log.message }}</span>
                  </div>
                </div>
              </v-card-text>
              <v-card-actions>
                <slot name="actions"></slot>
              </v-card-actions>
            </v-card>
          </v-col>
          <v-col cols="6">
            <v-card variant="tonal">
              <v-card-title>Evaluator Output</v-card-title>
              <v-card-text>
                <div class="v-card-text markdown-container" v-html="parseMarkdown(evaluatorOutput)"></div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { marked } from "marked";
import { ref, computed, watch, nextTick } from "vue";

export default {
  name: "index",
  props: {
    consoleOutput: {
      type: Array,
      required: false,
      default: () => []
    },
    evaluatorOutput: {
      type: String,
      required: true,
      default: ""
    },
    triggerErrorAnalysis: {
      type: Function,
      required: true
    }
  },
  setup(props) {
    const selectedLogLevel = ref('all');
    const consoleContainer = ref(null);

    const filteredLogs = computed(() => {
      // nextTick(() => {
      const logs = Array.isArray(props.consoleOutput) ? props.consoleOutput : [];
      console.log('consoleOutput:', logs);
      if (selectedLogLevel.value === 'all') {
        return logs;
      }
      // 创建新的过滤后的数组，而不是修改 logs
      const filteredLogs = logs.filter(log => log.type === selectedLogLevel.value);
      // console.log('filter log:', filteredLogs);
      return filteredLogs;
      // });
      // 确保 consoleOutput 是数组

    });

    watch(() => props.consoleOutput.length, () => {
      nextTick(() => {
        if (consoleContainer.value) {
          consoleContainer.value.scrollTop = consoleContainer.value.scrollHeight;
        }
      });
    });

    const getLogColor = (type) => {
      switch (type) {
        case 'error': return 'error';
        case 'warn': return 'warning';
        case 'info': return 'info';
        case 'log': return 'success';
        default: return 'grey';
      }
    };

    const getLogIcon = (type) => {
      switch (type) {
        case 'error': return 'mdi-alert-circle';
        case 'warn': return 'mdi-alert';
        case 'info': return 'mdi-information';
        case 'log': return 'mdi-check-circle';
        default: return 'mdi-circle';
      }
    };

    const formatTimestamp = (timestamp) => {
      const date = new Date(timestamp);
      return date.toLocaleTimeString();
    };

    const parseMarkdown = (markdown) => {
      if (!markdown) return "";
      return marked.parse(markdown);
    };

    return {
      selectedLogLevel,
      filteredLogs,
      getLogColor,
      getLogIcon,
      formatTimestamp,
      parseMarkdown
    };
  },
};
</script>

<style scoped>
.v-card-text {
  white-space: pre-wrap;
}

.markdown-container {
  text-align: left;
  overflow: auto;
  max-height: 300px;
}

.console-container {
  font-family: monospace;
  text-align: left;
  overflow: auto;
  max-height: 300px;
}

.log-entry {
  padding: 4px 8px;
  margin: 2px 0;
  border-radius: 4px;
  display: flex;
  align-items: center;
}

.log-entry.error {
  background-color: rgba(244, 67, 54, 0.1);
}

.log-entry.warn {
  background-color: rgba(255, 152, 0, 0.1);
}

.log-entry.info {
  background-color: rgba(3, 169, 244, 0.1);
}

.log-entry.log {
  background-color: rgba(76, 175, 80, 0.1);
}

.log-timestamp {
  color: #666;
  font-size: 0.85em;
  margin-right: 8px;
}

.log-message {
  flex: 1;
}
</style>
