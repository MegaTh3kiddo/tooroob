package ir.torob.seller.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import ir.torob.seller.data.model.ShopChangeRequestCreateDto
import ir.torob.seller.data.model.ShopChangeRequestDto
import ir.torob.seller.data.model.ShopDto
import ir.torob.seller.data.model.ShopUpdateDto
import ir.torob.seller.data.repository.ShopRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class StoreUiState(
    val shop: ShopDto? = null,
    val latestChangeRequest: ShopChangeRequestDto? = null,
    val isLoading: Boolean = false,
    val isSaving: Boolean = false,
    val isSubmittingRequest: Boolean = false,
    val errorMessage: String? = null,
    val successMessage: String? = null,
    val requestSuccessMessage: String? = null,
    val requestErrorMessage: String? = null
)

class StoreViewModel(private val repository: ShopRepository) : ViewModel() {

    private val _uiState = MutableStateFlow(StoreUiState())
    val uiState: StateFlow<StoreUiState> = _uiState.asStateFlow()

    init {
        loadProfile()
    }

    fun loadProfile() {
        _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
        viewModelScope.launch {
            repository.getShopProfile()
                .onSuccess { shop ->
                    _uiState.value = _uiState.value.copy(isLoading = false, shop = shop)
                }
                .onFailure { err ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        errorMessage = err.message ?: "خطا در دریافت اطلاعات فروشگاه"
                    )
                }
            loadLatestChangeRequest()
        }
    }

    fun loadLatestChangeRequest() {
        viewModelScope.launch {
            repository.getLatestChangeRequest()
                .onSuccess { req ->
                    _uiState.value = _uiState.value.copy(latestChangeRequest = req)
                }
                .onFailure {
                    // Ignore background load error for requests
                }
        }
    }

    fun submitChangeRequest(
        request: ShopChangeRequestCreateDto,
        onComplete: (Boolean) -> Unit = {}
    ) {
        _uiState.value = _uiState.value.copy(
            isSubmittingRequest = true,
            requestErrorMessage = null,
            requestSuccessMessage = null
        )
        viewModelScope.launch {
            repository.submitChangeRequest(request)
                .onSuccess { created ->
                    _uiState.value = _uiState.value.copy(
                        isSubmittingRequest = false,
                        latestChangeRequest = created,
                        requestSuccessMessage = "درخواست شما با موفقیت به پشتیبانی ترب ارسال شد."
                    )
                    onComplete(true)
                }
                .onFailure { err ->
                    _uiState.value = _uiState.value.copy(
                        isSubmittingRequest = false,
                        requestErrorMessage = err.message ?: "خطا در ثبت درخواست تغییر اطلاعات"
                    )
                    onComplete(false)
                }
        }
    }

    fun clearRequestMessages() {
        _uiState.value = _uiState.value.copy(
            requestSuccessMessage = null,
            requestErrorMessage = null
        )
    }

    fun toggleOpenStatus() {
        _uiState.value = _uiState.value.copy(isSaving = true, errorMessage = null, successMessage = null)
        viewModelScope.launch {
            repository.toggleShopStatus()
                .onSuccess { updated ->
                    _uiState.value = _uiState.value.copy(
                        isSaving = false,
                        shop = updated,
                        successMessage = if (updated.isOpen) "فروشگاه با موفقیت باز شد" else "فروشگاه بسته شد",
                        errorMessage = null
                    )
                }
                .onFailure { err ->
                    _uiState.value = _uiState.value.copy(
                        isSaving = false,
                        errorMessage = err.message ?: "خطا در تغییر وضعیت",
                        successMessage = null
                    )
                }
        }
    }

    fun updateProfile(update: ShopUpdateDto) {
        _uiState.value = _uiState.value.copy(isSaving = true, errorMessage = null, successMessage = null)
        viewModelScope.launch {
            repository.updateShopProfile(update)
                .onSuccess { updated ->
                    _uiState.value = _uiState.value.copy(
                        isSaving = false,
                        shop = updated,
                        successMessage = "اطلاعات فروشگاه با موفقیت ویرایش شد",
                        errorMessage = null
                    )
                }
                .onFailure { err ->
                    _uiState.value = _uiState.value.copy(
                        isSaving = false,
                        errorMessage = err.message ?: "خطا در ثبت تغییرات",
                        successMessage = null
                    )
                }
        }
    }
}
