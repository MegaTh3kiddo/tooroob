package ir.torob.seller.data.repository

import android.content.Context
import ir.torob.seller.data.model.ShopChangeRequestCreateDto
import ir.torob.seller.data.model.ShopChangeRequestDto
import ir.torob.seller.data.model.ShopDto
import ir.torob.seller.data.model.ShopUpdateDto
import ir.torob.seller.data.remote.ApiClient

class ShopRepository(private val context: Context) {
    private val api get() = ApiClient.getService(context)

    private fun parseErrorMessage(errorBody: String?, fallback: String): String {
        if (errorBody.isNullOrBlank()) return fallback
        return try {
            val json = org.json.JSONObject(errorBody)
            if (json.has("detail")) json.getString("detail") else fallback
        } catch (_: Exception) {
            errorBody
        }
    }

    suspend fun getShopProfile(): Result<ShopDto> {
        return try {
            val resp = api.getShopProfile()
            if (resp.isSuccessful && resp.body() != null) {
                Result.success(resp.body()!!)
            } else {
                val err = parseErrorMessage(resp.errorBody()?.string(), "خطا در دریافت اطلاعات فروشگاه")
                Result.failure(Exception(err))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun updateShopProfile(update: ShopUpdateDto): Result<ShopDto> {
        return try {
            val resp = api.updateShopProfile(update)
            if (resp.isSuccessful && resp.body() != null) {
                Result.success(resp.body()!!)
            } else {
                val err = parseErrorMessage(resp.errorBody()?.string(), "خطا در ویرایش فروشگاه")
                Result.failure(Exception(err))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun toggleShopStatus(): Result<ShopDto> {
        return try {
            val resp = api.toggleShopStatus()
            if (resp.isSuccessful && resp.body() != null) {
                Result.success(resp.body()!!)
            } else {
                val err = parseErrorMessage(resp.errorBody()?.string(), "خطا در تغییر وضعیت فروشگاه")
                Result.failure(Exception(err))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun submitChangeRequest(request: ShopChangeRequestCreateDto): Result<ShopChangeRequestDto> {
        return try {
            val resp = api.submitChangeRequest(request)
            if (resp.isSuccessful && resp.body() != null) {
                Result.success(resp.body()!!)
            } else {
                val err = parseErrorMessage(resp.errorBody()?.string(), "خطا در ثبت درخواست تغییر اطلاعات")
                Result.failure(Exception(err))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getLatestChangeRequest(): Result<ShopChangeRequestDto?> {
        return try {
            val resp = api.getLatestChangeRequest()
            if (resp.isSuccessful) {
                Result.success(resp.body())
            } else {
                val err = parseErrorMessage(resp.errorBody()?.string(), "خطا در دریافت وضعیت درخواست")
                Result.failure(Exception(err))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
