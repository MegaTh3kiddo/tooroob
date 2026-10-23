package ir.torob.seller.util

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
import ir.torob.seller.MainActivity
import ir.torob.seller.R

object NotificationHelper {

    const val CHANNEL_ID = "torob_inquiries_channel"
    const val CHANNEL_NAME = "استعلام‌های جدید خریداران"
    private const val TAG = "NotificationHelper"

    fun showInquiryNotification(
        context: Context,
        inquiryId: String,
        title: String,
        body: String,
        notificationType: String = "INITIAL_INQUIRY"
    ) {
        createNotificationChannel(context)

        // Deep-link intent directly to the inquiry detail page
        val intent = Intent(context, MainActivity::class.java).apply {
            action = Intent.ACTION_VIEW
            if (inquiryId.isNotBlank()) {
                data = Uri.parse("torob://inquiry/$inquiryId")
                putExtra("inquiry_id", inquiryId)
            }
            putExtra("notification_type", notificationType)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }

        val pendingIntentFlags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        } else {
            PendingIntent.FLAG_UPDATE_CURRENT
        }

        val pendingIntent = PendingIntent.getActivity(
            context,
            if (inquiryId.isNotBlank()) inquiryId.hashCode() else 1001,
            intent,
            pendingIntentFlags
        )

        val defaultSoundUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION)

        val notificationBuilder = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setAutoCancel(true)
            .setSound(defaultSoundUri)
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setDefaults(NotificationCompat.DEFAULT_ALL)
            .setCategory(NotificationCompat.CATEGORY_MESSAGE)
            .setContentIntent(pendingIntent)
            .setVibrate(longArrayOf(0, 400, 200, 400))

        val notificationId = if (inquiryId.isNotBlank()) inquiryId.hashCode() else System.currentTimeMillis().toInt()

        try {
            val notificationManager = NotificationManagerCompat.from(context)
            notificationManager.notify(notificationId, notificationBuilder.build())
        } catch (e: SecurityException) {
            Log.e(TAG, "Notification permission missing on Android 13+", e)
        }
    }

    fun createNotificationChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "اطلاع‌رسانی فوری برای استعلام قیمت و موجودی کالاها"
                enableVibration(true)
                enableLights(true)
            }
            val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }
}
