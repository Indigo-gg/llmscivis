<template>
  <div class="left-sidebar">
    <!-- Tabs Navigation -->
    <v-tabs
      v-model="currentTab"
      bg-color="white"
      color="primary"
      density="compact"
      class="tabs-header"
    >
      <v-tab value="config" class="tab-item">
        <v-icon start size="small">mdi-cog</v-icon>
        Configuration
        <v-badge
          v-if="tabStatus.config === 'completed'"
          color="success"
          icon="mdi-check"
          inline
        ></v-badge>
      </v-tab>
      
      <v-tab value="expansion" :disabled="!newCase.workflow.inquiryExpansion" class="tab-item">
        <v-icon start size="small">mdi-chart-timeline-variant</v-icon>
        Query Expansion
        <v-badge
          v-if="tabStatus.expansion === 'loading'"
          color="primary"
          icon="mdi-loading mdi-spin"
          inline
        ></v-badge>
        <v-badge
          v-if="tabStatus.expansion === 'completed'"
          color="success"
          icon="mdi-check"
          inline
        ></v-badge>
      </v-tab>
      
      <v-tab value="retrieval" :disabled="!newCase.workflow.rag" class="tab-item">
        <v-icon start size="small">mdi-database-search</v-icon>
        Retrieval
        <v-badge
          v-if="tabStatus.retrieval === 'loading'"
          color="primary"
          icon="mdi-loading mdi-spin"
          inline
        ></v-badge>
        <v-badge
          v-if="tabStatus.retrieval === 'completed'"
          color="success"
          icon="mdi-check"
          inline
        ></v-badge>
      </v-tab>
    </v-tabs>

    <v-divider></v-divider>

    <!-- Tab Windows -->
    <v-window v-model="currentTab" class="tab-windows">
      <!-- Tab 1: Configuration -->
      <v-window-item value="config" class="tab-content">
        <div class="sidebar-content config-content">
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
          rows="6"
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

      <!-- Generate Button -->
      <div class="action-section">
        <v-btn 
          color="primary" 
          block 
          :loading="isLoading"
          @click="handleStart"
          class="generate-btn"
        >
          <v-icon left>mdi-rocket-launch-outline</v-icon>
          Start
        </v-btn>
      </div>
    </div>
      </v-window-item>

      <!-- Tab 2: Query Expansion -->
      <v-window-item value="expansion" class="tab-content">
        <div class="sidebar-content expansion-content">
        <QueryExpansionTimeline 
          :content="queryExpansionData"
          :is-loading="isExpanding"
          :loading-text="'Expanding query...'"
          @update:content="handleExpansionUpdate"
          @next-step="handleProceedToRetrieval"
        />
        
        <!-- Manual Retrieval Button (Fallback) -->
        <div v-if="!isExpanding && queryExpansionData && queryExpansionData.length > 0 && newCase.workflow.rag" class="action-container" style="margin-top: 16px;">
          <v-btn
            color="success"
            size="large"
            block
            @click="handleProceedToRetrieval(queryExpansionData)"
            prepend-icon="mdi-database-search"
            class="retrieval-btn"
          >
            <v-icon start>mdi-database-search</v-icon>
            Go to Retrieval Module
          </v-btn>
        </div>
      </div>
      </v-window-item>

      <!-- Tab 3: Retrieval Results -->
      <v-window-item value="retrieval" class="tab-content">
        <div class="sidebar-content retrieval-content">
          <!-- Loading State for Retrieval -->
          <div v-if="isRetrieving" class="retrieval-loading">
            <v-progress-circular
              indeterminate
              size="48"
              width="5"
              color="primary"
            ></v-progress-circular>
            <p class="loading-text">Retrieving relevant examples...</p>
          </div>
          
          <!-- Retrieval Results Card -->
          <RetrievalResultsCard v-else :results="retrievalResults" />
          
          <!-- Proceed to Generation Button -->
          <v-btn
            color="success"
            size="large"
            block
            @click="handleProceedToGeneration"
            prepend-icon="mdi-rocket-launch"
            class="mt-4 generation-btn"
          >
            Proceed to Generation
          </v-btn>
        </div>
      </v-window-item>
    </v-window>

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
import { onMounted, reactive, ref, computed, watch } from "vue";
import QueryExpansionTimeline from "@/components/dashboard/QueryExpansionTimeline.vue";
import RetrievalResultsCard from "@/components/dashboard/RetrievalResultsCard.vue";
import { appConfig } from "@/view/config.js";
import { generateCode, getModels } from "@/api/api.js";
import { getCaseList } from "@/api/api.js";
import { VTreeview } from "vuetify/labs/VTreeview";
import axios from "axios";
import { post } from "@/api/request.js";

