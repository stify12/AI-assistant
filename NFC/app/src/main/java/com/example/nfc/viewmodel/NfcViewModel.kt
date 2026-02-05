package com.example.nfc.viewmodel

import android.app.Application
import android.content.Context
import android.nfc.NfcAdapter
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.nfc.data.*
import com.example.nfc.service.NfcHceService
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class NfcViewModel(application: Application) : AndroidViewModel(application) {

    private val prefs = application.getSharedPreferences("nfc_cards", Context.MODE_PRIVATE)
    private val dbPrefs = application.getSharedPreferences("nfc_database", Context.MODE_PRIVATE)
    private val gson = Gson()

    // ========== 卡片管理 ==========
    private val _cards = MutableStateFlow<List<CardInfo>>(emptyList())
    val cards: StateFlow<List<CardInfo>> = _cards.asStateFlow()

    // 按班级分组的卡片
    private val _cardGroups = MutableStateFlow<List<CardGroup>>(emptyList())
    val cardGroups: StateFlow<List<CardGroup>> = _cardGroups.asStateFlow()

    private val _batchConfig = MutableStateFlow(BatchConfig())
    val batchConfig: StateFlow<BatchConfig> = _batchConfig.asStateFlow()

    private val _currentCard = MutableStateFlow<CardInfo?>(null)
    val currentCard: StateFlow<CardInfo?> = _currentCard.asStateFlow()

    private val _isNfcEnabled = MutableStateFlow(false)
    val isNfcEnabled: StateFlow<Boolean> = _isNfcEnabled.asStateFlow()

    private val _remainingSeconds = MutableStateFlow(0)
    val remainingSeconds: StateFlow<Int> = _remainingSeconds.asStateFlow()

    // 上次使用的班级
    private val _lastUsedClass = MutableStateFlow<LastUsedInfo?>(null)
    val lastUsedClass: StateFlow<LastUsedInfo?> = _lastUsedClass.asStateFlow()

    // 最近使用的班级历史（最多5个）
    private val _recentClasses = MutableStateFlow<List<RecentClassInfo>>(emptyList())
    val recentClasses: StateFlow<List<RecentClassInfo>> = _recentClasses.asStateFlow()

    private var batchJob: Job? = null

    // ========== 数据库相关 ==========
    private val _grades = MutableStateFlow<List<GradeInfo>>(emptyList())
    val grades: StateFlow<List<GradeInfo>> = _grades.asStateFlow()

    private val _teachers = MutableStateFlow<List<TeacherInfo>>(emptyList())
    val teachers: StateFlow<List<TeacherInfo>> = _teachers.asStateFlow()

    private val _classes = MutableStateFlow<List<ClassInfo>>(emptyList())
    val classes: StateFlow<List<ClassInfo>> = _classes.asStateFlow()

    private val _students = MutableStateFlow<List<StudentInfo>>(emptyList())
    val students: StateFlow<List<StudentInfo>> = _students.asStateFlow()

    private val _selectedClass = MutableStateFlow<ClassInfo?>(null)
    val selectedClass: StateFlow<ClassInfo?> = _selectedClass.asStateFlow()

    private val _filterState = MutableStateFlow(FilterState())
    val filterState: StateFlow<FilterState> = _filterState.asStateFlow()

    private val _isDbLoading = MutableStateFlow(false)
    val isDbLoading: StateFlow<Boolean> = _isDbLoading.asStateFlow()

    private val _dbError = MutableStateFlow<String?>(null)
    val dbError: StateFlow<String?> = _dbError.asStateFlow()

    private val _favoriteClassIds = MutableStateFlow<Set<Long>>(emptySet())
    val favoriteClassIds: StateFlow<Set<Long>> = _favoriteClassIds.asStateFlow()

    // 离线模式
    private val _isOfflineMode = MutableStateFlow(false)
    val isOfflineMode: StateFlow<Boolean> = _isOfflineMode.asStateFlow()

    // ========== 书本搜索相关 ==========
    private val _books = MutableStateFlow<List<BookInfo>>(emptyList())
    val books: StateFlow<List<BookInfo>> = _books.asStateFlow()

    private val _selectedBook = MutableStateFlow<BookInfo?>(null)
    val selectedBook: StateFlow<BookInfo?> = _selectedBook.asStateFlow()

    private val _bookClasses = MutableStateFlow<List<BookClassInfo>>(emptyList())
    val bookClasses: StateFlow<List<BookClassInfo>> = _bookClasses.asStateFlow()

    private val _bookStudents = MutableStateFlow<List<BookStudentRfid>>(emptyList())
    val bookStudents: StateFlow<List<BookStudentRfid>> = _bookStudents.asStateFlow()

    private val _selectedBookClass = MutableStateFlow<BookClassInfo?>(null)
    val selectedBookClass: StateFlow<BookClassInfo?> = _selectedBookClass.asStateFlow()

    private val _bookSearchKeyword = MutableStateFlow("")
    val bookSearchKeyword: StateFlow<String> = _bookSearchKeyword.asStateFlow()

    private val _selectedSubjectId = MutableStateFlow<Int?>(null)
    val selectedSubjectId: StateFlow<Int?> = _selectedSubjectId.asStateFlow()

    private val _isBookLoading = MutableStateFlow(false)
    val isBookLoading: StateFlow<Boolean> = _isBookLoading.asStateFlow()

    private val _lastUsedBook = MutableStateFlow<LastUsedBookInfo?>(null)
    val lastUsedBook: StateFlow<LastUsedBookInfo?> = _lastUsedBook.asStateFlow()

    init {
        loadCards()
        loadFavorites()
        loadLastUsedClass()
        loadRecentClasses()
        loadLastUsedBook()
        loadCachedDbData()
        checkNfcStatus()
        updateCardGroups()
    }

    // ========== NFC 状态 ==========
    fun checkNfcStatus() {
        val nfcAdapter = NfcAdapter.getDefaultAdapter(getApplication())
        _isNfcEnabled.value = nfcAdapter?.isEnabled == true
    }
    
    // 最近扫描到的卡片ID（用于UI显示）
    private val _lastScannedTagId = MutableStateFlow<String?>(null)
    val lastScannedTagId: StateFlow<String?> = _lastScannedTagId.asStateFlow()
    
    // NFC 扫描到卡片时的回调
    fun onNfcTagScanned(tagId: String) {
        // tagId 是十六进制格式（如 "9F6A1B2A"）
        println("[NFC] 扫描到卡片(HEX): $tagId")
        
        // 转换为十进制（用于匹配数据库中的十进制卡号）
        val tagIdDecimal = try {
            java.lang.Long.parseUnsignedLong(tagId, 16).toString()
        } catch (e: Exception) {
            tagId // 转换失败则保持原样
        }
        println("[NFC] 转换为十进制: $tagIdDecimal")
        
        // 显示两种格式
        _lastScannedTagId.value = "$tagIdDecimal (0x$tagId)"
        
        // 查找匹配的卡片（支持十进制和十六进制匹配）
        val matchedCard = _cards.value.find { card ->
            val cardNum = card.cardNumber.trim()
            // 匹配十进制
            cardNum == tagIdDecimal ||
            // 匹配十六进制（忽略大小写、空格、冒号）
            cardNum.uppercase().replace(" ", "").replace(":", "") == tagId.uppercase()
        }
        
        if (matchedCard != null) {
            selectCard(matchedCard)
            println("[NFC] 匹配到卡片: ${matchedCard.name}")
        } else {
            println("[NFC] 未找到匹配卡片")
            println("[NFC] 当前卡片列表: ${_cards.value.map { it.cardNumber }}")
        }
    }
    
    // 清除扫描记录
    fun clearScannedTag() {
        _lastScannedTagId.value = null
    }

    // ========== 卡片分组 ==========
    private var lastCardsHashCode = 0
    
    private fun updateCardGroups() {
        val currentCards = _cards.value
        val hashCode = currentCards.hashCode()
        // 避免重复计算：只有卡片列表变化时才重新分组
        if (hashCode == lastCardsHashCode && _cardGroups.value.isNotEmpty()) return
        lastCardsHashCode = hashCode
        
        val grouped = currentCards.groupBy { it.classId to it.className }
        _cardGroups.value = grouped.map { (key, cards) ->
            CardGroup(
                classId = key.first,
                className = key.second ?: "未分类",
                cards = cards
            )
        }.sortedBy { it.className }
    }

    fun toggleGroupExpanded(classId: Long?) {
        _cardGroups.value = _cardGroups.value.map {
            if (it.classId == classId) it.copy(isExpanded = !it.isExpanded) else it
        }
    }

    // ========== 卡片管理 ==========
    fun addCard(name: String, cardNumber: String) {
        val newCard = CardInfo(name = name, cardNumber = cardNumber.uppercase())
        _cards.value = _cards.value + newCard
        saveCards()
        updateCardGroups()
    }

    fun addCardsFromStudents(students: List<StudentInfo>, classInfo: ClassInfo?) {
        val newCards = students.mapNotNull { student ->
            if (!student.rfidNo.isNullOrBlank()) {
                CardInfo(
                    name = student.name,
                    cardNumber = student.rfidNo.uppercase(),
                    studentId = student.id,
                    classId = student.classId,
                    className = classInfo?.name ?: student.className
                )
            } else null
        }
        val existingNumbers = _cards.value.map { it.cardNumber }.toSet()
        val uniqueNewCards = newCards.filter { it.cardNumber !in existingNumbers }
        _cards.value = _cards.value + uniqueNewCards
        saveCards()
        updateCardGroups()
        
        // 更新上次使用的班级
        classInfo?.let { saveLastUsedClass(it, uniqueNewCards.size) }
    }

    fun removeCard(cardId: String) {
        _cards.value = _cards.value.filter { it.id != cardId }
        if (_currentCard.value?.id == cardId) {
            _currentCard.value = null
        }
        saveCards()
        updateCardGroups()
    }

    fun removeCardsByClass(classId: Long) {
        _cards.value = _cards.value.filter { it.classId != classId }
        saveCards()
        updateCardGroups()
    }

    fun selectCard(card: CardInfo) {
        _cards.value = _cards.value.map { it.copy(isSelected = it.id == card.id) }
        _currentCard.value = card
        NfcHceService.currentCardNumber = card.cardNumber
        saveCards()
    }

    fun toggleCardSelection(cardId: String) {
        val card = _cards.value.find { it.id == cardId } ?: return
        val newSelected = !card.isSelected
        _cards.value = _cards.value.map {
            if (it.id == cardId) it.copy(isSelected = newSelected) else it
        }
        saveCards()
    }

    fun selectAllInGroup(classId: Long?, selected: Boolean) {
        _cards.value = _cards.value.map {
            if (it.classId == classId) it.copy(isSelected = selected) else it
        }
        saveCards()
    }

    fun updateInterval(seconds: Int) {
        _batchConfig.value = _batchConfig.value.copy(intervalSeconds = seconds)
    }

    fun startBatchSimulation() {
        val selectedCards = _cards.value.filter { it.isSelected }
        if (selectedCards.isEmpty()) return

        _batchConfig.value = _batchConfig.value.copy(
            isRunning = true,
            isPaused = false,
            currentIndex = 0,
            totalCount = selectedCards.size,
            successCount = 0,
            failedCount = 0
        )
        
        batchJob = viewModelScope.launch {
            var index = 0
            while (_batchConfig.value.isRunning && index < selectedCards.size) {
                // 暂停时挂起，不轮询
                if (_batchConfig.value.isPaused) {
                    kotlinx.coroutines.suspendCancellableCoroutine<Unit> { cont ->
                        viewModelScope.launch {
                            // 等待恢复或停止
                            while (_batchConfig.value.isPaused && _batchConfig.value.isRunning) {
                                delay(200)
                            }
                            if (cont.isActive) cont.resume(Unit) {}
                        }
                    }
                }
                if (!_batchConfig.value.isRunning) break
                
                val card = selectedCards[index]
                _currentCard.value = card
                NfcHceService.currentCardNumber = card.cardNumber
                _batchConfig.value = _batchConfig.value.copy(
                    currentIndex = index + 1,
                    successCount = index + 1
                )

                // 倒计时
                for (i in _batchConfig.value.intervalSeconds downTo 1) {
                    if (!_batchConfig.value.isRunning || _batchConfig.value.isPaused) break
                    _remainingSeconds.value = i
                    delay(1000)
                }
                
                // 暂停时保持当前状态，不继续
                if (_batchConfig.value.isPaused) continue
                
                _remainingSeconds.value = 0
                index++
            }
            // 完成
            if (!_batchConfig.value.isPaused) {
                _batchConfig.value = _batchConfig.value.copy(isRunning = false, isPaused = false)
            }
        }
    }

    fun pauseBatchSimulation() {
        _batchConfig.value = _batchConfig.value.copy(isPaused = true)
    }

    fun resumeBatchSimulation() {
        _batchConfig.value = _batchConfig.value.copy(isPaused = false)
    }

    fun stopBatchSimulation() {
        batchJob?.cancel()
        _batchConfig.value = _batchConfig.value.copy(isRunning = false, isPaused = false)
        _remainingSeconds.value = 0
    }

    // ========== 快捷操作：一键开始上次班级 ==========
    fun quickStartLastClass() {
        val lastClass = _lastUsedClass.value ?: return
        // 检查该班级是否还有卡片
        val classCards = _cards.value.filter { it.classId == lastClass.classId }
        if (classCards.isEmpty()) {
            // 班级卡片已删除，清除记录
            _lastUsedClass.value = null
            dbPrefs.edit().remove("last_used_class").apply()
            println("[NFC] 上次班级卡片已删除")
            return
        }
        // 选中该班级所有卡片（不保存，临时选择）
        _cards.value = _cards.value.map {
            it.copy(isSelected = it.classId == lastClass.classId)
        }
        startBatchSimulation()
    }

    /** 快捷开始指定班级（不保存，直接开始） */
    fun quickStartClass(classId: Long) {
        // 检查该班级是否还有卡片
        val classCards = _cards.value.filter { it.classId == classId }
        if (classCards.isEmpty()) {
            // 班级卡片已删除，从最近使用中移除
            _recentClasses.value = _recentClasses.value.filter { it.classId != classId }
            saveRecentClasses()
            println("[NFC] 班级 $classId 卡片已删除，已从最近使用中移除")
            return
        }
        _cards.value = _cards.value.map {
            it.copy(isSelected = it.classId == classId)
        }
        // 不调用 saveCards()，批量模拟是临时选择
        startBatchSimulation()
    }

    /** 预缓存常用班级 */
    fun preCacheFavoriteClasses() {
        viewModelScope.launch {
            _favoriteClassIds.value.forEach { classId ->
                DatabaseRepository.getClassStudentsWithRfid(classId).onSuccess { students ->
                    cacheStudents(classId, students)
                }
            }
        }
    }

    // ========== 数据库操作 ==========
    fun loadDatabaseData() {
        viewModelScope.launch {
            _isDbLoading.value = true
            _dbError.value = null
            _isOfflineMode.value = false

            // 加载年级
            DatabaseRepository.getGrades().onSuccess { 
                _grades.value = it
                cacheGrades(it)
            }.onFailure { 
                _isOfflineMode.value = true
            }

            // 加载老师
            DatabaseRepository.getTeachers().onSuccess { 
                _teachers.value = it
                cacheTeachers(it)
            }

            // 加载班级
            loadClasses()

            _isDbLoading.value = false
        }
    }

    fun updateFilter(filter: FilterState) {
        _filterState.value = filter
        loadClasses()
    }

    private fun loadClasses() {
        viewModelScope.launch {
            _isDbLoading.value = true
            val filter = _filterState.value
            val cachedIds = getCachedClassIds()
            
            DatabaseRepository.getClasses(
                gradeId = filter.gradeId,
                teacherId = filter.teacherId,
                keyword = filter.searchKeyword
            ).onSuccess { classList ->
                // 标记已缓存的班级
                _classes.value = classList.map { it.copy(isCached = it.id in cachedIds) }
                cacheClasses(classList)
            }.onFailure { 
                _dbError.value = "加载班级失败，使用缓存数据"
                _isOfflineMode.value = true
            }
            _isDbLoading.value = false
        }
    }

    fun selectClass(classInfo: ClassInfo) {
        _selectedClass.value = classInfo
        loadClassStudents(classInfo.id)
    }

    private fun loadClassStudents(classId: Long) {
        viewModelScope.launch {
            _isDbLoading.value = true
            
            // 先尝试从缓存加载
            val cached = getCachedStudents(classId)
            if (cached != null) {
                _students.value = cached
            }
            
            // 再尝试从网络加载
            DatabaseRepository.getClassStudentsWithRfid(classId).onSuccess { 
                _students.value = it
                cacheStudents(classId, it)
            }.onFailure { 
                if (cached == null) {
                    _dbError.value = "加载学生失败: ${it.message}"
                }
            }
            _isDbLoading.value = false
        }
    }

    fun toggleFavorite(classId: Long) {
        val current = _favoriteClassIds.value.toMutableSet()
        if (classId in current) {
            current.remove(classId)
        } else {
            current.add(classId)
        }
        _favoriteClassIds.value = current
        saveFavorites()
    }

    // ========== 持久化 ==========
    private fun loadCards() {
        val json = prefs.getString("cards", null)
        if (json != null) {
            val type = object : TypeToken<List<CardInfo>>() {}.type
            _cards.value = gson.fromJson(json, type)
            _cards.value.find { it.isSelected }?.let {
                _currentCard.value = it
                NfcHceService.currentCardNumber = it.cardNumber
            }
        }
    }

    private fun saveCards() {
        prefs.edit().putString("cards", gson.toJson(_cards.value)).apply()
    }

    private fun loadFavorites() {
        val json = dbPrefs.getString("favorites", null)
        if (json != null) {
            val type = object : TypeToken<Set<Long>>() {}.type
            _favoriteClassIds.value = gson.fromJson(json, type)
        }
    }

    private fun saveFavorites() {
        dbPrefs.edit().putString("favorites", gson.toJson(_favoriteClassIds.value)).apply()
    }

    private fun loadLastUsedClass() {
        val json = dbPrefs.getString("last_used_class", null)
        if (json != null) {
            _lastUsedClass.value = gson.fromJson(json, LastUsedInfo::class.java)
        }
    }

    private fun saveLastUsedClass(classInfo: ClassInfo, count: Int) {
        val info = LastUsedInfo(
            classId = classInfo.id,
            className = classInfo.name,
            studentCount = count
        )
        _lastUsedClass.value = info
        dbPrefs.edit().putString("last_used_class", gson.toJson(info)).apply()
        
        // 同时更新最近使用历史
        addToRecentClasses(classInfo, count)
    }

    /** 添加到最近使用班级历史 */
    private fun addToRecentClasses(classInfo: ClassInfo, rfidCount: Int) {
        val current = _recentClasses.value.toMutableList()
        // 移除已存在的同班级记录
        current.removeAll { it.classId == classInfo.id }
        // 添加到头部
        current.add(0, RecentClassInfo(
            classId = classInfo.id,
            className = classInfo.name,
            gradeName = classInfo.gradeName,
            studentCount = classInfo.studentCount,
            rfidCount = rfidCount
        ))
        // 只保留最近5个
        _recentClasses.value = current.take(5)
        saveRecentClasses()
    }

    private fun loadRecentClasses() {
        val json = dbPrefs.getString("recent_classes", null)
        if (json != null) {
            val type = object : TypeToken<List<RecentClassInfo>>() {}.type
            _recentClasses.value = gson.fromJson(json, type)
        }
    }

    private fun saveRecentClasses() {
        dbPrefs.edit().putString("recent_classes", gson.toJson(_recentClasses.value)).apply()
    }

    /** 检查班级是否已缓存 */
    fun isClassCached(classId: Long): Boolean {
        return dbPrefs.getString("cached_students_$classId", null) != null
    }

    /** 获取所有已缓存的班级ID */
    fun getCachedClassIds(): Set<Long> {
        val allKeys = dbPrefs.all.keys
        return allKeys.filter { it.startsWith("cached_students_") }
            .mapNotNull { it.removePrefix("cached_students_").toLongOrNull() }
            .toSet()
    }

    private fun loadCachedDbData() {
        dbPrefs.getString("cached_grades", null)?.let { json ->
            val type = object : TypeToken<List<GradeInfo>>() {}.type
            _grades.value = gson.fromJson(json, type)
        }
        dbPrefs.getString("cached_teachers", null)?.let { json ->
            val type = object : TypeToken<List<TeacherInfo>>() {}.type
            _teachers.value = gson.fromJson(json, type)
        }
        dbPrefs.getString("cached_classes", null)?.let { json ->
            val type = object : TypeToken<List<ClassInfo>>() {}.type
            _classes.value = gson.fromJson(json, type)
        }
    }

    private fun cacheGrades(grades: List<GradeInfo>) {
        dbPrefs.edit().putString("cached_grades", gson.toJson(grades)).apply()
    }

    private fun cacheTeachers(teachers: List<TeacherInfo>) {
        dbPrefs.edit().putString("cached_teachers", gson.toJson(teachers)).apply()
    }

    private fun cacheClasses(classes: List<ClassInfo>) {
        dbPrefs.edit().putString("cached_classes", gson.toJson(classes)).apply()
    }

    private fun cacheStudents(classId: Long, students: List<StudentInfo>) {
        dbPrefs.edit().putString("cached_students_$classId", gson.toJson(students)).apply()
    }

    private fun getCachedStudents(classId: Long): List<StudentInfo>? {
        val json = dbPrefs.getString("cached_students_$classId", null) ?: return null
        val type = object : TypeToken<List<StudentInfo>>() {}.type
        return gson.fromJson(json, type)
    }

    // ========== 书本搜索功能 ==========
    
    fun searchBooks(keyword: String = "", subjectId: Int? = null) {
        _bookSearchKeyword.value = keyword
        _selectedSubjectId.value = subjectId
        
        viewModelScope.launch {
            _isBookLoading.value = true
            DatabaseRepository.searchBooks(keyword, subjectId).onSuccess {
                _books.value = it
            }.onFailure {
                _books.value = emptyList()
            }
            _isBookLoading.value = false
        }
    }

    fun selectBook(book: BookInfo) {
        _selectedBook.value = book
        _bookClasses.value = emptyList()
        _selectedBookClass.value = null
        _bookStudents.value = emptyList()
        
        viewModelScope.launch {
            _isBookLoading.value = true
            DatabaseRepository.getBookClasses(book.id).onSuccess {
                _bookClasses.value = it
            }
            _isBookLoading.value = false
        }
    }

    fun selectBookClass(bookClass: BookClassInfo) {
        val book = _selectedBook.value ?: return
        _selectedBookClass.value = bookClass
        _bookStudents.value = emptyList()
        
        viewModelScope.launch {
            _isBookLoading.value = true
            DatabaseRepository.getBookClassStudents(book.id, bookClass.id).onSuccess {
                _bookStudents.value = it
            }
            _isBookLoading.value = false
        }
    }

    /** 添加书本RFID卡片并开始批量模拟 */
    fun addBookCardsAndStart(students: List<BookStudentRfid>) {
        val book = _selectedBook.value ?: return
        val bookClass = _selectedBookClass.value ?: return
        
        // 转换为CardInfo
        val newCards = students.map { student ->
            CardInfo(
                name = "${student.name} - ${book.bookName}",
                cardNumber = student.rfidNo.uppercase(),
                studentId = student.id.toLongOrNull(),
                classId = bookClass.id.toLongOrNull(),
                className = "${bookClass.name} - ${book.bookName}"
            )
        }
        
        // 清除旧的同书本班级卡片，添加新卡片
        val className = "${bookClass.name} - ${book.bookName}"
        _cards.value = _cards.value.filter { it.className != className } + newCards
        
        // 选中所有新卡片
        _cards.value = _cards.value.map {
            it.copy(isSelected = it.className == className)
        }
        
        saveCards()
        updateCardGroups()
        
        // 保存上次使用的书本
        saveLastUsedBook(book, bookClass, students.size)
        
        // 开始批量模拟
        startBatchSimulation()
    }

    /** 快捷开始上次使用的书本 */
    fun quickStartLastBook() {
        val lastBook = _lastUsedBook.value ?: return
        val className = "${lastBook.className} - ${lastBook.bookName}"
        
        // 选中该书本班级的所有卡片
        _cards.value = _cards.value.map {
            it.copy(isSelected = it.className == className)
        }
        saveCards()
        
        // 开始批量模拟
        startBatchSimulation()
    }

    private fun loadLastUsedBook() {
        val json = dbPrefs.getString("last_used_book", null)
        if (json != null) {
            _lastUsedBook.value = gson.fromJson(json, LastUsedBookInfo::class.java)
        }
    }

    private fun saveLastUsedBook(book: BookInfo, bookClass: BookClassInfo, count: Int) {
        val info = LastUsedBookInfo(
            bookId = book.id,
            bookName = book.bookName,
            classId = bookClass.id,
            className = bookClass.name,
            studentCount = count
        )
        _lastUsedBook.value = info
        dbPrefs.edit().putString("last_used_book", gson.toJson(info)).apply()
    }

    fun clearBookSelection() {
        _selectedBook.value = null
        _bookClasses.value = emptyList()
        _selectedBookClass.value = null
        _bookStudents.value = emptyList()
    }
}
