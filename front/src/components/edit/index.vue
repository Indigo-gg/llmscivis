<template>
  <div class="preview-container" :class="{ 'fullscreen': isFullscreen }">
    <!-- Title Bar -->
    <div class="editor-title-bar">
      <div class="title-left">
        <div class="mac-buttons">
          <span class="mac-dot red"></span>
          <span class="mac-dot yellow"></span>
          <span class="mac-dot green"></span>
        </div>
        <h3 class="editor-title">{{ editorTitle }}</h3>
      </div>
      <div class="title-actions">
        <!-- 插槽用于放置按钮 -->
        <slot name="actions"></slot>
      </div>
    </div>

    <!-- Content Area -->
    <div class="content-wrapper">
      <div v-if="!isShowVis" class="code-area">
        <div v-if="hasContent" class="monaco-wrapper" ref="editorContainer"></div>
        <div v-else class="empty-state">
          <div class="empty-icon-bg">
            <!-- 假设你有 v-icon 组件，如果没有可以用 svg 代替 -->
            <slot name="empty-icon">
              <svg style="width:48px;height:48px;color:#cbd5e1" viewBox="0 0 24 24">
                <path fill="currentColor"
                  d="M14.6,16.6L19.2,12L14.6,7.4L16,6L22,12L16,18L14.6,16.6M9.4,16.6L4.8,12L9.4,7.4L8,6L2,12L8,18L9.4,16.6Z" />
              </svg>
            </slot>
          </div>
          <p class="empty-text">Waiting for code generation...</p>
        </div>
      </div>

      <div v-else class="preview-area">
        <iframe ref="previewFrame" sandbox="allow-scripts allow-same-origin allow-top-navigation" class="preview-iframe"
          src="about:blank" frameBorder="0"></iframe>
      </div>
    </div>
  </div>
</template>

<script>
import { onMounted, nextTick, ref, watch, computed, onBeforeUnmount } from 'vue';
import * as monaco from 'monaco-editor';

