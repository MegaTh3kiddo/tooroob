package ir.torob.seller.ui.screens.inquiries

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChevronLeft
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.Inbox
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import ir.torob.seller.data.local.getLiveRemainingSeconds
import androidx.compose.ui.unit.sp
import android.os.SystemClock
import ir.torob.seller.data.local.InquiryEntity
import ir.torob.seller.ui.components.*
import ir.torob.seller.ui.theme.*
import ir.torob.seller.ui.viewmodel.InquiryViewModel
import ir.torob.seller.util.PersianFormatters
import kotlinx.coroutines.delay

@Composable
fun InquiriesListScreen(
    viewModel: InquiryViewModel,
    isOnline: Boolean,
    hasNotificationPermission: Boolean,
    onRequestNotificationPermission: () -> Unit,
    onInquiryClick: (String) -> Unit,
    onNavigateToHistory: () -> Unit = {}
) {
    val activeInquiries by viewModel.activeInquiries.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val pendingSyncCount by viewModel.pendingSyncCount.collectAsState()
    val errorMessage by viewModel.errorMessage.collectAsState()

    val isServerConnected by viewModel.isServerConnected.collectAsState()

    var filterType by remember { mutableStateOf("ALL") }

    // Periodic silent sync for incoming inquiries
    LaunchedEffect(Unit) {
        while (true) {
            delay(15_000L)
            viewModel.silentRefresh()
        }
    }

    val liveActiveInquiries = remember(activeInquiries) {
        activeInquiries.filter { it.getLiveRemainingSeconds() > 0 && it.status.equals("ACTIVE", ignoreCase = true) }
    }

    val urgentCount = remember(liveActiveInquiries) {
        liveActiveInquiries.count { it.getLiveRemainingSeconds() in 1..180 }
    }

    val filteredInquiries = remember(liveActiveInquiries, filterType) {
        when (filterType) {
            "URGENT" -> liveActiveInquiries.filter { it.getLiveRemainingSeconds() in 1..180 }
            "NORMAL" -> liveActiveInquiries.filter { it.getLiveRemainingSeconds() !in 1..180 }
            else -> liveActiveInquiries
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        // Connection & Offline Banner
        ConnectionStatusBar(isOnline = isOnline, pendingSyncCount = pendingSyncCount)

        // Modern Top App Bar
        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = MaterialTheme.colorScheme.surface,
            shadowElevation = 1.dp
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 14.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = "استعلام‌های فعال",
                        fontSize = 19.sp,
                        fontWeight = FontWeight.Black,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    if (liveActiveInquiries.isNotEmpty() && isOnline && isServerConnected) {
                        Spacer(modifier = Modifier.width(8.dp))
                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = MaterialTheme.colorScheme.primaryContainer
                        ) {
                            Text(
                                text = "${PersianFormatters.toPersianDigits(liveActiveInquiries.size)} مورد",
                                color = MaterialTheme.colorScheme.primary,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
                            )
                        }
                    }
                }

                FilledTonalButton(
                    onClick = viewModel::refresh,
                    colors = ButtonDefaults.filledTonalButtonColors(
                        containerColor = MaterialTheme.colorScheme.surfaceVariant,
                        contentColor = MaterialTheme.colorScheme.onSurface
                    ),
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
                    shape = RoundedCornerShape(10.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Refresh,
                        contentDescription = "بروزرسانی",
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = "بروزرسانی",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }

        // Notification permission guidance if disabled
        if (!hasNotificationPermission) {
            Box(modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
                NotificationPermissionBanner(onEnableClicked = onRequestNotificationPermission)
            }
        }

        // Interactive Summary Cards (All, Urgent, Normal)
        if (liveActiveInquiries.isNotEmpty() && isOnline && isServerConnected) {
            Box(modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp)) {
                InquirySummaryCards(
                    activeCount = liveActiveInquiries.size,
                    urgentCount = urgentCount,
                    selectedFilter = filterType,
                    onFilterSelected = { filterType = it }
                )
            }
        }

        // Content Area
        when {
            isLoading && liveActiveInquiries.isEmpty() -> {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator(color = TorobRed)
                }
            }

            !isOnline || !isServerConnected -> {
                EmptyStateView(
                    icon = Icons.Default.CloudOff,
                    iconTint = TorobError,
                    iconBgColor = TorobErrorLight,
                    title = "عدم ارتباط با سرور ترب",
                    description = "جهت حفظ امنیت اطلاعات فروشندگان، مشاهده استعلام‌ها بدون برقراری ارتباط با سرور امکان‌پذیر نیست.",
                    actionButtonText = "تلاش مجدد برای اتصال",
                    onActionClick = viewModel::refresh,
                    modifier = Modifier.fillMaxSize()
                )
            }

            liveActiveInquiries.isEmpty() -> {
                EmptyStateView(
                    icon = Icons.Default.Inbox,
                    iconTint = TorobRed,
                    iconBgColor = TorobRedLight,
                    title = "هیچ استعلام فعالی در انتظار پاسخ نیست",
                    description = "استعلام‌های جدید به محض ثبت با زنگ و اعلان به شما اطلاع داده می‌شوند.",
                    actionButtonText = "بروزرسانی صندوق",
                    onActionClick = viewModel::refresh,
                    secondaryActionText = "مشاهده استعلام‌های گذشته در تب تاریخچه ←",
                    onSecondaryActionClick = onNavigateToHistory,
                    modifier = Modifier.fillMaxSize()
                )
            }

            filteredInquiries.isEmpty() -> {
                EmptyStateView(
                    icon = Icons.Default.Inbox,
                    iconTint = TorobTextSecondary,
                    iconBgColor = TorobBackground,
                    title = "موردی با این فیلتر یافت نشد",
                    description = "استعلامی مطابق فیلتر انتخابی شما در صف انتظار قرار ندارد.",
                    actionButtonText = "مشاهده همه استعلام‌ها",
                    onActionClick = { filterType = "ALL" },
                    modifier = Modifier.fillMaxSize()
                )
            }

            else -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 4.dp, bottom = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(filteredInquiries, key = { it.inquiryId }) { inq ->
                        ModernInquiryCard(
                            inquiry = inq,
                            onClick = { onInquiryClick(inq.inquiryId) },
                            onExpired = { inqId -> viewModel.markInquiryExpired(inqId) }
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ModernInquiryCard(
    inquiry: InquiryEntity,
    onClick: () -> Unit,
    onExpired: (String) -> Unit = {}
) {
    var liveRemainingSeconds by remember(inquiry.inquiryId, inquiry.remainingSeconds) {
        mutableLongStateOf(inquiry.getLiveRemainingSeconds())
    }

    LaunchedEffect(inquiry.inquiryId, inquiry.remainingSeconds, inquiry.status) {
        if (inquiry.status.equals("ACTIVE", ignoreCase = true)) {
            val initialSeconds = inquiry.getLiveRemainingSeconds()
            liveRemainingSeconds = initialSeconds
            if (initialSeconds <= 0L) {
                onExpired(inquiry.inquiryId)
            } else {
                val startElapsed = SystemClock.elapsedRealtime()
                while (liveRemainingSeconds > 0) {
                    delay(1000L)
                    val elapsed = (SystemClock.elapsedRealtime() - startElapsed) / 1000L
                    liveRemainingSeconds = maxOf(0L, initialSeconds - elapsed)
                }
                onExpired(inquiry.inquiryId)
            }
        } else {
            liveRemainingSeconds = inquiry.getLiveRemainingSeconds()
        }
    }

    val isUrgent = liveRemainingSeconds in 1..180
    val effectiveStatus = if (inquiry.status == "ACTIVE" && liveRemainingSeconds <= 0) "EXPIRED" else inquiry.status

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .border(
                width = if (isUrgent) 1.5.dp else 1.dp,
                color = if (isUrgent) TorobWarning else MaterialTheme.colorScheme.outline,
                shape = RoundedCornerShape(16.dp)
            ),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.5.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            // Top Bar: Tracking code & Status badge with countdown
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "کد رهگیری: ${inquiry.trackingCode}",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                InquiryStatusBadge(
                    status = effectiveStatus,
                    remainingSeconds = liveRemainingSeconds,
                    autoCountdown = false
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Middle: Product Thumbnail + Title + Meta
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.Top,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                ProductThumbnail(
                    imageUrl = inquiry.productImageUrl,
                    contentDescription = inquiry.productTitle,
                    size = 64.dp,
                    cornerRadius = 10.dp
                )

                Column(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    Text(
                        text = inquiry.productTitle,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                        lineHeight = 20.sp
                    )

                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Person,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.size(13.dp)
                        )
                        Text(
                            text = "خریدار: ${inquiry.customerName}",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            // User note if provided
            if (!inquiry.userNote.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(10.dp))
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(8.dp),
                    color = MaterialTheme.colorScheme.surfaceVariant,
                    border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outline)
                ) {
                    Text(
                        text = "سوال خریدار: «${inquiry.userNote}»",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurface,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))
            HorizontalDivider(color = MaterialTheme.colorScheme.outline, thickness = 0.8.dp)
            Spacer(modifier = Modifier.height(10.dp))

            // Bottom Action Row: Reference Price + Big Response Button
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "قیمت مرجع در سایت",
                        fontSize = 10.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        text = PersianFormatters.formatPriceToman(inquiry.recordedPriceToman),
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }

                Button(
                    onClick = onClick,
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = TorobRed
                    ),
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp)
                ) {
                    Text(
                        text = "ثبت پاسخ",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = PureWhite
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Icon(
                        imageVector = Icons.Default.ChevronLeft,
                        contentDescription = null,
                        tint = PureWhite,
                        modifier = Modifier.size(16.dp)
                    )
                }
            }
        }
    }
}
