package ir.torob.seller.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.HourglassTop
import androidx.compose.material.icons.filled.Inbox
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
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

@Composable
fun InquirySummaryCards(
    activeCount: Int,
    urgentCount: Int,
    selectedFilter: String,
    onFilterSelected: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        SummaryCardItem(
            title = "کل در انتظار",
            count = activeCount,
            icon = Icons.Default.Inbox,
            accentColor = TorobRed,
            bgColor = TorobRedLight,
            isSelected = selectedFilter == "ALL",
            onClick = { onFilterSelected("ALL") },
            modifier = Modifier.weight(1f)
        )

        SummaryCardItem(
            title = "نیاز به اقدام فوری",
            count = urgentCount,
            icon = Icons.Default.WarningAmber,
            accentColor = TorobWarning,
            bgColor = TorobWarningLight,
            isSelected = selectedFilter == "URGENT",
            onClick = { onFilterSelected("URGENT") },
            modifier = Modifier.weight(1f)
        )

        SummaryCardItem(
            title = "مهلت عادی",
            count = (activeCount - urgentCount).coerceAtLeast(0),
            icon = Icons.Default.HourglassTop,
            accentColor = MaterialTheme.colorScheme.onSurfaceVariant,
            bgColor = MaterialTheme.colorScheme.surfaceVariant,
            isSelected = selectedFilter == "NORMAL",
            onClick = { onFilterSelected("NORMAL") },
            modifier = Modifier.weight(1f)
        )
    }
}

@Composable
private fun SummaryCardItem(
    title: String,
    count: Int,
    icon: ImageVector,
    accentColor: Color,
    bgColor: Color,
    isSelected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val borderModifier = if (isSelected) {
        Modifier.border(1.5.dp, accentColor, RoundedCornerShape(12.dp))
    } else {
        Modifier.border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(12.dp))
    }

    Card(
        modifier = modifier
            .then(borderModifier)
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = if (isSelected) 2.dp else 0.dp)
    ) {
        Column(
            modifier = Modifier.padding(10.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(24.dp)
                        .clip(RoundedCornerShape(6.dp))
                        .background(bgColor),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = icon,
                        contentDescription = null,
                        tint = accentColor,
                        modifier = Modifier.size(14.dp)
                    )
                }

                Text(
                    text = PersianFormatters.toPersianDigits(count),
                    fontSize = 17.sp,
                    fontWeight = FontWeight.Black,
                    color = accentColor
                )
            }

            Text(
                text = title,
                fontSize = 11.sp,
                color = if (isSelected) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant,
                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                maxLines = 1
            )
        }
    }
}