export default {
  name: 'ModernEditor',
  emits: ['error', 'console-output', 'update:htmlContent'],
  props: {
    htmlContent: {
      type: String,
      required: true,
    },
    isShowVis: {
      type: Boolean,
      default: false
    },
    // 新增：编辑器标题
    editorTitle: {
      type: String,
      default: 'Generated Code'
    },
    // 新增：报错行号 (从1开始)
    errorLine: {
      type: Number,
      default: null
    },
    // 新增：报错具体信息
    errorMessage: {
      type: String,
      default: ''
    }
  },
  setup(props, { emit }) {
    const editorContainer = ref(null);
    const previewFrame = ref(null);
    const isFullscreen = ref(false);

    let editor = null;
    let decorationIds = []; // 用于存储高亮的ID，以便清除
    let currentMessageHandler = null; // 存储当前的消息处理器引用，用于正确清理
    const iframeId = `iframe_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`; // 唯一标识符
    let lastLoadedContent = null; // 防止重复加载相同内容
    let isLoadingIframe = false; // 防止并发加载

    const hasContent = computed(() => {
      return props.htmlContent &&
        props.htmlContent.trim() !== '' &&
        props.htmlContent !== 'Ground Truth:' &&
        props.htmlContent !== 'Generated Code:';
    });

    function initEditor() {
      destroyEditor();
      if (editorContainer.value && hasContent.value) {
        // 在 initEditor 函数内
        editor = monaco.editor.create(editorContainer.value, {
          value: extractHtmlCode(props.htmlContent),
          language: 'html',
          theme: 'vs-light',
          automaticLayout: true,
          minimap: { enabled: false },
          fontSize: 14,
          fontFamily: "'Fira Code', 'JetBrains Mono', 'Consolas', monospace",

          // --- 修改重点开始 ---


          // 1. 行号设置：只保留最窄宽度
          lineNumbers: 'on',
          lineNumbersMinChars: 3, // 保持最小宽度，防止行号跳动

          // 2. 彻底关闭侧边栏的所有额外功能
          glyphMargin: false,        // 关闭字形边缘（红点断点处）
          folding: false,            // 关闭代码折叠（减号箭头）
          lineDecorationsWidth: 0,   // [关键] 强制装饰区宽度为0
          lineNumbersWidth: undefined, // 确保删除此行，让其自动计算

          // 3. 视觉优化
          renderLineHighlight: 'line', // 只高亮行内容，不包含侧边栏，减少视觉分割感
          guides: {
            indentation: true // 保持缩进线，但我们需要确保代码本身没缩进
          },


          // 6. [关键] 删除这一行！不要固定宽度！
          // lineNumbersWidth: 40,  <-- 删除它

          // --- 修改重点结束 ---

          scrollBeyondLastLine: false,
          roundedSelection: true,
          readOnly: false,
          cursorStyle: 'line',
          wordWrap: 'on',
          padding: { top: 8, bottom: 8 },
          renderLineHighlight: 'all',
          smoothScrolling: true,
          scrollbar: {
            useShadows: false,
            verticalScrollbarSize: 8,
            horizontalScrollbarSize: 8,
            vertical: 'auto',
            horizontal: 'auto'
          },
        });

        editor.onDidChangeModelContent(() => {
          const newValue = editor.getValue();
          if (newValue !== props.htmlContent) {
            emit('update:htmlContent', newValue);
          }
        });

        // 初始化时如果已有报错，立即显示
        if (props.errorLine && props.errorMessage) {
          updateErrorHighlight(props.errorLine, props.errorMessage);
        }
      }
    }

    function destroyEditor() {
      if (editor) {
        editor.dispose();
        editor = null;
      }
    }

    // 核心功能：处理报错高亮
    function updateErrorHighlight(line, msg) {
      if (!editor) return;

      const model = editor.getModel();

      // 1. 清除旧的高亮和标记
      editor.removeDecorations(decorationIds);
      monaco.editor.setModelMarkers(model, 'owner', []);

      if (!line || line <= 0) return;

      // 2. 添加波浪线标记 (Markers) - 鼠标悬浮会显示错误信息
      monaco.editor.setModelMarkers(model, 'owner', [{
        startLineNumber: line,
        startColumn: 1,
        endLineNumber: line,
        endColumn: model.getLineContent(line).length + 1,
        message: msg || 'Error occurred here',
        severity: monaco.MarkerSeverity.Error
      }]);

      // 3. 添加整行背景色高亮 (Decorations)
      decorationIds = editor.deltaDecorations([], [
        {
          range: new monaco.Range(line, 1, line, 1),
          options: {
            isWholeLine: true,
            className: 'myErrorLineDecoration', // 对应 CSS 中的样式
            glyphMarginClassName: 'myErrorGlyphMargin'
          }
        }
      ]);

      // 4. 滚动到错误行
      editor.revealLineInCenter(line);
    }

    // 监听报错属性变化
    watch([() => props.errorLine, () => props.errorMessage], ([newLine, newMsg]) => {
      if (!props.isShowVis) {
        // 只有在代码视图才高亮
        nextTick(() => {
          updateErrorHighlight(newLine, newMsg);
        });
      }
    });

    onMounted(() => {
      initEditor();
    });

    onBeforeUnmount(() => {
      destroyEditor();
      // 清理消息监听器，防止内存泄漏
      if (currentMessageHandler) {
        window.removeEventListener('message', currentMessageHandler);
        currentMessageHandler = null;
      }
    });

    function extractHtmlCode(input) {
      const regex = /```html([\s\S]*?)```/;
      const match = input.match(regex);
      // 如果没匹配到，就用原文本；匹配到了就取第一组
      let code = match ? match[1] : input;

      // 1. 移除首尾的空行，防止第一行就是个换行符
      code = code.replace(/^\n+/, '').replace(/\s+$/, '');

      // 2. 将代码按行分割
      const lines = code.split('\n');

      // 3. 计算最小缩进量 (忽略空行)
      let minIndent = Infinity;
      for (const line of lines) {
        // 只检查非空行
        if (line.trim().length > 0) {
          // 获取当前行开头的空格数量
          const indentMatch = line.match(/^\s*/);
          const currentIndent = indentMatch ? indentMatch[0].length : 0;
          if (currentIndent < minIndent) {
            minIndent = currentIndent;
          }
        }
      }

      // 4. 如果存在公共缩进，则每行都切掉这部分
      if (minIndent > 0 && minIndent !== Infinity) {
        code = lines.map(line => {
          // 如果这一行长度甚至小于缩进量（通常是空行），直接返回空
          if (line.length < minIndent) return '';
          return line.substring(minIndent);
        }).join('\n');
      }

      return code.trim();
    }

    function loadHtmlContentIntoIframe() {
      try {
        const iframe = previewFrame.value;
        if (!iframe) return;

        const doc = iframe.contentDocument || iframe.contentWindow.document;
        let content = extractHtmlCode(props.htmlContent);
        
        // 防止重复加载相同内容
        if (lastLoadedContent === content && !isLoadingIframe) {
          console.log('Skipping duplicate iframe load for:', props.editorTitle);
          return;
        }
        
        // 防止并发加载
        if (isLoadingIframe) {
          console.log('Already loading iframe, skipping for:', props.editorTitle);
          return;
        }
        
        isLoadingIframe = true;
        lastLoadedContent = content;

        // 1. 定义监控脚本
        const consoleScript = (
          'window.onerror = function(message, source, lineno, colno, error) {\n' +
          '  window.parent.postMessage({\n' +
          '    type: "console",\n' +
          '    logType: "error",\n' +
          '    message: "Error: " + message + " (at " + source + ":" + lineno + ":" + colno + ")",\n' +
          '    lineno: lineno,\n' +
          '    colno: colno,\n' +
          '    timestamp: new Date().toISOString()\n' +
          '  }, "*");\n' +
          '  return false;\n' +
          '};\n' +
          'window.addEventListener("unhandledrejection", function(event) {\n' +
          '  let message = "Unhandled Promise Rejection: ";\n' +
          '  let lineno = null;\n' +
          '  let colno = null;\n' +
          '  \n' +
          '  if (event.reason) {\n' +
          '    if (event.reason instanceof Error) {\n' +
          '      message += event.reason.message;\n' +
          '      if (event.reason.stack) {\n' +
          '        const stackMatch = event.reason.stack.match(/:([0-9]+):([0-9]+)/);\n' +
          '        if (stackMatch) {\n' +
          '          lineno = parseInt(stackMatch[1], 10);\n' +
          '          colno = parseInt(stackMatch[2], 10);\n' +
          '          message += " (at line " + lineno + ":" + colno + ")";\n' +
          '        }\n' +
          '      }\n' +
          '    } else {\n' +
          '      message += String(event.reason);\n' +
          '    }\n' +
          '  }\n' +
          '  \n' +
          '  window.parent.postMessage({\n' +
          '    type: "console",\n' +
          '    logType: "error",\n' +
          '    message: message,\n' +
          '    lineno: lineno,\n' +
          '    colno: colno,\n' +
          '    timestamp: new Date().toISOString()\n' +
          '  }, "*");\n' +
          '});\n' +
          '["log", "info", "warn", "error", "debug", "trace"].forEach(type => {\n' +
          '  const originalConsole = console[type];\n' +
          '  console[type] = function(...args) {\n' +
          '    const processedArgs = args.map(arg => {\n' +
          '      if (arg === null) return "null";\n' +
          '      if (arg === undefined) return "undefined";\n' +
          '      if (typeof arg === "object") {\n' +
          '        try { \n' +
          '          return JSON.stringify(arg);\n' +
          '        } catch(e) { \n' +
          '          return String(arg);\n' +
          '        }\n' +
          '      }\n' +
          '      return String(arg);\n' +
          '    });\n' +
          '    originalConsole.apply(this, args);\n' +
          '    window.parent.postMessage({\n' +
          '      type: "console",\n' +
          '      logType: type,\n' +
          '      message: processedArgs.join(" "),\n' +
          '      timestamp: new Date().toISOString()\n' +
          '    }, "*");\n' +
          '  };\n' +
          '});'
        );

        // 2. [关键] 智能注入逻辑：将脚本插入到现有的 <head> 中
        let finalHtml = '';
        let injectedLineOffset = 0;

        // 准备要注入的脚本标签字符串，强制加上换行符以便计算行数
        const scriptToInject = `<script>\n${consoleScript}\n<\/script>\n`;
        // 计算注入脚本占用的行数
        const scriptLinesCount = scriptToInject.split('\n').length - 1;

        if (content.includes('<head>')) {
          // 情况 A: 这是一个完整的 HTML，包含 <head>
          // 我们把脚本注入到 <head> 标签之后
          
          // 1. 找到 <head> 在原始内容中的位置
          const headIndex = content.indexOf('<head>');
          const beforeHead = content.substring(0, headIndex + 6); // +6 是 '<head>' 的长度
          
          // 2. 计算 <head> 之前有多少行（包括 <head> 这一行）
          const linesBeforeInjection = beforeHead.split('\n').length;
          
          // 3. 注入脚本
          finalHtml = content.replace('<head>', `<head>\n${scriptToInject}`);
          
          // 4. 偏移量 = <head> 之前的行数 + 注入脚本的行数 - 1
          // 因为用户代码从 <head> 的下一行开始，而注入的脚本会把用户代码向下推
          injectedLineOffset = linesBeforeInjection + scriptLinesCount - 1;
          
          console.log('Debug - Head position:', {
            headIndex,
            linesBeforeInjection,
            scriptLinesCount,
            calculatedOffset: injectedLineOffset
          });
        } else if (content.includes('<html>')) {
          // 情况 B: 有 html 但没写 head，注入到 html 之后
          finalHtml = content.replace('<html>', `<html><head>\n${scriptToInject}</head>`);
          injectedLineOffset = scriptLinesCount;
        } else {
          // 情况 C: 只是片段代码 (Fragment)，没有 DOCTYPE/HTML 标签
          const htmlStart = '<!DOCTYPE html><html><head>';
          const bodyStart = '</head><body>';
          const bodyEnd = '</body></html>';
          finalHtml = htmlStart + scriptToInject + bodyStart + content + bodyEnd;
          
          // 计算 Offset: 头部标签行数 + 注入脚本行数 + bodyStart行数
          const prefix = htmlStart + scriptToInject + bodyStart;
          injectedLineOffset = prefix.split('\n').length - 1;
        }

        // 3. 写入 iframe
        doc.open();
        doc.write(finalHtml);
        doc.close();
        
        console.log('Debug - scriptLinesCount:', scriptLinesCount);
        console.log('Debug - injectedLineOffset:', injectedLineOffset);

        // 4. 先清理旧的消息监听器（关键！防止内存泄漏）
        if (currentMessageHandler) {
          window.removeEventListener('message', currentMessageHandler);
          currentMessageHandler = null;
        }

        // 5. 在 iframe 中注入标识符，用于区分消息来源
        try {
          iframe.contentWindow.__iframeId = iframeId;
        } catch (e) {
          console.warn('Failed to set iframe id:', e);
        }

        // 6. 消息监听与行号修正
        const messageHandler = (event) => {
          // 只处理来自当前 iframe 的消息（通过检查 source）
          if (event.source !== iframe.contentWindow) {
            return; // 忽略其他 iframe 的消息
          }

          if (event.data && event.data.type === 'console') {
            let actualLineno = event.data.lineno;

            // [关键] 只有当报错行号大于偏移量时，才进行修正
            if (actualLineno && actualLineno > injectedLineOffset) {
              actualLineno = actualLineno - injectedLineOffset;
            }
            // 如果报错行号很小，说明是注入的脚本本身出错了
            
            console.log('Debug - line correction:', {
              originalLineno: event.data.lineno,
              injectedLineOffset,
              actualLineno
            });

            const logEntry = {
              type: event.data.logType,
              message: typeof event.data.message === 'string' ? event.data.message : String(event.data.message),
              timestamp: event.data.timestamp,
              lineno: actualLineno,  // 使用修正后的行号
              colno: event.data.colno
            };

            emit('console-output', [logEntry]);

            if (event.data.logType === 'error') {
              emit('error', logEntry);
            }
          }
        };

        // 保存引用以便后续清理
        currentMessageHandler = messageHandler;
        window.addEventListener('message', messageHandler);
        
        // 加载完成
        isLoadingIframe = false;
      } catch (error) {
        isLoadingIframe = false;
        console.error('Error in loadHtmlContentIntoIframe:', error);
        emit('error', { type: 'error', message: 'Failed to load iframe content: ' + error.message });
      }
    }

    watch(() => props.isShowVis, (newValue) => {
      nextTick(() => {
        if (newValue) {
          // 强制重新加载：切换到预览时重置防重复标记
          lastLoadedContent = null;
          destroyEditor();
          loadHtmlContentIntoIframe();
        } else {
          initEditor();
        }
      });
    });

    watch(() => props.htmlContent, (newValue) => {
      if (props.isShowVis) {
        // 防止与 isShowVis watch 重复触发
        // 只有内容真正变化时才重新加载
        const newContent = extractHtmlCode(newValue);
        if (newContent !== lastLoadedContent) {
          loadHtmlContentIntoIframe();
        }
        return;
      }

      const extractedValue = extractHtmlCode(newValue);
      if (!hasContent.value) {
        destroyEditor();
        return;
      }
      if (!editor) {
        nextTick(() => initEditor());
        return;
      }
      if (editor && editor.getValue() !== extractedValue) {
        const position = editor.getPosition(); // 保持光标位置
        editor.setValue(extractedValue);
        editor.setPosition(position);

        // 内容更新后，如果有报错，需要重新高亮，因为 setValue 会清除 decorations
        if (props.errorLine) {
          updateErrorHighlight(props.errorLine, props.errorMessage);
        }
      }
    });

    return {
      editorContainer,
      previewFrame,
      hasContent,
      isFullscreen
    };
  },
};
</script>

