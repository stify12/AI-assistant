package com.example.nfc.ui.components

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.CreditCard
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.nfc.data.CardInfo
import com.example.nfc.ui.theme.*

/**
 * 卡片项组件 - 遵循 ui-style.md 规范
 * 灰度系统、轻量阴影、统一圆角
 */
@Composable
fun CardItem(
    card: CardInfo,
    isCurrent: Boolean,
    onSelect: () -> Unit,
    onToggleSelection: () -> Unit,
    onDelete: () -> Unit,
    modifier: Modifier = Modifier
) {
    val scale by animateFloatAsState(if (isCurrent) 1.01f else 1f, label = "scale")
    val borderColor by animateColorAsState(
        if (isCurrent) AppleBlack else AppleGray200,
        label = "border"
    )

    Card(
        modifier = modifier
            .fillMaxWidth()
            .scale(scale)
            .border(if (isCurrent) 2.dp else 1.dp, borderColor, RoundedCornerShape(Radius.lg))
            .clickable { onSelect() },
        shape = RoundedCornerShape(Radius.lg),
        colors = CardDefaults.cardColors(
            containerColor = if (isCurrent) AppleGray100 else AppleWhite
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = if (isCurrent) 2.dp else 0.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(Spacing.md),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // 选择框
            Checkbox(
                checked = card.isSelected,
                onCheckedChange = { onToggleSelection() },
                colors = CheckboxDefaults.colors(
                    checkedColor = AppleBlack,
                    uncheckedColor = AppleGray400
                )
            )

            Spacer(modifier = Modifier.width(Spacing.sm))

            // 卡片图标
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clip(CircleShape)
                    .background(if (isCurrent) AppleBlack.copy(alpha = 0.1f) else AppleGray100),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.CreditCard,
                    contentDescription = null,
                    tint = if (isCurrent) AppleBlack else AppleGray500,
                    modifier = Modifier.size(22.dp)
                )
            }

            Spacer(modifier = Modifier.width(Spacing.md))

            // 卡片信息
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = card.name,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = AppleBlack
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = formatCardNumber(card.cardNumber),
                    style = MaterialTheme.typography.bodyMedium,
                    fontFamily = FontFamily.Monospace,
                    color = AppleGray500,
                    letterSpacing = 1.sp
                )
            }

            // 当前状态指示
            if (isCurrent) {
                Box(
                    modifier = Modifier
                        .size(28.dp)
                        .clip(CircleShape)
                        .background(AppleGreen),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Check,
                        contentDescription = "当前卡",
                        tint = AppleWhite,
                        modifier = Modifier.size(16.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.width(Spacing.sm))

            // 删除按钮
            IconButton(
                onClick = onDelete,
                modifier = Modifier.size(36.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Delete,
                    contentDescription = "删除",
                    tint = AppleGray400,
                    modifier = Modifier.size(20.dp)
                )
            }
        }
    }
}

private fun formatCardNumber(number: String): String {
    return number.chunked(2).joinToString(" ")
}
