package ir.torob.seller.data.local

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface SyncQueueDao {
    @Query("SELECT * FROM sync_queue WHERE syncState = 'SAVED_ON_PHONE' ORDER BY createdAt ASC")
    suspend fun getPendingSyncItems(): List<SyncQueueEntity>

    @Query("SELECT * FROM sync_queue WHERE inquiryId = :inquiryId LIMIT 1")
    fun getResponseForInquiryFlow(inquiryId: String): Flow<SyncQueueEntity?>

    @Query("SELECT * FROM sync_queue WHERE inquiryId = :inquiryId LIMIT 1")
    suspend fun getResponseForInquiry(inquiryId: String): SyncQueueEntity?

    @Query("SELECT COUNT(*) FROM sync_queue WHERE syncState = 'SAVED_ON_PHONE'")
    fun getPendingCountFlow(): Flow<Int>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertSyncItem(item: SyncQueueEntity)

    @Update
    suspend fun updateSyncItem(item: SyncQueueEntity)

    @Query("UPDATE sync_queue SET syncState = :state WHERE clientResponseId = :clientResponseId")
    suspend fun updateSyncState(clientResponseId: String, state: SyncState)

    @Query("DELETE FROM sync_queue WHERE clientResponseId = :clientResponseId")
    suspend fun deleteItem(clientResponseId: String)

    @Query("DELETE FROM sync_queue")
    suspend fun clearAll()
}
