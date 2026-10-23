package ir.torob.seller.ui.screens.settings

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings as AndroidSettings
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ir.torob.seller.data.repository.AlertSoundType
import ir.torob.seller.data.repository.AppThemeMode
import ir.torob.seller.ui.components.NotificationPermissionBanner
import ir.torob.seller.ui.theme.*
import ir.torob.seller.ui.viewmodel.AuthViewModel
import ir.torob.seller.ui.viewmodel.SettingsViewModel

// Persian digits converter
private fun String.toPersianDigits(): String {
    val persianDigits = charArrayOf('۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹')
    val sb = StringBuilder()
    for (ch in this) {
        if (ch in '0'..'9') {
            sb.append(persianDigits[ch - '0'])
        } else {
            sb.append(ch)
        }
    }
    return sb.toString()
}

private fun Int.toPersianDigits(): String = this.toString().toPersianDigits()

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    settingsViewModel: SettingsViewModel,
    authViewModel: AuthViewModel,
    hasNotificationPermission: Boolean,
    onRequestNotificationPermission: () -> Unit,
    onLogout: () -> Unit
) {
    val state by settingsViewModel.uiState.collectAsState()
    var showLogoutDialog by remember { mutableStateOf(false) }
    var showSoundPickerSheet by remember { mutableStateOf(false) }
    val context = LocalContext.current

    // Safety: stop preview when leaving settings
    DisposableEffect(Unit) {
        settingsViewModel.refreshFullScreenPermission()
        settingsViewModel.refreshShopStatus()
        onDispose {
            settingsViewModel.stopSoundPreview()
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        // Top App Bar
        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = MaterialTheme.colorScheme.surface,
            shadowElevation = 1.dp
        ) {
            Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp)) {
                Text(
                    text = "تنظیمات برنامه",
                    fontSize = 19.sp,
                    fontWeight = FontWeight.Black,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = "مدیریت اعلان‌ها، ظاهر برنامه، وضعیت فروشگاه و حساب کاربری",
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }

        // Feedback Snackbar / Banner
        AnimatedVisibility(
            visible = state.feedbackMessage != null,
            enter = fadeIn(),
            exit = fadeOut()
        ) {
            state.feedbackMessage?.let { msg ->
                Surface(
                    color = TorobSuccessLight,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp, vertical = 10.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                            text = msg,
                            fontSize = 12.sp,
                            color = TorobSuccess,
                            fontWeight = FontWeight.Bold
                        )
                        IconButton(
                            onClick = { settingsViewModel.clearFeedbackMessage() },
                            modifier = Modifier.size(20.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Close,
                                contentDescription = "بستن",
                                tint = TorobSuccess,
                                modifier = Modifier.size(16.dp)
                            )
                        }
                    }
                }
            }
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Android System Notification Permission Banner
            if (!hasNotificationPermission) {
                NotificationPermissionBanner(onEnableClicked = onRequestNotificationPermission)
            }

            // ==========================================
            // Section 1: Notifications & Instant Alerts
            // ==========================================
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.5f), RoundedCornerShape(16.dp)),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 0.5.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    SectionHeader(
                        icon = Icons.Default.Notifications,
                        title = "اعلان‌ها و استعلام‌های فوری",
                        iconColor = TorobRed,
                        iconBg = TorobRedLight
                    )

                    Spacer(modifier = Modifier.height(14.dp))

                    // Switch 1: Inquiry Push Notifications
                    SettingSwitchRow(
                        title = "دریافت نوتیفیکیشن استعلام جدید",
                        subtitle = "اعلان صوتی در ثانیه صفر و یادآوری مجدد در صورت عدم پاسخ",
                        checked = state.notificationsEnabled,
                        onCheckedChange = settingsViewModel::toggleNotifications
                    )

                    Spacer(modifier = Modifier.height(12.dp))
                    HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.3f), thickness = 0.8.dp)
                    Spacer(modifier = Modifier.height(12.dp))

                    // Switch 2: Urgent Ringtone
                    SettingSwitchRow(
                        title = "پخش زنگ استعلام فوری",
                        subtitle = "پخش صدای ممتد هنگام دریافت استعلام تا زمان پاسخگویی",
                        checked = state.urgentRingEnabled,
                        enabled = state.notificationsEnabled,
                        onCheckedChange = settingsViewModel::toggleUrgentRing
                    )

                    Spacer(modifier = Modifier.height(12.dp))
                    HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.3f), thickness = 0.8.dp)
                    Spacer(modifier = Modifier.height(12.dp))

                    // Switch 3: Vibration
                    SettingSwitchRow(
                        title = "لرزش (ویبره) هنگام استعلام",
                        subtitle = "ویبره گوشی هنگام اعلام استعلام جدید برای جلوگیری از بی‌پاسخ ماندن",
                        checked = state.vibrationEnabled,
                        enabled = state.notificationsEnabled,
                        onCheckedChange = settingsViewModel::toggleVibration
                    )

                    Spacer(modifier = Modifier.height(14.dp))
                    HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.3f), thickness = 0.8.dp)
                    Spacer(modifier = Modifier.height(14.dp))

                    // Alert Sound Selection Row
                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(12.dp))
                            .clickable { showSoundPickerSheet = true },
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                modifier = Modifier.weight(1f)
                            ) {
                                Box(
                                    modifier = Modifier
                                        .size(34.dp)
                                        .background(TorobRedLight, CircleShape),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.MusicNote,
                                        contentDescription = null,
                                        tint = TorobRed,
                                        modifier = Modifier.size(18.dp)
                                    )
                                }
                                Spacer(modifier = Modifier.width(10.dp))
                                Column {
                                    Text(
                                        text = "صدای زنگ و اعلان استعلام",
                                        fontSize = 13.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.onSurface
                                    )
                                    Spacer(modifier = Modifier.height(2.dp))
                                    Text(
                                        text = state.alertSoundType.title,
                                        fontSize = 11.sp,
                                        color = TorobRedDark,
                                        fontWeight = FontWeight.Medium
                                    )
                                }
                            }

                            FilledTonalButton(
                                onClick = { showSoundPickerSheet = true },
                                shape = RoundedCornerShape(8.dp),
                                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                            ) {
                                Text("تغییر", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    // Sound Test Preview Button
                    OutlinedButton(
                        onClick = { settingsViewModel.toggleSoundPreview() },
                        colors = ButtonDefaults.outlinedButtonColors(
                            contentColor = if (state.isPreviewPlaying) TorobError else MaterialTheme.colorScheme.onSurface
                        ),
                        border = BorderStroke(
                            1.dp,
                            if (state.isPreviewPlaying) TorobError else MaterialTheme.colorScheme.outline
                        ),
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = if (state.isPreviewPlaying) Icons.Default.Stop else Icons.Default.PlayArrow,
                                contentDescription = null,
                                tint = if (state.isPreviewPlaying) TorobError else TorobRed,
                                modifier = Modifier.size(18.dp)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = if (state.isPreviewPlaying) "توقف پخش صدا" else "پخش نمونه زنگ انتخابی",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    // Full-screen Alert Permission Status
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                        if (!state.canUseFullScreenIntent) {
                            Surface(
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(12.dp),
                                color = TorobWarningLight,
                                border = BorderStroke(1.dp, TorobWarning.copy(alpha = 0.5f))
                            ) {
                                Column(modifier = Modifier.padding(12.dp)) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(
                                            imageVector = Icons.Default.Security,
                                            contentDescription = null,
                                            tint = TorobWarning,
                                            modifier = Modifier.size(18.dp)
                                        )
                                        Spacer(modifier = Modifier.width(6.dp))
                                        Text(
                                            text = "مجوز اعلان تمام‌صفحه غیرفعال است",
                                            fontSize = 12.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = TorobWarning
                                        )
                                    }
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(
                                        text = "برای نمایش صفحه استعلام فوری روی قفل گوشی، فعال‌سازی این مجوز الزامی است.",
                                        fontSize = 11.sp,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        lineHeight = 16.sp
                                    )
                                    Spacer(modifier = Modifier.height(8.dp))
                                    Button(
                                        onClick = {
                                            try {
                                                val intent = Intent(AndroidSettings.ACTION_MANAGE_APP_USE_FULL_SCREEN_INTENT).apply {
                                                    data = Uri.parse("package:${context.packageName}")
                                                }
                                                context.startActivity(intent)
                                            } catch (_: Exception) {
                                                val intent = Intent(AndroidSettings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                                                    data = Uri.fromParts("package", context.packageName, null)
                                                }
                                                context.startActivity(intent)
                                            }
                                        },
                                        colors = ButtonDefaults.buttonColors(containerColor = TorobWarning),
                                        shape = RoundedCornerShape(8.dp),
                                        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                                    ) {
                                        Text("تنظیم مجوز تمام‌صفحه", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Color.White)
                                    }
                                }
                            }
                            Spacer(modifier = Modifier.height(10.dp))
                        } else {
                            Surface(
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(10.dp),
                                color = TorobSuccessLight
                            ) {
                                Row(
                                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.CheckCircle,
                                        contentDescription = null,
                                        tint = TorobSuccess,
                                        modifier = Modifier.size(15.dp)
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text(
                                        text = "مجوز نمایش اعلان تمام‌صفحه فعال است",
                                        fontSize = 11.sp,
                                        fontWeight = FontWeight.Medium,
                                        color = TorobSuccess
                                    )
                                }
                            }
                            Spacer(modifier = Modifier.height(10.dp))
                        }
                    }

                    // Autostart & Battery Background Optimization Shortcut
                    OutlinedButton(
                        onClick = {
                            val intent = Intent(AndroidSettings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                                data = Uri.fromParts("package", context.packageName, null)
                            }
                            context.startActivity(intent)
                        },
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.5f)),
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.BatteryChargingFull,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "تنظیمات پس‌زمینه و شروع خودکار (Autostart)",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
            }

            // ==========================================
            // Section 2: Appearance & Theme
            // ==========================================
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.5f), RoundedCornerShape(16.dp)),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 0.5.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    SectionHeader(
                        icon = Icons.Default.DarkMode,
                        title = "ظاهر برنامه",
                        iconColor = MaterialTheme.colorScheme.primary,
                        iconBg = MaterialTheme.colorScheme.primaryContainer
                    )

                    Spacer(modifier = Modifier.height(6.dp))

                    Text(
                        text = "انتخاب حالت تم برای سازگاری بهتر با شرایط نوری محیط شما",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )

                    Spacer(modifier = Modifier.height(14.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        ThemeOptionCard(
                            title = "سیستم",
                            icon = Icons.Default.BrightnessAuto,
                            isSelected = state.themeMode == AppThemeMode.SYSTEM,
                            modifier = Modifier.weight(1f),
                            onClick = { settingsViewModel.setThemeMode(AppThemeMode.SYSTEM) }
                        )

                        ThemeOptionCard(
                            title = "روشن",
                            icon = Icons.Default.LightMode,
                            isSelected = state.themeMode == AppThemeMode.LIGHT,
                            modifier = Modifier.weight(1f),
                            onClick = { settingsViewModel.setThemeMode(AppThemeMode.LIGHT) }
                        )

                        ThemeOptionCard(
                            title = "تاریک",
                            icon = Icons.Default.DarkMode,
                            isSelected = state.themeMode == AppThemeMode.DARK,
                            modifier = Modifier.weight(1f),
                            onClick = { settingsViewModel.setThemeMode(AppThemeMode.DARK) }
                        )
                    }
                }
            }

            // ==========================================
            // Section 3: Store Availability
            // ==========================================
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.5f), RoundedCornerShape(16.dp)),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 0.5.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        SectionHeader(
                            icon = Icons.Default.Storefront,
                            title = "وضعیت فروشگاه",
                            iconColor = TorobSuccess,
                            iconBg = TorobSuccessLight
                        )

                        if (state.isShopLoading) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(18.dp),
                                strokeWidth = 2.dp,
                                color = TorobRed
                            )
                        } else {
                            IconButton(
                                onClick = { settingsViewModel.refreshShopStatus() },
                                modifier = Modifier.size(24.dp)
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Refresh,
                                    contentDescription = "بروزرسانی",
                                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                                    modifier = Modifier.size(18.dp)
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    // Store Status Badge Banner
                    val isShopOpen = state.shop?.isOpen ?: true
                    val isManualOpen = state.shop?.manualIsOpen ?: true
                    val isWorkingHours = state.shop?.isWithinWorkingHours ?: true

                    Surface(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        color = when {
                            isShopOpen -> TorobSuccessLight
                            !isManualOpen -> TorobWarningLight
                            else -> MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f)
                        },
                        border = BorderStroke(
                            1.dp,
                            when {
                                isShopOpen -> TorobSuccess.copy(alpha = 0.4f)
                                !isManualOpen -> TorobWarning.copy(alpha = 0.4f)
                                else -> MaterialTheme.colorScheme.outline.copy(alpha = 0.4f)
                            }
                        )
                    ) {
                        Row(
                            modifier = Modifier.padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                imageVector = when {
                                    isShopOpen -> Icons.Default.CheckCircle
                                    !isManualOpen -> Icons.Default.PauseCircle
                                    else -> Icons.Default.Schedule
                                },
                                contentDescription = null,
                                tint = when {
                                    isShopOpen -> TorobSuccess
                                    !isManualOpen -> TorobWarning
                                    else -> MaterialTheme.colorScheme.onSurfaceVariant
                                },
                                modifier = Modifier.size(24.dp)
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                Text(
                                    text = when {
                                        isShopOpen -> "فروشگاه باز و آماده پاسخگویی"
                                        !isManualOpen -> "فروشگاه موقتاً غیرفعال توسط فروشنده"
                                        else -> "خارج از ساعات کاری فروشگاه"
                                    },
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = when {
                                        isShopOpen -> TorobSuccess
                                        !isManualOpen -> TorobWarning
                                        else -> MaterialTheme.colorScheme.onSurface
                                    }
                                )
                                Spacer(modifier = Modifier.height(2.dp))
                                Text(
                                    text = when {
                                        isShopOpen -> "استعلام‌های آنی به محض ثبت خریدار برای شما ارسال می‌شوند."
                                        !isManualOpen -> "فروشگاه غیرفعال است و هیچ استعلامی دریافت نمی‌کنید."
                                        else -> state.shop?.statusMessage ?: "ساعات کاری فروشگاه به پایان رسیده است."
                                    },
                                    fontSize = 11.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    lineHeight = 16.sp
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    // Store Working Hours Display
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "ساعات کاری تعیین‌شده:",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        val openTime = (state.shop?.openTime ?: "09:00").toPersianDigits()
                        val closeTime = (state.shop?.closeTime ?: "21:00").toPersianDigits()
                        Text(
                            text = "$openTime الی $closeTime",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    }

                    Spacer(modifier = Modifier.height(12.dp))
                    HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.3f), thickness = 0.8.dp)
                    Spacer(modifier = Modifier.height(12.dp))

                    // Store Availability Toggle Switch
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "پذیرش استعلام و وضعیت باز بودن",
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(
                                text = "با خاموش کردن این گزینه، دریافت استعلام‌ها متوقف می‌شود.",
                                fontSize = 11.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }

                        Switch(
                            checked = isShopOpen,
                            onCheckedChange = { settingsViewModel.toggleShopStatus() },
                            enabled = !state.isShopLoading,
                            colors = SwitchDefaults.colors(
                                checkedThumbColor = Color.White,
                                checkedTrackColor = TorobSuccess
                            )
                        )
                    }
                }
            }

            // ==========================================
            // Section 4: Account & Support
            // ==========================================
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.5f), RoundedCornerShape(16.dp)),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 0.5.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    SectionHeader(
                        icon = Icons.Default.AccountCircle,
                        title = "حساب کاربری و مشخصات فروشگاه",
                        iconColor = TorobInfo,
                        iconBg = TorobInfoLight
                    )

                    Spacer(modifier = Modifier.height(14.dp))

                    InfoRow(
                        icon = Icons.Default.Store,
                        label = "نام فروشگاه",
                        value = state.shop?.shopName?.ifBlank { "فروشگاه موبایل تخت جمشید" } ?: "فروشگاه موبایل تخت جمشید"
                    )

                    Spacer(modifier = Modifier.height(10.dp))
                    HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.2f), thickness = 0.6.dp)
                    Spacer(modifier = Modifier.height(10.dp))

                    InfoRow(
                        icon = Icons.Default.Person,
                        label = "نام مدیر فروشگاه",
                        value = state.sellerName.ifBlank { "علی رضایی" }
                    )

                    Spacer(modifier = Modifier.height(10.dp))
                    HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.2f), thickness = 0.6.dp)
                    Spacer(modifier = Modifier.height(10.dp))

                    InfoRow(
                        icon = Icons.Default.Phone,
                        label = "شماره تماس همراه",
                        value = state.sellerPhone.ifBlank { "09123456789" }.toPersianDigits()
                    )

                    Spacer(modifier = Modifier.height(10.dp))
                    HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.2f), thickness = 0.6.dp)
                    Spacer(modifier = Modifier.height(10.dp))

                    InfoRow(
                        icon = Icons.Default.Badge,
                        label = "شناسه فروشگاه (Shop ID)",
                        value = state.shopId.ifBlank { "shop_51d0c1a6edf81ba759726bab" }
                    )

                    Spacer(modifier = Modifier.height(16.dp))

                    // Safe Logout Button
                    OutlinedButton(
                        onClick = { showLogoutDialog = true },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(46.dp),
                        colors = ButtonDefaults.outlinedButtonColors(
                            contentColor = TorobError
                        ),
                        border = BorderStroke(1.dp, TorobError.copy(alpha = 0.5f)),
                        shape = RoundedCornerShape(10.dp)
                    ) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.Logout,
                            contentDescription = null,
                            tint = TorobError,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "خروج از حساب کاربری فروشنده",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = TorobError
                        )
                    }
                }
            }

            // ==========================================
            // Section 5: Application Info
            // ==========================================
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.5f), RoundedCornerShape(16.dp)),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 0.5.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    SectionHeader(
                        icon = Icons.Default.Info,
                        title = "درباره برنامه",
                        iconColor = MaterialTheme.colorScheme.onSurfaceVariant,
                        iconBg = MaterialTheme.colorScheme.surfaceVariant
                    )

                    Spacer(modifier = Modifier.height(14.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                            text = "نام نرم‌افزار",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = "اپلیکیشن فروشندگان ترب",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                            text = "نسخه نرم‌افزار",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = "${state.appVersionName} (کد ساخت ${state.appVersionCode})".toPersianDigits(),
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                            text = "فناوری توسعه رابط کاربری",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = "Jetpack Compose • Material 3",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = TorobRed
                        )
                    }

                    Spacer(modifier = Modifier.height(14.dp))
                    HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.2f), thickness = 0.6.dp)
                    Spacer(modifier = Modifier.height(12.dp))

                    Text(
                        text = "سامانه استعلام آنی قیمت و موجودی ترب",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.8f),
                        modifier = Modifier.align(Alignment.CenterHorizontally)
                    )
                }
            }
        }
    }

    // ==========================================
    // Sound Picker Modal Bottom Sheet
    // ==========================================
    if (showSoundPickerSheet) {
        ModalBottomSheet(
            onDismissRequest = {
                settingsViewModel.stopSoundPreview()
                showSoundPickerSheet = false
            },
            containerColor = MaterialTheme.colorScheme.surface,
            shape = RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp, vertical = 8.dp)
            ) {
                Text(
                    text = "انتخاب صدای اعلان و زنگ استعلام",
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "صدای مورد نظر خود را برای هشدار استعلام‌های دریافتی انتخاب کنید:",
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Spacer(modifier = Modifier.height(16.dp))

                AlertSoundType.values().forEach { soundType ->
                    val isSelected = state.alertSoundType == soundType

                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp)
                            .clip(RoundedCornerShape(12.dp))
                            .clickable {
                                settingsViewModel.selectAlertSound(soundType)
                            },
                        color = if (isSelected) TorobRedLight else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f),
                        border = BorderStroke(
                            1.dp,
                            if (isSelected) TorobRed else MaterialTheme.colorScheme.outline.copy(alpha = 0.3f)
                        ),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                modifier = Modifier.weight(1f)
                            ) {
                                RadioButton(
                                    selected = isSelected,
                                    onClick = { settingsViewModel.selectAlertSound(soundType) },
                                    colors = RadioButtonDefaults.colors(
                                        selectedColor = TorobRed,
                                        unselectedColor = MaterialTheme.colorScheme.outline
                                    )
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Column {
                                    Text(
                                        text = soundType.title,
                                        fontSize = 13.sp,
                                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                                        color = if (isSelected) TorobRedDark else MaterialTheme.colorScheme.onSurface
                                    )
                                    Spacer(modifier = Modifier.height(2.dp))
                                    Text(
                                        text = soundType.subtitle,
                                        fontSize = 11.sp,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            }

                            // Inline preview button
                            IconButton(
                                onClick = { settingsViewModel.toggleSoundPreview(soundType) },
                                modifier = Modifier.size(36.dp)
                            ) {
                                Icon(
                                    imageVector = if (state.isPreviewPlaying && state.alertSoundType == soundType) {
                                        Icons.Default.Stop
                                    } else {
                                        Icons.Default.PlayArrow
                                    },
                                    contentDescription = "پیش‌نمایش",
                                    tint = if (isSelected) TorobRed else MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(20.dp))

                Button(
                    onClick = {
                        settingsViewModel.stopSoundPreview()
                        showSoundPickerSheet = false
                    },
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = TorobRed),
                    shape = RoundedCornerShape(10.dp)
                ) {
                    Text("تأیید و بازگشت", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                }

                Spacer(modifier = Modifier.height(16.dp))
            }
        }
    }

    // ==========================================
    // Safe Logout Confirmation Dialog
    // ==========================================
    if (showLogoutDialog) {
        AlertDialog(
            onDismissRequest = { showLogoutDialog = false },
            title = {
                Text(
                    text = "خروج از حساب کاربری",
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp,
                    color = MaterialTheme.colorScheme.onSurface
                )
            },
            text = {
                Text(
                    text = "آیا اطمینان دارید که می‌خواهید از حساب کاربری خود خارج شوید؟ برای دریافت مجدد استعلام‌ها باید دوباره وارد شوید.",
                    fontSize = 13.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    lineHeight = 20.sp
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        showLogoutDialog = false
                        authViewModel.logout()
                        onLogout()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = TorobError),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text("بله، خروج", color = Color.White, fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { showLogoutDialog = false }) {
                    Text("انصراف", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            },
            containerColor = MaterialTheme.colorScheme.surface,
            shape = RoundedCornerShape(16.dp)
        )
    }
}

@Composable
private fun SectionHeader(
    icon: ImageVector,
    title: String,
    iconColor: Color,
    iconBg: Color
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Box(
            modifier = Modifier
                .size(32.dp)
                .background(iconBg, RoundedCornerShape(8.dp)),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = iconColor,
                modifier = Modifier.size(18.dp)
            )
        }

        Text(
            text = title,
            fontSize = 14.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onSurface
        )
    }
}

