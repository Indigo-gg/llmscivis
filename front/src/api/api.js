import { post, get, postStream } from "@/api/request.js";



function getCode(data) {
    return post('/get_code', data)
}

function getCodeStream(data, load) {
    return postStream('/get_code', data, load)
}
function getEvalResultStream(data, callback) {
    return postStream('/evaluate', data, callback)
}
function generateCodeStream(data, callback) {
    return postStream('/generateStream', data, callback)
}

/**
 *
 * @param data
 * @returns {options}
 */
function generateCode(data) {
    return post('/generate', data)
}

/**
 *
 * @param data
 * @returns {options}
 */
function getEvalResult(data) {
    return post('/evaluate', data)
}
function getAllCase() {
    return get('/get_all_data', {})
}
function handleCodeError(data) {
    return post('/code_error', data)
}
function handleErrorAnalysis(data) {
    return post('/error_analysis', data)
}
function handleExport(data) {
    return post('/export', data)
}
function getCaseList() {
    return get('/get_case_list', {})

}
function getExportedCases() {
    return get('/get_exported_cases', {})
}
export {
    getCode,
    getCodeStream,
    getEvalResult,
    getCaseList,
    getEvalResultStream,
    generateCodeStream,
    getAllCase,
    generateCode,
    handleCodeError,
    handleExport,
    handleErrorAnalysis,
    getExportedCases
}
