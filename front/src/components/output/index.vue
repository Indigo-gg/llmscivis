<template>
  <div class="output-wrapper">
    <v-row class="output-row">
      <!-- Console Output -->
      <v-col cols="12" md="6" class="output-col">
        <div class="minimal-card">
          <div class="card-header">
            <span class="card-title">Console Output</span>
          </div>
          <div class="card-body">
            <div v-if="filteredLogs.length > 0" class="console-list">
              <div v-for="(log, index) in filteredLogs" :key="index" class="log-item">
                <span class="log-time">{{ formatTimestamp(log.timestamp) }}</span>
                <span class="log-type" :class="log.type">[{{ log.type.toUpperCase() }}]</span>
                <pre class="log-msg">{{ log.message }}</pre>
              </div>
            </div>
            <div v-else class="empty-hint">No console output</div>
          </div>
        </div>
      </v-col>

      <!-- Evaluator Output -->
      <v-col cols="12" md="6" class="output-col">
        <div class="minimal-card">
          <div class="card-header">
            <span class="card-title">Evaluator Output</span>
          </div>
          <div class="card-body">
            <!-- Structured evaluation display -->
            <div v-if="parsedEvaluation && parsedEvaluation.overall !== null" class="eval-content">
              <!-- Overall Score -->
              <!-- <div class="eval-overall">
                <span class="eval-label">Overall Score</span>
                <span class="eval-score">{{ convertToHundredScale(parsedEvaluation.overall) }}</span>
              </div> -->

              <!-- Dimension Scores with Reasons -->
              <div class="eval-dimensions">
                <div v-for="(dimData, dimName) in parsedEvaluation.dimensions" :key="dimName" class="eval-dim-item">
                  <div class="dim-header">
                    <span class="dim-name">{{ formatDimensionName(dimName) }}</span>
                    <span class="dim-score">{{ convertToHundredScale(dimData.score) }}</span>
                  </div>
                  <div v-if="dimData.reason" class="dim-reason">{{ dimData.reason }}</div>
                </div>
              </div>

              <!-- Critique -->
              <div v-if="parsedEvaluation.critique" class="eval-critique">
                <div class="critique-label">Assessment</div>
                <div class="critique-text">{{ parsedEvaluation.critique }}</div>
              </div>
            </div>

            <!-- Fallback to Markdown -->
            <div v-else-if="evaluatorOutput && evaluatorOutput.trim()" class="markdown-content" v-html="parseMarkdown(evaluatorOutput)"></div>
            
            <!-- Empty state -->
            <div v-else class="empty-hint">No evaluation results</div>
          </div>
        </div>
      </v-col>
    </v-row>
  </div>
</template>

<script>
import { marked } from "marked";
import { ref, computed } from "vue";
import { convertToHundredScale } from "@/utils/scoreUtils.js";

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
    parsedEvaluation: {
      type: Object,
      required: false,
      default: null
    }
  },
  emits: ['export-results'],
  setup(props) {
    const filteredLogs = computed(() => {
      return Array.isArray(props.consoleOutput) ? props.consoleOutput : [];
    });

    const formatTimestamp = (timestamp) => {
      const date = new Date(timestamp);
      return date.toLocaleTimeString();
    };

    const parseMarkdown = (markdown) => {
      if (!markdown) return "";
      return marked.parse(markdown);
    };

    const formatDimensionName = (name) => {
      return name.replace(/([A-Z])/g, ' $1').trim();
    };

    return {
      filteredLogs,
      formatTimestamp,
      parseMarkdown,
      formatDimensionName,
      convertToHundredScale
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

.output-col {
  padding: 4px 6px;
}

/* 极简卡片样式 - 无边框 */
.minimal-card {
  background: #ffffff;
  border: none;
  border-radius: 0;
}

.card-header {
  padding: 8px 12px;
  border-bottom: 1px solid #e2e8f0;
  background-color: #f8fafc;
}

.card-title {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.card-body {
  padding: 8px 12px;
}

/* 空状态 - 极简 */
.empty-hint {
  color: #94a3b8;
  font-size: 12px;
  text-align: center;
  padding: 12px 0;
}

/* Console 日志列表 */
.console-list {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  line-height: 1.6;
}

.log-item {
  display: grid;
  grid-template-columns: 90px 65px 1fr;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px solid #f0f0f0;
  align-items: start;
}

.log-item:last-child {
  border-bottom: none;
}

.log-time {
  color: #999;
  flex-shrink: 0;
  width: 90px;
}

.log-type {
  flex-shrink: 0;
  font-weight: 500;
  width: 65px;
}

.log-type.error { color: #e53935; }
.log-type.warn { color: #fb8c00; }
.log-type.info { color: #1e88e5; }
.log-type.log { color: #43a047; }

.log-msg {
  color: #333;
  word-break: break-word;
  white-space: pre-wrap;
  margin: 0;
  font-family: inherit;
}

/* Evaluator 评估内容 */
.eval-content {
  font-size: 13px;
  line-height: 1.6;
}

.eval-overall {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 12px;
  margin-bottom: 12px;
  background: #f8fafc;
  border-radius: 0;
  border: 1px solid #e2e8f0;
}

.eval-label {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  letter-spacing: 0.5px;
}

.eval-score {
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1;
}

.eval-dimensions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.eval-dim-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 0;
  border: 1px solid #e2e8f0;
  transition: none;
}

.eval-dim-item:hover {
  background: #f8fafc;
  transform: none;
}

.dim-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.dim-name {
  font-size: 11px;
  font-weight: 500;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.dim-score {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
}

.dim-reason {
  font-size: 12px;
  color: #475569;
  line-height: 1.6;
  padding-top: 4px;
  border-top: 1px solid #e2e8f0;
}

.eval-critique {
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 0;
  margin-top: 12px;
}

.critique-label {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.critique-text {
  color: #334155;
  line-height: 1.7;
  font-size: 13px;
}

/* Markdown 内容 */
.markdown-content {
  font-size: 13px;
  line-height: 1.6;
  color: #333;
}
</style>