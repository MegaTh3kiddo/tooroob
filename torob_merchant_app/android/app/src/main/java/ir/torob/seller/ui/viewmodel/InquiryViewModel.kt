package ir.torob.seller.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import ir.torob.seller.data.local.InquiryEntity
import ir.torob.seller.data.local.SyncState
import ir.torob.seller.data.local.getLiveRemainingSeconds
import ir.torob.seller.data.repository.InquiryRepository
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

data class InquiryListUiState(
    val inquiries: List<InquiryEntity> = emptyList(),
    val selectedTab: String = "ACTIVE", // ACTIVE, ANSWERED, EXPIRED
    val isLoading: Boolean = false,
    val pendingSyncCount: Int = 0,
    val errorMessage: String? = null
)

data class InquiryDetailUiState(
    val inquiry: InquiryEntity? = null,
    val offeredPriceToman: Long = 0L,
    val isInStock: Boolean = true,
    val stockCount: Int = 1,
    val notes: String = "",
    val isSubmitting: Boolean = false,
    val syncState: SyncState? = null,
    val submissionSuccess: Boolean = false,
    val errorMessage: String? = null
)

class InquiryViewModel(private val repository: InquiryRepository) : ViewModel() {

    private val _selectedTab = MutableStateFlow("ACTIVE")
    val selectedTab: StateFlow<String> = _selectedTab.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    val pendingSyncCount: StateFlow<Int> = repository.getPendingOfflineCount()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), 0)

    val activeInquiries: StateFlow<List<InquiryEntity>> = repository.getLocalInquiries("ACTIVE")
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val inquiries: StateFlow<List<InquiryEntity>> = activeInquiries

    private val _historyFilter = MutableStateFlow("ALL")
    val historyFilter: StateFlow<String> = _historyFilter.asStateFlow()

    private val _isServerConnected = MutableStateFlow(true)
    val isServerConnected: StateFlow<Boolean> = _isServerConnected.asStateFlow()

    @OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
    val historyInquiries: StateFlow<List<InquiryEntity>> = _historyFilter
        .flatMapLatest { filter ->
            when (filter) {
                "ALL" -> repository.getHistoryInquiries("ALL")
                "ANSWERED" -> repository.getLocalInquiries("ANSWERED")
                "OUT_OF_STOCK" -> repository.getLocalInquiries("OUT_OF_STOCK")
                "DECLINED" -> repository.getLocalInquiries("DECLINED")
                "EXPIRED" -> repository.getLocalInquiries("EXPIRED")
                else -> repository.getHistoryInquiries(filter)
            }
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val answeredInquiries: StateFlow<List<InquiryEntity>> = repository.getLocalInquiries("ANSWERED")
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun setHistoryFilter(filter: String) {
        _historyFilter.value = filter
    }

    private val _detailUiState = MutableStateFlow(InquiryDetailUiState())
    val detailUiState: StateFlow<InquiryDetailUiState> = _detailUiState.asStateFlow()
    private val alertedInquiryIds = mutableSetOf<String>()

    init {
        refresh()
        startPeriodicSyncAndUrgentCheck()
    }

    private fun startPeriodicSyncAndUrgentCheck() {
        viewModelScope.launch {
            while (true) {
                delay(3000L)
                if (_isServerConnected.value) {
                    try {
                        repository.fetchRemoteInquiries()
                    } catch (_: Exception) {}
                }

                // Check active inquiries for urgent ringing (<= 120s) or auto-expiry (<= 0s)
                val currentActive = activeInquiries.value
                for (inq in currentActive) {
                    val remaining = inq.getLiveRemainingSeconds()
                    if (remaining <= 0) {
                        markInquiryExpired(inq.inquiryId)
                    } else if (remaining in 1..120 && inq.inquiryId !in alertedInquiryIds) {
                        alertedInquiryIds.add(inq.inquiryId)
                        triggerUrgentCall(inq)
                    }
                }
            }
        }
    }

    fun markInquiryExpired(inquiryId: String) {
        viewModelScope.launch {
            repository.markInquiryExpired(inquiryId)
            try {
                ir.torob.seller.util.InquiryRingtoneManager.stopRinging(repository.context)
                val stopIntent = android.content.Intent(repository.context, ir.torob.seller.service.InquiryAlertService::class.java).apply {
                    action = ir.torob.seller.service.InquiryAlertService.ACTION_STOP_ALERT
                }
                repository.context.startService(stopIntent)
            } catch (_: Exception) {}
        }
    }

    private fun triggerUrgentCall(inquiry: InquiryEntity) {
        try {
            val ctx = repository.context
            val intent = android.content.Intent(ctx, ir.torob.seller.service.InquiryAlertService::class.java).apply {
                action = ir.torob.seller.service.InquiryAlertService.ACTION_START_ALERT
                putExtra("inquiry_id", inquiry.inquiryId)
                putExtra("title", "تماس فوری استعلام ترب")
                putExtra("body", "فقط ۲ دقیقه تا پایان مهلت پاسخ به استعلام «${inquiry.productTitle}» باقی مانده است!")
                putExtra("duration_seconds", minOf(120, inquiry.getLiveRemainingSeconds().toInt()))
            }
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                ctx.startForegroundService(intent)
            } else {
                ctx.startService(intent)
            }
        } catch (e: Exception) {
            android.util.Log.e("InquiryViewModel", "Error triggering urgent call: ${e.message}", e)
        }
    }

    fun selectTab(tab: String) {
        _selectedTab.value = tab
    }

    fun refresh() {
        _isLoading.value = true
        _errorMessage.value = null
        viewModelScope.launch {
            repository.fetchRemoteInquiries()
                .onSuccess {
                    _isServerConnected.value = true
                }
                .onFailure {
                    _isServerConnected.value = false
                    _errorMessage.value = "عدم ارتباط با سرور ترب. جهت امنیت اطلاعات، استعلام‌ها بدون ارتباط با سرور نمایش داده نمی‌شوند."
                }
            _isLoading.value = false
        }
    }

    fun silentRefresh() {
        viewModelScope.launch {
            try {
                repository.fetchRemoteInquiries()
            } catch (_: Exception) {
                // Background sync failure handled silently
            }
        }
    }

    fun loadInquiryDetail(inquiryId: String) {
        _detailUiState.value = InquiryDetailUiState()
        viewModelScope.launch {
            val item = repository.getInquiryById(inquiryId)
            if (item != null) {
                _detailUiState.value = _detailUiState.value.copy(
                    inquiry = item,
                    offeredPriceToman = item.recordedPriceToman
                )
                // Observe local sync state
                repository.getSyncStateForInquiry(inquiryId).collect { state ->
                    _detailUiState.value = _detailUiState.value.copy(syncState = state)
                }
            } else {
                _detailUiState.value = _detailUiState.value.copy(errorMessage = "استعلام یافت نشد")
            }
        }
    }

    fun onPriceChanged(price: Long) {
        _detailUiState.value = _detailUiState.value.copy(offeredPriceToman = price)
    }

    fun onStockToggled(inStock: Boolean) {
        _detailUiState.value = _detailUiState.value.copy(isInStock = inStock)
    }

    fun onStockCountChanged(count: Int) {
        val safeCount = count.coerceAtLeast(1)
        _detailUiState.value = _detailUiState.value.copy(stockCount = safeCount)
    }

    fun onNotesChanged(notes: String) {
        _detailUiState.value = _detailUiState.value.copy(notes = notes)
    }

    fun submitResponse(inquiryId: String) {
        // Prevent double submit debounce
        if (_detailUiState.value.isSubmitting) return

        val state = _detailUiState.value
        _detailUiState.value = state.copy(isSubmitting = true, errorMessage = null)

        viewModelScope.launch {
            repository.submitResponse(
                inquiryId = inquiryId,
                priceToman = state.offeredPriceToman,
                inStock = state.isInStock,
                notes = state.notes.ifBlank { null },
                stockCount = if (state.isInStock) state.stockCount else 0
            ).onSuccess { syncState ->
                _detailUiState.value = _detailUiState.value.copy(
                    isSubmitting = false,
                    syncState = syncState,
                    submissionSuccess = true
                )
            }.onFailure { err ->
                _detailUiState.value = _detailUiState.value.copy(
                    isSubmitting = false,
                    errorMessage = err.message ?: "خطا در ثبت پاسخ"
                )
            }
        }
    }

    fun clearSubmissionSuccess() {
        _detailUiState.value = _detailUiState.value.copy(submissionSuccess = false)
    }
}
