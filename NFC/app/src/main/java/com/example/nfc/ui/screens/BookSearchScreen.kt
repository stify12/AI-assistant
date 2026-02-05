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
fun BookSearchScreen(
    books: List<BookInfo>,
    selectedBook: BookInfo?,
    bookClasses: List<BookClassInfo>,
    selectedBookClass: BookClassInfo?,
    bookStudents: List<BookStudentRfid>,
    searchKeyword: String,
    selectedSubjectId: Int?,
    isLoading: Boolean,
    onSearch: (String, Int?) -> Unit,
    onSelectBook: (BookInfo) -> Unit,
    onSelectClass: (BookClassInfo) -> Unit,
    onStartSimulation: (List<BookStudentRfid>) -> Unit,
    onBack: () -> Unit
) {
    var localKeyword by remember { mutableStateOf(searchKeyword) }
    var showStudentSheet by remember { mutableStateOf(false) }
    var selectedStudents by remember { mutableStateOf<Set<String>>(emptySet()) }

    // 初始加载
    LaunchedEffect(Unit) {
        if (books.isEmpty()) {
            onSearch("", null)
        }
    }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("书本搜索", fontWeight = FontWeight.SemiBold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBackIosNew, contentDescription = "返回")
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
            // 搜索框
            item {
                OutlinedTextField(
                    value = localKeyword,
                    onValueChange = { localKeyword = it },
                    placeholder = { Text("搜索书本名称") },
                    leadingIcon = {
                        Icon(Icons.Default.Search, contentDescription = null, tint = AppleGray400)
                    },
                    trailingIcon = {
                        if (localKeyword.isNotEmpty()) {
                            IconButton(onClick = {
                                localKeyword = ""
                                onSearch("", selectedSubjectId)
                            }) {
                                Icon(Icons.Default.Clear, contentDescription = "清除", tint = AppleGray400)
                            }
                        } else {
                            IconButton(onClick = { onSearch(localKeyword, selectedSubjectId) }) {
                                Icon(Icons.Default.Search, contentDescription = "搜索", tint = AppleBlack)
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

            // 科目筛选
            item {
                SubjectFilterRow(
                    selectedSubjectId = selectedSubjectId,
                    onSelectSubject = { subjectId ->
                        onSearch(localKeyword, subjectId)
                    }
                )
            }

            // 书本列表标题
            item {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 24.dp, vertical = 12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = if (selectedBook != null) "已选书本" else "书本列表",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold
                    )
                    if (selectedBook == null) {
                        Text(
                            text = "${books.size} 本",
                            style = MaterialTheme.typography.bodySmall,
                            color = AppleGray400
                        )
                    }
                }
            }

            // 加载状态
            if (isLoading && books.isEmpty()) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(48.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        CircularProgressIndicator(color = AppleBlack, strokeWidth = 2.dp)
                    }
                }
            } else if (selectedBook != null) {
                // 已选书本
                item {
                    SelectedBookCard(
                        book = selectedBook,
                        onClear = { onSearch(localKeyword, selectedSubjectId) }
                    )
                }

                // 关联班级
                item {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 24.dp, vertical = 12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "关联班级",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.SemiBold
                        )
                        Text(
                            text = "${bookClasses.size} 个",
                            style = MaterialTheme.typography.bodySmall,
                            color = AppleGray400
                        )
                    }
                }

                if (isLoading && bookClasses.isEmpty()) {
                    item {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(24.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            CircularProgressIndicator(color = AppleBlack, strokeWidth = 2.dp)
                        }
                    }
                } else if (bookClasses.isEmpty()) {
                    item {
                        EmptyState(message = "该书本暂无关联班级")
                    }
                } else {
                    items(bookClasses, key = { it.id }) { bookClass ->
                        BookClassItem(
                            bookClass = bookClass,
                            isSelected = selectedBookClass?.id == bookClass.id,
                            onClick = {
                                onSelectClass(bookClass)
                                showStudentSheet = true
                                selectedStudents = emptySet()
                            }
                        )
                    }
                }
            } else if (books.isEmpty()) {
                item {
                    EmptyState(message = "没有找到书本")
                }
            } else {
                items(books, key = { it.id }) { book ->
                    BookListItem(
                        book = book,
                        onClick = { onSelectBook(book) }
                    )
                }
            }
        }
    }

    // 学生列表底部弹窗
    if (showStudentSheet && selectedBook != null && selectedBookClass != null) {
        BookStudentBottomSheet(
            book = selectedBook,
            bookClass = selectedBookClass,
            students = bookStudents,
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
                selectedStudents = if (selectedStudents.size == bookStudents.size) {
                    emptySet()
                } else {
                    bookStudents.map { it.id }.toSet()
                }
            },
            onConfirm = {
                val selected = bookStudents.filter { it.id in selectedStudents }
                onStartSimulation(selected)
                showStudentSheet = false
            },
            onDismiss = {
                showStudentSheet = false
                selectedStudents = emptySet()
            }
        )
    }
}

