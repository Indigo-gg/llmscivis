<template>
  <div class="output-wrapper">
    <v-row class="output-row">
      <v-col cols="12" md="6" class="console-col">
        <v-card variant="tonal" class="output-card">
          <v-card-title class="d-flex align-center" style="padding: var(--spacing-md) var(--spacing-lg);">
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
              <p class="empty-text">No console output</p>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="6" class="evaluator-col">
        <v-card variant="tonal" class="output-card">
          <div class="evaluator-header" style="padding: var(--spacing-md) var(--spacing-lg);">
            <v-card-title class="flex-grow-1" style="padding: 0;">Evaluator Output</v-card-title>
            <v-btn 
              icon="mdi-download" 
              size="x-small" 
              variant="text"
              title="Export Evaluation Results"
              class="export-btn"
              @click="$emit('export-results')"
            >
              <v-icon>mdi-download</v-icon>
            </v-btn>
          </div>
          <v-card-text class="evaluator-content">
            <!-- Structured evaluation display when parsedEvaluation is available -->
            <div v-if="parsedEvaluation && parsedEvaluation.overall !== null" class="structured-evaluation">
              <!-- Overall Assessment Section -->
              <div class="overall-assessment">
                <div class="assessment-header">
                  <v-icon size="small" color="primary" class="mr-2">mdi-clipboard-text</v-icon>
                  <span class="assessment-title">Overall Assessment</span>
                </div>
                <div class="assessment-content">
                  {{ parsedEvaluation.critique || 'No critique provided' }}
                </div>
              </div>

              <v-divider class="my-4"></v-divider>

              <!-- Radar Chart Section -->
              <div class="radar-chart-section">
                <div class="section-title">
                  <v-icon size="small" class="mr-1" color="#4a5568">mdi-chart-radar</v-icon>
                  Model Evaluation
                </div>
                <div class="radar-chart-wrapper">
                  <div class="radar-chart-container">
                    <canvas ref="radarChart" width="400" height="300" style="max-width: 100%; height: auto;"></canvas>
                  </div>
                </div>
              </div>

              <v-divider class="my-4"></v-divider>

              <!-- Detailed Breakdown Section -->
              <div class="detailed-breakdown">
                <div class="breakdown-title">Detailed Breakdown</div>
                <v-expansion-panels variant="accordion" class="mt-2">
                  <v-expansion-panel
                    v-for="(dimData, dimName) in parsedEvaluation.dimensions"
                    :key="dimName"
                    elevation="0"
                  >
                    <v-expansion-panel-title>
                      <div class="dimension-header">
                        <v-icon size="small" color="#6b7280" class="mr-2">
                          {{ getDimensionIcon(dimName) }}
                        </v-icon>
                        <span class="dimension-name">{{ formatDimensionName(dimName) }}</span>
                        <v-spacer></v-spacer>
                        <v-chip
                          size="small"
                          color="#6b7280"
                          variant="flat"
                          class="score-chip"
                          text-color="white"
                        >
                          {{ convertToHundredScale(dimData.score) }}
                        </v-chip>
                      </div>
                    </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <div class="dimension-reason">
                        {{ dimData.reason || 'No reason provided' }}
                      </div>
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                </v-expansion-panels>
              </div>
            </div>

            <!-- Fallback to Markdown rendering for non-structured data -->
            <div v-else-if="evaluatorOutput && evaluatorOutput.trim()" class="markdown-container" v-html="parseMarkdown(evaluatorOutput)"></div>
            
            <!-- Empty state -->
            <div v-else class="empty-state">
              <v-icon size="48" color="grey-lighten-1">mdi-clipboard-text</v-icon>
              <p class="empty-text">No evaluation results</p>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script>
