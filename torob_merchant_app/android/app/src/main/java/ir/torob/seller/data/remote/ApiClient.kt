package ir.torob.seller.data.remote

import android.content.Context
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {
    // 127.0.0.1 with adb reverse routes to host localhost:8080 via USB
    private const val DEFAULT_BASE_URL = "http://127.0.0.1:8080/api/"

    private var service: SellerApiService? = null

    fun getService(context: Context): SellerApiService {
        if (service == null) {
            val prefs = context.getSharedPreferences("seller_auth_prefs", Context.MODE_PRIVATE)
            val customUrl = prefs.getString("custom_server_url", null)
            val baseUrl = if (!customUrl.isNullOrBlank()) customUrl else DEFAULT_BASE_URL

            val logging = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            }

            val okHttpClient = OkHttpClient.Builder()
                .addInterceptor(AuthInterceptor(context))
                .addInterceptor(logging)
                .connectTimeout(15, TimeUnit.SECONDS)
                .readTimeout(15, TimeUnit.SECONDS)
                .writeTimeout(15, TimeUnit.SECONDS)
                .build()

            val retrofit = Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()

            service = retrofit.create(SellerApiService::class.java)
        }
        return service!!
    }

    fun resetClient() {
        service = null
    }
}
