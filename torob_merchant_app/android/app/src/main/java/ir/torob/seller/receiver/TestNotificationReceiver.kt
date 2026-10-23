package ir.torob.seller.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.PowerManager
import androidx.core.content.ContextCompat
import ir.torob.seller.service.InquiryAlertService

class TestNotificationReceiver : BroadcastReceiver() {

    companion object {
        const val ACTION_TEST_NOTIFICATION = "ir.torob.seller.ACTION_TEST_NOTIFICATION"
        const val ACTION_TEST_RING = "ir.torob.seller.ACTION_TEST_RING"
        const val ACTION_STOP_RING = "ir.torob.seller.ACTION_STOP_RING"
    }

    override fun onReceive(context: Context, intent: Intent) {
        val pendingResult = goAsync()

        val pm = context.getSystemService(Context.POWER_SERVICE) as PowerManager
        val wakeLock = pm.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK or PowerManager.ACQUIRE_CAUSES_WAKEUP,
            "TorobSeller:ReceiverWakeLock"
        )
        wakeLock.acquire(10000)

        try {
            when (intent.action) {
                ACTION_TEST_RING -> {
                    val serviceIntent = Intent(context, InquiryAlertService::class.java).apply {
                        action = InquiryAlertService.ACTION_START_ALERT
                        putExtra("inquiry_id", intent.getStringExtra("inquiry_id") ?: "inq_01")
                        putExtra("title", intent.getStringExtra("title") ?: "استعلام فوری در ترب")
                        putExtra("body", intent.getStringExtra("body") ?: "خریدار منتظر استعلام قیمت گوشی آیفون ۱۵ است.")
                    }
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        ContextCompat.startForegroundService(context, serviceIntent)
                    } else {
                        context.startService(serviceIntent)
                    }
                }
                ACTION_STOP_RING -> {
                    val serviceIntent = Intent(context, InquiryAlertService::class.java).apply {
                        action = InquiryAlertService.ACTION_STOP_ALERT
                    }
                    context.startService(serviceIntent)
                }
                else -> {
                    // Default: ACTION_TEST_NOTIFICATION via InquiryAlertService to guarantee foreground execution
                    val serviceIntent = Intent(context, InquiryAlertService::class.java).apply {
                        action = InquiryAlertService.ACTION_SHOW_NOTIFICATION
                        putExtra("inquiry_id", intent.getStringExtra("inquiry_id") ?: "inq_01")
                        putExtra("title", intent.getStringExtra("title") ?: "استعلام جدید در ترب")
                        putExtra("body", intent.getStringExtra("body") ?: "خریدار منتظر استعلام قیمت گوشی آیفون ۱۵ است.")
                        putExtra("notification_type", intent.getStringExtra("notification_type") ?: "INITIAL_INQUIRY")
                    }
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        ContextCompat.startForegroundService(context, serviceIntent)
                    } else {
                        context.startService(serviceIntent)
                    }
                }
            }
        } finally {
            if (wakeLock.isHeld) {
                wakeLock.release()
            }
            pendingResult.finish()
        }
    }
}
