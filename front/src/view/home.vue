<template>

  <div class="home">
    <!-- Loading Overlay -->
    <v-overlay v-model="isGenerating" class="loading-overlay" persistent>
      <div class="loading-content">
        <v-progress-circular
          indeterminate
          size="64"
          width="6"
          color="#6ba4e6"
        ></v-progress-circular>
        <p class="loading-text">Generating Visualization Code...</p>
      </div>
    </v-overlay>

    <!-- Dashboard Area -->
    <div class="dashboard" :class="{ collapsed: isDashboardCollapsed }">
      <div class="dashboard-header">
        <span class="dashboard-title">Rawsiv</span>
        <div class="header-actions">
          <div class="showVis">
            <v-switch v-model="isShowVis" :title="isShowVis ? 'Show Preview' : 'Hide Preview'" true-icon="mdi-eye" false-icon="mdi-eye-off"
              color="primary" size="x-small" density="compact" hide-details inset class="mini-switch"
              @change="handleVisibilityChange"></v-switch>
          </div>
          <v-btn :icon="isDashboardCollapsed ? 'mdi-chevron-down' : 'mdi-chevron-up'" size="x-small" density="compact"
            variant="text" @click="isDashboardCollapsed = !isDashboardCollapsed" class="collapse-btn"></v-btn>
        </div>
      </div>
      <v-container fluid v-show="!isDashboardCollapsed" class="dashboard-content">
        <v-row>
          <v-col cols="12" md="4">
            <QueryExpansionCard :content="currentCase.queryExpansion" />
          </v-col>
          <v-col cols="12" md="4">
            <RetrievalResultsCard :results="currentCase.retrievalResults" />
          </v-col>
          <v-col cols="12" md="4">
            <EvaluationScoreCard 
              :score="currentCase.score" 
              :evaluation="currentCase.evaluatorEvaluation"
              :parsed-evaluation="currentCase.parsedEvaluation"
              :automated-checks="automatedEvaluationChecks"
              :manual-evaluation="currentCase.manualEvaluation"
              :eval-id="currentCase.evalId"
              :is-loading="isEvaluating" 
              @trigger-evaluation="triggerEvaluation"
              @submit-manual-evaluation="handleManualEvaluation" />
          </v-col>
        </v-row>
      </v-container>
    </div>
    <div class="container">
      <!-- Right side: Configuration sidebar -->
      <div class="right config-panel">
        <config :case-list="caseList" @end="handleSeGenEnd" @getNewCase="setCurrentCase">
        </config>
      </div>
      <!-- Left side: Code preview and output -->
      <div class="left">
        <div class="preview">
          <preview class="scrollable" :is-show-vis="isShowVis" :htmlContent="currentCase.generatedCode"
            :title="'Generated Code'" ref="generatedPreview" @console-output="handleConsoleOutput">
            <template #actions>
              <v-btn v-if="isShowVis" :icon="isFullScreen ? 'mdi-fullscreen-exit' : 'mdi-fullscreen'" size="small"
                variant="text" @click="toggleFullScreen('generated')" class="fullscreen-btn"></v-btn>
            </template>
          </preview>
          <preview class="scrollable" :is-show-vis="isShowVis" :htmlContent="currentCase.groundTruth"
            ref="truthPreview" @console-output="handleConsoleOutput">
            <template #actions>
              <v-btn v-if="isShowVis" :icon="isFullScreen ? 'mdi-fullscreen-exit' : 'mdi-fullscreen'" size="small"
                variant="text" @click="toggleFullScreen('truth')" class="fullscreen-btn"></v-btn>
            </template>
          </preview>
        </div>
        
        <div class="output">
          <div class="output-container">
            <Output 
              :console-output="currentCase.consoleOutput" 
              :evaluator-output="currentCase.evaluatorEvaluation"
              :parsed-evaluation="currentCase.parsedEvaluation"
              @export-results="exportResults">
            </Output>
          </div>
        </div>
      </div>
      
      
    </div>

    <v-snackbar v-model="info.snackbar" :timeout="info.timeout">
      {{ info.message }}

      <template v-slot:actions>
        <v-btn color="blue" variant="text" @click="info.snackbar = false">
          Close
        </v-btn>
      </template>
    </v-snackbar>

  </div>

