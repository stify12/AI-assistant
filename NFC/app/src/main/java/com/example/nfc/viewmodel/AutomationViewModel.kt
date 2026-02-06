package com.example.nfc.viewmodel

import android.app.Application
import android.content.Context
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.nfc.data.*
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject

/**
 * 自动化流程 ViewModel
 * 管理"选书本+页码 → 自动发布+提交作业"全流程
 */
class AutomationViewModel(application: Application) : AndroidViewModel(application) {

    private val prefs = application.getSharedPreferences("automation_prefs", Context.MODE_PRIVATE)

    // ========== 连接状态 ==========
    private val _connectionStatus = MutableStateFlow(AdbClientStatus())
    val connectionStatus: StateFlow<AdbClientStatus> = _connectionStatus.asStateFlow()

    // ========== 自动化配置 ==========
    private val _config = MutableStateFlow(AutomationConfig())
    val config: StateFlow<AutomationConfig> = _config.asStateFlow()

    // ========== 自动化状态 ==========
    private val _automationStatus = MutableStateFlow(AutomationStatus())
    val automationStatus: StateFlow<AutomationStatus> = _automationStatus.asStateFlow()

    // ========== 最近使用 ==========
    private val _recentUsages = MutableStateFlow<List<RecentUsage>>(emptyList())
    val recentUsages: StateFlow<List<RecentUsage>> = _recentUsages.asStateFlow()

    // ========== 收藏书本 ==========
    private val _favoriteBooks = MutableStateFlow<List<FavoriteBook>>(emptyList())
    val favoriteBooks: StateFlow<List<FavoriteBook>> = _favoriteBooks.asStateFlow()

    // ========== 筛选条件 ==========
    private val _selectedSubjectId = MutableStateFlow(0)
    val selectedSubjectId: StateFlow<Int> = _selectedSubjectId.asStateFlow()

    private val _selectedGradeId = MutableStateFlow(0)
    val selectedGradeId: StateFlow<Int> = _selectedGradeId.asStateFlow()

    // ========== 书本数据 ==========
    private val _books = MutableStateFlow<List<BookInfo>>(emptyList())
    val books: StateFlow<List<BookInfo>> = _books.asStateFlow()

    private val _selectedBook = MutableStateFlow<BookInfo?>(null)
    val selectedBook: StateFlow<BookInfo?> = _selectedBook.asStateFlow()

    private val _bookClasses = MutableStateFlow<List<BookClassInfo>>(emptyList())
    val bookClasses: StateFlow<List<BookClassInfo>> = _bookClasses.asStateFlow()

    private val _selectedBookClass = MutableStateFlow<BookClassInfo?>(null)
    val selectedBookClass: StateFlow<BookClassInfo?> = _selectedBookClass.asStateFlow()

    private val _bookStudents = MutableStateFlow<List<BookStudentRfid>>(emptyList())
    val bookStudents: StateFlow<List<BookStudentRfid>> = _bookStudents.asStateFlow()

    private val _searchKeyword = MutableStateFlow("")
    val searchKeyword: StateFlow<String> = _searchKeyword.asStateFlow()

    // ========== 加载状态 ==========
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    // ========== 日志 ==========
    private val _logs = MutableStateFlow<List<RfidLogEntry>>(emptyList())
    val logs: StateFlow<List<RfidLogEntry>> = _logs.asStateFlow()

    // 内部任务
    private var pollingJob: Job? = null
    private var automationJob: Job? = null
    private var searchJob: Job? = null

    init {
        loadPersistedData()
        startPolling()
    }

    // ==================== 持久化 ====================

    private fun loadPersistedData() {
        // 加载最近使用
        try {
            val recentJson = prefs.getString("recent_usages", "[]") ?: "[]"
            val arr = JSONArray(recentJson)
            val list = mutableListOf<RecentUsage>()
            for (i in 0 until arr.length()) {
                val obj = arr.getJSONObject(i)
                list.add(RecentUsage(
                    bookId = obj.getString("bookId"),
                    bookName = obj.getString("bookName"),
                    classId = obj.getString("classId"),
                    className = obj.getString("className"),
                    pageNumber = obj.optInt("pageNumber", 1),
                    studentCount = obj.optInt("studentCount", 0),
                    timestamp = obj.optLong("timestamp", 0)
                ))
            }
            _recentUsages.value = list.sortedByDescending { it.timestamp }.take(3)
        } catch (_: Exception) {}

        // 加载收藏
        try {
            val favJson = prefs.getString("favorite_books", "[]") ?: "[]"
            val arr = JSONArray(favJson)
            val list = mutableListOf<FavoriteBook>()
            for (i in 0 until arr.length()) {
                val obj = arr.getJSONObject(i)
                list.add(FavoriteBook(
                    bookId = obj.getString("bookId"),
                    bookName = obj.getString("bookName"),
                    subjectName = obj.optString("subjectName", null),
                    gradeName = obj.optString("gradeName", null),
                    timestamp = obj.optLong("timestamp", 0)
                ))
            }
            _favoriteBooks.value = list
        } catch (_: Exception) {}

        // 加载上次配置
        val lastPage = prefs.getInt("last_page_number", 1)
        _config.value = _config.value.copy(pageNumber = lastPage)
    }

