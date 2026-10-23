package ir.torob.seller.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ir.torob.seller.ui.theme.*
import ir.torob.seller.util.PersianFormatters
import java.text.DecimalFormat

@Composable
fun PriceInputField(
    priceToman: Long,
    onPriceChange: (Long) -> Unit,
    modifier: Modifier = Modifier,
    label: String = "قیمت پیشنهادی",
    enabled: Boolean = true,
    isError: Boolean = false,
    errorMessage: String? = null
) {
    val formatter = remember { DecimalFormat("#,###") }

    // Format initial / incoming value with thousands separator
    val displayValue = if (priceToman > 0) formatter.format(priceToman) else ""

    Column(modifier = modifier.fillMaxWidth()) {
        OutlinedTextField(
            value = displayValue,
            onValueChange = { input ->
                val normalized = input.map { ch ->
                    when (ch) {
                        in '0'..'9' -> ch
                        in '۰'..'۹' -> '0' + (ch - '۰')
                        in '٠'..'٩' -> '0' + (ch - '٠')
                        else -> ch
                    }
                }.joinToString("")

                val digitsOnly = normalized.filter { it.isDigit() }
                val newPrice = digitsOnly.toLongOrNull() ?: 0L
                onPriceChange(newPrice)
            },
            enabled = enabled,
            isError = isError,
            label = { Text(label, fontSize = 13.sp) },
            trailingIcon = {
                Text(
                    text = "تومان",
                    color = if (enabled) TorobRed else MaterialTheme.colorScheme.onSurfaceVariant,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(end = 12.dp)
                )
            },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = TorobRed,
                unfocusedBorderColor = MaterialTheme.colorScheme.outline,
                focusedLabelColor = TorobRed,
                unfocusedLabelColor = MaterialTheme.colorScheme.onSurfaceVariant,
                focusedContainerColor = MaterialTheme.colorScheme.surface,
                unfocusedContainerColor = MaterialTheme.colorScheme.surface,
                disabledContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                focusedTextColor = MaterialTheme.colorScheme.onSurface,
                unfocusedTextColor = MaterialTheme.colorScheme.onSurface
            ),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth()
        )

        // Supporting text with readable Persian digits preview
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 4.dp, start = 4.dp, end = 4.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            if (isError && errorMessage != null) {
                Text(
                    text = errorMessage,
                    color = TorobError,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium
                )
            } else if (priceToman > 0) {
                Text(
                    text = "معادل: ${PersianFormatters.formatPriceToman(priceToman)}",
                    color = TorobRed,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold
                )
            } else {
                Text(
                    text = "قیمت را به تومان وارد نمایید",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    fontSize = 11.sp
                )
            }
        }
    }
}
