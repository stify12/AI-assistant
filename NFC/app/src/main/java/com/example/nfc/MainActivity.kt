package com.example.nfc

import android.content.Intent
import android.nfc.NfcAdapter
import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.*
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.example.nfc.ui.screens.BookSearchScreen
import com.example.nfc.ui.screens.DatabaseScreen
import com.example.nfc.ui.screens.MainScreen
import com.example.nfc.ui.screens.RfidSimulatorScreen
import com.example.nfc.ui.screens.AutomationScreen
import com.example.nfc.ui.theme.NFCTheme
import com.example.nfc.viewmodel.NfcViewModel
import com.example.nfc.viewmodel.RfidSimulatorViewModel
import com.example.nfc.viewmodel.AutomationViewModel

class MainActivity : ComponentActivity() {
    
    private var nfcAdapter: NfcAdapter? = null
    private var nfcViewModel: NfcViewModel? = null
    
    override fun onCreate(savedInstanceState: Bundle?) {
        // 启动页
        installSplashScreen()
        
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        
        // 初始化 NFC 适配器
        nfcAdapter = NfcAdapter.getDefaultAdapter(this)
        
        setContent {
            NFCTheme {
                val viewModel: NfcViewModel = viewModel()
                nfcViewModel = viewModel
                
                val navController = rememberNavController()

                // 卡片相关状态
                val cards by viewModel.cards.collectAsState()
                val cardGroups by viewModel.cardGroups.collectAsState()
                val currentCard by viewModel.currentCard.collectAsState()
                val isNfcEnabled by viewModel.isNfcEnabled.collectAsState()
                val batchConfig by viewModel.batchConfig.collectAsState()
                val remainingSeconds by viewModel.remainingSeconds.collectAsState()
                val lastUsedClass by viewModel.lastUsedClass.collectAsState()

                // 数据库相关状态
                val grades by viewModel.grades.collectAsState()
                val teachers by viewModel.teachers.collectAsState()
                val classes by viewModel.classes.collectAsState()
                val students by viewModel.students.collectAsState()
                val selectedClass by viewModel.selectedClass.collectAsState()
                val filterState by viewModel.filterState.collectAsState()
                val isDbLoading by viewModel.isDbLoading.collectAsState()
                val dbError by viewModel.dbError.collectAsState()
                val favoriteClassIds by viewModel.favoriteClassIds.collectAsState()
                val isOfflineMode by viewModel.isOfflineMode.collectAsState()

                // 最近使用班级
                val recentClasses by viewModel.recentClasses.collectAsState()
                
                // NFC 扫描状态
                val lastScannedTagId by viewModel.lastScannedTagId.collectAsState()

                // 书本搜索相关状态
                val books by viewModel.books.collectAsState()
                val selectedBook by viewModel.selectedBook.collectAsState()
                val bookClasses by viewModel.bookClasses.collectAsState()
                val selectedBookClass by viewModel.selectedBookClass.collectAsState()
                val bookStudents by viewModel.bookStudents.collectAsState()
                val bookSearchKeyword by viewModel.bookSearchKeyword.collectAsState()
                val selectedSubjectId by viewModel.selectedSubjectId.collectAsState()
                val isBookLoading by viewModel.isBookLoading.collectAsState()
                val lastUsedBook by viewModel.lastUsedBook.collectAsState()

                NavHost(navController = navController, startDestination = "automation") {
                    // 自动化流程页面（新主界面）
                    composable("automation") {
                        val automationViewModel: AutomationViewModel = viewModel()
                        
                        val autoConnectionStatus by automationViewModel.connectionStatus.collectAsState()
                        val automationStatus by automationViewModel.automationStatus.collectAsState()
                        val autoConfig by automationViewModel.config.collectAsState()
                        val autoLogs by automationViewModel.logs.collectAsState()
                        val autoIsLoading by automationViewModel.isLoading.collectAsState()
                        val autoErrorMessage by automationViewModel.errorMessage.collectAsState()
                        val autoBooks by automationViewModel.books.collectAsState()
                        val autoSelectedBook by automationViewModel.selectedBook.collectAsState()
                        val autoBookClasses by automationViewModel.bookClasses.collectAsState()
                        val autoSelectedBookClass by automationViewModel.selectedBookClass.collectAsState()
                        val autoBookStudents by automationViewModel.bookStudents.collectAsState()
                        val autoSearchKeyword by automationViewModel.searchKeyword.collectAsState()
                        // 新增状态
                        val autoRecentUsages by automationViewModel.recentUsages.collectAsState()
                        val autoFavoriteBooks by automationViewModel.favoriteBooks.collectAsState()
                        val autoSelectedSubjectId by automationViewModel.selectedSubjectId.collectAsState()
                        val autoSelectedGradeId by automationViewModel.selectedGradeId.collectAsState()
                        
                        AutomationScreen(
                            connectionStatus = autoConnectionStatus,
                            automationStatus = automationStatus,
                            config = autoConfig,
                            logs = autoLogs,
                            isLoading = autoIsLoading,
                            errorMessage = autoErrorMessage,
                            books = autoBooks,
                            selectedBook = autoSelectedBook,
                            bookClasses = autoBookClasses,
                            selectedBookClass = autoSelectedBookClass,
                            bookStudents = autoBookStudents,
                            searchKeyword = autoSearchKeyword,
                            // 新增参数
                            recentUsages = autoRecentUsages,
                            favoriteBooks = autoFavoriteBooks,
                            selectedSubjectId = autoSelectedSubjectId,
                            selectedGradeId = autoSelectedGradeId,
                            onSearchBooks = automationViewModel::searchBooks,
                            onSelectBook = automationViewModel::selectBook,
                            onSelectBookClass = automationViewModel::selectBookClass,
                            onUpdatePageNumber = automationViewModel::updatePageNumber,
                            onUpdateUsername = automationViewModel::updateUsername,
                            onUpdatePassword = automationViewModel::updatePassword,
                            onUpdateHomeworkName = automationViewModel::updateHomeworkName,
                            onUpdatePhotoInterval = automationViewModel::updatePhotoInterval,
                            onToggleDoublePageMode = automationViewModel::toggleDoublePageMode,
                            onStartAutomation = automationViewModel::startAutomation,
                            onStopAutomation = automationViewModel::stopAutomation,
                            onClearLogs = automationViewModel::clearLogs,
                            onClearError = automationViewModel::clearError,
                            onRefreshLogs = automationViewModel::refreshLogs,
                            onNavigateToManual = { navController.navigate("rfid_simulator") },
                            // 新增回调
                            onQuickStartFromRecent = automationViewModel::quickStartFromRecent,
                            onToggleFavorite = automationViewModel::toggleFavorite,
                            onSelectSubject = automationViewModel::selectSubject,
                            onSelectGrade = automationViewModel::selectGrade,
                            isFavorite = automationViewModel::isFavorite
                        )
                    }

                    // 主页面
                    composable("main") {
                        MainScreen(
                            cards = cards,
                            cardGroups = cardGroups,
                            currentCard = currentCard,
                            isNfcEnabled = isNfcEnabled,
                            batchConfig = batchConfig,
                            remainingSeconds = remainingSeconds,
                            lastUsedClass = lastUsedClass,
                            lastUsedBook = lastUsedBook,
                            recentClasses = recentClasses,
                            lastScannedTagId = lastScannedTagId,
                            onAddCard = viewModel::addCard,
                            onRemoveCard = viewModel::removeCard,
                            onSelectCard = viewModel::selectCard,
                            onToggleSelection = viewModel::toggleCardSelection,
                            onToggleGroupExpanded = viewModel::toggleGroupExpanded,
                            onSelectAllInGroup = viewModel::selectAllInGroup,
                            onRemoveCardsByClass = viewModel::removeCardsByClass,
                            onUpdateInterval = viewModel::updateInterval,
                            onStartBatch = viewModel::startBatchSimulation,
                            onPauseBatch = viewModel::pauseBatchSimulation,
                            onResumeBatch = viewModel::resumeBatchSimulation,
                            onStopBatch = viewModel::stopBatchSimulation,
                            onQuickStart = viewModel::quickStartLastClass,
                            onQuickStartBook = viewModel::quickStartLastBook,
                            onQuickStartClass = viewModel::quickStartClass,
                            onClearScannedTag = viewModel::clearScannedTag,
                            onRefreshNfc = {
                                viewModel.checkNfcStatus()
                                if (!isNfcEnabled) {
                                    startActivity(Intent(Settings.ACTION_NFC_SETTINGS))
                                }
                            },
                            onNavigateToDatabase = {
                                viewModel.loadDatabaseData()
                                navController.navigate("database")
                            },
                            onNavigateToBookSearch = {
                                viewModel.clearBookSelection()
                                navController.navigate("book_search")
                            },
                            onNavigateToRfidSimulator = {
                                navController.navigate("rfid_simulator")
                            }
                        )
                    }

                    // 数据库页面
                    composable("database") {
                        DatabaseScreen(
                            grades = grades,
                            teachers = teachers,
                            classes = classes,
                            students = students,
                            selectedClass = selectedClass,
                            filterState = filterState,
                            isLoading = isDbLoading,
                            errorMessage = dbError,
                            favoriteClassIds = favoriteClassIds,
                            isOfflineMode = isOfflineMode,
                            onFilterChange = viewModel::updateFilter,
                            onSelectClass = viewModel::selectClass,
                            onAddStudentsToCards = { selectedStudents ->
                                viewModel.addCardsFromStudents(selectedStudents, selectedClass)
                                navController.popBackStack()
                            },
                            onToggleFavorite = viewModel::toggleFavorite,
                            onRefresh = viewModel::loadDatabaseData,
                            onBack = { navController.popBackStack() }
                        )
                    }

                    // 书本搜索页面
                    composable("book_search") {
                        BookSearchScreen(
                            books = books,
                            selectedBook = selectedBook,
                            bookClasses = bookClasses,
                            selectedBookClass = selectedBookClass,
                            bookStudents = bookStudents,
                            searchKeyword = bookSearchKeyword,
                            selectedSubjectId = selectedSubjectId,
                            isLoading = isBookLoading,
                            onSearch = viewModel::searchBooks,
                            onSelectBook = viewModel::selectBook,
                            onSelectClass = viewModel::selectBookClass,
                            onStartSimulation = { students ->
                                viewModel.addBookCardsAndStart(students)
                                navController.popBackStack()
                            },
                            onBack = { 
                                viewModel.clearBookSelection()
                                navController.popBackStack() 
                            }
                        )
                    }

                    // RFID 模拟器页面（主界面）
                    composable("rfid_simulator") {
                        val rfidViewModel: RfidSimulatorViewModel = viewModel()
                        
                        // 连接状态
                        val connectionStatus by rfidViewModel.connectionStatus.collectAsState()
                        val taskStatus by rfidViewModel.taskStatus.collectAsState()
                        val batchConfigRfid by rfidViewModel.batchConfig.collectAsState()
                        val logs by rfidViewModel.logs.collectAsState()
                        val rfidRemainingSeconds by rfidViewModel.remainingSeconds.collectAsState()
                        val rfidLoading by rfidViewModel.isLoading.collectAsState()
                        val rfidError by rfidViewModel.errorMessage.collectAsState()
                        
                        // 班级模式数据
                        val rfidGrades by rfidViewModel.grades.collectAsState()
                        val rfidClasses by rfidViewModel.classes.collectAsState()
                        val rfidStudents by rfidViewModel.students.collectAsState()
                        val rfidSelectedGrade by rfidViewModel.selectedGrade.collectAsState()
                        val rfidSelectedClass by rfidViewModel.selectedClass.collectAsState()
                        
                        // 书本模式数据
                        val rfidBooks by rfidViewModel.books.collectAsState()
                        val rfidBookClasses by rfidViewModel.bookClasses.collectAsState()
                        val rfidBookStudents by rfidViewModel.bookStudents.collectAsState()
                        val rfidSelectedBook by rfidViewModel.selectedBook.collectAsState()
                        val rfidSelectedBookClass by rfidViewModel.selectedBookClass.collectAsState()
                        val rfidSearchKeyword by rfidViewModel.searchKeyword.collectAsState()
                        
                        // 选中学生
                        val rfidSelectedStudentIds by rfidViewModel.selectedStudentIds.collectAsState()
                        
                        RfidSimulatorScreen(
                            // 连接状态
                            connectionStatus = connectionStatus,
                            taskStatus = taskStatus,
                            batchConfig = batchConfigRfid,
                            logs = logs,
                            remainingSeconds = rfidRemainingSeconds,
                            isLoading = rfidLoading,
                            errorMessage = rfidError,
                            // 班级模式
                            grades = rfidGrades,
                            classes = rfidClasses,
                            students = rfidStudents,
                            selectedGrade = rfidSelectedGrade,
                            selectedClass = rfidSelectedClass,
                            // 书本模式
                            books = rfidBooks,
                            bookClasses = rfidBookClasses,
                            bookStudents = rfidBookStudents,
                            selectedBook = rfidSelectedBook,
                            selectedBookClass = rfidSelectedBookClass,
                            searchKeyword = rfidSearchKeyword,
                            // 选中学生
                            selectedStudentIds = rfidSelectedStudentIds,
                            // 回调
                            onRefreshConnection = rfidViewModel::refreshConnection,
                            onTestConnection = rfidViewModel::testConnection,
                            onUpdateInterval = rfidViewModel::updateInterval,
                            onStartBatch = rfidViewModel::startBatchSimulation,
                            onPauseBatch = rfidViewModel::pauseBatchSimulation,
                            onResumeBatch = rfidViewModel::resumeBatchSimulation,
                            onStopBatch = rfidViewModel::stopBatchSimulation,
                            onClearLogs = rfidViewModel::clearLogs,
                            onClearError = rfidViewModel::clearError,
                            // 数据源回调
                            onSelectGrade = rfidViewModel::selectGrade,
                            onSelectClass = rfidViewModel::selectClass,
                            onSearchBooks = rfidViewModel::searchBooks,
                            onSelectBook = rfidViewModel::selectBook,
                            onSelectBookClass = rfidViewModel::selectBookClass,
                            onToggleStudent = rfidViewModel::toggleStudent,
                            onSelectAllStudents = rfidViewModel::selectAllStudents,
                            onLoadClasses = rfidViewModel::loadClasses,
                            onLoadBooks = rfidViewModel::loadBooks,
                            onNavigateBack = { navController.popBackStack() }
                        )
                    }
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        // HCE 模式不需要额外启用，系统自动处理
        nfcViewModel?.checkNfcStatus()
        println("[NFC] App 恢复，HCE 服务已就绪")
    }
    
    override fun onPause() {
        super.onPause()
        println("[NFC] App 暂停")
    }
}
