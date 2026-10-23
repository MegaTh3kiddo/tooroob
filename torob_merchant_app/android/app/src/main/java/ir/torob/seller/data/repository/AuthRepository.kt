package ir.torob.seller.data.repository

import android.content.Context
import android.content.SharedPreferences
import ir.torob.seller.data.model.*
import ir.torob.seller.data.remote.ApiClient
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class AuthRepository(private val context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("seller_auth_prefs", Context.MODE_PRIVATE)

    private val api = ApiClient.getService(context)

    private val _isLoggedIn = MutableStateFlow(hasToken())
    val isLoggedIn: StateFlow<Boolean> = _isLoggedIn.asStateFlow()

    fun hasToken(): Boolean = !prefs.getString("access_token", null).isNullOrEmpty()

    fun getAccessToken(): String? = prefs.getString("access_token", null)

    fun getShopId(): String = prefs.getString("shop_id", "shop_fazel_computer") ?: "shop_fazel_computer"

    fun getSellerName(): String = prefs.getString("full_name", "علی فاضل نیا (فروشگاه کامپیوتر فاضل‌نیا)") ?: "علی فاضل نیا (فروشگاه کامپیوتر فاضل‌نیا)"

    fun getPhoneNumber(): String = prefs.getString("phone_number", "09134257815") ?: "09134257815"

    fun getSellerId(): String = prefs.getString("seller_id", "seller_ali_fazelnya") ?: "seller_ali_fazelnya"

    suspend fun requestOtp(phone: String): Result<RequestOtpResponse> {
        return try {
            val response = api.requestOtp(RequestOtpRequest(phone))
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(response.errorBody()?.string() ?: "خطا در درخواست کد تایید"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun verifyOtp(phone: String, code: String): Result<TokenResponse> {
        return try {
            val response = api.verifyOtp(VerifyOtpRequest(phone, code))
            if (response.isSuccessful && response.body() != null) {
                val tokenResp = response.body()!!
                prefs.edit()
                    .putString("access_token", tokenResp.accessToken)
                    .putString("seller_id", tokenResp.seller.sellerId)
                    .putString("shop_id", tokenResp.seller.shopId)
                    .putString("phone_number", tokenResp.seller.phoneNumber)
                    .putString("full_name", tokenResp.seller.fullName)
                    .apply()
                _isLoggedIn.value = true
                Result.success(tokenResp)
            } else {
                Result.failure(Exception(response.errorBody()?.string() ?: "کد تایید اشتباه یا منقضی است"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    fun loginDemoSeller(customPhone: String = "09134257815") {
        val phone = if (customPhone.isNotBlank() && customPhone != "09123456789") customPhone else "09134257815"
        val isFazel = phone == "09134257815"
        val sellerId = if (isFazel) "seller_ali_fazelnya" else "seller_test_001"
        val shopId = if (isFazel) "shop_fazel_computer" else "shop_51d0c1a6edf81ba759726bab"
        val fullName = if (isFazel) "علی فاضل نیا (فروشگاه کامپیوتر فاضل‌نیا)" else "علی رضایی (فروشگاه موبایل تخت جمشید)"

        prefs.edit()
            .putString("access_token", "token_$sellerId")
            .putString("seller_id", sellerId)
            .putString("shop_id", shopId)
            .putString("phone_number", phone)
            .putString("full_name", fullName)
            .apply()
        _isLoggedIn.value = true
    }

    fun logout() {
        prefs.edit().clear().apply()
        _isLoggedIn.value = false
        kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.IO).launch {
            try {
                InquiryRepository(context).clearAllLocalData()
            } catch (e: Exception) {
                // ignore
            }
        }
    }
}
