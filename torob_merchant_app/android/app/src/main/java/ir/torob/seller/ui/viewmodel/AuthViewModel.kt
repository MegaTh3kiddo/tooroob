package ir.torob.seller.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import ir.torob.seller.data.repository.AuthRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class AuthUiState(
    val phoneNumber: String = "",
    val otpCode: String = "",
    val isLoading: Boolean = false,
    val demoOtp: String? = null,
    val errorMessage: String? = null,
    val isOtpSent: Boolean = false,
    val isLoggedIn: Boolean = false
)

class AuthViewModel(private val repository: AuthRepository) : ViewModel() {

    private val _uiState = MutableStateFlow(AuthUiState(isLoggedIn = repository.hasToken()))
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()

    fun onPhoneChanged(phone: String) {
        _uiState.value = _uiState.value.copy(phoneNumber = phone, errorMessage = null)
    }

    fun onOtpChanged(otp: String) {
        _uiState.value = _uiState.value.copy(otpCode = otp, errorMessage = null)
    }

    fun loginDemoSeller() {
        val phone = _uiState.value.phoneNumber.ifBlank { "09134257815" }
        repository.loginDemoSeller(phone)
        _uiState.value = _uiState.value.copy(isLoggedIn = true, isLoading = false)
    }

    fun requestOtp() {
        if (ir.torob.seller.BuildConfig.SKIP_OTP_AUTH) {
            loginDemoSeller()
            return
        }

        val phone = _uiState.value.phoneNumber.trim()
        if (phone.length < 10) {
            _uiState.value = _uiState.value.copy(errorMessage = "شماره موبایل وارد شده باید حداقل ۱۰ رقم باشد")
            return
        }

        _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
        viewModelScope.launch {
            repository.requestOtp(phone)
                .onSuccess { resp ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        isOtpSent = true,
                        demoOtp = resp.demoOtp
                    )
                }
                .onFailure { err ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        errorMessage = err.message ?: "خطا در برقراری ارتباط با سرور"
                    )
                }
        }
    }

    fun verifyOtp() {
        val phone = _uiState.value.phoneNumber.trim()
        val code = _uiState.value.otpCode.trim()

        if (code.isEmpty()) {
            _uiState.value = _uiState.value.copy(errorMessage = "لطفا کد تایید را وارد نمایید")
            return
        }

        _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
        viewModelScope.launch {
            repository.verifyOtp(phone, code)
                .onSuccess {
                    _uiState.value = _uiState.value.copy(isLoading = false, isLoggedIn = true)
                }
                .onFailure { err ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        errorMessage = err.message ?: "کد تایید نادرست است"
                    )
                }
        }
    }

    fun logout() {
        repository.logout()
        _uiState.value = AuthUiState(isLoggedIn = false)
    }
}
