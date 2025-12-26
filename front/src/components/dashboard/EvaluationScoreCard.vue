<template>
  <div class="evaluation-score-card">
    <!-- Generation Loading State -->
    <div v-if="isGenerating" class="generation-loading-state">
      <v-progress-circular
        indeterminate
        size="48"
        width="5"
        color="primary"
      ></v-progress-circular>
      <p class="generation-loading-text">Generating Code...</p>
    </div>

    <!-- Top Section: Overall Score + Automated Checks Badges -->
    <div v-else class="top-section">
      <div class="overall-score" :class="{ 'unscored': displayOverallScore === 0 }" :style="displayOverallScore === 0 ? { color: 'var(--disabled-color)' } : { color: overallScoreColor }">
        {{ displayOverallScore || 'N/A' }}
      </div>
      <div class="score-label">Overall Score</div>
      
      <!-- Automated Checks Badges -->
      <div class="badges-container" v-if="checkStatus !== 'idle'">
        <v-chip
          size="small"
          :color="checkStatus === 'loading' ? 'warning' : 'success'"
          variant="flat"
          class="mr-2"
        >
          <v-icon start size="small">{{ checkStatus === 'loading' ? 'mdi-timer-sand' : 'mdi-check-circle' }}</v-icon>
          {{ checkStatus === 'loading' ? 'Checking' : 'Executable' }}
        </v-chip>
        <v-chip
          size="small"
          :color="checkStatus === 'loading' ? 'warning' : 'success'"
          variant="flat"
        >
          <v-icon start size="small">{{ checkStatus === 'loading' ? 'mdi-timer-sand' : 'mdi-code-braces-box' }}</v-icon>
          {{ checkStatus === 'loading' ? 'Validating' : 'Valid' }}
        </v-chip>
      </div>
    </div>

    <v-divider class="my-3"></v-divider>

    <!-- Manual Evaluation Section -->
    <div class="manual-evaluation-section">
      <div class="manual-form">
          <!-- Correction Cost Slider -->
          <div class="slider-group">
            <div class="slider-header">
              <span class="slider-label">Correction Cost</span>
              <span class="slider-value">{{ manualCorrectionCost }}</span>
            </div>
            <v-slider
              v-model="manualCorrectionCost"
              :min="0"
              :max="100"
              :step="1"
              color="#10b981"
              track-color="#d1fae5"
              thumb-size="14"
              hide-details
            ></v-slider>
            <div class="slider-hint">Modified Lines / Total Lines</div>
          </div>

          <!-- Functionality Rating Slider -->
          <div class="slider-group">
            <div class="slider-header">
              <span class="slider-label">Functionality Rating</span>
              <span class="slider-value">{{ manualFunctionality }}</span>
            </div>
            <v-slider
              v-model="manualFunctionality"
              :min="0"
              :max="100"
              :step="1"
              color="#3b82f6"
              track-color="#dbeafe"
              thumb-size="14"
              hide-details
            ></v-slider>
            <div class="slider-hint">Missing Features ← → Complete</div>
          </div>

          <!-- Visual Quality Rating Slider -->
          <div class="slider-group">
            <div class="slider-header">
              <span class="slider-label">Visual Quality Rating</span>
              <span class="slider-value">{{ manualVisualQuality }}</span>
            </div>
            <v-slider
              v-model="manualVisualQuality"
              :min="0"
              :max="100"
              :step="1"
              color="#8b5cf6"
              track-color="#ede9fe"
              thumb-size="14"
              hide-details
            ></v-slider>
            <div class="slider-hint">Needs Improvement ← → Excellent</div>
          </div>

          <!-- Code Quality Rating Slider -->
          <div class="slider-group">
            <div class="slider-header">
              <span class="slider-label">Code Quality Rating</span>
              <span class="slider-value">{{ manualCodeQuality }}</span>
            </div>
            <v-slider
              v-model="manualCodeQuality"
              :min="0"
              :max="100"
              :step="1"
              color="#f59e0b"
              track-color="#fef3c7"
              thumb-size="14"
              hide-details
            ></v-slider>
            <div class="slider-hint">Obfuscated ← → Readable</div>
          </div>
        </div>
      </div>

    <!-- Export Button -->
    <v-btn
      variant="flat"
      color="#3b82f6"
      :loading="isExporting"
      block
      @click="handleExportResults"
      class="mt-4 export-btn"
    >
      <v-icon start>mdi-download</v-icon>
      Export Results
    </v-btn>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue';
import { convertToHundredScale, getScoreColor } from '@/utils/scoreUtils';

