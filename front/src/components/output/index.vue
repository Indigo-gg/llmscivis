<template>
  <div class="output-wrapper">
    <v-row class="output-row">
      <v-col cols="12" md="6" class="console-col">
        <v-card variant="tonal" class="output-card">
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
          <v-card-text class="console-content">
            <div v-if="filteredLogs.length > 0" class="console-container" ref="consoleContainer">
              <div v-for="(log, index) in filteredLogs" :key="index" class="log-entry" :class="log.type">
                <v-icon :color="getLogColor(log.type)" size="small" class="mr-2">{{ getLogIcon(log.type) }}</v-icon>
                <span class="log-timestamp">{{ formatTimestamp(log.timestamp) }}</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
            <div v-else class="empty-state">
              <v-icon size="48" color="grey-lighten-1">mdi-console</v-icon>
              <p class="empty-text">暂无控制台输出</p>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="6" class="evaluator-col">
        <v-card variant="tonal" class="output-card">
          <div class="evaluator-header">
            <v-card-title class="flex-grow-1">Evaluator Output</v-card-title>
            <v-btn 
              icon="mdi-download" 
              size="x-small" 
              variant="text"
              title="导出评估结果"
              class="export-btn"
              @click="$emit('export-results')"
            >
              <v-icon>mdi-download</v-icon>
            </v-btn>
          </div>
          <v-card-text class="evaluator-content">
            <div v-if="evaluatorOutput && evaluatorOutput.trim()" class="markdown-container" v-html="parseMarkdown(evaluatorOutput)"></div>
            <div v-else class="empty-state">
              <v-icon size="48" color="grey-lighten-1">mdi-clipboard-text</v-icon>
              <p class="empty-text">暂无评估结果</p>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
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
      required: false,
      default: ""
    }
  },
  emits: ['export-results'],
  setup(props) {
    const selectedLogLevel = ref('all');
    const consoleContainer = ref(null);

    const filteredLogs = computed(() => {
      const logs = Array.isArray(props.consoleOutput) ? props.consoleOutput : [];
      console.log('consoleOutput:', logs);
      if (selectedLogLevel.value === 'all') {
        return logs;
      }
      const filteredLogs = logs.filter(log => log.type === selectedLogLevel.value);
      return filteredLogs;
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
.output-wrapper {
  width: 100%;
  padding: 0;
}

.output-row {
  margin: 0;
}

.console-col,
.evaluator-col {
  padding: 8px;
}

.output-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.console-content,
.evaluator-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.evaluator-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  gap: 8px;
}

.evaluator-header .v-card-title {
  margin: 0;
  padding: 0;
}

.export-btn {
  flex-shrink: 0;
}

.v-card-text {
  white-space: pre-wrap;
}

.markdown-container {
  text-align: left;
  overflow: auto;
  max-height: 300px;
}

.console-container {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  text-align: left;
  overflow: auto;
  flex: 1;
  background-color: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 8px;
  color: #333333;
}

.log-entry {
  padding: 4px 8px;
  margin: 2px 0;
  border-radius: 4px;
  display: flex;
  align-items: center;
}

.log-entry.error {
  background-color: rgba(244, 67, 54, 0.05);
}

.log-entry.warn {
  background-color: rgba(255, 152, 0, 0.05);
}

.log-entry.info {
  background-color: rgba(3, 169, 244, 0.05);
}

.log-entry.log {
  background-color: rgba(76, 175, 80, 0.05);
}

.log-timestamp {
  color: #666;
  font-size: 0.85em;
  margin-right: 8px;
}

.log-message {
  flex: 1;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  min-height: 150px;
}

.empty-text {
  margin-top: 12px;
  font-size: 14px;
  color: #9e9e9e;
}
</style>