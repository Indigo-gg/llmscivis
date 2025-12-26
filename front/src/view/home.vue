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

    <!-- Main Header -->
    <div class="app-header">
      <span class="app-title">SivPilot</span>
      <div class="header-actions">
      </div>
    </div>

    <div class="container-main">
      <!-- Left Sidebar -->
      <div class="sidebar-left">
        <LeftSidebar 
          :query-expansion="currentCase.queryExpansion"
          :retrieval-results="currentCase.retrievalResults"
          @end="handleSeGenEnd"
          @getNewCase="setCurrentCase"
          @retrieval-complete="handleRetrievalComplete"
        />
      </div>

      <!-- Center: Code preview and output -->
      <div class="center">
        <div class="preview">
          <edit class="scrollable" :is-show-vis="isShowVis" :htmlContent="currentCase.generatedCode"
            :error-line="currentCase.errorLine" :error-message="currentCase.errorMessage"
            :editor-title="'Generated Code'"
            ref="generatedPreview" @console-output="handleConsoleOutput" @update:htmlContent="(val) => currentCase.generatedCode = val">
          </edit>
          <edit class="scrollable" :is-show-vis="isShowVis" :htmlContent="currentCase.groundTruth"
            :editor-title="'Ground Truth'"
            ref="truthPreview" @console-output="handleConsoleOutput" @update:htmlContent="(val) => currentCase.groundTruth = val">
            <template #actions>
              <v-switch v-model="isShowVis" :title="isShowVis ? 'Show Preview' : 'Hide Preview'" true-icon="mdi-eye" false-icon="mdi-eye-off"
                color="primary" density="compact" hide-details inset class="mini-switch"
                @change="handleVisibilityChange"></v-switch>
            </template>
          </edit>
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

      <!-- Right Sidebar -->
      <div class="sidebar-right">
        <RightSidebar 
          :score="currentCase.score" 
          :evaluation="currentCase.evaluatorEvaluation"
          :parsed-evaluation="currentCase.parsedEvaluation"
          :automated-checks="automatedEvaluationChecks"
          :manual-evaluation="currentCase.manualEvaluation"
          :eval-id="currentCase.evalId"
          :is-loading="isEvaluating"
          :is-generating="isGenerating"
          @trigger-evaluation="triggerEvaluation"
          @export-results="exportResults"
        />
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
import edit from "@/components/edit/index.vue";
import config from "@/components/config/index.vue";
import output from "@/components/output/index.vue"
import LeftSidebar from "@/components/sidebar/LeftSidebar.vue";
import RightSidebar from "@/components/sidebar/RightSidebar.vue";
import axios from "axios";
import { nextTick, onMounted, reactive, ref, computed, watch } from "vue";
import { getAllCase, getEvalResult, generateCode } from "@/api/api.js";
import { appConfig } from "@/view/config.js";
import { parseEvaluation } from "@/utils/scoreUtils.js";
import html2canvas from 'html2canvas';  // 需要安装这个包
import { ExportUtils } from '@/utils/export';
import { useRouter } from 'vue-router'; // 导入useRouter
import { saveCurrentCase, loadCurrentCase } from '@/utils/persistence.js';

