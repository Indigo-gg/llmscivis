/**
 * 状态持久化工具
 * 用于保存和恢复应用状态（配置和生成结果）
 */

const STORAGE_KEYS = {
  CONFIG: 'sivpilot_config',
  CURRENT_CASE: 'sivpilot_current_case',
  LAST_SAVE_TIME: 'sivpilot_last_save'
};

/**
 * 保存配置数据（prompt、模型选择、workflow等）
 */
export function saveConfig(configData) {
  try {
    const dataToSave = {
      prompt: configData.prompt,
      groundTruth: configData.groundTruth,
      generator: configData.generator,
      evaluator: configData.evaluator,
      workflow: configData.workflow,
      name: configData.name,
      path: configData.path,
      timestamp: new Date().toISOString()
    };
    
    localStorage.setItem(STORAGE_KEYS.CONFIG, JSON.stringify(dataToSave));
    localStorage.setItem(STORAGE_KEYS.LAST_SAVE_TIME, Date.now().toString());
    return true;
  } catch (error) {
    console.error('Failed to save config:', error);
    return false;
  }
}

/**
 * 恢复配置数据
 */
export function loadConfig() {
  try {
    const savedConfig = localStorage.getItem(STORAGE_KEYS.CONFIG);
    if (!savedConfig) return null;
    
    const config = JSON.parse(savedConfig);
    return config;
  } catch (error) {
    console.error('Failed to load config:', error);
    return null;
  }
}

/**
 * 保存当前案例结果数据
 */
export function saveCurrentCase(caseData) {
  try {
    const dataToSave = {
      evalId: caseData.evalId,
      prompt: caseData.prompt,
      groundTruth: caseData.groundTruth,
      generatedCode: caseData.generatedCode,
      generator: caseData.generator,
      evaluator: caseData.evaluator,
      evaluatorEvaluation: caseData.evaluatorEvaluation,
      parsedEvaluation: caseData.parsedEvaluation,
      score: caseData.score,
      consoleOutput: caseData.consoleOutput || [],
      workflow: caseData.workflow,
      queryExpansion: caseData.queryExpansion,
      retrievalResults: caseData.retrievalResults || [],
      manualEvaluation: caseData.manualEvaluation,
      automatedExecutable: caseData.automatedExecutable,
      automatedValidOutput: caseData.automatedValidOutput,
      timestamp: new Date().toISOString()
    };
    
    localStorage.setItem(STORAGE_KEYS.CURRENT_CASE, JSON.stringify(dataToSave));
    localStorage.setItem(STORAGE_KEYS.LAST_SAVE_TIME, Date.now().toString());
    return true;
  } catch (error) {
    console.error('Failed to save current case:', error);
    return false;
  }
}

/**
 * 恢复当前案例数据
 */
export function loadCurrentCase() {
  try {
    const savedCase = localStorage.getItem(STORAGE_KEYS.CURRENT_CASE);
    if (!savedCase) return null;
    
    const caseData = JSON.parse(savedCase);
    return caseData;
  } catch (error) {
    console.error('Failed to load current case:', error);
    return null;
  }
}

/**
 * 清除所有保存的数据
 */
export function clearAllSavedData() {
  try {
    localStorage.removeItem(STORAGE_KEYS.CONFIG);
    localStorage.removeItem(STORAGE_KEYS.CURRENT_CASE);
    localStorage.removeItem(STORAGE_KEYS.LAST_SAVE_TIME);
    return true;
  } catch (error) {
    console.error('Failed to clear saved data:', error);
    return false;
  }
}

/**
 * 获取最后保存时间
 */
export function getLastSaveTime() {
  try {
    const timestamp = localStorage.getItem(STORAGE_KEYS.LAST_SAVE_TIME);
    if (!timestamp) return null;
    return new Date(parseInt(timestamp));
  } catch (error) {
    console.error('Failed to get last save time:', error);
    return null;
  }
}

/**
 * 检查是否有保存的数据
 */
export function hasSavedData() {
  return !!(localStorage.getItem(STORAGE_KEYS.CONFIG) || localStorage.getItem(STORAGE_KEYS.CURRENT_CASE));
}