<style>
/* 这里放置全局或穿透样式，因为 Monaco 是动态挂载到 DOM 的 */

/* 强制覆盖 Monaco 内部的对齐方式 */
.monaco-editor .view-line {
  text-align: left !important;
}

/* 错误行背景高亮 */
.myErrorLineDecoration {
  background: rgba(255, 0, 0, 0.2);
  border-left: 2px solid #ff5252;
}
</style>

<style scoped>
/* 容器：简洁无圆角 */
.preview-container {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background-color: #ffffff;
  border: none;
  display: flex;
  flex-direction: column;
  transition: all 0.2s ease;
}

/* 头部：紧凑风格 */
.editor-title-bar {
  background-color: #f8fafc;
  padding: 6px 12px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 36px;
  flex-shrink: 0;
}

.title-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 模拟 Mac 窗口按钮 */
.mac-buttons {
  display: flex;
  gap: 5px;
}

.mac-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.mac-dot.red {
  background-color: #ff5f56;
}

.mac-dot.yellow {
  background-color: #ffbd2e;
}

.mac-dot.green {
  background-color: #27c93f;
}

.editor-title {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  font-family: system-ui, -apple-system, sans-serif;
  letter-spacing: 0.3px;
}

.title-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 内容区域 */
.content-wrapper {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: #fff;
}

.code-area,
.preview-area {
  width: 100%;
  height: 100%;
}

.monaco-wrapper {
  width: 100%;
  height: 100%;
  text-align: left;
}

.preview-iframe {
  width: 100%;
  height: 100%;
  display: block;
}

/* 空状态美化 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  background-color: #f8fafc;
  color: #94a3b8;
}

.empty-icon-bg {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background-color: #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.empty-icon-bg svg {
  width: 32px;
  height: 32px;
}

.empty-text {
  font-size: 13px;
  font-weight: 500;
  color: #94a3b8;
}

/* 全屏样式 */
.preview-container.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 9999;
  border-radius: 0;
}
</style>