</template>


<script>
import preview from "@/components/preview/index.vue";
import config from "@/components/config/index.vue";
import output from "@/components/output/index.vue"
import QueryExpansionCard from "@/components/dashboard/QueryExpansionCard.vue";
import RetrievalResultsCard from "@/components/dashboard/RetrievalResultsCard.vue";
import EvaluationScoreCard from "@/components/dashboard/EvaluationScoreCard.vue";
import axios from "axios";
import { nextTick, onMounted, reactive, ref, computed } from "vue";
import { getAllCase, getEvalResult, generateCode } from "@/api/api.js";
import { appConfig } from "@/view/config.js";
import { parseEvaluation } from "@/utils/scoreUtils.js";
import html2canvas from 'html2canvas';  // 需要安装这个包
import { ExportUtils } from '@/utils/export';
import { useRouter } from 'vue-router'; // 导入useRouter

export default {
  name: "home",
  components: {
    preview,
    config,
    Output: output,
    QueryExpansionCard,
    RetrievalResultsCard,
    EvaluationScoreCard
  },
  setup() {
    const router = useRouter(); // 使用router
    const caseList = ref([])
    const info = reactive({
      message: '',
      timeout: 3000,
      snackbar: false
    })
    let isShowVis = ref(false)

    const isEvaluating = ref(false); // For loading state of the new button
    const isDashboardCollapsed = ref(false); // Dashboard collapse state
    const isGenerating = ref(false); // Global loading state for code generation

    const isExporting = ref(false);
    const currentCase = reactive({
      evalId: 0,
      prompt: '',
      // groundTruth: appConfig.testCode,
      groundTruth: 'Ground Truth:',
      // generatedCode: appConfig.testGeneratedCode,
      generatedCode: 'Generated Code:',
      evaluatorPrompt: appConfig.evaluator_prompt,
      generator: '',
      evaluator: '',
      evaluatorEvaluation: '',
      consoleOutput: [],
      workflow: {
        inquiryExpansion: false,
        rag: false,
      },
      evalUser: appConfig.eval_user,
      score: '',
      manualEvaluation: [],
      options: '',
      queryExpansion: '',
      retrievalResults: [],
      parsedEvaluation: null,  // New: Parsed evaluation data
      automatedExecutable: null,  // New: Automated check for executability
      automatedValidOutput: null  // New: Automated check for valid output

    })
    const resetCurrentCase = (obj) => {
      currentCase.evalId = obj['eval_id']
      currentCase.score = obj['score']
      currentCase.evalId = obj['eval_id']
      currentCase.generatedCode = obj['generated_code']
      currentCase.manualEvaluation = obj['manual_evaluation']
      currentCase.options = obj['options']
      currentCase.evaluatorEvaluation = obj['evaluator_evaluation']
      
      // Parse evaluation data if available
      if (obj['evaluator_evaluation']) {
        currentCase.parsedEvaluation = parseEvaluation(obj['evaluator_evaluation']);
      } else {
        currentCase.parsedEvaluation = null;
      }
      
      // Load automated checks if available
      if (obj['automated_executable'] !== undefined) {
        currentCase.automatedExecutable = obj['automated_executable'];
      }
      if (obj['automated_valid_output'] !== undefined) {
        currentCase.automatedValidOutput = obj['automated_valid_output'];
      }
    }


    const handleSeGenEnd = async (res) => {
      try {
        // Hide loading overlay
        isGenerating.value = false;
        
        currentCase.consoleOutput = []

        // Handle query expansion data
        if (res.analysis && res.analysis.trim() !== '') {
          currentCase.queryExpansion = res.analysis;
        } else {
          currentCase.queryExpansion = '';
        }

        // Handle retrieval results data
        if (res.retrieval_results && Array.isArray(res.retrieval_results)) {
          currentCase.retrievalResults = res.retrieval_results;
        } else {
          currentCase.retrievalResults = [];
        }

        resetCurrentCase(res)
        isShowVis.value = true;

        // Wait for preview components to render
        await nextTick();

        // Additional wait for VTK.js initialization
        await new Promise(resolve => setTimeout(resolve, 1000));

        // Only trigger evaluation if we have valid generated code
        if (currentCase.generatedCode && 
            currentCase.generatedCode !== 'Generated Code:' && 
            currentCase.generatedCode && 
            currentCase.generatedCode.trim() !== '') {
          // Start auto evaluation
          setTimeout(() => {
            triggerEvaluation();
          }, 1000);
        } else {
          info.message = '生成代码失败或为空，请检查';
          info.snackbar = true;
        }
      } catch (error) {
        console.error('Error handling generation results:', error);
        info.message = 'Error processing generation results';
        info.snackbar = true;
      } finally {
        // Ensure loading is hidden even if there's an error
        isGenerating.value = false;
      }
    }
    const setCurrentCase = (caseItem) => {
      // Show loading overlay when generation starts
      isGenerating.value = true;
      
      currentCase.prompt = caseItem.prompt
      currentCase.groundTruth = caseItem.groundTruth
      currentCase.generator = caseItem.generator
      currentCase.evaluator = caseItem.evaluator
      currentCase.evalUser = caseItem.evalUser
      currentCase.evaluatorPrompt = caseItem.evaluatorPrompt
      currentCase.workflow = caseItem.workflow
      // currentCase.currentGeneratedCode=currentGeneratedCode.value
    }


    const handleConsoleOutput = (output) => {
      nextTick(() => {
        // 累积日志而不是替换
        if (Array.isArray(output)) {
          currentCase.consoleOutput.push(...output);
        } else if (output) {
          currentCase.consoleOutput.push(output);
        }
        console.log('Current console logs:', currentCase.consoleOutput);
      });
    };
    const init = () => {
      getAllCase().then(res => {
        // console.log('caseList',res)
        caseList.value.push(...res.data)
      })
    }
    const handleVisibilityChange = (value) => {
      console.log("Visibility changed:", value.target.checked);
      isShowVis.value = value.target.checked
      // 在这里可以添加其他逻辑，例如更新组件显示状态
    };
    onMounted(() => {
      init()
    })
    const isFullScreen = ref(false);
    const generatedPreview = ref(null);
    const truthPreview = ref(null);

    const toggleFullScreen = async (type) => {
      const container = type === 'generated'
        ? generatedPreview.value.$el
        : truthPreview.value.$el;

      if (!document.fullscreenElement) {
        await container.requestFullscreen();
        isFullScreen.value = true;
      } else {
        await document.exitFullscreen();
        isFullScreen.value = false;
      }
    };
    const exportResults = async () => {
      try {
        isExporting.value = true;

        // 确保预览组件已经渲染完成
        await nextTick();

        // 获取预览组件实例
        const generatedPreviewInstance = generatedPreview.value; // Access .value for ref
        const truthPreviewInstance = truthPreview.value;         // Access .value for ref

        // 确保子组件实例存在
        if (!generatedPreviewInstance || !truthPreviewInstance) {
          throw new Error('无法获取预览组件实例');
        }

        // 直接从子组件实例获取 iframe 元素
        const generatedIframe = generatedPreviewInstance.previewFrame;
        const truthIframe = truthPreviewInstance.previewFrame;

        if (!generatedIframe || !truthIframe) {
          // 如果 iframe 元素没有找到，抛出更具体的错误
          throw new Error('无法获取预览 iframe 元素');
        }


        const result = await ExportUtils.exportResults(
          currentCase,
          {
            generatedPreviewEl: generatedIframe, // 直接传递 iframe 元素
            truthPreviewEl: truthIframe        // 直接传递 iframe 元素
          }
        );

        info.message = result.message;
        info.snackbar = true;
      } catch (error) {
        console.error('导出错误:', error);
        info.message = '导出失败: ' + error.message;
        info.snackbar = true;
      } finally {
        isExporting.value = false;
      }
    };

    const triggerEvaluation = async () => {
      if (!currentCase.generatedCode || currentCase.generatedCode === 'Generated Code:' || currentCase.generatedCode === null || currentCase.generatedCode.trim() === '') {
        info.message = '没有可评估的生成代码，请先生成代码';
        info.snackbar = true;
        console.warn('Cannot evaluate: no generated code available');
        return;
      }
      isEvaluating.value = true;
      info.message = '正在评估...';
      info.snackbar = true;
      try {
        const evalRes = await getEvalResult(currentCase);
        console.log('evaluation', evalRes.data);
        currentCase.score = evalRes.data['score'];
        currentCase.evaluatorEvaluation = evalRes.data['evaluator_evaluation'];
        
        // Parse the evaluation data
        currentCase.parsedEvaluation = parseEvaluation(evalRes.data['evaluator_evaluation']);
        
        // Store automated checks if available
        if (evalRes.data['automated_executable'] !== undefined) {
          currentCase.automatedExecutable = evalRes.data['automated_executable'];
        }
        if (evalRes.data['automated_valid_output'] !== undefined) {
          currentCase.automatedValidOutput = evalRes.data['automated_valid_output'];
        }
        
        info.message = '评估完成';
        info.snackbar = true;
      } catch (error) {
        console.error('评估失败:', error);
        const errorMessage = error.response?.data?.detail || error.response?.data?.error || error.message || '未知错误';
        info.message = '评估失败: ' + errorMessage;
        info.snackbar = true;
      } finally {
        isEvaluating.value = false;
      }
    };


    // Computed property for automated evaluation checks
    const automatedEvaluationChecks = computed(() => {
      return {
        executable: currentCase.automatedExecutable,
        validOutput: currentCase.automatedValidOutput
      };
    });

    // Handle manual evaluation submission
    const handleManualEvaluation = async (manualData) => {
      try {
        console.log('Manual evaluation submitted:', manualData);
        
        // Update local state
        currentCase.manualEvaluation = manualData;
        
        // Send to backend API
        const response = await axios.post(`${appConfig.api_base_url}/update_manual_evaluation`, {
          eval_id: currentCase.evalId,
          manual_evaluation: manualData
        });
        
        if (response.data.success) {
          info.message = '人工评估已保存';
          info.snackbar = true;
        }
      } catch (error) {
        console.error('Failed to save manual evaluation:', error);
        info.message = '保存人工评估失败: ' + (error.message || '未知错误');
        info.snackbar = true;
      }
    };

    // 监听全屏变化
    onMounted(() => {
      document.addEventListener('fullscreenchange', () => {
        isFullScreen.value = !!document.fullscreenElement;
      });
    });

    // Return all reactive variables and methods
    return {
      title: 'Rawsiv',
      caseList,
      handleSeGenEnd,
      setCurrentCase,
      currentCase,
      info,
      isShowVis,
      handleVisibilityChange,
      handleConsoleOutput,
      // Fullscreen related properties
      isFullScreen,
      generatedPreview,
      truthPreview,
      toggleFullScreen,
      isExporting,
      exportResults,
      triggerEvaluation,
      isEvaluating,
      isDashboardCollapsed,
      isGenerating, // Global loading state
      automatedEvaluationChecks,  // New: Automated checks computed property
      handleManualEvaluation,  // New: Manual evaluation handler
    };
  }
}
</script>

