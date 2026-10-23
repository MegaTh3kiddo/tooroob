package ir.torob.seller.util

import android.content.Context
import android.media.AudioAttributes
import android.media.MediaPlayer
import android.media.RingtoneManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.util.Log
import ir.torob.seller.data.repository.AlertSoundType
import ir.torob.seller.data.repository.UserPreferencesRepository

object InquiryRingtoneManager {

    private const val TAG = "InquiryRingtone"
    private var mediaPlayer: MediaPlayer? = null
    private var previewPlayer: MediaPlayer? = null
    private var isPlaying = false
    private var isPreviewPlaying = false
    private val mainHandler = Handler(Looper.getMainLooper())
    private var stopPreviewRunnable: Runnable? = null

    @Synchronized
    fun startRinging(context: Context, maxDurationSec: Int = 30) {
        if (isPlaying) return

        val userPrefs = UserPreferencesRepository(context)
        val ringEnabled = userPrefs.isUrgentRingEnabled()
        val vibrationEnabled = userPrefs.isVibrationEnabled()

        if (!ringEnabled && !vibrationEnabled) {
            Log.d(TAG, "Both urgent ring and vibration are disabled by user.")
            return
        }

        try {
            if (ringEnabled) {
                val soundType = userPrefs.getAlertSoundType()
                val ringtoneUri = RingtoneManager.getDefaultUri(soundType.ringtoneType)
                    ?: RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE)
                    ?: RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION)

                mediaPlayer = MediaPlayer().apply {
                    setDataSource(context, ringtoneUri)
                    setAudioAttributes(
                        AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_ALARM)
                            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                            .build()
                    )
                    isLooping = true
                    prepare()
                    start()
                }
                isPlaying = true
                Log.d(TAG, "Ringtone started looping with sound: ${soundType.title}")
            }

            // Start repeating vibration if enabled
            if (vibrationEnabled) {
                startVibration(context)
                isPlaying = true
            }

            // Auto-stop after timeout so it doesn't drain battery
            mainHandler.postDelayed({
                stopRinging(context)
            }, (maxDurationSec * 1000).toLong())

        } catch (e: Exception) {
            Log.e(TAG, "Failed to start urgent alert", e)
        }
    }

    @Synchronized
    fun stopRinging(context: Context) {
        if (!isPlaying) return
        try {
            mediaPlayer?.let {
                if (it.isPlaying) {
                    it.stop()
                }
                it.reset()
                it.release()
            }
            mediaPlayer = null
            stopVibration(context)
            isPlaying = false
            Log.d(TAG, "Ringtone stopped")
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping ringtone", e)
        }
    }

    fun isRinging(): Boolean = isPlaying

    @Synchronized
    fun previewSound(context: Context, soundType: AlertSoundType, onCompletion: () -> Unit = {}) {
        stopPreview()

        try {
            val ringtoneUri = RingtoneManager.getDefaultUri(soundType.ringtoneType)
                ?: RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION)

            previewPlayer = MediaPlayer().apply {
                setDataSource(context, ringtoneUri)
                setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_NOTIFICATION_RINGTONE)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .build()
                )
                setOnCompletionListener {
                    stopPreview()
                    onCompletion()
                }
                prepare()
                start()
            }
            isPreviewPlaying = true

            // Stop preview after max 6 seconds if it's a looping/long sound
            stopPreviewRunnable = Runnable {
                stopPreview()
                onCompletion()
            }
            mainHandler.postDelayed(stopPreviewRunnable!!, 6000L)

        } catch (e: Exception) {
            Log.e(TAG, "Failed to preview sound", e)
            stopPreview()
            onCompletion()
        }
    }

    @Synchronized
    fun stopPreview() {
        stopPreviewRunnable?.let { mainHandler.removeCallbacks(it) }
        stopPreviewRunnable = null

        try {
            previewPlayer?.let {
                if (it.isPlaying) {
                    it.stop()
                }
                it.reset()
                it.release()
            }
            previewPlayer = null
            isPreviewPlaying = false
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping preview", e)
        }
    }

    fun isPreviewing(): Boolean = isPreviewPlaying

    private fun startVibration(context: Context) {
        try {
            val pattern = longArrayOf(0, 800, 400, 800, 400)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val vibratorManager = context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
                val vibrator = vibratorManager.defaultVibrator
                vibrator.vibrate(VibrationEffect.createWaveform(pattern, 0))
            } else {
                @Suppress("DEPRECATION")
                val vibrator = context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    vibrator.vibrate(VibrationEffect.createWaveform(pattern, 0))
                } else {
                    @Suppress("DEPRECATION")
                    vibrator.vibrate(pattern, 0)
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Vibration failed", e)
        }
    }

    private fun stopVibration(context: Context) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val vibratorManager = context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
                vibratorManager.defaultVibrator.cancel()
            } else {
                @Suppress("DEPRECATION")
                val vibrator = context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
                vibrator.cancel()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to cancel vibration", e)
        }
    }
}
