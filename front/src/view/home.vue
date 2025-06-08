<template>

  <div class="home">
    <div class="head">
      <div class="title-left">
        <v-btn icon="mdi-export" size="middle" variant="text" @click="go2Export">
          export-cases
        </v-btn>
      </div>
      <div class="title">
        {{ title }}
      </div>
      <!-- 移除原来的导出按钮 -->
      <div class="setting">
        <!-- 添加导出按钮 -->

        <div class="showVis">
          <v-switch v-model="isShowVis" hide-details inset :label="isShowVis ? 'Visible' : 'Hidden'"
            @change="handleVisibilityChange"></v-switch>
        </div>
        <div class="enableEval">

          <v-btn icon="mdi-play-circle-outline" size="small" variant="text" @click="triggerEvaluation"
            :loading="isEvaluating" title="手动评估">
            评估
          </v-btn>
        </div>
        <div class="export">
          <v-btn icon="mdi-export" size="large" variant="text" @click="exportResults" class="export-btn"
            title="export result">
            export
          </v-btn>
        </div>
      </div>
    </div>
    <div class="container">
      <div class="left">
        <div class="iteration-status" v-if="currentCase.workflow.iterativeLoop">
          <v-chip :color="currentCase.errorCount > 0 ? 'warning' : 'success'" class="ma-2">
            迭代次数: {{ currentCase.errorCount }}/{{ currentCase.maxIterations }}
          </v-chip>
          <v-progress-linear v-if="isIterating" indeterminate color="primary" class="mb-2"></v-progress-linear>
        </div>
        <div class="preview">
          <edit class="scrollable" :is-show-vis="isShowVis" :htmlContent="currentCase.generatedCode"
            @console-output="handleConsoleOutput" ref="generatedPreview">
            <v-btn v-if="isShowVis" :icon="isFullScreen ? 'mdi-fullscreen-exit' : 'mdi-fullscreen'" size="small"
              variant="text" @click="toggleFullScreen('generated')" class="fullscreen-btn"></v-btn>
          </edit>
          <preview class="scrollable" :is-show-vis="isShowVis" :htmlContent="currentCase.groundTruth"
            ref="truthPreview">
            <template #actions>
              <v-btn v-if="isShowVis" :icon="isFullScreen ? 'mdi-fullscreen-exit' : 'mdi-fullscreen'" size="small"
                variant="text" @click="toggleFullScreen('truth')" class="fullscreen-btn"></v-btn>
            </template>
          </preview>
        </div>
        <!-- 在输出组件部分添加导出按钮 -->
        <div class="output">
          <div class="output-container">
            <Output :console-output="currentCase.consoleOutput" :evaluator-output="currentCase.evaluatorEvaluation"
              :trigger-error-analysis="triggerErrorAnalysis">
              <template #actions>
                <div class="output-buttons-container">
                  <v-btn v-if="currentCase.consoleOutput && currentCase.consoleOutput.some(log => log.type === 'error')"
                    icon="mdi-auto-fix" size="small" color="warning" variant="tonal" @click="triggerErrorAnalysis"
                    :loading="isAnalyzingError" class="error-analysis-btn" title="分析错误">
                  </v-btn>
                  <!-- </template> -->

                </div>
              </template>

            </Output>
          </div>
          <!-- 在模板中添加错误详情展示 -->
          <div v-if="currentCase.errorAnalysisSuggestion" class="error-analysis-container pa-2 mt-2">
            <div class="error-summary mb-2" style="border-bottom: 1px solid #eee; padding-bottom: 8px;">
              <h4>错误分析摘要</h4>
              <div v-if="currentCase.errorSummary">
                <div>总迭代次数: {{ currentCase.errorSummary.total_iterations }}</div>
                <div>是否已解决: {{ currentCase.errorSummary.resolved ? '是' : '否' }}</div>
              </div>
            </div>

            <div class="error-details mb-2">
              <h4>错误详情</h4>
              <v-expansion-panels v-if="currentCase.errorDetails.length">
                <v-expansion-panel v-for="(error, index) in currentCase.errorDetails" :key="index">
                  <v-expansion-panel-title>
                    {{ error.type }} - {{ error.severity }}级错误
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <div>描述: {{ error.description }}</div>
                    <div v-if="error.location.line >= 0">
                      位置: 第{{ error.location.line }}行, 第{{ error.location.column }}列
                    </div>
                    <div v-if="error.location.context">
                      上下文: {{ error.location.context }}
                    </div>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
            </div>

            <div class="fix-suggestion mb-2">
              <h4>修复建议</h4>
              <pre style="white-space: pre-wrap; word-wrap: break-word;">{{ currentCase.errorAnalysisSuggestion }}</pre>
            </div>
          </div>
          <!-- Display error analysis result -->
          <div v-if="currentCase.errorAnalysisSuggestion" class="error-analysis-suggestion pa-2 mt-2"
            style="border: 1px solid #ccc; border-radius: 4px; background-color: #f9f9f9; max-height: 200px; overflow-y: auto;">
            <h4 class="mb-1">代码修改建议:</h4>
            <pre style="white-space: pre-wrap; word-wrap: break-word;">{{ currentCase.errorAnalysisSuggestion }}</pre>
          </div>
        </div>
      </div>
      <div class="right">
        <config :case-list="caseList" @end="handleSeGenEnd" @getNewCase="setCurrentCase">
        </config>
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
import axios from "axios";
import { nextTick, onMounted, reactive, ref } from "vue";
import { getAllCase, getEvalResult, generateCode, handleCodeError, handleErrorAnalysis } from "@/api/api.js";
import { appConfig } from "@/view/config.js";
import html2canvas from 'html2canvas';  // 需要安装这个包
import { ExportUtils } from '@/utils/export';
import { useRouter } from 'vue-router'; // 导入useRouter