<style scoped>
.home {
  height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  /*align-items: center;*/
}

.head {
  height: 3vh;
  width: 100vw;
  display: flex;
  justify-content: space-between;
  /* 确保两端对齐 */
  align-items: center;
  /* 垂直居中 */
  padding: 10px;
  color: #333;
  font-weight: bold;
  background-color: #6ba4e6;
}

.dashboard {
  padding: 4px 16px;
  background-color: #fafafa;
  border-bottom: 1px solid #e0e0e0;
  transition: max-height 0.3s ease-in-out, padding 0.3s ease-in-out;
  position: relative;
  overflow: hidden;
}

.dashboard.collapsed {
  max-height: 60px;
  padding-bottom: 4px;
}

.dashboard:not(.collapsed) {
  max-height: 500px;
}

.dashboard-header {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 3.5vh;
  padding: 10px;
  color: #333;
  font-weight: bold;
  position: relative;
}

.dashboard-title {
  font-size: 16px;
  font-weight:bold;
  color: #333;
  transform: scale(1.2) ;
  flex: 1;
  text-align: center;
  /* background-color: #6ba4e6; */
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  position: absolute;
  right: 10px;
}

.collapse-btn {
  background: rgba(255, 255, 255, 0.7) !important;
  border-radius: 4px;
}