    private fun saveRecentUsages() {
        try {
            val arr = JSONArray()
            _recentUsages.value.forEach { r ->
                arr.put(JSONObject().apply {
                    put("bookId", r.bookId)
                    put("bookName", r.bookName)
                    put("classId", r.classId)
                    put("className", r.className)
                    put("pageNumber", r.pageNumber)
                    put("studentCount", r.studentCount)
                    put("timestamp", r.timestamp)
                })
            }
            prefs.edit().putString("recent_usages", arr.toString()).apply()
        } catch (_: Exception) {}
    }

    private fun saveFavoriteBooks() {
        try {
            val arr = JSONArray()
            _favoriteBooks.value.forEach { f ->
                arr.put(JSONObject().apply {
                    put("bookId", f.bookId)
                    put("bookName", f.bookName)
                    put("subjectName", f.subjectName ?: "")
                    put("gradeName", f.gradeName ?: "")
                    put("timestamp", f.timestamp)
                })
            }
            prefs.edit().putString("favorite_books", arr.toString()).apply()
        } catch (_: Exception) {}
    }

    /** 添加到最近使用 */
    private fun addToRecentUsage() {
        val book = _selectedBook.value ?: return
        val cls = _selectedBookClass.value ?: return
        
        val newUsage = RecentUsage(
            bookId = book.id,
            bookName = book.bookName,
            classId = cls.id,
            className = cls.name,
            pageNumber = _config.value.pageNumber,
            studentCount = _bookStudents.value.size
        )
        
        // 去重并保留最近3个
        val updated = listOf(newUsage) + _recentUsages.value.filter { 
            !(it.bookId == newUsage.bookId && it.classId == newUsage.classId) 
        }
        _recentUsages.value = updated.take(3)
        saveRecentUsages()
        
        // 保存页码
        prefs.edit().putInt("last_page_number", _config.value.pageNumber).apply()
    }

    // ==================== 收藏功能 ====================

    fun toggleFavorite(book: BookInfo) {
        val current = _favoriteBooks.value.toMutableList()
        val existing = current.find { it.bookId == book.id }
        if (existing != null) {
            current.remove(existing)
        } else {
            current.add(FavoriteBook(
                bookId = book.id,
                bookName = book.bookName,
                subjectName = book.subjectName,
                gradeName = book.gradeName
            ))
        }
        _favoriteBooks.value = current
        saveFavoriteBooks()
    }

    fun isFavorite(bookId: String): Boolean {
        return _favoriteBooks.value.any { it.bookId == bookId }
    }

    // ==================== 快速开始（从最近使用） ====================

