<template>
  <div class="preview-container">
    <!-- Editor title bar - Theme color can be modified in editor-title-bar class -->
    <div class="editor-title-bar">
      <h3 class="editor-title">{{ title }}</h3>
      <div class="title-actions">
        <slot name="actions"></slot>
      </div>
    </div>
    <div v-if="!isShowVis" class="code-container">
      <div v-if="hasContent">
        <pre><code class="hljs" v-html="highlightedCode"></code></pre>
      </div>
      <div v-else class="empty-state">
        <v-icon size="64" color="grey-lighten-1">mdi-file-code</v-icon>
        <p class="empty-text">No {{ title }}</p>
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
import hljs from 'highlight.js';
import 'highlight.js/styles/github.css'; // Select a highlight theme

export default {
  name: 'index',
  emits: ['error', 'console-output'],
  props: {
    htmlContent: {
      type: String,
      required: true,
    },
    isShowVis: {
      type: Boolean,
      required: false,
      default: false
    },
    title: {
      type: String,
      required: false,
      default: 'Ground Truth'
    }
  },
  setup(props, { emit }) {
    const previewFrame = ref(null);

    function extractHtmlCode(input) {
      // Extract HTML code from markdown code block
      const htmlBlockRegex = /```html([\s\S]*?)```/;
      const match = input.match(htmlBlockRegex);
      return match ? match[1].trim() : input;
    }

    const highlightedCode = computed(() => {
      return hljs.highlightAuto(extractHtmlCode(props.htmlContent)).value;
    });

    const hasContent = computed(() => {
      return props.htmlContent && 
             props.htmlContent.trim() !== '' && 
             props.htmlContent !== 'Ground Truth:' &&
             props.htmlContent !== 'Generated Code:';
    });

    function loadHtmlContentIntoIframe() {
      const iframe = previewFrame.value;
      if (!iframe) {
        console.error('iframe ref not found');
        return;
      }

      try {
        const content = extractHtmlCode(props.htmlContent);
        
        // 构建完整的 HTML（不注入任何监听脚本）
        let finalHtml = '';
        
        if (!content.includes('<!DOCTYPE') && !content.includes('<html')) {
          // 片段代码，添加完整的 HTML 结构
          finalHtml = `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
${content}
</body>
</html>`;
        } else {
          // 完整的 HTML 代码
          finalHtml = content;
        }

        // 使用 Blob URL 加载（不注入脚本，保证行号准确）
        const blob = new Blob([finalHtml], { type: 'text/html;charset=utf-8' });
        const blobUrl = URL.createObjectURL(blob);
        
        // 清理旧的事件监听
        if (previewFrame.value && previewFrame.value._messageHandler) {
          window.removeEventListener('message', previewFrame.value._messageHandler);
        }
        
        // 在 iframe 加载完成后，从 iframe 内部获取 window.onerror
        iframe.onload = () => {
          try {
            // 注入一个最小的脚本来捕获 iframe 内的错误
            const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
            if (iframeDoc && !iframeDoc.querySelector('script[data-error-handler]')) {
              const script = iframeDoc.createElement('script');
              script.setAttribute('data-error-handler', 'true');
              script.textContent = `
window.onerror = function(message, source, lineno, colno, error) {
  window.parent.postMessage({
    type: "console",
    logType: "error",
    message: "Error: " + message + " (at " + source + ":" + lineno + ":" + colno + ")",
    lineno: lineno,
    colno: colno,
    timestamp: new Date().toISOString()
  }, "*");
  return false;
};
window.addEventListener("unhandledrejection", function(event) {
  let message = "Unhandled Promise Rejection: ";
  if (event.reason) message += String(event.reason.message || event.reason);
  window.parent.postMessage({
    type: "console",
    logType: "error",
    message: message,
    lineno: null,
    timestamp: new Date().toISOString()
  }, "*");
});
["log", "info", "warn", "error", "debug", "trace"].forEach(type => {
  const originalConsole = console[type];
  console[type] = function(...args) {
    const processedArgs = args.map(arg => String(arg));
    originalConsole.apply(this, args);
    window.parent.postMessage({
      type: "console",
      logType: type,
      message: processedArgs.join(" "),
      timestamp: new Date().toISOString()
    }, "*");
  };
});
`;
              iframeDoc.head.appendChild(script);
            }
          } catch (e) {
            console.warn('Failed to inject error handler into iframe:', e);
          }
        };
        
        // 设置 iframe src
        iframe.src = blobUrl;

        // 清理 Blob URL
        setTimeout(() => {
          URL.revokeObjectURL(blobUrl);
        }, 1000);

        // 消息监听（直接使用浏览器报告的行号）
        const messageHandler = (event) => {
          if (event.data && event.data.type === 'console') {
            const logEntry = {
              type: event.data.logType,
              message: typeof event.data.message === 'string' ? event.data.message : String(event.data.message),
              timestamp: event.data.timestamp,
              lineno: event.data.lineno,  // 直接使用浏览器报告的行号
              colno: event.data.colno
            };

            emit('console-output', [logEntry]);

            if (event.data.logType === 'error') {
              emit('error', logEntry);
            }
          }
        };

        // 保存事件监听器供后续清理
        previewFrame.value._messageHandler = messageHandler;
        window.removeEventListener('message', messageHandler);
        window.addEventListener('message', messageHandler);
      } catch (error) {
        console.error('Error in loadHtmlContentIntoIframe:', error);
        emit('error', { type: 'error', message: 'Failed to load iframe content: ' + error.message });
      }
    }

    watch(() => props.isShowVis, (newValue) => {
      console.log('isShowVis changed to ' + newValue);
      if (newValue) {
        nextTick(() => {
          if (previewFrame.value) {
            try {
              loadHtmlContentIntoIframe();
            } catch (error) {
              console.error('Error loading iframe content:', error);
              emit('error', { type: 'error', message: 'Failed to load preview: ' + error.message });
            }
          } else {
            console.error('Preview iframe element not found');
            emit('error', { type: 'error', message: 'Preview iframe element not found' });
          }
        });
      }
    });

    // Watch for htmlContent changes to reload when content updates
    watch(() => props.htmlContent, (newValue) => {
      if (newValue && hasContent.value && props.isShowVis) {
        nextTick(() => {
          loadHtmlContentIntoIframe();
        });
      }
    });

    return {
      previewFrame,
      highlightedCode,
      hasContent
    };
  },
};

</script>

<style scoped>
/* Theme color definition - Modify here to change editor title appearance */
.editor-title-bar {
  background-color: #4a5258;
  color: #ffffff;
  padding: 12px 16px;
  border-bottom: 2px solid #3a4248;
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
  border: 1px solid #3a4248;
  border-radius: 4px;
  overflow: hidden;
  background-color: #f5f5f5;
}

.preview-frame {
  width: 100%;
  height: calc(100% - 50px);
  border: none;
}

.code-container {
  height: calc(100% - 50px);
  background-color: #f5f5f5;
}

.code-container pre {
  margin: 0;
  padding: 12px;
  height: 100%;
  text-align: left;
  border-radius: 0;
  overflow-x: auto;
  background-color: #f5f5f5;
}

.hljs {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.5;
  background-color: #f5f5f5 !important;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  min-height: 300px;
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
