/**
 * 看板 API 封装模块
 * @module dashboard-api
 */

// ========== 缓存管理 ==========

/** @type {Map<string, {data: any, timestamp: number}>} API 响应缓存 */
const apiCache = new Map();

/** @type {number} 缓存有效期 (5分钟) */
const CACHE_TTL = 5 * 60 * 1000;

/**
 * 获取缓存数据
 * @param {string} key - 缓存键
 * @returns {any|null}
 */
function getCache(key) {
    const cached = apiCache.get(key);
    if (!cached) return null;
    
    if (Date.now() - cached.timestamp > CACHE_TTL) {
        apiCache.delete(key);
        return null;
    }
    
    return cached.data;
}

/**
 * 设置缓存数据
 * @param {string} key - 缓存键
 * @param {any} data - 数据
 */
function setCache(key, data) {
    apiCache.set(key, {
        data,
        timestamp: Date.now()
    });
}

/**
 * 清除所有缓存
 */
export function clearCache() {
    apiCache.clear();
}

// ========== 基础请求函数 ==========

/**
 * 发送 GET 请求
 * @param {string} url - 请求URL
 * @param {boolean} useCache - 是否使用缓存
 * @returns {Promise<Object>}
 */
async function get(url, useCache = true) {
    if (useCache) {
        const cached = getCache(url);
        if (cached) return cached;
    }
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        if (useCache && data.success) {
            setCache(url, data);
        }
        
        return data;
    } catch (error) {
        console.error(`[API] GET ${url} 失败:`, error);
        return { success: false, error: error.message };
    }
}

/**
 * 发送 POST 请求
 * @param {string} url - 请求URL
 * @param {Object} body - 请求体
 * @returns {Promise<Object>}
 */
async function post(url, body = {}) {
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        return await response.json();
    } catch (error) {
        console.error(`[API] POST ${url} 失败:`, error);
        return { success: false, error: error.message };
    }
}

/**
 * 发送 PUT 请求
 * @param {string} url - 请求URL
 * @param {Object} body - 请求体
 * @returns {Promise<Object>}
 */
