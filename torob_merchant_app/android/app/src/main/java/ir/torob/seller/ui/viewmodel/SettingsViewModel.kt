package ir.torob.seller.ui.viewmodel

import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import ir.torob.seller.BuildConfig
import ir.torob.seller.data.model.ShopDto
import ir.torob.seller.data.remote.ApiClient
import ir.torob.seller.data.repository.AlertSoundType
import ir.torob.seller.data.repository.AppThemeMode
import ir.torob.seller.data.repository.AuthRepository
import ir.torob.seller.data.repository.ShopRepository
import ir.torob.seller.data.repository.UserPreferencesRepository
import ir.torob.seller.util.InquiryRingtoneManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class SettingsUiState(
    // Section 1: Notifications & Inquiry Alerts
    val notificationsEnabled: Boolean = true,
    val urgentRingEnabled: Boolean = true,
    val vibrationEnabled: Boolean = true,
    val alertSoundType: AlertSoundType = AlertSoundType.DEFAULT_RINGTONE,
    val isPreviewPlaying: Boolean = false,
    val canUseFullScreenIntent: Boolean = true,

    // Section 2: Appearance
    val themeMode: AppThemeMode = AppThemeMode.SYSTEM,

    // Section 3: Store Availability
    val shop: ShopDto? = null,
    val isShopLoading: Boolean = false,
    val shopError: String? = null,

    // Section 4: Account Info
    val sellerName: String = "",
    val sellerPhone: String = "",
    val shopId: String = "",

    // Section 5: Application Info
    val appVersionName: String = BuildConfig.VERSION_NAME,
    val appVersionCode: Int = BuildConfig.VERSION_CODE,

    // Feedback
    val feedbackMessage: String? = null,
    val serverBaseUrl: String = "http://127.0.0.1:8080/api/"
)

class SettingsViewModel(private val context: Context) : ViewModel() {
    private val userPrefs = UserPreferencesRepository(context)
    private val shopRepo = ShopRepository(context)
    private val authRepo = AuthRepository(context)
    private val authPrefs = context.getSharedPreferences("seller_auth_prefs", Context.MODE_PRIVATE)

    private val _uiState = MutableStateFlow(
        SettingsUiState(
            notificationsEnabled = userPrefs.areNotificationsEnabled(),
            urgentRingEnabled = userPrefs.isUrgentRingEnabled(),
            vibrationEnabled = userPrefs.isVibrationEnabled(),
            alertSoundType = userPrefs.getAlertSoundType(),
            themeMode = userPrefs.getThemeMode(),
            canUseFullScreenIntent = checkFullScreenPermissionInternal(),
            sellerName = authRepo.getSellerName(),
            sellerPhone = authRepo.getPhoneNumber(),
            shopId = authRepo.getShopId(),
            serverBaseUrl = authPrefs.getString("custom_server_url", "http://127.0.0.1:8080/api/") ?: "http://127.0.0.1:8080/api/"
        )
    )
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()

    init {
        // Observe preferences flows reactively
        viewModelScope.launch {
            userPrefs.notificationsEnabled.collect { enabled ->
                _uiState.value = _uiState.value.copy(notificationsEnabled = enabled)
            }
        }
        viewModelScope.launch {
            userPrefs.urgentRingEnabled.collect { enabled ->
                _uiState.value = _uiState.value.copy(urgentRingEnabled = enabled)
            }
        }
        viewModelScope.launch {
            userPrefs.vibrationEnabled.collect { enabled ->
                _uiState.value = _uiState.value.copy(vibrationEnabled = enabled)
            }
        }
        viewModelScope.launch {
            userPrefs.alertSoundType.collect { sound ->
                _uiState.value = _uiState.value.copy(alertSoundType = sound)
            }
        }
        viewModelScope.launch {
            userPrefs.themeMode.collect { mode ->
                _uiState.value = _uiState.value.copy(themeMode = mode)
            }
        }

        refreshShopStatus()
    }

