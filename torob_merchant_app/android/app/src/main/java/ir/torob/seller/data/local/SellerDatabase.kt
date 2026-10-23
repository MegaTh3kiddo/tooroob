package ir.torob.seller.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverter
import androidx.room.TypeConverters

class Converters {
    @TypeConverter
    fun fromSyncState(state: SyncState): String = state.name

    @TypeConverter
    fun toSyncState(value: String): SyncState = try {
        SyncState.valueOf(value)
    } catch (e: Exception) {
        SyncState.SAVED_ON_PHONE
    }
}

@Database(entities = [InquiryEntity::class, SyncQueueEntity::class], version = 3, exportSchema = false)
@TypeConverters(Converters::class)
abstract class SellerDatabase : RoomDatabase() {
    abstract fun inquiryDao(): InquiryDao
    abstract fun syncQueueDao(): SyncQueueDao

    companion object {
        @Volatile
        private var INSTANCE: SellerDatabase? = null

        fun getDatabase(context: Context): SellerDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    SellerDatabase::class.java,
                    "torob_seller_local.db"
                )
                .fallbackToDestructiveMigration()
                .build()
                INSTANCE = instance
                instance
            }
        }
    }
}
