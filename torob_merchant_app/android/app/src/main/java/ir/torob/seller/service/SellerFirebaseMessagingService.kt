package ir.torob.seller.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.media.RingtoneManager
import android.net.Uri
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import ir.torob.seller.MainActivity
import ir.torob.seller.R
import ir.torob.seller.data.repository.PushRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class SellerFirebaseMessagingService : FirebaseMessagingService() {

    companion object {
        private const val TAG = "TorobFCMService"
        const val CHANNEL_ID = "torob_inquiries_channel"
        const val CHANNEL_NAME = "استعلام‌های جدید خریداران"
    }

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.d(TAG, "New FCM Token received: $token")
        // Register token with backend server
        CoroutineScope(Dispatchers.IO).launch {
            try {
                PushRepository(applicationContext).registerToken(token)
            } catch (e: Exception) {
                Log.e(TAG, "Failed to register new token on server", e)
            }
        }
    }

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        super.onMessageReceived(remoteMessage)
        Log.d(TAG, "Push received from: ${remoteMessage.from}, data: ${remoteMessage.data}")

        // Check if user disabled notifications in app settings
        val pushRepo = PushRepository(applicationContext)
        if (!pushRepo.areNotificationsEnabled()) {
            Log.d(TAG, "Notifications are disabled in app settings, skipping display.")
            return
        }

        val data = remoteMessage.data
        val inquiryId = data["inquiry_id"] ?: ""
        val notificationType = data["notification_type"] ?: data["type"] ?: "INITIAL_INQUIRY"

        val title = remoteMessage.notification?.title ?: data["title"] ?: "استعلام جدید در ترب"
        val body = remoteMessage.notification?.body ?: data["body"] ?: "یک مشتری منتظر استعلام قیمت و موجودی است."

        if (notificationType == "URGENT_CALL") {
            val alertIntent = Intent(this, InquiryAlertService::class.java).apply {
                action = InquiryAlertService.ACTION_START_ALERT
                putExtra("inquiry_id", inquiryId)
                putExtra("title", title)
                putExtra("body", body)
                putExtra("duration_seconds", 120)
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(alertIntent)
            } else {
                startService(alertIntent)
            }
        } else {
            if (notificationType == "EXPIRATION_ALERT") {
                val stopIntent = Intent(this, InquiryAlertService::class.java).apply {
                    action = InquiryAlertService.ACTION_STOP_ALERT
                }
                startService(stopIntent)
            }

            ir.torob.seller.util.NotificationHelper.showInquiryNotification(
                context = this,
                inquiryId = inquiryId,
                title = title,
                body = body,
                notificationType = notificationType
            )
        }
    }
}
