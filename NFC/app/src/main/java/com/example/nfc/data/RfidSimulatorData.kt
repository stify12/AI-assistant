package com.example.nfc.data

/**
 * RFID 模拟器数据模型
 */

/** ADB 客户端连接状态 */
data class AdbClientStatus(
    val connected: Boolean = false,
    val clientId: String? = null,
    val ipAddress: String? = null,
    val connectedAt: String? = null,
    val lastHeartbeat: String? = null,
    val deviceInfo: DeviceInfo? = null
)

/** 设备信息 */
data class DeviceInfo(
    val deviceIp: String? = null,
    val devicePath: String? = null,
    val model: String? = null,
    val connected: Boolean = false
)

/** 模拟任务状态 */
data class SimulationTaskStatus(
    val taskId: String? = null,
    val status: String = "idle",  // idle, running, paused, completed, stopped
    val totalCount: Int = 0,
    val currentIndex: Int = 0,
    val successCount: Int = 0,
    val failedCount: Int = 0,
    val intervalSeconds: Int = 5
)

/** RFID 批量配置 */
data class RfidBatchConfig(
    val intervalSeconds: Int = 5,
    val sendEnter: Boolean = true,
    val devicePath: String = "/dev/input/event2"
)

/** RFID 卡片（用于模拟器） */
data class RfidCard(
    val name: String,
    val cardNumber: String,
    val isSelected: Boolean = false
)

/** 日志条目 */
data class RfidLogEntry(
    val time: String,
    val level: String,  // info, success, warning, error
    val message: String,
    val data: Map<String, Any>? = null
)

/** 模拟器完整状态（API 返回） */
data class RfidSimulatorStatus(
    val connection: AdbClientStatus,
    val task: SimulationTaskStatus?
)
