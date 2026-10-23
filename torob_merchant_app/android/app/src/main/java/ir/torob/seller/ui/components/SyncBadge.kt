package ir.torob.seller.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ir.torob.seller.data.local.SyncState
import ir.torob.seller.ui.theme.*

@Composable
fun SyncBadge(
    syncState: SyncState?,
    modifier: Modifier = Modifier
) {
    // Do not display 'ثبت نهایی در سرور' when successfully synced on server. Only show pending offline states.
    if (syncState == null || syncState == SyncState.SYNCED_ON_SERVER) return

    val (bg, textColor, icon, label) = when (syncState) {
        SyncState.SYNCED_ON_SERVER -> return
        SyncState.SAVED_ON_PHONE -> Quadruple(
            TorobWarningLight,
            TorobWarning,
            Icons.Default.Schedule,
            "ذخیره در گوشی (در انتظار ارسال)"
        )
        SyncState.UPLOADING -> Quadruple(
            TorobInfoLight,
            TorobInfo,
            Icons.Default.Sync,
            "در حال مخابره به سرور..."
        )
        SyncState.FAILED_EXPIRED -> Quadruple(
            TorobErrorLight,
            TorobError,
            Icons.Default.ErrorOutline,
            "خطا در ارسال یا منقضی‌شده"
        )
    }

    Box(
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(bg)
            .padding(horizontal = 8.dp, vertical = 4.dp),
        contentAlignment = Alignment.Center
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = textColor,
                modifier = Modifier.size(13.dp)
            )
            Spacer(modifier = Modifier.width(4.dp))
            Text(
                text = label,
                color = textColor,
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

private data class Quadruple<A, B, C, D>(
    val first: A,
    val second: B,
    val third: C,
    val fourth: D
)
