package com.example.nfc.ui.screens

import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.FavoriteBorder
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.example.nfc.data.*
import com.example.nfc.ui.theme.*

/**
 * 自动化流程主界面
 * 设计理念：极简操作，选书本+页码即可一键完成全流程
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AutomationScreen(
    // 连接状态
    connectionStatus: AdbClientStatus,
    automationStatus: AutomationStatus,
    config: AutomationConfig,
    logs: List<RfidLogEntry>,
    isLoading: Boolean,
    errorMessage: String?,
    // 书本数据
    books: List<BookInfo>,
    selectedBook: BookInfo?,
    bookClasses: List<BookClassInfo>,
    selectedBookClass: BookClassInfo?,
    bookStudents: List<BookStudentRfid>,
    searchKeyword: String,
    // 新增：最近使用、收藏、筛选
    recentUsages: List<RecentUsage>,
    favoriteBooks: List<FavoriteBook>,
    selectedSubjectId: Int,
    selectedGradeId: Int,
    // 智能发布：老师
    smartTeachers: List<SmartPublishTeacher>,
    selectedSmartTeacher: SmartPublishTeacher?,
    needSelectTeacher: Boolean,
    // 回调
    onSearchBooks: (String) -> Unit,
    onSelectBook: (BookInfo) -> Unit,
    onSelectBookClass: (BookClassInfo) -> Unit,
    onUpdatePageNumber: (Int) -> Unit,
    onUpdatePhotoInterval: (Int) -> Unit,
    onToggleDoublePageMode: () -> Unit,
    onStartAutomation: () -> Unit,
    onStopAutomation: () -> Unit,
    onClearLogs: () -> Unit,
    onClearError: () -> Unit,
    onRefreshLogs: () -> Unit,
    onNavigateToManual: () -> Unit,
    // 新增回调
    onQuickStartFromRecent: (RecentUsage) -> Unit,
    onToggleFavorite: (BookInfo) -> Unit,
    onSelectSubject: (Int) -> Unit,
    onSelectGrade: (Int) -> Unit,
    isFavorite: (String) -> Boolean,
    // 智能发布回调
    onSelectSmartTeacher: (SmartPublishTeacher) -> Unit
) {
    // 老师选择弹窗状态
    var showTeacherDialog by remember { mutableStateOf(false) }
    
    val isRunning = automationStatus.phase != AutomationPhase.IDLE && 
                    automationStatus.phase != AutomationPhase.COMPLETED &&
                    automationStatus.phase != AutomationPhase.ERROR
    val canStart = selectedBook != null && bookStudents.isNotEmpty() && 
                   connectionStatus.connected && selectedSmartTeacher != null

    Scaffold(
        containerColor = AppleGray50,
        topBar = {
            // 顶部留白 + 状态栏
            Spacer(modifier = Modifier.height(24.dp))
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(bottom = 32.dp)
        ) {
            // 顶部标题区域（下移优化）
            item(key = "header") {
                HeaderSection(
                    connectionStatus = connectionStatus,
                    onNavigateToManual = onNavigateToManual
                )
            }

            // 最近使用卡片（最多3个）
            if (recentUsages.isNotEmpty() && !isRunning) {
                item(key = "recent_usages") {
                    RecentUsageSection(
                        usages = recentUsages,
                        onQuickStart = onQuickStartFromRecent
                    )
                }
            }

            // 运行中状态卡片
            if (isRunning) {
                item(key = "running_status") {
                    AutomationRunningCard(
                        status = automationStatus,
                        onStop = onStopAutomation
                    )
                }
            }

            // 步骤1: 选择书本（含筛选）
            item(key = "step_book") {
                StepCard(
                    stepNumber = 1,
                    title = "选择书本",
                    isCompleted = selectedBook != null,
                    isEnabled = !isRunning
                ) {
                    BookSearchSection(
                        keyword = searchKeyword,
                        books = books,
                        selectedBook = selectedBook,
                        isLoading = isLoading,
                        selectedSubjectId = selectedSubjectId,
                        selectedGradeId = selectedGradeId,
                        onSearch = onSearchBooks,
                        onSelect = onSelectBook,
                        onSelectSubject = onSelectSubject,
                        onSelectGrade = onSelectGrade,
                        onToggleFavorite = onToggleFavorite,
                        isFavorite = isFavorite
                    )
                }
            }

            // 老师显示区域（选择书本后自动匹配）
            if (selectedBook != null && selectedSmartTeacher != null) {
                item(key = "teacher_info") {
                    TeacherInfoCard(
                        teacher = selectedSmartTeacher,
                        needSelect = needSelectTeacher,
                        teacherCount = smartTeachers.size,
                        onClickChange = { showTeacherDialog = true }
                    )
                }
            }

            // 步骤2: 选择班级
            if (selectedBook != null && bookClasses.isNotEmpty()) {
                item(key = "step_class") {
                    StepCard(
                        stepNumber = 2,
                        title = "选择班级",
                        subtitle = "${bookStudents.size} 名学生",
                        isCompleted = selectedBookClass != null && bookStudents.isNotEmpty(),
                        isEnabled = !isRunning
                    ) {
                        BookClassSection(
                            classes = bookClasses,
                            selectedClass = selectedBookClass,
                            onSelect = onSelectBookClass
                        )
                    }
                }
            }

            // 步骤3: 选择页码
            if (selectedBookClass != null) {
                item(key = "step_page") {
                    StepCard(
                        stepNumber = 3,
                        title = "选择页码",
                        isCompleted = true,
                        isEnabled = !isRunning
                    ) {
                        PageSelector(
                            currentPage = config.pageNumber,
                            onSelect = onUpdatePageNumber
                        )
                    }
                }
            }

            // 高级设置（可折叠）
            if (selectedBookClass != null) {
                item(key = "advanced_settings") {
                    AdvancedSettingsCard(
                        config = config,
                        isEnabled = !isRunning,
                        onUpdatePhotoInterval = onUpdatePhotoInterval,
                        onToggleDoublePageMode = onToggleDoublePageMode
                    )
                }
            }

            // 开始按钮
            if (!isRunning) {
                item(key = "start_button") {
                    StartAutomationButton(
                        canStart = canStart,
                        studentCount = bookStudents.size,
                        isConnected = connectionStatus.connected,
                        onClick = onStartAutomation
                    )
                }
            }

            // 执行日志
            item(key = "logs") {
                LogSection(logs = logs, onClear = onClearLogs)
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
    
    // 老师选择弹窗
    if (showTeacherDialog && smartTeachers.isNotEmpty()) {
        TeacherSelectDialog(
            teachers = smartTeachers,
            selectedTeacher = selectedSmartTeacher,
            onSelect = { teacher ->
                onSelectSmartTeacher(teacher)
                showTeacherDialog = false
            },
            onDismiss = { showTeacherDialog = false }
        )
    }
}


// ==================== 顶部标题区域 ====================

@Composable
private fun HeaderSection(
    connectionStatus: AdbClientStatus,
    onNavigateToManual: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp)
            .padding(top = 32.dp, bottom = 16.dp)
    ) {
        // 标题行
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "作业自动化",
                style = MaterialTheme.typography.headlineLarge,
                fontWeight = FontWeight.Bold,
                color = AppleBlack
            )
            // 手动模式入口
            Surface(
                modifier = Modifier.clickable { onNavigateToManual() },
                shape = RoundedCornerShape(Radius.md),
                color = AppleGray100
            ) {
                Text(
                    text = "手动模式",
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                    style = MaterialTheme.typography.bodyMedium,
                    color = AppleGray600
                )
            }
        }
        
        Spacer(modifier = Modifier.height(12.dp))
        
        // 连接状态卡片
        Surface(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(Radius.md),
            color = if (connectionStatus.connected) AppleGray50 else AppleGray100
        ) {
            Row(
                modifier = Modifier.padding(12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(10.dp)
                        .clip(CircleShape)
                        .background(if (connectionStatus.connected) AppleGreen else AppleRed)
                )
                Spacer(modifier = Modifier.width(10.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = if (connectionStatus.connected) "ADB 已连接" else "ADB 未连接",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Medium,
                        color = AppleBlack
                    )
                    if (connectionStatus.connected) {
                        Text(
                            text = connectionStatus.deviceInfo?.model ?: connectionStatus.ipAddress ?: "",
                            style = MaterialTheme.typography.bodySmall,
                            color = AppleGray500
                        )
                    } else {
                        Text(
                            text = "请在电脑端启动 ADB 客户端",
                            style = MaterialTheme.typography.bodySmall,
                            color = AppleGray500
                        )
                    }
                }
            }
        }
    }
}

// ==================== 最近使用区域 ====================

@Composable
private fun RecentUsageSection(
    usages: List<RecentUsage>,
    onQuickStart: (RecentUsage) -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp)
            .padding(bottom = 8.dp)
    ) {
        Text(
            text = "最近使用",
            style = MaterialTheme.typography.titleSmall,
            fontWeight = FontWeight.SemiBold,
            color = AppleGray500
        )
        
        Spacer(modifier = Modifier.height(8.dp))
        
        LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            items(usages, key = { "${it.bookId}_${it.classId}" }) { usage ->
                RecentUsageCard(usage = usage, onClick = { onQuickStart(usage) })
            }
        }
    }
}

@Composable
private fun RecentUsageCard(
    usage: RecentUsage,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .width(180.dp)
            .clickable { onClick() },
        shape = RoundedCornerShape(Radius.lg),
        colors = CardDefaults.cardColors(containerColor = AppleWhite),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Text(
                text = usage.bookName,
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = FontWeight.Medium,
                color = AppleBlack,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "${usage.className} · 第${usage.pageNumber}页",
                style = MaterialTheme.typography.bodySmall,
                color = AppleGray500
            )
            Spacer(modifier = Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "${usage.studentCount}人",
                    style = MaterialTheme.typography.bodySmall,
                    color = AppleGray400
                )
                Surface(
                    shape = RoundedCornerShape(Radius.sm),
                    color = AppleBlack
                ) {
                    Text(
                        text = "开始",
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
                        style = MaterialTheme.typography.bodySmall,
                        fontWeight = FontWeight.Medium,
                        color = AppleWhite
                    )
                }
            }
        }
    }
}

// ==================== 连接状态行 ====================

@Composable
private fun ConnectionStatusRow(status: AdbClientStatus) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier
                .size(8.dp)
                .clip(CircleShape)
                .background(if (status.connected) AppleGreen else AppleRed)
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = if (status.connected) 
                "已连接 · ${status.deviceInfo?.model ?: status.ipAddress ?: ""}"
            else "未连接 ADB 客户端",
            style = MaterialTheme.typography.bodyMedium,
            color = AppleGray500
        )
    }
}

// ==================== 运行中状态卡片 ====================

@Composable
private fun AutomationRunningCard(
    status: AutomationStatus,
    onStop: () -> Unit
) {
    val phaseText = when (status.phase) {
        AutomationPhase.PUBLISHING -> "发布作业中"
        AutomationPhase.WAITING -> "准备提交"
        AutomationPhase.SUBMITTING -> "提交作业中"
        AutomationPhase.COMPLETED -> "已完成"
        AutomationPhase.ERROR -> "出错"
        else -> "准备中"
    }
    
    val phaseColor = when (status.phase) {
        AutomationPhase.ERROR -> AppleRed
        AutomationPhase.COMPLETED -> AppleGreen
        else -> AppleOrange
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(Spacing.md),
        shape = RoundedCornerShape(Radius.xl),
        colors = CardDefaults.cardColors(containerColor = AppleBlack)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
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
                                .background(phaseColor)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = phaseText,
                            style = MaterialTheme.typography.bodySmall,
                            color = phaseColor
                        )
                    }
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "自动化流程",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold,
                        color = AppleWhite
                    )
                }
                if (status.phase != AutomationPhase.COMPLETED) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(32.dp),
                        color = AppleWhite,
                        strokeWidth = 3.dp
                    )
                }
            }
            
            Spacer(modifier = Modifier.height(16.dp))
            
            Text(
                text = status.stepDescription,
                style = MaterialTheme.typography.bodyMedium,
                color = AppleGray400
            )
            
            if (status.phase != AutomationPhase.COMPLETED && status.phase != AutomationPhase.ERROR) {
                Spacer(modifier = Modifier.height(16.dp))
                Button(
                    onClick = onStop,
                    modifier = Modifier.fillMaxWidth().height(48.dp),
                    shape = RoundedCornerShape(Radius.lg),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = AppleWhite,
                        contentColor = AppleBlack
                    )
                ) {
                    Text("停止", fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
}

// ==================== 步骤卡片 ====================

@Composable
private fun StepCard(
    stepNumber: Int,
    title: String,
    subtitle: String? = null,
    isCompleted: Boolean,
    isEnabled: Boolean,
    content: @Composable () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = Spacing.md, vertical = Spacing.sm),
        shape = RoundedCornerShape(Radius.lg),
        colors = CardDefaults.cardColors(
            containerColor = if (isEnabled) AppleWhite else AppleGray100
        )
    ) {
        Column(modifier = Modifier.padding(Spacing.md)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                // 步骤编号
                Surface(
                    modifier = Modifier.size(28.dp),
                    shape = CircleShape,
                    color = if (isCompleted) AppleBlack else AppleGray200
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        if (isCompleted) {
                            Icon(
                                Icons.Default.Check,
                                contentDescription = null,
                                tint = AppleWhite,
                                modifier = Modifier.size(16.dp)
                            )
                        } else {
                            Text(
                                text = stepNumber.toString(),
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.SemiBold,
                                color = AppleGray500
                            )
                        }
                    }
                }
                Spacer(modifier = Modifier.width(12.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = title,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = AppleBlack
                    )
                    subtitle?.let {
                        Text(
                            text = it,
                            style = MaterialTheme.typography.bodySmall,
                            color = AppleGray500
                        )
                    }
                }
            }
            
            Spacer(modifier = Modifier.height(Spacing.md))
            
            content()
        }
    }
}


// ==================== 书本搜索区域 ====================

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun BookSearchSection(
    keyword: String,
    books: List<BookInfo>,
    selectedBook: BookInfo?,
    isLoading: Boolean,
    selectedSubjectId: Int,
    selectedGradeId: Int,
    onSearch: (String) -> Unit,
    onSelect: (BookInfo) -> Unit,
    onSelectSubject: (Int) -> Unit,
    onSelectGrade: (Int) -> Unit,
    onToggleFavorite: (BookInfo) -> Unit,
    isFavorite: (String) -> Boolean
) {
    var text by remember { mutableStateOf(keyword) }
    var showFilters by remember { mutableStateOf(false) }
    
    Column {
        // 搜索框
        OutlinedTextField(
            value = text,
            onValueChange = { text = it; onSearch(it) },
            modifier = Modifier.fillMaxWidth(),
            placeholder = { Text("搜索书本名称...", color = AppleGray400) },
            leadingIcon = { Icon(Icons.Default.Search, contentDescription = null, tint = AppleGray400) },
            trailingIcon = {
                Row {
                    // 筛选按钮
                    IconButton(onClick = { showFilters = !showFilters }) {
                        Icon(
                            Icons.Default.FilterList,
                            contentDescription = "筛选",
                            tint = if (selectedSubjectId > 0 || selectedGradeId > 0) AppleBlack else AppleGray400
                        )
                    }
                    if (text.isNotEmpty()) {
                        IconButton(onClick = { text = ""; onSearch("") }) {
                            Icon(Icons.Default.Clear, contentDescription = "清除", tint = AppleGray400)
                        }
                    }
                }
            },
            shape = RoundedCornerShape(Radius.md),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = AppleBlack,
                unfocusedBorderColor = AppleGray200,
                focusedContainerColor = AppleGray50,
                unfocusedContainerColor = AppleGray50
            ),
            singleLine = true
        )
        
        // 筛选区域（竖排展开）
        AnimatedVisibility(visible = showFilters) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.sm)
            ) {
                // 学科筛选
                Text(
                    text = "学科",
                    style = MaterialTheme.typography.bodySmall,
                    color = AppleGray500,
                    modifier = Modifier.padding(bottom = 6.dp)
                )
                LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    items(SubjectOption.all, key = { "subject_${it.id}_${it.name}" }) { option ->
                        val isSelected = selectedSubjectId == option.id
                        FilterChip(
                            selected = isSelected,
                            onClick = { onSelectSubject(option.id) },
                            label = { Text(option.name, style = MaterialTheme.typography.bodySmall) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = AppleBlack,
                                selectedLabelColor = AppleWhite,
                                containerColor = AppleGray50
                            ),
                            modifier = Modifier.height(32.dp)
                        )
                    }
                }
                
                Spacer(modifier = Modifier.height(10.dp))
                
                // 年级筛选
                Text(
                    text = "年级",
                    style = MaterialTheme.typography.bodySmall,
                    color = AppleGray500,
                    modifier = Modifier.padding(bottom = 6.dp)
                )
                LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    items(GradeOption.all, key = { "grade_${it.id}" }) { option ->
                        val isSelected = selectedGradeId == option.id
                        FilterChip(
                            selected = isSelected,
                            onClick = { onSelectGrade(option.id) },
                            label = { Text(option.name, style = MaterialTheme.typography.bodySmall) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = AppleBlack,
                                selectedLabelColor = AppleWhite,
                                containerColor = AppleGray50
                            ),
                            modifier = Modifier.height(32.dp)
                        )
                    }
                }
            }
        }
        
        Spacer(modifier = Modifier.height(Spacing.sm))
        
        if (isLoading) {
            Box(
                modifier = Modifier.fillMaxWidth().height(60.dp),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator(
                    modifier = Modifier.size(24.dp),
                    color = AppleBlack,
                    strokeWidth = 2.dp
                )
            }
        } else if (books.isEmpty() && (text.isNotBlank() || selectedSubjectId > 0 || selectedGradeId > 0)) {
            Text(
                text = "未找到相关书本",
                modifier = Modifier.fillMaxWidth().padding(Spacing.md),
                style = MaterialTheme.typography.bodyMedium,
                color = AppleGray400,
                textAlign = TextAlign.Center
            )
        } else if (books.isNotEmpty()) {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                items(books, key = { it.id }) { book ->
                    val isSelected = selectedBook?.id == book.id
                    val bookIsFavorite = isFavorite(book.id)
                    
                    Card(
                        modifier = Modifier
                            .width(170.dp)
                            .clickable { onSelect(book) },
                        shape = RoundedCornerShape(Radius.md),
                        colors = CardDefaults.cardColors(
                            containerColor = if (isSelected) AppleBlack else AppleGray50
                        )
                    ) {
                        Column(modifier = Modifier.padding(Spacing.md)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.Top
                            ) {
                                Text(
                                    text = book.bookName,
                                    style = MaterialTheme.typography.bodyLarge,
                                    fontWeight = FontWeight.Medium,
                                    color = if (isSelected) AppleWhite else AppleBlack,
                                    maxLines = 2,
                                    overflow = TextOverflow.Ellipsis,
                                    modifier = Modifier.weight(1f)
                                )
                                // 收藏按钮
                                IconButton(
                                    onClick = { onToggleFavorite(book) },
                                    modifier = Modifier.size(24.dp)
                                ) {
                                    Icon(
                                        imageVector = if (bookIsFavorite) Icons.Default.Favorite else Icons.Outlined.FavoriteBorder,
                                        contentDescription = "收藏",
                                        tint = if (bookIsFavorite) AppleRed else (if (isSelected) AppleGray400 else AppleGray400),
                                        modifier = Modifier.size(18.dp)
                                    )
                                }
                            }
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

// ==================== 班级选择区域 ====================

@Composable
private fun BookClassSection(
    classes: List<BookClassInfo>,
    selectedClass: BookClassInfo?,
    onSelect: (BookClassInfo) -> Unit
) {
    LazyRow(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        items(classes, key = { it.id }) { cls ->
            val isSelected = selectedClass?.id == cls.id
            FilterChip(
                selected = isSelected,
                onClick = { onSelect(cls) },
                label = { 
                    Text(
                        text = "${cls.name} (${cls.studentCount}人)",
                        fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Normal
                    )
                },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = AppleBlack,
                    selectedLabelColor = AppleWhite,
                    containerColor = AppleGray50
                )
            )
        }
    }
}

// ==================== 页码选择器 ====================

@Composable
private fun PageSelector(
    currentPage: Int,
    onSelect: (Int) -> Unit
) {
    LazyRow(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        items(PageOption.presets) { option ->
            val isSelected = currentPage == option.number
            Surface(
                modifier = Modifier
                    .size(56.dp)
                    .clickable { onSelect(option.number) },
                shape = RoundedCornerShape(Radius.md),
                color = if (isSelected) AppleBlack else AppleGray50
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text(
                        text = option.number.toString(),
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.SemiBold,
                        color = if (isSelected) AppleWhite else AppleGray500
                    )
                }
            }
        }
    }
}


// ==================== 高级设置卡片 ====================

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AdvancedSettingsCard(
    config: AutomationConfig,
    isEnabled: Boolean,
    onUpdatePhotoInterval: (Int) -> Unit,
    onToggleDoublePageMode: () -> Unit
) {
    var expanded by remember { mutableStateOf(false) }
    
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = Spacing.md, vertical = Spacing.sm),
        shape = RoundedCornerShape(Radius.lg),
        colors = CardDefaults.cardColors(containerColor = AppleWhite)
    ) {
        Column(modifier = Modifier.padding(Spacing.md)) {
            // 标题行（可点击展开）
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { expanded = !expanded },
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "高级设置",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = AppleGray500
                )
                Icon(
                    imageVector = if (expanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                    contentDescription = null,
                    tint = AppleGray400
                )
            }
            
            AnimatedVisibility(visible = expanded) {
                Column(modifier = Modifier.padding(top = Spacing.md)) {
                    // 拍照间隔
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "拍照间隔",
                            style = MaterialTheme.typography.bodyMedium,
                            color = AppleGray500
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            listOf(1, 2, 3, 5).forEach { sec ->
                                val isSelected = config.photoInterval == sec
                                Surface(
                                    modifier = Modifier.clickable(enabled = isEnabled) { 
                                        onUpdatePhotoInterval(sec) 
                                    },
                                    shape = RoundedCornerShape(Radius.sm),
                                    color = if (isSelected) AppleBlack else AppleGray100
                                ) {
                                    Text(
                                        text = "${sec}s",
                                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                                        style = MaterialTheme.typography.bodyMedium,
                                        fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Normal,
                                        color = if (isSelected) AppleWhite else AppleGray500
                                    )
                                }
                            }
                        }
                    }
                    
                    Spacer(modifier = Modifier.height(Spacing.md))
                    
                    // 双页模式
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable(enabled = isEnabled) { onToggleDoublePageMode() },
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "双页拍照模式",
                            style = MaterialTheme.typography.bodyMedium,
                            color = AppleGray500
                        )
                        Switch(
                            checked = config.enableDoublePageMode,
                            onCheckedChange = { onToggleDoublePageMode() },
                            enabled = isEnabled,
                            colors = SwitchDefaults.colors(
                                checkedThumbColor = AppleWhite,
                                checkedTrackColor = AppleBlack,
                                uncheckedThumbColor = AppleWhite,
                                uncheckedTrackColor = AppleGray300
                            )
                        )
                    }
                }
            }
        }
    }
}

// ==================== 开始按钮 ====================

@Composable
private fun StartAutomationButton(
    canStart: Boolean,
    studentCount: Int,
    isConnected: Boolean,
    onClick: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(Spacing.md)
    ) {
        Button(
            onClick = onClick,
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp),
            enabled = canStart,
            shape = RoundedCornerShape(Radius.lg),
            colors = ButtonDefaults.buttonColors(
                containerColor = AppleBlack,
                contentColor = AppleWhite,
                disabledContainerColor = AppleGray200,
                disabledContentColor = AppleGray400
            )
        ) {
            Icon(Icons.Default.PlayArrow, contentDescription = null, modifier = Modifier.size(24.dp))
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = if (studentCount > 0) "开始自动化 ($studentCount 人)" else "开始自动化",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )
        }
        
        // 提示信息
        if (!isConnected) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "请先连接 ADB 客户端",
                style = MaterialTheme.typography.bodySmall,
                color = AppleRed,
                modifier = Modifier.fillMaxWidth(),
                textAlign = TextAlign.Center
            )
        } else if (studentCount == 0) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "请先选择书本和班级",
                style = MaterialTheme.typography.bodySmall,
                color = AppleGray400,
                modifier = Modifier.fillMaxWidth(),
                textAlign = TextAlign.Center
            )
        }
    }
}

// ==================== 日志区域 ====================

@Composable
private fun LogSection(logs: List<RfidLogEntry>, onClear: () -> Unit) {
    Column(modifier = Modifier.fillMaxWidth().padding(Spacing.md)) {
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
            TextButton(onClick = onClear, enabled = logs.isNotEmpty()) {
                Text(
                    text = "清空",
                    color = if (logs.isNotEmpty()) AppleBlack else AppleGray400,
                    fontWeight = FontWeight.Medium
                )
            }
        }
        
        Spacer(modifier = Modifier.height(Spacing.sm))
        
        Card(
            shape = RoundedCornerShape(Radius.lg),
            colors = CardDefaults.cardColors(containerColor = AppleWhite)
        ) {
            if (logs.isEmpty()) {
                Box(
                    modifier = Modifier.fillMaxWidth().height(80.dp),
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
                        .heightIn(max = 200.dp)
                        .padding(Spacing.md),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    logs.take(10).forEach { log ->
                        val levelColor = when (log.level) {
                            "success" -> AppleGreen
                            "error" -> AppleRed
                            else -> AppleGray500
                        }
                        Row(verticalAlignment = Alignment.Top) {
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
                }
            }
        }
    }
}

// ==================== 老师信息卡片 ====================

@Composable
private fun TeacherInfoCard(
    teacher: SmartPublishTeacher,
    needSelect: Boolean,
    teacherCount: Int,
    onClickChange: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = Spacing.md, vertical = Spacing.sm),
        shape = RoundedCornerShape(Radius.lg),
        colors = CardDefaults.cardColors(containerColor = AppleWhite)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(Spacing.md),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                // 老师图标
                Surface(
                    modifier = Modifier.size(40.dp),
                    shape = CircleShape,
                    color = AppleGray100
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(
                            Icons.Default.Person,
                            contentDescription = null,
                            tint = AppleGray500,
                            modifier = Modifier.size(24.dp)
                        )
                    }
                }
                Spacer(modifier = Modifier.width(12.dp))
                Column {
                    Text(
                        text = teacher.teacherName,
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.Medium,
                        color = AppleBlack
                    )
                    Text(
                        text = teacher.className,
                        style = MaterialTheme.typography.bodySmall,
                        color = AppleGray500
                    )
                }
            }
            
            // 切换按钮（多老师时显示）
            if (needSelect && teacherCount > 1) {
                Surface(
                    modifier = Modifier.clickable { onClickChange() },
                    shape = RoundedCornerShape(Radius.sm),
                    color = AppleGray100
                ) {
                    Text(
                        text = "切换",
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                        style = MaterialTheme.typography.bodySmall,
                        fontWeight = FontWeight.Medium,
                        color = AppleGray600
                    )
                }
            }
        }
    }
}

// ==================== 老师选择弹窗 ====================

@Composable
private fun TeacherSelectDialog(
    teachers: List<SmartPublishTeacher>,
    selectedTeacher: SmartPublishTeacher?,
    onSelect: (SmartPublishTeacher) -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                text = "选择老师",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold
            )
        },
        text = {
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(teachers, key = { it.id }) { teacher ->
                    val isSelected = selectedTeacher?.id == teacher.id
                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { onSelect(teacher) },
                        shape = RoundedCornerShape(Radius.md),
                        color = if (isSelected) AppleBlack else AppleGray50
                    ) {
                        Row(
                            modifier = Modifier.padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = teacher.teacherName,
                                    style = MaterialTheme.typography.bodyLarge,
                                    fontWeight = FontWeight.Medium,
                                    color = if (isSelected) AppleWhite else AppleBlack
                                )
                                Text(
                                    text = teacher.className,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = if (isSelected) AppleGray400 else AppleGray500
                                )
                            }
                            if (isSelected) {
                                Icon(
                                    Icons.Default.Check,
                                    contentDescription = null,
                                    tint = AppleWhite,
                                    modifier = Modifier.size(20.dp)
                                )
                            }
                        }
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("关闭", color = AppleBlack)
            }
        },
        containerColor = AppleWhite,
        shape = RoundedCornerShape(Radius.xl)
    )
}
