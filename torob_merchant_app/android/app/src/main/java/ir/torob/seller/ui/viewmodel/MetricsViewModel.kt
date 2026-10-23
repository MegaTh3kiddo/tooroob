package ir.torob.seller.ui.viewmodel

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import ir.torob.seller.data.model.MetricsDto
import ir.torob.seller.data.remote.ApiClient
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class MetricsUiState(
    val metrics: MetricsDto? = null,
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)

class MetricsViewModel(private val context: Context) : ViewModel() {
    private val api = ApiClient.getService(context)

    private val _uiState = MutableStateFlow(MetricsUiState())
    val uiState: StateFlow<MetricsUiState> = _uiState.asStateFlow()

    init {
        loadMetrics()
    }

    fun loadMetrics() {
        _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
        viewModelScope.launch {
            try {
                val resp = api.getStoreMetrics()
                if (resp.isSuccessful && resp.body() != null) {
                    _uiState.value = _uiState.value.copy(isLoading = false, metrics = resp.body())
                } else {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        errorMessage = "خطا در دریافت آمار عملکرد"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    errorMessage = e.message ?: "عدم اتصال به سرور"
                )
            }
        }
    }
}
