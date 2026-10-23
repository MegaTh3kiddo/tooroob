package ir.torob.seller.data.repository

import android.content.Context
import androidx.work.*
import ir.torob.seller.data.local.*
import ir.torob.seller.data.model.*
import ir.torob.seller.data.remote.ApiClient
import ir.torob.seller.worker.SyncWorker
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import java.text.SimpleDateFormat
import java.util.*
import java.util.concurrent.TimeUnit

class InquiryRepository(val context: Context) {
    private val api = ApiClient.getService(context)
    private val db = SellerDatabase.getDatabase(context)
    private val inquiryDao = db.inquiryDao()
    private val syncQueueDao = db.syncQueueDao()
    private val authRepo = AuthRepository(context)

    private val isoFormat = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).apply {
        timeZone = TimeZone.getTimeZone("UTC")
    }

    fun getLocalInquiries(status: String? = null): Flow<List<InquiryEntity>> {
        val shopId = authRepo.getShopId()
        return if (status.isNullOrBlank()) {
            inquiryDao.getAllInquiries(shopId)
        } else {
            inquiryDao.getInquiriesByStatus(shopId, status.uppercase())
        }
    }

    fun getHistoryInquiries(statusFilter: String? = null): Flow<List<InquiryEntity>> {
        val shopId = authRepo.getShopId()
        return if (statusFilter.isNullOrBlank() || statusFilter.uppercase() == "ALL") {
            inquiryDao.getHistoryInquiries(shopId)
        } else {
            inquiryDao.getHistoryInquiriesFiltered(shopId, statusFilter.uppercase())
        }
    }

    suspend fun clearAllLocalData() {
        inquiryDao.clearAllInquiries()
        syncQueueDao.clearAll()
    }

    suspend fun markInquiryExpired(inquiryId: String) {
        inquiryDao.updateInquiryStatus(inquiryId, "EXPIRED")
    }

    suspend fun fetchRemoteInquiries(status: String? = null): Result<List<InquiryDto>> {
        val shopId = authRepo.getShopId()
        return try {
            val resp = api.getInquiries(status)
            if (resp.isSuccessful && resp.body() != null) {
                val list = resp.body()!!
                // Clear old cache for this shop so stale inquiries or other accounts' data never persist
                inquiryDao.clearInquiriesForShop(shopId)
                val entities = list.map { it.toEntity() }
                inquiryDao.insertInquiries(entities)
                Result.success(list)
            } else {
                Result.failure(Exception(resp.errorBody()?.string() ?: "خطا در دریافت استعلام‌ها"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getInquiryById(inquiryId: String): InquiryEntity? {
        val shopId = authRepo.getShopId()
        val cached = inquiryDao.getInquiryById(inquiryId, shopId)
        if (cached != null) return cached

        // Fetch remote if not in cache
        try {
            val resp = api.getInquiryDetail(inquiryId)
            if (resp.isSuccessful && resp.body() != null) {
                val dto = resp.body()!!
                val entity = dto.toEntity()
                inquiryDao.insertInquiry(entity)
                return entity
            }
        } catch (e: Exception) {
            // Offline fallback
        }

        return null
    }

    fun getSyncStateForInquiry(inquiryId: String): Flow<SyncState?> {
        return syncQueueDao.getResponseForInquiryFlow(inquiryId).map { it?.syncState }
    }

    fun getPendingOfflineCount(): Flow<Int> = syncQueueDao.getPendingCountFlow()

    suspend fun submitResponse(
        inquiryId: String,
        priceToman: Long,
        inStock: Boolean,
        notes: String?,
        stockCount: Int = 1,
        status: String? = null,
        declineReason: String? = null
    ): Result<SyncState> {
        val clientUuid = UUID.randomUUID().toString()
        val submittedAtIso = isoFormat.format(Date())

        val targetStatus = status ?: if (inStock) "ANSWERED" else "OUT_OF_STOCK"

        // 1. Immediately persist locally in Room DB
        val queueItem = SyncQueueEntity(
            clientResponseId = clientUuid,
            inquiryId = inquiryId,
            offeredPriceToman = priceToman,
            isInStock = inStock,
            stockCount = stockCount,
            notes = notes,
            status = targetStatus,
            declineReason = declineReason,
            submittedAt = submittedAtIso,
            syncState = SyncState.SAVED_ON_PHONE
        )
        syncQueueDao.insertSyncItem(queueItem)
        inquiryDao.updateInquiryResponse(
            id = inquiryId,
            status = targetStatus,
            declineReason = declineReason,
            price = priceToman,
            inStock = inStock,
            notes = notes
        )

        // 2. Attempt immediate network submission
        return try {
            val request = InquiryResponseRequest(
                clientResponseId = clientUuid,
                offeredPriceToman = priceToman,
                isInStock = inStock,
                stockCount = stockCount,
                notes = notes,
                status = targetStatus,
                declineReason = declineReason,
                submittedAt = submittedAtIso
            )
            val resp = api.submitResponse(inquiryId, request)
            if (resp.isSuccessful) {
                // Marked as permanently SYNCED on server
                syncQueueDao.updateSyncState(clientUuid, SyncState.SYNCED_ON_SERVER)
                Result.success(SyncState.SYNCED_ON_SERVER)
            } else {
                scheduleBackgroundSync()
                Result.success(SyncState.SAVED_ON_PHONE)
            }
        } catch (e: Exception) {
            scheduleBackgroundSync()
            Result.success(SyncState.SAVED_ON_PHONE)
        }
    }

    suspend fun syncPendingResponses(): BatchSyncResponse? {
        val pending = syncQueueDao.getPendingSyncItems()
        if (pending.isEmpty()) return null

        val batchItems = pending.map {
            BatchSyncItem(
                inquiryId = it.inquiryId,
                clientResponseId = it.clientResponseId,
                offeredPriceToman = it.offeredPriceToman,
                isInStock = it.isInStock,
                stockCount = it.stockCount,
                notes = it.notes,
                status = it.status,
                declineReason = it.declineReason,
                submittedAt = it.submittedAt
            )
        }

        return try {
            val resp = api.batchSyncResponses(BatchSyncRequest(batchItems))
            if (resp.isSuccessful && resp.body() != null) {
                val batchResult = resp.body()!!
                for (item in pending) {
                    syncQueueDao.updateSyncState(item.clientResponseId, SyncState.SYNCED_ON_SERVER)
                }
                batchResult
            } else {
                null
            }
        } catch (e: Exception) {
            null
        }
    }

    private fun scheduleBackgroundSync() {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val syncRequest = OneTimeWorkRequestBuilder<SyncWorker>()
            .setConstraints(constraints)
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 10, TimeUnit.SECONDS)
            .build()

        WorkManager.getInstance(context).enqueueUniqueWork(
            "TorobOfflineSyncWork",
            ExistingWorkPolicy.REPLACE,
            syncRequest
        )
    }
}
