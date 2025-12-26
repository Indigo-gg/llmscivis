<template>
  <div class="query-expansion-timeline">
    <!-- Loading State -->
    <div v-if="isLoading" class="loading-state">
      <v-progress-circular
        indeterminate
        size="64"
        width="6"
        color="primary"
      ></v-progress-circular>
      <p class="loading-text">{{ loadingText }}</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="!expansionData || expansionData.length === 0" class="empty-state">
      <v-icon size="48" color="grey-lighten-1">mdi-timeline-text-outline</v-icon>
      <p class="empty-text">No query expansion data available</p>
    </div>

    <!-- Timeline with Steps -->
    <div v-else class="timeline-container">
      <div 
        v-for="(step, index) in expansionData" 
        :key="index" 
        class="timeline-step"
        :class="{ 'editing': editingIndex === index }"
      >
        <!-- Step Number Circle -->
        <div class="step-indicator">
          <div class="step-circle">{{ index + 1 }}</div>
          <div v-if="index < expansionData.length - 1" class="step-line"></div>
        </div>

        <!-- Step Content Card -->
        <div class="step-content">
          <div class="step-card">
            <div class="step-header">
              <!-- Combined Phase and Step Name -->
              <div class="step-title">
                {{ step.phase }} - {{ step.step_name }}
              </div>

              <!-- Edit Button -->
              <v-btn 
                v-if="editingIndex !== index"
                icon="mdi-pencil" 
                size="x-small" 
                variant="text"
                @click="startEditing(index)"
                class="edit-btn"
              ></v-btn>
              
              <!-- Save/Cancel Buttons when editing -->
              <div v-else class="edit-actions">
                <v-btn 
                  icon="mdi-check" 
                  size="x-small" 
                  variant="text"
                  color="success"
                  @click="saveEditing(index)"
                ></v-btn>
                <v-btn 
                  icon="mdi-close" 
                  size="x-small" 
                  variant="text"
                  color="error"
                  @click="cancelEditing"
                ></v-btn>
              </div>
            </div>

            <div class="step-body">
              <!-- Description (main content) -->
              <div class="field-group">
                <v-textarea
                  v-if="editingIndex === index"
                  v-model="editingStep.description"
                  rows="3"
                  density="compact"
                  variant="outlined"
                  hide-details
                  auto-grow
                  label="Description"
                ></v-textarea>
                <div v-else class="description">{{ step.description }}</div>
              </div>

              <!-- VTK Modules (compact display) -->
              <div v-if="step.vtk_modules && step.vtk_modules.length > 0" class="modules-container">
                <v-chip
                  v-for="(module, mIndex) in step.vtk_modules"
                  :key="mIndex"
                  size="x-small"
                  color="primary"
                  variant="outlined"
                  class="module-chip"
                >
                  {{ module }}
                </v-chip>
              </div>
            </div>
          </div>
        </div>
      </div>


    </div>
  </div>
</template>

<script>
import { ref, watch } from 'vue';

export default {
  name: 'QueryExpansionTimeline',
  props: {
    content: {
      type: [String, Array],
      default: () => []
    },
    isLoading: {
      type: Boolean,
      default: false
    },
    loadingText: {
      type: String,
      default: 'Processing query expansion...'
    }
  },
  emits: ['update:content', 'next-step'],
  setup(props, { emit }) {
    const expansionData = ref([]);
    const editingIndex = ref(null);
    const editingStep = ref(null);

    // Parse content (could be JSON string or array)
    const parseContent = (content) => {
      if (!content) return [];
      
      if (Array.isArray(content)) {
        return content;
      }
      
      if (typeof content === 'string') {
        try {
          // Try to parse as JSON
          const parsed = JSON.parse(content);
          if (Array.isArray(parsed)) {
            return parsed;
          }
        } catch (e) {
          // Not valid JSON, return empty
          console.warn('Failed to parse query expansion content:', e);
        }
      }
      
      return [];
    };

    // Watch for content changes
    watch(
      () => props.content,
      (newContent) => {
        expansionData.value = parseContent(newContent);
      },
      { immediate: true }
    );

    // Get color for phase
    const getPhaseColor = (phase) => {
      const phaseColors = {
        'Data Loading': 'blue',
        'Data Processing': 'green',
        'Visualization': 'orange',
        'Rendering': 'purple',
        'Interaction': 'teal',
        'Default': 'grey'
      };
      return phaseColors[phase] || phaseColors['Default'];
    };

    // Get icon for phase
    const getPhaseIcon = (phase) => {
      const phaseIcons = {
        'Data Loading': 'mdi-database-import',
        'Data Processing': 'mdi-cog',
        'Visualization': 'mdi-chart-line',
        'Rendering': 'mdi-image-filter-hdr',
        'Interaction': 'mdi-cursor-pointer',
        'Default': 'mdi-circle'
      };
      return phaseIcons[phase] || phaseIcons['Default'];
    };

    // Start editing a step
    const startEditing = (index) => {
      editingIndex.value = index;
      editingStep.value = JSON.parse(JSON.stringify(expansionData.value[index]));
    };

    // Save editing
    const saveEditing = (index) => {
      expansionData.value[index] = JSON.parse(JSON.stringify(editingStep.value));
      editingIndex.value = null;
      editingStep.value = null;
      
      // Emit update to parent
      emit('update:content', expansionData.value);
    };

    // Cancel editing
    const cancelEditing = () => {
      editingIndex.value = null;
      editingStep.value = null;
    };

    // Handle next step button
    const handleNextStep = () => {
      emit('next-step', expansionData.value);
    };

    return {
      expansionData,
      editingIndex,
      editingStep,
      getPhaseColor,
      getPhaseIcon,
      startEditing,
      saveEditing,
      cancelEditing,
      handleNextStep
    };
  }
};
</script>

