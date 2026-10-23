package ir.torob.seller.data.remote

import ir.torob.seller.data.model.*
import retrofit2.Response
import retrofit2.http.*

interface SellerApiService {

    // --- Auth ---
    @POST("seller/auth/request-otp")
    suspend fun requestOtp(@Body request: RequestOtpRequest): Response<RequestOtpResponse>

    @POST("seller/auth/verify-otp")
    suspend fun verifyOtp(@Body request: VerifyOtpRequest): Response<TokenResponse>

    @GET("seller/auth/me")
    suspend fun getMe(): Response<SellerDto>

    // --- Shop Profile ---
    @GET("seller/shop")
    suspend fun getShopProfile(): Response<ShopDto>

    @PUT("seller/shop")
    suspend fun updateShopProfile(@Body update: ShopUpdateDto): Response<ShopDto>

    @POST("seller/shop/toggle-status")
    suspend fun toggleShopStatus(): Response<ShopDto>

    @POST("seller/shop/change-requests")
    suspend fun submitChangeRequest(@Body request: ShopChangeRequestCreateDto): Response<ShopChangeRequestDto>

    @GET("seller/shop/change-requests/latest")
    suspend fun getLatestChangeRequest(): Response<ShopChangeRequestDto>

    // --- Inquiries ---
    @GET("seller/inquiries")
    suspend fun getInquiries(@Query("status") status: String? = null): Response<List<InquiryDto>>

    @GET("seller/inquiries/{id}")
    suspend fun getInquiryDetail(@Path("id") inquiryId: String): Response<InquiryDto>

    @POST("seller/inquiries/{id}/respond")
    suspend fun submitResponse(
        @Path("id") inquiryId: String,
        @Body response: InquiryResponseRequest
    ): Response<InquiryResponseDto>

    @POST("seller/inquiries/batch-sync")
    suspend fun batchSyncResponses(
        @Body batch: BatchSyncRequest
    ): Response<BatchSyncResponse>


    // --- Push Notifications ---
    @POST("seller/push/register-token")
    suspend fun registerPushToken(@Body payload: PushTokenRegisterRequest): Response<Map<String, Any>>

    @PUT("seller/push/preferences")
    suspend fun updatePushPreferences(@Body payload: PushPreferenceRequest): Response<Map<String, Any>>

    // --- Metrics ---
    @GET("seller/metrics")
    suspend fun getStoreMetrics(): Response<MetricsDto>
}
