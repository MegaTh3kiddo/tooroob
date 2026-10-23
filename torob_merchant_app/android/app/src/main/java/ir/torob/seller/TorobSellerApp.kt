package ir.torob.seller

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import android.util.Log
import com.google.firebase.FirebaseApp
import com.google.firebase.messaging.FirebaseMessaging
import ir.torob.seller.data.repository.PushRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class TorobSellerApp : Application() {

    override fun onCreate() {
        super.onCreate()

        // 1. Create Notification Channels
        createNotificationChannels()

        // 2. Fetch and register FCM push token
        initializePushToken()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                "torob_inquiries_channel",
                "استعلام‌های جدید خریداران",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "اطلاع‌رسانی فوری برای استعلام قیمت و موجودی کالاها"
                enableVibration(true)
                enableLights(true)
            }
            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }

    private fun initializePushToken() {
        try {
            if (FirebaseApp.getApps(this).isNotEmpty()) {
                FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
                    if (task.isSuccessful && task.result != null) {
                        val token = task.result
                        Log.d("TorobSellerApp", "FCM Token: $token")
                        CoroutineScope(Dispatchers.IO).launch {
                            try {
                                PushRepository(applicationContext).registerToken(token)
                            } catch (e: Exception) {
                                Log.e("TorobSellerApp", "Error registering token", e)
                            }
                        }
                    }
                }
            }
        } catch (e: Exception) {
            Log.w("TorobSellerApp", "Firebase not initialized: ${e.message}")
        }
    }
}
