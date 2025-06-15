<template>
  <div class="preview-container">
    <div class="preview-header">
      <slot name="actions"></slot>
    </div>
    <div v-if="!isShowVis" class="code-container">
      <div class="monaco-editor-container" ref="editorContainer"></div>
    </div>
    <div class="preview-frame" v-else>
      <iframe ref="previewFrame" sandbox="allow-scripts allow-same-origin allow-top-navigation"
        style="width: 100%;height:100%" src="about:blank" frameBorder="0"></iframe>
    </div>
  </div>
</template>

<script>
import { onMounted, nextTick, ref, watch } from 'vue';
import * as monaco from 'monaco-editor';

export default {
  name: 'index',
  emits: ['error', 'console-output', 'update:htmlContent'],
  props: {
    htmlContent: {
      type: String,
      required: true,
    },
    isShowVis: {
      type: Boolean,
      required: false,
      default: false
    }
  },
  setup(props, { emit }) {
    const editorContainer = ref(null);
    const previewFrame = ref(null);
    let editor = null;

    function initEditor() {
      // Ensure we destroy any existing editor first
      destroyEditor();
      if (editorContainer.value) { // Check if container exists
        // 初始化Monaco编辑器
        editor = monaco.editor.create(editorContainer.value, {
          value: extractHtmlCode(props.htmlContent), // Use current prop value
          language: 'html',
          theme: 'vs-light',
          automaticLayout: true,
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          roundedSelection: false,
          readOnly: false,
          cursorStyle: 'line',
          wordWrap: 'off',
          lineDecorationsWidth: 0,
          folding: false,
          fixedOverflowWidgets: true,
          renderWhitespace: 'all',
          autoIndent: 'advanced',
          scrollbar: {
            vertical: 'visible',
            horizontal: 'visible',
            useShadows: false,
            verticalHasArrows: false,
            horizontalHasArrows: false,
            verticalScrollbarSize: 10,
            horizontalScrollbarSize: 10
          }
        });

        // 监听编辑器内容变化
        editor.onDidChangeModelContent(() => {
          const newValue = editor.getValue();
          // Check if the new value is different from the prop to avoid potential issues
          // Although the parent should handle the update, this adds robustness
          if (newValue !== props.htmlContent) { 
             emit('update:htmlContent', newValue);
          }
        });
      }
    }

    function destroyEditor() {
      if (editor) {
        editor.dispose();
        editor = null;
      }
    }

    onMounted(() => {
      initEditor();
    });

    function extractHtmlCode(input) {
      const regex = /```html([\s\S]*?)```/;
      const match = input.match(regex);
      return match ? match[1].trim() : input;
    }

    function loadHtmlContentIntoIframe() {
      const iframe = previewFrame.value;
      if (iframe) {
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        // 提取内容
        const content = extractHtmlCode(props.htmlContent);
        // 构建完整的 HTML 文档
        const consoleScript = `
          <script>
            window.onerror = function(message, source, lineno, colno, error) {
              window.parent.postMessage({
                type: 'console',
                logType: 'error',
                message: 'Error: ' + message + ' (at ' + source + ':' + lineno + ':' + colno + ')',
                timestamp: new Date().toISOString()
              }, '*');
              return false;
            };
            window.addEventListener('unhandledrejection', function(event) {
              window.parent.postMessage({
                type: 'console',
                logType: 'error',
                message: 'Unhandled Promise Rejection: ' + event.reason,
                timestamp: new Date().toISOString()
              }, '*');
            });
            ['log', 'info', 'warn', 'error'].forEach(type => {
              const originalConsole = console[type];
              console[type] = function(...args) {
                const processedArgs = args.map(arg => {
                  if (typeof arg === 'object') {
                    try {
                      return JSON.stringify(arg);
                    } catch (e) {
                      return String(arg);
                    }
                  }
                  return String(arg);
                });
                originalConsole.apply(this, args);
                window.parent.postMessage({
                  type: 'console',
                  logType: type,
                  message: processedArgs,
                  timestamp: new Date().toISOString()
                }, '*');
              };
            });
          <\/script>
        `;
        // 拼接完整 HTML
        const fullHtml = `<!DOCTYPE html><html><head>${consoleScript}</head><body>${content}</body></html>`;
        doc.open();
        doc.write(fullHtml);
        doc.close();
        // 监听消息
        const messageHandler = (event) => {
          if (event.data && event.data.type === 'console') {
            const logEntry = {
              type: event.data.logType,
              message: Array.isArray(event.data.message) ? event.data.message.join(' ') : event.data.message,
              timestamp: event.data.timestamp
            };
            emit('console-output', [logEntry]);
            if (event.data.logType === 'error') {
              emit('error', logEntry);
            }
          }
        };
        window.removeEventListener('message', messageHandler);
        window.addEventListener('message', messageHandler);
      }
    }

    watch(() => props.isShowVis, (newValue) => {
      nextTick(() => {
        if (newValue) {
          // Switching to preview
          destroyEditor();
          loadHtmlContentIntoIframe();
        } else {
          // Switching back to editor
          // Ensure editor is initialized *after* the container is visible
          // and potentially after parent updates have settled in nextTick
          nextTick(() => {
              initEditor();
          });
        }
      });
    });

    watch(() => props.htmlContent, (newValue) => {
      const extractedValue = extractHtmlCode(newValue);
      // Only update if the editor exists and its value differs from the extracted prop value
      if (editor && editor.getValue() !== extractedValue) {
        // Use a try-catch block in case the editor is disposed unexpectedly
        try {
            editor.setValue(extractedValue);
        } catch (error) {
            console.error("Error setting editor value:", error);
            // Optionally re-initialize the editor if setting value fails
            // initEditor(); 
        }
      }
    });

    return {
      editorContainer,
      previewFrame
    };
  },
};
</script>

<style scoped>
.preview-container {
  position: relative;
  width: 100%;
  height: 70vh;
  margin: 5px;
}

.preview-frame {
  width: 100%;
  height: 100%;
  border: none;
}

.code-container {
  height: 100%;
}

.monaco-editor-container {
  height: 100%;
  width: 100%;
  overflow: auto;
  text-align: left; /* 确保文本左对齐 */
}

.monaco-editor-container .monaco-editor {
  text-align: left;
  padding-left: 0;
  width: 100%; /* 确保编辑器宽度匹配容器 */
}

.monaco-editor .monaco-editor-background {
  left: 0;
  width: 100%; /* 确保编辑器宽度匹配容器 */
  overflow: scroll;
}

.monaco-editor .margin {
  margin-left: 0;
}

.preview-container:fullscreen {
  padding: 0;
  width: 100vw;
  height: 100vh;
  background: white;
}
</style>