<style scoped>
.query-expansion-timeline {
  width: 100%;
  height: 80vh;
  overflow-y: auto;
  padding: var(--spacing-md);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xxl) var(--spacing-xl);
  text-align: center;
  min-height: 300px;
}

.loading-text {
  color: var(--text-secondary);
  font-size: 15px;
  margin-top: var(--spacing-lg);
  font-weight: 500;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xxl);
  text-align: center;
  min-height: 200px;
}

.empty-text {
  color: var(--disabled-color);
  font-size: 14px;
  margin-top: var(--spacing-md);
}

.timeline-container {
  position: relative;
  padding: var(--spacing-sm) 0;
}

.timeline-step {
  display: flex;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
  position: relative;
}

.timeline-step.editing .step-card {
  border: 2px solid var(--primary-color);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
}

.step-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}

.step-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--primary-color);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  box-shadow: var(--shadow-light);
  z-index: 1;
}

.step-line {
  width: 2px;
  flex: 1;
  min-height: 40px;
  background: var(--border-color);
  margin-top: var(--spacing-xs);
}

.step-content {
  flex: 1;
  min-width: 0;
}

.step-card {
  background: white;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  transition: all 0.3s ease;
  box-shadow: var(--shadow-light);
}

.step-card:hover {
  box-shadow: var(--shadow-medium);
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md);
  background: var(--secondary-bg);
  border-bottom: 1px solid var(--border-color);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}

.step-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
  flex: 1;
}

.edit-btn {
  opacity: 0;
  transition: opacity 0.2s;
}

.step-card:hover .edit-btn {
  opacity: 1;
}

.edit-actions {
  display: flex;
  gap: var(--spacing-xs);
}

.step-body {
  padding: var(--spacing-md);
}

.field-group {
  margin-bottom: var(--spacing-sm);
}

.field-group:last-child {
  margin-bottom: 0;
}

.description {
  white-space: pre-wrap;
  word-break: break-word;
  padding: var(--spacing-sm);
  border-radius: var(--radius-sm);
  background: var(--secondary-bg);
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.6;
}

.modules-container {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xs);
  margin-top: var(--spacing-sm);
}

.module-chip {
  font-family: 'Courier New', monospace;
  font-size: 11px;
}

.action-container {
  margin-top: var(--spacing-xl);
  padding-top: var(--spacing-lg);
  border-top: 1px dashed var(--border-color);
}

.next-step-btn {
  font-weight: 600;
  font-size: 14px;
  text-transform: none;
  letter-spacing: 0.5px;
}

/* Scrollbar Styling */
.query-expansion-timeline::-webkit-scrollbar {
  width: 6px;
}

.query-expansion-timeline::-webkit-scrollbar-track {
  background: transparent;
}

.query-expansion-timeline::-webkit-scrollbar-thumb {
  background: var(--disabled-color);
  border-radius: 3px;
}

.query-expansion-timeline::-webkit-scrollbar-thumb:hover {
  background: var(--text-secondary);
}
</style>