    private fun checkFullScreenPermissionInternal(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager
            nm?.canUseFullScreenIntent() ?: true
        } else {
            true
        }
    }

    fun refreshFullScreenPermission() {
        _uiState.value = _uiState.value.copy(canUseFullScreenIntent = checkFullScreenPermissionInternal())
    }

    fun toggleNotifications(enabled: Boolean) {
        userPrefs.setNotificationsEnabled(enabled)
        _uiState.value = _uiState.value.copy(
            feedbackMessage = if (enabled) "دریافت نوتیفیکیشن فعال شد" else "نوتیفیکیشن‌ها غیرفعال شدند"
        )
    }

    fun toggleUrgentRing(enabled: Boolean) {
        userPrefs.setUrgentRingEnabled(enabled)
        _uiState.value = _uiState.value.copy(
            feedbackMessage = if (enabled) "زنگ استعلام فعال شد" else "زنگ استعلام بی‌صدا شد"
        )
    }

    fun toggleVibration(enabled: Boolean) {
        userPrefs.setVibrationEnabled(enabled)
        _uiState.value = _uiState.value.copy(
            feedbackMessage = if (enabled) "ویبره فعال شد" else "ویبره غیرفعال شد"
        )
    }

    fun selectAlertSound(soundType: AlertSoundType) {
        userPrefs.setAlertSoundType(soundType)
        _uiState.value = _uiState.value.copy(
            feedbackMessage = "صدای استعلام تغییر یافت: ${soundType.title}"
        )
    }

    fun toggleSoundPreview(soundType: AlertSoundType = _uiState.value.alertSoundType) {
        if (_uiState.value.isPreviewPlaying) {
            stopSoundPreview()
        } else {
            _uiState.value = _uiState.value.copy(isPreviewPlaying = true)
            InquiryRingtoneManager.previewSound(context, soundType) {
                _uiState.value = _uiState.value.copy(isPreviewPlaying = false)
            }
        }
    }

    fun stopSoundPreview() {
        InquiryRingtoneManager.stopPreview()
        _uiState.value = _uiState.value.copy(isPreviewPlaying = false)
    }

    fun setThemeMode(mode: AppThemeMode) {
        userPrefs.setThemeMode(mode)
    }

    fun refreshShopStatus() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isShopLoading = true, shopError = null)
            val result = shopRepo.getShopProfile()
            result.fold(
                onSuccess = { shop ->
                    _uiState.value = _uiState.value.copy(
                        shop = shop,
                        isShopLoading = false,
                        shopError = null,
                        shopId = shop.shopId.ifBlank { _uiState.value.shopId }
                    )
                },
                onFailure = { error ->
                    _uiState.value = _uiState.value.copy(
                        isShopLoading = false,
                        shopError = error.message
                    )
                }
            )
        }
    }

    fun toggleShopStatus() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isShopLoading = true, shopError = null)
            val result = shopRepo.toggleShopStatus()
            result.fold(
                onSuccess = { updatedShop ->
                    val statusText = if (updatedShop.isOpen) "فروشگاه باز شد" else "فروشگاه موقتاً بسته شد"
                    _uiState.value = _uiState.value.copy(
                        shop = updatedShop,
                        isShopLoading = false,
                        feedbackMessage = statusText
                    )
                },
                onFailure = { error ->
                    _uiState.value = _uiState.value.copy(
                        isShopLoading = false,
                        feedbackMessage = "خطا در تغییر وضعیت فروشگاه: ${error.message}"
                    )
                }
            )
        }
    }

    fun updateServerUrl(url: String) {
        authPrefs.edit().putString("custom_server_url", url).apply()
        ApiClient.resetClient()
        _uiState.value = _uiState.value.copy(serverBaseUrl = url, feedbackMessage = "آدرس سرور بروزرسانی شد")
    }

    fun clearFeedbackMessage() {
        _uiState.value = _uiState.value.copy(feedbackMessage = null)
    }

    override fun onCleared() {
        super.onCleared()
        InquiryRingtoneManager.stopPreview()
    }
}
