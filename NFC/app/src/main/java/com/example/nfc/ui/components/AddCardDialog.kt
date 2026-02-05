package com.example.nfc.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import com.example.nfc.ui.theme.*

/**
 * 添加卡片对话框 - 遵循 ui-style.md 规范
 * 灰度系统、统一圆角、轻量阴影
 */
@Composable
fun AddCardDialog(
    onDismiss: () -> Unit,
    onConfirm: (name: String, cardNumber: String) -> Unit
) {
    var name by remember { mutableStateOf("") }
    var cardNumber by remember { mutableStateOf("") }
    var isError by remember { mutableStateOf(false) }

    Dialog(onDismissRequest = onDismiss) {
        Card(
            shape = RoundedCornerShape(Radius.xl),
            colors = CardDefaults.cardColors(containerColor = AppleWhite),
            elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
        ) {
            Column(
                modifier = Modifier
                    .padding(Spacing.lg)
                    .fillMaxWidth()
            ) {
                Text(
                    text = "添加新卡",
                    style = MaterialTheme.typography.headlineSmall,
                    color = AppleBlack
                )

                Spacer(modifier = Modifier.height(Spacing.lg))

                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("卡片名称", color = AppleGray500) },
                    placeholder = { Text("例如: 门禁卡1", color = AppleGray400) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(Radius.lg),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = AppleBlack,
                        unfocusedBorderColor = AppleGray200
                    )
                )

                Spacer(modifier = Modifier.height(Spacing.md))

                OutlinedTextField(
                    value = cardNumber,
                    onValueChange = { 
                        val filtered = it.uppercase().filter { c -> 
                            c in '0'..'9' || c in 'A'..'F' 
                        }
                        cardNumber = filtered
                        isError = false
                    },
                    label = { Text("卡号 (HEX)", color = AppleGray500) },
                    placeholder = { Text("例如: A1B2C3D4", color = AppleGray400) },
                    singleLine = true,
                    isError = isError,
                    supportingText = {
                        if (isError) {
                            Text("请输入有效的十六进制卡号 (偶数位)", color = AppleRed)
                        } else {
                            Text("输入十六进制格式的卡号", color = AppleGray400)
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(Radius.lg),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = AppleBlack,
                        unfocusedBorderColor = AppleGray200,
                        errorBorderColor = AppleRed
                    ),
                    keyboardOptions = KeyboardOptions(
                        capitalization = KeyboardCapitalization.Characters
                    )
                )

                Spacer(modifier = Modifier.height(Spacing.lg))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End
                ) {
                    TextButton(onClick = onDismiss) {
                        Text("取消", color = AppleGray500)
                    }
                    Spacer(modifier = Modifier.width(Spacing.sm))
                    Button(
                        onClick = {
                            if (name.isNotBlank() && cardNumber.length >= 2 && cardNumber.length % 2 == 0) {
                                onConfirm(name, cardNumber)
                            } else {
                                isError = true
                            }
                        },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = AppleBlack,
                            contentColor = AppleWhite
                        ),
                        shape = RoundedCornerShape(Radius.lg)
                    ) {
                        Text("添加")
                    }
                }
            }
        }
    }
}
