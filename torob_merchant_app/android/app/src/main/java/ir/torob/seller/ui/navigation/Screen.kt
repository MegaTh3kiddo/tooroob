package ir.torob.seller.ui.navigation

sealed class Screen(val route: String) {
    object Login : Screen("login")
    object OtpVerify : Screen("otp_verify/{phone}") {
        fun createRoute(phone: String) = "otp_verify/$phone"
    }
    object Inquiries : Screen("inquiries")
    object InquiryDetail : Screen("inquiry_detail/{inquiryId}") {
        fun createRoute(inquiryId: String) = "inquiry_detail/$inquiryId"
    }
    object History : Screen("history")
    object StoreProfile : Screen("store_profile")
    object Metrics : Screen("metrics")
    object Settings : Screen("settings")
}
