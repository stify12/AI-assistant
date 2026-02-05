package com.example.nfc.data

import java.util.UUID

data class CardInfo(
    val id: String = UUID.randomUUID().toString(),
    val name: String,
    val cardNumber: String,
    val isSelected: Boolean = false,
    val studentId: Long? = null,
    val classId: Long? = null,
    val className: String? = null  // 班级名称，用于分组显示
)

data class BatchConfig(
    val intervalSeconds: Int = 5,
    val isRunning: Boolean = false,
    val isPaused: Boolean = false,  // 暂停状态
    val currentIndex: Int = 0,
    val totalCount: Int = 0,
    val successCount: Int = 0,  // 成功数量
    val failedCount: Int = 0    // 失败数量
)

/** 卡片分组（按班级） */
data class CardGroup(
    val classId: Long?,
    val className: String,
    val cards: List<CardInfo>,
    val isExpanded: Boolean = true
)

/** 上次使用记录 */
data class LastUsedInfo(
    val classId: Long,
    val className: String,
    val studentCount: Int,
    val lastUsedTime: Long = System.currentTimeMillis()
)

/** 最近使用的班级历史（最多5个） */
data class RecentClassInfo(
    val classId: Long,
    val className: String,
    val gradeName: String,
    val studentCount: Int,
    val rfidCount: Int,  // 有卡学生数
    val lastUsedTime: Long = System.currentTimeMillis()
)

// ========== 数据库实体 ==========

/** 年级信息 */
data class GradeInfo(
    val id: Int,
    val name: String
) {
    companion object {
        val GRADE_MAP = mapOf(
            1 to "一年级", 2 to "二年级", 3 to "三年级",
            4 to "四年级", 5 to "五年级", 6 to "六年级",
            7 to "七年级", 8 to "八年级", 9 to "九年级",
            10 to "高一", 11 to "高二", 12 to "高三"
        )
        
        fun fromId(id: Int) = GradeInfo(id, GRADE_MAP[id] ?: "${id}年级")
    }
}

/** 老师信息 */
data class TeacherInfo(
    val id: Long,
    val name: String,
    val subjectId: Int? = null,
    val subjectName: String? = null
)

/** 班级信息 */
data class ClassInfo(
    val id: Long,
    val name: String,
    val grade: Int,
    val gradeName: String,
    val studentCount: Int = 0,
    val rfidCount: Int = 0,  // 有卡学生数
    val teacherId: String? = null,
    val isFavorite: Boolean = false,
    val isCached: Boolean = false  // 是否已缓存
)

/** 学生信息（含RFID） */
data class StudentInfo(
    val id: Long,
    val name: String,
    val stuNum: String? = null,
    val sex: Int = 1,
    val classId: Long,
    val className: String? = null,
    val rfidNo: String? = null,
    val isRepresentative: Boolean = false,  // 是否课代表
    val subjectId: String? = null,          // 学科ID
    val subjectName: String? = null         // 学科名称（如"数学课代表"）
)

/** 筛选条件 */
data class FilterState(
    val gradeId: Int? = null,
    val teacherId: Long? = null,
    val searchKeyword: String = ""
)

/** 缓存的班级数据（离线模式） */
data class CachedClassData(
    val classInfo: ClassInfo,
    val students: List<StudentInfo>,
    val cachedTime: Long = System.currentTimeMillis()
)

// ========== 书本相关实体 ==========

/** 书本信息 */
data class BookInfo(
    val id: String,
    val bookSn: String? = null,
    val bookName: String,
    val subjectId: Int? = null,
    val subjectName: String? = null,
    val gradeId: Int? = null,
    val gradeName: String? = null,
    val publishing: String? = null
)

/** 书本关联的班级 */
data class BookClassInfo(
    val id: String,
    val name: String,
    val gradeId: Int? = null,
    val gradeName: String? = null,
    val studentCount: Int = 0
)

/** 书本学生RFID */
data class BookStudentRfid(
    val id: String,
    val name: String,
    val stuNum: String? = null,
    val className: String? = null,
    val rfidNo: String,
    val isRepresentative: Boolean = false,
    val subjectName: String? = null
)

/** 上次使用的书本记录 */
data class LastUsedBookInfo(
    val bookId: String,
    val bookName: String,
    val classId: String,
    val className: String,
    val studentCount: Int,
    val lastUsedTime: Long = System.currentTimeMillis()
)

/** 科目筛选 */
data class SubjectInfo(
    val id: Int,
    val name: String
) {
    companion object {
        val SUBJECT_LIST = listOf(
            SubjectInfo(0, "英语"),
            SubjectInfo(1, "语文"),
            SubjectInfo(2, "数学"),
            SubjectInfo(3, "物理"),
            SubjectInfo(4, "化学"),
            SubjectInfo(5, "生物"),
            SubjectInfo(6, "地理")
        )
    }
}
