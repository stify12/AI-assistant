package com.example.nfc.service

import android.nfc.cardemulation.HostApduService
import android.os.Bundle
import android.util.Log

class NfcHceService : HostApduService() {

    companion object {
        private const val TAG = "NfcHceService"
        
        // APDU 命令常量
        private val SELECT_AID_HEADER = byteArrayOf(0x00, 0xA4.toByte(), 0x04, 0x00)
        private val GET_DATA_COMMAND = byteArrayOf(0x00, 0xCA.toByte(), 0x00, 0x00)
        
        // 响应状态码
        private val SUCCESS_SW = byteArrayOf(0x90.toByte(), 0x00)
        private val UNKNOWN_CMD_SW = byteArrayOf(0x00, 0x00)
        
        // 当前模拟的卡号 (可被外部修改)
        @Volatile
        var currentCardNumber: String = "00000000"
            set(value) {
                field = value
                Log.d(TAG, "Card number updated to: $value")
            }
    }

    override fun processCommandApdu(commandApdu: ByteArray, extras: Bundle?): ByteArray {
        Log.d(TAG, "Received APDU: ${commandApdu.toHexString()}")
        
        return when {
            isSelectAidCommand(commandApdu) -> {
                Log.d(TAG, "SELECT AID command received")
                SUCCESS_SW
            }
            isGetDataCommand(commandApdu) -> {
                Log.d(TAG, "GET DATA command - returning card: $currentCardNumber")
                buildCardResponse()
            }
            else -> {
                // 默认返回卡号数据
                Log.d(TAG, "Unknown command - returning card data")
                buildCardResponse()
            }
        }
    }

    override fun onDeactivated(reason: Int) {
        Log.d(TAG, "Deactivated: ${if (reason == DEACTIVATION_LINK_LOSS) "Link Loss" else "Deselected"}")
    }

    private fun isSelectAidCommand(apdu: ByteArray): Boolean {
        return apdu.size >= 4 && 
               apdu[0] == SELECT_AID_HEADER[0] && 
               apdu[1] == SELECT_AID_HEADER[1] &&
               apdu[2] == SELECT_AID_HEADER[2]
    }

    private fun isGetDataCommand(apdu: ByteArray): Boolean {
        return apdu.size >= 4 &&
               apdu[0] == GET_DATA_COMMAND[0] &&
               apdu[1] == GET_DATA_COMMAND[1]
    }

    private fun buildCardResponse(): ByteArray {
        // 支持十进制和十六进制卡号
        val cardBytes = cardNumberToBytes(currentCardNumber)
        Log.d(TAG, "Card bytes: ${cardBytes.toHexString()}")
        return cardBytes + SUCCESS_SW
    }

    /** 将卡号转换为字节数组（支持十进制和十六进制） */
    private fun cardNumberToBytes(cardNumber: String): ByteArray {
        val cleanNumber = cardNumber.replace(" ", "").replace(":", "")
        
        // 判断是否为十进制数字
        return if (cleanNumber.all { it.isDigit() } && cleanNumber.length > 8) {
            // 十进制卡号，转换为4字节（小端序，与常见读卡器兼容）
            try {
                val num = cleanNumber.toLong()
                byteArrayOf(
                    (num and 0xFF).toByte(),
                    ((num shr 8) and 0xFF).toByte(),
                    ((num shr 16) and 0xFF).toByte(),
                    ((num shr 24) and 0xFF).toByte()
                )
            } catch (e: Exception) {
                Log.e(TAG, "Failed to parse decimal card number: $cardNumber")
                byteArrayOf(0, 0, 0, 0)
            }
        } else {
            // 十六进制卡号
            hexStringToByteArray(cleanNumber)
        }
    }

    private fun hexStringToByteArray(hex: String): ByteArray {
        val cleanHex = hex.replace(" ", "").replace(":", "")
        val len = cleanHex.length
        val data = ByteArray(len / 2)
        var i = 0
        while (i < len) {
            data[i / 2] = ((Character.digit(cleanHex[i], 16) shl 4) +
                    Character.digit(cleanHex[i + 1], 16)).toByte()
            i += 2
        }
        return data
    }

    private fun ByteArray.toHexString(): String {
        return joinToString(" ") { "%02X".format(it) }
    }
}
