/**
 * 数据集概览模块 - 简化版
 * @module dashboard-datasets
 * @description 提供数据集统计的初始化和加载功能
 * 注意：主要渲染逻辑已移至 index.js 内联实现
 */

import { DashboardAPI } from './dashboard-api.js';
import { SUBJECT_MAP, SUBJECT_COLORS, escapeHtml, showToast, toggleSkeleton } from './dashboard-utils.js';
import { PieChart, animateNumber } from './dashboard-charts.js';

// ========== 状态 ==========
let datasetStats = null;
let pieChart = null;

// ========== 初始化 ==========

/**
 * 初始化数据集概览模块
 */
export async function initDatasetOverview() {
    await loadDatasetStats();
}

/**
 * 加载数据集统计数据
 */
export async function loadDatasetStats() {
    try {
        const res = await DashboardAPI.getDatasets();
        if (res.success) {
            datasetStats = {
                total: res.data.total || 0,
                by_subject: res.data.by_subject || {},
                datasets: res.data.datasets || []
            };
            return datasetStats;
        }
    } catch (error) {
        console.error('[Datasets] 加载失败:', error);
    }
    return null;
}

export default { initDatasetOverview, loadDatasetStats };
