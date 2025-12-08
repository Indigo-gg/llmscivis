<template>
  <div class="preview-container">
    <!-- Editor title bar - Theme color can be modified in editor-title-bar class -->
    <div class="editor-title-bar">
      <h3 class="editor-title">Generated Code</h3>
      <div class="title-actions">
        <slot name="actions"></slot>
      </div>
    </div>
    <div v-if="!isShowVis" class="code-container">
      <div v-if="hasContent" class="monaco-editor-container" ref="editorContainer"></div>
      <div v-else class="empty-state">
        <v-icon size="64" color="grey-lighten-1">mdi-code-tags</v-icon>
        <p class="empty-text">No generated code</p>
      </div>
    </div>
    <div class="preview-frame" v-else>
      <iframe ref="previewFrame" sandbox="allow-scripts allow-same-origin allow-top-navigation"
        style="width: 100%;height:100%" src="about:blank" frameBorder="0"></iframe>
    </div>
  </div>
</template>

<script>
import { onMounted, nextTick, ref, watch, computed } from 'vue';
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

    const hasContent = computed(() => {
      return props.htmlContent && 
             props.htmlContent.trim() !== '' && 
             props.htmlContent !== 'Ground Truth:' &&
             props.htmlContent !== 'Generated Code:';
    });

    function initEditor() {
      // Ensure we destroy any existing editor first
      destroyEditor();
      if (editorContainer.value && hasContent.value) { // Check if container exists and has content
        // Initialize Monaco Editor
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

        // Listen for editor content changes
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
        // Extract content
        const content = extractHtmlCode(props.htmlContent);
        // Build complete HTML document
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
        // Concatenate complete HTML
        const fullHtml = `<!DOCTYPE html><html><head>${consoleScript}</head><body>${content}</body></html>`;
        doc.open();
        doc.write(fullHtml);
        doc.close();
        // Listen for messages
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
      
      // Check if there is content
      if (!hasContent.value) {
        destroyEditor();
        return;
      }
      
      // If there is no editor but there is content, initialize the editor
      if (!editor && !props.isShowVis) {
        nextTick(() => {
          initEditor();
        });
        return;
      }
      
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
      previewFrame,
      hasContent
    };
  },
};
</script>

<style scoped>
/* Theme color definition - Modify here to change editor title appearance */
.editor-title-bar {
  background-color: #4a5258;  /* Military Gray - Change this to modify theme */
  color: #ffffff;
  padding: 12px 16px;
  border-bottom: 2px solid #3a4248;  /* Darker Military Gray for border */
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
}

.editor-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.title-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.preview-container {
  position: relative;
  width: 100%;
  height: 70vh;
  margin: 5px;
  border: 1px solid #3a4248;  /* Military Gray border */
  border-radius: 4px;
  overflow: hidden;
  background-color: #f5f5f5;
}

.preview-frame {
  width: 100%;
  height: calc(100% - 50px);  /* Account for title bar */
  border: none;
}

.code-container {
  height: calc(100% - 50px);  /* Account for title bar */
  background-color: #f5f5f5;
}

.monaco-editor-container {
  height: 100%;
  width: 100%;
  overflow: auto;
  text-align: left;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}

.monaco-editor-container .monaco-editor {
  text-align: left;
  padding-left: 0;
  width: 100%;
}

.monaco-editor .monaco-editor-background {
  left: 0;
  width: 100%;
  overflow: scroll;
}

.monaco-editor .margin {
  margin-left: 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  min-height: 300px;
  height: 100%;
}

.empty-text {
  margin-top: 12px;
  font-size: 16px;
  color: #9e9e9e;
}

.preview-container:fullscreen {
  padding: 0;
  width: 100vw;
  height: 100vh;
  background: white;
}
</style>