export default {
  name: "home",
  components: {
    preview,
    edit,
    config,
    Output: output,
    LeftSidebar,
    RightSidebar
  },
  setup() {
    const router = useRouter(); // 使用router
    const info = reactive({
      message: '',
      timeout: 3000,
      snackbar: false
    })
    let isShowVis = ref(false)

    const isEvaluating = ref(false); // For loading state of the new button
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
      automatedValidOutput: null,  // New: Automated check for valid output
      // Error highlighting for editor
      errorLine: null,  // Line number where error occurred
      errorMessage: ''  // Error message to display

    })
    const resetCurrentCase = (obj) => {
      currentCase.evalId = obj['eval_id']
      currentCase.score = obj['score']
      currentCase.evalId = obj['eval_id']
      currentCase.generatedCode = obj['generated_code']
      currentCase.manualEvaluation = obj['manual_evaluation']
      currentCase.options = obj['options']
      currentCase.evaluatorEvaluation = obj['evaluator_evaluation']
      
      // Clear error highlighting when switching cases
      currentCase.errorLine = null;
      currentCase.errorMessage = '';
      
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
      
      // 自动保存当前案例数据
      saveCurrentCase(currentCase);
    }


    const handleSeGenEnd = async (res) => {
      try {
        // Hide loading overlay
        isGenerating.value = false;
        
        // 🧹 清空日志并释放内存
        currentCase.consoleOutput.length = 0; // 更高效的清空方式
        // Clear error highlighting when new code is generated
        currentCase.errorLine = null;
        currentCase.errorMessage = '';

        // Handle query expansion data - now it's structured data (array)
        if (res.analysis) {
          if (Array.isArray(res.analysis)) {
            currentCase.queryExpansion = res.analysis;
          } else if (typeof res.analysis === 'string' && res.analysis.trim() !== '') {
            // 如果是字符串，尝试解析
            try {
              currentCase.queryExpansion = JSON.parse(res.analysis);
            } catch (e) {
              currentCase.queryExpansion = [];
            }
          } else {
            currentCase.queryExpansion = [];
          }
        } else {
          currentCase.queryExpansion = [];
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
          info.message = 'Code generation failed or is empty, please check';
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

    // 处理检索完成事件
    const handleRetrievalComplete = (data) => {
      console.log('[Home] Retrieval completed with data:', data);
      
      // data 可能是数组或对象
      if (Array.isArray(data)) {
        // 简单数组格式
        currentCase.retrievalResults = data;
        console.log('[Home] Set retrievalResults (array):', data.length);
      } else if (data && typeof data === 'object') {
        // 对象格式，包含 retrieval_results 和 final_prompt
        currentCase.retrievalResults = data.retrieval_results || [];
        console.log('[Home] Set retrievalResults (object):', currentCase.retrievalResults.length);
        if (data.final_prompt) {
          currentCase.final_prompt = data.final_prompt;
        }
      }
      
      console.log('[Home] currentCase.retrievalResults:', currentCase.retrievalResults);
    }


    const handleConsoleOutput = (output) => {
      nextTick(() => {
        // 累积日志但限制最大数量，防止内存泄漏
        const MAX_CONSOLE_LOGS = 100; // 🔧 减少到 100 条，降低内存占用
        
        if (Array.isArray(output)) {
          currentCase.consoleOutput.push(...output);
        } else if (output) {
          currentCase.consoleOutput.push(output);
        }
        
        // 如果超过限制，删除旧的日志（批量删除更高效）
        if (currentCase.consoleOutput.length > MAX_CONSOLE_LOGS) {
          const removeCount = currentCase.consoleOutput.length - MAX_CONSOLE_LOGS;
          currentCase.consoleOutput.splice(0, removeCount);
        }
        
        console.log('Current console logs count:', currentCase.consoleOutput.length);
        
        // 提取错误行号并高亮
        const errorLogs = Array.isArray(output) ? output : [output];
        errorLogs.forEach(log => {
          if (log && log.type === 'error') {
            let lineNumber = null;
            
            // 优先使用直接传递的行号
            if (log.lineno && typeof log.lineno === 'number') {
              lineNumber = log.lineno;
              console.log('Using direct lineno:', lineNumber);
            } else {
              // 如果没有直接传递，尝试从错误消息中提取行号
              // 多种格式支持:
              // 1. "Error: ... (at http://localhost:5174/:26:42)"
              // 2. "Error: ... at line 26"
              // 3. "Uncaught TypeError: ... at <anonymous>:26:42"
              
              // 尝试匹配 URL 格式: :数字:数字)
              const urlMatch = log.message.match(/:([0-9]+):([0-9]+)\)/);
              if (urlMatch) {
                lineNumber = parseInt(urlMatch[1], 10);
              } else {
                // 尝试匹配 "at <anonymous>:行号:列号" 格式
                const anonymousMatch = log.message.match(/<anonymous>:([0-9]+):([0-9]+)/);
                if (anonymousMatch) {
                  lineNumber = parseInt(anonymousMatch[1], 10);
                } else {
                  // 尝试匹配 "at line 行号" 格式
                  const lineMatch = log.message.match(/at line ([0-9]+)/);
                  if (lineMatch) {
                    lineNumber = parseInt(lineMatch[1], 10);
                  }
                }
              }
            }
            
            if (lineNumber) {
              currentCase.errorLine = lineNumber;
              currentCase.errorMessage = log.message;
              console.log('Error detected at line:', lineNumber, 'Message:', log.message);
            }
          }
        });
      });
    };
    const handleVisibilityChange = (value) => {
      console.log("Visibility changed:", value.target.checked);
      isShowVis.value = value.target.checked
      // 在这里可以添加其他逻辑，例如更新组件显示状态
    };
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
        info.message = 'No generated code to evaluate, please generate code first';
        info.snackbar = true;
        console.warn('Cannot evaluate: no generated code available');
        return;
      }
      isEvaluating.value = true;
      info.message = 'Evaluating...';
      info.snackbar = true;
      try {
        // ⚠️ 只传递评估所需的最小数据集，避免传递大量日志和检索结果
        const evalData = {
          evalId: currentCase.evalId,
          generatedCode: currentCase.generatedCode,
          groundTruth: currentCase.groundTruth,
          evaluatorPrompt: currentCase.evaluatorPrompt,
          evaluator: currentCase.evaluator,
          generator: currentCase.generator,
          prompt: currentCase.prompt,
          workflow: currentCase.workflow,
          evalUser: currentCase.evalUser
          // 🚫 不传递 consoleOutput, retrievalResults, queryExpansion
        };
        const evalRes = await getEvalResult(evalData);
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
        
        info.message = 'Evaluation completed';
        info.snackbar = true;
      } catch (error) {
        console.error('Evaluation failed:', error);
        const errorMessage = error.response?.data?.detail || error.response?.data?.error || error.message || 'Unknown error';
        info.message = 'Evaluation failed: ' + errorMessage;
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

    // 恢复保存的案例数据
    const restoreSavedCase = () => {
      const savedCase = loadCurrentCase();
      if (savedCase) {
        console.log('Restoring saved case:', savedCase);
        
        // 使用 Object.assign 批量更新，减少触发次数
        // 先恢复非视觉相关的数据
        if (savedCase.evalId !== undefined) currentCase.evalId = savedCase.evalId;
        if (savedCase.prompt) currentCase.prompt = savedCase.prompt;
        if (savedCase.generator) currentCase.generator = savedCase.generator;
        if (savedCase.evaluator) currentCase.evaluator = savedCase.evaluator;
        if (savedCase.evaluatorEvaluation) currentCase.evaluatorEvaluation = savedCase.evaluatorEvaluation;
        if (savedCase.parsedEvaluation) currentCase.parsedEvaluation = savedCase.parsedEvaluation;
        if (savedCase.score) currentCase.score = savedCase.score;
        if (savedCase.workflow) currentCase.workflow = savedCase.workflow;
        if (savedCase.manualEvaluation) currentCase.manualEvaluation = savedCase.manualEvaluation;
        if (savedCase.automatedExecutable !== undefined) currentCase.automatedExecutable = savedCase.automatedExecutable;
        if (savedCase.automatedValidOutput !== undefined) currentCase.automatedValidOutput = savedCase.automatedValidOutput;
        
        // consoleOutput 需要限制大小
        if (savedCase.consoleOutput && Array.isArray(savedCase.consoleOutput)) {
          const MAX_CONSOLE_LOGS = 200;
          currentCase.consoleOutput = savedCase.consoleOutput.slice(-MAX_CONSOLE_LOGS);
        }
        
        // 延迟恢复可能触发大量渲染的数据
        nextTick(() => {
          // 恢复 queryExpansion 和 retrievalResults
          if (savedCase.queryExpansion) currentCase.queryExpansion = savedCase.queryExpansion;
          if (savedCase.retrievalResults) currentCase.retrievalResults = savedCase.retrievalResults;
          
          // 再延迟恢复代码内容和预览状态
          nextTick(() => {
            if (savedCase.groundTruth) currentCase.groundTruth = savedCase.groundTruth;
            if (savedCase.generatedCode) currentCase.generatedCode = savedCase.generatedCode;
            
            // 最后设置预览状态
            if (savedCase.generatedCode && savedCase.generatedCode !== 'Generated Code:') {
              nextTick(() => {
                isShowVis.value = true;
              });
            }
            
            info.message = 'Previous session recovered';
            info.snackbar = true;
          });
        });
      }
    };

    // 监听currentCase变化，自动保存（排除 consoleOutput 避免频繁触发）
    watch(
      () => ({
        evalId: currentCase.evalId,
        prompt: currentCase.prompt,
        groundTruth: currentCase.groundTruth,
        generatedCode: currentCase.generatedCode,
        generator: currentCase.generator,
        evaluator: currentCase.evaluator,
        evaluatorEvaluation: currentCase.evaluatorEvaluation,
        score: currentCase.score,
        workflow: currentCase.workflow,
        queryExpansion: currentCase.queryExpansion,
        retrievalResults: currentCase.retrievalResults,
        parsedEvaluation: currentCase.parsedEvaluation,
        manualEvaluation: currentCase.manualEvaluation
        // 注意：故意排除 consoleOutput，避免频繁触发保存
      }),
      () => {
        // 🛡️ 在评估期间暂停自动保存，避免内存压力
        if (isEvaluating.value) {
          console.log('Skipping auto-save during evaluation');
          return;
        }
        
        // 防抖保存
        if (saveCurrentCase.timeout) clearTimeout(saveCurrentCase.timeout);
        saveCurrentCase.timeout = setTimeout(() => {
          saveCurrentCase(currentCase);
          console.log('Current case auto-saved');
        }, 3000); // 🔧 进一步增加延迟到 3 秒
      },
      { deep: true }
    );

    // 监听全屏变化
    onMounted(() => {
      document.addEventListener('fullscreenchange', () => {
        isFullScreen.value = !!document.fullscreenElement;
      });
      
      // 页面加载时恢复保存的数据 (temporarily disabled)
      // setTimeout(() => {
      //   restoreSavedCase();
      // }, 500);
    });

    // Return all reactive variables and methods
    return {
      title: 'SivPilot',
      handleSeGenEnd,
      setCurrentCase,
      handleRetrievalComplete,
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
      isGenerating, // Global loading state
      automatedEvaluationChecks,  // New: Automated checks computed property
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
  justify-content: flex-start;
  background-color: #f8fafc;
}

/* App Header - Compact */
.app-header {
  height: 36px;
  padding: 0 12px;
  background-color: #1e293b;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.app-title {
  font-size: 14px;
  font-weight: 600;
  color: #f1f5f9;
  letter-spacing: 0.5px;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.showVis {
  height: 1.5em;
}

.mini-switch {
  transform: scale(0.75);
  transform-origin: right center;
  margin-right: -4px;
}

.mini-switch :deep(.v-label) {
  font-size: 12px;
  white-space: nowrap;
  margin-inline-start: 4px;
}

.mini-switch :deep(.v-switch__thumb .v-icon) {
  font-size: 10px;
  color: #fff;
}

/* Main Container - No gaps */
.container-main {
  flex: 1;
  display: flex;
  overflow: hidden;
  gap: 0;
  padding: 0;
  background-color: #f8fafc;
}

/* Sidebar Left - Seamless */
.sidebar-left {
  width: 280px;
  min-width: 260px;
  max-width: 320px;
  background-color: #ffffff;
  border-right: 1px solid #e2e8f0;
  overflow: hidden;
  flex-shrink: 0;
}

/* Center Area - Fill space */
.center {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
  background-color: #f8fafc;
}

.preview {
  flex: 1;
  display: flex;
  flex-direction: row;
  gap: 1px;
  position: relative;
  overflow: hidden;
  background-color: #e2e8f0;
}

.scrollable {
  flex: 1;
  overflow-y: auto;
  border: none;
  padding: 0;
  position: relative;
  min-width: 0;
  background-color: #ffffff;
}

.fullscreen-btn {
  position: absolute !important;
  top: 4px;
  right: 4px;
  z-index: 100;
  background: rgba(255, 255, 255, 0.8) !important;
  backdrop-filter: blur(4px);
}

/* Output - Minimal */
.output {
  flex-shrink: 0;
  background-color: #ffffff;
  overflow-y: auto;
  max-height: 25vh;
  border-top: 1px solid #e2e8f0;
}

.output-container {
  position: relative;
  width: 100%;
  padding: 0;
}

/* Sidebar Right - Seamless */
.sidebar-right {
  width: 280px;
  min-width: 260px;
  max-width: 320px;
  background-color: #ffffff;
  border-left: 1px solid #e2e8f0;
  overflow: hidden;
  flex-shrink: 0;
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
  gap: 16px;
  background-color: rgba(30, 41, 59, 0.85);
  padding: 32px 48px;
  border-radius: 8px;
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 10000;
}

.loading-text {
  color: #f1f5f9;
  font-size: 14px;
  font-weight: 500;
  margin: 0;
  letter-spacing: 0.3px;
}
</style>
