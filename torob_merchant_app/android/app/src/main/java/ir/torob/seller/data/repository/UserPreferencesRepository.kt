package ir.torob.seller.data.repository

import android.content.Context
import android.media.RingtoneManager
import ir.torob.seller.data.model.PushPreferenceRequest
import ir.torob.seller.data.remote.ApiClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

enum class AppThemeMode(val title: String, val description: String) {
    SYSTEM("مطابق تنظیمات سیستم", "پیروی از حالت روز یا شب دستگاه"),
    LIGHT("روشن", "تم روشن با کنتراست بالا"),
    DARK("تاریک", "تم تیره برای محیط‌های کم‌نور")
}

enum class AlertSoundType(val id: String, val title: String, val subtitle: String, val ringtoneType: Int) {
    DEFAULT_RINGTONE(
        id = "DEFAULT_RINGTONE",
        title = "زنگ پیش‌فرض ترب",
        subtitle = "صدای زنگ استاندارد تماس گوشی",
        ringtoneType = RingtoneManager.TYPE_RINGTONE
    ),
    NOTIFICATION_SOUND(
        id = "NOTIFICATION_SOUND",
        title = "صدای اعلان سیستم",
        subtitle = "صدای کوتاه و پیوسته اعلان سیستم",
        ringtoneType = RingtoneManager.TYPE_NOTIFICATION
    ),
    ALARM_SOUND(
        id = "ALARM_SOUND",
        title = "صدای آلارم هشدار",
        subtitle = "صدای زنگ ساعت و آلارم گوشی",
        ringtoneType = RingtoneManager.TYPE_ALARM
    );

    companion object {
        fun fromId(id: String?): AlertSoundType {
            return values().firstOrNull { it.id == id } ?: DEFAULT_RINGTONE
        }
    }
}

class UserPreferencesRepository(private val context: Context) {

    private val prefs = context.getSharedPreferences("seller_user_prefs", Context.MODE_PRIVATE)
    private val pushPrefs = context.getSharedPreferences("seller_push_prefs", Context.MODE_PRIVATE)

    companion object {
        private const val KEY_NOTIFICATIONS_ENABLED = "notifications_enabled"
        private const val KEY_URGENT_RING_ENABLED = "urgent_ring_enabled"
        private const val KEY_VIBRATION_ENABLED = "vibration_enabled"
        private const val KEY_ALERT_SOUND_TYPE = "alert_sound_type"
        private const val KEY_THEME_MODE = "theme_mode"
    }

    private val _notificationsEnabled = MutableStateFlow(
        prefs.getBoolean(KEY_NOTIFICATIONS_ENABLED, pushPrefs.getBoolean(KEY_NOTIFICATIONS_ENABLED, true))
    )
    val notificationsEnabled: StateFlow<Boolean> = _notificationsEnabled.asStateFlow()

    private val _urgentRingEnabled = MutableStateFlow(prefs.getBoolean(KEY_URGENT_RING_ENABLED, true))
    val urgentRingEnabled: StateFlow<Boolean> = _urgentRingEnabled.asStateFlow()

    private val _vibrationEnabled = MutableStateFlow(prefs.getBoolean(KEY_VIBRATION_ENABLED, true))
    val vibrationEnabled: StateFlow<Boolean> = _vibrationEnabled.asStateFlow()

    private val _alertSoundType = MutableStateFlow(
        AlertSoundType.fromId(prefs.getString(KEY_ALERT_SOUND_TYPE, AlertSoundType.DEFAULT_RINGTONE.id))
    )
    val alertSoundType: StateFlow<AlertSoundType> = _alertSoundType.asStateFlow()

    private val _themeMode = MutableStateFlow(
        try {
            AppThemeMode.valueOf(prefs.getString(KEY_THEME_MODE, AppThemeMode.SYSTEM.name) ?: AppThemeMode.SYSTEM.name)
        } catch (_: Exception) {
            AppThemeMode.SYSTEM
        }
    )
    val themeMode: StateFlow<AppThemeMode> = _themeMode.asStateFlow()

    fun areNotificationsEnabled(): Boolean = _notificationsEnabled.value
    fun isUrgentRingEnabled(): Boolean = _urgentRingEnabled.value
    fun isVibrationEnabled(): Boolean = _vibrationEnabled.value
    fun getAlertSoundType(): AlertSoundType = _alertSoundType.value
    fun getThemeMode(): AppThemeMode = _themeMode.value

    fun setNotificationsEnabled(enabled: Boolean) {
        prefs.edit().putBoolean(KEY_NOTIFICATIONS_ENABLED, enabled).apply()
        pushPrefs.edit().putBoolean(KEY_NOTIFICATIONS_ENABLED, enabled).apply()
        _notificationsEnabled.value = enabled

        // Sync with backend push preferences
        CoroutineScope(Dispatchers.IO).launch {
            try {
                ApiClient.getService(context).updatePushPreferences(PushPreferenceRequest(enabled))
            } catch (_: Exception) {}
        }
    }

    fun setUrgentRingEnabled(enabled: Boolean) {
        prefs.edit().putBoolean(KEY_URGENT_RING_ENABLED, enabled).apply()
        _urgentRingEnabled.value = enabled
    }

    fun setVibrationEnabled(enabled: Boolean) {
        prefs.edit().putBoolean(KEY_VIBRATION_ENABLED, enabled).apply()
        _vibrationEnabled.value = enabled
    }

    fun setAlertSoundType(soundType: AlertSoundType) {
        prefs.edit().putString(KEY_ALERT_SOUND_TYPE, soundType.id).apply()
        _alertSoundType.value = soundType
    }

    fun setThemeMode(mode: AppThemeMode) {
        prefs.edit().putString(KEY_THEME_MODE, mode.name).apply()
        _themeMode.value = mode
    }
}
