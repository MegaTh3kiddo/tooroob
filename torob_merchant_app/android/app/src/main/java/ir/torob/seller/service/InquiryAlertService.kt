package ir.torob.seller.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat
import ir.torob.seller.R
import ir.torob.seller.ui.screens.call.IncomingInquiryActivity
import ir.torob.seller.util.InquiryRingtoneManager
import ir.torob.seller.util.NotificationHelper

class InquiryAlertService : Service() {

    companion object {
        const val ACTION_START_ALERT = "ir.torob.seller.ACTION_START_ALERT"
        const val ACTION_STOP_ALERT = "ir.torob.seller.ACTION_STOP_ALERT"
        const val ACTION_SHOW_NOTIFICATION = "ir.torob.seller.ACTION_SHOW_NOTIFICATION"
        private const val NOTIFICATION_ID = 9001
        private const val SILENT_CALL_CHANNEL_ID = "torob_inquiry_call_service_silent_v2"
        private const val TAG = "InquiryAlertService"
    }

    private var wakeLock: PowerManager.WakeLock? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val action = intent?.action ?: ACTION_START_ALERT

        if (action == ACTION_STOP_ALERT) {
            stopAlert()
            stopSelf()
            return START_NOT_STICKY
        }

        if (action == ACTION_SHOW_NOTIFICATION) {
            val inquiryId = intent?.getStringExtra("inquiry_id") ?: "inq_01"
            val title = intent?.getStringExtra("title") ?: "استعلام جدید در ترب"
            val body = intent?.getStringExtra("body") ?: "خریدار منتظر استعلام قیمت گوشی آیفون ۱۵ است."
            val notificationType = intent?.getStringExtra("notification_type") ?: "INITIAL_INQUIRY"

            acquireWakeLock()
            createSilentCallChannel()

            // Post the inquiry notification with deep links
            NotificationHelper.showInquiryNotification(this, inquiryId, title, body, notificationType)

            // Satisfy startForeground contract if launched via startForegroundService
            val tempNotif = NotificationCompat.Builder(this, SILENT_CALL_CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_notification)
                .setContentTitle(title)
                .setContentText(body)
                .setPriority(NotificationCompat.PRIORITY_MIN)
                .setSilent(true)
                .build()

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                startForeground(NOTIFICATION_ID, tempNotif, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK)
            } else {
                startForeground(NOTIFICATION_ID, tempNotif)
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                stopForeground(STOP_FOREGROUND_REMOVE)
            } else {
                @Suppress("DEPRECATION")
                stopForeground(true)
            }
            releaseWakeLock()
            stopSelf()
            return START_NOT_STICKY
        }

        val inquiryId = intent?.getStringExtra("inquiry_id") ?: "inq_01"
        val title = intent?.getStringExtra("title") ?: "استعلام فوری در ترب"
        val body = intent?.getStringExtra("body") ?: "خریدار منتظر پاسخ قیمت و موجودی شماست (مهلت ۲ دقیقه)"
        val durationSeconds = intent?.getIntExtra("duration_seconds", 120) ?: 120

        startAlert(inquiryId, title, body, durationSeconds)
        return START_NOT_STICKY
    }

    private fun startAlert(inquiryId: String, title: String, body: String, durationSeconds: Int = 120) {
        acquireWakeLock(durationSeconds)
        createSilentCallChannel()

        // 1. Start continuous ringtone and vibration directly for 2 minutes
        InquiryRingtoneManager.startRinging(applicationContext, maxDurationSec = durationSeconds)

        // 2. Intent to open the full-screen Incoming Call UI
        val callIntent = Intent(this, IncomingInquiryActivity::class.java).apply {
            putExtra("inquiry_id", inquiryId)
            putExtra("title", title)
            putExtra("body", body)
            putExtra("duration_seconds", durationSeconds)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or
                    Intent.FLAG_ACTIVITY_CLEAR_TOP or
                    Intent.FLAG_ACTIVITY_REORDER_TO_FRONT
        }
        val contentPendingIntent = PendingIntent.getActivity(
            this,
            2001,
            callIntent,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE else PendingIntent.FLAG_UPDATE_CURRENT
        )

        // 3. Build foreground service notification.
        // NOTE: Strictly PRIORITY_LOW and IMPORTANCE_LOW with NO fullScreenIntent and NO action buttons
        // to prevent Android from displaying a floating Heads-Up Notification (HUN) banner on screen.
        // The full-screen IncomingInquiryActivity is displayed exclusively via startActivity.
        val notification = NotificationCompat.Builder(this, SILENT_CALL_CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle("تماس ورودی استعلام ترب")
            .setContentText(title)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setContentIntent(contentPendingIntent)
            .setOngoing(true)
            .setAutoCancel(false)
            .setSilent(true)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }

        // 4. Directly launch the full-screen call activity
        try {
            startActivity(callIntent)
        } catch (e: Exception) {
            Log.e(TAG, "Direct call activity launch failed: ${e.message}", e)
        }
    }

    private fun stopAlert() {
        InquiryRingtoneManager.stopRinging(applicationContext)
        releaseWakeLock()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            stopForeground(STOP_FOREGROUND_REMOVE)
        } else {
            @Suppress("DEPRECATION")
            stopForeground(true)
        }
        try {
            val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            nm.cancel(NOTIFICATION_ID)
        } catch (e: Exception) {
            // Ignored
        }
    }

    private fun acquireWakeLock(durationSeconds: Int = 120) {
        try {
            val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
            wakeLock = pm.newWakeLock(
                PowerManager.PARTIAL_WAKE_LOCK or PowerManager.ACQUIRE_CAUSES_WAKEUP,
                "TorobSeller:AlertWakeLock"
            ).apply {
                acquire((durationSeconds + 10) * 1000L)
            }
        } catch (e: Exception) {
            Log.e(TAG, "WakeLock acquisition failed", e)
        }
    }

    private fun releaseWakeLock() {
        try {
            if (wakeLock?.isHeld == true) {
                wakeLock?.release()
            }
        } catch (e: Exception) {
            Log.e(TAG, "WakeLock release error", e)
        }
        wakeLock = null
    }

    private fun createSilentCallChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            // Delete old noisy channel if it exists
            try {
                nm.deleteNotificationChannel("torob_inquiry_alert_channel")
            } catch (e: Exception) {
                // Ignore
            }

            val channel = NotificationChannel(
                SILENT_CALL_CHANNEL_ID,
                "سرویس تماس ورودی ترب",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "سرویس پیش‌زمینه جهت زنگ استعلام بدون ایجاد اعلان پاپ‌آپ مزاحم"
                setSound(null, null)
                enableVibration(false)
                lockscreenVisibility = android.app.Notification.VISIBILITY_SECRET
            }
            nm.createNotificationChannel(channel)
        }
    }

    override fun onDestroy() {
        stopAlert()
        super.onDestroy()
    }
}