@Composable
private fun SettingSwitchRow(
    title: String,
    subtitle: String,
    checked: Boolean,
    enabled: Boolean = true,
    onCheckedChange: (Boolean) -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = if (enabled) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = subtitle,
                fontSize = 11.sp,
                color = if (enabled) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f),
                lineHeight = 16.sp
            )
        }

        Spacer(modifier = Modifier.width(12.dp))

        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
            enabled = enabled,
            colors = SwitchDefaults.colors(
                checkedThumbColor = Color.White,
                checkedTrackColor = TorobSuccess
            )
        )
    }
}

@Composable
private fun ThemeOptionCard(
    title: String,
    icon: ImageVector,
    isSelected: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    Surface(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .clickable(onClick = onClick),
        color = if (isSelected) TorobRedLight else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f),
        border = BorderStroke(
            1.5.dp,
            if (isSelected) TorobRed else MaterialTheme.colorScheme.outline.copy(alpha = 0.4f)
        ),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(
            modifier = Modifier.padding(vertical = 12.dp, horizontal = 8.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = if (isSelected) TorobRedDark else MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(22.dp)
            )
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = title,
                fontSize = 11.sp,
                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                color = if (isSelected) TorobRedDark else MaterialTheme.colorScheme.onSurface
            )
        }
    }
}

@Composable
private fun InfoRow(
    icon: ImageVector,
    label: String,
    value: String
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.weight(1f)
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(16.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = label,
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        Text(
            text = value,
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onSurface
        )
    }
}
