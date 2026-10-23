package ir.torob.seller.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone

@Entity(tableName = "inquiries")
data class InquiryEntity(
    @PrimaryKey val inquiryId: String,
    val trackingCode: String,
    val shopId: String,
    val productId: String?,
    val productTitle: String,
    val productImageUrl: String?,
    val categoryName: String?,
    val recordedPriceToman: Long,
    val customerName: String,
    val customerPhone: String?,
    val inquiryType: String,
    val userNote: String?,
    val status: String, // ACTIVE, ANSWERED, OUT_OF_STOCK, DECLINED, EXPIRED
    val createdAt: String,
    val expiresAt: String,
    val remainingSeconds: Long,
    val declineReason: String? = null,
    val responsePrice: Long? = null,
    val responseInStock: Boolean? = null,
    val responseNotes: String? = null,
    val lastCachedAt: Long = System.currentTimeMillis()
)

fun InquiryEntity.toDto() = ir.torob.seller.data.model.InquiryDto(
    inquiryId = inquiryId,
    trackingCode = trackingCode,
    shopId = shopId,
    productId = productId,
    productTitle = productTitle,
    productImageUrl = productImageUrl,
    categoryName = categoryName,
    recordedPriceToman = recordedPriceToman,
    customerName = customerName,
    customerPhone = customerPhone,
    inquiryType = inquiryType,
    userNote = userNote,
    status = status,
    createdAt = createdAt,
    expiresAt = expiresAt,
    remainingSeconds = remainingSeconds,
    declineReason = declineReason,
    responsePrice = responsePrice,
    responseInStock = responseInStock,
    responseNotes = responseNotes
)

fun ir.torob.seller.data.model.InquiryDto.toEntity() = InquiryEntity(
    inquiryId = inquiryId,
    trackingCode = trackingCode,
    shopId = shopId,
    productId = productId,
    productTitle = productTitle,
    productImageUrl = productImageUrl,
    categoryName = categoryName,
    recordedPriceToman = recordedPriceToman,
    customerName = customerName,
    customerPhone = customerPhone,
    inquiryType = inquiryType,
    userNote = userNote,
    status = status,
    createdAt = createdAt,
    expiresAt = expiresAt,
    remainingSeconds = remainingSeconds,
    declineReason = declineReason,
    responsePrice = responsePrice,
    responseInStock = responseInStock,
    responseNotes = responseNotes
)

fun InquiryEntity.getLiveRemainingSeconds(): Long {
    try {
        val sdf = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }
        val expDate = sdf.parse(expiresAt.replace("T", " ").replace("Z", ""))
        if (expDate != null) {
            val diffSec = (expDate.time - System.currentTimeMillis()) / 1000L
            return maxOf(0L, diffSec)
        }
    } catch (_: Exception) {}

    val elapsed = (System.currentTimeMillis() - lastCachedAt) / 1000L
    return maxOf(0L, remainingSeconds - elapsed)
}

