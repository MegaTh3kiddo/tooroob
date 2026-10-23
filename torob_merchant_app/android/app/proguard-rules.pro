# Retrofit rules
-dontwarn okio.**
-dontwarn javax.annotation.**
-keepattributes Signature
-keepattributes *Annotation*
-keep class com.squareup.retrofit2.** { *; }

# Gson rules
-keepclassmembers class * {
    @com.google.gson.annotations.SerializedName <fields>;
}

# Room rules
-keep class * extends androidx.room.RoomDatabase
-dontwarn androidx.room.paging.**