@Composable
private fun SubjectFilterRow(
    selectedSubjectId: Int?,
    onSelectSubject: (Int?) -> Unit
) {
    LazyRow(
        contentPadding = PaddingValues(horizontal = 24.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        // 全部
        item {
            FilterChip(
                selected = selectedSubjectId == null,
                onClick = { onSelectSubject(null) },
                label = { Text("全部") },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = AppleBlack,
                    selectedLabelColor = AppleWhite
                )
            )
        }
        // 各科目
        items(SubjectInfo.SUBJECT_LIST) { subject ->
            FilterChip(
                selected = selectedSubjectId == subject.id,
                onClick = { onSelectSubject(subject.id) },
                label = { Text(subject.name) },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = AppleBlack,
                    selectedLabelColor = AppleWhite
                )
            )
        }
    }
}

@Composable
private fun BookListItem(
    book: BookInfo,
    onClick: () -> Unit
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp, vertical = 4.dp)
            .clickable { onClick() },
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.surfaceVariant
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // 书本图标
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(AppleBlue.copy(alpha = 0.1f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    Icons.Outlined.MenuBook,
                    contentDescription = null,
                    tint = AppleBlue,
                    modifier = Modifier.size(22.dp)
                )
            }

            Spacer(modifier = Modifier.width(14.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = book.bookName,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (!book.subjectName.isNullOrBlank()) {
                        Text(
                            text = book.subjectName,
                            style = MaterialTheme.typography.bodySmall,
                            color = AppleBlue
                        )
                        Text(
                            text = " · ",
                            style = MaterialTheme.typography.bodySmall,
                            color = AppleGray400
                        )
                    }
                    if (!book.gradeName.isNullOrBlank()) {
                        Text(
                            text = book.gradeName,
                            style = MaterialTheme.typography.bodySmall,
                            color = AppleGray400
                        )
                    }
                }
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

@Composable
private fun SelectedBookCard(
    book: BookInfo,
    onClear: () -> Unit
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp, vertical = 4.dp),
        shape = RoundedCornerShape(12.dp),
        color = AppleBlue.copy(alpha = 0.08f)
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(AppleBlue.copy(alpha = 0.15f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    Icons.Filled.MenuBook,
                    contentDescription = null,
                    tint = AppleBlue,
                    modifier = Modifier.size(22.dp)
                )
            }

            Spacer(modifier = Modifier.width(14.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = book.bookName,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
                Row {
                    if (!book.subjectName.isNullOrBlank()) {
                        Text(
                            text = book.subjectName,
                            style = MaterialTheme.typography.bodySmall,
                            color = AppleBlue
                        )
                    }
                    if (!book.gradeName.isNullOrBlank()) {
                        Text(
                            text = " · ${book.gradeName}",
                            style = MaterialTheme.typography.bodySmall,
                            color = AppleGray400
                        )
                    }
                }
            }

            IconButton(onClick = onClear) {
                Icon(
                    Icons.Default.Close,
                    contentDescription = "取消选择",
                    tint = AppleGray500,
                    modifier = Modifier.size(20.dp)
                )
            }
        }
    }
}

