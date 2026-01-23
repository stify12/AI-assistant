/**
 * 学科分析模块 - 简化版
 * @module dashboard-subjects
 * @description 提供学科分析的导出功能
 * 注意：主要渲染逻辑已移至 index.js 内联实现
 */

import { showToast } from './dashboard-utils.js';
import { DashboardAPI } from './dashboard-api.js';

/**
 * 导出学科分析报告
 * 从 API 获取最新数据并导出为 CSV
 */
export async function exportSubjectReport() {
    try {
        const res = await DashboardAPI.getSubjects();
        if (!res.success || !res.data || res.data.length === 0) {
            showToast('暂无数据可导出', 'warning');
            return;
        }
        
        const subjects = res.data;
        const headers = ['学科', '任务数', '作业数', '题目数', '正确数', '准确率'];
        const rows = subjects.map(s => [
            s.subject_name || '--',
            s.task_count || 0,
            s.homework_count || 0,
            s.question_count || 0,
            s.correct_count || 0,
            s.accuracy != null ? (s.accuracy * 100).toFixed(1) + '%' : '--'
        ]);
        
        const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
        const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `学科评估报告_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        
        URL.revokeObjectURL(url);
        showToast('报告导出成功', 'success');
    } catch (error) {
        console.error('[Subjects] 导出失败:', error);
        showToast('导出失败', 'error');
    }
}

export default { exportSubjectReport };
