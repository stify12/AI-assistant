# -*- coding: utf-8 -*-
"""修复 calculateAccuracyStats 函数"""

with open('static/js/batch-evaluation.js', 'r', encoding='gbk') as f:
    content = f.read()

# 找到旧的 calculateAccuracyStats 函数
old_func_start = content.find('function calculateAccuracyStats(homeworkItems) {')
old_func_end = content.find('// ========== 计算一致性', old_func_start)

if old_func_start == -1 or old_func_end == -1:
    print('ERROR: 找不到函数位置')
    exit(1)

print(f'旧函数位置: {old_func_start} - {old_func_end}')

# 新的函数实现 - 基于 error_distribution
new_func = r'''function calculateAccuracyStats(homeworkItems) {
    console.log('[calculateAccuracyStats] 开始计算, items数量:', homeworkItems.length);
    
    let totalQuestions = 0;
    let recognitionCorrect = 0;
    let gradingCorrect = 0;

    homeworkItems.forEach((item, idx) => {
        const evaluation = item.evaluation || {};
        const analysis = evaluation.analysis || {};
        const errorDist = evaluation.error_distribution || {};
        
        const itemTotal = analysis.total_questions || 0;
        totalQuestions += itemTotal;
        
        if (itemTotal === 0) {
            console.log(`[Item ${idx}] 无题目数据`);
            return;
        }
        
        // 基于 error_distribution 计算
        let recognitionErrors = 0;
        let gradingErrors = 0;
        
        Object.keys(errorDist).forEach(key => {
            const count = errorDist[key] || 0;
            if (key.includes('识别错误')) {
                recognitionErrors += count;
            }
            if (key.includes('判断错误') && !key.includes('识别错误')) {
                gradingErrors += count;
            }
        });
        
        const itemRecCorrect = itemTotal - recognitionErrors;
        const itemGradeCorrect = itemRecCorrect - gradingErrors;
        
        console.log(`[Item ${idx}] total=${itemTotal}, recErr=${recognitionErrors}, gradeErr=${gradingErrors}`);
        
        recognitionCorrect += itemRecCorrect;
        gradingCorrect += itemGradeCorrect;
    });

    console.log('[calculateAccuracyStats] 结果:', {totalQuestions, recognitionCorrect, gradingCorrect});

    return {
        totalQuestions,
        recognitionCorrect,
        recognitionWrong: Math.max(0, totalQuestions - recognitionCorrect),
        gradingCorrect,
        gradingWrong: Math.max(0, recognitionCorrect - gradingCorrect),
        recognitionRate: totalQuestions > 0 ? (recognitionCorrect / totalQuestions) * 100 : 0,
        gradingRate: recognitionCorrect > 0 ? (gradingCorrect / recognitionCorrect) * 100 : 0
    };
}

'''

# 替换函数
new_content = content[:old_func_start] + new_func + content[old_func_end:]

with open('static/js/batch-evaluation.js', 'w', encoding='gbk') as f:
    f.write(new_content)

print('SUCCESS: 函数已替换')
print(f'新文件大小: {len(new_content)} 字符')
