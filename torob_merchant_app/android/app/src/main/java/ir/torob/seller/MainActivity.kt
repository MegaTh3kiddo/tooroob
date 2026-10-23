package ir.torob.seller

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.MotionEvent
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.*
import androidx.core.content.ContextCompat
import androidx.navigation.compose.rememberNavController
import ir.torob.seller.data.repository.AuthRepository
import ir.torob.seller.data.repository.InquiryRepository
import ir.torob.seller.data.repository.ShopRepository
import ir.torob.seller.ui.navigation.AppNavGraph
import ir.torob.seller.ui.theme.TorobSellerTheme
import ir.torob.seller.ui.viewmodel.*
import ir.torob.seller.util.NetworkMonitor

class MainActivity : ComponentActivity() {

    private val authRepository by lazy { AuthRepository(applicationContext) }
    private val inquiryRepository by lazy { InquiryRepository(applicationContext) }
    private val shopRepository by lazy { ShopRepository(applicationContext) }
    private val networkMonitor by lazy { NetworkMonitor(applicationContext) }

    private var hasNotificationPermission by mutableStateOf(true)
    private var pendingInquiryId by mutableStateOf<String?>(null)

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        hasNotificationPermission = isGranted
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // If opened from notification or alert, immediately silence ringing
        stopRingingAndAlert()

        checkNotificationPermission()

        val initialInquiryId = extractInquiryId(intent)
        android.util.Log.d("MainActivityNav", "onCreate: intent=$intent, data=${intent?.data}, initialInquiryId=$initialInquiryId")
        pendingInquiryId = initialInquiryId

        setContent {
            val settingsViewModel = remember { SettingsViewModel(applicationContext) }
            val settingsUiState by settingsViewModel.uiState.collectAsState()
            val isDarkTheme = when (settingsUiState.themeMode) {
                ir.torob.seller.data.repository.AppThemeMode.SYSTEM -> androidx.compose.foundation.isSystemInDarkTheme()
                ir.torob.seller.data.repository.AppThemeMode.LIGHT -> false
                ir.torob.seller.data.repository.AppThemeMode.DARK -> true
            }

            TorobSellerTheme(darkTheme = isDarkTheme) {
                val navController = rememberNavController()

                val authViewModel = remember { AuthViewModel(authRepository) }
                val inquiryViewModel = remember { InquiryViewModel(inquiryRepository) }
                val storeViewModel = remember { StoreViewModel(shopRepository) }
                val metricsViewModel = remember { MetricsViewModel(applicationContext) }

                val isOnline by networkMonitor.isOnline.collectAsState(initial = true)

                AppNavGraph(
                    navController = navController,
                    authViewModel = authViewModel,
                    inquiryViewModel = inquiryViewModel,
                    storeViewModel = storeViewModel,
                    metricsViewModel = metricsViewModel,
                    settingsViewModel = settingsViewModel,
                    isOnline = isOnline,
                    hasNotificationPermission = hasNotificationPermission,
                    onRequestNotificationPermission = {
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                            requestPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                        } else {
                            openAppSettings()
                        }
                    },
                    deepLinkInquiryId = pendingInquiryId,
                    onDeepLinkHandled = { pendingInquiryId = null }
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        stopRingingAndAlert()
        val inquiryId = extractInquiryId(intent)
        android.util.Log.d("MainActivityNav", "onNewIntent: intent=$intent, data=${intent.data}, inquiryId=$inquiryId")
        if (!inquiryId.isNullOrBlank()) {
            pendingInquiryId = inquiryId
        }
    }

    private fun stopRingingAndAlert() {
        try {
            ir.torob.seller.util.InquiryRingtoneManager.stopRinging(applicationContext)
            stopService(Intent(this, ir.torob.seller.service.InquiryAlertService::class.java))
        } catch (e: Exception) {
            // Ignored
        }
    }

    private fun checkNotificationPermission() {
        hasNotificationPermission = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED
        } else {
            true
        }
    }

    private fun extractInquiryId(intent: Intent?): String? {
        if (intent == null) return null
        val data: Uri? = intent.data
        if (data != null && data.scheme == "torob" && data.host == "inquiry") {
            return data.lastPathSegment
        }
        return intent.getStringExtra("inquiry_id")
    }

    private fun openAppSettings() {
        val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = Uri.fromParts("package", packageName, null)
        }
        startActivity(intent)
    }

    override fun dispatchGenericMotionEvent(ev: MotionEvent?): Boolean {
        return try {
            super.dispatchGenericMotionEvent(ev)
        } catch (e: IllegalStateException) {
            if (e.message?.contains("ACTION_HOVER_EXIT") == true) {
                true
            } else {
                throw e
            }
        }
    }

    override fun dispatchTouchEvent(ev: MotionEvent?): Boolean {
        return try {
            super.dispatchTouchEvent(ev)
        } catch (e: IllegalStateException) {
            if (e.message?.contains("ACTION_HOVER_EXIT") == true) {
                true
            } else {
                throw e
            }
        }
    }
}
