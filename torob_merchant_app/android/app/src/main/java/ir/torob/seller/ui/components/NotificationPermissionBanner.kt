package ir.torob.seller.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
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
import ir.torob.seller.ui.theme.*

@Composable
fun NotificationPermissionBanner(
    onEnableClicked: () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(TorobWarningLight)
            .border(1.dp, TorobWarning.copy(alpha = 0.35f), RoundedCornerShape(12.dp))
            .padding(14.dp)
    ) {
        Column {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Default.Notifications,
                    contentDescription = null,
                    tint = WarningAmberDark,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = "مجوز دریافت نوتیفیکیشن غیرفعال است!",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold,
                    color = WarningAmberDark
                )
            }
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "برای دریافت به موقع استعلام خریداران و جلوگیری از دست رفتن مهلت ۵ دقیقه‌ای، مجوز اعلان‌های برنامه را فعال کنید.",
                fontSize = 12.sp,
                color = TorobTextPrimary,
                lineHeight = 18.sp
            )
            Spacer(modifier = Modifier.height(10.dp))
            Button(
                onClick = onEnableClicked,
                colors = ButtonDefaults.buttonColors(containerColor = TorobWarning),
                shape = RoundedCornerShape(8.dp),
                contentPadding = PaddingValues(horizontal = 14.dp, vertical = 6.dp),
                modifier = Modifier.align(Alignment.End)
            ) {
                Text(
                    text = "فعال‌سازی در تنظیمات گوشی",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    color = PureWhite
                )
            }
        }
    }
}
