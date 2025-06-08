import html2canvas from 'html2canvas';
import { handleExport } from '../api/api';

export const ExportUtils = {
    // 等待元素渲染完成
    async waitForRender(ms = 1000) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },

    // 截图函数
    async captureElement(element, options = {}) {
        // 如果是 iframe 内容，需要特殊处理
        const targetElement = element.tagName === 'IFRAME'
            ? element.contentDocument.body
            : element;

        const canvas = await html2canvas(targetElement, {
            useCORS: true,
            allowTaint: true,
            foreignObjectRendering: true,
            width: targetElement.scrollWidth,
            height: targetElement.scrollHeight,
            scale: 2,
            logging: false,
            onclone: (clonedDoc) => {
                // 处理克隆的文档
                const clonedElement = clonedDoc.body;
                // 移除不需要的按钮等元素
                const buttonsToRemove = clonedElement.querySelectorAll('.fullscreen-btn, .export-btn');
                buttonsToRemove.forEach(btn => btn.remove());
            },
            ...options
        });

        return canvas.toDataURL('image/png');
    },

    // 设置全屏样式并返回原始样式
    setFullscreenStyle(element) {
        const originalStyles = {
            width: element.style.width,
            height: element.style.height,
            position: element.style.position,
            top: element.style.top,
            left: element.style.left,
            zIndex: element.style.zIndex,
            background: element.style.background,
            overflow: element.style.overflow
        };

        Object.assign(element.style, {
            width: '100vw',
            height: '100vh',
            position: 'fixed',
            top: '0',
            left: '0',
            zIndex: '9999',
            background: 'white',
            overflow: 'hidden'
        });

        return originalStyles;
    },

    // 恢复原始样式
    resetStyle(element, originalStyles) {
        Object.assign(element.style, originalStyles);
    },

    // 等待 VTK 渲染完成
    async waitForVTKRender(element) {
        return new Promise(resolve => {
            // 检查是否存在 iframe
            const iframe = element.querySelector('iframe');
            if (!iframe) {
                resolve();
                return;
            }

            // 等待 iframe 加载完成
            const checkRender = () => {
                try {
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    const vtkContainer = iframeDoc.querySelector('#vtkContainer');
                    if (vtkContainer && vtkContainer.children.length > 0) {
                        // 额外等待一段时间确保 VTK 渲染完成
                        setTimeout(resolve, 2000);
                    } else {
                        setTimeout(checkRender, 100);
                    }
                } catch (e) {
                    setTimeout(checkRender, 100);
                }
            };
            checkRender();
        });
    },

    // 导出结果
    async exportResults(data, elements) {
        try {
            const { generatedPreviewEl, truthPreviewEl } = elements;

            // 确保元素存在
            if (!generatedPreviewEl || !truthPreviewEl) {
                throw new Error('预览元素不存在');
            }

            // 等待一段时间确保渲染完成
            await this.waitForRender(1000);

            let generatedImage = null;
            try {
                // 获取生成代码的截图
                generatedImage = await this.captureElement(generatedPreviewEl);
            } catch (captureError) {
                console.error('生成预览截图失败:', captureError);
                // 将截图字段置空
                generatedImage = null;
            }

            let truthImage = null;
            try {
                // 获取 ground truth 的截图
                truthImage = await this.captureElement(truthPreviewEl);
            } catch (captureError) {
                console.error('Ground truth 截图失败:', captureError);
                // 将截图字段置空
                truthImage = null;
            }

            // 准备导出数据
            const exportData = {
                ...data,
                generatedImage,
                truthImage,
                exportTime: new Date().toISOString()
            };

            // 调用后端API
            const response = await handleExport(exportData);

            if (!response.data.success) {
                throw new Error('导出失败');
            }

            return response.data;

        } catch (error) {
            console.error('导出错误:', error);
            throw error;
        }
    }
};