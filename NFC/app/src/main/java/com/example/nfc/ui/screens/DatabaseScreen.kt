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
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.example.nfc.data.*
import com.example.nfc.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DatabaseScreen(
    grades: List<GradeInfo>,
    teachers: List<TeacherInfo>,
    classes: List<ClassInfo>,
    students: List<StudentInfo>,
    selectedClass: ClassInfo?,
    filterState: FilterState,
    isLoading: Boolean,
    errorMessage: String?,
    favoriteClassIds: Set<Long>,
    isOfflineMode: Boolean,
    onFilterChange: (FilterState) -> Unit,
    onSelectClass: (ClassInfo) -> Unit,
    onAddStudentsToCards: (List<StudentInfo>) -> Unit,
    onToggleFavorite: (Long) -> Unit,
    onRefresh: () -> Unit,
    onBack: () -> Unit
) {
    var showStudentSheet by remember { mutableStateOf(false) }
    var selectedStudents by remember { mutableStateOf<Set<Long>>(emptySet()) }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { 
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("选择班级", fontWeight = FontWeight.SemiBold)
                        if (isOfflineMode) {
                            Text(
                                text = "离线模式",
                                style = MaterialTheme.typography.bodySmall,
                                color = AppleOrange
                            )
                        }
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBackIosNew, contentDescription = "返回")
                    }
                },
                actions = {
                    IconButton(onClick = onRefresh) {
                        Icon(
                            imageVector = if (isLoading) Icons.Default.Sync else Icons.Default.Refresh,
                            contentDescription = "刷新",
                            tint = if (isLoading) AppleGray400 else MaterialTheme.colorScheme.onSurface
                        )
                    }
                },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background
                )
            )
        },
        containerColor = MaterialTheme.colorScheme.background
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = PaddingValues(bottom = 32.dp)
        ) {
            // 错误提示
            if (errorMessage != null) {
                item {
                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 24.dp, vertical = 8.dp),
                        shape = RoundedCornerShape(12.dp),
                        color = AppleOrange.copy(alpha = 0.1f)
                    ) {
                        Row(
                            modifier = Modifier.padding(16.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                Icons.Outlined.Info,
                                contentDescription = null,
                                tint = AppleOrange,
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Text(
                                text = errorMessage,
                                style = MaterialTheme.typography.bodySmall,
                                color = AppleOrange
                            )
                        }
                    }
                }
            }

            // 搜索框
            item {
                OutlinedTextField(
                    value = filterState.searchKeyword,
                    onValueChange = { onFilterChange(filterState.copy(searchKeyword = it)) },
                    placeholder = { Text("搜索班级") },
                    leadingIcon = { 
                        Icon(
                            Icons.Default.Search, 
                            contentDescription = null,
                            tint = AppleGray400
                        ) 
                    },
                    trailingIcon = {
                        if (filterState.searchKeyword.isNotEmpty()) {
                            IconButton(onClick = { onFilterChange(filterState.copy(searchKeyword = "")) }) {
                                Icon(Icons.Default.Clear, contentDescription = "清除", tint = AppleGray400)
                            }
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 24.dp, vertical = 8.dp),
                    shape = RoundedCornerShape(12.dp),
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = AppleBlack,
                        unfocusedBorderColor = AppleGray200,
                        focusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                        unfocusedContainerColor = MaterialTheme.colorScheme.surfaceVariant
                    )
                )
            }

            // 筛选标签
            item {
                FilterChipsRow(
                    grades = grades,
                    teachers = teachers,
                    filterState = filterState,
                    onFilterChange = onFilterChange
                )
            }

            // 常用班级
            val favoriteClasses = classes.filter { it.id in favoriteClassIds }
            if (favoriteClasses.isNotEmpty()) {
                item {
                    Column(modifier = Modifier.padding(top = 16.dp)) {
                        Row(
                            modifier = Modifier.padding(horizontal = 24.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                Icons.Default.Star,
                                contentDescription = null,
                                tint = AppleOrange,
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "常用",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.SemiBold
                            )
                        }
                        Spacer(modifier = Modifier.height(12.dp))
                        LazyRow(
                            contentPadding = PaddingValues(horizontal = 24.dp),
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            items(favoriteClasses) { classInfo ->
                                FavoriteClassChip(
                                    classInfo = classInfo,
                                    isSelected = selectedClass?.id == classInfo.id,
                                    onClick = {
                                        onSelectClass(classInfo)
                                        showStudentSheet = true
                                        selectedStudents = emptySet()
                                    }
                                )
                            }
                        }
                    }
                }
            }

            // 班级列表标题
            item {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 24.dp, vertical = 16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "全部班级",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        text = "${classes.size} 个",
                        style = MaterialTheme.typography.bodySmall,
                        color = AppleGray400
                    )
                }
            }

            // 加载状态
            if (isLoading && classes.isEmpty()) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(48.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        CircularProgressIndicator(
                            color = AppleBlack,
                            strokeWidth = 2.dp
                        )
                    }
                }
            } else if (classes.isEmpty()) {
                item {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(48.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Icon(
                            Icons.Outlined.SearchOff,
                            contentDescription = null,
                            modifier = Modifier.size(48.dp),
                            tint = AppleGray200
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        Text(
                            text = "没有找到班级",
                            style = MaterialTheme.typography.bodyMedium,
                            color = AppleGray400
                        )
                    }
                }
            } else {
                items(classes, key = { it.id }) { classInfo ->
                    ClassListItem(
                        classInfo = classInfo,
                        isSelected = selectedClass?.id == classInfo.id,
                        isFavorite = classInfo.id in favoriteClassIds,
                        onClick = {
                            onSelectClass(classInfo)
                            showStudentSheet = true
                            selectedStudents = emptySet()
                        },
                        onToggleFavorite = { onToggleFavorite(classInfo.id) }
                    )
                }
            }
        }
    }

    // 学生列表底部弹窗
    if (showStudentSheet && selectedClass != null) {
        StudentBottomSheet(
            classInfo = selectedClass,
            students = students,
            selectedStudents = selectedStudents,
            isLoading = isLoading,
            onSelectStudent = { studentId ->
                selectedStudents = if (studentId in selectedStudents) {
                    selectedStudents - studentId
                } else {
                    selectedStudents + studentId
                }
            },
            onSelectAll = {
                val rfidStudents = students.filter { !it.rfidNo.isNullOrBlank() }
                selectedStudents = if (selectedStudents.size == rfidStudents.size) {
                    emptySet()
                } else {
                    rfidStudents.map { it.id }.toSet()
                }
            },
            onConfirm = {
                val selected = students.filter { it.id in selectedStudents && !it.rfidNo.isNullOrBlank() }
                onAddStudentsToCards(selected)
                showStudentSheet = false
                selectedStudents = emptySet()
            },
            onDismiss = {
                showStudentSheet = false
                selectedStudents = emptySet()
            }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun FilterChipsRow(
    grades: List<GradeInfo>,
    teachers: List<TeacherInfo>,
    filterState: FilterState,
    onFilterChange: (FilterState) -> Unit
) {
    var showGradeMenu by remember { mutableStateOf(false) }
    var showTeacherMenu by remember { mutableStateOf(false) }

    LazyRow(
        contentPadding = PaddingValues(horizontal = 24.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        // 年级筛选
        item {
            Box {
                FilterChip(
                    selected = filterState.gradeId != null,
                    onClick = { showGradeMenu = true },
                    label = {
                        Text(
                            text = filterState.gradeId?.let { GradeInfo.GRADE_MAP[it] } ?: "年级",
                            maxLines = 1
                        )
                    },
                    trailingIcon = {
                        Icon(
                            Icons.Default.ArrowDropDown,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp)
                        )
                    },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = AppleBlack,
                        selectedLabelColor = AppleWhite
                    )
                )
                DropdownMenu(
                    expanded = showGradeMenu,
                    onDismissRequest = { showGradeMenu = false }
                ) {
                    DropdownMenuItem(
                        text = { Text("全部年级") },
                        onClick = {
                            onFilterChange(filterState.copy(gradeId = null))
                            showGradeMenu = false
                        }
                    )
                    grades.forEach { grade ->
                        DropdownMenuItem(
                            text = { Text(grade.name) },
                            onClick = {
                                onFilterChange(filterState.copy(gradeId = grade.id))
                                showGradeMenu = false
                            }
                        )
                    }
                }
            }
        }

        // 老师筛选
        item {
            Box {
                FilterChip(
                    selected = filterState.teacherId != null,
                    onClick = { showTeacherMenu = true },
                    label = {
                        Text(
                            text = filterState.teacherId?.let { id ->
                                teachers.find { it.id == id }?.name
                            } ?: "老师",
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    },
                    trailingIcon = {
                        Icon(
                            Icons.Default.ArrowDropDown,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp)
                        )
                    },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = AppleBlack,
                        selectedLabelColor = AppleWhite
                    )
                )
                DropdownMenu(
                    expanded = showTeacherMenu,
                    onDismissRequest = { showTeacherMenu = false },
                    modifier = Modifier.heightIn(max = 300.dp)
                ) {
                    DropdownMenuItem(
                        text = { Text("全部老师") },
                        onClick = {
                            onFilterChange(filterState.copy(teacherId = null))
                            showTeacherMenu = false
                        }
                    )
                    teachers.take(50).forEach { teacher ->
                        DropdownMenuItem(
                            text = { Text(teacher.name) },
                            onClick = {
                                onFilterChange(filterState.copy(teacherId = teacher.id))
                                showTeacherMenu = false
                            }
                        )
                    }
                }
            }
        }

        // 清除筛选
        if (filterState.gradeId != null || filterState.teacherId != null) {
            item {
                FilterChip(
                    selected = false,
                    onClick = { onFilterChange(FilterState()) },
                    label = { Text("清除") },
                    leadingIcon = {
                        Icon(
                            Icons.Default.Clear,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                )
            }
        }
    }
}

@Composable
private fun FavoriteClassChip(
    classInfo: ClassInfo,
    isSelected: Boolean,
    onClick: () -> Unit
) {
    Surface(
        modifier = Modifier.clickable { onClick() },
        shape = RoundedCornerShape(12.dp),
        color = if (isSelected) AppleBlack else MaterialTheme.colorScheme.surfaceVariant
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = classInfo.name,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Medium,
                color = if (isSelected) AppleWhite else MaterialTheme.colorScheme.onSurface
            )
            Text(
                text = if (classInfo.rfidCount > 0) "${classInfo.studentCount}人·${classInfo.rfidCount}卡" else "${classInfo.studentCount}人",
                style = MaterialTheme.typography.bodySmall,
                color = if (isSelected) AppleWhite.copy(alpha = 0.7f) else AppleGray400
            )
        }
    }
}

