package ir.torob.seller.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Inventory
import androidx.compose.material.icons.filled.Remove
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ir.torob.seller.ui.theme.*
import ir.torob.seller.util.PersianFormatters

@Composable
fun InventoryQuantitySelector(
    quantity: Int,
    onQuantityChange: (Int) -> Unit,
    modifier: Modifier = Modifier,
    minQuantity: Int = 1,
    maxQuantity: Int = 9999,
    enabled: Boolean = true
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        color = if (enabled) MaterialTheme.colorScheme.surface else MaterialTheme.colorScheme.surfaceVariant,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Right Side: Clean Label
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Inventory,
                    contentDescription = null,
                    tint = if (enabled) TorobRed else MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(20.dp)
                )
                Text(
                    text = "تعداد موجودی",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold,
                    color = if (enabled) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            // Left Side: Modern Touch-Friendly Segmented Counter
            Surface(
                shape = RoundedCornerShape(10.dp),
                color = MaterialTheme.colorScheme.surface,
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Decrement Button (−)
                    Box(
                        modifier = Modifier
                            .size(width = 42.dp, height = 40.dp)
                            .clip(RoundedCornerShape(topStart = 9.dp, bottomStart = 9.dp))
                            .clickable(
                                enabled = enabled && quantity > minQuantity,
                                onClick = { onQuantityChange(quantity - 1) }
                            )
                            .background(
                                if (enabled && quantity > minQuantity) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Remove,
                            contentDescription = "کاهش تعداد",
                            tint = if (enabled && quantity > minQuantity) TorobRed else MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.size(20.dp)
                        )
                    }

                    VerticalDivider(
                        modifier = Modifier.height(24.dp),
                        thickness = 1.dp,
                        color = MaterialTheme.colorScheme.outline
                    )

                    // Quantity Value Display
                    Box(
                        modifier = Modifier
                            .defaultMinSize(minWidth = 60.dp)
                            .padding(horizontal = 8.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "${PersianFormatters.toPersianDigits(quantity)} عدد",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                            color = if (enabled) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    VerticalDivider(
                        modifier = Modifier.height(24.dp),
                        thickness = 1.dp,
                        color = MaterialTheme.colorScheme.outline
                    )

                    // Increment Button (+)
                    Box(
                        modifier = Modifier
                            .size(width = 42.dp, height = 40.dp)
                            .clip(RoundedCornerShape(topEnd = 9.dp, bottomEnd = 9.dp))
                            .clickable(
                                enabled = enabled && quantity < maxQuantity,
                                onClick = { onQuantityChange(quantity + 1) }
                            )
                            .background(
                                if (enabled && quantity < maxQuantity) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Add,
                            contentDescription = "افزایش تعداد",
                            tint = if (enabled && quantity < maxQuantity) TorobRed else MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.size(20.dp)
                        )
                    }
                }
            }
        }
    }
}
