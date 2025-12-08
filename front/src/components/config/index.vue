<template>
  <div class="config-sidebar">
    <!-- Prompt Configuration Section -->
    <div class="config-section prompt-section">
      <h4 class="section-header">Prompt Configuration</h4>
      <v-textarea
        label="Prompt" 
        rows="3"
        v-model="newCase.prompt"
        density="compact"
        variant="outlined"
        hide-details="auto"
      ></v-textarea>
      <v-textarea
        label="Ground Truth"
        v-model="newCase.groundTruth"
        outlined
        rows="8"
        density="compact"
        variant="outlined"
        hide-details="auto"
        class="mt-2"
      ></v-textarea>
    </div>

    <!-- Model Settings Section -->
    <div class="config-section model-section">
      <h4 class="section-header">Model Settings</h4>
      <v-select
        v-model="newCase.generator"
        :items="models"
        label="Generator"
        density="compact"
        variant="outlined"
        hide-details="auto"
      ></v-select>
      <v-select
        v-model="newCase.evaluator"
        :items="models"
        label="Evaluator"
        density="compact"
        variant="outlined"
        hide-details="auto"
        class="mt-2"
      ></v-select>
    </div>

    <!-- Workflow Options Section -->
    <div class="config-section workflow-section">
      <h4 class="section-header">Workflow Options</h4>
      <v-checkbox 
        v-model="inquiryExpansionSelected"
        label="Inquiry Expansion"
        prepend-icon="mdi-magnify-expand"
        density="compact"
        hide-details
        @change="updateWorkflow('inquiryExpansion')"
      ></v-checkbox>
      <v-checkbox 
        v-model="ragSelected"
        label="RAG"
        prepend-icon="mdi-database"
        density="compact"
        hide-details
        @change="updateWorkflow('rag')"
      ></v-checkbox>
    </div>

    <!-- Data Selection Section (Collapsible) -->
    <div class="config-section data-section">
      <v-expansion-panels variant="accordion">
        <v-expansion-panel>
          <v-expansion-panel-title class="expansion-header">
            <v-icon class="mr-2">mdi-folder-open-outline</v-icon>
            Select Task Case
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <div class="tree-container">
              <v-treeview
                v-if="treeData && treeData.length > 0"
                :items="treeData"
                item-key="path"
                item-text="name"
                density="compact"
                activatable
                return-object
                open-on-click
                @update:activated="handleActiveChange"
              >
                <template #prepend="{ item }">
                  <v-icon v-if="item.type === 'file'" size="small">mdi-file-document-outline</v-icon>
                  <v-icon v-else size="small">mdi-folder</v-icon>
                </template>
                <template #title="{ item }">
                  {{ item.name }}
                </template>
              </v-treeview>
              <div v-else class="empty-state-small">
                <p class="empty-text-small">No case data available</p>
              </div>
            </div>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </div>

    <!-- Generate Button (Fixed at bottom) -->
    <div class="action-section">
      <v-btn 
        color="#4a5258" 
        block 
        :loading="isLoading"
        @click="handleUpload"
        class="generate-btn"
      >
        <v-icon left>mdi-play</v-icon>
        Generate
      </v-btn>
    </div>

    <!-- Snackbar for notifications -->
    <v-snackbar
      v-model="info.snackbar"
      :timeout="info.timeout"
    >
      {{ info.message }}
      <template v-slot:actions>
        <v-btn
          color="blue"
          variant="text"
          @click="info.snackbar = false"
        >
          Close
        </v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script>
