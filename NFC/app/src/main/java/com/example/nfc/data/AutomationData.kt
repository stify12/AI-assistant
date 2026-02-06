package com.example.nfc.data

/**
 * 自动化流程数据模型
 * 支持"选书本+页码 → 自动发布+提交作业"全流程
 */

/** 自动化流程配置 */
data class AutomationConfig(
    val username: String = "shuxue",
    val password: String = "123456zp.",
    val homeworkName: String = "",           // 留空则自动生成
    val pageNumber: Int = 1,                 // 页码
    val photoInterval: Int = 2,              // 拍照间隔(秒)
    val enableDoublePageMode: Boolean = true // 双页模式
)

/** 最近使用记录 */
data class RecentUsage(
    val bookId: String,
    val bookName: String,
    val classId: String,
    val className: String,
    val pageNumber: Int,
    val studentCount: Int,
    val timestamp: Long = System.currentTimeMillis()
)

/** 收藏的书本 */
data class FavoriteBook(
    val bookId: String,
    val bookName: String,
    val subjectName: String? = null,
    val gradeName: String? = null,
    val timestamp: Long = System.currentTimeMillis()
)

/** 学科选项 */
data class SubjectOption(
    val id: Int,
    val name: String
) {
    companion object {
        val all = listOf(
            SubjectOption(0, "全部"),
            SubjectOption(2, "数学"),
            SubjectOption(3, "物理"),
            SubjectOption(4, "化学"),
            SubjectOption(5, "生物"),
            SubjectOption(1, "语文"),
            SubjectOption(0, "英语")
        )
    }
}

/** 年级选项 */
data class GradeOption(
    val id: Int,
    val name: String
) {
    companion object {
        val all = listOf(
            GradeOption(0, "全部"),
            GradeOption(7, "七年级"),
            GradeOption(8, "八年级"),
            GradeOption(9, "九年级"),
            GradeOption(10, "高一"),
            GradeOption(11, "高二"),
            GradeOption(12, "高三")
        )
    }
}

/** 自动化流程状态 */
enum class AutomationPhase {
    IDLE,           // 空闲
    PUBLISHING,     // 发布作业中
    WAITING,        // 等待中（发布完成，准备提交）
    SUBMITTING,     // 提交作业中
    COMPLETED,      // 完成
    ERROR           // 错误
}

/** 自动化流程状态 */
data class AutomationStatus(
    val phase: AutomationPhase = AutomationPhase.IDLE,
    val currentStep: Int = 0,
    val totalSteps: Int = 0,
    val stepDescription: String = "",
    val errorMessage: String? = null,
    val progress: Float = 0f                 // 0-1
)

/** 流程步骤定义 */
data class WorkflowStep(
    val action: String,
    val description: String,
    val params: Map<String, Any> = emptyMap(),
    val waitSeconds: Float = 0f
)

/** 页码选项 */
data class PageOption(
    val number: Int,
    val label: String
) {
    companion object {
        // 预设页码选项
        val presets = listOf(
            PageOption(1, "第1页"),
            PageOption(2, "第2页"),
            PageOption(3, "第3页"),
            PageOption(4, "第4页"),
            PageOption(5, "第5页"),
            PageOption(6, "第6页"),
            PageOption(7, "第7页"),
            PageOption(8, "第8页"),
            PageOption(9, "第9页"),
            PageOption(10, "第10页")
        )
    }
}
