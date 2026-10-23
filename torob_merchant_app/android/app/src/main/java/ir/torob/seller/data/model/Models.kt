package ir.torob.seller.data.model

import com.google.gson.annotations.SerializedName

// --- Authentication Models ---
data class RequestOtpRequest(
    @SerializedName("phone_number") val phoneNumber: String
)

data class RequestOtpResponse(
    @SerializedName("success") val success: Boolean,
    @SerializedName("message") val message: String,
    @SerializedName("demo_otp") val demoOtp: String? = null
)

data class VerifyOtpRequest(
    @SerializedName("phone_number") val phoneNumber: String,
    @SerializedName("otp_code") val otpCode: String
)

data class SellerDto(
    @SerializedName("seller_id") val sellerId: String,
    @SerializedName("phone_number") val phoneNumber: String,
    @SerializedName("shop_id") val shopId: String,
    @SerializedName("full_name") val fullName: String?,
    @SerializedName("is_active") val isActive: Boolean
)

data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String,
    @SerializedName("seller") val seller: SellerDto
)

// --- Shop Models ---
data class ShopDto(
    @SerializedName("shop_id") val shopId: String,
    @SerializedName("shop_name") val shopName: String,
    @SerializedName("address") val address: String,
    @SerializedName("phone") val phone: String,
    @SerializedName("is_open") val isOpen: Boolean,
    @SerializedName("open_time") val openTime: String,
    @SerializedName("close_time") val closeTime: String,
    @SerializedName("accept_inquiries") val acceptInquiries: Boolean,
    @SerializedName("holiday_mode") val holidayMode: Boolean,
    @SerializedName("manual_is_open") val manualIsOpen: Boolean = true,
    @SerializedName("is_within_working_hours") val isWithinWorkingHours: Boolean = true,
    @SerializedName("status_message") val statusMessage: String? = null
)

data class ShopUpdateDto(
    @SerializedName("shop_name") val shopName: String? = null,
    @SerializedName("address") val address: String? = null,
    @SerializedName("phone") val phone: String? = null,
    @SerializedName("is_open") val isOpen: Boolean? = null,
    @SerializedName("open_time") val openTime: String? = null,
    @SerializedName("close_time") val closeTime: String? = null,
    @SerializedName("accept_inquiries") val acceptInquiries: Boolean? = null,
    @SerializedName("holiday_mode") val holidayMode: Boolean? = null
)

data class ShopChangeRequestCreateDto(
    @SerializedName("requested_shop_name") val requestedShopName: String? = null,
    @SerializedName("requested_phone") val requestedPhone: String? = null,
    @SerializedName("requested_address") val requestedAddress: String? = null,
    @SerializedName("requested_open_time") val requestedOpenTime: String? = null,
    @SerializedName("requested_close_time") val requestedCloseTime: String? = null,
    @SerializedName("reason") val reason: String? = null
)

data class ShopChangeRequestDto(
    @SerializedName("request_id") val requestId: String,
    @SerializedName("shop_id") val shopId: String,
    @SerializedName("seller_id") val sellerId: String,
    @SerializedName("requested_shop_name") val requestedShopName: String? = null,
    @SerializedName("requested_phone") val requestedPhone: String? = null,
    @SerializedName("requested_address") val requestedAddress: String? = null,
    @SerializedName("requested_open_time") val requestedOpenTime: String? = null,
    @SerializedName("requested_close_time") val requestedCloseTime: String? = null,
    @SerializedName("reason") val reason: String? = null,
    @SerializedName("status") val status: String,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("reviewed_at") val reviewedAt: String? = null,
    @SerializedName("review_notes") val reviewNotes: String? = null
)

// --- Inquiry Models ---
data class InquiryDto(
    @SerializedName("inquiry_id") val inquiryId: String,
    @SerializedName("tracking_code") val trackingCode: String,
    @SerializedName("shop_id") val shopId: String,
    @SerializedName("product_id") val productId: String? = null,
    @SerializedName("product_title") val productTitle: String,
    @SerializedName("product_image_url") val productImageUrl: String? = null,
    @SerializedName("category_name") val categoryName: String? = null,
    @SerializedName("recorded_price_toman") val recordedPriceToman: Long,
    @SerializedName("customer_name") val customerName: String,
    @SerializedName("customer_phone") val customerPhone: String? = null,
    @SerializedName("inquiry_type") val inquiryType: String,
    @SerializedName("user_note") val userNote: String? = null,
    @SerializedName("status") val status: String, // ACTIVE, ANSWERED, OUT_OF_STOCK, DECLINED, EXPIRED
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("expires_at") val expiresAt: String,
    @SerializedName("remaining_seconds") val remainingSeconds: Long = 0,
    @SerializedName("decline_reason") val declineReason: String? = null,
    @SerializedName("response_price") val responsePrice: Long? = null,
    @SerializedName("response_in_stock") val responseInStock: Boolean? = null,
    @SerializedName("response_notes") val responseNotes: String? = null
)