    fun quickStartFromRecent(usage: RecentUsage) {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                // 加载书本班级学生
                DatabaseRepository.getBookClassStudents(usage.bookId, usage.classId).onSuccess { students ->
                    _bookStudents.value = students.filter { it.rfidNo.isNotBlank() }
                    _selectedBook.value = BookInfo(id = usage.bookId, bookName = usage.bookName)
                    _selectedBookClass.value = BookClassInfo(id = usage.classId, name = usage.className)
                    _config.value = _config.value.copy(pageNumber = usage.pageNumber)
                    
                    // 直接开始
                    if (_bookStudents.value.isNotEmpty() && _connectionStatus.value.connected) {
                        startAutomation()
                    }
                }
            } catch (e: Exception) {
                _errorMessage.value = "加载失败: ${e.message}"
            }
            _isLoading.value = false
        }
    }

    // ==================== 状态轮询 ====================

    private fun startPolling() {
        pollingJob?.cancel()
        pollingJob = viewModelScope.launch {
            while (true) {
                refreshStatus()
                delay(3000)
            }
        }
    }

    private fun refreshStatus() {
        viewModelScope.launch {
            try {
                DatabaseRepository.getRfidSimulatorStatus().onSuccess { status ->
                    _connectionStatus.value = status.connection
                }
            } catch (_: Exception) {
                _connectionStatus.value = AdbClientStatus(connected = false)
            }
        }
    }

    fun refreshLogs() {
        viewModelScope.launch {
            try {
                DatabaseRepository.getRfidSimulatorLogs().onSuccess { logList ->
                    _logs.value = logList
                }
            } catch (_: Exception) {}
        }
    }

    // ==================== 筛选条件 ====================

    fun selectSubject(subjectId: Int) {
        _selectedSubjectId.value = subjectId
        performSearch()
    }

    fun selectGrade(gradeId: Int) {
        _selectedGradeId.value = gradeId
        performSearch()
    }

    // ==================== 书本搜索 ====================

    fun searchBooks(keyword: String) {
        _searchKeyword.value = keyword
        performSearch()
    }

    private fun performSearch() {
        searchJob?.cancel()
        
        val keyword = _searchKeyword.value
        val subjectId = _selectedSubjectId.value
        val gradeId = _selectedGradeId.value
        
        // 如果没有任何筛选条件，不搜索
        if (keyword.isBlank() && subjectId == 0 && gradeId == 0) {
            _books.value = emptyList()
            return
        }
        
        searchJob = viewModelScope.launch {
            delay(300)
            _isLoading.value = true
            try {
                DatabaseRepository.searchBooks(
                    keyword = keyword,
                    subjectId = if (subjectId > 0) subjectId else null
                ).onSuccess { bookList ->
                    // 客户端过滤年级
                    val filtered = if (gradeId > 0) {
                        bookList.filter { it.gradeId == gradeId }
                    } else {
                        bookList
                    }
                    _books.value = filtered
                }
            } catch (e: Exception) {
                _errorMessage.value = "搜索失败: ${e.message}"
            }
            _isLoading.value = false
        }
    }

    fun selectBook(book: BookInfo) {
        _selectedBook.value = book
        _selectedBookClass.value = null
        _bookStudents.value = emptyList()
        loadBookClasses(book.id)
    }

    private fun loadBookClasses(bookId: String) {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                DatabaseRepository.getBookClasses(bookId).onSuccess { classList ->
                    _bookClasses.value = classList
                    if (classList.isNotEmpty()) {
                        selectBookClass(classList.first())
                    }
                }
            } catch (e: Exception) {
                _errorMessage.value = "加载班级失败: ${e.message}"
            }
            _isLoading.value = false
        }
    }

    fun selectBookClass(classInfo: BookClassInfo) {
        _selectedBookClass.value = classInfo
        loadBookStudents()
    }

    private fun loadBookStudents() {
        val book = _selectedBook.value ?: return
        val cls = _selectedBookClass.value ?: return
        
        viewModelScope.launch {
            _isLoading.value = true
            try {
                DatabaseRepository.getBookClassStudents(book.id, cls.id).onSuccess { studentList ->
                    _bookStudents.value = studentList
                        .filter { it.rfidNo.isNotBlank() }
                        .sortedByDescending { it.isRepresentative }
                }
            } catch (e: Exception) {
                _errorMessage.value = "加载学生失败: ${e.message}"
            }
            _isLoading.value = false
        }
    }

    // ==================== 配置更新 ====================

    fun updateConfig(update: (AutomationConfig) -> AutomationConfig) {
        _config.value = update(_config.value)
    }

    fun updatePageNumber(page: Int) {
        _config.value = _config.value.copy(pageNumber = page)
    }

    fun updateUsername(username: String) {
        _config.value = _config.value.copy(username = username)
    }

    fun updatePassword(password: String) {
        _config.value = _config.value.copy(password = password)
    }

    fun updateHomeworkName(name: String) {
        _config.value = _config.value.copy(homeworkName = name)
    }

    fun updatePhotoInterval(interval: Int) {
        _config.value = _config.value.copy(photoInterval = interval)
    }

    fun toggleDoublePageMode() {
        _config.value = _config.value.copy(
            enableDoublePageMode = !_config.value.enableDoublePageMode
        )
    }

    // ==================== 自动化流程控制 ====================

    /** 开始自动化流程 */
    fun startAutomation() {
        if (_selectedBook.value == null) {
            _errorMessage.value = "请先选择书本"
            return
        }
        if (_bookStudents.value.isEmpty()) {
            _errorMessage.value = "没有可用的学生数据"
            return
        }
        if (!_connectionStatus.value.connected) {
            _errorMessage.value = "请先连接 ADB 客户端"
            return
        }

        // 保存到最近使用
        addToRecentUsage()

        automationJob?.cancel()
        automationJob = viewModelScope.launch {
            runAutomationFlow()
        }
    }

    /** 停止自动化流程 */
    fun stopAutomation() {
        automationJob?.cancel()
        _automationStatus.value = AutomationStatus(phase = AutomationPhase.IDLE)
        addLog("info", "自动化流程已停止")
    }

    /** 执行自动化流程 */
    private suspend fun runAutomationFlow() {
        try {
            // 阶段1: 发布作业
            _automationStatus.value = AutomationStatus(
                phase = AutomationPhase.PUBLISHING,
                stepDescription = "正在发布作业..."
            )
            addLog("info", "开始发布作业流程")
            
            val publishResult = runPublishWorkflow()
            if (!publishResult) {
                _automationStatus.value = AutomationStatus(
                    phase = AutomationPhase.ERROR,
                    errorMessage = "发布作业失败"
                )
                return
            }
            
            addLog("success", "发布作业完成")
            
            // 阶段2: 等待
            _automationStatus.value = AutomationStatus(
                phase = AutomationPhase.WAITING,
                stepDescription = "等待3秒后开始提交..."
            )
            delay(3000)
            
            // 阶段3: 提交作业
            _automationStatus.value = AutomationStatus(
                phase = AutomationPhase.SUBMITTING,
                stepDescription = "正在提交作业..."
            )
            addLog("info", "开始提交作业流程")
            
            val submitResult = runSubmitWorkflow()
            if (!submitResult) {
                _automationStatus.value = AutomationStatus(
                    phase = AutomationPhase.ERROR,
                    errorMessage = "提交作业失败"
                )
                return
            }
            
            // 完成
            _automationStatus.value = AutomationStatus(
                phase = AutomationPhase.COMPLETED,
                stepDescription = "全部完成"
            )
            addLog("success", "自动化流程完成")
            
        } catch (e: Exception) {
            _automationStatus.value = AutomationStatus(
                phase = AutomationPhase.ERROR,
                errorMessage = e.message ?: "未知错误"
            )
            addLog("error", "自动化流程出错: ${e.message}")
        }
    }

    /** 执行发布作业流程 */
    private suspend fun runPublishWorkflow(): Boolean {
        val cfg = _config.value
        return try {
            DatabaseRepository.runWorkflow(
                workflowId = "publish_homework",
                params = mapOf(
                    "username" to cfg.username,
                    "password" to cfg.password,
                    "homework_name" to cfg.homeworkName.ifBlank { 
                        "自动作业_${System.currentTimeMillis() % 10000}" 
                    }
                )
            ).isSuccess
        } catch (e: Exception) {
            addLog("error", "发布流程失败: ${e.message}")
            false
        }
    }

    /** 执行提交作业流程 */
    private suspend fun runSubmitWorkflow(): Boolean {
        val students = _bookStudents.value
        if (students.isEmpty()) return false
        
        val cards = students.map { mapOf("name" to it.name, "card_number" to it.rfidNo) }
        val cfg = _config.value
        
        return try {
            // 先执行提交流程的前置步骤
            DatabaseRepository.runWorkflow(
                workflowId = "submit_homework",
                params = mapOf("photo_interval" to cfg.photoInterval)
            )
            
            // 然后批量刷卡
            DatabaseRepository.startRfidBatch(
                cards = cards,
                intervalSeconds = cfg.photoInterval + 1,
                sendEnter = true,
                devicePath = "/dev/input/event2"
            ).isSuccess
        } catch (e: Exception) {
            addLog("error", "提交流程失败: ${e.message}")
            false
        }
    }

    // ==================== 日志管理 ====================

    private fun addLog(level: String, message: String) {
        val time = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault())
            .format(java.util.Date())
        val newLog = RfidLogEntry(time = time, level = level, message = message)
        _logs.value = listOf(newLog) + _logs.value.take(49)
    }

    fun clearLogs() {
        _logs.value = emptyList()
    }

    fun clearError() {
        _errorMessage.value = null
    }

    // ==================== 清理 ====================

    override fun onCleared() {
        super.onCleared()
        pollingJob?.cancel()
        automationJob?.cancel()
        searchJob?.cancel()
    }
}