@Composable
private fun BookClassItem(
    bookClass: BookClassInfo,
    isSelected: Boolean,
    onClick: () -> Unit
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
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(CircleShape)
                    .background(if (isSelected) AppleBlue.copy(alpha = 0.15f) else AppleGray100),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    Icons.Outlined.Groups,
                    contentDescription = null,
                    tint = if (isSelected) AppleBlue else AppleGray500,
                    modifier = Modifier.size(20.dp)
                )
            }

            Spacer(modifier = Modifier.width(12.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = bookClass.name,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium
                )
                Text(
                    text = "${bookClass.gradeName ?: ""} · ${bookClass.studentCount}人有卡",
                    style = MaterialTheme.typography.bodySmall,
                    color = AppleGray400
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

@Composable
private fun EmptyState(message: String) {
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
            text = message,
            style = MaterialTheme.typography.bodyMedium,
            color = AppleGray400
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun BookStudentBottomSheet(
    book: BookInfo,
    bookClass: BookClassInfo,
    students: List<BookStudentRfid>,
    selectedStudents: Set<String>,
    isLoading: Boolean,
    onSelectStudent: (String) -> Unit,
    onSelectAll: () -> Unit,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit
) {
    val representativeCount = students.count { it.isRepresentative }
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
                        text = bookClass.name,
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "${students.size}人有卡" +
                            if (representativeCount > 0) "，${representativeCount}名课代表" else "",
                        style = MaterialTheme.typography.bodySmall,
                        color = AppleGray400
                    )
                }
                TextButton(onClick = onSelectAll) {
                    Text(
                        text = if (selectedCount == students.size) "取消全选" else "全选",
                        color = AppleBlue,
                        fontWeight = FontWeight.Medium
                    )
                }
            }

            // 书本信息
            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 12.dp),
                shape = RoundedCornerShape(8.dp),
                color = AppleBlue.copy(alpha = 0.06f)
            ) {
                Row(
                    modifier = Modifier.padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        Icons.Outlined.MenuBook,
                        contentDescription = null,
                        tint = AppleBlue,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = book.bookName,
                        style = MaterialTheme.typography.bodySmall,
                        color = AppleBlue,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }

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
                        .heightIn(max = 350.dp),
                    verticalArrangement = Arrangement.spacedBy(2.dp)
                ) {
                    items(students, key = { it.id }) { student ->
                        val isSelected = student.id in selectedStudents

                        Surface(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { onSelectStudent(student.id) },
                            shape = RoundedCornerShape(10.dp),
                            color = when {
                                isSelected -> AppleBlue.copy(alpha = 0.08f)
                                student.isRepresentative -> AppleOrange.copy(alpha = 0.06f)
                                else -> MaterialTheme.colorScheme.surface
                            }
                        ) {
                            Row(
                                modifier = Modifier.padding(12.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Checkbox(
                                    checked = isSelected,
                                    onCheckedChange = { onSelectStudent(student.id) },
                                    colors = CheckboxDefaults.colors(
                                        checkedColor = AppleBlack,
                                        uncheckedColor = AppleGray400
                                    )
                                )

                                Spacer(modifier = Modifier.width(8.dp))

                                Column(modifier = Modifier.weight(1f)) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Text(
                                            text = student.name,
                                            style = MaterialTheme.typography.bodyMedium,
                                            fontWeight = FontWeight.Medium
                                        )
                                        if (!student.stuNum.isNullOrBlank()) {
                                            Text(
                                                text = " ${student.stuNum}",
                                                style = MaterialTheme.typography.bodySmall,
                                                color = AppleGray400
                                            )
                                        }
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
                                        text = student.rfidNo,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = AppleBlue
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
                    text = if (selectedCount > 0) "开始模拟 $selectedCount 张卡片" else "请选择学生",
                    fontWeight = FontWeight.SemiBold
                )
            }
        }
    }
}
