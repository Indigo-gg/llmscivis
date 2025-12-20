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
      <div class="section-subtitle">
        <v-icon size="small" class="mr-1">mdi-account-edit</v-icon>
        Manual Evaluation
      </div>
      
      <div class="manual-form">
          <!-- Correction Cost Slider -->
          <div class="slider-group">
            <div class="slider-label">Correction Cost</div>
            <v-slider
              v-model="manualCorrectionCost"
              :min="0"
              :max="100"
              :step="1"
              color="#546e7a"
              density="compact"
            >
              <template v-slot:append>
                <span class="slider-value">{{ manualCorrectionCost }}</span>
              </template>
            </v-slider>
            <div class="slider-hint">Modified Lines / Total Lines</div>
          </div>

          <!-- Functionality Rating Slider -->
          <div class="slider-group">
            <div class="slider-label">Functionality Rating</div>
            <v-slider
              v-model="manualFunctionality"
              :min="0"
              :max="100"
              :step="1"
              color="#546e7a"
              density="compact"
            >
              <template v-slot:append>
                <span class="slider-value">{{ manualFunctionality }}</span>
              </template>
            </v-slider>
            <div class="slider-hint">Missing Features ← → Complete</div>
          </div>

          <!-- Visual Quality Rating Slider -->
          <div class="slider-group">
            <div class="slider-label">Visual Quality Rating</div>
            <v-slider
              v-model="manualVisualQuality"
              :min="0"
              :max="100"
              :step="1"
              color="#546e7a"
              density="compact"
            >
              <template v-slot:append>
                <span class="slider-value">{{ manualVisualQuality }}</span>
              </template>
            </v-slider>
            <div class="slider-hint">Needs Improvement ← → Excellent</div>
          </div>

          <!-- Code Quality Rating Slider -->
          <div class="slider-group">
            <div class="slider-label">Code Quality Rating</div>
            <v-slider
              v-model="manualCodeQuality"
              :min="0"
              :max="100"
              :step="1"
              color="primary"
              density="compact"
            >
              <template v-slot:append>
                <span class="slider-value">{{ manualCodeQuality }}</span>
              </template>
            </v-slider>
            <div class="slider-hint">Obfuscated ← → Readable</div>
          </div>
        </div>
      </div>

    <!-- Save Button -->
    <v-btn
      variant="tonal"
      color="primary"
      :loading="isManualSubmitting"
      block
      @click="submitManualEvaluation"
      class="mt-4"
    >
      <v-icon start>mdi-account-check</v-icon>
      Save Human Evaluation
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
  emits: ['trigger-evaluation', 'submit-manual-evaluation', 'export-results'],
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


    const submitManualEvaluation = () => {
      isManualSubmitting.value = true;
      
      const manualData = {
        evalId: props.evalId,
        correctionCost: manualCorrectionCost.value,
        functionality: manualFunctionality.value,
        visualQuality: manualVisualQuality.value,
        codeQuality: manualCodeQuality.value,
        timestamp: new Date().toISOString()
      };

      emit('submit-manual-evaluation', manualData);
      
      setTimeout(() => {
        isManualSubmitting.value = false;
      }, 500);
    };

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
      isManualSubmitting,
      isExporting,
      hasScore,
      hasParsedEvaluation,
      displayOverallScore,
      overallScoreColor,
      scoreLevel,
      submitManualEvaluation,
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
  color: #666;
  margin-bottom: 10px;
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
  padding: 12px 0;
  margin-top: 12px;
}

.section-subtitle {
  display: flex;
  align-items: center;
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 12px;
  color: #37474f;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.manual-form {
  margin-top: 8px;
}

.slider-group {
  margin-bottom: 14px;
}

.slider-label {
  font-size: 13px;
  font-weight: 500;
  color: #333;
  margin-bottom: 4px;
}

.slider-value {
  min-width: 35px;
  text-align: right;
  font-weight: 500;
  font-size: 14px;
  color: #546e7a;
}

.slider-hint {
  font-size: 11px;
  color: #999;
  margin-top: -8px;
  text-align: center;
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
</style>
