package com.example.nfc.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.nfc.data.*
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * RFID 模拟器 ViewModel
 * 整合班级/书本选择 + 批量发送功能
 */
class RfidSimulatorViewModel(application: Application) : AndroidViewModel(application) {

    // ========== 连接状态 ==========
    private val _connectionStatus = MutableStateFlow(AdbClientStatus())
    val connectionStatus: StateFlow<AdbClientStatus> = _connectionStatus.asStateFlow()

    private val _taskStatus = MutableStateFlow(SimulationTaskStatus())
    val taskStatus: StateFlow<SimulationTaskStatus> = _taskStatus.asStateFlow()

    private val _batchConfig = MutableStateFlow(RfidBatchConfig())
    val batchConfig: StateFlow<RfidBatchConfig> = _batchConfig.asStateFlow()

    private val _logs = MutableStateFlow<List<RfidLogEntry>>(emptyList())
    val logs: StateFlow<List<RfidLogEntry>> = _logs.asStateFlow()

    private val _remainingSeconds = MutableStateFlow(0)
    val remainingSeconds: StateFlow<Int> = _remainingSeconds.asStateFlow()

    // ========== 数据源 - 班级模式 ==========
    private val _grades = MutableStateFlow<List<GradeInfo>>(emptyList())
    val grades: StateFlow<List<GradeInfo>> = _grades.asStateFlow()

    private val _classes = MutableStateFlow<List<ClassInfo>>(emptyList())
    val classes: StateFlow<List<ClassInfo>> = _classes.asStateFlow()

    private val _students = MutableStateFlow<List<StudentInfo>>(emptyList())
    val students: StateFlow<List<StudentInfo>> = _students.asStateFlow()

    private val _selectedGrade = MutableStateFlow<Int?>(null)
    val selectedGrade: StateFlow<Int?> = _selectedGrade.asStateFlow()

    private val _selectedClass = MutableStateFlow<ClassInfo?>(null)
    val selectedClass: StateFlow<ClassInfo?> = _selectedClass.asStateFlow()


    // ========== 数据源 - 书本模式 ==========
    private val _books = MutableStateFlow<List<BookInfo>>(emptyList())
    val books: StateFlow<List<BookInfo>> = _books.asStateFlow()

    private val _bookClasses = MutableStateFlow<List<BookClassInfo>>(emptyList())
    val bookClasses: StateFlow<List<BookClassInfo>> = _bookClasses.asStateFlow()

    private val _bookStudents = MutableStateFlow<List<BookStudentRfid>>(emptyList())
    val bookStudents: StateFlow<List<BookStudentRfid>> = _bookStudents.asStateFlow()

    private val _selectedBook = MutableStateFlow<BookInfo?>(null)
    val selectedBook: StateFlow<BookInfo?> = _selectedBook.asStateFlow()

    private val _selectedBookClass = MutableStateFlow<BookClassInfo?>(null)
    val selectedBookClass: StateFlow<BookClassInfo?> = _selectedBookClass.asStateFlow()

    private val _searchKeyword = MutableStateFlow("")
    val searchKeyword: StateFlow<String> = _searchKeyword.asStateFlow()

    // ========== 选中的学生 (使用 String 统一 Long/String ID) ==========
    private val _selectedStudentIds = MutableStateFlow<Set<String>>(emptySet())
    val selectedStudentIds: StateFlow<Set<String>> = _selectedStudentIds.asStateFlow()

    // ========== 加载状态 ==========
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    // 轮询任务
    private var pollingJob: Job? = null
    private var countdownJob: Job? = null
    private var searchJob: Job? = null

    init {
        startPolling()
        loadClasses()
    }

    // ==================== 状态轮询 ====================

    private var pollFailCount = 0
    private val maxPollFails = 3

    private fun startPolling() {
        pollingJob?.cancel()
        pollingJob = viewModelScope.launch {
            while (true) {
                refreshStatus()
                // 连接正常时 2 秒轮询，异常时 5 秒
                val interval = if (pollFailCount > 0) 5000L else 2000L
                delay(interval)
            }
        }
    }

