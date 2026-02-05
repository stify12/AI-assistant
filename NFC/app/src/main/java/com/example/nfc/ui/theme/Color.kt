package com.example.nfc.ui.theme

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

// ========== 苹果风格灰度主题 ==========
// 遵循 ui-style.md 规范：简约高级、轻量质感

// 主色调 - 纯黑白
val AppleBlack = Color(0xFF1D1D1F)      // 主按钮、标题
val AppleWhite = Color(0xFFFFFFFF)      // 纯白

// 灰度系统 - 用深浅区分层次
val AppleGray50 = Color(0xFFF5F5F7)     // 页面背景
val AppleGray100 = Color(0xFFE8E8ED)    // 卡片悬停/激活背景
val AppleGray200 = Color(0xFFD2D2D7)    // 边框
val AppleGray300 = Color(0xFFC7C7CC)    // 分割线
val AppleGray400 = Color(0xFF86868B)    // 弱化文字/占位符
val AppleGray500 = Color(0xFF6E6E73)    // 正文/次要文字
val AppleGray600 = Color(0xFF636366)    // 中等强调
val AppleGray800 = Color(0xFF3A3A3C)    // 深灰/hover

// 状态色 - 仅用于状态指示，不用于大面积背景
val AppleGreen = Color(0xFF34C759)      // 成功/在线
val AppleRed = Color(0xFFFF3B30)        // 错误/离线
val AppleOrange = Color(0xFFFF9500)     // 警告/课代表标识

// 深色主题
val DarkSurface = Color(0xFF1C1C1E)
val DarkBackground = Color(0xFF000000)
val DarkCard = Color(0xFF2C2C2E)
val DarkGray = Color(0xFF48484A)

// 兼容旧代码 - 逐步迁移到灰度系统
val AppleBlue = Color(0xFF007AFF)       // 保留用于链接/特殊强调
val AppleBlueDark = Color(0xFF0056B3)
val AppleBlueLight = Color(0xFFF5F5F7)  // 改为灰色

val NfcBlue = AppleBlack                // 迁移：蓝色 → 黑色
val NfcGreen = AppleGreen
val NfcRed = AppleRed
val NfcOrange = AppleOrange
val NfcGray = AppleGray400

// 间距系统
object Spacing {
    val xs = 4.dp
    val sm = 8.dp
    val md = 16.dp
    val lg = 24.dp
    val xl = 32.dp
}

// 圆角系统
object Radius {
    val xs = 4.dp      // 标签、小按钮
    val sm = 6.dp      // 输入框、普通按钮
    val md = 8.dp      // 小卡片
    val lg = 12.dp     // 卡片、下拉框
    val xl = 16.dp     // 大卡片、弹窗
}

// 旧版颜色（保持兼容）
val Purple80 = Color(0xFFD0BCFF)
val PurpleGrey80 = Color(0xFFCCC2DC)
val Pink80 = Color(0xFFEFB8C8)
val Purple40 = Color(0xFF6650a4)
val PurpleGrey40 = Color(0xFF625b71)
val Pink40 = Color(0xFF7D5260)