export default {
  name: 'EvaluationScoreCard',
  props: {
    score: {
      type: [String, Number],
      required: false,
      default: ''
    },
    evaluation: {
      type: String,
      required: false,
      default: ''
    },
    parsedEvaluation: {
      type: Object,
      required: false,
      default: null
    },
    automatedChecks: {
      type: Object,
      required: false,
      default: null
    },
    manualEvaluation: {
      type: Object,
      required: false,
      default: null
    },
    evalId: {
      type: [String, Number],
      required: false,
      default: ''
    },
    isLoading: {
      type: Boolean,
      default: false
    },
    isGenerating: {
      type: Boolean,
      default: false
    }
  },
  emits: ['export-results'],
  setup(props, { emit }) {

    // Check status management
    const checkStatus = ref('idle'); // idle, loading, passed, failed

    // Manual evaluation form state
    const manualCorrectionCost = ref(0);
    const manualFunctionality = ref(50);
    const manualVisualQuality = ref(50);
    const manualCodeQuality = ref(50);
    const isManualSubmitting = ref(false);
    const isExporting = ref(false);

    // Computed properties
    const hasScore = computed(() => {
      return props.score !== '' && props.score !== null && props.score !== undefined;
    });

    const hasParsedEvaluation = computed(() => {
      return props.parsedEvaluation && 
             props.parsedEvaluation.dimensions && 
             Object.keys(props.parsedEvaluation.dimensions).length > 0;
    });

    const displayOverallScore = computed(() => {
      if (hasParsedEvaluation.value && props.parsedEvaluation.overall !== null) {
        return convertToHundredScale(props.parsedEvaluation.overall, 0) || 0;
      }
      if (hasScore.value) {
        return convertToHundredScale(props.score, 0) || 0;
      }
      return 0;
    });

    const overallScoreColor = computed(() => {
      return getScoreColor(displayOverallScore.value, true);
    });

    const scoreLevel = computed(() => {
      const score = displayOverallScore.value;
      if (score >= 90) return 'Excellent';
      if (score >= 80) return 'Good';
      if (score >= 60) return 'Pass';
      return 'Fail';
    });

    // Methods
    const handleExportResults = () => {
      isExporting.value = true;
      emit('export-results');
      setTimeout(() => {
        isExporting.value = false;
      }, 1000);
    };

    // Watch for manual evaluation data and load it
    watch(() => props.manualEvaluation, (newVal) => {
      if (newVal) {
        manualCorrectionCost.value = newVal.correctionCost || 0;
        manualFunctionality.value = newVal.functionality || 50;
        manualVisualQuality.value = newVal.visualQuality || 50;
        manualCodeQuality.value = newVal.codeQuality || 50;
      }
    }, { immediate: true });

    // Watch for generated code and update check status
    watch(() => props.isLoading, (newVal) => {
      if (newVal) {
        // When code is being generated, set status to loading
        checkStatus.value = 'loading';
      }
    });

    // Watch for when evaluation completes
    watch(() => props.parsedEvaluation, (newVal) => {
      if (newVal && !props.isLoading) {
        // When evaluation is complete, set status to passed
        checkStatus.value = 'passed';
      }
    }, { deep: true });

    return {
      checkStatus,
      manualCorrectionCost,
      manualFunctionality,
      manualVisualQuality,
      manualCodeQuality,
      isExporting,
      hasScore,
      hasParsedEvaluation,
      displayOverallScore,
      overallScoreColor,
      scoreLevel,
      handleExportResults
    };
  }
}
</script>

<style scoped>
.evaluation-score-card {
  height: 100%;
  transition: background-color 0.3s ease;
}

.card-title {
  font-size: 18px;
  font-weight: 500;
  padding: 16px;
  border-bottom: 1px solid #e0e0e0;
}

.card-content {
  padding: 12px;
  overflow-y: auto;
}

.top-section {
  text-align: center;
  padding: 12px 0;
}

.overall-score {
  font-size: 52px;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 6px;
}

.overall-score.unscored {
  color: #9e9e9e !important;
}

.score-label {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 10px;
  font-weight: 500;
}

.badges-container {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 12px;
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
  font-size: 16px;
  color: #b0bec5;
}

.manual-evaluation-section {
  padding: 8px 0;
  margin-top: 8px;
}

.manual-form {
  margin-top: 0;
}

.slider-group {
  margin-bottom: 20px;
}

.slider-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 6px;
}

.slider-label {
  font-size: 12px;
  font-weight: 500;
  color: #1e293b;
  letter-spacing: 0.2px;
}

.slider-value {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  min-width: 30px;
  text-align: right;
}

.slider-hint {
  font-size: 10px;
  color: #64748b;
  margin-top: 4px;
  text-align: center;
  letter-spacing: 0.3px;
}

.mb-3 {
  margin-bottom: 12px;
}

.generation-loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 20px;
  min-height: 200px;
}

.generation-loading-text {
  margin-top: 16px;
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.export-btn {
  text-transform: none;
  font-weight: 500;
  letter-spacing: 0.3px;
  box-shadow: none !important;
}

.export-btn:hover {
  background-color: #2563eb !important;
}
</style>
