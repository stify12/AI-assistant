package com.example.nfc.data

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

// 导入 RFID 模拟器数据类
import com.example.nfc.data.AdbClientStatus
import com.example.nfc.data.SimulationTaskStatus
import com.example.nfc.data.RfidLogEntry

/**
 * 数据库仓库 - 通过 HTTP API 获取班级/学生/RFID 数据
 * 注意：Android 不支持 JDBC，必须通过 HTTP 接口访问数据库
 */
object DatabaseRepository {
    
    private const val TAG = "DatabaseRepository"
    
    // API 基础地址（你的后端服务器）
    private const val BASE_URL = "http://47.82.64.147:5000"
    
    /** 通用 HTTP GET 请求 */
    private suspend fun httpGet(endpoint: String): String = withContext(Dispatchers.IO) {
        val url = URL("$BASE_URL$endpoint")
        val connection = url.openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "GET"
            connection.connectTimeout = 10000  // 10秒连接超时
            connection.readTimeout = 10000     // 10秒读取超时
            connection.setRequestProperty("Content-Type", "application/json")
            connection.setRequestProperty("Connection", "keep-alive")  // 保持连接
            
            val responseCode = connection.responseCode
            if (responseCode == HttpURLConnection.HTTP_OK) {
                BufferedReader(InputStreamReader(connection.inputStream)).use { reader ->
                    reader.readText()
                }
            } else {
                throw Exception("HTTP $responseCode")
            }
        } finally {
            connection.disconnect()
        }
    }
    
    /** 通用 HTTP POST 请求 */
    private suspend fun httpPost(endpoint: String, body: JSONObject): String = withContext(Dispatchers.IO) {
        val url = URL("$BASE_URL$endpoint")
        val connection = url.openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "POST"
            connection.doOutput = true
            connection.connectTimeout = 10000  // 10秒连接超时
            connection.readTimeout = 10000     // 10秒读取超时
            connection.setRequestProperty("Content-Type", "application/json")
            connection.setRequestProperty("Connection", "keep-alive")  // 保持连接
            
            OutputStreamWriter(connection.outputStream).use { writer ->
                writer.write(body.toString())
                writer.flush()
            }
            
            val responseCode = connection.responseCode
            if (responseCode == HttpURLConnection.HTTP_OK) {
                BufferedReader(InputStreamReader(connection.inputStream)).use { reader ->
                    reader.readText()
                }
            } else {
                throw Exception("HTTP $responseCode")
            }
        } finally {
            connection.disconnect()
        }
    }

    /** 获取所有年级列表 */
    suspend fun getGrades(): Result<List<GradeInfo>> = withContext(Dispatchers.IO) {
        try {
            val response = httpGet("/api/nfc/grades")
            val json = JSONObject(response)
            
            if (json.optBoolean("success", false)) {
                val data = json.getJSONArray("data")
                val grades = mutableListOf<GradeInfo>()
                for (i in 0 until data.length()) {
                    val item = data.getJSONObject(i)
                    grades.add(GradeInfo(
                        id = item.getInt("id"),
                        name = item.getString("name")
                    ))
                }
                Result.success(grades)
            } else {
                Result.failure(Exception(json.optString("error", "获取年级失败")))
            }
        } catch (e: Exception) {
            Log.e(TAG, "获取年级失败: ${e.message}")
            // 返回默认年级列表（离线模式）
            Result.success(listOf(
                GradeInfo(1, "一年级"), GradeInfo(2, "二年级"), GradeInfo(3, "三年级"),
                GradeInfo(4, "四年级"), GradeInfo(5, "五年级"), GradeInfo(6, "六年级"),
                GradeInfo(7, "七年级"), GradeInfo(8, "八年级"), GradeInfo(9, "九年级"),
                GradeInfo(10, "高一"), GradeInfo(11, "高二"), GradeInfo(12, "高三")
            ))
        }
    }
    
    /** 获取老师列表 */
    suspend fun getTeachers(): Result<List<TeacherInfo>> = withContext(Dispatchers.IO) {
        try {
            val response = httpGet("/api/nfc/teachers")
            val json = JSONObject(response)
            
            if (json.optBoolean("success", false)) {
                val data = json.getJSONArray("data")
                val teachers = mutableListOf<TeacherInfo>()
                for (i in 0 until data.length()) {
                    val item = data.getJSONObject(i)
                    teachers.add(TeacherInfo(
                        id = item.getLong("id"),
                        name = item.getString("name"),
                        subjectId = item.optInt("subject_id", 0)
                    ))
                }
                Result.success(teachers)
            } else {
                Result.failure(Exception(json.optString("error", "获取老师失败")))
            }
        } catch (e: Exception) {
            Log.e(TAG, "获取老师失败: ${e.message}")
            Result.success(emptyList())
        }
    }
    
    /** 获取班级列表（支持筛选） */
    suspend fun getClasses(
        gradeId: Int? = null,
        teacherId: Long? = null,
        keyword: String = ""
    ): Result<List<ClassInfo>> = withContext(Dispatchers.IO) {
        try {
            val params = mutableListOf<String>()
            if (gradeId != null && gradeId > 0) params.add("grade=$gradeId")
            if (teacherId != null && teacherId > 0) params.add("teacher_id=$teacherId")
            if (keyword.isNotBlank()) params.add("keyword=${java.net.URLEncoder.encode(keyword, "UTF-8")}")
            
            val queryString = if (params.isNotEmpty()) "?" + params.joinToString("&") else ""
            val response = httpGet("/api/nfc/classes$queryString")
            val json = JSONObject(response)
            
            if (json.optBoolean("success", false)) {
                val data = json.getJSONArray("data")
                val classes = mutableListOf<ClassInfo>()
                for (i in 0 until data.length()) {
                    val item = data.getJSONObject(i)
                    val grade = item.optInt("grade", 0)
                    classes.add(ClassInfo(
                        id = item.getLong("id"),
                        name = item.getString("name"),
                        grade = grade,
                        gradeName = GradeInfo.GRADE_MAP[grade] ?: "${grade}年级",
                        studentCount = item.optInt("student_count", 0),
                        rfidCount = item.optInt("rfid_count", 0),
                        teacherId = item.optString("teacher_id", null)
                    ))
                }
                Result.success(classes)
            } else {
                Result.failure(Exception(json.optString("error", "获取班级失败")))
            }
        } catch (e: Exception) {
            Log.e(TAG, "获取班级失败: ${e.message}")
            Result.failure(e)
        }
    }
    
    /** 获取班级学生及其 RFID */
    suspend fun getClassStudentsWithRfid(classId: Long): Result<List<StudentInfo>> = withContext(Dispatchers.IO) {
        try {
            val response = httpGet("/api/nfc/class/$classId/students")
            val json = JSONObject(response)
            
            if (json.optBoolean("success", false)) {
                val data = json.getJSONArray("data")
                val students = mutableListOf<StudentInfo>()
                for (i in 0 until data.length()) {
                    val item = data.getJSONObject(i)
                    students.add(StudentInfo(
                        id = item.getLong("id"),
                        name = item.getString("name"),
                        stuNum = item.optString("stu_num", null),
                        sex = item.optInt("sex", 0),
                        classId = item.optLong("class_id", classId),
                        className = item.optString("class_name", null),
                        rfidNo = item.optString("rfid_no", null).takeIf { it != "null" && it.isNotBlank() },
                        isRepresentative = item.optBoolean("is_representative", false),
                        subjectId = item.optString("subject_id", null).takeIf { it != "null" && it.isNotBlank() },
                        subjectName = item.optString("subject_name", null).takeIf { it != "null" && it.isNotBlank() }
                    ))
                }
                Result.success(students)
            } else {
                Result.failure(Exception(json.optString("error", "获取学生失败")))
            }
        } catch (e: Exception) {
            Log.e(TAG, "获取学生失败: ${e.message}")
            Result.failure(e)
        }
    }
    
    /** 测试连接 */
    suspend fun testConnection(): Result<Boolean> = withContext(Dispatchers.IO) {
        try {
            val response = httpGet("/api/nfc/ping")
            val json = JSONObject(response)
            Result.success(json.optBoolean("success", false))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    // ========== 书本相关 API ==========
    
    /** 搜索书本（支持科目筛选） */
    suspend fun searchBooks(
        keyword: String = "",
        subjectId: Int? = null
    ): Result<List<BookInfo>> = withContext(Dispatchers.IO) {
        try {
            val params = mutableListOf<String>()
            if (keyword.isNotBlank()) {
                params.add("keyword=${java.net.URLEncoder.encode(keyword, "UTF-8")}")
            }
            if (subjectId != null) {
                params.add("subject_id=$subjectId")
            }
            
            val queryString = if (params.isNotEmpty()) "?" + params.joinToString("&") else ""
            val response = httpGet("/api/nfc/books$queryString")
            val json = JSONObject(response)
            
            if (json.optBoolean("success", false)) {
                val data = json.getJSONArray("data")
                val books = mutableListOf<BookInfo>()
                for (i in 0 until data.length()) {
                    val item = data.getJSONObject(i)
                    books.add(BookInfo(
                        id = item.getString("id"),
                        bookSn = item.optString("book_sn", null),
                        bookName = item.getString("book_name"),
                        subjectId = item.optInt("subject_id", -1).takeIf { it >= 0 },
                        subjectName = item.optString("subject_name", null).takeIf { it.isNotBlank() },
                        gradeId = item.optInt("grade_id", -1).takeIf { it >= 0 },
                        gradeName = item.optString("grade_name", null).takeIf { it.isNotBlank() },
                        publishing = item.optString("publishing", null).takeIf { it.isNotBlank() }
                    ))
                }
                Result.success(books)
            } else {
                Result.failure(Exception(json.optString("error", "搜索书本失败")))
            }
        } catch (e: Exception) {
            Log.e(TAG, "搜索书本失败: ${e.message}")
            Result.failure(e)
        }
    }
    
    /** 获取书本关联的班级 */
    suspend fun getBookClasses(bookId: String): Result<List<BookClassInfo>> = withContext(Dispatchers.IO) {
        try {
            val response = httpGet("/api/nfc/book/$bookId/classes")
            val json = JSONObject(response)
            
            if (json.optBoolean("success", false)) {
                val data = json.getJSONArray("data")
                val classes = mutableListOf<BookClassInfo>()
                for (i in 0 until data.length()) {
                    val item = data.getJSONObject(i)
                    classes.add(BookClassInfo(
                        id = item.getString("id"),
                        name = item.getString("name"),
                        gradeId = item.optInt("grade_id", -1).takeIf { it >= 0 },
                        gradeName = item.optString("grade_name", null).takeIf { it.isNotBlank() },
                        studentCount = item.optInt("student_count", 0)
                    ))
                }
                Result.success(classes)
            } else {
                Result.failure(Exception(json.optString("error", "获取班级失败")))
            }
        } catch (e: Exception) {
            Log.e(TAG, "获取书本班级失败: ${e.message}")
            Result.failure(e)
        }
    }
    
    /** 获取班级学生的书本RFID */
    suspend fun getBookClassStudents(
        bookId: String,
        classId: String
    ): Result<List<BookStudentRfid>> = withContext(Dispatchers.IO) {
        try {
            val response = httpGet("/api/nfc/book/$bookId/class/$classId/students")
            val json = JSONObject(response)
            
            if (json.optBoolean("success", false)) {
                val data = json.getJSONArray("data")
                val students = mutableListOf<BookStudentRfid>()
                for (i in 0 until data.length()) {
                    val item = data.getJSONObject(i)
                    students.add(BookStudentRfid(
                        id = item.getString("id"),
                        name = item.getString("name"),
                        stuNum = item.optString("stu_num", null).takeIf { it.isNotBlank() },
                        className = item.optString("class_name", null).takeIf { it.isNotBlank() },
                        rfidNo = item.getString("rfid_no"),
                        isRepresentative = item.optBoolean("is_representative", false),
                        subjectName = item.optString("subject_name", null).takeIf { it.isNotBlank() }
                    ))
                }
                Result.success(students)
            } else {
                Result.failure(Exception(json.optString("error", "获取学生失败")))
            }
        } catch (e: Exception) {
            Log.e(TAG, "获取书本学生失败: ${e.message}")
            Result.failure(e)
        }
    }
    
    // ========== RFID 模拟器 API ==========
    
    /** RFID 模拟器状态响应 */
    data class RfidSimulatorStatusResponse(
        val connection: AdbClientStatus,
        val task: SimulationTaskStatus?
    )
    
    /** 获取 RFID 模拟器状态 */
    suspend fun getRfidSimulatorStatus(): Result<RfidSimulatorStatusResponse> = withContext(Dispatchers.IO) {
        try {
            val response = httpGet("/api/rfid-simulator/status")
            val json = JSONObject(response)
            
            if (json.optBoolean("success", false)) {
                val data = json.getJSONObject("data")
                
                // 服务端返回: { connected: bool, client: {...}, task: {...} }
                val clientJson = data.optJSONObject("client")
                val taskJson = data.optJSONObject("task")
                
                val connection = AdbClientStatus(
                    connected = data.optBoolean("connected", false),
                    clientId = clientJson?.optString("client_id"),
                    ipAddress = clientJson?.optString("ip_address"),
                    connectedAt = clientJson?.optString("connected_at"),
                    lastHeartbeat = clientJson?.optString("last_heartbeat")
                )
                
                val task = if (taskJson != null && taskJson.has("task_id")) {
                    SimulationTaskStatus(
                        taskId = taskJson.optString("task_id"),
                        totalCount = taskJson.optInt("total_count", 0),
                        currentIndex = taskJson.optInt("current_index", 0),
                        successCount = taskJson.optInt("success_count", 0),
                        failedCount = taskJson.optInt("failed_count", 0),
                        status = taskJson.optString("status", "idle"),
                        intervalSeconds = taskJson.optInt("interval_seconds", 5)
                    )
                } else null
                
                Result.success(RfidSimulatorStatusResponse(connection, task))
            } else {
                Result.failure(Exception(json.optString("error", "获取状态失败")))
            }
        } catch (e: Exception) {
            Log.e(TAG, "获取 RFID 模拟器状态失败: ${e.message}")
            Result.failure(e)
        }
    }
    
    /** 获取 RFID 模拟器日志 */
    suspend fun getRfidSimulatorLogs(limit: Int = 50): Result<List<RfidLogEntry>> = withContext(Dispatchers.IO) {
        try {
            val response = httpGet("/api/rfid-simulator/logs?limit=$limit")
            val json = JSONObject(response)
            
            if (json.optBoolean("success", false)) {
                val data = json.getJSONArray("data")
                val logs = mutableListOf<RfidLogEntry>()
                for (i in 0 until data.length()) {
                    val item = data.getJSONObject(i)
                    logs.add(RfidLogEntry(
                        time = item.optString("time", ""),
                        level = item.optString("level", "info"),
                        message = item.optString("message", "")
                    ))
                }
                Result.success(logs)
            } else {
                Result.failure(Exception(json.optString("error", "获取日志失败")))
            }
        } catch (e: Exception) {
            Log.e(TAG, "获取 RFID 日志失败: ${e.message}")
            Result.failure(e)
        }
    }
    
    /** 清空 RFID 模拟器日志 */
    suspend fun clearRfidLogs(): Result<Boolean> = withContext(Dispatchers.IO) {
        try {
            val url = URL("$BASE_URL/api/rfid-simulator/logs")
            val connection = url.openConnection() as HttpURLConnection
            try {
                connection.requestMethod = "DELETE"
                connection.connectTimeout = 10000
                connection.readTimeout = 10000
                val responseCode = connection.responseCode
                Result.success(responseCode == HttpURLConnection.HTTP_OK)
            } finally {
                connection.disconnect()
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /** 测试 RFID 连接 */
    suspend fun testRfidConnection(): Result<Boolean> = withContext(Dispatchers.IO) {
        try {
            val response = httpPost("/api/rfid-simulator/test-connection", JSONObject())
            val json = JSONObject(response)
            if (json.optBoolean("success", false)) {
                Result.success(true)
            } else {
                Result.failure(Exception(json.optString("error", "测试连接失败")))
            }
        } catch (e: Exception) {
            Log.e(TAG, "测试 RFID 连接失败: ${e.message}")
            Result.failure(e)
        }
    }
    
    /** 检测 RFID 设备 */
    suspend fun detectRfidDevice(): Result<Boolean> = withContext(Dispatchers.IO) {
        try {
            val response = httpPost("/api/rfid-simulator/detect-device", JSONObject())
            val json = JSONObject(response)
            if (json.optBoolean("success", false)) {
                Result.success(true)
            } else {
                Result.failure(Exception(json.optString("error", "检测设备失败")))
            }
        } catch (e: Exception) {
            Log.e(TAG, "检测 RFID 设备失败: ${e.message}")
            Result.failure(e)
        }
    }
    
    /** 发送单个 RFID */
    suspend fun sendRfid(
        rfidCode: String,
        devicePath: String = "/dev/input/event2",
        sendEnter: Boolean = true
    ): Result<Boolean> = withContext(Dispatchers.IO) {
        try {
            val body = JSONObject().apply {
                put("rfid_code", rfidCode)
                put("device_path", devicePath)
                put("send_enter", sendEnter)
            }
            val response = httpPost("/api/rfid-simulator/send", body)
            val json = JSONObject(response)
            if (json.optBoolean("success", false)) {
                Result.success(true)
            } else {
                Result.failure(Exception(json.optString("error", "发送失败")))
            }
        } catch (e: Exception) {
            Log.e(TAG, "发送 RFID 失败: ${e.message}")
            Result.failure(e)
        }
    }
    
    /** 开始批量模拟 */
    suspend fun startRfidBatch(
        cards: List<Map<String, String>>,
        intervalSeconds: Int = 5,
        sendEnter: Boolean = true,
        devicePath: String = "/dev/input/event2"
    ): Result<SimulationTaskStatus> = withContext(Dispatchers.IO) {
        try {
            val cardsArray = JSONArray()
            cards.forEach { card ->
                cardsArray.put(JSONObject().apply {
                    put("name", card["name"])
                    put("card_number", card["card_number"])
                })
            }
            
            val body = JSONObject().apply {
                put("cards", cardsArray)
                put("interval_seconds", intervalSeconds)
                put("send_enter", sendEnter)
                put("device_path", devicePath)
            }
            
            val response = httpPost("/api/rfid-simulator/batch/start", body)
            val json = JSONObject(response)
            
            if (json.optBoolean("success", false)) {
                val data = json.getJSONObject("data")
                Result.success(SimulationTaskStatus(
                    taskId = data.optString("task_id"),
                    totalCount = data.optInt("total_count", 0),
                    currentIndex = data.optInt("current_index", 0),
                    successCount = data.optInt("success_count", 0),
                    failedCount = data.optInt("failed_count", 0),
                    status = data.optString("status", "pending"),
                    intervalSeconds = data.optInt("interval_seconds", intervalSeconds)
                ))
            } else {
                Result.failure(Exception(json.optString("error", "启动批量模拟失败")))
            }
        } catch (e: Exception) {
            Log.e(TAG, "启动批量模拟失败: ${e.message}")
            Result.failure(e)
        }
    }
    
    /** 暂停批量模拟 */
    suspend fun pauseRfidBatch(): Result<Boolean> = withContext(Dispatchers.IO) {
        try {
            val response = httpPost("/api/rfid-simulator/batch/pause", JSONObject())
            val json = JSONObject(response)
            Result.success(json.optBoolean("success", false))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /** 恢复批量模拟 */
    suspend fun resumeRfidBatch(): Result<Boolean> = withContext(Dispatchers.IO) {
        try {
            val response = httpPost("/api/rfid-simulator/batch/resume", JSONObject())
            val json = JSONObject(response)
            Result.success(json.optBoolean("success", false))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /** 停止批量模拟 */
    suspend fun stopRfidBatch(): Result<Boolean> = withContext(Dispatchers.IO) {
        try {
            val response = httpPost("/api/rfid-simulator/batch/stop", JSONObject())
            val json = JSONObject(response)
            Result.success(json.optBoolean("success", false))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /** 执行自动化流程 */
    suspend fun runWorkflow(
        workflowId: String,
        params: Map<String, Any> = emptyMap(),
        students: List<Map<String, String>> = emptyList(),
        representative: Map<String, String>? = null
    ): Result<Boolean> = withContext(Dispatchers.IO) {
        try {
            val paramsJson = JSONObject()
            params.forEach { (key, value) ->
                paramsJson.put(key, value)
            }
            
            val studentsArray = JSONArray()
            students.forEach { student ->
                studentsArray.put(JSONObject().apply {
                    student.forEach { (k, v) -> put(k, v) }
                })
            }
            
            val body = JSONObject().apply {
                put("params", paramsJson)
                put("students", studentsArray)
                representative?.let { rep ->
                    put("representative", JSONObject().apply {
                        rep.forEach { (k, v) -> put(k, v) }
                    })
                }
            }
            
            val response = httpPost("/api/rfid-simulator/workflows/$workflowId/run", body)
            val json = JSONObject(response)
            
            if (json.optBoolean("success", false)) {
                Result.success(true)
            } else {
                Result.failure(Exception(json.optString("error", "执行流程失败")))
            }
        } catch (e: Exception) {
            Log.e(TAG, "执行流程失败: ${e.message}")
            Result.failure(e)
        }
    }
    
    // ========== 智能发布 API ==========
    
    /** 获取智能发布书本列表 */
    suspend fun getSmartPublishBooks(): Result<List<SmartPublishBook>> = withContext(Dispatchers.IO) {
        try {
            val response = httpGet("/api/smart-publish/books")
            val json = JSONObject(response)
            
            if (json.optBoolean("success", false)) {
                val data = json.getJSONArray("data")
                val books = mutableListOf<SmartPublishBook>()
                for (i in 0 until data.length()) {
                    val item = data.getJSONObject(i)
                    books.add(SmartPublishBook(
                        id = item.getString("id"),
                        bookName = item.getString("book_name"),
                        subjectId = item.optInt("subject_id", -1).takeIf { it >= 0 },
                        subjectName = item.optString("subject_name", null).takeIf { it.isNotBlank() },
                        gradeId = item.optInt("grade_id", -1).takeIf { it >= 0 }
                    ))
                }
                Result.success(books)
            } else {
                Result.failure(Exception(json.optString("error", "获取书本失败")))
            }
        } catch (e: Exception) {
            Log.e(TAG, "获取智能发布书本失败: ${e.message}")
            Result.failure(e)
        }
    }
    
    /** 根据书本获取老师列表 */
    suspend fun getSmartPublishTeachers(bookId: String): Result<SmartPublishTeachersResponse> = withContext(Dispatchers.IO) {
        try {
            val response = httpGet("/api/smart-publish/teachers?book_id=$bookId")
            val json = JSONObject(response)
            
            if (json.optBoolean("success", false)) {
                val data = json.getJSONObject("data")
                val teachersArray = data.getJSONArray("teachers")
                val teachers = mutableListOf<SmartPublishTeacher>()
                
                for (i in 0 until teachersArray.length()) {
                    val item = teachersArray.getJSONObject(i)
                    teachers.add(SmartPublishTeacher(
                        id = item.getString("id"),
                        teacherName = item.getString("teacher_name"),
                        classId = item.getString("class_id"),
                        className = item.getString("class_name"),
                        gradeId = item.optString("grade_id", null),
                        subjectId = item.optInt("subject_id", -1).takeIf { it >= 0 }
                    ))
                }
                
                val selectedTeacherJson = data.optJSONObject("selected_teacher")
                val selectedTeacher = if (selectedTeacherJson != null) {
                    SmartPublishTeacher(
                        id = selectedTeacherJson.getString("id"),
                        teacherName = selectedTeacherJson.getString("teacher_name"),
                        classId = selectedTeacherJson.getString("class_id"),
                        className = selectedTeacherJson.getString("class_name"),
                        gradeId = selectedTeacherJson.optString("grade_id", null),
                        subjectId = selectedTeacherJson.optInt("subject_id", -1).takeIf { it >= 0 }
                    )
                } else null
                
                Result.success(SmartPublishTeachersResponse(
                    teachers = teachers,
                    needSelect = data.optBoolean("need_select", false),
                    selectedTeacher = selectedTeacher
                ))
            } else {
                Result.failure(Exception(json.optString("error", "获取老师失败")))
            }
        } catch (e: Exception) {
            Log.e(TAG, "获取智能发布老师失败: ${e.message}")
            Result.failure(e)
        }
    }
    
    /** 智能发布作业 */
    suspend fun smartPublish(
        bookId: String,
        teacherId: String,
        classId: String,
        pages: String
    ): Result<SmartPublishResult> = withContext(Dispatchers.IO) {
        try {
            val body = JSONObject().apply {
                put("book_id", bookId)
                put("teacher_id", teacherId)
                put("class_id", classId)
                put("pages", pages)
            }
            
            val response = httpPost("/api/smart-publish/publish", body)
            val json = JSONObject(response)
            
            if (json.optBoolean("success", false)) {
                val data = json.getJSONObject("data")
                Result.success(SmartPublishResult(
                    homeworkName = data.getString("homework_name"),
                    teacherName = data.getString("teacher_name"),
                    className = data.getString("class_name"),
                    pages = data.getString("pages"),
                    submitTriggered = data.optBoolean("submit_triggered", false),
                    submitError = data.optString("submit_error", null).takeIf { it.isNotBlank() }
                ))
            } else {
                Result.failure(Exception(json.optString("error", "发布失败")))
            }
        } catch (e: Exception) {
            Log.e(TAG, "智能发布失败: ${e.message}")
            Result.failure(e)
        }
    }
}