    fun refreshStatus() {
        viewModelScope.launch {
            try {
                DatabaseRepository.getRfidSimulatorStatus().onSuccess { status ->
                    _connectionStatus.value = status.connection
                    status.task?.let { _taskStatus.value = it }
                    pollFailCount = 0  // 成功则重置
                }.onFailure {
                    pollFailCount++
                    if (pollFailCount >= maxPollFails) {
                        _connectionStatus.value = AdbClientStatus(connected = false)
                    }
                }
            } catch (e: Exception) {
                pollFailCount++
                if (pollFailCount >= maxPollFails) {
                    _connectionStatus.value = AdbClientStatus(connected = false)
                }
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

    fun testConnection() {
        viewModelScope.launch {
            DatabaseRepository.testRfidConnection().onSuccess {
                addLog("info", "连接测试请求已发送")
            }.onFailure { e ->
                addLog("error", "连接测试失败: ${e.message}")
            }
            delay(500)
            refreshLogs()
        }
    }

    fun refreshConnection() {
        refreshStatus()
        refreshLogs()
    }

    // ==================== 班级模式 ====================

    fun loadClasses() {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                DatabaseRepository.getGrades().onSuccess { gradeList ->
                    _grades.value = gradeList
                }
                DatabaseRepository.getClasses().onSuccess { classList ->
                    _classes.value = classList
                }
            } catch (e: Exception) {
                _errorMessage.value = "加载班级失败: ${e.message}"
            }
            _isLoading.value = false
        }
    }

    fun selectGrade(gradeId: Int?) {
        _selectedGrade.value = gradeId
    }

    fun selectClass(classInfo: ClassInfo) {
        _selectedClass.value = classInfo
        _selectedStudentIds.value = emptySet()
        loadStudents(classInfo.id)
    }

    private fun loadStudents(classId: Long) {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                DatabaseRepository.getClassStudentsWithRfid(classId).onSuccess { studentList ->
                    val sorted = studentList
                        .filter { it.rfidNo?.isNotBlank() == true }
                        .sortedByDescending { it.isRepresentative }
                    _students.value = sorted
                    _selectedStudentIds.value = sorted.map { it.id.toString() }.toSet()
                }
            } catch (e: Exception) {
                _errorMessage.value = "加载学生失败: ${e.message}"
            }
            _isLoading.value = false
        }
    }


    // ==================== 书本模式 ====================

    fun loadBooks() {
        // 初始不加载，等搜索
    }

    fun searchBooks(keyword: String) {
        _searchKeyword.value = keyword
        searchJob?.cancel()
        
        if (keyword.isBlank()) {
            _books.value = emptyList()
            return
        }
        
        searchJob = viewModelScope.launch {
            delay(300)
            _isLoading.value = true
            try {
                DatabaseRepository.searchBooks(keyword).onSuccess { bookList ->
                    _books.value = bookList
                }
            } catch (e: Exception) {
                _errorMessage.value = "搜索书本失败: ${e.message}"
            }
            _isLoading.value = false
        }
    }

    fun selectBook(book: BookInfo) {
        _selectedBook.value = book
        _selectedBookClass.value = null
        _bookStudents.value = emptyList()
        _selectedStudentIds.value = emptySet()
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
        _selectedStudentIds.value = emptySet()
        loadBookStudents()
    }

    private fun loadBookStudents() {
        val book = _selectedBook.value ?: return
        val cls = _selectedBookClass.value ?: return
        
        viewModelScope.launch {
            _isLoading.value = true
            try {
                DatabaseRepository.getBookClassStudents(book.id, cls.id).onSuccess { studentList ->
                    val sorted = studentList
                        .filter { it.rfidNo.isNotBlank() }
                        .sortedByDescending { it.isRepresentative }
                    _bookStudents.value = sorted
                    _selectedStudentIds.value = sorted.map { it.id }.toSet()
                }
            } catch (e: Exception) {
                _errorMessage.value = "加载学生失败: ${e.message}"
            }
            _isLoading.value = false
        }
    }

    // ==================== 学生选择 ====================

    fun toggleStudent(studentId: String) {
        val current = _selectedStudentIds.value.toMutableSet()
        if (current.contains(studentId)) {
            current.remove(studentId)
        } else {
            current.add(studentId)
        }
        _selectedStudentIds.value = current
    }

    fun selectAllStudents(selectAll: Boolean) {
        val classStudentIds = _students.value
            .filter { it.rfidNo?.isNotBlank() == true }
            .map { it.id.toString() }
        val bookStudentIds = _bookStudents.value
            .filter { it.rfidNo.isNotBlank() }
            .map { it.id }
        
        val allIds = (classStudentIds + bookStudentIds).toSet()
        _selectedStudentIds.value = if (selectAll) allIds else emptySet()
    }

    // ==================== 批量配置 ====================

    fun updateInterval(seconds: Int) {
        _batchConfig.value = _batchConfig.value.copy(intervalSeconds = seconds)
    }


    // ==================== 批量模拟控制 ====================

    fun startBatchSimulation() {
        val selectedIds = _selectedStudentIds.value
        if (selectedIds.isEmpty()) {
            _errorMessage.value = "请先选择学生"
            return
        }
        
        val cards = mutableListOf<Map<String, String>>()
        
        // 班级模式学生
        _students.value
            .filter { selectedIds.contains(it.id.toString()) && it.rfidNo?.isNotBlank() == true }
            .forEach { cards.add(mapOf("name" to it.name, "card_number" to (it.rfidNo ?: ""))) }
        
        // 书本模式学生
        _bookStudents.value
            .filter { selectedIds.contains(it.id) && it.rfidNo.isNotBlank() }
            .forEach { cards.add(mapOf("name" to it.name, "card_number" to it.rfidNo)) }
        
        if (cards.isEmpty()) {
            _errorMessage.value = "选中的学生没有有效 RFID"
            return
        }
        
        viewModelScope.launch {
            _isLoading.value = true
            try {
                val config = _batchConfig.value
                DatabaseRepository.startRfidBatch(
                    cards = cards,
                    intervalSeconds = config.intervalSeconds,
                    sendEnter = config.sendEnter,
                    devicePath = config.devicePath
                ).onSuccess { task ->
                    _taskStatus.value = task
                    addLog("info", "批量模拟已启动，共 ${task.totalCount} 张卡片")
                    startCountdown(config.intervalSeconds)
                }.onFailure { e ->
                    _errorMessage.value = "启动失败: ${e.message}"
                    addLog("error", "启动失败: ${e.message}")
                }
            } catch (e: Exception) {
                _errorMessage.value = "启动失败: ${e.message}"
            }
            _isLoading.value = false
        }
    }

    fun pauseBatchSimulation() {
        viewModelScope.launch {
            DatabaseRepository.pauseRfidBatch().onSuccess {
                _taskStatus.value = _taskStatus.value.copy(status = "paused")
                addLog("info", "批量模拟已暂停")
                stopCountdown()
            }.onFailure { e ->
                addLog("error", "暂停失败: ${e.message}")
            }
        }
    }

    fun resumeBatchSimulation() {
        viewModelScope.launch {
            DatabaseRepository.resumeRfidBatch().onSuccess {
                _taskStatus.value = _taskStatus.value.copy(status = "running")
                addLog("info", "批量模拟已恢复")
                startCountdown(_batchConfig.value.intervalSeconds)
            }.onFailure { e ->
                addLog("error", "恢复失败: ${e.message}")
            }
        }
    }

    fun stopBatchSimulation() {
        viewModelScope.launch {
            DatabaseRepository.stopRfidBatch().onSuccess {
                _taskStatus.value = SimulationTaskStatus()
                addLog("info", "批量模拟已停止")
                stopCountdown()
            }.onFailure { e ->
                addLog("error", "停止失败: ${e.message}")
            }
        }
    }

    // ==================== 倒计时 ====================

    private fun startCountdown(intervalSeconds: Int) {
        stopCountdown()
        countdownJob = viewModelScope.launch {
            while (true) {
                for (i in intervalSeconds downTo 1) {
                    _remainingSeconds.value = i
                    delay(1000)
                }
                _remainingSeconds.value = 0
                refreshStatus()
                refreshLogs()
            }
        }
    }

    private fun stopCountdown() {
        countdownJob?.cancel()
        countdownJob = null
        _remainingSeconds.value = 0
    }

    // ==================== 日志管理 ====================

    fun clearLogs() {
        viewModelScope.launch {
            DatabaseRepository.clearRfidLogs().onSuccess {
                _logs.value = emptyList()
            }
        }
    }

    fun clearError() {
        _errorMessage.value = null
    }

    private fun addLog(level: String, message: String) {
        val time = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault())
            .format(java.util.Date())
        val newLog = RfidLogEntry(time = time, level = level, message = message)
        _logs.value = listOf(newLog) + _logs.value.take(49)
    }

    // ==================== 生命周期 ====================

    override fun onCleared() {
        super.onCleared()
        pollingJob?.cancel()
        countdownJob?.cancel()
        searchJob?.cancel()
    }
}
