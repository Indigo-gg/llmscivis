import html2canvas from 'html2canvas';
import { handleExport } from '../api/api';
import { convertToHundredScale } from './scoreUtils.js';

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

    // Transform evaluation data to new format with English field names
    transformEvaluationData(currentCase) {
        // Extract automated checks
        const automatedChecks = {
            executable: currentCase.automatedExecutable ?? null,
            has_output: currentCase.automatedValidOutput ?? null,
            error_count: currentCase.consoleOutput ? 
                currentCase.consoleOutput.filter(log => log.type === 'error').length : 0
        };

        // Extract LLM evaluation with score conversion
        let llmEvaluation = null;
        if (currentCase.parsedEvaluation) {
            const dimensions = {};
            if (currentCase.parsedEvaluation.dimensions) {
                Object.keys(currentCase.parsedEvaluation.dimensions).forEach(key => {
                    const dim = currentCase.parsedEvaluation.dimensions[key];
                    const snakeKey = key.replace(/([A-Z])/g, '_$1').toLowerCase().replace(/^_/, '');
                    dimensions[snakeKey] = {
                        score: convertToHundredScale(dim.score, 1) || 0,
                        reason: dim.reason || ''
                    };
                });
            }

            llmEvaluation = {
                overall_score: convertToHundredScale(currentCase.parsedEvaluation.overall, 1) || 0,
                dimensions: dimensions,
                critique: currentCase.parsedEvaluation.critique || '',
                raw_output: currentCase.evaluatorEvaluation || ''
            };
        } else if (currentCase.score) {
            // Fallback to old format
            llmEvaluation = {
                overall_score: convertToHundredScale(currentCase.score, 1) || 0,
                dimensions: {},
                critique: '',
                raw_output: currentCase.evaluatorEvaluation || ''
            };
        }

        // Extract manual evaluation with score conversion
        let manualEvaluation = null;
        if (currentCase.manualEvaluation && typeof currentCase.manualEvaluation === 'object') {
            if (Array.isArray(currentCase.manualEvaluation) && currentCase.manualEvaluation.length > 0) {
                const latest = currentCase.manualEvaluation[currentCase.manualEvaluation.length - 1];
                manualEvaluation = {
                    correction_cost: latest.correctionCost || 0,
                    functionality: convertToHundredScale(latest.functionality, 1) || 0,
                    visual_quality: convertToHundredScale(latest.visualQuality, 1) || 0,
                    code_quality: convertToHundredScale(latest.codeQuality, 1) || 0,
                    timestamp: latest.timestamp || null
                };
            } else {
                manualEvaluation = {
                    correction_cost: currentCase.manualEvaluation.correctionCost || 0,
                    functionality: convertToHundredScale(currentCase.manualEvaluation.functionality, 1) || 0,
                    visual_quality: convertToHundredScale(currentCase.manualEvaluation.visualQuality, 1) || 0,
                    code_quality: convertToHundredScale(currentCase.manualEvaluation.codeQuality, 1) || 0,
                    timestamp: currentCase.manualEvaluation.timestamp || null
                };
            }
        }

        // Build transformed data object
        return {
            evalId: currentCase.evalId?.toString() || '0',  // Backend expects evalId
            evaluation_id: currentCase.evalId?.toString() || '0',
            timestamp: new Date().toISOString(),
            prompt: currentCase.prompt || '',
            generator_model: currentCase.generator || '',
            evaluator_model: currentCase.evaluator || '',
            automated_checks: automatedChecks,
            llm_evaluation: llmEvaluation,
            manual_evaluation: manualEvaluation,
            retrieval_results: currentCase.retrievalResults || [],
            query_expansion: currentCase.queryExpansion || '',
            console_output: currentCase.consoleOutput || [],
            generated_code: currentCase.generatedCode || '',
            ground_truth: currentCase.groundTruth || ''
        };
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

            // Transform data to new format with English field names
            const transformedData = this.transformEvaluationData(data);

            // 准备导出数据
            const exportData = {
                ...transformedData,
                generatedImage,
                truthImage,
                export_time: new Date().toISOString()
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