@Composable
private fun ClassListItem(
    classInfo: ClassInfo,
    isSelected: Boolean,
    isFavorite: Boolean,
    onClick: () -> Unit,
    onToggleFavorite: () -> Unit
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp, vertical = 4.dp)
            .clickable { onClick() },
        shape = RoundedCornerShape(12.dp),
        color = if (isSelected) AppleBlue.copy(alpha = 0.08f) else MaterialTheme.colorScheme.surfaceVariant
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // 班级图标
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clip(CircleShape)
                    .background(if (isSelected) AppleBlue.copy(alpha = 0.15f) else AppleGray100),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    Icons.Outlined.Groups,
                    contentDescription = null,
                    tint = if (isSelected) AppleBlue else AppleGray500,
                    modifier = Modifier.size(22.dp)
                )
            }

            Spacer(modifier = Modifier.width(14.dp))

            // 班级信息
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = classInfo.name,
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.Medium
                    )
                    // 缓存标识
                    if (classInfo.isCached) {
                        Spacer(modifier = Modifier.width(6.dp))
                        Surface(
                            shape = RoundedCornerShape(4.dp),
                            color = AppleGreen.copy(alpha = 0.12f)
                        ) {
                            Text(
                                text = "已缓存",
                                style = MaterialTheme.typography.labelSmall,
                                color = AppleGreen,
                                modifier = Modifier.padding(horizontal = 4.dp, vertical = 1.dp)
                            )
                        }
                    }
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = classInfo.gradeName,
                        style = MaterialTheme.typography.bodySmall,
                        color = AppleGray400
                    )
                    Text(
                        text = " · ${classInfo.studentCount}人",
                        style = MaterialTheme.typography.bodySmall,
                        color = AppleGray400
                    )
                    // 显示有卡人数
                    if (classInfo.rfidCount > 0) {
                        Text(
                            text = " · ${classInfo.rfidCount}有卡",
                            style = MaterialTheme.typography.bodySmall,
                            color = AppleBlue
                        )
                    }
                }
            }

            // 收藏按钮
            IconButton(
                onClick = onToggleFavorite,
                modifier = Modifier.size(36.dp)
            ) {
                Icon(
                    imageVector = if (isFavorite) Icons.Default.Star else Icons.Outlined.StarBorder,
                    contentDescription = if (isFavorite) "取消收藏" else "收藏",
                    tint = if (isFavorite) AppleOrange else AppleGray400,
                    modifier = Modifier.size(20.dp)
                )
            }

            Icon(
                Icons.Default.ChevronRight,
                contentDescription = null,
                tint = AppleGray400,
                modifier = Modifier.size(20.dp)
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun StudentBottomSheet(
    classInfo: ClassInfo,
    students: List<StudentInfo>,
    selectedStudents: Set<Long>,
    isLoading: Boolean,
    onSelectStudent: (Long) -> Unit,
    onSelectAll: () -> Unit,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit
) {
    val rfidStudents = students.filter { !it.rfidNo.isNullOrBlank() }
    val representativeCount = students.count { it.isRepresentative && !it.rfidNo.isNullOrBlank() }
    val selectedCount = selectedStudents.size

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        containerColor = MaterialTheme.colorScheme.surface,
        dragHandle = {
            Box(
                modifier = Modifier
                    .padding(vertical = 12.dp)
                    .width(36.dp)
                    .height(4.dp)
                    .clip(RoundedCornerShape(2.dp))
                    .background(AppleGray200)
            )
        }
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 24.dp)
                .padding(bottom = 32.dp)
        ) {
            // 标题
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = classInfo.name,
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "${students.size}名学生，${rfidStudents.size}人有卡" + 
                            if (representativeCount > 0) "，${representativeCount}名课代表" else "",
                        style = MaterialTheme.typography.bodySmall,
                        color = AppleGray400
                    )
                }
                TextButton(onClick = onSelectAll) {
                    Text(
                        text = if (selectedCount == rfidStudents.size) "取消全选" else "全选",
                        color = AppleBlue,
                        fontWeight = FontWeight.Medium
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // 学生列表
            if (isLoading) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(200.dp),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator(color = AppleBlack, strokeWidth = 2.dp)
                }
            } else {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(max = 400.dp),
                    verticalArrangement = Arrangement.spacedBy(2.dp)
                ) {
                    items(students, key = { it.id }) { student ->
                        val hasRfid = !student.rfidNo.isNullOrBlank()
                        val isSelected = student.id in selectedStudents

                        Surface(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable(enabled = hasRfid) { onSelectStudent(student.id) },
                            shape = RoundedCornerShape(10.dp),
                            color = when {
                                isSelected -> AppleBlue.copy(alpha = 0.08f)
                                student.isRepresentative -> AppleOrange.copy(alpha = 0.06f)
                                !hasRfid -> AppleGray50.copy(alpha = 0.5f)
                                else -> MaterialTheme.colorScheme.surface
                            }
                        ) {
                            Row(
                                modifier = Modifier.padding(12.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Checkbox(
                                    checked = isSelected,
                                    onCheckedChange = { if (hasRfid) onSelectStudent(student.id) },
                                    enabled = hasRfid,
                                    colors = CheckboxDefaults.colors(
                                        checkedColor = AppleBlack,
                                        uncheckedColor = if (hasRfid) AppleGray400 else AppleGray200
                                    )
                                )

                                Spacer(modifier = Modifier.width(8.dp))

                                Column(modifier = Modifier.weight(1f)) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Text(
                                            text = student.name,
                                            style = MaterialTheme.typography.bodyMedium,
                                            fontWeight = FontWeight.Medium,
                                            color = if (hasRfid) MaterialTheme.colorScheme.onSurface else AppleGray400
                                        )
                                        if (!student.stuNum.isNullOrBlank()) {
                                            Text(
                                                text = " ${student.stuNum}",
                                                style = MaterialTheme.typography.bodySmall,
                                                color = AppleGray400
                                            )
                                        }
                                        // 课代表标识
                                        if (student.isRepresentative) {
                                            Spacer(modifier = Modifier.width(6.dp))
                                            Surface(
                                                shape = RoundedCornerShape(4.dp),
                                                color = AppleOrange.copy(alpha = 0.15f)
                                            ) {
                                                Text(
                                                    text = "${student.subjectName ?: ""}课代表",
                                                    style = MaterialTheme.typography.labelSmall,
                                                    color = AppleOrange,
                                                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                                )
                                            }
                                        }
                                    }
                                    Text(
                                        text = if (hasRfid) student.rfidNo!! else "无卡",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = if (hasRfid) AppleBlue else AppleRed.copy(alpha = 0.6f)
                                    )
                                }
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(20.dp))

            // 确认按钮
            Button(
                onClick = onConfirm,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(50.dp),
                enabled = selectedCount > 0,
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = AppleBlack,
                    contentColor = AppleWhite
                )
            ) {
                Text(
                    text = if (selectedCount > 0) "添加 $selectedCount 张卡片" else "请选择学生",
                    fontWeight = FontWeight.SemiBold
                )
            }
        }
    }
}
