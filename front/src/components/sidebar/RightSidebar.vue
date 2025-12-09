<template>
  <div class="right-sidebar">
    <div class="sidebar-header">
      <h3 class="sidebar-title">Evaluation</h3>
    </div>

    <v-divider class="my-2"></v-divider>

    <div class="sidebar-content evaluation-content">
      <EvaluationScoreCard 
        :score="score" 
        :evaluation="evaluation"
        :parsed-evaluation="parsedEvaluation"
        :automated-checks="automatedChecks"
        :manual-evaluation="manualEvaluation"
        :eval-id="evalId"
        :is-loading="isLoading"
        :is-generating="isGenerating"
        @trigger-evaluation="$emit('trigger-evaluation')"
        @submit-manual-evaluation="$emit('submit-manual-evaluation', $event)"
        @export-results="$emit('export-results')"
      />
    </div>
  </div>
</template>

<script>
import { defineComponent } from 'vue';
import EvaluationScoreCard from '@/components/dashboard/EvaluationScoreCard.vue';

export default defineComponent({
  name: 'RightSidebar',
  components: {
    EvaluationScoreCard,
  },
  props: {
    score: {
      type: [String, Number],
      default: ''
    },
    evaluation: {
      type: String,
      default: ''
    },
    parsedEvaluation: {
      type: Object,
      default: null
    },
    automatedChecks: {
      type: Object,
      default: null
    },
    manualEvaluation: {
      type: Object,
      default: null
    },
    evalId: {
      type: [String, Number],
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
  setup() {
    return {
      // Props are automatically available in template
    };
  }
});
</script>

<style scoped>
.right-sidebar {
  width: 100%;
  height: 100%;
  background-color: #ffffff;
  padding: 12px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  border-left: 1px solid #e0e0e0;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  margin-bottom: 8px;
}

.sidebar-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin: 0;
  flex: 1;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  padding-right: 4px;
}

.sidebar-content::-webkit-scrollbar {
  width: 6px;
}

.sidebar-content::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar-content::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}

.sidebar-content::-webkit-scrollbar-thumb:hover {
  background: #999;
}

.evaluation-content {
  padding: 0;
}
</style>
