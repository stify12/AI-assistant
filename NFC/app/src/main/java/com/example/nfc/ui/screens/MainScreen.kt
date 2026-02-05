package com.example.nfc.ui.screens

import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
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
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.nfc.data.BatchConfig
import com.example.nfc.data.CardGroup
import com.example.nfc.data.CardInfo
import com.example.nfc.data.LastUsedInfo
import com.example.nfc.data.LastUsedBookInfo
import com.example.nfc.data.RecentClassInfo
import com.example.nfc.ui.theme.*

/**
 * 主屏幕 - 遵循 ui-style.md 规范
 * 简约高级、灰度为主、有质感
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    cards: List<CardInfo>,
    cardGroups: List<CardGroup>,
    currentCard: CardInfo?,
    isNfcEnabled: Boolean,
    batchConfig: BatchConfig,
    remainingSeconds: Int,
    lastUsedClass: LastUsedInfo?,
    lastUsedBook: LastUsedBookInfo?,
    recentClasses: List<RecentClassInfo>,
    lastScannedTagId: String? = null,
    onAddCard: (String, String) -> Unit,
    onRemoveCard: (String) -> Unit,
    onSelectCard: (CardInfo) -> Unit,
    onToggleSelection: (String) -> Unit,
    onToggleGroupExpanded: (Long?) -> Unit,
    onSelectAllInGroup: (Long?, Boolean) -> Unit,
    onRemoveCardsByClass: (Long) -> Unit,
    onUpdateInterval: (Int) -> Unit,
    onStartBatch: () -> Unit,
    onPauseBatch: () -> Unit,
    onResumeBatch: () -> Unit,
    onStopBatch: () -> Unit,
    onQuickStart: () -> Unit,
    onQuickStartBook: () -> Unit,
    onQuickStartClass: (Long) -> Unit,
    onRefreshNfc: () -> Unit,
    onNavigateToDatabase: () -> Unit,
    onNavigateToBookSearch: () -> Unit,
    onNavigateToRfidSimulator: () -> Unit,
    onClearScannedTag: () -> Unit = {}
) {
    var showAddDialog by remember { mutableStateOf(false) }
    val selectedCount = cards.count { it.isSelected }

    Scaffold(
        containerColor = AppleGray50
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = PaddingValues(bottom = 100.dp)
        ) {
            // 顶部标题 + RFID 模拟入口
            item {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    color = AppleWhite,
                    shadowElevation = 1.dp
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = Spacing.lg, vertical = Spacing.md)
                    ) {
                        // 标题行
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(
                                    text = "NFC 卡片",
                                    style = MaterialTheme.typography.headlineLarge,
                                    fontWeight = FontWeight.Bold,
                                    color = AppleBlack
                                )
                                Spacer(modifier = Modifier.height(4.dp))
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Box(
                                        modifier = Modifier
                                            .size(8.dp)
                                            .clip(CircleShape)
                                            .background(if (isNfcEnabled) AppleGreen else AppleRed)
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text(
                                        text = if (isNfcEnabled) "NFC 已开启" else "NFC 未开启",
                                        style = MaterialTheme.typography.bodyMedium,
                                        color = AppleGray500
                                    )
                                }
                            }
                            // RFID 模拟快捷入口
                            Surface(
                                modifier = Modifier.clickable { onNavigateToRfidSimulator() },
                                shape = RoundedCornerShape(Radius.lg),
                                color = AppleBlack
                            ) {
                                Row(
                                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Icon(
                                        Icons.Default.Send,
                                        contentDescription = null,
                                        tint = AppleWhite,
                                        modifier = Modifier.size(18.dp)
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text(
                                        text = "RFID 模拟",
                                        style = MaterialTheme.typography.bodyMedium,
                                        fontWeight = FontWeight.SemiBold,
                                        color = AppleWhite
                                    )
                                }
                            }
                        }
                        
                        // 显示最近扫描到的卡片ID
                        if (lastScannedTagId != null) {
                            Spacer(modifier = Modifier.height(Spacing.md))
                            Surface(
                                shape = RoundedCornerShape(Radius.md),
                                color = AppleGray100,
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Row(
                                    modifier = Modifier.padding(Spacing.md),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Icon(
                                        Icons.Default.Nfc,
                                        contentDescription = null,
                                        tint = AppleBlack,
                                        modifier = Modifier.size(20.dp)
                                    )
                                    Spacer(modifier = Modifier.width(Spacing.sm))
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(
                                            text = "扫描到卡片",
                                            style = MaterialTheme.typography.bodySmall,
                                            color = AppleGray500
                                        )
                                        Text(
                                            text = lastScannedTagId,
                                            style = MaterialTheme.typography.bodyLarge,
                                            fontWeight = FontWeight.Medium,
                                            letterSpacing = 1.sp,
                                            color = AppleBlack
                                        )
                                    }
                                    IconButton(
                                        onClick = onClearScannedTag,
                                        modifier = Modifier.size(32.dp)
                                    ) {
                                        Icon(
                                            Icons.Default.Close,
                                            contentDescription = "清除",
                                            tint = AppleGray400,
                                            modifier = Modifier.size(16.dp)
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // 快捷操作卡片
            item {
                QuickActionCard(
                    lastUsedClass = lastUsedClass,
                    lastUsedBook = lastUsedBook,
                    recentClasses = recentClasses,
                    onQuickStart = onQuickStart,
                    onQuickStartBook = onQuickStartBook,
                    onQuickStartClass = onQuickStartClass,
                    onNavigateToDatabase = onNavigateToDatabase,
                    onNavigateToBookSearch = onNavigateToBookSearch
                )
            }

            // 批量模拟控制
            item {
                BatchControlCard(
                    batchConfig = batchConfig,
                    remainingSeconds = remainingSeconds,
                    currentCard = currentCard,
                    selectedCount = selectedCount,
                    onUpdateInterval = onUpdateInterval,
                    onStartBatch = onStartBatch,
                    onPauseBatch = onPauseBatch,
                    onResumeBatch = onResumeBatch,
                    onStopBatch = onStopBatch
                )
            }

            // 卡片分组列表
            if (cardGroups.isEmpty()) {
                item {
                    EmptyStateCard(
                        onAddCard = { showAddDialog = true },
                        onNavigateToDatabase = onNavigateToDatabase
                    )
                }
            } else {
                item {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = Spacing.lg, vertical = Spacing.md),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "卡片列表",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                            color = AppleBlack
                        )
                        Text(
                            text = "${cards.size} 张",
                            style = MaterialTheme.typography.bodyMedium,
                            color = AppleGray500
                        )
                    }
                }

                items(cardGroups, key = { it.classId ?: 0L }) { group ->
                    CardGroupItem(
                        group = group,
                        onToggleExpanded = { onToggleGroupExpanded(group.classId) },
                        onSelectAll = { selected -> onSelectAllInGroup(group.classId, selected) },
                        onRemoveGroup = { group.classId?.let { onRemoveCardsByClass(it) } },
                        onSelectCard = onSelectCard,
                        onToggleSelection = onToggleSelection,
                        onRemoveCard = onRemoveCard,
                        currentCard = currentCard
                    )
                }
            }

            // 底部操作按钮
            item {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(Spacing.lg),
                    verticalArrangement = Arrangement.spacedBy(Spacing.md)
                ) {
                    // 第一行：手动添加 + 从数据库
                    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.md)) {
                        OutlinedButton(
                            onClick = { showAddDialog = true },
                            modifier = Modifier.weight(1f).height(48.dp),
                            shape = RoundedCornerShape(Radius.lg),
                            colors = ButtonDefaults.outlinedButtonColors(
                                contentColor = AppleBlack
                            ),
                            border = ButtonDefaults.outlinedButtonBorder.copy(
                                brush = androidx.compose.ui.graphics.SolidColor(AppleGray200)
                            )
                        ) {
                            Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("手动添加", fontWeight = FontWeight.Medium)
                        }
                        Button(
                            onClick = onNavigateToDatabase,
                            modifier = Modifier.weight(1f).height(48.dp),
                            shape = RoundedCornerShape(Radius.lg),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = AppleBlack,
                                contentColor = AppleWhite
                            )
                        ) {
                            Icon(Icons.Default.CloudDownload, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("从数据库", fontWeight = FontWeight.Medium)
                        }
                    }
                    // 第二行：书本搜索
                    OutlinedButton(
                        onClick = onNavigateToBookSearch,
                        modifier = Modifier.fillMaxWidth().height(48.dp),
                        shape = RoundedCornerShape(Radius.lg),
                        colors = ButtonDefaults.outlinedButtonColors(
                            contentColor = AppleGray600
                        ),
                        border = ButtonDefaults.outlinedButtonBorder.copy(
                            brush = androidx.compose.ui.graphics.SolidColor(AppleGray200)
                        )
                    ) {
                        Icon(Icons.Outlined.MenuBook, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("书本搜索", fontWeight = FontWeight.Medium)
                    }
                }
            }
        }
    }

    // 添加卡片对话框
    if (showAddDialog) {
        AddCardDialog(
            onDismiss = { showAddDialog = false },
            onConfirm = { name, number ->
                onAddCard(name, number)
                showAddDialog = false
            }
        )
    }
}

@Composable
private fun QuickActionCard(
    lastUsedClass: LastUsedInfo?,
    lastUsedBook: LastUsedBookInfo?,
    recentClasses: List<RecentClassInfo>,
    onQuickStart: () -> Unit,
    onQuickStartBook: () -> Unit,
    onQuickStartClass: (Long) -> Unit,
    onNavigateToDatabase: () -> Unit,
    onNavigateToBookSearch: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = Spacing.lg, vertical = Spacing.sm),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm)
    ) {
        // 最近使用的班级（横向滚动）
        if (recentClasses.isNotEmpty()) {
            Text(
                text = "最近使用",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
                color = AppleBlack,
                modifier = Modifier.padding(bottom = 4.dp)
            )
            androidx.compose.foundation.lazy.LazyRow(
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                items(recentClasses.size) { index ->
                    val recent = recentClasses[index]
                    Surface(
                        modifier = Modifier.clickable { onQuickStartClass(recent.classId) },
                        shape = RoundedCornerShape(Radius.lg),
                        color = AppleWhite
                    ) {
                        Column(
                            modifier = Modifier.padding(horizontal = Spacing.md, vertical = Spacing.md),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Text(
                                text = recent.className,
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.Medium,
                                color = AppleBlack
                            )
                            Text(
                                text = "${recent.rfidCount}张卡",
                                style = MaterialTheme.typography.bodySmall,
                                color = AppleGray500
                            )
                        }
                    }
                }
            }
            Spacer(modifier = Modifier.height(4.dp))
        }

        // 上次使用的班级（主卡片）
        Card(
            shape = RoundedCornerShape(Radius.xl),
            colors = CardDefaults.cardColors(containerColor = AppleWhite),
            elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
        ) {
            if (lastUsedClass != null) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onQuickStart() }
                        .padding(20.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(48.dp)
                            .clip(CircleShape)
                            .background(AppleGray100),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            Icons.Default.PlayArrow,
                            contentDescription = null,
                            tint = AppleBlack,
                            modifier = Modifier.size(24.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(Spacing.md))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "继续上次",
                            style = MaterialTheme.typography.bodySmall,
                            color = AppleGray500
                        )
                        Text(
                            text = lastUsedClass.className,
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                            color = AppleBlack
                        )
                        Text(
                            text = "${lastUsedClass.studentCount} 张卡片",
                            style = MaterialTheme.typography.bodySmall,
                            color = AppleGray500
                        )
                    }
                    Icon(
                        Icons.Default.ChevronRight,
                        contentDescription = null,
                        tint = AppleGray400
                    )
                }
            } else {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onNavigateToDatabase() }
                        .padding(20.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(48.dp)
                            .clip(CircleShape)
                            .background(AppleGray100),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            Icons.Default.School,
                            contentDescription = null,
                            tint = AppleBlack,
                            modifier = Modifier.size(24.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(Spacing.md))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "开始使用",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                            color = AppleBlack
                        )
                        Text(
                            text = "从数据库选择班级导入卡片",
                            style = MaterialTheme.typography.bodySmall,
                            color = AppleGray500
                        )
                    }
                    Icon(
                        Icons.Default.ChevronRight,
                        contentDescription = null,
                        tint = AppleGray400
                    )
                }
            }
        }

        // 上次使用的书本
        if (lastUsedBook != null) {
            Card(
                shape = RoundedCornerShape(Radius.xl),
                colors = CardDefaults.cardColors(containerColor = AppleGray100),
                elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onQuickStartBook() }
                        .padding(Spacing.md),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(40.dp)
                            .clip(RoundedCornerShape(Radius.md))
                            .background(AppleGray200),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            Icons.Outlined.MenuBook,
                            contentDescription = null,
                            tint = AppleGray600,
                            modifier = Modifier.size(20.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(Spacing.md))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "上次书本",
                            style = MaterialTheme.typography.bodySmall,
                            color = AppleGray500
                        )
                        Text(
                            text = "${lastUsedBook.className} · ${lastUsedBook.bookName}",
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.Medium,
                            color = AppleBlack,
                            maxLines = 1,
                            overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis
                        )
                        Text(
                            text = "${lastUsedBook.studentCount} 张卡片",
                            style = MaterialTheme.typography.bodySmall,
                            color = AppleGray500
                        )
                    }
                    Icon(
                        Icons.Default.PlayArrow,
                        contentDescription = null,
                        tint = AppleGray600,
                        modifier = Modifier.size(20.dp)
                    )
                }
            }
        }
    }
}

@Composable
private fun BatchControlCard(
    batchConfig: BatchConfig,
    remainingSeconds: Int,
    currentCard: CardInfo?,
    selectedCount: Int,
    onUpdateInterval: (Int) -> Unit,
    onStartBatch: () -> Unit,
    onPauseBatch: () -> Unit,
    onResumeBatch: () -> Unit,
    onStopBatch: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = Spacing.lg, vertical = Spacing.sm),
        shape = RoundedCornerShape(Radius.xl),
        colors = CardDefaults.cardColors(
            containerColor = if (batchConfig.isRunning) AppleBlack else AppleWhite
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = if (batchConfig.isRunning) 4.dp else 0.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            if (batchConfig.isRunning) {
                // 运行中状态
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = if (batchConfig.isPaused) "已暂停" else "正在模拟",
                            style = MaterialTheme.typography.bodySmall,
                            color = if (batchConfig.isPaused) AppleOrange else AppleWhite.copy(alpha = 0.7f)
                        )
                        Text(
                            text = currentCard?.name ?: "",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            color = AppleWhite
                        )
                    }
                    // 进度显示
                    Column(horizontalAlignment = Alignment.End) {
                        Text(
                            text = "${batchConfig.currentIndex}/${batchConfig.totalCount}",
                            style = MaterialTheme.typography.headlineMedium,
                            fontWeight = FontWeight.Bold,
                            color = AppleWhite
                        )
                        Text(
                            text = if (batchConfig.isPaused) "暂停中" else "${remainingSeconds}s",
                            style = MaterialTheme.typography.bodyMedium,
                            color = if (batchConfig.isPaused) AppleOrange else AppleWhite.copy(alpha = 0.7f)
                        )
                    }
                }
                
                Spacer(modifier = Modifier.height(16.dp))
                
                // 进度条
                LinearProgressIndicator(
                    progress = { batchConfig.currentIndex.toFloat() / batchConfig.totalCount.coerceAtLeast(1) },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(4.dp)
                        .clip(RoundedCornerShape(2.dp)),
                    color = if (batchConfig.isPaused) AppleOrange else AppleWhite,
                    trackColor = AppleWhite.copy(alpha = 0.2f)
                )
                
                Spacer(modifier = Modifier.height(16.dp))
                
                // 卡号显示
                Text(
                    text = currentCard?.cardNumber ?: "",
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.Medium,
                    color = AppleWhite.copy(alpha = 0.9f),
                    modifier = Modifier.fillMaxWidth(),
                    textAlign = TextAlign.Center,
                    letterSpacing = 2.sp
                )
                
                Spacer(modifier = Modifier.height(16.dp))
                
                // 控制按钮：暂停/继续 + 停止
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    // 暂停/继续按钮
                    OutlinedButton(
                        onClick = if (batchConfig.isPaused) onResumeBatch else onPauseBatch,
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.outlinedButtonColors(
                            contentColor = AppleWhite
                        ),
                        border = ButtonDefaults.outlinedButtonBorder.copy(
                            brush = androidx.compose.ui.graphics.SolidColor(AppleWhite.copy(alpha = 0.5f))
                        )
                    ) {
                        Icon(
                            if (batchConfig.isPaused) Icons.Default.PlayArrow else Icons.Default.Pause,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(if (batchConfig.isPaused) "继续" else "暂停", fontWeight = FontWeight.SemiBold)
                    }
                    // 停止按钮
                    Button(
                        onClick = onStopBatch,
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = AppleWhite,
                            contentColor = AppleBlack
                        )
                    ) {
                        Text("停止", fontWeight = FontWeight.SemiBold)
                    }
                }
                
                // 完成统计（模拟完成后显示）
                if (!batchConfig.isRunning && batchConfig.successCount > 0) {
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = "完成 ${batchConfig.successCount} 张",
                        style = MaterialTheme.typography.bodySmall,
                        color = AppleGreen,
                        modifier = Modifier.fillMaxWidth(),
                        textAlign = TextAlign.Center
                    )
                }
            } else {
                // 待机状态
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "批量模拟",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        text = "已选 $selectedCount 张",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                
                Spacer(modifier = Modifier.height(16.dp))
                
                // 间隔设置（更多选项：1s, 3s, 5s, 10s）
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "切换间隔",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.weight(1f))
                    listOf(1, 3, 5, 10).forEach { sec ->
                        val isSelected = batchConfig.intervalSeconds == sec
                        Surface(
                            modifier = Modifier
                                .padding(start = 6.dp)
                                .clickable { onUpdateInterval(sec) },
                            shape = RoundedCornerShape(8.dp),
                            color = if (isSelected) AppleBlack else MaterialTheme.colorScheme.surfaceVariant
                        ) {
                            Text(
                                text = "${sec}s",
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Normal,
                                color = if (isSelected) AppleWhite else MaterialTheme.colorScheme.onSurface
                            )
                        }
                    }
                }
                
                Spacer(modifier = Modifier.height(16.dp))
                
                Button(
                    onClick = onStartBatch,
                    modifier = Modifier.fillMaxWidth(),
                    enabled = selectedCount > 0,
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = AppleBlack,
                        contentColor = AppleWhite
                    )
                ) {
                    Icon(Icons.Default.PlayArrow, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("开始模拟", fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
}

@Composable
private fun CardGroupItem(
    group: CardGroup,
    onToggleExpanded: () -> Unit,
    onSelectAll: (Boolean) -> Unit,
    onRemoveGroup: () -> Unit,
    onSelectCard: (CardInfo) -> Unit,
    onToggleSelection: (String) -> Unit,
    onRemoveCard: (String) -> Unit,
    currentCard: CardInfo?
) {
    val allSelected = group.cards.all { it.isSelected }
    val someSelected = group.cards.any { it.isSelected }

    Column(modifier = Modifier.padding(horizontal = 24.dp, vertical = 4.dp)) {
        // 分组标题
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .clickable { onToggleExpanded() },
            shape = RoundedCornerShape(12.dp),
            color = MaterialTheme.colorScheme.surfaceVariant
        ) {
            Row(
                modifier = Modifier.padding(16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Checkbox(
                    checked = allSelected,
                    onCheckedChange = { onSelectAll(!allSelected) },
                    colors = CheckboxDefaults.colors(
                        checkedColor = AppleBlack,
                        uncheckedColor = AppleGray400
                    )
                )
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = group.className,
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        text = "${group.cards.size} 张卡片",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                IconButton(onClick = onRemoveGroup) {
                    Icon(
                        Icons.Outlined.Delete,
                        contentDescription = "删除分组",
                        tint = AppleRed.copy(alpha = 0.7f)
                    )
                }
                Icon(
                    if (group.isExpanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }

        // 展开的卡片列表
        AnimatedVisibility(visible = group.isExpanded) {
            Column(modifier = Modifier.padding(start = 16.dp, top = 8.dp)) {
                group.cards.forEach { card ->
                    CardItem(
                        card = card,
                        isCurrent = currentCard?.id == card.id,
                        onSelect = { onSelectCard(card) },
                        onToggleSelection = { onToggleSelection(card.id) },
                        onRemove = { onRemoveCard(card.id) }
                    )
                }
            }
        }
    }
}

@Composable
private fun CardItem(
    card: CardInfo,
    isCurrent: Boolean,
    onSelect: () -> Unit,
    onToggleSelection: () -> Unit,
    onRemove: () -> Unit
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp)
            .clickable { onSelect() },
        shape = RoundedCornerShape(10.dp),
        color = if (isCurrent) AppleBlue.copy(alpha = 0.1f) else Color.Transparent
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Checkbox(
                checked = card.isSelected,
                onCheckedChange = { onToggleSelection() },
                colors = CheckboxDefaults.colors(
                    checkedColor = AppleBlack,
                    uncheckedColor = AppleGray400
                )
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = card.name,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = if (isCurrent) FontWeight.SemiBold else FontWeight.Normal
                )
                Text(
                    text = card.cardNumber,
                    style = MaterialTheme.typography.bodySmall,
                    color = if (isCurrent) AppleBlue else MaterialTheme.colorScheme.onSurfaceVariant,
                    letterSpacing = 1.sp
                )
            }
            if (isCurrent) {
                Box(
                    modifier = Modifier
                        .size(8.dp)
                        .clip(CircleShape)
                        .background(AppleGreen)
                )
            }
        }
    }
}

@Composable
private fun EmptyStateCard(
    onAddCard: () -> Unit,
    onNavigateToDatabase: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(48.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(
            Icons.Outlined.CreditCard,
            contentDescription = null,
            modifier = Modifier.size(64.dp),
            tint = AppleGray200
        )
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = "还没有卡片",
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = "从数据库导入班级学生卡片\n或手动添加卡片",
            style = MaterialTheme.typography.bodyMedium,
            color = AppleGray400,
            textAlign = TextAlign.Center
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AddCardDialog(
    onDismiss: () -> Unit,
    onConfirm: (String, String) -> Unit
) {
    var name by remember { mutableStateOf("") }
    var cardNumber by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("添加卡片", fontWeight = FontWeight.SemiBold) },
        text = {
            Column {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("名称") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(10.dp)
                )
                Spacer(modifier = Modifier.height(12.dp))
                OutlinedTextField(
                    value = cardNumber,
                    onValueChange = { cardNumber = it },
                    label = { Text("卡号") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(10.dp)
                )
            }
        },
        confirmButton = {
            Button(
                onClick = { if (name.isNotBlank() && cardNumber.isNotBlank()) onConfirm(name, cardNumber) },
                colors = ButtonDefaults.buttonColors(containerColor = AppleBlack)
            ) {
                Text("添加")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("取消", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    )
}
