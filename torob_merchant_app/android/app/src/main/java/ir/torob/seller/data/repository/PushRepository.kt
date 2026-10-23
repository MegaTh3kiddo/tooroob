package ir.torob.seller.data.repository

import android.content.Context
import android.os.Build
import ir.torob.seller.data.model.PushPreferenceRequest
import ir.torob.seller.data.model.PushTokenRegisterRequest
import ir.torob.seller.data.remote.ApiClient

class PushRepository(private val context: Context) {
    private val prefs = context.getSharedPreferences("seller_push_prefs", Context.MODE_PRIVATE)
    private val api = ApiClient.getService(context)

    fun getStoredToken(): String? = prefs.getString("fcm_token", null)

    fun areNotificationsEnabled(): Boolean = prefs.getBoolean("notifications_enabled", true)

    suspend fun registerToken(token: String): Result<Boolean> {
        prefs.edit().putString("fcm_token", token).apply()
        return try {
            val payload = PushTokenRegisterRequest(
                fcmToken = token,
                deviceModel = "${Build.MANUFACTURER} ${Build.MODEL}",
                osVersion = "Android ${Build.VERSION.RELEASE} (SDK ${Build.VERSION.SDK_INT})",
                appVersion = "1.0.0",
                notificationsEnabled = areNotificationsEnabled()
            )
            val resp = api.registerPushToken(payload)
            if (resp.isSuccessful) {
                Result.success(true)
            } else {
                Result.failure(Exception("Failed to register push token with server"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun setNotificationsEnabled(enabled: Boolean): Result<Boolean> {
        prefs.edit().putBoolean("notifications_enabled", enabled).apply()
        return try {
            val resp = api.updatePushPreferences(PushPreferenceRequest(enabled))
            if (resp.isSuccessful) {
                Result.success(true)
            } else {
                Result.failure(Exception("Failed to update push preferences"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