export default {
  name: "LeftSidebar",
  components: {
    QueryExpansionTimeline,
    RetrievalResultsCard,
    VTreeview,
  },
  props: {
    queryExpansion: {
      type: [String, Array],
      default: ''
    },
    retrievalResults: {
      type: Array,
      default: () => []
    }
  },
  emits: ['end', 'getNewCase', 'retrieval-complete'],
  setup(props, context) {
    const currentTab = ref('config'); // 'config', 'expansion', 'retrieval'
    const tabStatus = reactive({
      config: 'idle', // 'idle', 'loading', 'completed'
      expansion: 'idle',
      retrieval: 'idle'
    });
    const workflowState = ref('idle'); // 'idle', 'expanded', 'retrieved', 'generated'
    const queryExpansionData = ref([]);
    const updatedExpansionData = ref(null); // 存储用户编辑后的数据
    const isExpanding = ref(false); // 提示词拓展加载状态
    const isRetrieving = ref(false); // 检索加载状态
    const isGenerating = ref(false); // 生成加载状态
    const finalPrompt = ref(''); // 存储检索后的最终prompt
    
    // 监听 props.queryExpansion 的变化
    watch(
      () => props.queryExpansion,
      (newVal) => {
        if (newVal) {
          queryExpansionData.value = newVal;
          if (Array.isArray(newVal) && newVal.length > 0) {
            workflowState.value = 'expanded';
            tabStatus.expansion = 'completed';
            // 自动切换到 expansion 标签页
            currentTab.value = 'expansion';
            isExpanding.value = false; // 拓展完成，关闭加载状态
          }
        }
      },
      { deep: true }
    );

    // 监听 retrieval results 的变化
    watch(
      () => props.retrievalResults,
      (newVal) => {
        if (newVal && newVal.length > 0) {
          workflowState.value = 'retrieved';
          tabStatus.retrieval = 'completed';
          // 自动切换到 retrieval 标签页
          currentTab.value = 'retrieval';
          isRetrieving.value = false; // 检索完成，关闭加载状态
        }
      },
      { deep: true }
    );

    // Computed property for workflow state text
    const workflowStateText = computed(() => {
      const stateTexts = {
        'idle': 'Ready',
        'expanded': 'Query Expanded - Ready for Retrieval',
        'retrieved': 'Retrieved - Ready for Generation',
        'generated': 'Code Generated'
      };
      return stateTexts[workflowState.value] || 'Unknown';
    });
    
    const newCase = ref({
      path: null,
      name: null,
      prompt: appConfig.testDes,
      groundTruth: appConfig.testCode,
      evaluatorPrompt: appConfig.evaluator_prompt,
      generatorPrompt: appConfig.generator_prompt,
      generator: null,
      evaluator: null,
      errorCount: 0,
      maxIterations: 3,
      workflow: {
        inquiryExpansion: false,
        rag: false,
      },
      evalUser: appConfig.eval_user
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
    const handleActiveChange = (activeNodes) => {
      console.log('activeNodes', activeNodes);
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
    };

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

      generateCode(newCase.value).then((res) => {
        if (res.data && res.data.generated_code && res.data.generated_code.trim() !== '') {
          info.message = '代码生成成功';
          info.snackbar = true;
          context.emit('end', res.data);
        } else {
          info.message = '代码生成失败：返回的代码为空';
          info.snackbar = true;
          console.error('Generated code is empty:', res.data);
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
          newCase.value.workflow.inquiryExpansion = inquiryExpansionSelected.value;
          console.log('1', newCase.value.workflow);
          break;
        case 'rag':
          if (ragSelected.value) {
            inquiryExpansionSelected.value = true;
          }
          newCase.value.workflow.inquiryExpansion = inquiryExpansionSelected.value;
          newCase.value.workflow.rag = ragSelected.value;
          console.log('2', newCase.value.workflow);
          break;
        default:
          console.log('workflow', newCase.value.workflow);
      }
    };

    // 处理用户编辑拓展数据
    const handleExpansionUpdate = (updatedData) => {
      console.log('Query expansion data updated:', updatedData);
      updatedExpansionData.value = updatedData;
      queryExpansionData.value = updatedData;
    };

    // 处理 Start 按钮：启动提示词拓展
    const handleStart = async () => {
      const { prompt, generator, evaluator } = newCase.value;
      
      // 字段验证
      if (!prompt || prompt.trim() === '') {
        info.message = 'Prompt cannot be empty';
        info.snackbar = true;
        return;
      }

      if (!generator || generator.trim() === '') {
        info.message = 'Generator cannot be empty';
        info.snackbar = true;
        return;
      }

      if (!evaluator || evaluator.trim() === '') {
        info.message = 'Evaluator cannot be empty';
        info.snackbar = true;
        return;
      }

      // 标记配置标签页完成
      tabStatus.config = 'completed';

      // 如果启用了提示词拓展，先执行拓展
      if (newCase.value.workflow.inquiryExpansion) {
        try {
          info.message = '正在拓展查询...';
          info.snackbar = true;
          isExpanding.value = true;
          isLoading.value = true;
          tabStatus.expansion = 'loading';
          
          // 切换到 expansion 标签页
          currentTab.value = 'expansion';
          workflowState.value = 'idle';
          queryExpansionData.value = []; // 清空旧数据
          
          // 调用拓展 API
          const response = await axios.post('http://127.0.0.1:5001/expand', {
            prompt: prompt
          });

          if (response.data && response.data.success) {
            queryExpansionData.value = response.data.analysis;
            workflowState.value = 'expanded';
            info.message = `拓展完成，生成 ${response.data.analysis.length} 个步骤`;
            info.snackbar = true;
            
            // 通知父组件
            context.emit('expansion-complete', response.data.analysis);
          } else {
            throw new Error(response.data.error || '拓展失败');
          }
        } catch (error) {
          console.error('Expansion failed:', error);
          info.message = '拓展失败: ' + (error.response?.data?.detail || error.message);
          info.snackbar = true;
          workflowState.value = 'idle';
        } finally {
          isExpanding.value = false;
          isLoading.value = false;
        }
      } else {
        // 如果没启用拓展，直接进入生成流程
        handleDirectGeneration();
      }
    };

    // 处理“进入检索”按钮
    const handleProceedToRetrieval = async (expansionData) => {
      console.log('Proceeding to retrieval with data:', expansionData);
      
      try {
        info.message = '正在检索相关示例...';
        info.snackbar = true;
        isRetrieving.value = true;
        isLoading.value = true;
        tabStatus.retrieval = 'loading';
        // 切换到检索标签页
        currentTab.value = 'retrieval';

        // 调用后端 RAG 检索 API
        const response = await axios.post('http://127.0.0.1:5001/retrieval', {
          analysis: expansionData,
          prompt: newCase.value.prompt
        });

        if (response.data && response.data.success) {
          // 保存检索后的 final_prompt
          finalPrompt.value = response.data.final_prompt;
          
          // 更新检索结果（通过 emit 通知父组件）
          context.emit('retrieval-complete', {
            retrieval_results: response.data.retrieval_results,
            final_prompt: response.data.final_prompt
          });
          
          workflowState.value = 'retrieved';
          info.message = `检索完成，找到 ${response.data.retrieval_results.length} 个相关示例`;
          info.snackbar = true;
        }
      } catch (error) {
        console.error('Retrieval failed:', error);
        info.message = '检索失败: ' + (error.response?.data?.detail || error.message);
        info.snackbar = true;
      } finally {
        isRetrieving.value = false;
        isLoading.value = false;
      }
    };

    // 处理"进入生成"按钮
    const handleProceedToGeneration = async () => {
      console.log('Proceeding to generation...');
      
      try {
        info.message = '正在生成代码...';
        info.snackbar = true;
        isGenerating.value = true;
        isLoading.value = true;
        
        // 使用更新后的拓展数据执行生成
        const finalExpansionData = updatedExpansionData.value || queryExpansionData.value;
        
        // 构造请求数据
        const payload = {
          ...newCase.value,
          expansionData: finalExpansionData,
          finalPrompt: finalPrompt.value // 使用检索后的 prompt
        };
        
        // 调用生成 API
        const response = await generateCode(payload);
        
        if (response.data && response.data.generated_code && response.data.generated_code.trim() !== '') {
          info.message = '代码生成成功';
          info.snackbar = true;
          workflowState.value = 'generated';
          context.emit('end', response.data);
        } else {
          info.message = '代码生成失败：返回的代码为空';
          info.snackbar = true;
          console.error('Generated code is empty:', response.data);
          context.emit('end', response.data);
        }
      } catch (error) {
        console.error('Generation failed:', error);
        info.message = '代码生成失败: ' + (error.response?.data?.detail || error.message);
        info.snackbar = true;
      } finally {
        isGenerating.value = false;
        isLoading.value = false;
      }
      
      context.emit('getNewCase', newCase.value);
    };
    
    // 直接生成（未启用拓展和检索）
    const handleDirectGeneration = async () => {
      try {
        info.message = '正在生成代码...';
        info.snackbar = true;
        isLoading.value = true;
        
        const response = await generateCode(newCase.value);
        
        if (response.data && response.data.generated_code && response.data.generated_code.trim() !== '') {
          info.message = '代码生成成功';
          info.snackbar = true;
          context.emit('end', response.data);
        } else {
          info.message = '代码生成失败：返回的代码为空';
          info.snackbar = true;
          console.error('Generated code is empty:', response.data);
          context.emit('end', response.data);
        }
      } catch (error) {
        console.error('Generation failed:', error);
        info.message = '代码生成失败: ' + (error.response?.data?.detail || error.message);
        info.snackbar = true;
      } finally {
        isLoading.value = false;
      }
      
      context.emit('getNewCase', newCase.value);
    };

    onMounted(() => {
      fetchModels();
      fetchTreeData();
    });

    return {
      currentTab,
      tabStatus,
      workflowState,
      workflowStateText,
      queryExpansionData,
      updatedExpansionData,
      isExpanding,
      isRetrieving,
      isGenerating,
      newCase,
      handleStart,
      handleUpload,
      updateWorkflow,
      handleExpansionUpdate,
      handleProceedToRetrieval,
      handleProceedToGeneration,
      handleDirectGeneration,
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
.left-sidebar {
  width: 100%;
  height: 100%;
  background-color: var(--background-color);
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Tabs Header */
.tabs-header {
  flex-shrink: 0;
  border-bottom: 1px solid var(--border-color);
}

.tab-item {
  font-size: 13px;
  text-transform: none;
  letter-spacing: 0.3px;
}

/* Tab Windows */
.tab-windows {
  flex: 1;
  overflow: hidden;
}

.tab-content {
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.sidebar-content {
  padding: var(--spacing-sm);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  flex: 1;
  overflow: auto;
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

/* Config Content */
.config-content {
}

.config-section {
  border-bottom: 1px solid var(--border-color);
  padding-bottom: var(--spacing-sm);
}

.config-section:last-of-type {
  border-bottom: none;
}

.section-header {
  background-color: var(--secondary-bg);
  color: var(--text-primary);
  padding: var(--spacing-sm);
  margin: 0 calc(-1 * var(--spacing-sm)) var(--spacing-sm) calc(-1 * var(--spacing-sm));
  font-size: 13px;
  font-weight: 600;
  border-bottom: 1px solid var(--border-color);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
}

.expansion-header {
  font-size: 14px;
  font-weight: 500;
}

.tree-container {
  max-height: 250px;
  overflow-y: auto;
  padding: 8px 0;
}

.empty-state-small {
  text-align: center;
  padding: 16px;
}

.empty-text-small {
  color: #9e9e9e;
  font-size: 13px;
  margin: 0;
}

.action-section {
  margin-top: auto;
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--border-color);
}

.generate-btn {
  font-weight: 600;
  text-transform: none;
  letter-spacing: 0.5px;
}

/* Retrieval Content */
.retrieval-content,
.expansion-content {
  gap: var(--spacing-md);
}

.workflow-state {
  padding: 8px 0;
  margin-bottom: 8px;
}

.state-chip {
  width: 100%;
  justify-content: center;
  font-weight: 600;
}

.expansion-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.expansion-section .section-header {
  flex-shrink: 0;
}

.retrieval-section {
  padding: 8px 0;
  border-bottom: 1px solid #e8e8e8;
}

.retrieval-section:last-child {
  border-bottom: none;
}

.generation-btn {
  font-weight: 600;
  text-transform: none;
  letter-spacing: 0.5px;
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
}

.generation-btn:hover {
  box-shadow: 0 6px 16px rgba(76, 175, 80, 0.4);
}

.retrieval-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px;
  text-align: center;
  min-height: 200px;
}

.retrieval-loading .loading-text {
  color: #666;
  font-size: 15px;
  margin-top: 20px;
  font-weight: 500;
}

.retrieval-btn {
  font-weight: 600;
  text-transform: none;
  letter-spacing: 0.5px;
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
}

.retrieval-btn:hover {
  box-shadow: 0 6px 16px rgba(76, 175, 80, 0.4);
}

.action-container {
  margin-top: var(--spacing-lg);
  padding-top: var(--spacing-md);
}
</style>
