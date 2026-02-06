package com.example.nfc.ui.screens

import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.example.nfc.data.*
import com.example.nfc.ui.theme.*

/**
 * RFID 模拟器主界面
 * 遵循 ui-style.md 规范：简约高级、灰度为主、有质感
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RfidSimulatorScreen(
    connectionStatus: AdbClientStatus,
    taskStatus: SimulationTaskStatus,
    batchConfig: RfidBatchConfig,
    logs: List<RfidLogEntry>,
    remainingSeconds: Int,
    isLoading: Boolean,
    errorMessage: String?,
    grades: List<GradeInfo> = emptyList(),
    classes: List<ClassInfo> = emptyList(),
    students: List<StudentInfo> = emptyList(),
    selectedGrade: Int? = null,
    selectedClass: ClassInfo? = null,
    books: List<BookInfo> = emptyList(),
    bookClasses: List<BookClassInfo> = emptyList(),
    bookStudents: List<BookStudentRfid> = emptyList(),
    selectedBook: BookInfo? = null,
    selectedBookClass: BookClassInfo? = null,
    searchKeyword: String = "",
    selectedStudentIds: Set<String> = emptySet(),
    onRefreshConnection: () -> Unit,
    onTestConnection: () -> Unit,
    onUpdateInterval: (Int) -> Unit,
    onStartBatch: () -> Unit,
    onPauseBatch: () -> Unit,
    onResumeBatch: () -> Unit,
    onStopBatch: () -> Unit,
    onClearLogs: () -> Unit,
    onClearError: () -> Unit,
    onSelectGrade: (Int?) -> Unit,
    onSelectClass: (ClassInfo) -> Unit,
    onSearchBooks: (String) -> Unit,
    onSelectBook: (BookInfo) -> Unit,
    onSelectBookClass: (BookClassInfo) -> Unit,
    onToggleStudent: (String) -> Unit,
    onSelectAllStudents: (Boolean) -> Unit,
    onLoadClasses: () -> Unit,
    onLoadBooks: () -> Unit,
    onNavigateBack: (() -> Unit)? = null
) {
    var currentTab by remember { mutableStateOf(0) }
    val isRunning = taskStatus.status == "running"
    val isPaused = taskStatus.status == "paused"
    
    val validStudentCount = if (currentTab == 0) {
        students.count { it.rfidNo?.isNotBlank() == true }
    } else {
        bookStudents.count { it.rfidNo.isNotBlank() }
    }
    val selectedCount = selectedStudentIds.size
    val hasValidStudents = validStudentCount > 0

    Scaffold(
        containerColor = AppleGray50,
        topBar = {
            // 顶部标题栏 - 有质感的设计
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = AppleWhite,
                shadowElevation = 1.dp
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 20.dp)
                        .padding(top = 16.dp, bottom = 12.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            // 返回按钮
                            onNavigateBack?.let { onBack ->
                                IconButton(
                                    onClick = onBack,
                                    modifier = Modifier.size(32.dp)
                                ) {
                                    Icon(
                                        Icons.Default.ArrowBack,
                                        contentDescription = "返回",
                                        tint = AppleGray500,
                                        modifier = Modifier.size(20.dp)
                                    )
                                }
                                Spacer(modifier = Modifier.width(8.dp))
                            }
                            Text(
                                text = "手动模式",
                                style = MaterialTheme.typography.headlineLarge,
                                fontWeight = FontWeight.Bold,
                                color = AppleBlack
                            )
                        }
                    }
                    Spacer(modifier = Modifier.height(4.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .clip(CircleShape)
                                .background(if (connectionStatus.connected) AppleGreen else AppleRed)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = if (connectionStatus.connected) 
                                "已连接 · ${connectionStatus.deviceInfo?.model ?: connectionStatus.ipAddress ?: ""}"
                            else "未连接 ADB 客户端",
                            style = MaterialTheme.typography.bodyMedium,
                            color = AppleGray500
                        )
                        Spacer(modifier = Modifier.weight(1f))
                        IconButton(
                            onClick = onRefreshConnection,
                            modifier = Modifier.size(32.dp)
                        ) {
                            Icon(
                                Icons.Default.Refresh,
                                contentDescription = "刷新",
                                tint = AppleGray500,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                    }
                }
            }
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(bottom = 32.dp)
        ) {
            // 运行中状态卡片
            if (isRunning || isPaused) {
                item(key = "running_status") {
                    RunningStatusCard(
                        taskStatus = taskStatus,
                        remainingSeconds = remainingSeconds,
                        isPaused = isPaused,
                        onPause = onPauseBatch,
                        onResume = onResumeBatch,
                        onStop = onStopBatch
                    )
                }
            }

            // Tab 切换
            item(key = "tab_row") {
                SourceTabRow(currentTab = currentTab, onTabChange = { 
                    currentTab = it
                    if (it == 0) onLoadClasses() else onLoadBooks()
                })
            }

            // 数据源选择
            if (currentTab == 0) {
                item(key = "grade_filter") {
                    GradeFilterRow(grades, selectedGrade, onSelectGrade)
                }
                item(key = "class_selector") {
                    ClassSelector(
                        classes = classes.filter { selectedGrade == null || it.grade == selectedGrade },
                        selectedClass = selectedClass,
                        onSelectClass = onSelectClass,
                        isLoading = isLoading
                    )
                }
                if (students.isNotEmpty()) {
                    item(key = "class_student_header") {
                        StudentListHeader(validStudentCount, selectedCount, onSelectAllStudents)
                    }
                    val filteredStudents = students
                        .filter { it.rfidNo?.isNotBlank() == true }
                        .distinctBy { it.id }
                    items(count = filteredStudents.size, key = { "cs_${filteredStudents[it].id}" }) { index ->
                        val student = filteredStudents[index]
                        ClassStudentItem(
                            student = student,
                            isSelected = selectedStudentIds.contains(student.id.toString()),
                            onToggle = { onToggleStudent(student.id.toString()) }
                        )
                    }
                }
            } else {
                item(key = "book_search") {
                    BookSearchBar(searchKeyword, onSearchBooks)
                }
                item(key = "book_selector") {
                    BookSelector(books, selectedBook, onSelectBook, isLoading)
                }
                if (selectedBook != null && bookClasses.isNotEmpty()) {
                    item(key = "book_class_selector") {
                        BookClassSelector(bookClasses, selectedBookClass, onSelectBookClass)
                    }
                }
                if (bookStudents.isNotEmpty()) {
                    item(key = "book_student_header") {
                        StudentListHeader(validStudentCount, selectedCount, onSelectAllStudents)
                    }
                    val filteredBookStudents = bookStudents
                        .filter { it.rfidNo.isNotBlank() }
                        .distinctBy { it.id }
                    items(count = filteredBookStudents.size, key = { "bs_${filteredBookStudents[it].id}" }) { index ->
                        val student = filteredBookStudents[index]
                        BookStudentItem(
                            student = student,
                            isSelected = selectedStudentIds.contains(student.id),
                            onToggle = { onToggleStudent(student.id) }
                        )
                    }
                }
            }

            // 批量控制
            if (!isRunning && !isPaused) {
                item(key = "batch_control") {
                    BatchControlSection(
                        batchConfig = batchConfig,
                        selectedCount = selectedCount,
                        isConnected = connectionStatus.connected,
                        hasValidStudents = hasValidStudents,
                        onUpdateInterval = onUpdateInterval,
                        onStart = onStartBatch
                    )
                }
            }

            // 执行日志
            item(key = "log_section") {
                LogSection(logs, onClearLogs)
            }
        }
    }

    // 错误提示
    errorMessage?.let { msg ->
        Snackbar(
            modifier = Modifier.padding(16.dp),
            action = { TextButton(onClick = onClearError) { Text("关闭", color = AppleWhite) } },
            containerColor = AppleRed
        ) { Text(msg, color = AppleWhite) }
    }
}


// ==================== 运行中状态卡片 ====================

@Composable
private fun RunningStatusCard(
    taskStatus: SimulationTaskStatus,
    remainingSeconds: Int,
    isPaused: Boolean,
    onPause: () -> Unit,
    onResume: () -> Unit,
    onStop: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(Spacing.md)
            .shadow(8.dp, RoundedCornerShape(Radius.xl)),
        shape = RoundedCornerShape(Radius.xl),
        colors = CardDefaults.cardColors(containerColor = AppleBlack)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            // 标题行
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .clip(CircleShape)
                                .background(if (isPaused) AppleOrange else AppleGreen)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = if (isPaused) "已暂停" else "正在发送",
                            style = MaterialTheme.typography.bodySmall,
                            color = if (isPaused) AppleOrange else AppleGray400
                        )
                    }
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "RFID 模拟",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold,
                        color = AppleWhite
                    )
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        text = "${taskStatus.currentIndex} / ${taskStatus.totalCount}",
                        style = MaterialTheme.typography.headlineMedium,
                        fontWeight = FontWeight.Bold,
                        color = AppleWhite
                    )
                    Text(
                        text = if (isPaused) "暂停中" else "${remainingSeconds}s",
                        style = MaterialTheme.typography.bodyMedium,
                        color = if (isPaused) AppleOrange else AppleGray400
                    )
                }
            }
            
            Spacer(modifier = Modifier.height(20.dp))
            
            // 进度条
            LinearProgressIndicator(
                progress = { 
                    if (taskStatus.totalCount > 0) taskStatus.currentIndex.toFloat() / taskStatus.totalCount else 0f 
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(4.dp)
                    .clip(RoundedCornerShape(2.dp)),
                color = if (isPaused) AppleOrange else AppleWhite,
                trackColor = AppleWhite.copy(alpha = 0.15f)
            )
            
            Spacer(modifier = Modifier.height(20.dp))
            
            // 统计
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                StatItem("成功", taskStatus.successCount.toString(), AppleGreen)
                StatItem("失败", taskStatus.failedCount.toString(), AppleRed)
            }
            
            Spacer(modifier = Modifier.height(20.dp))
            
            // 控制按钮
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedButton(
                    onClick = if (isPaused) onResume else onPause,
                    modifier = Modifier.weight(1f).height(48.dp),
                    shape = RoundedCornerShape(Radius.lg),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = AppleWhite),
                    border = ButtonDefaults.outlinedButtonBorder.copy(
                        brush = androidx.compose.ui.graphics.SolidColor(AppleWhite.copy(alpha = 0.3f))
                    )
                ) {
                    Icon(
                        if (isPaused) Icons.Default.PlayArrow else Icons.Default.Pause,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(if (isPaused) "继续" else "暂停", fontWeight = FontWeight.Medium)
                }
                Button(
                    onClick = onStop,
                    modifier = Modifier.weight(1f).height(48.dp),
                    shape = RoundedCornerShape(Radius.lg),
                    colors = ButtonDefaults.buttonColors(containerColor = AppleWhite, contentColor = AppleBlack)
                ) {
                    Text("停止", fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
}

@Composable
private fun StatItem(label: String, value: String, color: androidx.compose.ui.graphics.Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = value,
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold,
            color = color
        )
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = AppleWhite.copy(alpha = 0.6f)
        )
    }
}


// ==================== Tab 切换 ====================

@Composable
private fun SourceTabRow(currentTab: Int, onTabChange: (Int) -> Unit) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = Spacing.md, vertical = Spacing.sm),
        shape = RoundedCornerShape(Radius.lg),
        color = AppleWhite
    ) {
        Row(
            modifier = Modifier.padding(4.dp),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            listOf("按班级", "按书本").forEachIndexed { index, title ->
                val isSelected = currentTab == index
                Surface(
                    modifier = Modifier
                        .weight(1f)
                        .clickable { onTabChange(index) },
                    shape = RoundedCornerShape(Radius.md),
                    color = if (isSelected) AppleBlack else AppleWhite
                ) {
                    Text(
                        text = title,
                        modifier = Modifier.padding(vertical = 12.dp),
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Normal,
                        color = if (isSelected) AppleWhite else AppleGray500,
                        textAlign = TextAlign.Center
                    )
                }
            }
        }
    }
}

// ==================== 年级筛选 ====================

@Composable
private fun GradeFilterRow(grades: List<GradeInfo>, selectedGrade: Int?, onSelectGrade: (Int?) -> Unit) {
    LazyRow(
        modifier = Modifier.fillMaxWidth().padding(vertical = Spacing.sm),
        contentPadding = PaddingValues(horizontal = Spacing.md),
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm)
    ) {
        item {
            FilterChip(
                selected = selectedGrade == null,
                onClick = { onSelectGrade(null) },
                label = { Text("全部") },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = AppleBlack,
                    selectedLabelColor = AppleWhite,
                    containerColor = AppleWhite
                )
            )
        }
        items(grades) { grade ->
            FilterChip(
                selected = selectedGrade == grade.id,
                onClick = { onSelectGrade(grade.id) },
                label = { Text(grade.name) },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = AppleBlack,
                    selectedLabelColor = AppleWhite,
                    containerColor = AppleWhite
                )
            )
        }
    }
}

// ==================== 班级选择器 ====================

@Composable
private fun ClassSelector(
    classes: List<ClassInfo>,
    selectedClass: ClassInfo?,
    onSelectClass: (ClassInfo) -> Unit,
    isLoading: Boolean
) {
    Column(modifier = Modifier.fillMaxWidth().padding(horizontal = Spacing.md, vertical = Spacing.sm)) {
        Text(
            text = "选择班级",
            style = MaterialTheme.typography.titleSmall,
            fontWeight = FontWeight.SemiBold,
            color = AppleGray500,
            modifier = Modifier.padding(bottom = Spacing.sm)
        )
        
        if (isLoading) {
            Box(modifier = Modifier.fillMaxWidth().height(80.dp), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(modifier = Modifier.size(24.dp), color = AppleBlack, strokeWidth = 2.dp)
            }
        } else if (classes.isEmpty()) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(Radius.lg),
                colors = CardDefaults.cardColors(containerColor = AppleWhite)
            ) {
                Text(
                    text = "暂无班级数据",
                    modifier = Modifier.fillMaxWidth().padding(Spacing.lg),
                    style = MaterialTheme.typography.bodyMedium,
                    color = AppleGray400,
                    textAlign = TextAlign.Center
                )
            }
        } else {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                items(classes, key = { it.id }) { cls ->
                    val isSelected = selectedClass?.id == cls.id
                    Card(
                        modifier = Modifier
                            .width(140.dp)
                            .clickable { onSelectClass(cls) },
                        shape = RoundedCornerShape(Radius.lg),
                        colors = CardDefaults.cardColors(
                            containerColor = if (isSelected) AppleBlack else AppleWhite
                        )
                    ) {
                        Column(modifier = Modifier.padding(Spacing.md)) {
                            Text(
                                text = cls.name,
                                style = MaterialTheme.typography.bodyLarge,
                                fontWeight = FontWeight.Medium,
                                color = if (isSelected) AppleWhite else AppleBlack,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = "${cls.studentCount} 人",
                                style = MaterialTheme.typography.bodySmall,
                                color = if (isSelected) AppleGray400 else AppleGray500
                            )
                        }
                    }
                }
            }
        }
    }
}


// ==================== 书本搜索 ====================

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun BookSearchBar(keyword: String, onSearch: (String) -> Unit) {
    var text by remember { mutableStateOf(keyword) }
    
    OutlinedTextField(
        value = text,
        onValueChange = { text = it; onSearch(it) },
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = Spacing.md, vertical = Spacing.sm),
        placeholder = { Text("搜索书本名称...", color = AppleGray400) },
        leadingIcon = { Icon(Icons.Default.Search, contentDescription = null, tint = AppleGray400) },
        trailingIcon = {
            if (text.isNotEmpty()) {
                IconButton(onClick = { text = ""; onSearch("") }) {
                    Icon(Icons.Default.Clear, contentDescription = "清除", tint = AppleGray400)
                }
            }
        },
        shape = RoundedCornerShape(Radius.lg),
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = AppleBlack,
            unfocusedBorderColor = AppleGray200,
            focusedContainerColor = AppleWhite,
            unfocusedContainerColor = AppleWhite
        ),
        singleLine = true
    )
}

// ==================== 书本选择器 ====================

@Composable
private fun BookSelector(
    books: List<BookInfo>,
    selectedBook: BookInfo?,
    onSelectBook: (BookInfo) -> Unit,
    isLoading: Boolean
) {
    Column(modifier = Modifier.fillMaxWidth().padding(horizontal = Spacing.md, vertical = Spacing.sm)) {
        if (isLoading) {
            Box(modifier = Modifier.fillMaxWidth().height(80.dp), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(modifier = Modifier.size(24.dp), color = AppleBlack, strokeWidth = 2.dp)
            }
        } else if (books.isEmpty()) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(Radius.lg),
                colors = CardDefaults.cardColors(containerColor = AppleWhite)
            ) {
                Text(
                    text = "输入关键词搜索书本",
                    modifier = Modifier.fillMaxWidth().padding(Spacing.lg),
                    style = MaterialTheme.typography.bodyMedium,
                    color = AppleGray400,
                    textAlign = TextAlign.Center
                )
            }
        } else {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                items(books, key = { it.id }) { book ->
                    val isSelected = selectedBook?.id == book.id
                    Card(
                        modifier = Modifier
                            .width(160.dp)
                            .clickable { onSelectBook(book) },
                        shape = RoundedCornerShape(Radius.lg),
                        colors = CardDefaults.cardColors(
                            containerColor = if (isSelected) AppleBlack else AppleWhite
                        )
                    ) {
                        Column(modifier = Modifier.padding(Spacing.md)) {
                            Text(
                                text = book.bookName,
                                style = MaterialTheme.typography.bodyLarge,
                                fontWeight = FontWeight.Medium,
                                color = if (isSelected) AppleWhite else AppleBlack,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Row {
                                book.subjectName?.let {
                                    Text(
                                        text = it,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = if (isSelected) AppleGray400 else AppleGray500
                                    )
                                }
                                book.gradeName?.let {
                                    Text(
                                        text = " · $it",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = if (isSelected) AppleGray400 else AppleGray500
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

// ==================== 书本关联班级选择 ====================

@Composable
private fun BookClassSelector(
    classes: List<BookClassInfo>,
    selectedClass: BookClassInfo?,
    onSelectClass: (BookClassInfo) -> Unit
) {
    Column(modifier = Modifier.fillMaxWidth().padding(horizontal = Spacing.md, vertical = Spacing.sm)) {
        Text(
            text = "选择班级",
            style = MaterialTheme.typography.titleSmall,
            fontWeight = FontWeight.SemiBold,
            color = AppleGray500,
            modifier = Modifier.padding(bottom = Spacing.sm)
        )
        LazyRow(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            items(classes, key = { it.id }) { cls ->
                val isSelected = selectedClass?.id == cls.id
                FilterChip(
                    selected = isSelected,
                    onClick = { onSelectClass(cls) },
                    label = { Text(cls.name) },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = AppleBlack,
                        selectedLabelColor = AppleWhite,
                        containerColor = AppleWhite
                    )
                )
            }
        }
    }
}


// ==================== 学生列表头部 ====================

@Composable
private fun StudentListHeader(totalCount: Int, selectedCount: Int, onSelectAll: (Boolean) -> Unit) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = Spacing.md, vertical = Spacing.sm),
        shape = RoundedCornerShape(Radius.lg),
        color = AppleWhite
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(Spacing.md),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "学生列表",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = AppleBlack
                )
                Text(
                    text = "共 $totalCount 人，已选 $selectedCount 人",
                    style = MaterialTheme.typography.bodySmall,
                    color = AppleGray500
                )
            }
            TextButton(onClick = { onSelectAll(selectedCount < totalCount) }) {
                Text(
                    text = if (selectedCount < totalCount) "全选" else "取消全选",
                    color = AppleBlack,
                    fontWeight = FontWeight.Medium
                )
            }
        }
    }
}

// ==================== 班级学生项 ====================

@Composable
private fun ClassStudentItem(student: StudentInfo, isSelected: Boolean, onToggle: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = Spacing.md, vertical = 3.dp)
            .clickable { onToggle() },
        shape = RoundedCornerShape(Radius.lg),
        colors = CardDefaults.cardColors(
            containerColor = if (isSelected) AppleGray100 else AppleWhite
        )
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(Spacing.md),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Checkbox(
                checked = isSelected,
                onCheckedChange = { onToggle() },
                colors = CheckboxDefaults.colors(
                    checkedColor = AppleBlack,
                    uncheckedColor = AppleGray400
                )
            )
            Spacer(modifier = Modifier.width(Spacing.sm))
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = student.name,
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.Medium,
                        color = AppleBlack
                    )
                    if (student.isRepresentative) {
                        Spacer(modifier = Modifier.width(6.dp))
                        Surface(
                            shape = RoundedCornerShape(Radius.xs),
                            color = AppleGray100
                        ) {
                            Text(
                                text = "课代表",
                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                                style = MaterialTheme.typography.labelSmall,
                                color = AppleGray600,
                                fontWeight = FontWeight.Medium
                            )
                        }
                    }
                }
                Text(
                    text = student.rfidNo ?: "",
                    style = MaterialTheme.typography.bodySmall,
                    color = AppleGray500,
                    fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace
                )
            }
        }
    }
}

// ==================== 书本学生项 ====================

@Composable
private fun BookStudentItem(student: BookStudentRfid, isSelected: Boolean, onToggle: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = Spacing.md, vertical = 3.dp)
            .clickable { onToggle() },
        shape = RoundedCornerShape(Radius.lg),
        colors = CardDefaults.cardColors(
            containerColor = if (isSelected) AppleGray100 else AppleWhite
        )
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(Spacing.md),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Checkbox(
                checked = isSelected,
                onCheckedChange = { onToggle() },
                colors = CheckboxDefaults.colors(
                    checkedColor = AppleBlack,
                    uncheckedColor = AppleGray400
                )
            )
            Spacer(modifier = Modifier.width(Spacing.sm))
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = student.name,
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.Medium,
                        color = AppleBlack
                    )
                    if (student.isRepresentative) {
                        Spacer(modifier = Modifier.width(6.dp))
                        Surface(
                            shape = RoundedCornerShape(Radius.xs),
                            color = AppleGray100
                        ) {
                            Text(
                                text = "课代表",
                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                                style = MaterialTheme.typography.labelSmall,
                                color = AppleGray600,
                                fontWeight = FontWeight.Medium
                            )
                        }
                    }
                }
                Text(
                    text = student.rfidNo,
                    style = MaterialTheme.typography.bodySmall,
                    color = AppleGray500,
                    fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace
                )
            }
        }
    }
}


// ==================== 批量控制区域 ====================

@Composable
private fun BatchControlSection(
    batchConfig: RfidBatchConfig,
    selectedCount: Int,
    isConnected: Boolean,
    hasValidStudents: Boolean,
    onUpdateInterval: (Int) -> Unit,
    onStart: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(Spacing.md),
        shape = RoundedCornerShape(Radius.xl),
        colors = CardDefaults.cardColors(containerColor = AppleWhite)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            // 间隔设置
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "发送间隔",
                    style = MaterialTheme.typography.bodyMedium,
                    color = AppleGray500
                )
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    listOf(3, 5, 10, 15).forEach { sec ->
                        val isSelected = batchConfig.intervalSeconds == sec
                        Surface(
                            modifier = Modifier.clickable { onUpdateInterval(sec) },
                            shape = RoundedCornerShape(Radius.md),
                            color = if (isSelected) AppleBlack else AppleGray100
                        ) {
                            Text(
                                text = "${sec}s",
                                modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Normal,
                                color = if (isSelected) AppleWhite else AppleGray500
                            )
                        }
                    }
                }
            }
            
            Spacer(modifier = Modifier.height(20.dp))
            
            // 开始按钮
            Button(
                onClick = onStart,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                enabled = selectedCount > 0 && isConnected && hasValidStudents,
                shape = RoundedCornerShape(Radius.lg),
                colors = ButtonDefaults.buttonColors(
                    containerColor = AppleBlack,
                    contentColor = AppleWhite,
                    disabledContainerColor = AppleGray200,
                    disabledContentColor = AppleGray400
                )
            ) {
                Icon(Icons.Default.PlayArrow, contentDescription = null, modifier = Modifier.size(20.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = if (selectedCount > 0) "开始模拟 ($selectedCount)" else "开始模拟",
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.SemiBold
                )
            }
            
            // 提示信息
            if (!isConnected) {
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = "请先连接 ADB 客户端",
                    style = MaterialTheme.typography.bodySmall,
                    color = AppleRed,
                    modifier = Modifier.fillMaxWidth(),
                    textAlign = TextAlign.Center
                )
            } else if (selectedCount == 0 && hasValidStudents) {
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = "请选择要模拟的学生",
                    style = MaterialTheme.typography.bodySmall,
                    color = AppleGray400,
                    modifier = Modifier.fillMaxWidth(),
                    textAlign = TextAlign.Center
                )
            }
        }
    }
}

// ==================== 日志区域 ====================

@Composable
private fun LogSection(logs: List<RfidLogEntry>, onClear: () -> Unit) {
    Column(modifier = Modifier.fillMaxWidth().padding(Spacing.md)) {
        // 标题行
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "执行日志",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
                color = AppleBlack
            )
            TextButton(
                onClick = onClear,
                enabled = logs.isNotEmpty()
            ) {
                Text(
                    text = "清空",
                    color = if (logs.isNotEmpty()) AppleBlack else AppleGray400,
                    fontWeight = FontWeight.Medium
                )
            }
        }
        
        Spacer(modifier = Modifier.height(Spacing.sm))
        
        // 日志卡片
        Card(
            shape = RoundedCornerShape(Radius.lg),
            colors = CardDefaults.cardColors(containerColor = AppleWhite)
        ) {
            if (logs.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(100.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "暂无日志",
                        style = MaterialTheme.typography.bodyMedium,
                        color = AppleGray400
                    )
                }
            } else {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(max = 250.dp)
                        .padding(Spacing.md),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    logs.take(15).forEach { log -> LogItem(log) }
                }
            }
        }
    }
}

@Composable
private fun LogItem(log: RfidLogEntry) {
    val levelColor = when (log.level) {
        "success" -> AppleGreen
        "error" -> AppleRed
        "warning" -> AppleOrange
        else -> AppleGray500
    }
    
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.Top
    ) {
        Text(
            text = log.time,
            style = MaterialTheme.typography.bodySmall,
            color = AppleGray400,
            fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace,
            modifier = Modifier.width(56.dp)
        )
        Spacer(modifier = Modifier.width(Spacing.sm))
        Box(
            modifier = Modifier
                .padding(top = 5.dp)
                .size(6.dp)
                .clip(CircleShape)
                .background(levelColor)
        )
        Spacer(modifier = Modifier.width(Spacing.sm))
        Text(
            text = log.message,
            style = MaterialTheme.typography.bodySmall,
            color = AppleBlack,
            modifier = Modifier.weight(1f)
        )
    }
}