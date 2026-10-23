package ir.torob.seller.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ir.torob.seller.ui.theme.*

@Composable
fun QuickPriceChips(
    currentPrice: Long,
    recordedPrice: Long,
    onPriceSelected: (Long) -> Unit,
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier.fillMaxWidth()) {
        Text(
            text = "تغییر سریع قیمت با یک لمس:",
            fontSize = 12.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            fontWeight = FontWeight.Medium,
            modifier = Modifier.padding(bottom = 6.dp)
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            QuickPriceChipItem(
                label = "قیمت مرجع",
                onClick = { onPriceSelected(recordedPrice) },
                modifier = Modifier.weight(1f)
            )
            QuickPriceChipItem(
                label = "۵۰- هزار",
                onClick = { onPriceSelected(maxOf(0L, currentPrice - 50_000)) },
                modifier = Modifier.weight(1f)
            )
            QuickPriceChipItem(
                label = "۵۰+ هزار",
                onClick = { onPriceSelected(currentPrice + 50_000) },
                modifier = Modifier.weight(1f)
            )
            QuickPriceChipItem(
                label = "۱۰۰+ هزار",
                onClick = { onPriceSelected(currentPrice + 100_000) },
                modifier = Modifier.weight(1f)
            )
        }
    }
}

@Composable
private fun QuickPriceChipItem(
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(8.dp),
        color = MaterialTheme.colorScheme.surfaceVariant,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        modifier = modifier.height(36.dp)
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 4.dp),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = label,
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 1,
                softWrap = false
            )
        }
    }
}