data class InquiryResponseRequest(
    @SerializedName("client_response_id") val clientResponseId: String,
    @SerializedName("offered_price_toman") val offeredPriceToman: Long,
    @SerializedName("is_in_stock") val isInStock: Boolean,
    @SerializedName("stock_count") val stockCount: Int = 1,
    @SerializedName("notes") val notes: String?,
    @SerializedName("status") val status: String? = null,
    @SerializedName("decline_reason") val declineReason: String? = null,
    @SerializedName("submitted_at") val submittedAt: String
)

data class InquiryResponseDto(
    @SerializedName("response_id") val responseId: String,
    @SerializedName("client_response_id") val clientResponseId: String,
    @SerializedName("inquiry_id") val inquiryId: String,
    @SerializedName("offered_price_toman") val offeredPriceToman: Long,
    @SerializedName("is_in_stock") val isInStock: Boolean,
    @SerializedName("stock_count") val stockCount: Int = 1,
    @SerializedName("notes") val notes: String?,
    @SerializedName("status") val status: String? = null,
    @SerializedName("decline_reason") val declineReason: String? = null,
    @SerializedName("submitted_at") val submittedAt: String,
    @SerializedName("received_at") val receivedAt: String,
    @SerializedName("is_duplicate") val isDuplicate: Boolean = false
)

data class BatchSyncItem(
    @SerializedName("inquiry_id") val inquiryId: String,
    @SerializedName("client_response_id") val clientResponseId: String,
    @SerializedName("offered_price_toman") val offeredPriceToman: Long,
    @SerializedName("is_in_stock") val isInStock: Boolean,
    @SerializedName("stock_count") val stockCount: Int = 1,
    @SerializedName("notes") val notes: String?,
    @SerializedName("status") val status: String? = null,
    @SerializedName("decline_reason") val declineReason: String? = null,
    @SerializedName("submitted_at") val submittedAt: String
)

data class BatchSyncRequest(
    @SerializedName("items") val items: List<BatchSyncItem>
)

data class BatchSyncResponse(
    @SerializedName("total_processed") val totalProcessed: Int,
    @SerializedName("synced_count") val syncedCount: Int,
    @SerializedName("duplicate_count") val duplicateCount: Int,
    @SerializedName("results") val results: List<InquiryResponseDto>
)

// --- Push Models ---
data class PushTokenRegisterRequest(
    @SerializedName("fcm_token") val fcmToken: String,
    @SerializedName("device_model") val deviceModel: String? = null,
    @SerializedName("os_version") val osVersion: String? = null,
    @SerializedName("app_version") val appVersion: String? = null,
    @SerializedName("notifications_enabled") val notificationsEnabled: Boolean = true
)

data class PushPreferenceRequest(
    @SerializedName("notifications_enabled") val notificationsEnabled: Boolean
)

data class PushLogDto(
    @SerializedName("log_id") val logId: String,
    @SerializedName("inquiry_id") val inquiryId: String?,
    @SerializedName("shop_id") val shopId: String?,
    @SerializedName("fcm_token") val fcmToken: String?,
    @SerializedName("notification_type") val notificationType: String,
    @SerializedName("title") val title: String,
    @SerializedName("body") val body: String,
    @SerializedName("status") val status: String,
    @SerializedName("error_detail") val errorDetail: String?,
    @SerializedName("dispatched_at") val dispatchedAt: String
)

// --- Metrics Models ---
data class MetricsDto(
    @SerializedName("shop_id") val shopId: String,
    @SerializedName("total_inquiries") val totalInquiries: Int,
    @SerializedName("answered_inquiries") val answeredInquiries: Int,
    @SerializedName("expired_inquiries") val expiredInquiries: Int,
    @SerializedName("active_inquiries") val activeInquiries: Int,
    @SerializedName("response_rate_percent") val responseRatePercent: Float,
    @SerializedName("average_response_time_seconds") val averageResponseTimeSeconds: Int,
    @SerializedName("average_response_time_formatted") val averageResponseTimeFormatted: String
)