.dashboard-content {
  transition: opacity 0.2s ease;
  opacity: 1;
}

.dashboard.collapsed .dashboard-content {
  opacity: 0;
  pointer-events: none;
}

.container {
  flex: 1;
  display: flex;
  /*justify-content: space-around;*/
  /*flex: 10 2 auto;*/
  padding: 10px;
  overflow: hidden;
}


.left,
.right {
  padding: 10px;
  overflow-y: auto;
}

.left {
  flex: 1;
  min-width: 0;
}

.right {
  width: 320px;
  min-width: 280px;
  max-width: 400px;
  border-left: 1px solid #e0e0e0;
  background-color: #fafafa;
}

.config-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.preview {
  display: flex;
  flex-direction: row;
  justify-content: space-around;
  position: relative;
  /* 添加相对定位 */
}

.scrollable {
  overflow-y: auto;
  max-height: 80vh;
  border: 1px solid #ccc;
  padding: 10px;
  position: relative;
  /* 添加相对定位 */
}

.fullscreen-btn {
  position: absolute !important;
  top: 8px;
  right: 8px;
  z-index: 100;
  background: rgba(255, 255, 255, 0.7) !important;
  backdrop-filter: blur(4px);
}

.title {
  flex: 1;
  text-align: center;
}



.output {
  width: 100%;
  margin-top: 10px;
}