import {onMounted,reactive, ref} from "vue";
import workflow from "@/components/config/workflow.vue";
import {appConfig} from "@/view/config.js";
import {generateCode, getModels} from "@/api/api.js";
import { getCaseList } from "../../api/api";
import { VTreeview } from "vuetify/labs/VTreeview";
export default {
  name: "index",
  components: {
    workflow,
    VTreeview,
  },
  props: {
    /***
     * {
     *   "prompt": "...",
     *   "groundTruth": "...",
     * }
     */
    caseList: {
      type: Array,
      required: true
    }
  },
  setup(props, context) {
    const newCase = ref({
      path:null,
      name:null,
      prompt:appConfig.testDes,
      groundTruth:appConfig.testCode,
      evaluatorPrompt: appConfig.evaluator_prompt,
      generatorPrompt:appConfig.generator_prompt,
      generator:null,
      evaluator:null,
      errorCount: 0,
      maxIterations: 3,
      workflow:{
        inquiryExpansion:false,
        rag:false,
      },
      evalUser:appConfig.eval_user
    });
    
    let inquiryExpansionSelected = ref(false);
    let ragSelected = ref(false);

    const info = reactive({
      message: '',
      timeout: 3000,
      snackbar: false
    });

    const isLoading = ref(false);
    const treeData = ref([]);
    const models = ref([]);

    // Fetch models from backend
    const fetchModels = async () => {
      try {
        const response = await getModels();
        models.value = response.data || [];
        console.log('Models loaded:', models.value);
      } catch (error) {
        console.error('Failed to fetch models:', error);
        models.value = [];
      }
    };

    // Fetch tree data on component mount
    const fetchTreeData = async () => {
      try {
        const response = await getCaseList();
        // Handle the response - it should be an array, but ensure we normalize it
        const data = response.data || [];
        if (Array.isArray(data)) {
          treeData.value = data;
          console.log('Processed treeData.value:', treeData.value);
        } else {
          console.error('Expected response.data to be an array, but got:', data);
          treeData.value = [];
        }
      } catch (error) {
        console.error('Error fetching tree data:', error);
        info.message = 'Failed to fetch case list';
        info.snackbar = true;
        treeData.value = [];
      }
    };

    // Handle tree node activation
    const handleActiveChange=(activeNodes)=> {
      console.log('activeNodes',activeNodes);
      if (activeNodes && activeNodes.length > 0) {
        const selectedNode = activeNodes[0];
        const filePath = selectedNode.path;

        const findNodeByPath = (nodes, path) => {
          for (const node of nodes) {
            if (node.path === path) {
              return node;
            }
            if (node.children) {
              const found = findNodeByPath(node.children, path);
              if (found) {
                return found;
              }
            }
          }
          return null;
        };

        const node = findNodeByPath(treeData.value, filePath);

        if (node && node.type === 'file') {
          const findParent = (nodes, targetNode) => {
            for (const node of nodes) {
              if (node.children) {
                if (node.children.some(child => child.path === targetNode.path)) {
                  return node;
                }
                const found = findParent(node.children, targetNode);
                if (found) {
                  return found;
                }
              }
            }
            return null;
          };

          const parentNode = findParent(treeData.value, node);

          if (parentNode && parentNode.children) {
            let groundTruthContent = '';
            let descriptionContent = '';

            for (const child of parentNode.children) {
              if (child.type === 'file') {
                if (child.name === 'ground_truth.html' && child.content) {
                  groundTruthContent = child.content;
                } else if (child.name === 'description.txt' && child.content) {
                  descriptionContent = child.content;
                }
              }
            }

            if (groundTruthContent || descriptionContent) {
              newCase.value.groundTruth = groundTruthContent;
              newCase.value.prompt = descriptionContent;
              newCase.value.name = node.name;
              newCase.value.path = node.path;
            } else {
              newCase.value.groundTruth = node.content || '';
              newCase.value.prompt = `Please generate a VTK.js visualization code for the file: ${node.name}`;
              newCase.value.name = node.name;
              newCase.value.path = node.path;
            }
          } else {
            newCase.value.groundTruth = node.content || '';
            newCase.value.prompt = `Please generate a VTK.js visualization code for the file: ${node.name}`;
            newCase.value.name = node.name;
            newCase.value.path = node.path;
          }
        } else {
          newCase.value.groundTruth = '';
          newCase.value.prompt = '';
          newCase.value.name = '';
          newCase.value.path = '';
        }
      }
    }

    const handleUpload = () => {
      const { prompt, groundTruth, generator, evaluator, maxIterations } = newCase.value;
      
      // Field validation
      if (!prompt || prompt.trim() === '') {
        info.message = 'Prompt cannot be empty';
        info.snackbar = true;
        console.error('Prompt cannot be empty');
        return;
      }

      if (!maxIterations || maxIterations < 1) {
        info.message = 'Max iterations must be greater than 0';
        info.snackbar = true;
        console.error('Max iterations must be greater than 0');
        return;
      }

      if (!groundTruth || groundTruth.trim() === '') {
        info.message = 'Ground truth cannot be empty';
        info.snackbar = true;
        console.error('Ground truth cannot be empty');
        return;
      }

      if (!generator || generator.trim() === '') {
        info.message = 'Generator cannot be empty';
        info.snackbar = true;
        console.error('Generator cannot be empty');
        return;
      }

      if (!evaluator || evaluator.trim() === '') {
        info.message = 'Evaluator cannot be empty';
        info.snackbar = true;
        console.error('Evaluator cannot be empty');
        return;
      }

      isLoading.value = true;

      generateCode(newCase.value).then((res)=>{
        // Check if generated code is valid
        if (res.data && res.data.generated_code && res.data.generated_code.trim() !== '') {
          info.message = '代码生成成功';
          info.snackbar = true;
          context.emit('end', res.data);
        } else {
          info.message = '代码生成失败：返回的代码为空';
          info.snackbar = true;
          console.error('Generated code is empty:', res.data);
          // Still emit the response but mark it as failed
          context.emit('end', res.data);
        }
      }).catch(error => {
        info.message = '代码生成失败: ' + (error.response?.data?.detail || error.message);
        info.snackbar = true;
        console.error('Generation failed:', error);
      }).finally(() => {
        isLoading.value = false;
      });

      context.emit('getNewCase', newCase.value);
    };

    const updateWorkflow = (type) => {

      switch (type) {

        case 'inquiryExpansion':
          newCase.value.workflow.inquiryExpansion=inquiryExpansionSelected.value
          console.log('1',newCase.value.workflow);
          break;
        case 'rag':
          if (ragSelected.value) {
            inquiryExpansionSelected.value = true;
          }
          newCase.value.workflow.inquiryExpansion=inquiryExpansionSelected.value
          newCase.value.workflow.rag=ragSelected.value
          console.log('2',newCase.value.workflow);
          break;
        default:
          console.log('workflow',newCase.value.workflow);
      }
    };


    onMounted(()=>{
      fetchModels();
      fetchTreeData();
    })
    
    return {
      newCase,
      handleUpload,
      updateWorkflow,
      inquiryExpansionSelected,
      ragSelected,
      info,
      models,
      isLoading,
      treeData,
      handleActiveChange,
    };

  }
};
</script>

