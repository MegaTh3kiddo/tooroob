package ir.torob.seller.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.expandVertically
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ir.torob.seller.ui.theme.TorobWarning
import ir.torob.seller.ui.theme.TorobInfo
import ir.torob.seller.util.PersianFormatters

@Composable
fun ConnectionStatusBar(
    isOnline: Boolean,
    pendingSyncCount: Int = 0
) {
    AnimatedVisibility(
        visible = !isOnline || pendingSyncCount > 0,
        enter = expandVertically(),
        exit = shrinkVertically()
    ) {
        val bgColor = if (!isOnline) TorobWarning else TorobInfo
        val text = if (!isOnline) {
            if (pendingSyncCount > 0) {
                "عدم اتصال به شبکه • ${PersianFormatters.toPersianDigits(pendingSyncCount)} پاسخ در حافظه گوشی ذخیره شده و پس از اتصال ارسال می‌شود"
            } else {
                "عدم اتصال به شبکه (حالت آفلاین فعال است)"
            }
        } else {
            "در حال همگام‌سازی ${PersianFormatters.toPersianDigits(pendingSyncCount)} پاسخ ذخیره‌شده با سرور..."
        }

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(bgColor)
                .padding(horizontal = 16.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center
        ) {
            Text(
                text = text,
                color = Color.White,
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold
            )
        }
    }
}
