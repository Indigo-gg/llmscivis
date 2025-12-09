import html2canvas from 'html2canvas';
import { handleExport } from '../api/api';
import { convertToHundredScale } from './scoreUtils.js';

export const ExportUtils = {
    // 等待元素渲染完成
    async waitForRender(ms = 1000) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },

    // 截图函数 - 改进版本，特别处理iframe和VTK内容
    async captureElement(element, options = {}) {
        try {
            // 检查是否是iframe
            if (element.tagName === 'IFRAME') {
                try {
                    const iframeDoc = element.contentDocument || element.contentWindow.document;
                    if (!iframeDoc) {
                        console.warn('无法访问iframe内容，使用备选方案');
                        return await this.captureIframeAsImage(element);
                    }
                    
                    // 尝试直接截图iframe内容
                    const canvas = await html2canvas(iframeDoc.body, {
                        useCORS: true,
                        allowTaint: true,
                        foreignObjectRendering: false, // 禁用SVG渲染以更好地处理canvas内容
                        backgroundColor: '#ffffff',
                        scale: 1,
                        logging: false,
                        width: element.clientWidth,
                        height: element.clientHeight,
                        ...options
                    });
                    return canvas.toDataURL('image/png');
                } catch (iframeError) {
                    console.error('直接截图iframe失败:', iframeError);
                    // 如果直接方法失败，尝试备选方案
                    return await this.captureIframeAsImage(element);
                }
            } else {
                // 非iframe元素的处理
                const canvas = await html2canvas(element, {
                    useCORS: true,
                    allowTaint: true,
                    foreignObjectRendering: true,
                    backgroundColor: '#ffffff',
                    width: element.scrollWidth,
                    height: element.scrollHeight,
                    scale: 2,
                    logging: false,
                    ...options
                });
                return canvas.toDataURL('image/png');
            }
        } catch (error) {
            console.error('截图失败:', error);
            // 返回一个占位符图像而不是抛出错误
            return this.createPlaceholderImage('Screenshot Failed');
        }
    },

    // 备选截图方法 - 用于iframe内容
    async captureIframeAsImage(iframe) {
        return new Promise((resolve) => {
            try {
                const canvas = iframe.contentWindow.document.createElement('canvas');
                const rect = iframe.getBoundingClientRect();
                canvas.width = rect.width;
                canvas.height = rect.height;
                
                const ctx = canvas.getContext('2d');
                if (ctx) {
                    // 填充白色背景
                    ctx.fillStyle = '#ffffff';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);
                    
                    // 尝试绘制iframe内容
                    try {
                        const iframeCanvas = iframe.contentWindow.document.querySelector('canvas');
                        if (iframeCanvas) {
                            ctx.drawImage(iframeCanvas, 0, 0);
                        }
                    } catch (e) {
                        console.warn('无法从iframe提取canvas');
                    }
                }
                resolve(canvas.toDataURL('image/png'));
            } catch (error) {
                console.error('备选截图方法失败:', error);
                resolve(this.createPlaceholderImage('Preview Not Available'));
            }
        });
    },

    // 创建占位符图像
    createPlaceholderImage(text) {
        const canvas = document.createElement('canvas');
        canvas.width = 400;
        canvas.height = 300;
        const ctx = canvas.getContext('2d');
        
        // 填充背景
        ctx.fillStyle = '#f5f5f5';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // 绘制边框
        ctx.strokeStyle = '#ddd';
        ctx.lineWidth = 2;
        ctx.strokeRect(0, 0, canvas.width, canvas.height);
        
        // 绘制文本
        ctx.fillStyle = '#999';
        ctx.font = 'bold 16px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, canvas.width / 2, canvas.height / 2);
        
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
                // 如果没有iframe，直接解决
                setTimeout(resolve, 1000);
                return;
            }

            // 等待 iframe 加载完成
            let attempts = 0;
            const maxAttempts = 30; // 最多等待3秒
            const checkRender = () => {
                try {
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    if (!iframeDoc) {
                        attempts++;
                        if (attempts < maxAttempts) {
                            setTimeout(checkRender, 100);
                        } else {
                            resolve();
                        }
                        return;
                    }
                    
                    // 检查iframe中是否有canvas元素
                    const vtkContainer = iframeDoc.querySelector('canvas');
                    if (vtkContainer && vtkContainer.offsetHeight > 0) {
                        // 额外等待一段时间确保 VTK 渲染完成
                        setTimeout(resolve, 1500);
                    } else {
                        attempts++;
                        if (attempts < maxAttempts) {
                            setTimeout(checkRender, 100);
                        } else {
                            resolve();
                        }
                    }
                } catch (e) {
                    console.warn('检查iframe渲染失败:', e);
                    attempts++;
                    if (attempts < maxAttempts) {
                        setTimeout(checkRender, 100);
                    } else {
                        resolve();
                    }
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
        let totalManualScore = 0;
        if (currentCase.manualEvaluation && typeof currentCase.manualEvaluation === 'object') {
            if (Array.isArray(currentCase.manualEvaluation) && currentCase.manualEvaluation.length > 0) {
                const latest = currentCase.manualEvaluation[currentCase.manualEvaluation.length - 1];
                const functionality = convertToHundredScale(latest.functionality, 1) || 0;
                const visualQuality = convertToHundredScale(latest.visualQuality, 1) || 0;
                const codeQuality = convertToHundredScale(latest.codeQuality, 1) || 0;
                // 计算总分（平均分）
                totalManualScore = Math.round((functionality + visualQuality + codeQuality) / 3);
                manualEvaluation = {
                    correction_cost: latest.correctionCost || 0,
                    functionality: functionality,
                    visual_quality: visualQuality,
                    code_quality: codeQuality,
                    total_score: totalManualScore,
                    timestamp: latest.timestamp || null
                };
            } else {
                const functionality = convertToHundredScale(currentCase.manualEvaluation.functionality, 1) || 0;
                const visualQuality = convertToHundredScale(currentCase.manualEvaluation.visualQuality, 1) || 0;
                const codeQuality = convertToHundredScale(currentCase.manualEvaluation.codeQuality, 1) || 0;
                // 计算总分（平均分）
                totalManualScore = Math.round((functionality + visualQuality + codeQuality) / 3);
                manualEvaluation = {
                    correction_cost: currentCase.manualEvaluation.correctionCost || 0,
                    functionality: functionality,
                    visual_quality: visualQuality,
                    code_quality: codeQuality,
                    total_score: totalManualScore,
                    timestamp: currentCase.manualEvaluation.timestamp || null
                };
            }
        }

        // Calculate overall score (combination of LLM and manual evaluation)
        let overallScore = 0;
        if (llmEvaluation && manualEvaluation) {
            // 如果有人工评估，取人工评估分数，否则取LLM分数
            overallScore = manualEvaluation.total_score || llmEvaluation.overall_score;
        } else if (llmEvaluation) {
            overallScore = llmEvaluation.overall_score;
        } else if (manualEvaluation) {
            overallScore = manualEvaluation.total_score;
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
            overall_score: overallScore,
            retrieval_results: currentCase.retrievalResults || [],
            query_expansion: currentCase.queryExpansion || '',
            console_output: currentCase.consoleOutput || [],
            generated_code: currentCase.generatedCode || '',
            ground_truth: currentCase.groundTruth || '',
            final_prompt: currentCase.final_prompt || '',
            workflow: currentCase.workflow || {}
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