<style scoped>
/* Config Sidebar - Modify config-sidebar class to change sidebar layout */
.config-sidebar {
  width: 100%;
  height: 100%;
  background-color: #ffffff;
  padding: 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Section styling with military gray theme */
.config-section {
  border-bottom: 1px solid #e8e8e8;
  padding-bottom: 16px;
}

.config-section:last-of-type {
  border-bottom: none;
}

/* Section headers with military gray background */
.section-header {
  background-color: #4a5258;  /* Military Gray - Change this to modify theme */
  color: #ffffff;
  padding: 8px 12px;
  margin: 0 -16px 12px -16px;
  font-size: 14px;
  font-weight: 600;
  border-bottom: 2px solid #3a4248;
}

/* Expansion panel header styling */
.expansion-header {
  font-size: 14px;
  font-weight: 500;
}

/* Tree container */
.tree-container {
  max-height: 300px;
  overflow-y: auto;
  padding: 8px 0;
}

/* Empty state for tree */
.empty-state-small {
  text-align: center;
  padding: 20px;
}

.empty-text-small {
  color: #9e9e9e;
  font-size: 13px;
  margin: 0;
}

/* Action section for generate button */
.action-section {
  margin-top: auto;
  padding-top: 16px;
  border-top: 2px solid #e8e8e8;
}

.generate-btn {
  font-weight: 600;
  text-transform: none;
  letter-spacing: 0.5px;
}
</style>
