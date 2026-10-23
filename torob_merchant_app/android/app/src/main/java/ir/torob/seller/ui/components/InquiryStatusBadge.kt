package ir.torob.seller.ui.components

import android.os.SystemClock
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessTime
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.HourglassEmpty
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ir.torob.seller.ui.theme.*
import ir.torob.seller.util.PersianFormatters
import kotlinx.coroutines.delay

@Composable
fun InquiryStatusBadge(
    status: String,
    remainingSeconds: Long = 0L,
    modifier: Modifier = Modifier,
    autoCountdown: Boolean = true
) {
    var liveSeconds by remember(status, remainingSeconds) { mutableLongStateOf(remainingSeconds) }

    LaunchedEffect(status, remainingSeconds, autoCountdown) {
        if (autoCountdown && status.equals("ACTIVE", ignoreCase = true) && remainingSeconds > 0) {
            val startElapsed = SystemClock.elapsedRealtime()
            val initialSeconds = remainingSeconds
            liveSeconds = initialSeconds
            while (liveSeconds > 0) {
                delay(1000L)
                val elapsed = (SystemClock.elapsedRealtime() - startElapsed) / 1000L
                liveSeconds = maxOf(0L, initialSeconds - elapsed)
            }
        } else {
            liveSeconds = remainingSeconds
        }
    }

    val currentSeconds = if (autoCountdown) liveSeconds else remainingSeconds

    val (bgColor: Color, textColor: Color, icon: ImageVector, text: String) = when (status.uppercase()) {
        "ACTIVE" -> {
            if (currentSeconds in 1..180) {
                // Urgent: under 3 minutes left -> amber warning (NOT red)
                Tuple4(
                    TorobWarningLight,
                    WarningAmberDark,
                    Icons.Default.WarningAmber,
                    "فرصت فوری: ${PersianFormatters.formatRemainingTime(currentSeconds)}"
                )
            } else if (currentSeconds > 180) {
                // Active with standard countdown
                Tuple4(
                    TorobWarningLight,
                    TorobWarning,
                    Icons.Default.AccessTime,
                    "مهلت: ${PersianFormatters.formatRemainingTime(currentSeconds)}"
                )
            } else {
                Tuple4(
                    TorobBackground,
                    TorobTextSecondary,
                    Icons.Default.HourglassEmpty,
                    "منقضی شده"
                )
            }
        }
        "ANSWERED" -> {
            Tuple4(
                TorobSuccessLight,
                TorobSuccess,
                Icons.Default.Check,
                "پاسخ داده شد"
            )
        }
        "OUT_OF_STOCK" -> {
            Tuple4(
                TorobWarningLight,
                WarningAmberDark,
                Icons.Default.Close,
                "عدم موجودی"
            )
        }
        "DECLINED" -> {
            Tuple4(
                TorobErrorLight,
                TorobError,
                Icons.Default.Close,
                "رد شده"
            )
        }
        "EXPIRED" -> {
            Tuple4(
                TorobBackground,
                TorobTextSecondary,
                Icons.Default.HourglassEmpty,
                "منقضی شده"
            )
        }
        else -> {
            Tuple4(
                TorobBackground,
                TorobTextSecondary,
                Icons.Default.HourglassEmpty,
                status
            )
        }
    }

    Box(
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(bgColor)
            .padding(horizontal = 8.dp, vertical = 4.dp)
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = textColor,
                modifier = Modifier.size(13.dp)
            )
            Text(
                text = text,
                color = textColor,
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

private data class Tuple4<A, B, C, D>(
    val first: A,
    val second: B,
    val third: C,
    val fourth: D
)