async function put(url, body = {}) {
    try {
        const response = await fetch(url, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        return await response.json();
    } catch (error) {
        console.error(`[API] PUT ${url} 失败:`, error);
        return { success: false, error: error.message };
    }
}

/**
 * 发送 DELETE 请求
 * @param {string} url - 请求URL
 * @returns {Promise<Object>}
 */
async function del(url) {
    try {
        const response = await fetch(url, { method: 'DELETE' });
        return await response.json();
    } catch (error) {
        console.error(`[API] DELETE ${url} 失败:`, error);
        return { success: false, error: error.message };
    }
}

// ========== Dashboard API ==========

export const DashboardAPI = {
    // ========== 概览统计 ==========
    
    /**
     * 获取概览统计数据
     * @param {string} range - 时间范围: today|week|month
     * @returns {Promise<Object>}
     */
    getOverview: (range = 'today') => 
        get(`/api/dashboard/overview?range=${range}`),
    
    /**
     * 同步刷新数据
     * @returns {Promise<Object>}
     */
    sync: () => post('/api/dashboard/sync'),
    
    // ========== 任务相关 ==========
    
    /**
     * 获取批量任务列表
     * @param {number} page - 页码
     * @param {number} pageSize - 每页数量
     * @param {string} status - 状态筛选
     * @returns {Promise<Object>}
     */
    getTasks: (page = 1, pageSize = 20, status = 'all') => 
        get(`/api/dashboard/tasks?page=${page}&page_size=${pageSize}&status=${status}`),
    
    // ========== 数据集相关 ==========
    
    /**
     * 获取数据集概览
     * @param {string} subjectId - 学科ID筛选
     * @param {string} sortBy - 排序字段
     * @param {string} order - 排序方向
     * @returns {Promise<Object>}
     */
    getDatasets: (subjectId = '', sortBy = 'created_at', order = 'desc') => 
        get(`/api/dashboard/datasets?subject_id=${subjectId}&sort_by=${sortBy}&order=${order}`),
    
    /**
     * 获取数据集统计摘要
     * @returns {Promise<Object>}
     */
    getDatasetStats: () => get('/api/dashboard/dataset-stats'),
    
    // ========== 学科相关 ==========
    
    /**
     * 获取学科评估概览
     * @returns {Promise<Object>}
     */
    getSubjects: () => get('/api/dashboard/subjects'),
    
    /**
     * 获取学科详细分析
     * @param {number} subjectId - 学科ID
     * @param {number} days - 天数
     * @returns {Promise<Object>}
     */
    getSubjectDetail: (subjectId, days = 7) => 
        get(`/api/dashboard/subjects/${subjectId}?days=${days}`, false),
    
    // ========== 测试计划相关 ==========
    
    /**
     * 获取测试计划列表
     * @param {string} status - 状态筛选
     * @returns {Promise<Object>}
     */
    getPlans: (status = 'all') => 
        get(`/api/test-plans?status=${status}`, false),
    
    /**
     * 获取测试计划详情
     * @param {string} planId - 计划ID
     * @returns {Promise<Object>}
     */
    getPlan: (planId) => get(`/api/test-plans/${planId}`, false),
    
    /**
     * 创建测试计划
     * @param {Object} planData - 计划数据
     * @returns {Promise<Object>}
     */
    createPlan: (planData) => post('/api/test-plans', planData),
    
    /**
     * 更新测试计划
     * @param {string} planId - 计划ID
     * @param {Object} planData - 计划数据
     * @returns {Promise<Object>}
     */
    updatePlan: (planId, planData) => put(`/api/test-plans/${planId}`, planData),
    
    /**
     * 删除测试计划
     * @param {string} planId - 计划ID
     * @returns {Promise<Object>}
     */
    deletePlan: (planId) => del(`/api/test-plans/${planId}`),
    
    /**
     * 预览关键字匹配
     * @param {string} keyword - 关键字
     * @param {string} matchType - 匹配类型
     * @returns {Promise<Object>}
     */
    previewMatch: (keyword, matchType = 'fuzzy') => 
        post('/api/test-plans/preview-match', { keyword, match_type: matchType }),
    
    /**
     * 执行测试计划
     * @param {string} planId - 计划ID
     * @returns {Promise<Object>}
     */
    executePlan: (planId) => post(`/api/test-plans/${planId}/execute`),
    
    /**
     * 刷新批改状态
     * @param {string} planId - 计划ID
     * @returns {Promise<Object>}
     */
    refreshGradingStatus: (planId) => 
        post(`/api/test-plans/${planId}/refresh-grading`),
    
    // ========== AI 生成计划 ==========
    
    /**
     * AI 生成测试计划
     * @param {string[]} datasetIds - 数据集ID列表
     * @param {number} sampleCount - 测试样本数量
     * @param {number|null} subjectId - 学科ID
     * @returns {Promise<Object>}
     */
    generateAIPlan: (datasetIds, sampleCount = 30, subjectId = null) => 
        post('/api/dashboard/ai-plan', {
            dataset_ids: datasetIds,
            sample_count: sampleCount,
            subject_id: subjectId
        }),
    
    // ========== 热点图 ==========
    
    /**
     * 获取问题热点图数据
     * @param {string} subjectId - 学科ID
     * @param {number} days - 天数
     * @returns {Promise<Object>}
     */
    getHeatmap: (subjectId = '', days = 7) => 
        get(`/api/dashboard/heatmap?subject_id=${subjectId}&days=${days}`),
    
    // ========== 趋势分析 ==========
    
    /**
     * 获取趋势数据
     * @param {number} days - 天数
     * @param {string} subjectId - 学科ID
     * @returns {Promise<Object>}
     */
    getTrends: (days = 7, subjectId = '') => 
        get(`/api/dashboard/trends?days=${days}&subject_id=${subjectId}`),
    
    /**
     * 导出趋势数据
     * @param {number} days - 天数
     * @returns {string} 下载URL
     */
    exportTrends: (days = 30) => 
        `/api/dashboard/trends/export?days=${days}&format=csv`,
    
    // ========== 日报 ==========
    
    /**
     * 生成日报
     * @param {string} date - 日期 YYYY-MM-DD
     * @returns {Promise<Object>}
     */
    generateDailyReport: (date = null) => 
        post('/api/dashboard/daily-report', { date }),
    
    /**
     * 获取历史日报列表
     * @param {number} page - 页码
     * @param {number} pageSize - 每页数量
     * @returns {Promise<Object>}
     */
    getDailyReports: (page = 1, pageSize = 10) => 
        get(`/api/dashboard/daily-reports?page=${page}&page_size=${pageSize}`),
    
    /**
     * 获取日报详情
     * @param {string} reportId - 日报ID
     * @returns {Promise<Object>}
     */
    getDailyReport: (reportId) => 
        get(`/api/dashboard/daily-report/${reportId}`, false),
    
    /**
     * 导出日报
     * @param {string} reportId - 日报ID
     * @param {string} format - 导出格式
     * @returns {string} 下载URL
     */
    exportDailyReport: (reportId, format = 'docx') => 
        `/api/dashboard/daily-report/${reportId}/export?format=${format}`,
    
    // ========== 搜索 ==========
    
    /**
     * 搜索任务和数据集
     * @param {string} query - 搜索关键词
     * @param {string} type - 搜索类型
     * @returns {Promise<Object>}
     */
    search: (query, type = 'all') => 
        get(`/api/dashboard/search?q=${encodeURIComponent(query)}&type=${type}`, false),
    
    // ========== 调度 ==========
    
    /**
     * 获取调度配置
     * @param {string} planId - 计划ID
     * @returns {Promise<Object>}
     */
    getSchedule: (planId) => 
        get(`/api/test-plans/${planId}/schedule`, false),
    
    /**
     * 保存调度配置
     * @param {string} planId - 计划ID
     * @param {Object} config - 调度配置
     * @returns {Promise<Object>}
     */
    saveSchedule: (planId, config) => 
        put(`/api/test-plans/${planId}/schedule`, config),
    
    /**
     * 获取执行日志
     * @param {string} planId - 计划ID
     * @param {number} page - 页码
     * @returns {Promise<Object>}
     */
    getScheduleLogs: (planId, page = 1) => 
        get(`/api/test-plans/${planId}/logs?page=${page}`, false)
};

export default DashboardAPI;