export default {
  name: "home",
  components: {
    preview,
    config,
    edit,
    Output: output
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

    const isExporting = ref(false);
    const isAnalyzingError = ref(false); // New ref
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
        iterativeLoop: false,
      },
      evalUser: appConfig.eval_user,
      score: '',
      manualEvaluation: [],
      options: '',
      errorAnalysisSuggestion: '', // 错误修复建议
      errorDetails: [], // 错误详细信息
      errorSummary: {}, // 错误分析摘要
      maxIterations: 3

    })
    const resetCurrentCase = (obj) => {
      currentCase.evalId = obj['eval_id']
      currentCase.score = obj['score']
      currentCase.evalId = obj['eval_id']
      currentCase.generatedCode = obj['generated_code']
      currentCase.manualEvaluation = obj['manual_evaluation']
      currentCase.options = obj['options']
      currentCase.evaluatorEvaluation = obj['evaluator_evaluation']
    }
    const isIterating = ref(false);

    const handleSeGenEnd = async (res) => {
      try {
        currentCase.consoleOutput = []
        if (currentCase.workflow.iterativeLoop) {
          currentCase.errorCount = 0
          currentCase.maxIterations = 3
        }
        resetCurrentCase(res)
        isShowVis.value = true;

        // 等待预览组件渲染完成
        await nextTick();

        // 额外等待一段时间确保 VTK.js 初始化完成
        await new Promise(resolve => setTimeout(resolve, 1000));

        //启动自动评估
        setTimeout(() => {
          triggerEvaluation();
        }, 1000);
        // 现在检查错误
        const hasError = res.error ||
          (res.options && res.options.error_log) ||
          currentCase.consoleOutput.some(log => log.type === 'error');

        console.log('hasError', hasError, 'currentCase.workflow.iterativeLoop', currentCase.workflow.iterativeLoop,
          'currentCase.errorCount', currentCase.errorCount, 'currentCase.maxIterations', currentCase.maxIterations);

        // 如果有错误，先进行错误分析
        if (hasError) {
          let errors = [];
          if (res.error) {
            errors.push({ type: 'error', message: res.error });
          }
          if (res.options && res.options.error_log) {
            errors.push({ type: 'error', message: res.options.error_log });
          }
          if (currentCase.consoleOutput.length > 0) {
            errors.push(...currentCase.consoleOutput.filter(log => log.type === 'error'));
          }

          // 调用错误分析接口
          handleCodeError({
            errors: errors,
            current_code: currentCase.generatedCode
          }).then(analysisRes => {
            if (analysisRes.data.success) {
              currentCase.errorAnalysisSuggestion = analysisRes.data.suggestion;
              currentCase.errorDetails = analysisRes.data.errors;
              if (analysisRes.data.new_code) {
                currentCase.generatedCode = analysisRes.data.new_code;
              }
              info.message = '错误分析完成';
              info.snackbar = true;
            } else {
              info.message = '错误分析失败';
              info.snackbar = true;
            }
          });
        }


        // 如果开启了迭代循环，则进行代码优化
        if (currentCase.workflow.iterativeLoop) {
          isIterating.value = true;  // 开始迭代
          if (currentCase.errorCount < currentCase.maxIterations) {
            currentCase.errorCount++
            info.message = `代码存在错误，正在进行第${currentCase.errorCount}次优化...`
            info.snackbar = true

            let errors = []
            if (res.error) {
              errors.push({ type: 'error', message: res.error })
            }
            if (res.options && res.options.error_log) {
              errors.push({ type: 'error', message: res.options.error_log })
            }
            if (currentCase.consoleOutput.length > 0) {
              errors.push(...currentCase.consoleOutput.filter(log => log.type === 'error'))
            }

            // 调用错误分析接口
            handleCodeError({
              errors: errors,
              current_code: currentCase.generatedCode
            }).then(analysisRes => {
              if (analysisRes.data.errors && analysisRes.data.errors.length > 0) {
                // 使用新的代码继续迭代
                currentCase.generatedCode = analysisRes.data.new_code
                info.message = `正在应用优化建议...`
                info.snackbar = true
                handleSeGenEnd({
                  ...res,
                  generated_code: analysisRes.data.new_code
                })
              } else {
                isIterating.value = false;  // 迭代完成
                info.message = `代码已优化完成`
                info.snackbar = true

              }
            })
            return
          } else {
            isIterating.value = false;  // 达到最大迭代次数
            info.message = '已达到最大迭代次数'
            info.snackbar = true
          }
        } else {
          isIterating.value = false;  // 无需迭代
        }
      } catch (error) {
        console.error('处理生成结果时出错:', error);
        info.message = '处理生成结果时出错';
        info.snackbar = true;
        isIterating.value = false;
      }
    }
    const setCurrentCase = (caseItem) => {
      currentCase.prompt = caseItem.prompt
      currentCase.groundTruth = caseItem.groundTruth
      currentCase.generator = caseItem.generator
      currentCase.evaluator = caseItem.evaluator
      currentCase.evalUser = caseItem.evalUser
      currentCase.evaluatorPrompt = caseItem.evaluatorPrompt
      currentCase.workflow = caseItem.workflow
      // currentCase.currentGeneratedCode=currentGeneratedCode.value
    }
    // error - record页面
    const go2Export = () => {
      console.log('go2Export')
      router.push('/error-record');
    };

    const handleConsoleOutput = (output) => {

      nextTick(() => {
        // 在这里处理控制台输出
        console.log('handleConsoleOutput', currentCase.consoleOutput)
        currentCase.consoleOutput = output
      })
      // 在这里处理控制台输出
      // console.log('handleConsoleOutput',currentCase.consoleOutput)
      // currentCase.consoleOutput=output
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
        info.message = '没有可评估的生成代码';
        info.snackbar = true;
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
    const triggerErrorAnalysis = async () => {
      if (!currentCase.consoleOutput || currentCase.consoleOutput.length === 0) {
        info.message = '没有控制台日志可供分析';
        info.snackbar = true;
        return;
      }
      const errorLogs = currentCase.consoleOutput.filter(log => log.type === 'error');
      if (errorLogs.length === 0) {
        info.message = '控制台日志中没有发现错误信息';
        info.snackbar = true;
        return;
      }

      isAnalyzingError.value = true;
      currentCase.errorAnalysisSuggestion = ''; // 清空旧的建议
      try {
        const payload = {
          errors: errorLogs, // 发送包含类型和消息的错误对象数组
          current_code: currentCase.generatedCode
        };
        const res = await handleErrorAnalysis(payload);
        if (res.data && res.data.success) {
          currentCase.errorAnalysisSuggestion = res.data.suggestion;
          currentCase.errorDetails = res.data.errors;
          currentCase.errorSummary = res.data.error_summary;

          if (res.data.new_code) {
            currentCase.generatedCode = res.data.new_code;
          }
          info.message = '错误分析完成';
          info.snackbar = true;
        } else {
          info.message = '错误分析失败';
          info.snackbar = true;
        }
      } catch (error) {
        console.error('调用错误分析接口失败:', error);
        const errorMessage = error.response?.data?.detail || error.response?.data?.error || error.message || '未知错误';
        currentCase.errorAnalysisSuggestion = `调用分析接口失败: ${errorMessage}`;
        info.message = `错误分析接口请求失败: ${errorMessage}`;
        info.snackbar = true;
      } finally {
        isAnalyzingError.value = false;
      }
    };

    // 监听全屏变化
    onMounted(() => {
      document.addEventListener('fullscreenchange', () => {
        isFullScreen.value = !!document.fullscreenElement;
      });
    });

    // 在 return 中添加新的属性
    return {
      title: 'Vtkjs Evaluator',
      caseList,
      handleSeGenEnd,
      setCurrentCase,
      currentCase,
      info,
      isShowVis,
      handleVisibilityChange,
      handleConsoleOutput,
      // 添加全屏相关的属性
      isFullScreen,
      generatedPreview,
      truthPreview,
      toggleFullScreen,
      isExporting,
      exportResults,
      triggerErrorAnalysis,
      isAnalyzingError,
      triggerEvaluation,
      isEvaluating,
      go2Export, // 添加go2Export函数
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
  height: 10vh;
  width: 100vw;
  display: flex;
  justify-content: space-between;
  /* 确保两端对齐 */
  align-items: center;
  /* 垂直居中 */
  padding: 10px;
  background-color: #f0f0f0;
}

.container {
  height: 90vh;
  display: flex;
  /*justify-content: space-around;*/
  /*flex: 10 2 auto;*/
  padding: 10px;
}


.left,
.right {
  padding: 10px;
  overflow-y: scroll;
}

.left {
  flex: 10;
}

.right {
  flex: 2;
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

.head .title-left {
  flex: 2;
  display: flex;
  gap: 16px;
  align-items: center;
}

.title {
  flex: 7;
}

.head .setting {
  flex: 3;
  display: flex;
  gap: 8px;
  align-items: center;
}

.iteration-status {
  padding: 8px;
  margin-bottom: 16px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.iteration-status .v-chip {
  margin-right: 8px;
}

.output-container {
  position: relative;
  width: 100%;
}

.output-buttons-container {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  gap: 8px;
  z-index: 10;
}

.error-analysis-btn {
  margin: 4px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.error-analysis-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.export-btn {
  position: absolute !important;
  top: 8px;
  right: 16px;
  z-index: 100;
  background: rgba(255, 255, 255, 0.7) !important;
  backdrop-filter: blur(4px);
}
</style>