import { marked } from "marked";
import { ref, computed, watch, nextTick, onMounted } from "vue";
import Chart from "chart.js/auto";
import { convertToHundredScale, getScoreColor } from "@/utils/scoreUtils.js";

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
    },
    parsedEvaluation: {  // New: Parsed evaluation data
      type: Object,
      required: false,
      default: null
    }
  },
  emits: ['export-results'],
  setup(props) {
    const selectedLogLevel = ref('all');
    const consoleContainer = ref(null);
    const radarChart = ref(null);
    const radarChartInstance = ref(null);

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

    // Format dimension name for display
    const formatDimensionName = (name) => {
      // Convert CamelCase to separate words
      return name.replace(/([A-Z])/g, ' $1').trim();
    };

    // Get icon for each dimension
    const getDimensionIcon = (name) => {
      const iconMap = {
        'Functionality': 'mdi-cog',
        'VisualQuality': 'mdi-palette',
        'CodeQuality': 'mdi-code-tags'
      };
      return iconMap[name] || 'mdi-chart-box';
    };

    // Draw radar chart with Chart.js
    const drawRadarChart = async () => {
      if (!props.parsedEvaluation || !props.parsedEvaluation.dimensions) return;

      // Wait for DOM to be ready
      await nextTick();
      
      // Check if canvas element exists
      if (!radarChart.value) {
        console.warn('Canvas element not found, retrying in next tick');
        await new Promise(resolve => setTimeout(resolve, 100));
        if (!radarChart.value) {
          console.error('Canvas element still not found');
          return;
        }
      }

      const dims = props.parsedEvaluation.dimensions;
      const labels = Object.keys(dims);
      if (labels.length === 0) return;
      
      const scores = labels.map(key => convertToHundredScale(dims[key].score, 0) || 0);
      const chartLabels = labels.map(label => formatDimensionName(label));

      // Destroy existing chart if it exists
      if (radarChartInstance.value) {
        radarChartInstance.value.destroy();
        radarChartInstance.value = null;
      }

      // Reset canvas dimensions to ensure proper rendering
      if (radarChart.value) {
        radarChart.value.width = 400;
        radarChart.value.height = 300;
      }

      const ctx = radarChart.value?.getContext('2d');
      if (!ctx) {
        console.error('Failed to get canvas 2D context');
        return;
      }
      radarChartInstance.value = new Chart(ctx, {
        type: 'radar',
        data: {
          labels: chartLabels,
          datasets: [
            {
              label: 'Evaluation Score',
              data: scores,
              borderColor: 'var(--text-primary)',
              backgroundColor: 'rgba(59, 130, 246, 0.1)',
              borderWidth: 2.5,
              pointBackgroundColor: 'var(--primary-color)',
              pointBorderColor: '#fff',
              pointBorderWidth: 2,
              pointRadius: 4,
              pointHoverRadius: 6
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: true,
          plugins: {
            legend: {
              display: false
            },
            tooltip: {
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              padding: 12,
              titleFont: { size: 13 },
              bodyFont: { size: 12 },
              borderColor: 'var(--primary-color)',
              borderWidth: 1,
              callbacks: {
                label: function(context) {
                  return context.label + ': ' + context.parsed.r;
                }
              }
            }
          },
          scales: {
            r: {
              min: 0,
              max: 100,
              ticks: {
                stepSize: 20,
                font: { size: 11 },
                color: '#999',
                callback: function(value) {
                  return value;
                }
              },
              grid: {
                color: 'var(--border-color)',
                drawBorder: false
              },
              pointLabels: {
                font: { size: 12, weight: 'bold' },
                color: 'var(--text-primary)',
                padding: 8
              }
            }
          }
        }
      });
    };

    // Watch for data changes and redraw chart
    watch(() => props.parsedEvaluation, () => {
      drawRadarChart();
    }, { deep: true });

    onMounted(() => {
      drawRadarChart();
    });

    return {
      selectedLogLevel,
      filteredLogs,
      getLogColor,
      getLogIcon,
      formatTimestamp,
      parseMarkdown,
      formatDimensionName,
      getDimensionIcon,
      convertToHundredScale,
      getScoreColor,
      consoleContainer,
      radarChart,
      radarChartInstance
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
  padding: var(--spacing-sm);
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
  padding: var(--spacing-md);
}

.evaluator-header {
  display: flex;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  gap: var(--spacing-sm);
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
  background-color: var(--secondary-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: var(--spacing-sm);
  color: var(--text-primary);
}

.log-entry {
  padding: var(--spacing-xs) var(--spacing-sm);
  margin: 2px 0;
  border-radius: var(--radius-sm);
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
  color: var(--text-secondary);
  font-size: 0.85em;
  margin-right: var(--spacing-sm);
}

.log-message {
  flex: 1;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xxl) var(--spacing-lg);
  min-height: 150px;
}

.empty-text {
  margin-top: var(--spacing-md);
  font-size: 14px;
  color: var(--disabled-color);
}

/* Structured Evaluation Styles */
.structured-evaluation {
  text-align: left;
  overflow: auto;
  max-height: 300px;
}

.overall-assessment {
  background-color: var(--secondary-bg);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  border-left: 3px solid var(--text-secondary);
}

.assessment-header {
  display: flex;
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.assessment-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
}

.assessment-content {
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary);
  font-style: italic;
}

.detailed-breakdown {
  margin-top: var(--spacing-sm);
  background-color: var(--secondary-bg);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
}

.breakdown-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
  margin-bottom: var(--spacing-md);
  padding-left: var(--spacing-sm);
  border-left: 3px solid var(--text-secondary);
}

.dimension-header {
  display: flex;
  align-items: center;
  width: 100%;
}

.dimension-name {
  font-weight: 500;
  font-size: 14px;
}

.score-chip {
  font-weight: 600;
}

.dimension-reason {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-secondary);
  padding: var(--spacing-sm) 0;
}

/* Radar Chart Styles */
.radar-chart-section {
  margin: var(--spacing-md) 0;
}

.section-title {
  display: flex;
  align-items: center;
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
  padding-left: var(--spacing-sm);
  border-left: 3px solid var(--text-secondary);
}

.radar-chart-wrapper {
  margin: var(--spacing-md) 0;
  background-color: var(--background-color);
  width: 100%;
  height: 300px;
  border-radius: var(--radius-md);
  display: flex;
  justify-content: center;
  box-shadow: var(--shadow-light);
}

.radar-chart-container {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: auto;
}

.radar-chart-container canvas {
  max-width: 60%;
  height: auto;
  background-color: var(--background-color);
}
</style>