package ir.torob.seller.data.local

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface InquiryDao {
    @Query("SELECT * FROM inquiries WHERE shopId = :shopId ORDER BY createdAt DESC")
    fun getAllInquiries(shopId: String): Flow<List<InquiryEntity>>

    @Query("SELECT * FROM inquiries WHERE shopId = :shopId AND status = :status ORDER BY createdAt DESC")
    fun getInquiriesByStatus(shopId: String, status: String): Flow<List<InquiryEntity>>

    @Query("SELECT * FROM inquiries WHERE shopId = :shopId AND status IN ('ANSWERED', 'OUT_OF_STOCK', 'DECLINED', 'EXPIRED') ORDER BY createdAt DESC")
    fun getHistoryInquiries(shopId: String): Flow<List<InquiryEntity>>

    @Query("SELECT * FROM inquiries WHERE shopId = :shopId AND status = :status ORDER BY createdAt DESC")
    fun getHistoryInquiriesFiltered(shopId: String, status: String): Flow<List<InquiryEntity>>

    @Query("SELECT * FROM inquiries WHERE inquiryId = :id AND shopId = :shopId")
    suspend fun getInquiryById(id: String, shopId: String): InquiryEntity?

    @Query("SELECT * FROM inquiries WHERE inquiryId = :id")
    suspend fun getInquiryByIdDirect(id: String): InquiryEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertInquiries(inquiries: List<InquiryEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertInquiry(inquiry: InquiryEntity)

    @Query("UPDATE inquiries SET status = :status WHERE inquiryId = :id")
    suspend fun updateInquiryStatus(id: String, status: String)

    @Query("UPDATE inquiries SET status = :status, declineReason = :declineReason, responsePrice = :price, responseInStock = :inStock, responseNotes = :notes WHERE inquiryId = :id")
    suspend fun updateInquiryResponse(
        id: String,
        status: String,
        declineReason: String?,
        price: Long?,
        inStock: Boolean?,
        notes: String?
    )

    @Query("DELETE FROM inquiries WHERE shopId = :shopId")
    suspend fun clearInquiriesForShop(shopId: String)

    @Query("DELETE FROM inquiries")
    suspend fun clearAllInquiries()

    @Query("DELETE FROM inquiries WHERE status = 'EXPIRED' AND lastCachedAt < :thresholdTime")
    suspend fun clearOldExpired(thresholdTime: Long)
}