.output-container {
  position: relative;
  width: 100%;
}
.mini-switch {
  /* 核心：整体缩小组件到 0.75 倍 */
  transform: scale(0.75);
  /* 设定缩放原点为左侧居中，防止缩放后位置跑偏 */
  transform-origin: left center;
  /* 消除多余的边距，使布局更紧凑 */
  margin-left: -4px; 
}
.showVis{
  height: 2em;
}

/* Adjust the Switch's label text size and weight */
.mini-switch :deep(.v-label) {
  font-size: 14px; /* Increase font size to compensate for scaling */
  white-space: nowrap; /* Prevent text wrapping */
  margin-inline-start: 8px; /* Adjust spacing between text and switch */
}

/* Adjust the icon size inside the switch thumb */
.mini-switch :deep(.v-switch__thumb .v-icon) {
  font-size: 12px; /* Ensure icon is visible in the scaled thumb */
  color: #fff; /* Icon color, usually white looks good */
}

/* Loading Overlay Styles */
.loading-overlay {
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  background-color: rgba(0, 0, 0, 0.6);
  padding: 48px;
  border-radius: 8px;
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 10000;
}

.loading-text {
  color: #ffffff;
  font-size: 18px;
  font-weight: 500;
  margin: 0;
  letter-spacing: 0.5px;
}
</style>
