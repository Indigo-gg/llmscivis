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
          <v-card elevation="2" class="step-card">
            <v-card-title class="step-header">
              <!-- Phase Badge -->
              <v-chip 
                :color="getPhaseColor(step.phase)" 
                size="small" 
                class="phase-chip"
                label
              >
                <v-icon start size="small">{{ getPhaseIcon(step.phase) }}</v-icon>
                {{ step.phase }}
              </v-chip>

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
            </v-card-title>

            <v-card-text class="step-body">
              <!-- Step Name -->
              <div class="field-group">
                <label class="field-label">Step Name</label>
                <v-text-field
                  v-if="editingIndex === index"
                  v-model="editingStep.step_name"
                  density="compact"
                  variant="outlined"
                  hide-details
                ></v-text-field>
                <div v-else class="field-value step-name">{{ step.step_name }}</div>
              </div>

              <!-- VTK Modules -->
              <div class="field-group">
                <label class="field-label">VTK Modules</label>
                <v-combobox
                  v-if="editingIndex === index"
                  v-model="editingStep.vtk_modules"
                  chips
                  multiple
                  density="compact"
                  variant="outlined"
                  hide-details
                  closable-chips
                  class="modules-input"
                >
                  <template v-slot:chip="{ props, item }">
                    <v-chip
                      v-bind="props"
                      :text="item"
                      size="small"
                      color="primary"
                      closable
                    ></v-chip>
                  </template>
                </v-combobox>
                <div v-else class="field-value modules-list">
                  <v-chip
                    v-for="(module, mIndex) in step.vtk_modules"
                    :key="mIndex"
                    size="small"
                    color="primary"
                    variant="outlined"
                    class="module-chip"
                  >
                    {{ module }}
                  </v-chip>
                  <span v-if="!step.vtk_modules || step.vtk_modules.length === 0" class="no-modules">
                    No modules specified
                  </span>
                </div>
              </div>

              <!-- Description -->
              <div class="field-group">
                <label class="field-label">Description</label>
                <v-textarea
                  v-if="editingIndex === index"
                  v-model="editingStep.description"
                  rows="3"
                  density="compact"
                  variant="outlined"
                  hide-details
                  auto-grow
                ></v-textarea>
                <div v-else class="field-value description">{{ step.description }}</div>
              </div>
            </v-card-text>
          </v-card>
        </div>
      </div>

      <!-- Next Step Button -->
      <div class="action-container">
        <v-btn
          color="primary"
          size="large"
          block
          @click="handleNextStep"
          :disabled="editingIndex !== null"
          prepend-icon="mdi-arrow-right-circle"
          class="next-step-btn"
        >
          Proceed to Retrieval
        </v-btn>
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
  height: 100%;
  overflow-y: auto;
  padding: 12px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px;
  text-align: center;
  min-height: 300px;
}

.loading-text {
  color: #666;
  font-size: 15px;
  margin-top: 20px;
  font-weight: 500;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  text-align: center;
  min-height: 200px;
}

.empty-text {
  color: #9e9e9e;
  font-size: 14px;
  margin-top: 12px;
}

.timeline-container {
  position: relative;
  padding: 8px 0;
}

.timeline-step {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  position: relative;
}

.timeline-step.editing .step-card {
  border: 2px solid #1976d2;
  box-shadow: 0 4px 12px rgba(25, 118, 210, 0.2);
}

.step-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}

.step-circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
  z-index: 1;
}

.step-line {
  width: 2px;
  flex: 1;
  min-height: 40px;
  background: linear-gradient(180deg, #667eea 0%, #e0e0e0 100%);
  margin-top: 4px;
}

.step-content {
  flex: 1;
  min-width: 0;
}

.step-card {
  border-radius: 8px;
  transition: all 0.3s ease;
}

.step-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-bottom: 1px solid #e0e0e0;
}

.phase-chip {
  font-weight: 600;
  font-size: 12px;
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
  gap: 4px;
}

.step-body {
  padding: 16px;
}

.field-group {
  margin-bottom: 12px;
}

.field-group:last-child {
  margin-bottom: 0;
}

.field-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #666;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.field-value {
  font-size: 14px;
  color: #333;
  line-height: 1.5;
}

.step-name {
  font-weight: 600;
  font-size: 15px;
  color: #1976d2;
}

.modules-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.module-chip {
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.no-modules {
  color: #9e9e9e;
  font-style: italic;
  font-size: 13px;
}

.description {
  white-space: pre-wrap;
  word-break: break-word;
  background-color: #f9f9f9;
  padding: 8px;
  border-radius: 4px;
  border-left: 3px solid #1976d2;
}

.modules-input :deep(.v-field) {
  font-family: 'Courier New', monospace;
}

.action-container {
  margin-top: 32px;
  padding-top: 16px;
  border-top: 2px dashed #e0e0e0;
}

.next-step-btn {
  font-weight: 600;
  font-size: 15px;
  text-transform: none;
  letter-spacing: 0.5px;
  padding: 24px 0;
  box-shadow: 0 4px 12px rgba(25, 118, 210, 0.3);
}

.next-step-btn:hover {
  box-shadow: 0 6px 16px rgba(25, 118, 210, 0.4);
}

/* Scrollbar Styling */
.query-expansion-timeline::-webkit-scrollbar {
  width: 6px;
}

.query-expansion-timeline::-webkit-scrollbar-track {
  background: transparent;
}

.query-expansion-timeline::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}

.query-expansion-timeline::-webkit-scrollbar-thumb:hover {
  background: #999;
}
</style>
