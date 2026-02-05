package com.example.nfc.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

/**
 * 苹果风格主题 - 遵循 ui-style.md 规范
 * 简约高级、轻量质感，灰度为主
 */

// 浅色主题 - 灰度系统
private val AppleLightScheme = lightColorScheme(
    // 主色 - 黑色
    primary = AppleBlack,
    onPrimary = AppleWhite,
    primaryContainer = AppleGray50,
    onPrimaryContainer = AppleBlack,
    // 次要色 - 深灰
    secondary = AppleGray800,
    onSecondary = AppleWhite,
    secondaryContainer = AppleGray100,
    onSecondaryContainer = AppleBlack,
    // 第三色 - 中灰
    tertiary = AppleGray500,
    onTertiary = AppleWhite,
    tertiaryContainer = AppleGray50,
    onTertiaryContainer = AppleGray500,
    // 背景
    background = AppleWhite,
    onBackground = AppleBlack,
    // 表面
    surface = AppleWhite,
    onSurface = AppleBlack,
    surfaceVariant = AppleGray50,
    onSurfaceVariant = AppleGray500,
    // 边框
    outline = AppleGray200,
    outlineVariant = AppleGray100,
    // 反转
    inverseSurface = AppleBlack,
    inverseOnSurface = AppleWhite,
    inversePrimary = AppleGray100
)

// 深色主题 - 灰度系统
private val AppleDarkScheme = darkColorScheme(
    primary = AppleWhite,
    onPrimary = AppleBlack,
    primaryContainer = DarkCard,
    onPrimaryContainer = AppleWhite,
    secondary = AppleGray400,
    onSecondary = AppleBlack,
    secondaryContainer = DarkGray,
    onSecondaryContainer = AppleWhite,
    tertiary = AppleGray400,
    onTertiary = AppleBlack,
    tertiaryContainer = DarkGray,
    onTertiaryContainer = AppleGray400,
    background = DarkBackground,
    onBackground = AppleWhite,
    surface = DarkSurface,
    onSurface = AppleWhite,
    surfaceVariant = DarkCard,
    onSurfaceVariant = AppleGray400,
    outline = DarkGray,
    outlineVariant = DarkGray,
    inverseSurface = AppleWhite,
    inverseOnSurface = AppleBlack,
    inversePrimary = AppleGray800
)

@Composable
fun NFCTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) AppleDarkScheme else AppleLightScheme
    
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = Color.Transparent.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
